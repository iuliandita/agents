import importlib.util
import subprocess
from pathlib import Path

import pytest

import lint_prompts as linter


def test_lint_file_flags_private_path_marker(tmp_path):
    target = tmp_path / "core.md"
    target.write_text("Render from internal.example/prompt-core.md instead.\n", encoding="utf-8")

    failures = linter.lint_file(target, private_patterns=("internal.example",))

    assert failures == 1


def test_load_private_patterns_from_file(tmp_path):
    repo = tmp_path / "repo"
    (repo / "prompts").mkdir(parents=True)
    (repo / "prompts" / "private-patterns.txt").write_text(
        "# comments are ignored\ninternal.example\n\n",
        encoding="utf-8",
    )

    assert "internal.example" in linter.load_private_patterns(repo)


def test_lint_file_flags_token_like_secret(tmp_path):
    target = tmp_path / "core.md"
    target.write_text("Example token: sk-" + "a" * 32 + "\n", encoding="utf-8")

    failures = linter.lint_file(target)

    assert failures == 1


def test_lint_file_flags_additional_vendor_secret_prefixes(tmp_path):
    samples = {
        "gitlab.md": "Example token: glpat-" + "a" * 24,
        "slack.md": "Example token: xoxb-" + "1" * 20,
        "google.md": "Example token: AIza" + "a" * 35,
        "github_oauth.md": "Example token: gho_" + "a" * 32,
        "github_server.md": "Example token: ghs_" + "b" * 32,
        "github_user.md": "Example token: ghu_" + "c" * 32,
        "github_refresh.md": "Example token: ghr_" + "d" * 32,
        "huggingface.md": "Example token: hf_" + "e" * 34,
        "npm.md": "Example token: npm_" + "f" * 36,
    }
    for filename, body in samples.items():
        target = tmp_path / filename
        target.write_text(body + "\n", encoding="utf-8")
        assert linter.lint_file(target) == 1, filename


def test_lint_file_flags_non_ascii_content(tmp_path):
    target = tmp_path / "core.md"
    target.write_text("Use a regular dash, not an em—dash.\n", encoding="utf-8")

    failures = linter.lint_file(target)

    assert failures == 1


def test_lint_file_flags_crlf_line_endings(tmp_path):
    target = tmp_path / "core.md"
    target.write_bytes(b"Line one\r\nLine two\r\n")

    failures = linter.lint_file(target)

    assert failures == 1


def test_lint_file_passes_clean_ascii(tmp_path):
    target = tmp_path / "core.md"
    target.write_text("Plain ASCII guidance with no markers.\n", encoding="utf-8")

    failures = linter.lint_file(target)

    assert failures == 0


def test_lint_line_count_returns_failure_when_over_hard_cap(tmp_path):
    target = tmp_path / "core.md"
    target.write_text("\n".join("line" for _ in range(12)), encoding="utf-8")

    failures = linter.lint_line_count(target, warn_at=8, max_lines=10)

    assert failures == 1


def test_lint_line_count_returns_zero_when_within_warn_threshold(tmp_path):
    target = tmp_path / "core.md"
    target.write_text("\n".join("line" for _ in range(5)), encoding="utf-8")

    failures = linter.lint_line_count(target, warn_at=8, max_lines=10)

    assert failures == 0


def test_lint_line_count_returns_zero_when_only_warning(tmp_path):
    target = tmp_path / "core.md"
    target.write_text("\n".join("line" for _ in range(9)), encoding="utf-8")

    failures = linter.lint_line_count(target, warn_at=8, max_lines=10)

    assert failures == 0


@pytest.mark.parametrize("name", ["private.example.md", "local.example.md"])
def test_tracked_overlay_examples_are_lint_clean(name):
    repo = Path(__file__).resolve().parents[1]
    target = repo / "prompts" / name

    assert target.exists(), f"prompts/{name} is a tracked template"
    assert linter.lint_file(target) == 0
    assert (
        linter.lint_line_count(
            target,
            linter.PRIVATE_EXAMPLE_WARN_LINES,
            linter.PRIVATE_EXAMPLE_MAX_LINES,
        )
        == 0
    )


