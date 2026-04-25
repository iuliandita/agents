import importlib.util
import sys
from pathlib import Path


def load_linter():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module_path = scripts_dir / "lint_prompts.py"
    spec = importlib.util.spec_from_file_location("lint_prompts", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_lint_file_flags_private_path_marker(tmp_path):
    linter = load_linter()
    target = tmp_path / "core.md"
    target.write_text("Render from ~/.config/ai/prompt-core.md instead.\n", encoding="utf-8")

    failures = linter.lint_file(target)

    assert failures == 1


def test_lint_file_flags_token_like_secret(tmp_path):
    linter = load_linter()
    target = tmp_path / "core.md"
    target.write_text("Example token: sk-" + "a" * 32 + "\n", encoding="utf-8")

    failures = linter.lint_file(target)

    assert failures == 1


def test_lint_file_flags_additional_vendor_secret_prefixes(tmp_path):
    linter = load_linter()
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
    linter = load_linter()
    target = tmp_path / "core.md"
    target.write_text("Use a regular dash, not an em—dash.\n", encoding="utf-8")

    failures = linter.lint_file(target)

    assert failures == 1


def test_lint_file_flags_crlf_line_endings(tmp_path):
    linter = load_linter()
    target = tmp_path / "core.md"
    target.write_bytes(b"Line one\r\nLine two\r\n")

    failures = linter.lint_file(target)

    assert failures == 1


def test_lint_file_passes_clean_ascii(tmp_path):
    linter = load_linter()
    target = tmp_path / "core.md"
    target.write_text("Plain ASCII guidance with no markers.\n", encoding="utf-8")

    failures = linter.lint_file(target)

    assert failures == 0


def test_lint_line_count_returns_failure_when_over_hard_cap(tmp_path):
    linter = load_linter()
    target = tmp_path / "core.md"
    target.write_text("\n".join("line" for _ in range(12)), encoding="utf-8")

    failures = linter.lint_line_count(target, warn_at=8, max_lines=10)

    assert failures == 1


def test_lint_line_count_returns_zero_when_within_warn_threshold(tmp_path):
    linter = load_linter()
    target = tmp_path / "core.md"
    target.write_text("\n".join("line" for _ in range(5)), encoding="utf-8")

    failures = linter.lint_line_count(target, warn_at=8, max_lines=10)

    assert failures == 0


def test_lint_line_count_returns_zero_when_only_warning(tmp_path):
    linter = load_linter()
    target = tmp_path / "core.md"
    target.write_text("\n".join("line" for _ in range(9)), encoding="utf-8")

    failures = linter.lint_line_count(target, warn_at=8, max_lines=10)

    assert failures == 0


def test_tracked_private_example_is_lint_clean():
    linter = load_linter()
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
    linter = load_linter()
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    prompts = repo_root / "prompts"
    (prompts / "harnesses").mkdir(parents=True)
    (prompts / "core.md").write_text("# Core\nclean line\n", encoding="utf-8")
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
    linter = load_linter()
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    prompts = repo_root / "prompts"
    (prompts / "harnesses").mkdir(parents=True)
    (prompts / "core.md").write_text("# Core\nclean line\n", encoding="utf-8")
    for harness in linter.HARNESSES:
        (prompts / "harnesses" / harness.fragment).write_text(
            "## Fragment\nclean line\n", encoding="utf-8"
        )
    (prompts / "private.example.md").write_text(
        "# Example\nLeaks /home/id/secret path.\n", encoding="utf-8"
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
