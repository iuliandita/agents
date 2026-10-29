import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
OVERRIDE_PREFIXES = ("AGENTS_", "CLAUDE_", "CODEX_", "OPENCODE_", "COMMANDCODE_", "ANTIGRAVITY_", "OMP_", "PI_", "HERMES_")


@pytest.fixture
def env(tmp_path):
    clean = {k: v for k, v in os.environ.items() if not k.startswith(OVERRIDE_PREFIXES)}
    clean["HOME"] = str(tmp_path / "home")
    clean["USERPROFILE"] = clean["HOME"]
    return clean


def run(env, script, *args):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args], cwd=REPO, env=env, capture_output=True, text=True
    )
    return proc


def run_json(env, script, *args):
    proc = run(env, script, "--json", *args)
    data = json.loads(proc.stdout)
    assert proc.stdout.count("\n") == 1, "stdout holds exactly one line"
    assert isinstance(data, dict)
    assert data["ok"] == (proc.returncode == 0)
    assert isinstance(data["errors"], list)
    assert bool(data["errors"]) == (not data["ok"])
    assert all(isinstance(line, str) and line.startswith("error:") for line in data["errors"])
    return proc.returncode, data


def test_prompts_list_targets(env):
    code, data = run_json(env, "render_prompts.py", "--list-targets", "--harness", "claude,codex")
    assert code == 0
    assert data["mode"] == "list-targets"
    assert [t["name"] for t in data["targets"]] == ["claude", "codex"]
    assert set(data["targets"][0]) == {"name", "display", "support", "path", "target"}


def test_prompts_check_render_and_notes(env, tmp_path):
    code, data = run_json(env, "render_prompts.py", "--check", "--harness", "claude")
    assert code == 0 and data["mode"] == "check" and data["checked"] == [{"harness": "claude"}]
    code, data = run_json(env, "render_prompts.py", "--target", "claude", "--out-dir", str(tmp_path / "out"))
    assert code == 0 and data["mode"] == "render"
    assert data["rendered"][0]["harness"] == "claude"
    assert Path(data["rendered"][0]["path"]).is_file()


def test_prompts_dry_run_deploy_and_status(env, tmp_path):
    env["CLAUDE_AGENTS_PATH"] = str(tmp_path / "CLAUDE.md")
    code, data = run_json(env, "render_prompts.py", "--dry-run", "--harness", "claude")
    assert code == 0 and data["mode"] == "deploy" and data["dry_run"] is True
    assert data["actions"] == [{"harness": "claude", "action": "would-update", "path": str(tmp_path / "CLAUDE.md")}]
    assert not (tmp_path / "CLAUDE.md").exists()

    code, data = run_json(env, "render_prompts.py", "--deploy", "--harness", "claude", "--backup-dir", str(tmp_path / "b"))
    assert code == 0 and data["actions"][0]["action"] == "updated"
    code, data = run_json(env, "render_prompts.py", "--status", "--harness", "claude")
    assert code == 0 and data["harnesses"][0]["state"] == "in-sync"

    (tmp_path / "CLAUDE.md").write_text("changed\n", encoding="utf-8")
    code, data = run_json(env, "render_prompts.py", "--status", "--harness", "claude")
    assert code == 1 and data["harnesses"][0]["state"] in {"drift", "local-edits"}
    assert "differ from a fresh render" in data["errors"][0]


def test_prompts_prune_backups(env, tmp_path):
    backups = tmp_path / "b"
    backups.mkdir()
    for index in range(3):
        (backups / f"f{index}.bak").write_text("x", encoding="utf-8")
        os.utime(backups / f"f{index}.bak", (index, index))
    code, data = run_json(env, "render_prompts.py", "--prune-backups", "1", "--dry-run", "--backup-dir", str(backups))
    assert code == 0 and data["mode"] == "prune-backups" and data["keep"] == 1
    assert [b["action"] for b in data["backups"]] == ["would-remove", "would-remove"]


def test_prompts_errors_and_usage(env):
    code, data = run_json(env, "render_prompts.py", "--check", "--harness", "nope")
    assert code == 1 and "unknown harness: nope" in data["errors"][0]
    code, data = run_json(env, "render_prompts.py", "--deploy")
    assert code == 1 and "--deploy requires --target" in data["errors"][0]
    proc = run(env, "render_prompts.py", "--json", "--bogus")
    data = json.loads(proc.stdout)
    assert proc.returncode == 2 and data["ok"] is False and "unrecognized arguments" in data["errors"][0]


