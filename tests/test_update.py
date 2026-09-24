import subprocess
import sys
from pathlib import Path

import pytest

import update


def write_targets(repo: Path, text: str) -> None:
    (repo / "prompts").mkdir(parents=True, exist_ok=True)
    (repo / "prompts" / "deploy-targets.txt").write_text(text, encoding="utf-8")


def test_targets_precedence_cli_then_env_then_file(tmp_path):
    write_targets(tmp_path, "# mine\nclaude\nomp  # comment\n")
    assert update.load_targets(tmp_path, None, env={}) == ["claude", "omp"]
    assert update.load_targets(tmp_path, None, env={"AGENTS_DEPLOY_TARGETS": "codex"}) == ["codex"]
    assert update.load_targets(tmp_path, "opencode,hermes", env={"AGENTS_DEPLOY_TARGETS": "codex"}) == [
        "opencode",
        "hermes",
    ]


def test_targets_missing_points_at_detect(tmp_path):
    with pytest.raises(SystemExit, match="--detect"):
        update.load_targets(tmp_path, None, env={})


@pytest.mark.parametrize("names", ["claud", "generic", "claude,generic"])
def test_targets_reject_unknown_and_project_level(tmp_path, names):
    with pytest.raises(SystemExit, match="unknown or project-level harness"):
        update.load_targets(tmp_path, names, env={})


def scripts_and_flags(steps):
    return [[Path(step[1]).name, *step[2:-2]] for step in steps]


def test_plan_orders_checks_deploys_and_verification(tmp_path):
    steps = update.plan(tmp_path, ["claude", "hermes", "omp"], dry_run=False)
    assert all(step[0] == sys.executable and step[-2:] == ["--repo-root", str(tmp_path)] for step in steps)
    assert scripts_and_flags(steps) == [
        ["render_prompts.py", "--check"],
        ["render_agents.py", "--check"],
        ["render_prompts.py", "--target", "claude,omp", "--deploy"],
        ["render_hermes.py", "--deploy"],
        ["render_agents.py", "--target", "claude,omp", "--deploy"],
        ["render_invariants.py", "--deploy"],
        ["render_agents.py", "--target", "claude,omp", "--verify"],
        ["render_prompts.py", "--target", "claude,omp", "--status"],
    ]


def test_plan_dry_run_previews_without_verification(tmp_path):
    steps = scripts_and_flags(update.plan(tmp_path, ["codex"], dry_run=True))
    assert steps == [
        ["render_prompts.py", "--check"],
        ["render_agents.py", "--check"],
        ["render_prompts.py", "--target", "codex", "--dry-run"],
        ["render_agents.py", "--target", "codex", "--dry-run"],
    ]


def test_plan_hermes_only_skips_file_targets(tmp_path):
    steps = scripts_and_flags(update.plan(tmp_path, ["hermes"], dry_run=False))
    assert steps == [
        ["render_prompts.py", "--check"],
        ["render_agents.py", "--check"],
        ["render_hermes.py", "--deploy"],
    ]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_pull_refuses_local_tracked_changes(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "file.txt").write_text("one\n", encoding="utf-8")
    git(tmp_path, "add", "file.txt")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "init")
    (tmp_path / "file.txt").write_text("two\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="Local tracked changes"):
        update.pull(tmp_path)


def test_detect_uses_binaries_then_config_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(update.shutil, "which", lambda name: "/bin/x" if name == "omp" else None)
    (tmp_path / ".codex").mkdir()
    found = update.detect(home=tmp_path)
    assert found == {"codex": f"config {tmp_path / '.codex'}", "omp": "binary omp"}
