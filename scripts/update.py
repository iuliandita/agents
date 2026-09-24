#!/usr/bin/env python3
"""Pull, check, and redeploy everything for a saved list of harnesses.

One command for first-time setup, manual refreshes, and a daily schedule. It pulls
fast-forward only, refuses to run over local tracked edits, renders and checks, then
deploys prompts, the Hermes merge, subagents, and the Claude invariants hook for the
listed harnesses, and finishes with a drift check. Any failing step stops the run with
a non-zero exit so a scheduler can report it.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from render_agents import AGENT_HARNESSES
from render_prompts import DEPLOYABLE, harness_by_name, harness_names

TARGETS_ENV = "AGENTS_DEPLOY_TARGETS"
TARGETS_FILE = ("prompts", "deploy-targets.txt")

# Evidence that a harness is installed: a binary on PATH or its config home.
DETECTION = {
    "claude": (("claude",), "~/.claude"),
    "codex": (("codex",), "~/.codex"),
    "opencode": (("opencode",), "~/.config/opencode"),
    "commandcode": (("commandcode", "command-code", "cmdc"), "~/.commandcode"),
    "antigravity": (("agy",), "~/.gemini"),
    "omp": (("omp",), "~/.omp"),
    "hermes": (("hermes",), "~/.hermes"),
}


def detect(home: Path | None = None) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, (binaries, config) in DETECTION.items():
        binary = next((b for b in binaries if shutil.which(b)), None)
        config_dir = Path(config.replace("~", str(home), 1)) if home else Path(config).expanduser()
        if binary:
            found[name] = f"binary {binary}"
        elif config_dir.is_dir():
            found[name] = f"config {config_dir}"
    return found


def parse_names(raw: str) -> list[str]:
    return [part.strip() for part in raw.replace(",", "\n").split() if part.strip()]


def load_targets(repo_root: Path, cli: str | None, env: dict[str, str] | None = None) -> list[str]:
    values = os.environ if env is None else env
    path = repo_root.joinpath(*TARGETS_FILE)
    if cli:
        names, source = parse_names(cli), "--targets"
    elif values.get(TARGETS_ENV, "").strip():
        names, source = parse_names(values[TARGETS_ENV]), TARGETS_ENV
    elif path.exists():
        lines = [line.split("#", 1)[0] for line in path.read_text(encoding="utf-8").splitlines()]
        names, source = parse_names("\n".join(lines)), str(path)
    else:
        raise SystemExit(
            f"No deploy targets. Write them to {path} (one per line), set {TARGETS_ENV}, or pass --targets. "
            "Run with --detect to see which supported harnesses are installed."
        )
    if not names:
        raise SystemExit(f"{source} lists no harnesses")
    supported = [name for name in harness_names() if name != "generic"]
    unknown = [name for name in names if name not in supported]
    if unknown:
        raise SystemExit(f"{source}: unknown or project-level harness {', '.join(unknown)}; supported: {', '.join(supported)}")
    return list(dict.fromkeys(names))


def plan(repo_root: Path, targets: list[str], dry_run: bool) -> list[list[str]]:
    """Commands to run in order; each is a repo script invoked with the current interpreter."""
    scripts = repo_root / "scripts"
    global_targets = [name for name in targets if harness_by_name(name).support_level == DEPLOYABLE]
    agent_targets = [name for name in targets if name in AGENT_HARNESSES]
    deploy_flag = "--dry-run" if dry_run else "--deploy"
    steps = [
        [str(scripts / "render_prompts.py"), "--check"],
        [str(scripts / "render_agents.py"), "--check"],
    ]
    if global_targets:
        steps.append([str(scripts / "render_prompts.py"), "--target", ",".join(global_targets), deploy_flag])
    if "hermes" in targets:
        steps.append([str(scripts / "render_hermes.py"), deploy_flag])
    if agent_targets:
        steps.append([str(scripts / "render_agents.py"), "--target", ",".join(agent_targets), deploy_flag])
    if "claude" in targets:
        steps.append([str(scripts / "render_invariants.py"), deploy_flag])
    if not dry_run:
        if agent_targets:
            steps.append([str(scripts / "render_agents.py"), "--target", ",".join(agent_targets), "--verify"])
        if global_targets:
            steps.append([str(scripts / "render_prompts.py"), "--target", ",".join(global_targets), "--status"])
    return [[sys.executable, *step, "--repo-root", str(repo_root)] for step in steps]


def tracked_changes(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def pull(repo_root: Path) -> None:
    dirty = tracked_changes(repo_root)
    if dirty:
        raise SystemExit(f"Local tracked changes in {repo_root}; not updating:\n{dirty}")
    subprocess.run(["git", "-C", str(repo_root), "pull", "--ff-only"], check=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Pull, check, and redeploy prompts and subagents for saved targets.")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--targets", help=f"Comma-separated harnesses; overrides {TARGETS_ENV} and prompts/deploy-targets.txt.")
    parser.add_argument("--detect", action="store_true", help="List supported harnesses installed on this machine and exit.")
    parser.add_argument("--no-pull", action="store_true", help="Skip git pull (use the checkout as is).")
    parser.add_argument("--dry-run", action="store_true", help="Pull and check, then preview deploys without writing.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.detect:
        for name, evidence in detect().items():
            print(f"{name}\t{evidence}")
        return 0
    targets = load_targets(args.repo_root, args.targets)
    if not args.no_pull:
        pull(args.repo_root)
    for step in plan(args.repo_root, targets, args.dry_run):
        label = " ".join([Path(step[1]).name, *step[2:-2]])
        print(f"==> {label}", flush=True)
        result = subprocess.run(step)
        if result.returncode != 0:
            print(f"update failed at: {label}", file=sys.stderr)
            return result.returncode
    print(f"update complete for: {', '.join(targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
