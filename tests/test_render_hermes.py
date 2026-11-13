from pathlib import Path

import pytest
import yaml

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


@pytest.mark.parametrize("comment", ["# settings\n", "\n# settings\n\n"])
def test_merge_finds_existing_instructions_after_column_zero_comments(comment):
    text = f"agent:\n  model: x\n{comment}  coding_instructions: old\nother: 1\n"

    merged = rh.merge_coding_instructions(text, "new\n")

    assert comment in merged
    assert yaml.safe_load(merged) == {"agent": {"model": "x", "coding_instructions": "new\n"}, "other": 1}
    assert merged.count("coding_instructions:") == 1


@pytest.mark.parametrize("agent", ["agent", '"agent"', "'agent'"])
@pytest.mark.parametrize("key", ["coding_instructions", '"coding_instructions"', "'coding_instructions'"])
def test_merge_recognizes_quoted_keys(agent, key):
    text = f"{agent}:\n    {key}: old\n    model: x\nother: 1\n"

    merged = rh.merge_coding_instructions(text, "new\n")

    assert merged.startswith(f"{agent}:\n")
    assert yaml.safe_load(merged) == {"agent": {"coding_instructions": "new\n", "model": "x"}, "other": 1}
    assert rh.merge_coding_instructions(merged, "new\n") == merged


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


@pytest.mark.parametrize(
    "existing",
    ["", "    coding_instructions: |\n        - old\n\n        - older\n", "    coding_instructions: old\n      wrapped\n"],
)
def test_merge_keeps_sibling_keys_in_four_space_agent_block(existing):
    text = f"agent:\n{existing}    model: opus\n    max_turns: 50\nother: 1\n"

    merged = yaml.safe_load(rh.merge_coding_instructions(text, "- rule\n\n- two\n"))

    assert merged["agent"] == {"coding_instructions": "- rule\n\n- two\n", "model": "opus", "max_turns": 50}
    assert merged["other"] == 1