def test_main_flags_orphan_harness_fragment(tmp_path, capsys):
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    prompts = repo_root / "prompts"
    (prompts / "harnesses").mkdir(parents=True)
    (prompts / "core.md").write_text("# Core\nclean line\n", encoding="utf-8")
    (prompts / "invariants.md").write_text("# Invariants\nclean line\n", encoding="utf-8")
    for harness in linter.HARNESSES:
        (prompts / "harnesses" / harness.fragment).write_text(
            "## Fragment\nclean line\n", encoding="utf-8"
        )
    (prompts / "harnesses" / "orphan.md").write_text(
        "## Orphan\nclean line\n", encoding="utf-8"
    )
    (prompts / "local.example.md").write_text("# Local\nclean line\n", encoding="utf-8")
    (prompts / "private.example.md").write_text(
        "# Example\nclean line\n", encoding="utf-8"
    )

    fake_script = scripts_dir / "lint_prompts.py"
    fake_script.write_bytes(Path(linter.__file__).read_bytes())

    spec = importlib.util.spec_from_file_location("lint_prompts_orphan_tmp", fake_script)
    sandbox = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(sandbox)

    rc = sandbox.main()
    captured = capsys.readouterr()

    assert rc == 1
    assert "orphan.md" in captured.err
    assert "orphan fragment" in captured.err


def test_main_lints_private_example_when_present(tmp_path, capsys):
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    prompts = repo_root / "prompts"
    (prompts / "harnesses").mkdir(parents=True)
    (prompts / "core.md").write_text("# Core\nclean line\n", encoding="utf-8")
    (prompts / "invariants.md").write_text("# Invariants\nclean line\n", encoding="utf-8")
    for harness in linter.HARNESSES:
        (prompts / "harnesses" / harness.fragment).write_text(
            "## Fragment\nclean line\n", encoding="utf-8"
        )
    (prompts / "private-patterns.txt").write_text("internal.example\n", encoding="utf-8")
    (prompts / "local.example.md").write_text("# Local\nclean line\n", encoding="utf-8")
    (prompts / "private.example.md").write_text(
        "# Example\nLeaks internal.example/secret path.\n", encoding="utf-8"
    )

    fake_script = scripts_dir / "lint_prompts.py"
    fake_script.write_bytes(Path(linter.__file__).read_bytes())

    spec = importlib.util.spec_from_file_location("lint_prompts_under_tmp", fake_script)
    sandbox = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(sandbox)

    rc = sandbox.main()
    captured = capsys.readouterr()

    assert rc == 1
    assert "private.example.md" in captured.err
    assert "private path or name marker" in captured.err


def test_main_lints_agent_sources(tmp_path, capsys):
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    prompts = repo_root / "prompts"
    (prompts / "harnesses").mkdir(parents=True)
    (prompts / "core.md").write_text("# Core\nclean line\n", encoding="utf-8")
    (prompts / "invariants.md").write_text("# Invariants\nclean line\n", encoding="utf-8")
    for harness in linter.HARNESSES:
        (prompts / "harnesses" / harness.fragment).write_text(
            "## Fragment\nclean line\n", encoding="utf-8"
        )
    (prompts / "local.example.md").write_text("# Local\nclean line\n", encoding="utf-8")
    (prompts / "private.example.md").write_text("# Example\nclean line\n", encoding="utf-8")
    agents = repo_root / "agents"
    agents.mkdir()
    (agents / "explorer.md").write_text(
        "---\nname: explorer\n---\nsee /home/yourname/secret\n", encoding="utf-8"
    )

    fake_script = scripts_dir / "lint_prompts.py"
    fake_script.write_bytes(Path(linter.__file__).read_bytes())
    spec = importlib.util.spec_from_file_location("lint_prompts_agents_tmp", fake_script)
    sandbox = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(sandbox)

    rc = sandbox.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "explorer.md" in captured.err
    assert "private path or name marker" in captured.err


