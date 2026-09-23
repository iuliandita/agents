#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import NamedTuple


DEPLOYABLE = "deployable"
MANUAL = "manual"
SUPPORT_LEVELS = {DEPLOYABLE, MANUAL}


class Harness(NamedTuple):
    name: str
    display: str
    fragment: str
    output_name: str
    target_template: str | None
    env_var: str
    support_level: str = DEPLOYABLE
    notes: str = ""
    source_url: str = ""
    verified_on: str = ""
    confidence: str = "high"
    optional_blocks: tuple[str, ...] = ("subagents",)
    max_bytes: int | None = None
    native_env_var: str = ""
    native_filename: str = ""


# Seven supported harnesses plus one generic project-level target. Paths, overrides,
# and verification receipts live in docs/harness-contract.md. Only add a harness
# here once its rules path is confirmed against upstream docs.
HARNESSES: tuple[Harness, ...] = (
    Harness(
        "claude",
        "Claude Code",
        "claude.md",
        "CLAUDE.md",
        "{home}/.claude/CLAUDE.md",
        "CLAUDE_AGENTS_PATH",
        notes="",
        source_url="https://code.claude.com/docs/en/memory",
        verified_on="2026-09-17",
        native_env_var="CLAUDE_CONFIG_DIR",
        native_filename="CLAUDE.md",
    ),
    Harness(
        "codex",
        "OpenAI Codex",
        "codex.md",
        "AGENTS.md",
        "{home}/.codex/AGENTS.md",
        "CODEX_AGENTS_PATH",
        notes="Global path follows $CODEX_HOME (default ~/.codex); set CODEX_AGENTS_PATH when CODEX_HOME is customized.",
        source_url="https://developers.openai.com/codex/agent-configuration/agents-md",
        verified_on="2026-09-17",
        max_bytes=32768,
        native_env_var="CODEX_HOME",
        native_filename="AGENTS.md",
    ),
    Harness(
        "opencode",
        "OpenCode",
        "opencode.md",
        "AGENTS.md",
        "{home}/.config/opencode/AGENTS.md",
        "OPENCODE_AGENTS_PATH",
        notes="Same home-relative path on macOS; on Windows run under WSL or use %USERPROFILE%\\.config\\opencode.",
        source_url="https://opencode.ai/docs/rules/",
        verified_on="2026-09-17",
        native_env_var="OPENCODE_CONFIG_DIR",
        native_filename="AGENTS.md",
    ),
    Harness(
        "commandcode",
        "Command Code",
        "commandcode.md",
        "AGENTS.md",
        "{home}/.commandcode/AGENTS.md",
        "COMMANDCODE_AGENTS_PATH",
        notes="",
        source_url="https://commandcode.ai/docs/memory",
        verified_on="2026-09-17",
        confidence="medium",
    ),
    Harness(
        "antigravity",
        "Antigravity",
        "antigravity.md",
        "GEMINI.md",
        "{home}/.gemini/GEMINI.md",
        "ANTIGRAVITY_AGENTS_PATH",
        notes="Desktop, IDE, and CLI share ~/.gemini/GEMINI.md; workspace rules live in .agents/rules/ (12k char cap per file).",
        source_url="https://antigravity.google/docs/rules-workflows/",
        verified_on="2026-09-17",
    ),
    Harness(
        "omp",
        "Oh My Pi",
        "omp.md",
        "AGENTS.md",
        "{home}/.omp/agent/AGENTS.md",
        "OMP_AGENTS_PATH",
        notes="Global path follows PI_CODING_AGENT_DIR (default ~/.omp/agent); named profiles use ~/.omp/profiles/<name>/agent.",
        source_url="https://omp.sh",
        verified_on="2026-09-24",
        native_env_var="PI_CODING_AGENT_DIR",
        native_filename="AGENTS.md",
    ),
    Harness(
        "hermes",
        "Hermes Agent",
        "hermes.md",
        "HERMES.md",
        None,
        "HERMES_AGENTS_PATH",
        MANUAL,
        "Global rules merge into agent.coding_instructions in $HERMES_HOME/config.yaml; project rules deploy to HERMES.md or AGENTS.override.md via HERMES_AGENTS_PATH.",
        source_url="https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files",
        verified_on="2026-09-17",
    ),
    Harness(
        "generic",
        "Generic AGENTS.md",
        "AGENTS.md",
        "AGENTS.md",
        None,
        "GENERIC_AGENTS_PATH",
        MANUAL,
        "Project-level AGENTS.md for tools with no verified global rules path; deploy with GENERIC_AGENTS_PATH pointing at a project file.",
        source_url="",
        verified_on="2026-09-17",
        confidence="n/a",
        optional_blocks=(),
    ),
)


