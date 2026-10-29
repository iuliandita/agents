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
import contextlib
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

from render_agents import AGENT_HARNESSES
from render_hermes import hermes_config_path
from render_prompts import (
    DEPLOYABLE,
    EXIT_CODES_HELP,
    PRIVATE_HARNESSES_ENV,
    PRIVATE_HARNESSES_FILE,
    JsonArgumentParser,
    harness_by_name,
    harness_names,
    json_extra,
    json_record,
    load_overlays,
    run_json,
    target_path,
)

TARGETS_ENV = "AGENTS_DEPLOY_TARGETS"
TARGETS_FILE = ("prompts", "deploy-targets.txt")

GIT_TIMEOUT_SECONDS = 300
# Binaries that show a harness is installed; config homes come from the deploy resolvers.
BINARIES = {
    "claude": ("claude",),
    "codex": ("codex",),
    "opencode": ("opencode",),
    "commandcode": ("commandcode", "command-code", "cmdc"),
    "antigravity": ("agy",),
    "omp": ("omp",),
    "hermes": ("hermes",),
}


def config_home(name: str, home: Path | None, env: dict[str, str]) -> Path | None:
    if name == "hermes":
        explicit = env.get("HERMES_CONFIG_PATH") or env.get("HERMES_HOME")
        if home is not None and not explicit:
            return Path(home) / ".hermes"
        return hermes_config_path(env).parent
    target = target_path(name, home=home, env=env)
    return None if target is None else target.parent


def detect(home: Path | None = None, env: dict[str, str] | None = None) -> dict[str, str]:
    """Supported harnesses with a binary on PATH or a config home where this repo would deploy."""
    values = dict(os.environ) if env is None else env
    found: dict[str, str] = {}
    for name, binaries in BINARIES.items():
        binary = next((b for b in binaries if shutil.which(b)), None)
        config_dir = config_home(name, home, values)
        if binary:
            found[name] = f"binary {binary}"
        elif config_dir is not None and config_dir.is_dir():
            found[name] = f"config {config_dir}"
    return found


def parse_names(raw: str) -> list[str]:
    return [part.strip() for part in raw.replace(",", "\n").split() if part.strip()]


def load_targets(repo_root: Path, cli: str | None, env: dict[str, str] | None = None) -> list[str]:
    values = os.environ if env is None else env
    path = repo_root.joinpath(*TARGETS_FILE)
    if cli is not None:
        names, source = parse_names(cli), "--targets"
    elif values.get(TARGETS_ENV, "").strip():
        names, source = parse_names(values[TARGETS_ENV]), TARGETS_ENV
    elif path.exists():
        lines = [line.split("#", 1)[0] for line in path.read_text(encoding="utf-8").splitlines()]
        names, source = parse_names("\n".join(lines)), str(path)
    else:
        raise SystemExit(
            f"error: no deploy targets. Write them to {path} (one per line), set {TARGETS_ENV}, or pass --harness (alias --targets). "
            "Run with --detect to see which supported harnesses are installed."
        )
    if not names:
        raise SystemExit(f"error: {source} lists no harnesses")
    supported = [name for name in harness_names() if name not in {"generic", "paperclip"}]
    unknown = [name for name in names if name not in supported]
    if unknown:
        raise SystemExit(f"error: {source}: unknown or project-level harness {', '.join(unknown)}; supported: {', '.join(supported)}")
    return list(dict.fromkeys(names))


def plan(repo_root: Path, targets: list[str], dry_run: bool) -> list[list[str]]:
    """Commands to run in order; each is a repo script invoked with the current interpreter."""
    scripts = repo_root / "scripts"
    global_targets = [name for name in targets if harness_by_name(name).support_level == DEPLOYABLE]
    agent_targets = [name for name in targets if name in AGENT_HARNESSES]
    deploy_flag = "--dry-run" if dry_run else "--deploy"
    steps = [[str(scripts / "render_prompts.py"), "--target", ",".join(targets), "--check"]]
    if agent_targets:
        steps.append([str(scripts / "render_agents.py"), "--target", ",".join(agent_targets), "--check"])
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


def git(repo_root: Path, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    # Unattended runs must fail instead of waiting on a password prompt or a stalled remote.
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=capture,
            text=True,
            check=True,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        print("error: git is not on PATH; install it or run with --no-pull", file=sys.stderr)
        raise SystemExit(3)
    except subprocess.TimeoutExpired:
        raise SystemExit(f"error: git {' '.join(args)} timed out after {GIT_TIMEOUT_SECONDS}s")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"error: git {' '.join(args)} failed with exit {exc.returncode}")