def git_repo_with(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", *files], check=True)
    return tmp_path


def test_tracked_marker_scan_covers_every_tracked_file(tmp_path, capsys):
    repo = git_repo_with(tmp_path, {"README.md": "see lab.example.net\n", "docs/x.md": "clean\n"})
    (repo / "untracked.md").write_text("lab.example.net\n", encoding="utf-8")
    assert linter.lint_tracked_markers(repo, ("lab.example.net",)) == 1
    out = capsys.readouterr().err
    assert "README.md: tracked file contains local marker: lab.example.net" in out
    assert "untracked.md" not in out


def test_tracked_marker_scan_skips_example_and_binaries(tmp_path):
    repo = git_repo_with(
        tmp_path, {"prompts/private-patterns.example.txt": "lab.example.net\n", "blob.bin": "x\0lab.example.net"}
    )
    assert linter.lint_tracked_markers(repo, ("lab.example.net",)) == 0


def test_tracked_marker_scan_is_noop_without_user_markers(tmp_path):
    repo = git_repo_with(tmp_path, {"README.md": "internal.example\n"})
    assert linter.lint_tracked_markers(repo, ()) == 0


def test_user_patterns_exclude_builtin_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTS_PRIVATE_PATTERNS", "mine.example")
    assert linter.load_user_patterns(tmp_path) == ("mine.example",)
    assert "internal.example" in linter.load_private_patterns(tmp_path)


@pytest.mark.parametrize("marker,text", [
    ("lab.example.net", "LAB.EXAMPLE.NET"),
    ("Lab.Example.Net", "lab.example.net"),
])
def test_private_markers_ignore_case_in_sources_and_tracked_files(tmp_path, marker, text):
    repo = git_repo_with(tmp_path, {"README.md": text + "\n"})

    assert linter.lint_file(repo / "README.md", private_patterns=(marker,)) == 1
    assert linter.lint_tracked_markers(repo, (marker,)) == 1


def test_tracked_markers_use_unicode_casefold(tmp_path):
    repo = git_repo_with(tmp_path, {"README.md": "STRASSE\n"})

    assert linter.lint_tracked_markers(repo, ("Stra\u00dfe",)) == 1


@pytest.fixture
def lint_repo(tmp_path, monkeypatch):
    files = {
        "prompts/core.md": "# Core\nclean\n",
        "prompts/invariants.md": "# Invariants\nclean\n",
        "prompts/local.example.md": "# Local\nclean\n",
        "prompts/private.example.md": "# Private\nclean\n",
    }
    files.update({f"prompts/harnesses/{h.fragment}": "clean\n" for h in linter.HARNESSES})
    repo = git_repo_with(tmp_path, files)
    monkeypatch.setattr(linter, "__file__", str(repo / "scripts/lint_prompts.py"))
    monkeypatch.delenv("AGENTS_PRIVATE_PATTERNS", raising=False)
    return repo


@pytest.mark.parametrize("relative", [
    "skills/nested/example/SKILL.md",
    "templates/project/AGENTS.md.example",
    "templates/nested/settings.toml",
    "prompts/models.json",
])
@pytest.mark.parametrize("body,message", [
    ("sk-" + "a" * 32, "token-like secret"),
    ("non-ASCII \u00e9", "non-ASCII content"),
])
def test_main_lints_additional_public_sources(lint_repo, capsys, relative, body, message):
    target = lint_repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body + "\n", encoding="utf-8")

    assert linter.main() == 1
    errors = capsys.readouterr().err
    assert f"{target}:" in errors
    assert message in errors


def test_main_skips_binary_templates(lint_repo):
    target = lint_repo / "templates/project/image.bin"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"\0sk-" + b"a" * 32)

    assert linter.main() == 0


@pytest.mark.parametrize("relative", [
    "prompts/local.md", "prompts/private.md",
    "prompts/local.md.bak", "prompts/private.md.orig", "prompts/private.md~",
    "prompts/.local.md.swp", "prompts/.private.md.swo", "prompts/.private.md.un~",
    "prompts/#private.md#", "prompts/.#local.md",
    "prompts/private-patterns.txt", "prompts/private-harnesses.txt",
    "prompts/models.local.json", "prompts/deploy-targets.txt",
])
def test_main_rejects_tracked_overlays_and_editor_copies(lint_repo, capsys, relative):
    target = lint_repo / relative
    target.write_text("local context\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(lint_repo), "add", "-f", relative], check=True)

    assert linter.main() == 1
    assert f"{relative}: private overlay or editor copy must not be tracked" in capsys.readouterr().err


def test_tracked_overlay_check_fails_when_git_is_unavailable(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(linter, "tracked_files", lambda repo: None)

    assert linter.lint_tracked_overlays(tmp_path) == 1
    assert "cannot check for tracked private overlays" in capsys.readouterr().err


def test_gitignore_covers_overlay_editor_copies_but_keeps_examples(tmp_path):
    repo = git_repo_with(tmp_path, {
        ".gitignore": (Path(__file__).resolve().parents[1] / ".gitignore").read_text(),
    })
    ignored = [
        f"prompts/{name}"
        for stem in ("local.md", "private.md")
        for name in (stem, stem + ".bak", stem + ".orig", stem + "~", "." + stem + ".swp",
                     "." + stem + ".swo", "." + stem + ".un~", "#" + stem + "#", ".#" + stem)
    ]
    examples = ["prompts/local.example.md", "prompts/private.example.md"]
    result = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "--no-index", *ignored, *examples],
        capture_output=True, text=True, check=True,
    )

    assert set(result.stdout.splitlines()) == set(ignored)
