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


def test_repository_venv_takes_precedence_over_path(runtime):
    checkout, bin_dir, _ = runtime
    venv_python = checkout / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.symlink_to(sys.executable)
    path_python = bin_dir / "python"
    path_python.write_text(
        '#!/bin/sh\nif [ "$1" = "-c" ]; then\n'
        f'  exec {shlex.quote(sys.executable)} "$@"\nfi\nexit 97\n'
    )
    path_python.chmod(0o755)
    old_python(bin_dir / "python3")
    result = run(runtime)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("invalid", ["old", "not-executable", "broken-symlink"])
def test_invalid_repository_venv_never_falls_back(runtime, invalid):
    checkout, bin_dir, env = runtime
    venv_python = checkout / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    if invalid == "old":
        old_python(venv_python)
    elif invalid == "not-executable":
        venv_python.write_text("#!/bin/sh\nexit 0\n")
    else:
        venv_python.symlink_to(checkout / "missing-python")
    (bin_dir / "python").symlink_to(sys.executable)
    result = run(runtime)
    assert result.returncode != 0
    assert ".venv/bin/python" in result.stderr
    assert "INSTALL.md" in result.stderr
    env["AGENTS_PYTHON"] = sys.executable
    result = run(runtime)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("selection", ["relative-override", "venv"])
def test_autoimprove_score_uses_selected_python_after_chdir(runtime, selection):
    checkout, bin_dir, env = runtime
    caller = bin_dir.parent
    selected = (
        bin_dir / "selected python"
        if selection == "relative-override"
        else checkout / ".venv" / "bin" / "python"
    )
    selected.parent.mkdir(parents=True, exist_ok=True)
    log = caller / "score.log"
    selected.write_text(
        '#!/bin/sh\nif [ "$1" = "-c" ]; then\n'
        f'  exec {shlex.quote(sys.executable)} "$@"\nfi\n'
        f'printf "%s\\n" "$*" >> {shlex.quote(str(log))}\n'
    )
    selected.chmod(0o755)
    old_python(bin_dir / "python")
    if selection == "relative-override":
        env["AGENTS_PYTHON"] = str(selected.relative_to(caller))
    result = subprocess.run(
        [BASH, str(checkout / "scripts" / "autoimprove-prompts"), "--iterations", "0"],
        cwd=caller, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == [
        str(checkout / "scripts" / "lint_prompts.py"),
        str(checkout / "scripts" / "scan_prompt_sources.py"),
        f"-m pytest -q {checkout / 'tests'}",
        f"{checkout / 'scripts' / 'render_prompts.py'} --repo-root {checkout} "
        f"--out-dir {checkout / 'build' / 'generated'}",
    ]
