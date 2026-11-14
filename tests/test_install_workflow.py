from pathlib import Path

import pytest

import install_workflow


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    source = root / "skills" / "consolidate-agents-md" / "SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nname: consolidate-agents-md\ndescription: Consolidate instructions\n---\nBody\n")
    monkeypatch.setattr(install_workflow, "REPO_ROOT", root)
    return root


def destination(directory: Path) -> Path:
    return directory / "consolidate-agents-md" / "SKILL.md"


def test_dry_run_does_not_write(repo, tmp_path):
    skills = tmp_path / "new skills"
    legacy = tmp_path / "old.md"
    legacy.write_text("private old content")
    assert install_workflow.main(["--skills-dir", str(skills), "--legacy-command", str(legacy)]) == 0
    assert not skills.exists()
    assert legacy.read_text() == "private old content"
    assert not (repo / ".backups").exists()


def test_deploy_copies_all_and_is_idempotent(repo, tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    legacy = tmp_path / "commands" / "consolidate.md"
    args = ["--skills-dir", str(first), "--skills-dir", str(second),
            "--legacy-command", str(legacy), "--deploy"]
    assert install_workflow.main(args) == 0
    source = destination(repo / "skills")
    for target in (destination(first), destination(second), legacy):
        assert target.read_bytes() == source.read_bytes()
        assert not target.is_symlink()
    assert install_workflow.main(args) == 0
    assert not (repo / ".backups").exists()


def test_overwrite_preserves_private_backups(repo, tmp_path, capsys):
    skills = tmp_path / "skills"
    target = destination(skills)
    target.parent.mkdir(parents=True)
    target.write_text("private skill")
    legacy = tmp_path / "command.md"
    legacy.write_text("private command")
    args = ["--skills-dir", str(skills), "--legacy-command", str(legacy), "--deploy"]
    assert install_workflow.main(args) == 0
    backups = list((repo / ".backups").glob("workflow-*"))
    assert len(backups) == 1
    assert backups[0].stat().st_mode & 0o777 == 0o700
    assert {item.read_text() for item in backups[0].iterdir()} == {"private skill", "private command"}
    assert install_workflow.main(args) == 0
    assert list((repo / ".backups").iterdir()) == backups
    assert "private skill" not in capsys.readouterr().out


@pytest.mark.parametrize("collision", ["ancestor_link", "file_link", "directory", "ancestor_file", "legacy_directory"])
def test_late_invalid_target_prevents_all_writes(repo, tmp_path, collision):
    first = tmp_path / "first"
    second = tmp_path / "second"
    args = ["--skills-dir", str(first), "--deploy"]
    if collision == "ancestor_link":
        second.symlink_to(repo, target_is_directory=True)
    elif collision == "ancestor_file":
        second.write_text("keep")
    else:
        destination(second).parent.mkdir(parents=True)
        if collision == "file_link":
            destination(second).symlink_to(tmp_path / "missing")
        else:
            destination(second).mkdir()
    if collision == "legacy_directory":
        args += ["--legacy-command", str(destination(second))]
    else:
        args += ["--skills-dir", str(second)]
    assert install_workflow.main(args) == 1
    assert not first.exists()
    assert not (repo / ".backups").exists()


def test_invalid_source_prevents_writes(repo, tmp_path):
    destination(repo / "skills").write_text("---\nname: wrong\ndescription: test\n---\n")
    target = tmp_path / "target"
    assert install_workflow.main(["--skills-dir", str(target), "--deploy"]) == 1
    assert not target.exists()


def test_workflow_backups_prune_per_source_and_remove_empty_bundles(repo, tmp_path):
    from render_prompts import prune_backups

    skills = tmp_path / "skills"
    target = destination(skills)
    target.parent.mkdir(parents=True)
    for index in range(3):
        target.write_text(str(index))
        assert install_workflow.main(["--skills-dir", str(skills), "--deploy"]) == 0
    backup_root = repo / ".backups"
    assert len(list(backup_root.glob("workflow-*"))) == 3
    assert prune_backups(backup_root, 1, False) == 0
    remaining = list(backup_root.glob("workflow-*"))
    assert len(remaining) == 1
    assert [path.read_text() for path in remaining[0].iterdir()] == ["2"]


def test_workflow_backups_cap_long_destination_names(repo, tmp_path):
    target = tmp_path / ("command" * 30 + ".md")
    target.write_text("old command")
    assert install_workflow.main([
        "--skills-dir", str(tmp_path / "skills"), "--legacy-command", str(target), "--deploy",
    ]) == 0
    backups = list((repo / ".backups").glob("workflow-*/*.bak"))
    assert len(backups) == 1 and len(backups[0].name) < 255
    assert backups[0].read_text() == "old command"
