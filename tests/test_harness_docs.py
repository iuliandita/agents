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
