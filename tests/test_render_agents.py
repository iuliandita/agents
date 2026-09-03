import tomllib
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


def spec(**overrides):
    fields = dict(
        name="sample",
        description="Sample.",
        tier="cheap",
        effort="low",
        tools=("read",),
        max_turns=None,
        body="Body.\n",
        source=Path("agents/sample.md"),
        source_text="",
    )
    fields.update(overrides)
    return ra.AgentSpec(**fields)


def test_resolve_claude_defaults():
    resolved = ra.resolve(spec(tier="flagship", effort="high"), "claude", {})
    assert resolved.model == "opus"
    assert resolved.effort == "high"
    assert resolved.notices == []


def test_resolve_codex_apex_falls_back_to_flagship_with_notice():
    resolved = ra.resolve(spec(tier="apex"), "codex", {})
    assert resolved.model == "gpt-5.6-sol"
    assert any("apex" in notice for notice in resolved.notices)


def test_resolve_opencode_inherits_without_override():
    resolved = ra.resolve(spec(tier="mid"), "opencode", {})
    assert resolved.model is None


def test_resolve_applies_tier_and_agent_overrides():
    overrides = {
        "opencode": {
            "tiers": {"cheap": "opencode-go/glm-5.3-flash"},
            "agents": {"sample": {"tier": "cheap", "effort": "medium"}},
        }
    }
    resolved = ra.resolve(spec(tier="flagship", effort="high"), "opencode", overrides)
    assert resolved.model == "opencode-go/glm-5.3-flash"
    assert resolved.effort == "medium"


@pytest.mark.parametrize(
    "payload",
    [
        {"nope": {}},
        {"claude": {"colors": {}}},
        {"claude": {"tiers": {"huge": "x"}}},
        {"claude": {"tiers": {"cheap": 3}}},
        {"claude": {"agents": {"sample": {"model": "x"}}}},
        {"claude": {"agents": {"sample": {"tier": "huge"}}}},
        {"claude": {"effort_key": 5}},
        [],
    ],
)
def test_load_overrides_rejects_bad_shapes(tmp_path, payload):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "models.local.json").write_text(
        __import__("json").dumps(payload), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="models.local.json"):
        ra.load_overrides(tmp_path)


def test_load_overrides_missing_file_is_empty(tmp_path):
    assert ra.load_overrides(tmp_path) == {}


def test_tracked_example_overrides_load():
    example = REPO / "prompts" / "models.local.example.json"
    ra.validate_overrides(__import__("json").loads(example.read_text(encoding="utf-8")), example)


INVARIANTS = "# Hard Invariants (non-negotiable)\n- Never add AI attribution to git artifacts.\n"


def test_render_claude_frontmatter_and_body():
    text = ra.render_claude(spec(tools=("read", "search", "shell-ro"), max_turns=30), ra.resolve(spec(), "claude", {}), INVARIANTS)
    fields, body = ra.parse_frontmatter(text, Path("claude/sample.md"))
    assert fields == {
        "name": "sample",
        "description": "Sample.",
        "tools": "Read, Grep, Glob, Bash",
        "model": "haiku",
        "effort": "low",
        "maxTurns": "30",
    }
    assert ra.GENERATED_MARKER in body
    assert "Never add AI attribution" in body
    assert body.rstrip().endswith("Body.")


def test_render_claude_omits_model_when_inherit():
    resolved = ra.Resolved(model=None, effort="low", effort_key="effort", notices=[])
    fields, _ = ra.parse_frontmatter(ra.render_claude(spec(), resolved, INVARIANTS), Path("x.md"))
    assert "model" not in fields


def test_render_codex_is_valid_toml_with_sandbox():
    read_only = ra.render_codex(spec(tools=("read", "search", "shell-ro")), ra.resolve(spec(), "codex", {}), INVARIANTS)
    data = tomllib.loads(read_only)
    assert data["name"] == "sample"
    assert data["model"] == "gpt-5.6-luna"
    assert data["model_reasoning_effort"] == "low"
    assert data["sandbox_mode"] == "read-only"
    assert data["fork_turns"] == "none"
    assert "Never add AI attribution" in data["developer_instructions"]
    assert data["developer_instructions"].rstrip().endswith("Body.")

    writer = ra.render_codex(spec(tools=("read", "edit")), ra.resolve(spec(), "codex", {}), INVARIANTS)
    assert tomllib.loads(writer)["sandbox_mode"] == "workspace-write"


def test_render_codex_escapes_description_quotes():
    text = ra.render_codex(spec(description='Say "hi" \\ now'), ra.resolve(spec(), "codex", {}), INVARIANTS)
    assert tomllib.loads(text)["description"] == 'Say "hi" \\ now'


def test_render_codex_rejects_triple_quote_in_body():
    with pytest.raises(SystemExit, match='"""'):
        ra.render_codex(spec(body='x = """y"""\n'), ra.resolve(spec(), "codex", {}), INVARIANTS)


def test_render_opencode_permission_map_for_shell_ro():
    resolved = ra.resolve(spec(), "opencode", {"opencode": {"tiers": {"cheap": "opencode-go/glm-5.3-flash"}}})
    text = ra.render_opencode(spec(tools=("read", "search", "shell-ro"), max_turns=30), resolved, INVARIANTS)
    head = text.split("---")[1]
    assert "mode: subagent" in head
    assert "model: opencode-go/glm-5.3-flash" in head
    assert "reasoningEffort: low" in head
    assert "steps: 30" in head
    assert "  read: allow" in head
    assert "  grep: allow" in head
    assert "  glob: allow" in head
    assert "  edit: deny" in head
    assert "  task: deny" in head
    assert '    "*": deny' in head
    assert '    "git diff*": allow' in head


def test_render_opencode_full_shell_and_inherit():
    text = ra.render_opencode(spec(tools=("read", "shell")), ra.resolve(spec(), "opencode", {}), INVARIANTS)
    head = text.split("---")[1]
    assert "model:" not in head
    assert "  bash: allow" in head


def test_render_commandcode_tools_list():
    text = ra.render_commandcode(spec(tools=("read", "search", "web"), max_turns=30), ra.resolve(spec(), "commandcode", {}), INVARIANTS)
    fields, body = ra.parse_frontmatter(text, Path("x.md"))
    assert fields["tools"] == "read_file, read_directory, grep, glob, web_fetch, web_search"
    assert fields["reasoningEffort"] == "low"
    assert fields["maxTurns"] == "30"
    assert "model" not in fields
    assert ra.GENERATED_MARKER in body


def test_generated_header_hash_tracks_sources():
    one = ra.generated_header(spec(source_text="a"), "inv")
    two = ra.generated_header(spec(source_text="b"), "inv")
    three = ra.generated_header(spec(source_text="a"), "inv2")
    assert one != two != three
    assert ra.GENERATED_MARKER in one