def harness_by_name(name: str) -> Harness:
    for harness in HARNESSES:
        if harness.name == name:
            return harness
    supported = ", ".join(harness_names())
    raise SystemExit(f"Unknown harness: {name}. Supported: {supported}")


def harness_names() -> list[str]:
    return [harness.name for harness in HARNESSES]


def harness_display_names() -> list[str]:
    return [harness.display for harness in HARNESSES]


def default_target_label(harness: Harness, home: str = "~") -> str:
    if harness.target_template is None:
        return f"manual override via {harness.env_var}"
    return harness.target_template.format(home=home)


def harness_target_rows(home: str = "~") -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for harness in HARNESSES:
        rows.append((harness.display, harness.support_level, default_target_label(harness, home), harness.notes))
    return rows


def selected_harnesses(selected: list[str] | None) -> list[Harness]:
    if not selected:
        return list(HARNESSES)

    names: list[str] = []
    for item in selected:
        names.extend(part.strip() for part in item.split(",") if part.strip())
    if not names:
        raise SystemExit("No harness names parsed from --target; nothing to do")
    return [harness_by_name(name) for name in names]


OMP_PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
WINDOWS_RESERVED_RE = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?$", re.IGNORECASE)


def omp_profile(env: dict[str, str] | os._Environ[str]) -> str | None:
    """Active omp profile, resolved as omp does: OMP_PROFILE wins even when empty."""
    raw = env["OMP_PROFILE"] if "OMP_PROFILE" in env else env.get("PI_PROFILE")
    name = (raw or "").strip()
    if not name or name == "default":
        return None
    if name.endswith(".") or not OMP_PROFILE_RE.match(name) or WINDOWS_RESERVED_RE.match(name):
        raise SystemExit(f"Invalid omp profile {name!r}; names must match {OMP_PROFILE_RE.pattern}")
    return name


def omp_profile_agent_dir(home: str | Path | None, env: dict[str, str] | os._Environ[str]) -> Path | None:
    """A named profile moves omp's agent dir, taking precedence over PI_CODING_AGENT_DIR."""
    profile = omp_profile(env)
    if profile is None:
        return None
    home_path = Path.home() if home is None else Path(home)
    return home_path / ".omp" / "profiles" / profile / "agent"


def omp_is_profile_derived(home: str | Path | None, env: dict[str, str] | os._Environ[str], agent_dir: str) -> bool:
    """omp ignores a PI_CODING_AGENT_DIR that a parent's profile switch propagated (PI_PROFILE's agent dir)."""
    try:
        legacy = omp_profile({"PI_PROFILE": env.get("PI_PROFILE", "")})
    except SystemExit:
        return False
    if legacy is None:
        return False
    home_path = Path.home() if home is None else Path(home)
    return Path(agent_dir).expanduser() == home_path / ".omp" / "profiles" / legacy / "agent"


def target_path(harness: str, home: str | Path | None = None, env: dict[str, str] | None = None) -> Path | None:
    item = harness_by_name(harness)
    values = os.environ if env is None else env
    if item.env_var in values and values[item.env_var]:
        return Path(values[item.env_var]).expanduser()

    native_dir = values.get(item.native_env_var) if item.native_env_var else None
    if harness == "omp":
        profile_dir = omp_profile_agent_dir(home, values)
        if profile_dir is not None:
            return profile_dir / item.native_filename
        if native_dir and omp_is_profile_derived(home, values, native_dir):
            native_dir = None

    if native_dir:
        return Path(native_dir).expanduser() / item.native_filename

    if item.target_template is None:
        return None

    home_path = Path.home() if home is None else Path(home)
    return Path(item.target_template.format(home=home_path)).expanduser()


OPTIONAL_BLOCK_RE = re.compile(
    r"[ \t]*<!--\s*optional:([a-z0-9_-]+)\s*-->\n(.*?)\n[ \t]*<!--\s*/optional:\1\s*-->\n?",
    re.DOTALL,
)


