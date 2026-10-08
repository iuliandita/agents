#!/usr/bin/env python3
"""Flag documentation obligations when prompt sources, renderers, or deployment code change.

Source fingerprints per domain live in docs/contracts.lock.json with a review receipt.
A changed domain needs a new receipt: updated docs or a specific no-impact reason.
This catches review obligations; it cannot prove that prose is correct.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path


LOCK_PATH = "docs/contracts.lock.json"
SCHEMA = 1
CHANGELOG = "CHANGELOG.md"

# Each tracked file under MAPPED_ROOTS must belong to exactly one domain.
# .github/, tests/, and docs are excluded: action pins have Dependabot and
# actionlint, tests are not user-facing, and docs are the obligation itself.
MAPPED_ROOTS = ("agents/", "prompts/", "scripts/", "skills/", "templates/")
DOMAINS: dict[str, dict[str, tuple[str, ...]]] = {
    "prompts": {
        "sources": ("prompts/core.md", "prompts/invariants.md", "prompts/harnesses/*.md"),
        "docs": ("README.md", "INSTALL.md", "docs/surfaces.md", CHANGELOG),
    },
    "models-agents": {
        "sources": (
            "agents/*.md",
            "prompts/models.json",
            "prompts/models.local.example.json",
            "scripts/render_agents.py",
            "scripts/render-agents",
            "scripts/render-agents.ps1",
        ),
        "docs": ("README.md", "INSTALL.md", "docs/harness-contract.md", CHANGELOG),
    },
    "harnesses": {
        "sources": ("scripts/render_prompts.py", "scripts/sync-ai-prompts", "scripts/sync-ai-prompts.ps1"),
        "docs": (
            "README.md",
            "INSTALL.md",
            "docs/harness-contract.md",
            "docs/surfaces.md",
            "docs/legacy-harnesses.md",
            CHANGELOG,
        ),
    },
    "deployment": {
        "sources": (
            "scripts/update",
            "scripts/update.ps1",
            "scripts/update.py",
            "scripts/render_invariants.py",
            "scripts/render-invariants",
            "scripts/render-invariants.ps1",
            "scripts/render_hermes.py",
            "scripts/render-hermes",
            "scripts/render-hermes.ps1",
            "scripts/python-runtime.sh",
            "scripts/python-runtime.ps1",
            "scripts/install_workflow.py",
        ),
        "docs": ("README.md", "INSTALL.md", "SECURITY.md", CHANGELOG),
    },
    "overlays-trust": {
        "sources": (
            "prompts/local.example.md",
            "prompts/private.example.md",
            "prompts/private-patterns.example.txt",
            "scripts/lint_prompts.py",
            "scripts/scan_prompt_sources.py",
            ".gitignore",
        ),
        "docs": ("README.md", "INSTALL.md", "SECURITY.md", CHANGELOG),
    },
    "workflow-templates": {
        "sources": ("skills/*", "templates/*"),
        "docs": ("README.md", "INSTALL.md", CHANGELOG),
    },
    "maintenance": {
        "sources": ("scripts/check_*.py",),
        "docs": ("docs/MAINTENANCE.md", "README.md", CHANGELOG),
    },
}
GENERIC_REASONS = {"docs reviewed", "no impact", "no docs impact", "n/a", "none", "not needed", "nothing to update"}
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ANCHOR_TAG_RE = re.compile(r"<a\s+(?:id|name)=\"([^\"]+)\"")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
HARNESS_NAME_RE = re.compile(r"Harness\(\s*\"([a-z0-9_-]+)\"")
WRAPPED_PY_RE = re.compile(r"scripts/([a-z0-9_]+\.py)")
SCRIPT_TOKEN_RE = re.compile(r"scripts/[A-Za-z0-9_.-]+")
URL_SCHEME_RE = re.compile(r"[a-z][a-z0-9+.-]*:")
COMMAND_LANGS = ("", "bash", "sh", "shell", "zsh", "powershell", "pwsh")
MISSING_LOCK = f"{LOCK_PATH} is missing; create it once with --init --note"


class ToolError(Exception):
    """Missing tooling or invalid usage: exit 2, never a pass."""


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise ToolError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout if result.returncode == 0 else ""


def tracked_files(repo: Path) -> list[str]:
    # The index includes staged new files; untracked scratch files stay out.
    return sorted(p for p in git(repo, "ls-files", "-z").split("\0") if p)


def owners_of(path: str) -> list[str]:
    return [
        name for name, spec in DOMAINS.items() if any(fnmatch.fnmatchcase(path, pat) for pat in spec["sources"])
    ]


def domain_files(files: list[str]) -> dict[str, list[str]]:
    members: dict[str, list[str]] = {name: [] for name in DOMAINS}
    for path in files:
        for name in owners_of(path):
            members[name].append(path)
    return members


def fingerprint(repo: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        file = repo / path
        content = hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else "<deleted>"
        digest.update(f"{path}\0{content}\n".encode())
    return digest.hexdigest()


def load_lock_text(text: str, where: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ToolError(f"{where}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("domains"), dict):
        raise ToolError(f"{where}: expected schema {SCHEMA} with a 'domains' object; migrate the lock explicitly")
    for name, receipt in data["domains"].items():
        if not isinstance(receipt, dict):
            raise ToolError(f"{where}: receipt for '{name}' must be an object")
    return data


def read_lock(repo: Path) -> dict | None:
    path = repo / LOCK_PATH
    return load_lock_text(path.read_text(encoding="utf-8"), LOCK_PATH) if path.exists() else None


def require_lock(repo: Path) -> dict:
    lock = read_lock(repo)
    if lock is None:
        raise ToolError(MISSING_LOCK)
    return lock


def is_breaking(receipt: dict) -> bool:
    return str(receipt.get("breaking", "none")).strip().lower() != "none"


def specific(reason: str, minimum: int) -> bool:
    cleaned = reason.strip().lower().rstrip(".")
    return len(cleaned) >= minimum and len(cleaned.split()) >= 5 and cleaned not in GENERIC_REASONS


def migration_complete(text: str) -> bool:
    text = text.lower()
    return (
        "upgrade" in text
        and ("rollback" in text or "roll back" in text)
        and ("backup" in text or "back up" in text)
    )


def receipt_errors(name: str, receipt: dict) -> list[str]:
    """The --accept rules, rechecked on every run so a hand-edited lock cannot skip them."""
    errors = []
    if not isinstance(receipt.get("fingerprint"), str):
        errors.append(f"{name}: receipt has no fingerprint; record it with --accept {name}")
    breaking = receipt.get("breaking")
    if not isinstance(breaking, str) or not breaking.strip():
        errors.append(f"{name}: --breaking must be 'none' or the concrete compatibility consequence")
    docs = receipt.get("docs", [])
    if not isinstance(docs, list):
        return errors + [f"{name}: receipt 'docs' must be a list"]
    allowed = DOMAINS.get(name, {}).get("docs", ())
    errors += [f"{name} does not cover {doc}; allowed: {', '.join(allowed)}" for doc in docs if doc not in allowed]
    note = receipt.get("note") or ""
    no_impact = receipt.get("no_impact") or ""
    if receipt.get("baseline"):
        if docs or no_impact or is_breaking(receipt) or not specific(note, 20):
            errors.append(f"{name}: a baseline receipt carries only a baseline note")
        return errors
    if docs and no_impact:
        errors.append(f"{name}: pass either --docs with --note, or --no-impact")
    elif docs and not specific(note, 20):
        errors.append(f"{name}: --note must say what the docs now cover (20+ characters, five or more words)")
    elif not docs and not specific(no_impact, 40):
        errors.append(f"{name}: --no-impact needs a specific reason tied to this change (40+ characters, five or more words)")
    if is_breaking(receipt):
        if not docs:
            errors.append(f"{name}: a breaking change cannot use --no-impact")
        elif CHANGELOG not in docs:
            errors.append(f"{name}: a breaking change must update {CHANGELOG}")
        if not migration_complete(receipt.get("migration") or ""):
            errors.append(f"{name}: --migration must give backup, upgrade, and rollback instructions")
    return errors


def write_lock(repo: Path, data: dict) -> None:
    path = repo / LOCK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def check_mapping(files: list[str]) -> list[str]:
    failures = []
    for path in files:
        owners = owners_of(path)
        if len(owners) > 1:
            failures.append(f"{path}: matched by several domains ({', '.join(owners)}); fix DOMAINS")
        elif not owners and path.startswith(MAPPED_ROOTS):
            failures.append(f"{path}: not covered by any docs domain; add it to DOMAINS in scripts/check_docs_impact.py")
    return failures


def check_receipts(repo: Path, lock: dict | None, members: dict[str, list[str]]) -> list[str]:
    if lock is None:
        return [MISSING_LOCK]
    failures = []
    recorded = set(lock["domains"])
    if recorded != set(DOMAINS):
        failures.append(
            f"{LOCK_PATH} domains {sorted(recorded)} differ from DOMAINS {sorted(DOMAINS)}; migrate the lock explicitly"
        )
    for name, paths in members.items():
        receipt = lock["domains"].get(name)
        if receipt is None:
            continue
        failures += receipt_errors(name, receipt)
        if receipt.get("fingerprint") != fingerprint(repo, paths):
            failures.append(
                f"{name}: sources changed since the last review; update its docs and run --accept {name} "
                "(see docs/MAINTENANCE.md)"
            )
    return failures


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


def check_links(repo: Path, files: list[str]) -> list[str]:
    tracked = set(files)
    docs = [p for p in files if p.endswith(".md")]
    cache: dict[str, set[str]] = {}
    failures = []
    for doc in docs:
        text = (repo / doc).read_text(encoding="utf-8")
        for number, line, in_fence, _ in markdown_lines(text):
            if in_fence:
                continue
            for target in LINK_RE.findall(INLINE_CODE_RE.sub("", line)):
                if URL_SCHEME_RE.match(target):
                    continue
                path_part, _, anchor = target.partition("#")
                resolved = doc if not path_part else posixpath.normpath(posixpath.join(posixpath.dirname(doc), path_part))
                is_dir = any(p.startswith(resolved.rstrip("/") + "/") for p in tracked)
                if resolved not in tracked and not is_dir:
                    failures.append(f"{doc}:{number}: link target '{target}' is not a tracked file")
                    continue
                if anchor and resolved.endswith(".md"):
                    if resolved not in cache:
                        cache[resolved] = anchors_for((repo / resolved).read_text(encoding="utf-8"))
                    if anchor not in cache[resolved]:
                        failures.append(f"{doc}:{number}: anchor '#{anchor}' not found in {resolved}")
    return failures


def command_snippets(text: str) -> Iterator[tuple[int, str]]:
    pending: tuple[int, str] | None = None
    for number, line, in_fence, lang in markdown_lines(text):
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
    # Changelog entries are history: they may name scripts and flags that were later removed.
    for doc in (p for p in files if p.endswith(".md") and p != CHANGELOG and not p.startswith("prompts/")):
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


def changed_since(repo: Path, base: str) -> set[str]:
    # Diffing a commit against the work tree includes staged and unstaged changes.
    return {p for p in git(repo, "diff", "--name-only", "-z", base).split("\0") if p}


def check_range(repo: Path, base_rev: str, lock: dict | None) -> list[str]:
    if lock is None:
        return []
    merge_base = git(repo, "merge-base", base_rev, "HEAD").strip()
    if not merge_base:
        raise ToolError(f"no merge base between {base_rev} and HEAD; fetch full history (fetch-depth: 0)")
    changed = changed_since(repo, merge_base)
    base_text = git(repo, "show", f"{merge_base}:{LOCK_PATH}", check=False)
    base_lock = load_lock_text(base_text, f"{merge_base[:12]}:{LOCK_PATH}") if base_text else None
    failures = []
    base_domains = base_lock["domains"] if base_lock else {}
    for name, receipt in lock["domains"].items():
        previous = base_domains.get(name)
        if receipt == previous:
            continue
        if receipt.get("baseline") and base_lock is not None:
            failures.append(f"{name}: baseline receipts cannot replace an existing lock; use --accept")
        for doc in receipt.get("docs", []):
            if doc not in changed:
                failures.append(f"{name}: receipt cites {doc}, but {doc} did not change since {base_rev}")

    # A later receipt must not drop a breaking assessment recorded earlier in the range.
    commits = git(repo, "rev-list", f"{merge_base}..HEAD", "--", LOCK_PATH).split()
    snapshots = [(c[:12], git(repo, "show", f"{c}:{LOCK_PATH}", check=False)) for c in commits]
    for commit, text in snapshots:
        if not text:
            continue
        for name, receipt in load_lock_text(text, f"{commit}:{LOCK_PATH}")["domains"].items():
            # A breaking receipt carried over unchanged from the base was reviewed in an earlier range.
            if receipt == base_domains.get(name):
                continue
            if is_breaking(receipt) and not is_breaking(lock["domains"].get(name, {})):
                failures.append(
                    f"{name}: commit {commit} recorded a breaking change, but the final receipt says none; "
                    "re-accept with the combined breaking and migration assessment for this range"
                )

    base_registry = git(repo, "show", f"{merge_base}:scripts/render_prompts.py", check=False)
    head_registry = repo / "scripts/render_prompts.py"
    if base_registry and head_registry.is_file():
        removed = set(HARNESS_NAME_RE.findall(base_registry)) - set(
            HARNESS_NAME_RE.findall(head_registry.read_text(encoding="utf-8"))
        )
        receipt = lock["domains"].get("harnesses", {})
        if removed and (not is_breaking(receipt) or "docs/legacy-harnesses.md" not in receipt.get("docs", [])):
            failures.append(
                f"harnesses: removed {', '.join(sorted(removed))}; accept with --breaking, --migration, "
                "and docs/legacy-harnesses.md"
            )
    return failures


def check_release(repo: Path, tag: str) -> list[str]:
    version = tag.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        return [f"release tag '{tag}' is not vX.Y.Z"]
    changelog = (repo / CHANGELOG).read_text(encoding="utf-8")
    if not re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.MULTILINE):
        return [f"{CHANGELOG} has no dated '## [{version}] - YYYY-MM-DD' section for {tag}"]
    return []


def accept(repo: Path, args: argparse.Namespace, members: dict[str, list[str]]) -> None:
    lock = require_lock(repo)
    name = args.accept
    if name not in DOMAINS:
        raise ToolError(f"unknown domain '{name}'; known: {', '.join(DOMAINS)}")
    breaking = (args.breaking or "").strip()
    if not breaking:
        raise ToolError("--breaking is required: 'none' or the concrete compatibility consequence")
    docs = sorted({d.strip() for d in (args.docs or "").split(",") if d.strip()})
    if bool(docs) == bool(args.no_impact):
        raise ToolError("pass either --docs with --note, or --no-impact")
    for doc in docs:
        if not (repo / doc).is_file():
            raise ToolError(f"{doc} does not exist")
    receipt: dict = {
        "fingerprint": fingerprint(repo, members[name]),
        "breaking": "none" if breaking.lower() == "none" else breaking,
        "docs": docs,
    }
    if docs:
        receipt["note"] = (args.note or "").strip()
    else:
        receipt["no_impact"] = args.no_impact.strip()
    if receipt["breaking"] != "none":
        receipt["migration"] = (args.migration or "").strip()
    errors = receipt_errors(name, receipt)
    if errors:
        raise ToolError(errors[0])
    lock["domains"][name] = receipt
    write_lock(repo, lock)
    print(f"Accepted {name}")


def init(repo: Path, note: str | None, members: dict[str, list[str]]) -> None:
    if (repo / LOCK_PATH).exists():
        raise ToolError(f"{LOCK_PATH} already exists; use --accept for routine changes")
    if not note or not specific(note, 20):
        raise ToolError("--init needs a --note describing the baseline")
    domains = {
        name: {"baseline": True, "breaking": "none", "docs": [], "fingerprint": fingerprint(repo, paths), "note": note}
        for name, paths in members.items()
    }
    write_lock(repo, {"schema": SCHEMA, "domains": domains})
    print(f"Created {LOCK_PATH} baseline for {len(domains)} domains")


def explain(lock: dict | None, members: dict[str, list[str]]) -> None:
    for name, spec in DOMAINS.items():
        receipt = (lock or {}).get("domains", {}).get(name, {})
        print(f"{name}:")
        print(f"  docs: {', '.join(spec['docs'])}")
        print(f"  files ({len(members[name])}): {', '.join(members[name]) or '-'}")
        summary = receipt.get("note") or receipt.get("no_impact") or "no receipt"
        print(f"  receipt: {summary} [breaking: {receipt.get('breaking', '-')}]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", help="git revision to diff against (PR base or previous release tag)")
    parser.add_argument("--release-tag", help="also require a dated CHANGELOG section for this tag")
    parser.add_argument("--explain", action="store_true", help="print domains, member files, and receipts")
    parser.add_argument("--init", action="store_true", help="create the lock baseline when it is missing")
    parser.add_argument("--accept", metavar="DOMAIN", help="record a review receipt for DOMAIN")
    parser.add_argument("--docs", help="comma-separated docs updated for the domain")
    parser.add_argument("--note", help="what the updated docs now cover")
    parser.add_argument("--no-impact", help="specific reason the change needs no docs update")
    parser.add_argument("--breaking", help="'none' or the concrete compatibility consequence")
    parser.add_argument("--migration", help="backup, upgrade, and rollback instructions for a breaking change")
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()

    try:
        if shutil.which("git") is None:
            raise ToolError("git is required")
        if git(repo, "rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
            raise ToolError(f"{repo} is not a git work tree")
        files = tracked_files(repo)
        members = domain_files(files)
        if args.init:
            init(repo, args.note, members)
            return 0
        if args.accept:
            accept(repo, args, members)
            return 0
        lock = read_lock(repo)
        if args.explain:
            explain(lock, members)
            return 0
        failures = check_mapping(files) + check_receipts(repo, lock, members)
        failures += check_links(repo, files) + check_commands(repo, files)
        if args.base:
            failures += check_range(repo, args.base, lock)
        if args.release_tag:
            failures += check_release(repo, args.release_tag)
    except ToolError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print("Docs impact check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
