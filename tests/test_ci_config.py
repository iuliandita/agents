from pathlib import Path

import pytest


def test_release_workflow_creates_a_release_on_version_tags():
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert 'tags:' in workflow
    assert '"v*"' in workflow
    assert "gh release create" in workflow
    assert "contents: write" in workflow


def test_checkouts_do_not_persist_credentials():
    repo = Path(__file__).resolve().parents[1]
    for workflow in sorted((repo / ".github" / "workflows").glob("*.yml")):
        lines = workflow.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "uses: actions/checkout@" in line:
                block = "\n".join(lines[index + 1 : index + 4])
                assert "persist-credentials: false" in block, f"{workflow.name}:{index + 1}"


def test_ci_smoke_tests_powershell_launchers_on_windows():
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "runs-on: windows-" in workflow
    assert "./scripts/sync-ai-prompts.ps1 --target claude --check" in workflow


def load_workflow(name):
    import yaml

    repo = Path(__file__).resolve().parents[1]
    return yaml.safe_load((repo / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def test_ci_and_security_run_on_develop_and_main_with_shared_job_ids():
    for name, jobs in (("ci.yml", {"lint", "test"}), ("security.yml", {"secrets", "zizmor"})):
        workflow = load_workflow(name)
        assert workflow[True]["push"]["branches"] == ["develop", "main"]
        assert jobs <= set(workflow["jobs"])
        for job_id in jobs:
            assert workflow["jobs"][job_id]["name"] == job_id


RELEASE_CHANGELOG = """# Changelog

## [Unreleased]

- Not released yet.

## [1.2.0] - 2026-10-01

### Added

- The new thing.

## [1.1.0] - 2026-09-01

- Older.

[Unreleased]: https://example.test/compare/v1.2.0...HEAD
[1.2.0]: https://example.test/compare/v1.1.0...v1.2.0
"""


def run_release_notes_step(tmp_path, tag, changelog=RELEASE_CHANGELOG):
    import subprocess

    steps = load_workflow("release.yml")["jobs"]["release"]["steps"]
    step = next(s for s in steps if s["name"] == "Extract release notes from the changelog")
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    env = {"PATH": "/usr/bin:/bin", "GITHUB_REF_NAME": tag, "RUNNER_TEMP": str(tmp_path)}
    result = subprocess.run(["bash", "-c", step["run"]], cwd=tmp_path, env=env, capture_output=True, text=True)
    return result, tmp_path / "notes.md"


def test_release_notes_come_from_the_tagged_changelog_section(tmp_path):
    result, notes = run_release_notes_step(tmp_path, "v1.2.0")
    assert result.returncode == 0, result.stdout
    text = notes.read_text(encoding="utf-8")
    assert "The new thing." in text
    assert "Older." not in text and "Not released yet." not in text and "example.test" not in text


def test_release_notes_step_fails_without_a_section_for_the_tag(tmp_path):
    result, _ = run_release_notes_step(tmp_path, "v9.9.9")
    assert result.returncode == 1
    assert "no notes for 9.9.9" in result.stdout


def test_stack_conventions_step_is_blocking():
    steps = load_workflow("ci.yml")["jobs"]["lint"]["steps"]
    step = next(s for s in steps if s["name"] == "Check stack conventions")
    assert step["run"] == "python3 .github/stack/stack-check.py"
    assert "continue-on-error" not in step


def test_release_notes_extract_from_the_real_changelog(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    result, notes = run_release_notes_step(tmp_path, "v4.3.0", (repo / "CHANGELOG.md").read_text(encoding="utf-8"))
    assert result.returncode == 0, result.stdout
    text = notes.read_text(encoding="utf-8")
    assert "omit_sections" in text
    assert "## [" not in text and "compare/" not in text


@pytest.mark.parametrize("ci,security", [("success", "success"), ("failure", "success"), ("success", "cancelled"), ("missing", "success")])
def test_release_requires_successful_checks_for_the_tagged_commit(tmp_path, ci, security):
    import os
    import subprocess

    steps = load_workflow("release.yml")["jobs"]["release"]["steps"]
    step = next(s for s in steps if s["name"] == "Require successful CI for the tagged commit")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    commands = {
        "git": '#!/bin/sh\nprintf "%s\\n" tagged-commit\n',
        "gh": '#!/bin/sh\nprintf "%s\\n" "$*" >> "$REQUESTS"\ncase "$*" in\n  *ci.yml*) echo "$CI_RESULT";;\n  *) echo "$SECURITY_RESULT";;\nesac\n',
    }
    for name, body in commands.items():
        path = bin_dir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    requests = tmp_path / "requests"
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}", REQUESTS=str(requests),
               GITHUB_REF_NAME="v1.0.0", GITHUB_REPOSITORY="example/repo", CI_RESULT=ci, SECURITY_RESULT=security)
    result = subprocess.run(["bash", "-e", "-c", step["run"]], env=env, capture_output=True, text=True)
    assert result.returncode == (0 if ci == security == "success" else 1), result.stdout + result.stderr
    calls = requests.read_text(encoding="utf-8").splitlines()
    assert all("-f head_sha=tagged-commit -f event=push -f branch=main" in call for call in calls)


@pytest.fixture
def stack_checker(monkeypatch):
    import importlib.util
    import sys

    source = Path(__file__).resolve().parents[1] / ".github" / "stack" / "stack-check.py"
    spec = importlib.util.spec_from_file_location("stack_checker", source)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("version", [None, 0, 2, True])
def test_stack_rejects_missing_or_unsupported_canon_version(tmp_path, monkeypatch, stack_checker, version):
    canon = stack_checker.load_json("canon.json")
    canon["canon_version"] = version
    monkeypatch.setattr(stack_checker, "load_json", lambda name: canon if name == "canon.json" else {"repo": "fixture"})
    args = stack_checker.build_parser().parse_args(["--root", str(tmp_path), "--only", "private-patterns"])
    with pytest.raises(stack_checker.UsageError, match="canon_version"):
        stack_checker.run(args)


@pytest.mark.parametrize("requirement", ["persist-credentials: true", "fetch-depth: 3"])
def test_stack_checkout_uses_configured_key_and_value(tmp_path, stack_checker, requirement):
    canon = stack_checker.load_json("canon.json")
    canon["workflows"]["checkout_require"] = requirement
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    key, value = requirement.split(": ")
    workflow.write_text(f"jobs:\n  test:\n    steps:\n      - uses: actions/checkout@{'a' * 40}\n        with:\n          {key}: '{value}' # configured\n", encoding="utf-8")
    ctx = stack_checker.Ctx(tmp_path, canon, {})
    assert stack_checker.check_workflow_checkout(ctx) == []
    workflow.write_text(workflow.read_text().replace(f"'{value}'", "false"), encoding="utf-8")
    findings = stack_checker.check_workflow_checkout(stack_checker.Ctx(tmp_path, canon, {}))
    assert len(findings) == 1 and requirement in findings[0].message


@pytest.mark.parametrize("git_checkout", [False, True])
def test_stack_directory_exclusions_apply_at_every_depth(tmp_path, stack_checker, git_checkout):
    import subprocess

    canon = stack_checker.load_json("canon.json")
    canon["private_patterns"]["skip_dirs"].append("custom-skip")
    for relative in ("local/private.txt", "nested/local/private.txt", "nested/custom-skip/private.txt"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("host " + "192.168." + "1.1", encoding="utf-8")
    if git_checkout:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    ctx = stack_checker.Ctx(tmp_path, canon, {})
    assert stack_checker.check_private_patterns(ctx) == []
    if not git_checkout:
        assert not any(name.endswith("private.txt") for name in ctx.files)
    (tmp_path / "public.txt").write_text("host " + "192.168." + "1.1", encoding="utf-8")
    findings = stack_checker.check_private_patterns(stack_checker.Ctx(tmp_path, canon, {}))
    assert len(findings) == 1 and findings[0].file == "public.txt"


def test_stack_rejects_root_paths_and_exempts_reusable_workflow_timeouts(tmp_path, stack_checker):
    canon = stack_checker.load_json("canon.json")
    (tmp_path / "notes.txt").write_text("path /ro" + "ot/private", encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("jobs:\n  reusable:\n    uses: ./.github/workflows/shared.yml\n  ordinary:\n    runs-on: ubuntu-latest\n    steps: []\n", encoding="utf-8")
    ctx = stack_checker.Ctx(tmp_path, canon, {})
    private = stack_checker.check_private_patterns(ctx)
    assert len(private) == 1 and "root-path" in private[0].message
    timeouts = stack_checker.check_workflow_timeouts(ctx)
    assert len(timeouts) == 1 and '"ordinary"' in timeouts[0].message


def test_documented_skill_installer_covers_every_bundled_skill(tmp_path):
    import json
    import subprocess
    import sys

    repo = Path(__file__).resolve().parents[1]
    target = tmp_path / "installed-skills"
    result = subprocess.run(
        [sys.executable, str(repo / "scripts" / "install_workflow.py"), "--skills-dir", str(target), "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    actions = json.loads(result.stdout)["actions"]
    expected = {target / source.relative_to(repo / "skills") for source in (repo / "skills").rglob("SKILL.md")}
    assert expected
    assert {Path(action["path"]) for action in actions} == expected
