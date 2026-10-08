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


def test_checkouts_do_not_persist_credentials():
    repo = Path(__file__).resolve().parents[1]
    for workflow in sorted((repo / ".github" / "workflows").glob("*.yml")):
        lines = workflow.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "uses: actions/checkout@" in line:
                block = "\n".join(lines[index + 1 : index + 4])
                assert "persist-credentials: false" in block, f"{workflow.name}:{index + 1}"


def test_dependabot_waits_before_proposing_releases():
    repo = Path(__file__).resolve().parents[1]
    config = (repo / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert config.count("default-days: 7") == 2


def test_ci_smoke_tests_powershell_launchers_on_windows():
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "runs-on: windows-" in workflow
    assert "./scripts/sync-ai-prompts.ps1 --target claude --check" in workflow