def test_agents_modes(env, tmp_path):
    env["CLAUDE_AGENTS_DIR"] = str(tmp_path / "agents")
    code, data = run_json(env, "render_agents.py", "--list-targets", "--harness", "claude")
    assert code == 0 and data["targets"][0]["env_var"] == "CLAUDE_AGENTS_DIR"
    code, data = run_json(env, "render_agents.py", "--check", "--harness", "claude")
    assert code == 0 and data["checked"] == [{"harness": "claude", "agents": 6}]
    code, data = run_json(env, "render_agents.py", "--dry-run", "--harness", "claude")
    assert code == 0 and {a["action"] for a in data["actions"]} == {"would-create"} and len(data["actions"]) == 6
    code, data = run_json(env, "render_agents.py", "--verify", "--harness", "claude")
    assert code == 1 and data["harnesses"][0]["missing"] and "role file is missing" in data["errors"][0]
    code, data = run_json(env, "render_agents.py", "--deploy", "--harness", "claude", "--backup-dir", str(tmp_path / "b"))
    assert code == 0 and {a["action"] for a in data["actions"]} == {"updated"}
    code, data = run_json(env, "render_agents.py", "--verify", "--harness", "claude")
    assert code == 0 and data["harnesses"][0]["missing"] == []
    code, data = run_json(env, "render_agents.py", "--harness", "claude", "--out-dir", str(tmp_path / "out"))
    assert code == 0 and data["rendered"][0]["agents"] == 6


def test_invariants_modes(env, tmp_path):
    hooks, settings = tmp_path / "hooks", tmp_path / "settings.json"
    args = ["--hooks-dir", str(hooks), "--settings-path", str(settings), "--backup-dir", str(tmp_path / "b")]
    code, data = run_json(env, "render_invariants.py", "--dry-run", *args)
    assert code == 0 and [a["action"] for a in data["actions"]] == ["would-install", "would-merge"]
    code, data = run_json(env, "render_invariants.py", "--deploy", *args)
    assert code == 0 and [a["action"] for a in data["actions"]] == ["installed", "merged"]
    code, data = run_json(env, "render_invariants.py", "--deploy", *args)
    assert [a["action"] for a in data["actions"]] == ["unchanged", "unchanged"]
    code, data = run_json(env, "render_invariants.py", *args, "--out-dir", str(tmp_path / "out"))
    assert code == 0 and data["mode"] == "render" and data["rendered"]
    settings.write_text("[]", encoding="utf-8")
    code, data = run_json(env, "render_invariants.py", "--dry-run", *args)
    assert code == 1 and "settings.json root is not an object" in data["errors"][0]


def test_hermes_modes(env, tmp_path):
    config = tmp_path / "config.yaml"
    args = ["--path", str(config), "--backup-dir", str(tmp_path / "b")]
    code, data = run_json(env, "render_hermes.py", "--dry-run", *args)
    assert code == 0 and data["actions"] == [{"harness": "hermes", "action": "would-update", "path": str(config)}]
    code, data = run_json(env, "render_hermes.py", "--deploy", *args)
    assert code == 0 and data["actions"][0]["action"] == "updated" and config.is_file()
    code, data = run_json(env, "render_hermes.py", "--deploy", *args)
    assert data["actions"][0]["action"] == "unchanged"
    code, data = run_json(env, "render_hermes.py", *args, "--out-dir", str(tmp_path / "out"))
    assert code == 0 and data["rendered"][0]["harness"] == "hermes"


def test_install_workflow_modes(env, tmp_path):
    skills = tmp_path / "skills"
    code, data = run_json(env, "install_workflow.py", "--skills-dir", str(skills))
    assert code == 0 and data["mode"] == "dry-run" and data["actions"][0]["action"] == "would-install"
    assert not skills.exists()
    code, data = run_json(env, "install_workflow.py", "--skills-dir", str(skills), "--deploy")
    assert code == 0 and data["mode"] == "deploy" and data["actions"][0]["action"] == "installed"
    assert Path(data["actions"][0]["path"]).is_file()
    target = tmp_path / "file"
    target.write_text("x", encoding="utf-8")
    code, data = run_json(env, "install_workflow.py", "--skills-dir", str(target / "sub"))
    assert code == 1 and data["errors"]
    proc = run(env, "install_workflow.py", "--json")
    assert proc.returncode == 2 and json.loads(proc.stdout)["ok"] is False


def test_update_detect_and_steps(env, tmp_path):
    code, data = run_json(env, "update.py", "--detect")
    assert code == 0 and data["mode"] == "detect" and isinstance(data["harnesses"], list)
    env["CLAUDE_AGENTS_PATH"] = str(tmp_path / "CLAUDE.md")
    env["CLAUDE_AGENTS_DIR"] = str(tmp_path / "agents")
    code, data = run_json(env, "update.py", "--harness", "claude", "--no-pull", "--dry-run")
    assert code == 0 and data["mode"] == "update" and data["targets"] == ["claude"]
    assert data["dry_run"] is True and data["pull"] is False
    assert data["steps"] and all(step["exit"] == 0 for step in data["steps"])
    assert not (tmp_path / "CLAUDE.md").exists()


def test_update_failure_is_reported(env, tmp_path):
    (tmp_path / "home").mkdir()
    code, data = run_json(env, "update.py", "--harness", "nope", "--no-pull")
    assert code == 1 and "unknown" in data["errors"][0]
