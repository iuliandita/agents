#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from render_prompts import HARNESSES


SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[oprsu]_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"glpat-[A-Za-z0-9_-]{20,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{35}"),
    re.compile(r"hf_[A-Za-z0-9]{30,}"),
    re.compile(r"npm_[A-Za-z0-9]{36}"),
)

PRIVATE_PATTERNS = (
    "/home/id/",
    "/home/id",
    "iuliandita",
    "ditas.cc",
    "~/.config/ai",
)

CORE_WARN_LINES = 85
CORE_MAX_LINES = 100
HARNESS_WARN_LINES = 8
HARNESS_MAX_LINES = 10
PRIVATE_EXAMPLE_WARN_LINES = 30
PRIVATE_EXAMPLE_MAX_LINES = 40


def error(message: str) -> None:
    print(f"ERROR: {message}")


def warn(message: str) -> None:
    print(f"WARN: {message}")


def lint_line_count(path: Path, warn_at: int, max_lines: int) -> int:
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    if line_count > max_lines:
        error(f"{path}: {line_count} lines exceeds hard cap {max_lines}")
        return 1
    if line_count > warn_at:
        warn(f"{path}: {line_count} lines exceeds warning threshold {warn_at}")
    return 0


def lint_file(path: Path) -> int:
    failures = 0
    raw = path.read_bytes()
    if b"\r\n" in raw:
        error(f"{path}: contains CRLF line endings; convert to LF")
        failures += 1
    text = raw.decode("utf-8", errors="replace")
    for needle in PRIVATE_PATTERNS:
        if needle in text:
            error(f"{path}: contains private path or name marker: {needle}")
            failures += 1

    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            error(f"{path}: contains a token-like secret pattern: {pattern.pattern}")
            failures += 1

    bad_lines = [
        (line_no, line)
        for line_no, line in enumerate(text.splitlines(), start=1)
        if any(ord(char) > 127 for char in line)
    ]
    for line_no, line in bad_lines:
        error(f"{path}:{line_no}: non-ASCII content: {line}")
        failures += 1
    return failures


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    prompt_root = repo_root / "prompts"
    failures = 0

    core = prompt_root / "core.md"
    if not core.exists():
        error("missing prompts/core.md")
        failures += 1
    else:
        failures += lint_line_count(core, CORE_WARN_LINES, CORE_MAX_LINES)
        failures += lint_file(core)

    registered_fragments = {harness.fragment for harness in HARNESSES}
    for harness in HARNESSES:
        fragment = prompt_root / "harnesses" / harness.fragment
        if not fragment.exists():
            error(f"missing {harness.name} fragment: {fragment}")
            failures += 1
            continue
        failures += lint_line_count(fragment, HARNESS_WARN_LINES, HARNESS_MAX_LINES)
        failures += lint_file(fragment)

    harness_dir = prompt_root / "harnesses"
    if harness_dir.is_dir():
        for fragment_path in sorted(harness_dir.glob("*.md")):
            if fragment_path.name in registered_fragments:
                continue
            error(
                f"{fragment_path}: orphan fragment not registered in HARNESSES; "
                "register it in scripts/render_prompts.py or remove the file"
            )
            failures += 1

    private_example = prompt_root / "private.example.md"
    if not private_example.exists():
        error("missing prompts/private.example.md")
        failures += 1
    else:
        failures += lint_line_count(
            private_example,
            PRIVATE_EXAMPLE_WARN_LINES,
            PRIVATE_EXAMPLE_MAX_LINES,
        )
        failures += lint_file(private_example)

    if failures:
        print(f"Prompt lint failed: {failures} issue(s)")
        return 1
    print("Prompt lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
