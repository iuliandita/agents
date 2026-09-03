from pathlib import Path

import pytest

import render_agents as ra


REPO = Path(__file__).resolve().parents[1]


def write_agent(path: Path, name: str = "sample", **overrides: str) -> Path:
    fields = {
        "name": name,
        "description": 'Sample agent: locates "things".',
        "tier": "cheap",
        "effort": "low",
        "tools": "read, search, shell-ro",
        "max_turns": "20",
    }
    fields.update(overrides)
    front = "\n".join(f"{key}: {value}" for key, value in fields.items() if value is not None)
    path.write_text(f"---\n{front}\n---\nBody line one.\n\nBody line two.\n", encoding="utf-8")
    return path


def test_parse_frontmatter_splits_keys_and_body(tmp_path):
    path = write_agent(tmp_path / "sample.md")
    fields, body = ra.parse_frontmatter(path.read_text(encoding="utf-8"), path)
    assert fields["name"] == "sample"
    assert fields["tools"] == "read, search, shell-ro"
    assert body == "Body line one.\n\nBody line two.\n"


def test_parse_frontmatter_strips_matching_quotes(tmp_path):
    path = write_agent(tmp_path / "sample.md", description='"Quoted: value"')
    fields, _ = ra.parse_frontmatter(path.read_text(encoding="utf-8"), path)
    assert fields["description"] == "Quoted: value"


def test_parse_frontmatter_rejects_missing_delimiters(tmp_path):
    path = tmp_path / "broken.md"
    path.write_text("name: x\nbody\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="frontmatter"):
        ra.parse_frontmatter(path.read_text(encoding="utf-8"), path)


def test_load_agent_builds_spec(tmp_path):
    path = write_agent(tmp_path / "sample.md")
    spec = ra.load_agent(path)
    assert spec.name == "sample"
    assert spec.tier == "cheap"
    assert spec.effort == "low"
    assert spec.tools == ("read", "search", "shell-ro")
    assert spec.max_turns == 20
    assert spec.body.startswith("Body line one.")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tier", "huge", "tier"),
        ("effort", "ultra", "effort"),
        ("tools", "read, laser", "tool"),
        ("max_turns", "zero", "max_turns"),
        ("name", "Sample", "name"),
    ],
)
def test_load_agent_rejects_bad_values(tmp_path, field, value, message):
    path = write_agent(tmp_path / "sample.md", **{field: value})
    with pytest.raises(SystemExit, match=message):
        ra.load_agent(path)


def test_load_agent_rejects_name_filename_mismatch(tmp_path):
    path = write_agent(tmp_path / "other.md", name="sample")
    with pytest.raises(SystemExit, match="filename"):
        ra.load_agent(path)


def test_load_agent_rejects_unknown_and_missing_keys(tmp_path):
    path = write_agent(tmp_path / "sample.md", color="red")
    with pytest.raises(SystemExit, match="unknown key"):
        ra.load_agent(path)
    path = write_agent(tmp_path / "sample.md", description=None)
    with pytest.raises(SystemExit, match="missing key"):
        ra.load_agent(path)


def test_load_agent_rejects_reserved_commandcode_name(tmp_path):
    path = write_agent(tmp_path / "explore.md", name="explore")
    with pytest.raises(SystemExit, match="reserved"):
        ra.load_agent(path)


def test_load_agents_reads_repo_roster():
    specs = ra.load_agents(REPO)
    assert [spec.name for spec in specs] == [
        "builder",
        "explorer",
        "planner",
        "researcher",
        "reviewer",
        "verifier",
    ]
