import importlib.util
from pathlib import Path

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


def test_tracked_private_example_is_lint_clean():
    repo = Path(__file__).resolve().parents[1]
    target = repo / "prompts" / "private.example.md"

    assert target.exists(), "prompts/private.example.md is a tracked template"
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
    assert "orphan.md" in captured.out
    assert "orphan fragment" in captured.out


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
    assert "private.example.md" in captured.out
    assert "private path or name marker" in captured.out
