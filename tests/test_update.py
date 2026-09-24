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


def test_empty_cli_targets_do_not_fall_back(tmp_path):
    write_targets(tmp_path, "claude\n")
    with pytest.raises(SystemExit, match="lists no harnesses"):
        update.load_targets(tmp_path, "", env={"AGENTS_DEPLOY_TARGETS": "codex"})


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
        ["render_prompts.py", "--target", "claude,hermes,omp", "--check"],
        ["render_agents.py", "--target", "claude,omp", "--check"],
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
        ["render_prompts.py", "--target", "codex", "--check"],
        ["render_agents.py", "--target", "codex", "--check"],
        ["render_prompts.py", "--target", "codex", "--dry-run"],
        ["render_agents.py", "--target", "codex", "--dry-run"],
    ]


def test_plan_hermes_only_skips_file_targets(tmp_path):
    steps = scripts_and_flags(update.plan(tmp_path, ["hermes"], dry_run=False))
    assert steps == [
        ["render_prompts.py", "--target", "hermes", "--check"],
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
    found = update.detect(home=tmp_path, env={})
    assert found == {"codex": f"config {tmp_path / '.codex'}", "omp": "binary omp"}


def test_detect_follows_native_config_home(tmp_path, monkeypatch):
    monkeypatch.setattr(update.shutil, "which", lambda name: None)
    (tmp_path / "custom-codex").mkdir()
    found = update.detect(home=tmp_path, env={"CODEX_HOME": str(tmp_path / "custom-codex")})
    assert found == {"codex": f"config {tmp_path / 'custom-codex'}"}


def test_git_missing_fails_with_clear_message(tmp_path, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(update.subprocess, "run", missing)
    with pytest.raises(SystemExit, match="git is not on PATH"):
        update.pull(tmp_path)


def test_git_runs_noninteractive_with_timeout(tmp_path, monkeypatch):
    seen = {}

    def fake(cmd, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(update.subprocess, "run", fake)
    update.git(tmp_path, "status")
    assert seen["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert seen["timeout"] == update.GIT_TIMEOUT_SECONDS


def run_main(tmp_path, monkeypatch, fail_at=None):
    calls = []

    def fake(cmd, **kwargs):
        calls.append(cmd)
        code = 1 if fail_at is not None and len(calls) == fail_at else 0
        return subprocess.CompletedProcess(cmd, code)

    monkeypatch.setattr(update.subprocess, "run", fake)
    monkeypatch.delenv("AGENTS_PRIVATE_HARNESSES", raising=False)
    (tmp_path / "prompts").mkdir(exist_ok=True)
    rc = update.main(["--repo-root", str(tmp_path), "--targets", "claude,codex", "--no-pull"])
    return rc, calls


def test_main_runs_every_step_and_reports_success(tmp_path, monkeypatch, capsys):
    rc, calls = run_main(tmp_path, monkeypatch)
    assert rc == 0
    assert len(calls) == len(update.plan(tmp_path, ["claude", "codex"], dry_run=False))
    out = capsys.readouterr().out
    assert "private overlay: none" in out
    assert "update complete for: claude, codex" in out


@pytest.mark.parametrize("fail_at", [1, 3, 6])
def test_main_stops_at_first_failing_step(tmp_path, monkeypatch, capsys, fail_at):
    rc, calls = run_main(tmp_path, monkeypatch, fail_at=fail_at)
    assert rc == 1
    assert len(calls) == fail_at
    captured = capsys.readouterr()
    assert "update failed at:" in captured.err
    assert "update complete" not in captured.out


def test_overlay_summary_names_trust_source(tmp_path, monkeypatch):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "private.md").write_text("secret\n", encoding="utf-8")
    monkeypatch.setenv("AGENTS_PRIVATE_HARNESSES", "all")
    lines = update.overlay_summary(tmp_path, ["claude", "omp"])
    assert lines[1] == "private overlay: sent to claude, omp (trust list from AGENTS_PRIVATE_HARNESSES)"


def test_second_run_is_refused_while_locked(tmp_path):
    with update.run_lock(tmp_path):
        with pytest.raises(SystemExit, match="Another update is running"):
            with update.run_lock(tmp_path):
                pass
