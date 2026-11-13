import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import update


@pytest.fixture(autouse=True)
def isolated_git_config(tmp_path, monkeypatch):
    config = tmp_path / "gitconfig"
    config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("AGENTS_UPDATE_BRANCHES", raising=False)


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


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def commit_file(repo: Path, text: str) -> None:
    (repo / "file.txt").write_text(text, encoding="utf-8")
    git(repo, "add", "file.txt")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "change")


@pytest.fixture
def remote_checkout(tmp_path):
    remote, seed, checkout = (tmp_path / name for name in ("remote.git", "seed", "checkout"))
    for repo in (remote, seed):
        repo.mkdir()
    git(remote, "init", "--bare", "--initial-branch=main")
    git(seed, "init", "--initial-branch=main")
    commit_file(seed, "one\n")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    git(tmp_path, "clone", str(remote), str(checkout))
    return checkout, seed


@pytest.mark.parametrize(("branch", "allowed"), [("main", None), ("develop", None), ("develop", " develop ")])
def test_pull_fast_forwards_allowed_tracking_branch(remote_checkout, monkeypatch, branch, allowed):
    checkout, seed = remote_checkout
    if allowed is not None:
        monkeypatch.setenv("AGENTS_UPDATE_BRANCHES", allowed)
    if branch != "main":
        git(seed, "switch", "-c", branch)
        git(seed, "push", "-u", "origin", branch)
        git(checkout, "fetch")
        git(checkout, "switch", "--track", f"origin/{branch}")
    commit_file(seed, "remote change\n")
    git(seed, "push")

    update.pull(checkout)

    assert git(checkout, "rev-parse", "HEAD") == git(seed, "rev-parse", "HEAD")
    assert (checkout / "file.txt").read_text(encoding="utf-8") == "remote change\n"


def test_pull_refuses_diverged_history(remote_checkout):
    checkout, seed = remote_checkout
    commit_file(checkout, "local change\n")
    original = git(checkout, "rev-parse", "HEAD")
    commit_file(seed, "remote change\n")
    git(seed, "push")

    with pytest.raises(SystemExit, match="error: git pull --ff-only failed with exit"):
        update.pull(checkout)

    assert git(checkout, "rev-parse", "HEAD") == original
    assert (checkout / "file.txt").read_text(encoding="utf-8") == "local change\n"


@pytest.mark.parametrize(
    ("state", "allowed", "message"),
    [
        ("feature", None, "branch feature is not allowed"),
        ("feature", "main,develop,feature", "branch feature is not allowed"),
        ("main", "develop", "branch main is not allowed"),
        ("main", "", "allowed branches: none"),
        ("no-upstream", None, "must track an upstream"),
        ("detached", None, "detached HEAD"),
    ],
)
def test_main_refuses_untrusted_checkout_before_steps(remote_checkout, monkeypatch, state, allowed, message):
    checkout, _ = remote_checkout
    if state == "feature":
        git(checkout, "switch", "-c", "feature", "--track", "origin/main")
    elif state == "no-upstream":
        git(checkout, "branch", "--unset-upstream")
    elif state == "detached":
        git(checkout, "checkout", "--detach")
    if allowed is not None:
        monkeypatch.setenv("AGENTS_UPDATE_BRANCHES", allowed)
    original = git(checkout, "rev-parse", "HEAD")

    result = subprocess.run(
        [sys.executable, update.__file__, "--repo-root", str(checkout), "--targets", "hermes", "--dry-run"],
        capture_output=True, text=True,
    )

    assert result.returncode == 1
    assert "error:" in result.stderr
    assert message in result.stderr
    assert "==>" not in result.stdout
    assert git(checkout, "rev-parse", "HEAD") == original


@pytest.mark.parametrize("state", ["feature", "detached"])
def test_no_pull_skips_branch_and_upstream_checks(remote_checkout, monkeypatch, capsys, state):
    checkout, _ = remote_checkout
    git(checkout, "switch", "-c", "feature")
    if state == "detached":
        git(checkout, "checkout", "--detach")
    monkeypatch.setenv("AGENTS_UPDATE_BRANCHES", "")
    calls = []
    monkeypatch.setattr(update, "plan", lambda *args: calls.append(args) or [])

    assert update.main(["--repo-root", str(checkout), "--targets", "hermes", "--no-pull"]) == 0

    assert calls
    assert "note: --no-pull: the checkout is deployed as is" in capsys.readouterr().err


