import subprocess
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


def test_readme_docs_include_watchlist_and_provider_boundary():
    repo = Path(__file__).resolve().parents[1]
    readme = (repo / "README.md").read_text(encoding="utf-8")

    for name in ("Devin for Terminal", "Junie", "Kilo Code", "Qoder CLI", "Rovo Dev", "Trae"):
        assert name in readme
    assert "Z.ai and MiniMax are treated as providers/tool integrations" in readme