def apply_optional_blocks(text: str, enabled: frozenset[str]) -> str:
    """Keep enabled optional blocks, drop the rest, and collapse left gaps."""

    def replace(match: re.Match[str]) -> str:
        return match.group(2) + "\n" if match.group(1) in enabled else ""

    result = OPTIONAL_BLOCK_RE.sub(replace, text)
    return re.sub(r"\n{3,}", "\n\n", result)


def render_document(
    fragment: str,
    core: str,
    private: str = "",
    stamp: str | None = None,
    enabled_optional: frozenset[str] = frozenset({"subagents"}),
) -> str:
    core = apply_optional_blocks(core, enabled_optional)
    if stamp is not None:
        provenance = f"on {stamp}"
    else:
        digest = hashlib.sha256((fragment + "\n" + core + "\n" + private).encode("utf-8")).hexdigest()[:12]
        provenance = f"rev {digest}"
    rendered = (
        f"<!-- Generated by sync-ai-prompts {provenance}. "
        "Edit prompts/core.md and prompts/harnesses/*.md, plus optional prompts/private.md "
        "(see prompts/private.example.md), not rendered files. -->\n\n"
        f"{fragment.rstrip()}\n\n"
        f"{core.rstrip()}\n"
    )
    if private.strip():
        rendered += f"\n{private.rstrip()}\n"
    return rendered


def read_fragment(repo_root: Path, harness: Harness) -> str:
    path = repo_root / "prompts" / "harnesses" / harness.fragment
    if not path.exists():
        raise SystemExit(f"Missing fragment for {harness.name}: {path}")
    return path.read_text(encoding="utf-8")


def read_private(repo_root: Path) -> str:
    path = repo_root / "prompts" / "private.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


PRIVATE_HARNESSES_ENV = "AGENTS_PRIVATE_HARNESSES"
# Private overlays can hold home-lab hosts, identities, and local paths. Only
# first-party harnesses receive them by default; opt other harnesses in with
# AGENTS_PRIVATE_HARNESSES or prompts/private-harnesses.txt.
DEFAULT_PRIVATE_HARNESSES = ("claude", "codex")


def private_harnesses(repo_root: Path, env: dict[str, str] | None = None) -> frozenset[str]:
    values = os.environ if env is None else env
    override = values.get(PRIVATE_HARNESSES_ENV, "")
    if override.strip():
        return frozenset(part.strip() for part in override.replace(",", "\n").split() if part.strip())

    path = repo_root / "prompts" / "private-harnesses.txt"
    if path.exists():
        names = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        return frozenset(names)

    return frozenset(DEFAULT_PRIVATE_HARNESSES)


def output_path(out_dir: Path, harness: Harness, collisions: set[str]) -> Path:
    if harness.output_name in collisions:
        return out_dir / harness.name / harness.output_name
    return out_dir / harness.output_name


def enforce_budget(harness: Harness, rendered: str) -> None:
    if harness.max_bytes is None:
        return
    size = len(rendered.encode("utf-8"))
    if size > harness.max_bytes:
        raise SystemExit(
            f"{harness.name}: rendered {size} bytes exceeds its {harness.max_bytes}-byte budget; "
            "trim the fragment or the private overlay"
        )


def render_all(
    repo_root: Path,
    out_dir: Path,
    selected: list[str] | None = None,
    stamp: str | None = None,
) -> dict[str, Path]:
    harnesses = selected_harnesses(selected)
    output_counts: dict[str, int] = {}
    for harness in harnesses:
        output_counts[harness.output_name] = output_counts.get(harness.output_name, 0) + 1
    collisions = {name for name, count in output_counts.items() if count > 1}

    core = (repo_root / "prompts" / "core.md").read_text(encoding="utf-8")
    private = read_private(repo_root)
    allowed_private = private_harnesses(repo_root)
    written: dict[str, Path] = {}
    for harness in harnesses:
        dest = output_path(out_dir, harness, collisions)
        dest.parent.mkdir(parents=True, exist_ok=True)
        rendered = render_document(
            read_fragment(repo_root, harness),
            core,
            private=private if harness.name in allowed_private else "",
            stamp=stamp,
            enabled_optional=frozenset(harness.optional_blocks),
        )
        enforce_budget(harness, rendered)
        dest.write_text(rendered, encoding="utf-8", newline="\n")
        written[harness.name] = dest
    return written