@pytest.mark.parametrize("key", ["agent", '"agent"', "'agent'"])
def test_merge_refuses_inline_agent_value(key):
    with pytest.raises(SystemExit, match="inline value"):
        rh.merge_coding_instructions(f"{key}: {{model: opus}}\n", "- rule\n")


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


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("dangling", [False, True])
def test_deploy_refuses_symlinks_without_writing(tmp_path, dangling, dry_run):
    target = tmp_path / "target.yaml"
    original = "agent:\n  model: x\n"
    if not dangling:
        target.write_text(original, encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.symlink_to(target)

    with pytest.raises(SystemExit, match="error: .* is a symlink; refusing to write through it"):
        rh.deploy(REPO, config, tmp_path / "backups", dry_run=dry_run)

    assert config.is_symlink()
    assert target.exists() is not dangling
    if not dangling:
        assert target.read_text(encoding="utf-8") == original
    assert not (tmp_path / "backups").exists()


@pytest.mark.parametrize(
    "original",
    [
        'agent:\n  model: x\n"agent":\n  model: y\n',
        '"agent":\n  coding_instructions: old\n  \'coding_instructions\': older\n',
    ],
)
@pytest.mark.parametrize("dry_run", [False, True])
def test_deploy_refuses_duplicate_keys_without_writing(tmp_path, original, dry_run):
    config = tmp_path / "config.yaml"
    config.write_text(original, encoding="utf-8")

    with pytest.raises(SystemExit, match="error: duplicate agent or agent.coding_instructions keys"):
        rh.deploy(REPO, config, tmp_path / "backups", dry_run=dry_run)

    assert config.read_text(encoding="utf-8") == original
    assert not (tmp_path / "backups").exists()


def test_merge_refuses_loss_of_top_level_keys(monkeypatch):
    # Simulate an overlong replacement range to exercise the post-merge guard.
    monkeypatch.setattr(rh, "_block_end", lambda lines, start, min_indent: len(lines))

    with pytest.raises(SystemExit, match="error: merge removed top-level keys: other"):
        rh.merge_coding_instructions('agent:\n  coding_instructions: old\n"other": 1\n', "new\n")


def test_structure_ignores_nested_keys_and_scalar_contents():
    text = 'agent:\n  nested:\n    coding_instructions: keep\n  coding_instructions: |\n    agent:\n    coding_instructions: text\n"other": 1\n'

    merged = rh.merge_coding_instructions(text, "agent:\ncoding_instructions: text\n")

    assert yaml.safe_load(merged)["agent"]["nested"] == {"coding_instructions": "keep"}
    assert rh._structure(merged) == (["agent", "other"], 1)


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
    assert "withheld from hermes" in capsys.readouterr().err


def test_render_rules_includes_private_when_trusted(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTS_PRIVATE_HARNESSES", "hermes")
    rules = rh.render_rules(overlay_repo(tmp_path))
    assert rules.index("local layer") < rules.index("private layer")


@pytest.mark.parametrize("override", ["HERMES_CONFIG_PATH", "HERMES_HOME", None])
@pytest.mark.parametrize("git_marker", ["directory", "file", "absent"])
def test_environment_config_withholds_overlays_only_inside_work_tree(tmp_path, monkeypatch, capsys, override, git_marker):
    repo = overlay_repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    if git_marker == "directory":
        (home / ".git").mkdir()
    elif git_marker == "file":
        (home / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    config = home / ".hermes" / "config.yaml"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("AGENTS_PRIVATE_HARNESSES", "hermes")
    monkeypatch.delenv("HERMES_CONFIG_PATH", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    if override:
        monkeypatch.setenv(override, str(config if override == "HERMES_CONFIG_PATH" else config.parent))
    args = rh.parse_args(["--repo-root", str(repo), "--backup-dir", str(tmp_path / "backups")])
    args.deploy = True

    assert rh.run(args) == 0

    rules = yaml.safe_load(config.read_text(encoding="utf-8"))["agent"]["coding_instructions"]
    withheld = override is not None and git_marker != "absent"
    assert ("local layer" in rules) is not withheld
    assert ("private layer" in rules) is not withheld
    assert ("note: prompts/local.md and prompts/private.md withheld from hermes" in capsys.readouterr().err) is withheld


def test_work_tree_detection_resolves_parent_symlinks(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(repo, target_is_directory=True)
    assert rh._inside_work_tree(alias / "new" / "config.yaml")


def test_hermes_replace_failure_preserves_config_and_private_preview(tmp_path, monkeypatch):
    repo = overlay_repo(tmp_path)
    config = tmp_path / "config.yaml"
    original = "agent:\n  model: existing\n"
    config.write_text(original)
    replace = rh.os.replace

    def fail_config(source, target):
        if target == config:
            assert Path(source).parent == config.parent
            raise OSError("config replacement failed")
        replace(source, target)

    monkeypatch.setattr(rh.os, "replace", fail_config)
    with pytest.raises(OSError, match="replacement failed"):
        rh.deploy(repo, config, tmp_path / "backups", False)
    assert config.read_text() == original
    assert not list(tmp_path.glob(".agents-*"))
    preview = rh.render_preview(repo, tmp_path / "out")
    if rh.os.name != "nt":
        assert preview.stat().st_mode & 0o777 == 0o600


def test_hermes_directory_target_refused(tmp_path):
    config = tmp_path / "config.yaml"
    config.mkdir()
    with pytest.raises(SystemExit, match="not a regular file"):
        rh.deploy(REPO, config, tmp_path / "backups", False)

def test_dry_run_flags_unmanaged_coding_instructions(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("AGENTS_PRIVATE_HARNESSES", raising=False)
    config = tmp_path / "config.yaml"
    config.write_text("agent:\n  coding_instructions: my own rules\n", encoding="utf-8")
    rh.deploy(overlay_repo(tmp_path), config, tmp_path / "b", dry_run=True)
    assert "would replace unmanaged hermes agent.coding_instructions" in capsys.readouterr().out
