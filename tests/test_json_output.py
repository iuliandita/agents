import importlib
import json
import os
import shutil
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


@pytest.mark.parametrize("harness,filename", [
    ("claude", "invariants-userpromptsubmit.sh"),
    ("antigravity", "invariants-preinvocation.sh"),
])
@pytest.mark.parametrize("adopt", [False, True])
def test_invariants_dry_run_reports_unmanaged_hook(env, tmp_path, harness, filename, adopt):
    hook = tmp_path / filename
    hook.write_text("user hook\n", encoding="utf-8")
    code, data = run_json(
        env, "render_invariants.py", "--dry-run", "--harness", harness,
        "--hooks-dir", str(tmp_path), "--settings-path", str(tmp_path / "settings.json"),
        "--antigravity-config-dir", str(tmp_path), *( ["--adopt"] if adopt else []),
    )
    assert code == 0 and data["mode"] == "deploy"
    assert data["actions"][0]["action"] == ("would-install" if adopt else "would-replace-unmanaged")
    assert hook.read_text(encoding="utf-8") == "user hook\n"
    assert not (tmp_path / "settings.json").exists()


@pytest.mark.parametrize("module_name,default_out", [
    ("render_prompts", "build/generated"), ("render_agents", "build/agents"),
    ("render_invariants", "build/generated/invariants"), ("render_hermes", "build/generated"),
])
@pytest.mark.parametrize("kind", ["default", "relative", "absolute"])
def test_renderer_paths_follow_repo_root(tmp_path, module_name, default_out, kind):
    module = importlib.import_module(module_name)
    root = tmp_path / "other-repo"
    extra = []
    out, backup = root / default_out, root / ".backups"
    if kind != "default":
        out_arg = Path("artifacts") if kind == "relative" else tmp_path / "artifacts"
        backup_arg = Path("saved") if kind == "relative" else tmp_path / "saved"
        extra = ["--out-dir", str(out_arg), "--backup-dir", str(backup_arg)]
        out, backup = root / out_arg, root / backup_arg
    args = module.parse_args(["--repo-root", str(root), *extra])
    assert args.out_dir == out
    assert args.backup_dir == backup


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
    sizes = data["actions"][0].pop("bytes")
    assert data["actions"] == [{"harness": "claude", "action": "would-update", "path": str(tmp_path / "CLAUDE.md")}]
    assert sizes["total"] == sum(section["bytes"] for section in sizes["sections"])
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
        name = f"CLAUDE-2026-01-0{index + 1}-tmp-CLAUDE.md.bak"
        (backups / name).write_text("x", encoding="utf-8")
        os.utime(backups / name, (index, index))
    code, data = run_json(env, "render_prompts.py", "--prune-backups", "1", "--dry-run", "--backup-dir", str(backups))
    assert code == 0 and data["mode"] == "prune-backups" and data["keep"] == 1
    assert [b["action"] for b in data["backups"]] == ["would-remove", "would-remove"]


def test_prompts_errors_and_usage(env):
    code, data = run_json(env, "render_prompts.py", "--check", "--harness", "nope")
    assert code == 2 and "unknown harness: nope" in data["errors"][0]
    code, data = run_json(env, "render_prompts.py", "--deploy")
    assert code == 2 and "--deploy requires --target" in data["errors"][0]
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
    args = ["--harness", "claude", "--hooks-dir", str(hooks), "--settings-path", str(settings), "--backup-dir", str(tmp_path / "b")]
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
    assert code == 2 and "unknown" in data["errors"][0]


ENTRYPOINTS = (
    ("render_prompts.py", "sync-ai-prompts", []),
    ("render_agents.py", "render-agents", []),
    ("render_hermes.py", "render-hermes", []),
    ("render_invariants.py", "render-invariants", []),
    ("update.py", "update", ["--detect"]),
    ("install_workflow.py", "install_workflow", ["--skills-dir", "unused"]),
)


