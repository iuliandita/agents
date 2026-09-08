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
