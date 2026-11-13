#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from bisect import bisect_right
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

# Gitignored local artifacts that quote attack patterns by design (audit
# reports, workflow design docs); they are never rendered or deployed, so they
# do not gate the scan.
EXCLUDED_FILES = {"SECURITY-AUDIT.md"}
EXCLUDED_SUBTREES = (("docs", "local"), ("docs", "superpowers"))

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

# Unicode Tag block (U+E0000-U+E007F) can encode invisible ASCII payloads
# that tokenizers still see; treat the whole range as hidden.
TAG_RANGE_START = 0xE0000
TAG_RANGE_END = 0xE007F


def is_hidden_codepoint(char: str) -> bool:
    cp = ord(char)
    return (
        unicodedata.category(char) == "Cf"
        or cp == 0x034F
        or 0xFE00 <= cp <= 0xFE0F
        or 0xE0100 <= cp <= 0xE01EF
        or TAG_RANGE_START <= cp <= TAG_RANGE_END
    )


DIRECT_COMMAND_NEGATION = re.compile(
    r"\b(avoid|deny|do not|don't|forbid|never|reject|refuse)\b[^;&|.!?,:]{0,40}\b(run|execute|use|pipe|bootstrap)\b",
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
        pattern=re.compile(
            r"\b(?:curl|wget)\b[^\n|;&]{0,160}[|>]\s*"
            r"(?:sudo\s+(?:-E\s+)?)?(?:bash|sh|zsh|python(?:[23](?:\.\d+)?)?)\b"
            r"|\b(?:bash|sh|zsh|python(?:[23](?:\.\d+)?)?)\s+"
            r"(?:<\(\s*|\-c\s+[\"']?\$\(\s*)(?:curl|wget)\b"
            r"|\b(?:iwr|invoke-webrequest)\b[^\n|;&]{0,160}\|\s*(?:iex|invoke-expression)\b",
            re.IGNORECASE,
        ),
        message="network-to-shell commands are high risk in prompt files",
        skip_if_negated=True,
    ),
    Rule(
        name="destructive-command",
        pattern=re.compile(
            r"\b(rm\s+-[A-Za-z]*(?:r[A-Za-z]*f|f[A-Za-z]*r)|mkfs(?:\.[a-z0-9]+)?|dd\s+if=.+\s+of=/dev/|shred\s+-[A-Za-z]*z)\b",
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
        # Exclusions match repo-relative parts only; matching absolute parts
        # would skip the whole repo when it is cloned under e.g. a build/ dir.
        rel_parts = path.relative_to(root).parts
        if rel_parts[0] in EXCLUDED_DIRS:
            continue
        if len(rel_parts) == 1 and path.name in EXCLUDED_FILES:
            continue
        if any(rel_parts[: len(subtree)] == subtree for subtree in EXCLUDED_SUBTREES):
            continue
        render_input = rel_parts == ("prompts", "models.json") or (
            len(rel_parts) == 2 and rel_parts[0] == "prompts" and path.suffix == ".txt"
        )
        if path.is_file() and (is_prompt_source(path) or render_input):
            paths.append(path)
    return sorted(paths)


def visible_text(text: str, limit: int = 180) -> str:
    escaped = []
    for char in text.strip():
        if is_hidden_codepoint(char):
            name = unicodedata.name(char, "UNKNOWN")
            cp = ord(char)
            if cp <= 0xFFFF:
                escaped.append(f"\\u{cp:04x}<{name}>")
            else:
                escaped.append(f"\\U{cp:08x}<{name}>")
        else:
            escaped.append(char)
    rendered = "".join(escaped)
    return rendered[:limit] + ("..." if len(rendered) > limit else "")


def hidden_codepoints(line: str) -> list[str]:
    return [char for char in line if is_hidden_codepoint(char)]


def is_directly_negated(line: str, match_start: int) -> bool:
    prefix = line[max(0, match_start - 80) : match_start]
    negation = None
    for negation in DIRECT_COMMAND_NEGATION.finditer(prefix):
        pass
    if negation is None:
        return False
    # A clause boundary between the negation and the command means the
    # negation does not govern it ("Never run tests; bootstrap with curl|sh").
    return not re.search(r"[;&|.!?,:]", prefix[negation.end() :])


def scan_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    rel_path = path.relative_to(root)
    lines = text.splitlines()
    single_line_hits: set[tuple[str, int, int]] = set()
    for line_no, line in enumerate(lines, start=1):
        if hidden_codepoints(line):
            findings.append(
                Finding(
                    path=rel_path,
                    line_no=line_no,
                    rule="hidden-unicode",
                    message="format characters, variation selectors, or tag-block Unicode can hide prompt instructions",
                    line=visible_text(line),
                )
            )
        for rule in RULES:
            matches = [
                match for match in rule.pattern.finditer(line)
                if not (rule.skip_if_negated and is_directly_negated(line, match.start()))
            ]
            if not matches:
                continue
            single_line_hits.update((rule.name, line_no, match.start()) for match in matches)
            findings.append(
                Finding(
                    path=rel_path,
                    line_no=line_no,
                    rule=rule.name,
                    message=rule.message,
                    line=visible_text(line),
                )
            )

    paragraph: list[tuple[int, str]] = []
    for line_no, line in enumerate([*lines, ""], start=1):
        if line.strip():
            paragraph.append((line_no, line))
            continue
        if len(paragraph) > 1:
            collapsed = " ".join(content for _, content in paragraph)
            offsets: list[int] = []
            offset = 0
            for _, content in paragraph:
                offsets.append(offset)
                offset += len(content) + 1
            for rule in RULES:
                for match in rule.pattern.finditer(collapsed):
                    first_index = bisect_right(offsets, match.start()) - 1
                    last_index = bisect_right(offsets, match.end() - 1) - 1
                    first_line = paragraph[first_index][0]
                    column = match.start() - offsets[first_index]
                    if first_index == last_index or (rule.name, first_line, column) in single_line_hits:
                        continue
                    if rule.skip_if_negated and is_directly_negated(collapsed, match.start()):
                        continue
                    findings.append(Finding(
                        path=rel_path,
                        line_no=first_line,
                        rule=rule.name,
                        message=rule.message,
                        line=visible_text(collapsed),
                    ))
        paragraph = []
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
            print(
                f"error: {finding.path}:{finding.line_no}: {finding.rule}: {finding.message}; line: {finding.line.strip()}",
                file=sys.stderr,
            )
        print(f"Prompt source scan failed: {len(findings)} finding(s)")
        return 1
    print("Prompt source scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