def pull(repo_root: Path) -> None:
    dirty = git(repo_root, "status", "--porcelain", "--untracked-files=no", capture=True).stdout.strip()
    if dirty:
        raise SystemExit(f"error: local tracked changes in {repo_root}; not updating:\n{dirty}")
    git(repo_root, "pull", "--ff-only")


@contextlib.contextmanager
def run_lock(repo_root: Path) -> Iterator[None]:
    """Refuse to start while another update runs from the same checkout."""
    handle = open(repo_root / ".update.lock", "a+")
    try:
        try:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise SystemExit(f"error: another update is running in {repo_root}")
        yield
    finally:
        handle.close()


def overlay_summary(repo_root: Path, targets: list[str]) -> list[str]:
    overlays = load_overlays(repo_root)
    lines = [f"local overlay: {'prompts/local.md' if overlays.local.strip() else 'none'}"]
    if not overlays.private.strip():
        lines.append("private overlay: none")
        return lines
    source = PRIVATE_HARNESSES_ENV if os.environ.get(PRIVATE_HARNESSES_ENV, "").strip() else f"prompts/{PRIVATE_HARNESSES_FILE}"
    sent = [name for name in targets if name in overlays.trusted]
    lines.append(f"private overlay: sent to {', '.join(sent) or 'no target'} (trust list from {source})")
    return lines


HELP_EPILOG = """\
Environment:
  AGENTS_PYTHON            Python 3.11+ executable the launcher runs (a path, not a command).
  AGENTS_DEPLOY_TARGETS    Harnesses to manage, comma-separated; --harness overrides it, and it overrides
                           prompts/deploy-targets.txt.
  AGENTS_PRIVATE_HARNESSES Comma-separated harnesses that receive prompts/private.md; 'all' for every one.
  GIT_SSH_COMMAND          Used for the pull; defaults to 'ssh -o BatchMode=yes' so it never prompts.
  The render steps also read their path and home overrides, so set them in a scheduled job:
  <HARNESS>_AGENTS_PATH, <HARNESS>_AGENTS_DIR, CLAUDE_CONFIG_DIR, CODEX_HOME, OPENCODE_CONFIG_DIR,
  PI_CODING_AGENT_DIR, OMP_PROFILE, PI_PROFILE, HERMES_HOME, HERMES_CONFIG_PATH, CLAUDE_HOOKS_DIR,
  CLAUDE_SETTINGS_PATH, HOME.

""" + EXIT_CODES_HELP + "  A failing step's exit code is passed through; git missing exits 3.\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = JsonArgumentParser(
        description="Pull, check, and redeploy prompts and subagents for saved targets.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument(
        "--targets",
        "--harness",
        dest="targets",
        action="append",
        metavar="HARNESS",
        help=f"Comma-separated harnesses, repeatable; overrides {TARGETS_ENV} and prompts/deploy-targets.txt (--harness is an alias).",
    )
    parser.add_argument("--detect", action="store_true", help="List supported harnesses installed on this machine and exit.")
    parser.add_argument("--no-pull", action="store_true", help="Skip git pull (use the checkout as is).")
    parser.add_argument("--dry-run", action="store_true", help="Pull and check, then preview deploys without writing.")
    parser.add_argument("--json", action="store_true", help="Print one JSON object to stdout; human output goes to stderr.")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    if args.detect:
        for name, evidence in detect().items():
            print(f"{name}\t{evidence}")
            json_record(harness=name, evidence=evidence)
        return 0
    targets = load_targets(args.repo_root, ",".join(args.targets) if args.targets is not None else None)
    json_extra(targets=targets)
    with run_lock(args.repo_root):
        if not args.no_pull:
            pull(args.repo_root)
        for line in overlay_summary(args.repo_root, targets):
            print(line)
        for step in plan(args.repo_root, targets, args.dry_run):
            label = " ".join([Path(step[1]).name, *step[2:-2]])
            print(f"==> {label}", flush=True)
            # With --json, child output goes to stderr so stdout holds only the JSON object.
            result = subprocess.run(step, stdout=2 if args.json else None)
            json_record(step=label, exit=result.returncode)
            if result.returncode != 0:
                print(f"error: update failed at {label}; fix it and rerun", file=sys.stderr)
                return result.returncode
    print(f"update complete for: {', '.join(targets)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.json:
        return run(args)
    if args.detect:
        return run_json(lambda: run(args), "update", "harnesses", mode="detect")
    return run_json(
        lambda: run(args), "update", "steps", mode="update", dry_run=args.dry_run, pull=not args.no_pull, targets=[]
    )


if __name__ == "__main__":
    raise SystemExit(main())
