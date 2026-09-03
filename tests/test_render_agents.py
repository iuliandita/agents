import tomllib
from pathlib import Path

import pytest
import yaml

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


def test_parse_frontmatter_keeps_value_with_interior_matching_quote(tmp_path):
    path = write_agent(tmp_path / "sample.md", description='"a" and "b"')
    fields, _ = ra.parse_frontmatter(path.read_text(encoding="utf-8"), path)
    assert fields["description"] == '"a" and "b"'


def test_parse_frontmatter_rejects_missing_delimiters(tmp_path):
    path = tmp_path / "broken.md"
    path.write_text("name: x\nbody\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="frontmatter"):
        ra.parse_frontmatter(path.read_text(encoding="utf-8"), path)


def test_parse_frontmatter_rejects_missing_closing_delimiter(tmp_path):
    path = tmp_path / "broken.md"
    path.write_text("---\nname: x\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="closing"):
        ra.parse_frontmatter(path.read_text(encoding="utf-8"), path)


def test_parse_frontmatter_rejects_duplicate_key(tmp_path):
    path = tmp_path / "dup.md"
    path.write_text("---\nname: x\nname: y\n---\nbody\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="duplicate"):
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


def test_load_agent_rejects_control_character_in_description(tmp_path):
    path = write_agent(tmp_path / "sample.md", description="bad\x07bell")
    with pytest.raises(SystemExit, match="control character"):
        ra.load_agent(path)


def test_load_agent_allows_missing_max_turns(tmp_path):
    path = write_agent(tmp_path / "sample.md", max_turns=None)
    spec = ra.load_agent(path)
    assert spec.max_turns is None


def test_opencode_ro_bash_excludes_find_includes_git_grep():
    assert "find *" not in ra.OPENCODE_RO_BASH
    assert "git grep *" in ra.OPENCODE_RO_BASH


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
        {"codex": {"tiers": {"cheap": "haiku\ntools: Bash"}}},
        {"codex": {"tiers": {"cheap": "foo # comment"}}},
        {"codex": {"effort_key": "a.b"}},
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
    assert "fork_turns" not in data
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
    assert 'model: "opencode-go/glm-5.3-flash"' in head
    assert "reasoningEffort: low" in head
    assert "steps: 30" in head
    assert "  read: allow" in head
    assert "  grep: allow" in head
    assert "  glob: allow" in head
    assert "  edit: deny" in head
    assert "  task: deny" in head
    assert "  todowrite: deny" in head
    assert "  question: deny" in head
    assert '    "*": deny' in head
    assert '    "git diff *": allow' in head


def test_render_opencode_full_shell_and_inherit():
    text = ra.render_opencode(spec(tools=("read", "shell")), ra.resolve(spec(), "opencode", {}), INVARIANTS)
    head = text.split("---")[1]
    assert "model:" not in head
    assert "  bash: allow" in head


def test_render_harness_notices_when_every_model_inherits():
    specs = [spec(name="a", source=Path("agents/a.md")), spec(name="b", source=Path("agents/b.md"))]
    _, notices = ra.render_harness(specs, "opencode", {}, INVARIANTS)
    assert any("every tier renders as inherit" in notice for notice in notices)


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


def test_generated_header_hash_tracks_salt():
    one = ra.generated_header(spec(source_text="a"), "inv", salt="claude:sonnet:high")
    two = ra.generated_header(spec(source_text="a"), "inv", salt="codex:gpt-5.6-terra:high")
    assert one != two


def test_render_all_writes_every_harness(tmp_path):
    written = ra.render_all(REPO, tmp_path, selected=None, overrides={})
    assert set(written) == set(ra.AGENT_HARNESSES)
    for harness, paths in written.items():
        names = sorted(path.stem for path in paths)
        assert names == ["builder", "explorer", "planner", "researcher", "reviewer", "verifier"]
        assert all(path.suffix == ra.EXTENSIONS[harness] for path in paths)
        assert all(path.parent == tmp_path / harness for path in paths)
        if harness not in ("claude", "opencode", "commandcode"):
            continue
        for path in paths:
            text = path.read_text(encoding="utf-8")
            head = text.split("---")[1]
            data = yaml.safe_load(head)
            assert isinstance(data, dict)
            if harness == "opencode":
                assert data["permission"]["task"] == "deny"
                if path.stem in ("explorer", "reviewer"):
                    assert isinstance(data["permission"]["bash"], dict)
                    assert data["permission"]["bash"]["*"] == "deny"


def test_check_fails_when_marker_missing(monkeypatch, capsys):
    # GENERATED_MARKER itself feeds both the writer (generated_header) and the
    # checker, so patching the constant alone would not create a mismatch;
    # patch the writer instead so it stops emitting the real marker.
    monkeypatch.setattr(ra, "generated_header", lambda spec, invariants, salt="": "no marker here")
    assert ra.check(REPO, None) == 1
    assert "lacks the generated marker" in capsys.readouterr().out


def test_render_all_respects_target_selection(tmp_path):
    written = ra.render_all(REPO, tmp_path, selected=["claude,codex"], overrides={})
    assert set(written) == {"claude", "codex"}


def test_render_all_rejects_unknown_target(tmp_path):
    with pytest.raises(SystemExit, match="Unknown agent harness"):
        ra.render_all(REPO, tmp_path, selected=["cursor"], overrides={})


def test_selected_agent_harnesses_dedupes_preserving_order():
    assert ra.selected_agent_harnesses(["claude,claude", "claude"]) == ["claude"]


def test_check_override_agents_rejects_unknown_name():
    specs = ra.load_agents(REPO)
    overrides = {"claude": {"agents": {"nope": {"tier": "mid"}}}}
    with pytest.raises(SystemExit, match="does not match"):
        ra.check_override_agents(overrides, specs)


def test_render_all_rejects_unknown_override_agent_name(tmp_path):
    overrides = {"claude": {"agents": {"nope": {"tier": "mid"}}}}
    with pytest.raises(SystemExit, match="does not match"):
        ra.render_all(REPO, tmp_path, selected=["claude"], overrides=overrides)


def test_validate_overrides_allows_null_tier_for_inherit():
    overrides = ra.validate_overrides({"claude": {"tiers": {"cheap": None}}}, Path("models.local.json"))
    resolved = ra.resolve(spec(tier="cheap"), "claude", overrides)
    assert resolved.model is None


def test_check_passes_on_repo(capsys):
    assert ra.check(REPO, selected=None) == 0
    assert "check passed" in capsys.readouterr().out


def test_agent_target_dir_uses_env_override(tmp_path):
    env = {"CLAUDE_AGENTS_DIR": str(tmp_path / "custom")}
    assert ra.agent_target_dir("claude", home=tmp_path, env=env) == tmp_path / "custom"
    assert ra.agent_target_dir("codex", home=tmp_path, env={}) == tmp_path / ".codex" / "agents"


def test_deploy_writes_backs_up_and_cleans_stale(tmp_path, monkeypatch, capsys):
    target = tmp_path / "claude-agents"
    target.mkdir()
    stale = target / "old.md"
    stale.write_text(f"---\nname: old\n---\n<!-- {ra.GENERATED_MARKER} from agents/old.md (hash 0) -->\n", encoding="utf-8")
    foreign = target / "mine.md"
    foreign.write_text("---\nname: mine\n---\nhand written\n", encoding="utf-8")
    existing = target / "explorer.md"
    existing.write_text("previous content\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_AGENTS_DIR", str(target))
    backup_dir = tmp_path / "backups"

    ra.deploy(REPO, selected=["claude"], overrides={}, dry_run=False, backup_dir=backup_dir)

    assert not stale.exists()
    assert foreign.read_text(encoding="utf-8") == "---\nname: mine\n---\nhand written\n"
    assert ra.GENERATED_MARKER in existing.read_text(encoding="utf-8")
    backups = sorted(path.name for path in backup_dir.iterdir())
    assert any(name.startswith("explorer-") for name in backups)
    assert any(name.startswith("old-") for name in backups)
    out = capsys.readouterr().out
    assert f"removed stale claude: {stale} (backup in {backup_dir})" in out


def test_deploy_rejects_non_file_dest(tmp_path, monkeypatch):
    target = tmp_path / "claude-agents"
    target.mkdir()
    # "verifier" sorts after "builder" and "explorer"; nothing may be written before the refusal.
    (target / "verifier.md").mkdir()
    monkeypatch.setenv("CLAUDE_AGENTS_DIR", str(target))
    with pytest.raises(SystemExit, match="move it aside"):
        ra.deploy(REPO, selected=["claude"], overrides={}, dry_run=False, backup_dir=tmp_path / "b")
    assert sorted(path.name for path in target.iterdir()) == ["verifier.md"]


def test_deploy_rejects_symlink_dest(tmp_path, monkeypatch):
    target = tmp_path / "claude-agents"
    target.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("do not touch\n", encoding="utf-8")
    (target / "verifier.md").symlink_to(outside)
    monkeypatch.setenv("CLAUDE_AGENTS_DIR", str(target))
    with pytest.raises(SystemExit, match="move it aside"):
        ra.deploy(REPO, selected=["claude"], overrides={}, dry_run=False, backup_dir=tmp_path / "b")
    assert outside.read_text(encoding="utf-8") == "do not touch\n"


def test_deploy_target_dir_is_a_file(tmp_path, monkeypatch):
    target = tmp_path / "claude-agents"
    target.write_text("not a directory\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_AGENTS_DIR", str(target))
    with pytest.raises(SystemExit, match="not a directory"):
        ra.deploy(REPO, selected=["claude"], overrides={}, dry_run=False, backup_dir=tmp_path / "b")


def test_deploy_dry_run_writes_nothing(tmp_path, monkeypatch, capsys):
    target = tmp_path / "codex-agents"
    monkeypatch.setenv("CODEX_AGENTS_DIR", str(target))
    ra.deploy(REPO, selected=["codex"], overrides={}, dry_run=True, backup_dir=tmp_path / "b")
    assert not target.exists()
    out = capsys.readouterr().out
    assert "would create" in out
    assert "explorer.toml" in out


def test_deploy_dry_run_reports_unchanged_file(tmp_path, monkeypatch, capsys):
    target = tmp_path / "codex-agents"
    monkeypatch.setenv("CODEX_AGENTS_DIR", str(target))
    ra.deploy(REPO, selected=["codex"], overrides={}, dry_run=False, backup_dir=tmp_path / "b")
    capsys.readouterr()
    ra.deploy(REPO, selected=["codex"], overrides={}, dry_run=True, backup_dir=tmp_path / "b")
    out = capsys.readouterr().out
    assert "unchanged" in out
    assert "would replace" not in out


def test_deploy_is_idempotent(tmp_path, monkeypatch, capsys):
    target = tmp_path / "cc-agents"
    monkeypatch.setenv("COMMANDCODE_AGENTS_DIR", str(target))
    ra.deploy(REPO, selected=["commandcode"], overrides={}, dry_run=False, backup_dir=tmp_path / "b")
    capsys.readouterr()
    ra.deploy(REPO, selected=["commandcode"], overrides={}, dry_run=False, backup_dir=tmp_path / "b")
    out = capsys.readouterr().out
    assert "unchanged" in out
    assert "updated" not in out


def test_main_list_targets(capsys):
    assert ra.main(["--list-targets"]) == 0
    out = capsys.readouterr().out
    for harness in ra.AGENT_HARNESSES:
        assert harness in out


def test_main_check(capsys):
    assert ra.main(["--check"]) == 0


def test_render_all_prunes_stale_generated_outputs(tmp_path):
    stale_dir = tmp_path / "claude"
    stale_dir.mkdir()
    stale = stale_dir / "gone.md"
    stale.write_text(f"---\nname: gone\n---\n<!-- {ra.GENERATED_MARKER} -->\n", encoding="utf-8")
    foreign = stale_dir / "keep.md"
    foreign.write_text("hand written\n", encoding="utf-8")
    ra.render_all(REPO, tmp_path, selected=["claude"], overrides={})
    assert not stale.exists()
    assert foreign.exists()


# --- shell-ro enforcement -------------------------------------------------


def test_opencode_ro_bash_patterns_use_space_star():
    assert "ls *" in ra.OPENCODE_RO_BASH
    assert "git grep *" in ra.OPENCODE_RO_BASH
    assert all(pattern.endswith(" *") for pattern in ra.OPENCODE_RO_BASH)


def test_ro_commands_feed_opencode_patterns():
    assert ra.OPENCODE_RO_BASH == tuple(f"{cmd} *" for cmd in ra.RO_COMMANDS)


def test_render_opencode_emits_wrapper_patterns():
    overrides = {"opencode": {"shell_ro_wrappers": ["rtk"]}}
    resolved = ra.resolve(spec(), "opencode", overrides)
    assert resolved.wrappers == ("rtk",)
    text = ra.render_opencode(spec(tools=("read", "shell-ro")), resolved, INVARIANTS)
    head = text.split("---")[1]
    assert '    "ls *": allow' in head
    assert '    "rtk ls *": allow' in head
    assert '    "rtk git grep *": allow' in head


def test_resolve_wrappers_default_empty():
    assert ra.resolve(spec(), "opencode", {}).wrappers == ()


@pytest.mark.parametrize(
    "payload",
    [
        {"claude": {"shell_ro_wrappers": ["a b"]}},
        {"claude": {"shell_ro_wrappers": "rtk"}},
        {"claude": {"shell_ro_wrappers": [3]}},
        {"claude": {"shell_ro_wrappers": ["rtk;rm"]}},
    ],
)
def test_load_overrides_rejects_bad_wrappers(tmp_path, payload):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "models.local.json").write_text(
        __import__("json").dumps(payload), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="shell_ro_wrappers"):
        ra.load_overrides(tmp_path)


def test_validate_overrides_accepts_wrappers():
    data = ra.validate_overrides(
        {"claude": {"shell_ro_wrappers": ["rtk", "/usr/bin/env"]}}, Path("models.local.json")
    )
    assert data["claude"]["shell_ro_wrappers"] == ["rtk", "/usr/bin/env"]


def test_render_claude_adds_guard_hook_for_shell_ro():
    path = "/tmp/hooks/agents-shell-ro-guard.py"
    text = ra.render_claude(
        spec(tools=("read", "shell-ro")), ra.resolve(spec(), "claude", {}), INVARIANTS, guard_command=path
    )
    head = text.split("---")[1]
    assert "hooks:" in head
    assert "matcher: Bash" in head
    data = yaml.safe_load(head)
    assert data["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["type"] == "command"
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == path


def test_render_claude_omits_guard_hook_without_shell_ro():
    text = ra.render_claude(
        spec(tools=("read", "edit", "shell")),
        ra.resolve(spec(), "claude", {}),
        INVARIANTS,
        guard_command="/tmp/hooks/agents-shell-ro-guard.py",
    )
    head = text.split("---")[1]
    assert "hooks:" not in head
    assert yaml.safe_load(head).get("hooks") is None


def test_render_claude_omits_guard_hook_without_command():
    text = ra.render_claude(spec(tools=("read", "shell-ro")), ra.resolve(spec(), "claude", {}), INVARIANTS)
    assert "hooks:" not in text.split("---")[1]


def guard_path(tmp_path):
    path = tmp_path / ra.GUARD_NAME
    path.write_text(ra.render_guard(("rtk",)), encoding="utf-8")
    return path


def run_guard(path, payload):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, str(path)], input=payload, capture_output=True, text=True
    )


@pytest.mark.parametrize(
    "command",
    [
        "git diff --stat",
        "rtk ls -la scripts",
        "sed -n 1,5p x.py",
        "git log --oneline | head -5",
        "ls",
    ],
)
def test_guard_allows_read_only_commands(tmp_path, command):
    payload = __import__("json").dumps({"tool_input": {"command": command}})
    result = run_guard(guard_path(tmp_path), payload)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "ls; rm -rf x",
        "cat a > b",
        "echo $(id)",
        "sed -n -i s/a/b/ x",
        "find . -delete",
        "rtk rm x",
        "cat a `id`",
        "rg foo --output x",
    ],
)
def test_guard_blocks_non_read_only_commands(tmp_path, command):
    payload = __import__("json").dumps({"tool_input": {"command": command}})
    result = run_guard(guard_path(tmp_path), payload)
    assert result.returncode == 2
    assert "shell-ro guard" in result.stderr