@pytest.mark.parametrize("script,prog,args", ENTRYPOINTS)
@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize("failure", [PermissionError("denied"), RuntimeError("failed"),
                                    UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")])
def test_unexpected_errors_preserve_records_and_hide_tracebacks(script, prog, args, json_output, failure, monkeypatch, capsys):
    module = importlib.import_module(script.removesuffix(".py"))
    renderer = importlib.import_module("render_prompts")

    def fail(_args):
        renderer.json_record(action="completed")
        raise failure

    monkeypatch.setattr(module, "run", fail)
    code = module.main([*args, *(["--json"] if json_output else [])])
    output = capsys.readouterr()
    assert code == 1
    assert output.err == f"error: {prog}: {failure}\n"
    assert "Traceback" not in output.err
    if json_output:
        data = json.loads(output.out)
        assert output.out.count("\n") == 1
        assert data["ok"] is False and data["mode"] is not None
        assert data["errors"] == [output.err.strip()]
        key = "harnesses" if script == "update.py" else "actions" if script == "install_workflow.py" else "rendered"
        assert data[key] == [{"action": "completed"}]
    else:
        assert output.out == ""


@pytest.mark.parametrize("script", ["render_prompts.py", "render_hermes.py"])
def test_unreadable_core_has_one_json_object(env, tmp_path, script):
    # A directory cannot be read as core text, even when tests run as root.
    (tmp_path / "prompts" / "core.md").mkdir(parents=True)
    proc = run(env, script, "--json", "--repo-root", str(tmp_path), "--out-dir", str(tmp_path / "out"))
    data = json.loads(proc.stdout)
    assert proc.returncode == 1 and proc.stdout.count("\n") == 1
    assert data["mode"] == "render" and data["rendered"] == []
    assert "core.md" in data["errors"][0] and "Traceback" not in proc.stderr
    assert proc.stderr.startswith("error:")


@pytest.mark.parametrize("script,args,message", [
    ("render_prompts.py", ["--deploy"], "--deploy requires --target"),
    ("render_agents.py", ["--deploy"], "--deploy requires --target"),
    ("render_prompts.py", ["--target", "nope"], "unknown harness"),
    ("render_agents.py", ["--target", "nope"], "unknown agent harness"),
    ("render_prompts.py", ["--target", ","], "no harness names"),
    ("render_agents.py", ["--target", ","], "no harness names"),
    ("render_prompts.py", ["--prune-backups", "-1"], "non-negative count"),
    ("update.py", ["--no-pull"], "no deploy targets"),
    ("update.py", ["--targets", "nope", "--no-pull"], "unknown"),
    ("update.py", ["--targets", ",", "--no-pull"], "lists no harnesses"),
])
@pytest.mark.parametrize("json_output", [False, True])
def test_usage_errors_exit_two(env, tmp_path, script, args, message, json_output):
    proc = run(env, script, *(["--json"] if json_output else []), "--repo-root", str(tmp_path), *args)
    assert proc.returncode == 2
    assert message in proc.stderr and "Traceback" not in proc.stderr
    if json_output:
        data = json.loads(proc.stdout)
        assert data["ok"] is False and "mode" in data
        key = "steps" if script == "update.py" else "backups" if "--prune-backups" in args else "actions" if "--deploy" in args else "rendered"
        assert data[key] == []
    else:
        assert proc.stdout == ""


@pytest.mark.parametrize("script,args", [
    ("render_prompts.py", ["--check", "--deploy"]),
    ("render_prompts.py", ["--status", "--deploy"]),
    ("render_prompts.py", ["--list-targets", "--check"]),
    ("render_prompts.py", ["--prune-backups", "1", "--deploy"]),
    ("render_prompts.py", ["--check", "--dry-run"]),
    ("render_agents.py", ["--check", "--deploy"]),
    ("render_agents.py", ["--verify", "--deploy"]),
    ("render_agents.py", ["--list-targets", "--check"]),
    ("render_agents.py", ["--verify", "--dry-run"]),
    ("update.py", ["--detect", "--dry-run"]),
    *[(script, [*args, "--js"]) for script, _prog, args in ENTRYPOINTS],
])
@pytest.mark.parametrize("json_output", [False, True])
def test_parser_errors_have_consistent_output(env, script, args, json_output):
    proc = run(env, script, *(["--json"] if json_output else []), *args)
    assert proc.returncode == 2 and proc.stderr.startswith("error:")
    assert "Traceback" not in proc.stderr
    if json_output:
        data = json.loads(proc.stdout)
        assert proc.stdout.count("\n") == 1 and data["ok"] is False
        assert data["mode"] is None and data["records"] == []
        assert data["errors"] == [proc.stderr.strip()]
    else:
        assert proc.stdout == ""


@pytest.mark.parametrize("script,prog,args", ENTRYPOINTS[:4])
def test_deploy_dry_run_still_works(env, tmp_path, script, prog, args):
    extra = ["--harness", "claude"] if script != "render_hermes.py" else []
    proc = run(env, script, "--json", "--deploy", "--dry-run", *extra)
    data = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stderr
    assert data["mode"] == "deploy" and data["dry_run"] is True
    assert data["actions"]
    assert not Path(env["HOME"]).exists()


@pytest.mark.parametrize("script,prog,args", ENTRYPOINTS)
@pytest.mark.parametrize("json_output", [False, True])
def test_direct_entrypoints_reject_old_python(env, script, prog, args, json_output):
    probe = "import runpy, sys; sys.version_info = (3, 10, 0); sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')"
    proc = subprocess.run(
        [sys.executable, "-c", probe, str(SCRIPTS / script), *(["--json"] if json_output else [])],
        env=env, capture_output=True, text=True,
    )
    assert proc.returncode == 3 and proc.stderr.startswith(f"error: {prog}:")
    assert "Python 3.11+" in proc.stderr and "Traceback" not in proc.stderr
    if json_output:
        data = json.loads(proc.stdout)
        assert proc.stdout.count("\n") == 1 and data["ok"] is False
        assert data["mode"] is None and data["records"] == []
        assert data["errors"] == [proc.stderr.strip()]
    else:
        assert proc.stdout == ""


@pytest.mark.parametrize("wrapper", ["sync-ai-prompts", "render-agents", "render-invariants", "render-hermes", "update"])
@pytest.mark.parametrize("shell", ["bash", "pwsh"])
def test_launchers_follow_symlink_chains(env, tmp_path, wrapper, shell):
    if os.name == "nt" and shell == "bash":
        pytest.skip("native Windows launchers use PowerShell")
    executable = shutil.which(shell)
    if executable is None:
        pytest.skip(f"{shell} is not installed")
    suffix = ".ps1" if shell == "pwsh" else ""
    directory = tmp_path / "linked launchers"
    directory.mkdir()
    first = directory / f"first{suffix}"
    first.symlink_to(SCRIPTS / f"{wrapper}{suffix}")
    entry = directory / f"entry{suffix}"
    entry.symlink_to(first.name)
    env["AGENTS_PYTHON"] = sys.executable
    command = [executable, str(entry), "--help"] if shell == "bash" else [
        executable, "-NoProfile", "-File", str(entry), "--help",
    ]
    proc = subprocess.run(command, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "usage:" in proc.stdout and "--repo-root" in proc.stdout


@pytest.mark.parametrize("wrapper", ["sync-ai-prompts", "render-agents", "render-hermes", "render-invariants", "update"])
@pytest.mark.parametrize("shell", ["bash", "pwsh"])
def test_launcher_errors_have_mode_and_records(env, tmp_path, wrapper, shell):
    executable = shutil.which(shell)
    if executable is None:
        pytest.skip(f"{shell} not installed")
    env["AGENTS_PYTHON"] = str(tmp_path / "missing-python")
    command = [executable, str(SCRIPTS / wrapper), "--json"] if shell == "bash" else [
        executable, "-NoProfile", "-File", str(SCRIPTS / f"{wrapper}.ps1"), "--json",
    ]
    proc = subprocess.run(command, env=env, capture_output=True, text=True)
    data = json.loads(proc.stdout)
    assert proc.returncode == 3 and proc.stdout.count("\n") == 1
    assert data["ok"] is False and data["mode"] is None and data["records"] == []
    assert data["errors"] == [proc.stderr.strip()]
