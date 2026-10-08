#!/usr/bin/env python3
"""Check local Markdown links, heading anchors, and the script commands shown in the docs."""
from __future__ import annotations

import argparse
import posixpath
import re
import shlex
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

from check_docs_impact import CHANGELOG, ToolError, git, tracked_files


LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ANCHOR_TAG_RE = re.compile(r"<a\s+(?:id|name)=\"([^\"]+)\"")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
WRAPPED_PY_RE = re.compile(r"scripts/([a-z0-9_]+\.py)")
SCRIPT_TOKEN_RE = re.compile(r"scripts/[A-Za-z0-9_.-]+")
URL_SCHEME_RE = re.compile(r"[a-z][a-z0-9+.-]*:")
COMMAND_LANGS = ("", "bash", "sh", "shell", "zsh", "powershell", "pwsh")


def github_slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    # GitHub keeps word-internal underscores, so only backticks, asterisks, and tildes are stripped.
    text = re.sub(r"[`*~]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", text)
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


def markdown_lines(text: str) -> Iterator[tuple[int, str, bool, str | None]]:
    """Yield (number, line, in_fence, fence_lang); fence delimiter lines count as fenced with no language."""
    fence: str | None = None
    lang = ""
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if fence is None:
                fence, lang = marker, stripped[3:].strip().lower()
                yield number, line, True, None
                continue
            if marker == fence:
                fence, lang = None, ""
                yield number, line, True, None
                continue
        yield number, line, fence is not None, lang


def anchors_for(text: str) -> set[str]:
    seen: dict[str, int] = {}
    anchors: set[str] = set()
    for _, line, in_fence, _ in markdown_lines(text):
        if in_fence:
            continue
        anchors.update(ANCHOR_TAG_RE.findall(line))
        match = HEADING_RE.match(line)
        if not match:
            continue
        slug = github_slug(match.group(2))
        count = seen.get(slug, 0)
        anchors.add(slug if count == 0 else f"{slug}-{count}")
        seen[slug] = count + 1
    return anchors


def doc_files(files: list[str], current_only: bool) -> list[str]:
    """Links are checked in every tracked doc, since a broken path is wrong anywhere. Commands are
    checked only in current docs: changelog entries are history, and prompts/ fragments are
    rendered into agent context rather than run."""
    docs = [p for p in files if p.endswith(".md")]
    if current_only:
        docs = [p for p in docs if p != CHANGELOG and not p.startswith("prompts/")]
    return docs


def link_failure(repo: Path, doc: str, target: str, tracked: set[str], cache: dict[str, set[str]]) -> str | None:
    if URL_SCHEME_RE.match(target):
        return None
    path_part, _, anchor = target.partition("#")
    resolved = doc if not path_part else posixpath.normpath(posixpath.join(posixpath.dirname(doc), path_part))
    is_dir = resolved == "." or any(p.startswith(resolved.rstrip("/") + "/") for p in tracked)
    if resolved not in tracked and not is_dir:
        return f"link target '{target}' is not a tracked file"
    if anchor and resolved.endswith(".md"):
        if not (repo / resolved).is_file():
            return f"link target '{target}' is tracked but missing from the work tree"
        if resolved not in cache:
            cache[resolved] = anchors_for((repo / resolved).read_text(encoding="utf-8"))
        if anchor not in cache[resolved]:
            return f"anchor '#{anchor}' not found in {resolved}"
    return None


def check_links(repo: Path, files: list[str]) -> list[str]:
    tracked = set(files)
    cache: dict[str, set[str]] = {}
    failures = []
    for doc in doc_files(files, current_only=False):
        if not (repo / doc).is_file():
            failures.append(f"{doc}: tracked but missing from the work tree")
            continue
        for number, line, in_fence, _ in markdown_lines((repo / doc).read_text(encoding="utf-8")):
            if in_fence:
                continue
            for target in LINK_RE.findall(INLINE_CODE_RE.sub("", line)):
                failure = link_failure(repo, doc, target, tracked, cache)
                if failure:
                    failures.append(f"{doc}:{number}: {failure}")
    return failures


def command_snippets(text: str) -> Iterator[tuple[int, str]]:
    pending: tuple[int, str] | None = None
    for number, line, in_fence, lang in markdown_lines(text):
        if in_fence and lang is None:
            # A fence delimiter ends any continuation, so an unterminated one is still checked.
            if pending:
                yield pending[0], pending[1].strip()
            pending = None
            continue
        if in_fence and lang in COMMAND_LANGS:
            start, joined = pending or (number, "")
            joined += " " + line.strip()
            # Join backslash continuations so their flags are checked with the command.
            if joined.endswith("\\"):
                pending = (start, joined[:-1])
                continue
            pending = None
            yield start, joined.strip()
        elif not in_fence:
            for span in INLINE_CODE_RE.findall(line):
                yield number, span.strip()


def script_flag_sources(repo: Path, script: str) -> str:
    text = (repo / script).read_text(encoding="utf-8", errors="replace")
    sources = [text]
    for name in WRAPPED_PY_RE.findall(text):
        if (repo / "scripts" / name).is_file():
            sources.append((repo / "scripts" / name).read_text(encoding="utf-8"))
    return "\n".join(sources)


def check_commands(repo: Path, files: list[str]) -> list[str]:
    tracked = set(files)
    failures = []
    for doc in doc_files(files, current_only=True):
        if not (repo / doc).is_file():
            continue  # check_links reports the missing file
        text = (repo / doc).read_text(encoding="utf-8")
        for number, snippet in command_snippets(text):
            if "scripts/" not in snippet or snippet.startswith("#"):
                continue
            try:
                tokens = shlex.split(snippet, comments=True, posix=True)
            except ValueError as exc:
                failures.append(f"{doc}:{number}: cannot parse script command ({exc}): {snippet}")
                continue
            script = None
            for token in tokens:
                if token in ("|", "&&", "||", ";"):
                    script = None
                    continue
                candidate = token.removeprefix("./")
                if SCRIPT_TOKEN_RE.fullmatch(candidate):
                    if candidate not in tracked:
                        failures.append(f"{doc}:{number}: command references missing script '{candidate}'")
                        script = None
                    else:
                        script = candidate
                    continue
                if script and token.startswith("--") and len(token) > 2:
                    flag = token.split("=", 1)[0]
                    if not re.search(rf"{re.escape(flag)}(?![\w-])", script_flag_sources(repo, script)):
                        failures.append(f"{doc}:{number}: '{script}' does not define flag '{flag}'")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    try:
        if shutil.which("git") is None:
            raise ToolError("git is required")
        if git(repo, "rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
            raise ToolError(f"{repo} is not a git work tree")
        files = tracked_files(repo)
        failures = check_links(repo, files) + check_commands(repo, files)
    except ToolError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print("Docs links check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
