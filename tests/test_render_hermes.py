from pathlib import Path

import render_hermes as rh


REPO = Path(__file__).resolve().parents[1]


def test_merge_inserts_into_existing_agent_block_preserving_comments():
    text = "# top\nmodel:\n  default: x\n# between\nagent:\n  reasoning_effort: medium\n_config_version: 44\n"

    merged = rh.merge_coding_instructions(text, "- rule\n")

    assert "# top" in merged and "# between" in merged
    assert "  coding_instructions: |" in merged
    assert "    - rule" in merged
    assert "  reasoning_effort: medium" in merged
    assert "_config_version: 44" in merged


def test_merge_is_idempotent():
    once = rh.merge_coding_instructions("agent:\n  reasoning_effort: medium\n", "- rule\n")
    assert rh.merge_coding_instructions(once, "- rule\n") == once


def test_merge_replaces_inline_and_block_values():
    inline = "agent:\n  coding_instructions: old\n  reasoning_effort: low\n"
    replaced = rh.merge_coding_instructions(inline, "- new\n")

    assert "old" not in replaced
    assert "  reasoning_effort: low" in replaced

    block = rh.merge_coding_instructions(replaced, "- newer\n")
    assert "- new\n" not in block
    assert "    - newer" in block
    assert "  reasoning_effort: low" in block


def test_merge_appends_agent_key_when_missing():
    merged = rh.merge_coding_instructions("model:\n  default: x\n", "- rule\n")
    assert "agent:\n  coding_instructions: |" in merged


def test_merge_handles_empty_config():
    merged = rh.merge_coding_instructions("", "- rule\n")
    assert merged.startswith("agent:\n  coding_instructions: |")


def test_hermes_config_path_precedence():
    assert rh.hermes_config_path({"HERMES_CONFIG_PATH": "/x/c.yaml"}) == Path("/x/c.yaml")
    assert rh.hermes_config_path({"HERMES_HOME": "/h"}) == Path("/h/config.yaml")


def test_render_rules_contains_core_and_fragment():
    rules = rh.render_rules(REPO)
    assert "Global Preferences" in rules
    assert "## Hermes Notes" in rules


def test_deploy_merges_and_backs_up(tmp_path):
    config = tmp_path / "hermes" / "config.yaml"
    config.parent.mkdir()
    config.write_text("agent:\n  reasoning_effort: medium\n", encoding="utf-8")
    backup_dir = tmp_path / "backups"

    assert rh.deploy(REPO, config, backup_dir, dry_run=False) == 0
    assert "coding_instructions: |" in config.read_text(encoding="utf-8")
    assert list(backup_dir.iterdir())


def test_deploy_dry_run_writes_nothing(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("agent:\n  reasoning_effort: medium\n", encoding="utf-8")
    before = config.read_text(encoding="utf-8")

    assert rh.deploy(REPO, config, tmp_path / "b", dry_run=True) == 0
    assert config.read_text(encoding="utf-8") == before
    assert not (tmp_path / "b").exists()


def overlay_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "prompts" / "harnesses").mkdir(parents=True)
    (repo / "prompts" / "core.md").write_text("# Core\nshared\n", encoding="utf-8")
    (repo / "prompts" / "harnesses" / "hermes.md").write_text("## Hermes\nx\n", encoding="utf-8")
    (repo / "prompts" / "local.md").write_text("local layer\n", encoding="utf-8")
    (repo / "prompts" / "private.md").write_text("private layer\n", encoding="utf-8")
    return repo


def test_render_rules_adds_local_and_withholds_untrusted_private(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("AGENTS_PRIVATE_HARNESSES", raising=False)
    rules = rh.render_rules(overlay_repo(tmp_path))
    assert "local layer" in rules
    assert "private layer" not in rules
    assert "withheld from hermes" in capsys.readouterr().out


def test_render_rules_includes_private_when_trusted(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTS_PRIVATE_HARNESSES", "hermes")
    rules = rh.render_rules(overlay_repo(tmp_path))
    assert rules.index("local layer") < rules.index("private layer")
