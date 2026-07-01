import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import render_invariants as ri


REPO = Path(__file__).resolve().parents[1]


def test_invariants_source_exists_and_is_nonempty():
    invariants = ri.read_invariants(REPO)
    assert "Hard Invariants" in invariants
    assert "Never add AI attribution" in invariants


def test_render_all_writes_three_artifacts(tmp_path):
    written = ri.render_all(REPO, tmp_path, "$HOME/.claude/hooks/" + ri.HOOK_NAME)
    assert set(written) == {"hook", "settings", "subagent"}
    for path in written.values():
        assert path.exists()


def test_hook_is_executable_and_emits_invariants(tmp_path):
    written = ri.render_all(REPO, tmp_path, "$HOME/.claude/hooks/" + ri.HOOK_NAME)
    hook = written["hook"]
    text = hook.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "Never add AI attribution" in text
    assert hook.stat().st_mode & 0o111  # executable bit set


def test_settings_snippet_is_valid_json_userpromptsubmit(tmp_path):
    written = ri.render_all(REPO, tmp_path, "/custom/path.sh")
    data = json.loads(written["settings"].read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in data["hooks"]
    cmd = data["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert cmd["type"] == "command"
    assert cmd["command"] == "/custom/path.sh"


def test_subagent_block_carries_invariants(tmp_path):
    written = ri.render_all(REPO, tmp_path, "unused")
    text = written["subagent"].read_text(encoding="utf-8")
    assert "subagent" in text.lower()
    assert "Do only what was asked" in text


def test_merge_is_idempotent():
    settings, changed = ri.merge_hook_into_settings({}, "/h.sh")
    assert changed is True
    again, changed2 = ri.merge_hook_into_settings(settings, "/h.sh")
    assert changed2 is False
    assert len(again["hooks"]["UserPromptSubmit"]) == 1


def test_merge_preserves_existing_hooks():
    existing = {
        "hooks": {
            "UserPromptSubmit": [
                {"hooks": [{"type": "command", "command": "/caveman.sh"}]}
            ],
            "PreToolUse": [{"matcher": "Bash", "hooks": []}],
        }
    }
    merged, changed = ri.merge_hook_into_settings(existing, "/invariants.sh")
    assert changed is True
    commands = [
        h["command"]
        for entry in merged["hooks"]["UserPromptSubmit"]
        for h in entry["hooks"]
    ]
    assert commands == ["/caveman.sh", "/invariants.sh"]
    assert "PreToolUse" in merged["hooks"]
    # original object untouched
    assert len(existing["hooks"]["UserPromptSubmit"]) == 1


def test_load_settings_handles_missing_empty_and_bad(tmp_path):
    assert ri.load_settings(tmp_path / "nope.json") == {}
    empty = tmp_path / "empty.json"
    empty.write_text("   ", encoding="utf-8")
    assert ri.load_settings(empty) == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    try:
        ri.load_settings(bad)
        assert False, "expected SystemExit on invalid JSON"
    except SystemExit:
        pass


def test_deploy_installs_hook_and_merges_settings(tmp_path):
    hooks_dir = tmp_path / "hooks"
    settings_path = tmp_path / "settings.json"
    backup_dir = tmp_path / "backups"

    ri.deploy(REPO, hooks_dir, settings_path, backup_dir, dry_run=False)

    hook = hooks_dir / ri.HOOK_NAME
    assert hook.exists() and hook.stat().st_mode & 0o111
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    cmd = data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert cmd == str(hook)

    # second deploy is idempotent: still one entry, no duplicate
    ri.deploy(REPO, hooks_dir, settings_path, backup_dir, dry_run=False)
    data2 = json.loads(settings_path.read_text(encoding="utf-8"))
    assert len(data2["hooks"]["UserPromptSubmit"]) == 1


def test_deploy_merges_into_existing_settings_without_clobber(tmp_path):
    hooks_dir = tmp_path / "hooks"
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"model": "opus", "hooks": {"UserPromptSubmit": [
            {"hooks": [{"type": "command", "command": "/caveman.sh"}]}
        ]}}),
        encoding="utf-8",
    )
    ri.deploy(REPO, hooks_dir, settings_path, tmp_path / "b", dry_run=False)
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert data["model"] == "opus"
    cmds = [h["command"] for e in data["hooks"]["UserPromptSubmit"] for h in e["hooks"]]
    assert "/caveman.sh" in cmds and str(hooks_dir / ri.HOOK_NAME) in cmds


def test_dry_run_writes_nothing(tmp_path):
    hooks_dir = tmp_path / "hooks"
    settings_path = tmp_path / "settings.json"
    ri.deploy(REPO, hooks_dir, settings_path, tmp_path / "b", dry_run=True)
    assert not hooks_dir.exists()
    assert not settings_path.exists()
