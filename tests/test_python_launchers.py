"""Exercise shell launchers with an isolated executable search path."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1]
LAUNCHERS = {
    "sync-ai-prompts": "render_prompts.py",
    "render-agents": "render_agents.py",
    "render-invariants": "render_invariants.py",
}


@pytest.fixture
def launcher_repo(tmp_path):
    repo = tmp_path / "repo with spaces"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    for name in (*LAUNCHERS, "python-runtime.sh", "autoimprove-prompts"):
        shutil.copy2(SOURCE / "scripts" / name, scripts / name)
    for renderer in LAUNCHERS.values():
        (scripts / renderer).write_text(
            "import json, os, sys\n"
            "print(json.dumps(sys.argv[1:]))\n"
            "sys.exit(int(os.environ.get('RENDER_STATUS', '0')))\n"
        )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("bash", "dirname"):
        (bin_dir / name).symlink_to(shutil.which(name))
    env = {**os.environ, "PATH": str(bin_dir)}
    env.pop("AGENTS_PYTHON", None)
    return repo, bin_dir, env


def launch(fixture, name="sync-ai-prompts", *args):
    repo, _, env = fixture
    return subprocess.run(
        [str(repo / "scripts" / name), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("name", LAUNCHERS)
def test_python3_only_path_preserves_arguments_and_status(launcher_repo, name):
    repo, bin_dir, env = launcher_repo
    (bin_dir / "python3").symlink_to(sys.executable)
    env["RENDER_STATUS"] = "23"
    result = launch(launcher_repo, name, "--out-dir", "folder with spaces", "")
    assert result.returncode == 23, result.stderr
    assert json.loads(result.stdout) == [
        "--repo-root", str(repo), "--out-dir", "folder with spaces", ""
    ]


def test_explicit_path_with_spaces_takes_precedence(launcher_repo):
    repo, bin_dir, env = launcher_repo
    interpreter = bin_dir / "chosen python"
    interpreter.symlink_to(sys.executable)
    env["AGENTS_PYTHON"] = str(interpreter)
    venv = repo / ".venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").write_text("#!/bin/sh\nexit 99\n")
    (venv / "python").chmod(0o755)
    result = launch(launcher_repo)
    assert result.returncode == 0, result.stderr


def test_explicit_command_name(launcher_repo):
    _, bin_dir, env = launcher_repo
    (bin_dir / "custom-python").symlink_to(sys.executable)
    env["AGENTS_PYTHON"] = "custom-python"
    assert launch(launcher_repo).returncode == 0


def test_venv_precedes_path(launcher_repo):
    repo, bin_dir, _ = launcher_repo
    venv = repo / ".venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").symlink_to(sys.executable)
    (bin_dir / "python3").write_text("#!/bin/sh\nexit 99\n")
    (bin_dir / "python3").chmod(0o755)
    result = launch(launcher_repo)
    assert result.returncode == 0, result.stderr


def test_python_fallback(launcher_repo):
    _, bin_dir, _ = launcher_repo
    (bin_dir / "python").symlink_to(sys.executable)
    result = launch(launcher_repo)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("override", ["", "/missing/python", "python --invalid-option"])
def test_invalid_override_never_falls_back(launcher_repo, override):
    _, bin_dir, env = launcher_repo
    (bin_dir / "python3").symlink_to(sys.executable)
    env["AGENTS_PYTHON"] = override
    result = launch(launcher_repo)
    assert result.returncode != 0
    assert "INSTALL.md" in result.stderr
    assert "AGENTS_PYTHON" in result.stderr
    assert not result.stdout


def test_missing_interpreter_has_bootstrap_guidance(launcher_repo):
    result = launch(launcher_repo)
    assert result.returncode != 0
    assert "Python 3.11+" in result.stderr
    assert "INSTALL.md" in result.stderr


def test_old_python_is_rejected_without_fallback(launcher_repo):
    _, bin_dir, env = launcher_repo
    # Run the actual version probe with an older version tuple.
    old = bin_dir / "old-python"
    old.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "sys.version_info = (3, 10, 9)\n"
        "exec(sys.argv[2])\n"
    )
    old.chmod(0o755)
    (bin_dir / "python3").symlink_to(sys.executable)
    env["AGENTS_PYTHON"] = str(old)
    result = launch(launcher_repo)
    assert result.returncode != 0
    assert "Python 3.11+" in result.stderr
    assert "INSTALL.md" in result.stderr
    assert not result.stdout


def test_autoimprove_score_uses_selected_python(launcher_repo):
    repo, bin_dir, env = launcher_repo
    (bin_dir / "python3").symlink_to(sys.executable)
    log = repo / "invocations.jsonl"
    interpreter = bin_dir / "score python"
    interpreter.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "if sys.argv[1] == '-c':\n"
        "    exec(sys.argv[2])\n"
        "else:\n"
        "    with open(os.environ['SCORE_LOG'], 'a') as log:\n"
        "        log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
    )
    interpreter.chmod(0o755)
    env.update(AGENTS_PYTHON=str(interpreter), SCORE_LOG=str(log))
    result = launch(launcher_repo, "autoimprove-prompts", "--iterations", "0")
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls == [
        [str(repo / "scripts/lint_prompts.py")],
        [str(repo / "scripts/scan_prompt_sources.py")],
        ["-m", "pytest", "-q", str(repo / "tests")],
        [str(repo / "scripts/render_prompts.py"), "--repo-root", str(repo),
         "--out-dir", str(repo / "build/generated")],
    ]
