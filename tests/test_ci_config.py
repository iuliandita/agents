from pathlib import Path


def test_ci_installs_python_test_dependencies_from_requirements_file():
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    requirements = (repo / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "python -m pip install -r requirements-dev.txt" in workflow
    assert "pytest>=" in requirements


def test_dependabot_tracks_github_actions_and_pip_dependencies():
    repo = Path(__file__).resolve().parents[1]
    config = (repo / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert 'package-ecosystem: "github-actions"' in config
    assert 'package-ecosystem: "pip"' in config


def test_release_workflow_creates_a_release_on_version_tags():
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert 'tags:' in workflow
    assert '"v*"' in workflow
    assert "gh release create" in workflow
    assert "contents: write" in workflow


def test_ci_runs_a_python_matrix():
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "matrix:" in workflow
    assert '"3.11"' in workflow
    assert '"3.13"' in workflow