def check_render_shape(repo_root: Path, selected: list[str] | None = None) -> int:
    with TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir)
        written = render_all(repo_root, out_dir, selected=selected, stamp="check")
        paths = list(written.values())
        if len(paths) != len(set(paths)):
            print("ERROR: render output paths collide")
            return 1
        for harness, path in written.items():
            if not path.exists():
                print(f"ERROR: missing rendered output for {harness}: {path}")
                return 1
        print("Render shape check passed")
        return 0


def resolve_deploy_targets(harnesses: list[Harness]) -> tuple[dict[Harness, Path], list[Harness]]:
    resolved: dict[Harness, Path] = {}
    skipped: list[Harness] = []
    for harness in harnesses:
        dest = target_path(harness.name)
        if dest is None:
            skipped.append(harness)
            continue
        resolved[harness] = dest
    return resolved, skipped


def target_collisions(resolved: dict[Harness, Path]) -> dict[Path, list[Harness]]:
    by_key: dict[str, list[tuple[Path, Harness]]] = {}
    for harness, dest in resolved.items():
        resolved_path = dest.expanduser().resolve(strict=False)
        # normcase folds case so Windows/macOS default filesystems cannot collide unseen.
        by_key.setdefault(os.path.normcase(str(resolved_path)), []).append((resolved_path, harness))
    return {
        pairs[0][0]: [harness for _, harness in pairs]
        for pairs in by_key.values()
        if len(pairs) > 1
    }


def format_target_collision(collisions: dict[Path, list[Harness]]) -> str:
    lines = ["Deploy target collision detected:"]
    for dest, harnesses in sorted(collisions.items(), key=lambda item: str(item[0])):
        labels = ", ".join(f"{harness.name} ({harness.display})" for harness in harnesses)
        lines.append(f"- {dest}: {labels}")
    lines.append("Select one target with --target or override one path with its *_AGENTS_PATH env var.")
    return "\n".join(lines)


