import subprocess
import textwrap
from pathlib import Path


def test_harness_docs_are_in_sync_with_renderer_registry():
    repo = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        ["python", "scripts/check_harness_docs.py"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Harness docs check passed" in result.stdout


def test_install_docs_describe_support_levels():
    repo = Path(__file__).resolve().parents[1]
    install = (repo / "INSTALL.md").read_text(encoding="utf-8")

    assert "| Harness | Support | Target | Notes |" in install
    assert "| Antigravity CLI | deployable | `~/.gemini/GEMINI.md` |" in install
    assert "| Kimi Code | manual | `manual override via KIMI_AGENTS_PATH` |" in install


def test_harness_docs_check_binds_notes_to_matching_install_row(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    fixture = tmp_path / "repo"
    scripts = fixture / "scripts"
    scripts.mkdir(parents=True)

    (scripts / "check_harness_docs.py").write_text(
        (repo / "scripts/check_harness_docs.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (scripts / "render_prompts.py").write_text(
        textwrap.dedent(
            """\
            def harness_display_names():
                return ["Alpha", "Beta"]


            def harness_target_rows():
                return [
                    ("Alpha", "deployable", "~/alpha", "Alpha notes"),
                    ("Beta", "manual", "~/beta", "Beta notes"),
                ]
            """
        ),
        encoding="utf-8",
    )
    (fixture / "README.md").write_text("Alpha\nBeta\n", encoding="utf-8")
    (fixture / "INSTALL.md").write_text(
        textwrap.dedent(
            """\
            | Harness | Support | Target | Notes |
            | --- | --- | --- | --- |
            | Alpha | deployable | `~/alpha` | Beta notes |
            | Beta | manual | `~/beta` | Alpha notes |
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["python", "scripts/check_harness_docs.py"],
        cwd=fixture,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert (
        "INSTALL.md target row drifted for Alpha: deployable ~/alpha Alpha notes"
        in result.stdout
    )


def test_readme_docs_include_watchlist_and_provider_boundary():
    repo = Path(__file__).resolve().parents[1]
    readme = (repo / "README.md").read_text(encoding="utf-8")

    for name in ("Devin for Terminal", "Junie", "Kilo Code", "Qoder CLI", "Rovo Dev", "Trae"):
        assert name in readme
    assert "Z.ai and MiniMax are treated as providers/tool integrations" in readme
