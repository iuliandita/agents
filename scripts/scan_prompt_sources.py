#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


EXCLUDED_DIRS = {
    ".git",
    ".claude",
    ".codex",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "venv",
}

PROMPT_FILE_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "SKILL.md",
}

PROMPT_SUFFIXES = {
    ".md",
    ".mdx",
    ".prompt",
    ".prompt.yaml",
    ".prompt.yml",
}

HIDDEN_CODEPOINTS = {
    "\u200b",
    "\u200c",
    "\u200d",
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
    "\ufeff",
}

NEGATING_WORDS = re.compile(
    r"\b(avoid|block|blocked|deny|do not|don't|forbid|forbidden|never|reject|refuse|warn)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    message: str
    skip_if_negated: bool = False


RULES = (
    Rule(
        name="hidden-html",
        pattern=re.compile(
            r"<[^>]+(?:display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0|font-size\s*:\s*0)",
            re.IGNORECASE,
        ),
        message="hidden HTML/CSS can conceal instructions from human reviewers",
    ),
    Rule(
        name="commented-override",
        pattern=re.compile(
            r"<!--.*\b(ignore|disregard|override|bypass|forget)\b.{0,80}\b(previous|prior|above|system|developer)\b",
            re.IGNORECASE,
        ),
        message="HTML comments containing override-style instructions are suspicious in prompt files",
    ),
    Rule(
        name="prompt-override",
        pattern=re.compile(
            r"\b(ignore|disregard|override|bypass|forget)\b.{0,80}\b(previous|prior|above|earlier|system|developer|safety|security)\b.{0,80}\b(instruction|message|rule|policy|prompt)s?\b",
            re.IGNORECASE,
        ),
        message="override-style instructions can hijack downstream agents",
    ),
    Rule(
        name="covert-exfiltration",
        pattern=re.compile(
            r"\b(send|upload|post|exfiltrat\w*|steal|leak)\b.{0,100}\b(secret|token|credential|api[-_ ]?key|ssh[-_ ]?key|private[-_ ]?key|environment|\.env)\b",
            re.IGNORECASE,
        ),
        message="instructions to extract or transmit secrets are not valid prompt guidance",
    ),
    Rule(
        name="conceal-from-user",
        pattern=re.compile(
            r"\b(do not|don't|never)\b.{0,80}\b(tell|reveal|inform|mention|show)\b.{0,80}\b(user|maintainer|owner|developer|reviewer)\b",
            re.IGNORECASE,
        ),
        message="instructions to hide behavior from reviewers or users are suspicious",
    ),
    Rule(
        name="network-shell-pipe",
        pattern=re.compile(r"\b(curl|wget)\b[^\n|;&]{0,160}[|>]\s*(?:sudo\s+)?(?:ba)?sh\b", re.IGNORECASE),
        message="network-to-shell commands are high risk in prompt files",
        skip_if_negated=True,
    ),
    Rule(
        name="destructive-command",
        pattern=re.compile(
            r"\b(rm\s+-[A-Za-z]*r[A-Za-z]*f|mkfs(?:\.[a-z0-9]+)?|dd\s+if=.+\s+of=/dev/|shred\s+-[A-Za-z]*z)\b",
            re.IGNORECASE,
        ),
        message="destructive shell commands should not appear as executable prompt guidance",
        skip_if_negated=True,
    ),
)


@dataclass(frozen=True)
class Finding:
    path: Path
    line_no: int
    rule: str
    message: str
    line: str


def is_prompt_source(path: Path) -> bool:
    if path.name in PROMPT_FILE_NAMES:
        return True
    return any(str(path).endswith(suffix) for suffix in PROMPT_SUFFIXES)


def iter_prompt_sources(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.is_file() and is_prompt_source(path):
            paths.append(path)
    return sorted(paths)


def visible_text(text: str, limit: int = 180) -> str:
    escaped = []
    for char in text.strip():
        if char in HIDDEN_CODEPOINTS:
            name = unicodedata.name(char, "UNKNOWN")
            escaped.append(f"\\u{ord(char):04x}<{name}>")
        else:
            escaped.append(char)
    rendered = "".join(escaped)
    return rendered[:limit] + ("..." if len(rendered) > limit else "")


def hidden_codepoints(line: str) -> list[str]:
    return [char for char in line if char in HIDDEN_CODEPOINTS]


def scan_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    rel_path = path.relative_to(root)
    for line_no, line in enumerate(text.splitlines(), start=1):
        if hidden_codepoints(line):
            findings.append(
                Finding(
                    path=rel_path,
                    line_no=line_no,
                    rule="hidden-unicode",
                    message="zero-width or bidirectional Unicode can hide prompt instructions",
                    line=visible_text(line),
                )
            )
        for rule in RULES:
            if rule.skip_if_negated and NEGATING_WORDS.search(line):
                continue
            if rule.pattern.search(line):
                findings.append(
                    Finding(
                        path=rel_path,
                        line_no=line_no,
                        rule=rule.name,
                        message=rule.message,
                        line=visible_text(line),
                    )
                )
    return findings


def scan_prompt_sources(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_prompt_sources(root):
        findings.extend(scan_file(path, root))
    return findings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan prompt source files for injected malicious instructions.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve()
    findings = scan_prompt_sources(root)
    if findings:
        for finding in findings:
            print(f"ERROR: {finding.path}:{finding.line_no}: {finding.rule}: {finding.message}")
            print(f"  {finding.line}")
        print(f"Prompt source scan failed: {len(findings)} finding(s)")
        return 1
    print("Prompt source scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
