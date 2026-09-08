from pathlib import Path
import shutil
import shlex
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
WRAPPERS = ("sync-ai-prompts", "render-agents", "render-invariants")


@pytest.fixture
def runtime(tmp_path):
    checkout = tmp_path / "checkout with spaces"
    shutil.copytree(REPO / "scripts", checkout / "scripts")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "dirname").symlink_to(shutil.which("dirname"))
    env = {"PATH": str(bin_dir), "HOME": str(tmp_path)}
    return checkout, bin_dir, env


def run(runtime, wrapper="sync-ai-prompts", *args):
    checkout, _, env = runtime
    return subprocess.run(
        [BASH, str(checkout / "scripts" / wrapper), *(args or ("--help",))],
        env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize("wrapper", WRAPPERS)
def test_wrappers_work_with_only_python3(runtime, wrapper):
    _, bin_dir, _ = runtime
    (bin_dir / "python3").symlink_to(sys.executable)
    result = run(runtime, wrapper)
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


def old_python(path):
    probe = "import sys; sys.version_info = (3, 9, 6); exec(sys.argv[1])"
    path.write_text(
        f"#!/bin/sh\nexec {shlex.quote(sys.executable)} -c {shlex.quote(probe)} \"$2\"\n"
    )
    path.chmod(0o755)


def test_old_python_falls_back_to_python3(runtime):
    _, bin_dir, _ = runtime
    old_python(bin_dir / "python")
    (bin_dir / "python3").symlink_to(sys.executable)
    result = run(runtime)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("old", [False, True])
def test_missing_or_old_python_reports_setup_instructions(runtime, old):
    checkout, bin_dir, _ = runtime
    if old:
        old_python(bin_dir / "python3")
    result = run(runtime)
    assert result.returncode != 0
    assert "Python 3.11+" in result.stderr
    assert "AGENTS_PYTHON" in result.stderr
    assert "INSTALL.md" in result.stderr
    assert not (checkout / "build").exists()


def test_explicit_interpreter_with_spaces_takes_precedence(runtime):
    _, bin_dir, env = runtime
    chosen = bin_dir / "selected python"
    chosen.symlink_to(sys.executable)
    old_python(bin_dir / "python")
    env["AGENTS_PYTHON"] = str(chosen)
    result = run(runtime)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("override", ["missing-python", "", "old-python"])
def test_invalid_explicit_override_never_falls_back(runtime, override):
    _, bin_dir, env = runtime
    (bin_dir / "python").symlink_to(sys.executable)
    old_python(bin_dir / "old-python")
    env["AGENTS_PYTHON"] = override
    result = run(runtime)
    assert result.returncode != 0
    assert "AGENTS_PYTHON" in result.stderr


def test_renderer_error_status_is_preserved(runtime):
    _, bin_dir, _ = runtime
    (bin_dir / "python3").symlink_to(sys.executable)
    result = run(runtime, "sync-ai-prompts", "--not-a-valid-option")
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr


def test_python_on_path_is_preferred_to_python3(runtime):
    _, bin_dir, _ = runtime
    (bin_dir / "python").symlink_to(sys.executable)
    old_python(bin_dir / "python3")
    result = run(runtime)
    assert result.returncode == 0, result.stderr


def test_prompt_dry_run_needs_no_site_packages(runtime):
    checkout, bin_dir, _ = runtime
    shutil.copytree(
        REPO / "prompts", checkout / "prompts",
        ignore=shutil.ignore_patterns("private.md", "models.local.json", "private-patterns.txt"),
    )
    interpreter = bin_dir / "python3"
    interpreter.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -S "$@"\n')
    interpreter.chmod(0o755)
    result = run(runtime, "sync-ai-prompts", "--target", "claude", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "would update claude:" in result.stdout
    assert not (checkout / "build").exists()
