import subprocess
from pathlib import Path

import check_docs_impact as cdi

NOTE = "Describe the new prompt rule in the README"
MIGRATION = "Back up the config, upgrade by rerunning deploy, roll back by restoring the backup"
REGISTRY = 'HARNESSES = (\n    Harness(\n        "claude",\n    ),\n    Harness(\n        "codex",\n    ),\n)\n"--target"\n'
FILES = {
    "README.md": "# Readme\n",
    "INSTALL.md": "# Install\n\n## Setup steps\n",
    "SECURITY.md": "# Security\n",
    "CHANGELOG.md": "# Changelog\n\n## [1.0.0] - 2026-01-01\n",
    "docs/surfaces.md": "# Surfaces\n",
    "docs/harness-contract.md": "# Contract\n",
    "docs/legacy-harnesses.md": "# Legacy\n",
    "docs/MAINTENANCE.md": "# Maintenance\n",
    "prompts/core.md": "core v1\n",
    "scripts/render_prompts.py": REGISTRY,
    "scripts/sync-ai-prompts": "#!/bin/sh\nexec python scripts/render_prompts.py\n",
    "scripts/check_x.py": "print('x')\n",
}


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def write(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo, msg):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def bare_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "commit.gpgsign", "false")
    for rel, text in FILES.items():
        write(repo, rel, text)
    return repo


def make_repo(tmp_path):
    repo = bare_repo(tmp_path)
    base = commit(repo, "files")
    assert cdi.main(["--repo-root", str(repo), "--init", "--note", "Initial baseline for the fixture repository docs"]) == 0
    commit(repo, "lock")
    return repo, base


def run(repo, capsys, *args):
    capsys.readouterr()
    code = cdi.main(["--repo-root", str(repo), *args])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def accept_prompts(repo, capsys, *extra, docs="README.md", breaking="none"):
    return run(repo, capsys, "--accept", "prompts", "--docs", docs, "--note", NOTE, "--breaking", breaking, *extra)


def test_clean_baseline_passes(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    code, out = run(repo, capsys)
    assert code == 0, out
    assert "Docs impact check passed" in out


def test_source_change_without_receipt_fails(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core v2\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "prompts: sources changed" in out


def test_accept_with_docs_passes_and_range_sees_doc_change(tmp_path, capsys):
    repo, base = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core v2\n")
    write(repo, "README.md", "# Readme\n\nNew prompt rule.\n")
    code, out = accept_prompts(repo, capsys)
    assert code == 0, out
    assert run(repo, capsys)[0] == 0
    code, out = run(repo, capsys, "--base", base)
    assert code == 0, out


def test_stale_receipt_fails_after_further_edit(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core v2\n")
    assert accept_prompts(repo, capsys)[0] == 0
    write(repo, "prompts/core.md", "core v3\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "prompts: sources changed" in out


def test_receipt_citing_unchanged_doc_fails_range(tmp_path, capsys):
    repo, base = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core v2\n")
    assert accept_prompts(repo, capsys)[0] == 0
    code, out = run(repo, capsys, "--base", base)
    assert code == 1
    assert "did not change since" in out


def test_no_impact_must_be_specific(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core v2\n")
    code, _ = run(repo, capsys, "--accept", "prompts", "--no-impact", "docs reviewed", "--breaking", "none")
    assert code == 2
    reason = "Typo fix in prompt wording only, no behavior or documented surface changed"
    code, out = run(repo, capsys, "--accept", "prompts", "--no-impact", reason, "--breaking", "none")
    assert code == 0, out
    assert run(repo, capsys)[0] == 0


def test_breaking_receipt_requirements(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core v2\n")
    code, _ = accept_prompts(repo, capsys, docs="CHANGELOG.md,README.md", breaking="x is removed")
    assert code == 2
    code, _ = accept_prompts(repo, capsys, "--migration", MIGRATION, docs="README.md", breaking="x is removed")
    assert code == 2
    code, out = accept_prompts(
        repo, capsys, "--migration", MIGRATION, docs="CHANGELOG.md,README.md", breaking="x is removed"
    )
    assert code == 0, out


def test_superseded_breaking_receipt_fails_range(tmp_path, capsys):
    repo, base = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core v2\n")
    write(repo, "README.md", "# Readme\n\nv2\n")
    write(repo, "CHANGELOG.md", FILES["CHANGELOG.md"] + "\nBreaking.\n")
    code, out = accept_prompts(
        repo, capsys, "--migration", MIGRATION, docs="CHANGELOG.md,README.md", breaking="x is removed"
    )
    assert code == 0, out
    commit(repo, "breaking")
    write(repo, "prompts/core.md", "core v3\n")
    assert accept_prompts(repo, capsys)[0] == 0
    commit(repo, "none")
    code, out = run(repo, capsys, "--base", base)
    assert code == 1
    assert "recorded a breaking change" in out


def test_removed_harness_needs_breaking_receipt(tmp_path, capsys):
    repo, base = make_repo(tmp_path)
    write(repo, "scripts/render_prompts.py", REGISTRY.replace('    Harness(\n        "codex",\n    ),\n', ""))
    write(repo, "README.md", "# Readme\n\ncodex gone\n")
    code, out = run(
        repo, capsys, "--accept", "harnesses", "--docs", "README.md", "--note", NOTE, "--breaking", "none"
    )
    assert code == 0, out
    code, out = run(repo, capsys, "--base", base)
    assert code == 1
    assert "removed codex" in out


def test_unmapped_tracked_file_fails_but_untracked_is_ignored(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    write(repo, "scripts/new_tool.py", "print('new')\n")
    code, out = run(repo, capsys)
    assert code == 0, out
    git(repo, "add", "scripts/new_tool.py")
    code, out = run(repo, capsys)
    assert code == 1
    assert "not covered by any docs domain" in out


def test_broken_links_and_anchors(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n[ok](INSTALL.md#setup-steps)\n")
    assert run(repo, capsys)[0] == 0
    write(repo, "README.md", "# Readme\n\n[x](docs/nope.md)\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "docs/nope.md" in out
    write(repo, "README.md", "# Readme\n\n[x](INSTALL.md#missing)\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "anchor '#missing' not found" in out


def test_doc_command_flags_are_checked(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/sync-ai-prompts --bogus\n```\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "does not define flag '--bogus'" in out
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/sync-ai-prompts --target claude\n```\n")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_release_tag_needs_dated_changelog_section(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    assert run(repo, capsys, "--release-tag", "v1.0.0")[0] == 0
    code, out = run(repo, capsys, "--release-tag", "v9.9.9")
    assert code == 1
    assert "no dated" in out


def test_accept_without_lock_and_double_init_are_tool_errors(tmp_path, capsys):
    repo = bare_repo(tmp_path)
    commit(repo, "files")
    code, out = run(repo, capsys, "--accept", "prompts", "--no-impact", "x", "--breaking", "none")
    assert code == 2
    assert "is missing" in out
    repo2, _ = make_repo(tmp_path / "second")
    code, out = run(repo2, capsys, "--init", "--note", "Initial baseline for the fixture repository docs")
    assert code == 2
    assert "already exists" in out


def test_unknown_base_revision_is_tool_error(tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    code, out = run(repo, capsys, "--base", "no-such-rev")
    assert code == 2
    assert "ERROR" in out