@pytest.mark.parametrize("payload", ["", '{"tool_input":{}}', "not json"])
def test_guard_blocks_unreadable_input(tmp_path, payload):
    result = run_guard(guard_path(tmp_path), payload)
    assert result.returncode == 2
    assert "shell-ro guard: unreadable hook input" in result.stderr


def test_render_guard_is_marked_and_parses(tmp_path):
    import ast

    text = ra.render_guard(())
    assert ra.GENERATED_MARKER in text
    assert text.startswith("#!/usr/bin/env python3\n")
    ast.parse(text)
    assert ra.render_guard(("rtk",)) != text


def test_render_all_writes_executable_guard(tmp_path):
    ra.render_all(REPO, tmp_path, selected=["claude"], overrides={})
    guard = tmp_path / "claude" / "agents-shell-ro-guard.py"
    assert guard.is_file()
    assert guard.stat().st_mode & 0o111


def test_deploy_installs_guard_and_references_it(tmp_path, monkeypatch, capsys):
    agents_dir = tmp_path / "claude-agents"
    hooks_dir = tmp_path / "claude-hooks"
    monkeypatch.setenv("CLAUDE_AGENTS_DIR", str(agents_dir))
    monkeypatch.setenv("CLAUDE_HOOKS_DIR", str(hooks_dir))

    ra.deploy(REPO, selected=["claude"], overrides={}, dry_run=False, backup_dir=tmp_path / "b")
    guard = hooks_dir / ra.GUARD_NAME
    assert guard.is_file()
    assert guard.stat().st_mode & 0o111
    explorer = (agents_dir / "explorer.md").read_text(encoding="utf-8")
    assert str(guard) in explorer
    data = yaml.safe_load(explorer.split("---")[1])
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == str(guard)
    assert "builder" not in yaml.safe_load((agents_dir / "builder.md").read_text(encoding="utf-8").split("---")[1]).get("hooks", {})

    capsys.readouterr()
    ra.deploy(REPO, selected=["claude"], overrides={}, dry_run=False, backup_dir=tmp_path / "b")
    out = capsys.readouterr().out
    assert f"unchanged claude: {guard}" in out
    assert "updated" not in out
    assert guard.is_file()


def test_deploy_dry_run_reports_guard(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_AGENTS_DIR", str(tmp_path / "a"))
    monkeypatch.setenv("CLAUDE_HOOKS_DIR", str(tmp_path / "h"))
    ra.deploy(REPO, selected=["claude"], overrides={}, dry_run=True, backup_dir=tmp_path / "b")
    out = capsys.readouterr().out
    assert f"would create claude: {tmp_path / 'h' / ra.GUARD_NAME}" in out
    assert not (tmp_path / "h").exists()


def test_readme_roster_table_matches_agent_sources():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    rows = {}
    for line in readme.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[0] not in {"agent", "---"} and cells[1] in ra.TIERS:
            rows[cells[0]] = cells
    specs = {spec.name: spec for spec in ra.load_agents(REPO)}
    assert set(rows) == set(specs)
    for name, spec in specs.items():
        assert rows[name][1] == spec.tier, name
        assert rows[name][2] == spec.effort, name
        assert rows[name][3] == ", ".join(spec.tools), name
