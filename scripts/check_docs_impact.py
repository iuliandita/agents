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


def domain_of(path: str) -> list[str]:
    return [
        name for name, spec in DOMAINS.items() if any(fnmatch.fnmatchcase(path, pat) for pat in spec["sources"])
    ]


def domain_files(files: list[str]) -> dict[str, list[str]]:
    members: dict[str, list[str]] = {name: [] for name in DOMAINS}
    for path in files:
        for name in domain_of(path):
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
    return data


def read_lock(repo: Path) -> dict | None:
    path = repo / LOCK_PATH
    return load_lock_text(path.read_text(encoding="utf-8"), LOCK_PATH) if path.exists() else None


def write_lock(repo: Path, data: dict) -> None:
    path = repo / LOCK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def check_mapping(files: list[str]) -> list[str]:
    failures = []
    for path in files:
        owners = domain_of(path)
        if len(owners) > 1:
            failures.append(f"{path}: matched by several domains ({', '.join(owners)}); fix DOMAINS")
        elif not owners and path.startswith(MAPPED_ROOTS):
            failures.append(f"{path}: not covered by any docs domain; add it to DOMAINS in scripts/check_docs_impact.py")
    return failures


def check_receipts(repo: Path, lock: dict | None, members: dict[str, list[str]]) -> list[str]:
    if lock is None:
        return [f"{LOCK_PATH} is missing; create it once with --init --note"]
    failures = []
    recorded = set(lock["domains"])
    if recorded != set(DOMAINS):
        failures.append(
            f"{LOCK_PATH} domains {sorted(recorded)} differ from DOMAINS {sorted(DOMAINS)}; migrate the lock explicitly"
        )
    for name, paths in members.items():
        receipt = lock["domains"].get(name)
        if receipt and receipt.get("fingerprint") != fingerprint(repo, paths):
            failures.append(
                f"{name}: sources changed since the last review; update its docs and run --accept {name} "
                "(see docs/MAINTENANCE.md)"
            )
    return failures


def github_slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", text)
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


def markdown_lines(text: str):
    """Yield (line, in_fence, fence_lang) for each line."""
    fence: str | None = None
    lang = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if fence is None:
                fence, lang = marker, stripped[3:].strip().lower()
                continue
            if marker == fence:
                fence, lang = None, ""
                continue
        yield line, fence is not None, lang


def anchors_for(text: str) -> set[str]:
    seen: dict[str, int] = {}
    anchors: set[str] = set()
    for line, in_fence, _ in markdown_lines(text):
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
        for number, (line, in_fence, _) in enumerate(markdown_lines(text), start=1):
            if in_fence:
                continue
            for target in LINK_RE.findall(INLINE_CODE_RE.sub("", line)):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target):
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


def command_snippets(text: str):
    for number, (line, in_fence, lang) in enumerate(markdown_lines(text), start=1):
        if in_fence and lang in ("", "bash", "sh", "shell", "zsh", "powershell", "pwsh"):
            yield number, line.strip()
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
            except ValueError:
                continue
            script = None
            for token in tokens:
                if token in ("|", "&&", "||", ";"):
                    script = None
                    continue
                candidate = token.removeprefix("./")
                if re.fullmatch(r"scripts/[A-Za-z0-9_.-]+", candidate):
                    if candidate not in tracked:
                        failures.append(f"{doc}:{number}: command references missing script '{candidate}'")
                        script = None
                    else:
                        script = candidate
                    continue
                if script and token.startswith("--") and len(token) > 2:
                    flag = token.split("=", 1)[0]
                    if flag not in script_flag_sources(repo, script):
                        failures.append(f"{doc}:{number}: '{script}' does not define flag '{flag}'")
    return failures


def harness_names(text: str) -> set[str]:
    return set(HARNESS_NAME_RE.findall(text))


def changed_since(repo: Path, base: str) -> set[str]:
    changed = git(repo, "diff", "--name-only", base).split()
    changed += git(repo, "diff", "--cached", "--name-only", base).split()
    return set(changed)


def check_range(repo: Path, base_rev: str, lock: dict | None) -> list[str]:
    merge_base = git(repo, "merge-base", base_rev, "HEAD").strip()
    if not merge_base:
        raise ToolError(f"no merge base between {base_rev} and HEAD; fetch full history (fetch-depth: 0)")
    changed = changed_since(repo, merge_base)
    base_text = git(repo, "show", f"{merge_base}:{LOCK_PATH}", check=False)
    base_lock = load_lock_text(base_text, f"{merge_base[:12]}:{LOCK_PATH}") if base_text else None
    if lock is None:
        return []
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
            final = lock["domains"].get(name, {})
            if receipt.get("breaking", "none") != "none" and final.get("breaking", "none") == "none":
                failures.append(
                    f"{name}: commit {commit} recorded a breaking change, but the final receipt says none; "
                    "re-accept with the combined breaking and migration assessment for this range"
                )

    base_registry = git(repo, "show", f"{merge_base}:scripts/render_prompts.py", check=False)
    head_registry = repo / "scripts/render_prompts.py"
    if base_registry and head_registry.is_file():
        removed = harness_names(base_registry) - harness_names(head_registry.read_text(encoding="utf-8"))
        receipt = lock["domains"].get("harnesses", {})
        if removed and (
            receipt.get("breaking", "none") == "none" or "docs/legacy-harnesses.md" not in receipt.get("docs", [])
        ):
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


def specific(reason: str, minimum: int) -> bool:
    cleaned = reason.strip().lower().rstrip(".")
    return len(cleaned) >= minimum and len(cleaned.split()) >= 5 and cleaned not in GENERIC_REASONS


def accept(repo: Path, args: argparse.Namespace, members: dict[str, list[str]]) -> None:
    lock = read_lock(repo)
    if lock is None:
        raise ToolError(f"{LOCK_PATH} is missing; create it once with --init --note")
    name = args.accept
    if name not in DOMAINS:
        raise ToolError(f"unknown domain '{name}'; known: {', '.join(DOMAINS)}")
    if args.breaking is None:
        raise ToolError("--breaking is required: 'none' or the concrete compatibility consequence")
    docs = [d.strip() for d in (args.docs or "").split(",") if d.strip()]
    if bool(docs) == bool(args.no_impact):
        raise ToolError("pass either --docs with --note, or --no-impact")
    receipt: dict = {"fingerprint": fingerprint(repo, members[name]), "breaking": args.breaking.strip()}
    if docs:
        allowed = DOMAINS[name]["docs"]
        for doc in docs:
            if doc not in allowed:
                raise ToolError(f"{name} does not cover {doc}; allowed: {', '.join(allowed)}")
            if not (repo / doc).is_file():
                raise ToolError(f"{doc} does not exist")
        if not args.note or not specific(args.note, 20):
            raise ToolError("--note must say what the docs now cover (at least five words)")
        receipt.update(docs=sorted(docs), note=args.note.strip())
    else:
        if not specific(args.no_impact, 40):
            raise ToolError("--no-impact needs a specific reason tied to this change (40+ characters)")
        receipt.update(docs=[], no_impact=args.no_impact.strip())
    if receipt["breaking"] != "none":
        if not docs:
            raise ToolError("a breaking change cannot use --no-impact")
        if CHANGELOG not in docs:
            raise ToolError(f"a breaking change must update {CHANGELOG}")
        migration = (args.migration or "").lower()
        if not (
            "upgrade" in migration and ("rollback" in migration or "roll back" in migration)
            and ("backup" in migration or "back up" in migration)
        ):
            raise ToolError("--migration must give backup, upgrade, and rollback instructions")
        receipt["migration"] = args.migration.strip()
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