def backup_existing(path: Path, backup_dir: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Collapse separators, drive letters, and other unsafe characters so Windows
    # paths (C:\...) produce a valid flat backup name.
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", str(path)).strip("-")
    backup_stem = f"{path.stem}-{date.today().isoformat()}-{safe_name}"
    backup = backup_dir / f"{backup_stem}.bak"
    counter = 2
    while backup.exists() or backup.is_symlink():
        backup = backup_dir / f"{backup_stem}-{counter}.bak"
        counter += 1
    if path.is_symlink() and not path.exists():
        # Dangling symlink: copy the link itself; following it would crash.
        shutil.copy2(path, backup, follow_symlinks=False)
        return
    shutil.copy2(path, backup)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def manifest_path(repo_root: Path) -> Path:
    return repo_root / "build" / "deploy-manifest.json"


def load_manifest(repo_root: Path) -> dict:
    path = manifest_path(repo_root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_manifest(repo_root: Path, manifest: dict) -> None:
    path = manifest_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def deploy(
    repo_root: Path,
    selected: list[str] | None,
    stamp: str | None,
    dry_run: bool,
    backup_dir: Path,
) -> dict[str, Path]:
    harnesses = selected_harnesses(selected)
    core = (repo_root / "prompts" / "core.md").read_text(encoding="utf-8")
    private = read_private(repo_root)
    allowed_private = private_harnesses(repo_root)
    resolved, skipped = resolve_deploy_targets(harnesses)

    for harness in skipped:
        print(f"skipping {harness.name}: manual target requires {harness.env_var}")

    collisions = target_collisions(resolved)
    if collisions:
        raise SystemExit(format_target_collision(collisions))

    for harness, dest in resolved.items():
        if dest.is_symlink():
            raise SystemExit(
                f"{dest} is a symlink; refusing to write through it. "
                f"Move it aside or point {harness.env_var} at a regular file."
            )

    manifest = load_manifest(repo_root)
    deployed: dict[str, Path] = {}
    for harness, dest in resolved.items():
        rendered = render_document(
            read_fragment(repo_root, harness),
            core,
            private=private if harness.name in allowed_private else "",
            stamp=stamp,
            enabled_optional=frozenset(harness.optional_blocks),
        )
        enforce_budget(harness, rendered)
        deployed[harness.name] = dest
        if dry_run:
            print(f"would update {harness.name}: {dest}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.read_text(encoding="utf-8", errors="replace") == rendered:
            print(f"unchanged {harness.name}: {dest}")
        else:
            backup_existing(dest, backup_dir)
            dest.write_text(rendered, encoding="utf-8", newline="\n")
            print(f"updated {harness.name}: {dest}")
        manifest[harness.name] = {"path": str(dest), "hash": content_hash(rendered)}

    if not dry_run:
        write_manifest(repo_root, manifest)
    return deployed


def prune_backups(backup_dir: Path, keep: int, dry_run: bool) -> int:
    """Keep the newest `keep` backups, remove the rest. Dry-run reports only."""
    if keep < 0:
        raise SystemExit("--prune-backups requires a non-negative count")
    if not backup_dir.is_dir():
        print(f"no backups at {backup_dir}")
        return 0
    files = [
        path
        for path in backup_dir.iterdir()
        if (path.is_file() or path.is_symlink()) and path.name.endswith(".bak")
    ]
    files.sort(key=lambda path: path.lstat().st_mtime, reverse=True)
    stale = files[keep:]
    for path in stale:
        if dry_run:
            print(f"would remove {path}")
            continue
        path.unlink()
        print(f"removed {path}")
    verb = "would prune" if dry_run else "pruned"
    print(f"{verb} {len(stale)} of {len(files)} backups in {backup_dir}")
    return 0


def status(repo_root: Path, selected: list[str] | None, stamp: str | None) -> int:
    """Report whether each deployed file matches a fresh render, or was edited locally."""
    core = (repo_root / "prompts" / "core.md").read_text(encoding="utf-8")
    private = read_private(repo_root)
    allowed_private = private_harnesses(repo_root)
    manifest = load_manifest(repo_root)
    drift = 0
    for harness in selected_harnesses(selected):
        dest = target_path(harness.name)
        if dest is None:
            print(f"{harness.name}: manual target ({harness.env_var})")
            continue
        rendered = render_document(
            read_fragment(repo_root, harness),
            core,
            private=private if harness.name in allowed_private else "",
            stamp=stamp,
            enabled_optional=frozenset(harness.optional_blocks),
        )
        if not dest.exists():
            print(f"{harness.name}: not deployed ({dest})")
            drift += 1
            continue
        current = dest.read_text(encoding="utf-8", errors="replace")
        if current == rendered:
            print(f"{harness.name}: in sync ({dest})")
            continue
        recorded = manifest.get(harness.name, {}).get("hash")
        if recorded and content_hash(current) != recorded:
            print(f"{harness.name}: local edits since deploy ({dest})")
        else:
            print(f"{harness.name}: drift from current render ({dest})")
        drift += 1
    return 1 if drift else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Render and deploy canonical agent prompt files.")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--out-dir", type=Path, default=repo_root / "build" / "generated")
    parser.add_argument("--target", action="append", help="Harness target, repeatable or comma-separated.")
    parser.add_argument("--stamp", help="Override generated date, useful for tests.")
    parser.add_argument("--deploy", action="store_true", help="Write rendered files to global harness paths.")
    parser.add_argument("--dry-run", action="store_true", help="Print deploy targets without writing.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate render output shape without writing persistent output.",
    )
    parser.add_argument("--list-targets", action="store_true", help="List supported harnesses and output paths.")
    parser.add_argument("--status", action="store_true", help="Report deployed files that differ from a fresh render.")
    parser.add_argument(
        "--prune-backups",
        type=int,
        metavar="KEEP",
        help="Keep the newest KEEP backups under --backup-dir and remove the rest (combine with --dry-run to preview).",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=repo_root / ".backups",
        help="Directory for deploy backups.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list_targets:
        for harness in selected_harnesses(args.target):
            dest = target_path(harness.name)
            target = str(dest) if dest is not None else f"manual override via {harness.env_var}"
            print(f"{harness.name}\t{harness.display}\t{harness.support_level}\t{target}")
        return 0

    if args.check:
        return check_render_shape(args.repo_root, args.target)

    if args.status:
        return status(args.repo_root, args.target, args.stamp)

    if args.prune_backups is not None:
        return prune_backups(args.backup_dir, args.prune_backups, dry_run=args.dry_run)

    if args.deploy and not args.target:
        raise SystemExit(
            "--deploy requires --target (for example --target claude,opencode). "
            "Use --dry-run without --target to preview every harness."
        )

    if args.deploy or args.dry_run:
        deploy(args.repo_root, args.target, args.stamp, args.dry_run, args.backup_dir)
        return 0

    written = render_all(args.repo_root, args.out_dir, selected=args.target, stamp=args.stamp)
    for harness, path in written.items():
        print(f"rendered {harness}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
