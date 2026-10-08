import os
import subprocess

import check_docs_links as cdl

# The "--target" literal exists so the flag check has a defined flag for scripts/sync-ai-prompts.
FILES = {
    "README.md": "# Readme\n",
    "INSTALL.md": "# Install\n\n## Setup steps\n",
    "CHANGELOG.md": "# Changelog\n",
    "prompts/core.md": "core\n",
    "scripts/sync-ai-prompts": "#!/bin/sh\nexec python scripts/render_prompts.py\n",
    "scripts/render_prompts.py": '"--target"\n',
}


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def write(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "commit.gpgsign", "false")
    for rel, text in FILES.items():
        write(repo, rel, text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "files")
    return repo


def run(repo, capsys):
    capsys.readouterr()
    code = cdl.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def test_clean_repo_passes(tmp_path, capsys):
    code, out = run(make_repo(tmp_path), capsys)
    assert code == 0, out
    assert "Docs links check passed" in out


def test_broken_links_and_anchors(tmp_path, capsys):
    repo = make_repo(tmp_path)
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


def test_underscore_slug_anchor_passes(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "INSTALL.md", "# Install\n\n## render_prompts.py usage\n")
    write(repo, "README.md", "# Readme\n\n[x](INSTALL.md#render_promptspy-usage)\n")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_links_in_fences_and_inline_code_are_ignored(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n```bash\n[x](nope.md)\n```\n\nInline `[x](nope.md)` here.\n")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_broken_link_in_prompts_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core [x](nope.md)\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "prompts/core.md:1:" in out


def test_doc_command_flags_are_checked(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/sync-ai-prompts --bogus\n```\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "does not define flag '--bogus'" in out
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/sync-ai-prompts --target claude\n```\n")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_backslash_continuation_flags_are_checked(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/sync-ai-prompts \\\n  --bogus\n```\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "README.md:4:" in out
    assert "does not define flag '--bogus'" in out


def test_flag_prefix_is_not_a_match(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/sync-ai-prompts --targ\n```\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "does not define flag '--targ'" in out


def test_commands_in_changelog_are_ignored_but_not_in_readme(tmp_path, capsys):
    repo = make_repo(tmp_path)
    line = "```bash\nscripts/sync-ai-prompts --bogus\n```\n"
    write(repo, "CHANGELOG.md", f"# Changelog\n\n{line}")
    code, out = run(repo, capsys)
    assert code == 0, out
    write(repo, "README.md", f"# Readme\n\n{line}")
    code, out = run(repo, capsys)
    assert code == 1
    assert "README.md:" in out


def test_commands_in_prompts_fences_are_ignored(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "prompts/core.md", "core\n\n```bash\nscripts/sync-ai-prompts --bogus\n```\n")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_url_scheme_links_are_skipped(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n[a](https://example.com/x) [b](mailto:a@example.com)\n")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_directory_links_pass(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "docs/x.md", "# X\n\n[up](../README.md)\n")
    write(repo, "README.md", "# Readme\n\n[s](scripts/) [root](./)\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docs")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_duplicate_heading_anchors(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "INSTALL.md", "# Install\n\n## Setup\n\n## Setup\n")
    write(repo, "README.md", "# Readme\n\n[a](INSTALL.md#setup) [b](INSTALL.md#setup-1)\n")
    code, out = run(repo, capsys)
    assert code == 0, out
    write(repo, "README.md", "# Readme\n\n[c](INSTALL.md#setup-2)\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "anchor '#setup-2' not found" in out


def test_html_anchor_tag_works(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "INSTALL.md", '# Install\n\n<a id="custom"></a>\n')
    write(repo, "README.md", "# Readme\n\n[x](INSTALL.md#custom)\n")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_command_naming_missing_script_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/nope --x\n```\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "missing script 'scripts/nope'" in out


def test_flag_check_resets_after_and(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/sync-ai-prompts --target x && echo --bogus\n```\n")
    code, out = run(repo, capsys)
    assert code == 0, out


def test_unbalanced_quote_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", '# Readme\n\n```bash\nscripts/sync-ai-prompts --target "x\n```\n')
    code, out = run(repo, capsys)
    assert code == 1
    assert "cannot parse script command" in out


def test_continuation_at_end_of_fence_is_checked(tmp_path, capsys):
    repo = make_repo(tmp_path)
    write(repo, "README.md", "# Readme\n\n```bash\nscripts/sync-ai-prompts --bogus \\\n```\n")
    code, out = run(repo, capsys)
    assert code == 1
    assert "README.md:4:" in out
    assert "does not define flag '--bogus'" in out


def test_tracked_doc_missing_from_work_tree_is_reported(tmp_path, capsys):
    repo = make_repo(tmp_path)
    os.remove(repo / "INSTALL.md")
    code, out = run(repo, capsys)
    assert code == 1
    assert "INSTALL.md: tracked but missing from the work tree" in out
    assert "Traceback" not in out