def test_pull_refuses_local_tracked_changes(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "file.txt").write_text("one\n", encoding="utf-8")
    git(tmp_path, "add", "file.txt")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "init")
    (tmp_path / "file.txt").write_text("two\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="local tracked changes"):
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


def test_git_missing_exits_three_with_clear_message(tmp_path, monkeypatch, capsys):
    def missing(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(update.subprocess, "run", missing)
    with pytest.raises(SystemExit) as exc:
        update.pull(tmp_path)
    assert exc.value.code == 3
    assert "error: git is not on PATH" in capsys.readouterr().err


def test_git_runs_noninteractive_with_timeout(tmp_path, monkeypatch):
    seen = {}

    def fake(cmd, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(update.subprocess, "run", fake)
    update.git(tmp_path, "status")
    assert seen["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert seen["timeout"] == update.GIT_TIMEOUT_SECONDS


@pytest.mark.parametrize("failure", ["timeout", "nonzero"])
def test_git_failures_have_clear_errors(tmp_path, monkeypatch, failure):
    def fail(cmd, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(cmd, update.GIT_TIMEOUT_SECONDS)
        raise subprocess.CalledProcessError(17, cmd)

    monkeypatch.setattr(update.subprocess, "run", fail)
    message = "timed out after 300s" if failure == "timeout" else "failed with exit 17"
    with pytest.raises(SystemExit, match=f"error: git status {message}"):
        update.git(tmp_path, "status")


def run_main(tmp_path, monkeypatch, fail_at=None, flag="--targets"):
    calls = []

    def fake(cmd, **kwargs):
        calls.append(cmd)
        code = 1 if fail_at is not None and len(calls) == fail_at else 0
        return subprocess.CompletedProcess(cmd, code)

    monkeypatch.setattr(update.subprocess, "run", fake)
    monkeypatch.delenv("AGENTS_PRIVATE_HARNESSES", raising=False)
    (tmp_path / "prompts").mkdir(exist_ok=True)
    rc = update.main(["--repo-root", str(tmp_path), flag, "claude,codex", "--no-pull"])
    return rc, calls


def test_main_runs_every_step_and_reports_success(tmp_path, monkeypatch, capsys):
    rc, calls = run_main(tmp_path, monkeypatch)
    assert rc == 0
    assert len(calls) == len(update.plan(tmp_path, ["claude", "codex"], dry_run=False))
    out = capsys.readouterr().out
    assert "private overlay: none" in out
    assert "update complete for: claude, codex" in out


def test_harness_is_an_alias_of_targets(tmp_path, monkeypatch, capsys):
    rc, calls = run_main(tmp_path, monkeypatch, flag="--harness")
    assert rc == 0
    assert len(calls) == len(update.plan(tmp_path, ["claude", "codex"], dry_run=False))
    assert "update complete for: claude, codex" in capsys.readouterr().out
    assert update.parse_args(["--harness", "claude", "--harness", "codex"]).targets == ["claude", "codex"]
    assert update.parse_args(["--targets", "claude"]).targets == ["claude"]
    assert update.parse_args([]).targets is None


@pytest.mark.parametrize("fail_at", [1, 3, 6])
def test_main_stops_at_first_failing_step(tmp_path, monkeypatch, capsys, fail_at):
    rc, calls = run_main(tmp_path, monkeypatch, fail_at=fail_at)
    assert rc == 1
    assert len(calls) == fail_at
    captured = capsys.readouterr()
    assert "update failed at" in captured.err
    assert "update complete" not in captured.out
    with update.run_lock(tmp_path):
        pass


def test_overlay_summary_names_trust_source(tmp_path, monkeypatch):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "private.md").write_text("secret\n", encoding="utf-8")
    monkeypatch.setenv("AGENTS_PRIVATE_HARNESSES", "all")
    lines = update.overlay_summary(tmp_path, ["claude", "omp"])
    assert lines[1] == "private overlay: sent to claude, omp (trust list from AGENTS_PRIVATE_HARNESSES)"


def test_second_run_is_refused_while_locked(tmp_path):
    with update.run_lock(tmp_path):
        with pytest.raises(SystemExit, match="another update is running"):
            with update.run_lock(tmp_path):
                pass


def test_windows_lock_contention_has_clear_error(tmp_path, monkeypatch):
    def contended(fd, mode, length):
        raise OSError("lock is held")

    monkeypatch.setitem(sys.modules, "fcntl", None)
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(locking=contended, LK_NBLCK=1))
    with pytest.raises(SystemExit, match="error: another update is running"):
        with update.run_lock(tmp_path):
            pytest.fail("contended lock was acquired")
