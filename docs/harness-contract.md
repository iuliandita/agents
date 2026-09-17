# Harness Contract

This is the single source of truth for the supported harnesses: global rules path, override, and the
receipts behind the claim. If a harness is not here, the repo does not claim to support it; use the
generic project-level `AGENTS.md` target instead.

Verified 2026-09-17 against upstream docs. `confidence` reflects whether the vendor documents the path
directly (`high`), it is inferred from a consistent pattern (`medium`), or it is not vendored (`n/a`).

| Harness | Global rules file | Override | Confidence | Source |
|---|---|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` (+ `~/.claude/settings.json`) | `CLAUDE_AGENTS_PATH`, `CLAUDE_CONFIG_DIR` | high | code.claude.com/docs/en/memory |
| OpenAI Codex | `$CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`) | `CODEX_AGENTS_PATH`, `CODEX_HOME` | high | developers.openai.com/codex/agent-configuration/agents-md |
| OpenCode | `~/.config/opencode/AGENTS.md` (+ `opencode.json`) | `OPENCODE_AGENTS_PATH`, `OPENCODE_CONFIG_DIR` | high | opencode.ai/docs/rules/ |
| Command Code | `~/.commandcode/AGENTS.md` (+ `settings.json`) | `COMMANDCODE_AGENTS_PATH` | medium | commandcode.ai/docs/memory |
| Antigravity | `~/.gemini/GEMINI.md`; workspace `.agents/rules/` | `ANTIGRAVITY_AGENTS_PATH`, none native | high | antigravity.google/docs/rules-workflows/ |
| Hermes Agent | `agent.coding_instructions` in `$HERMES_HOME/config.yaml`; project `.hermes.md`/`HERMES.md` > `AGENTS.override.md` > `AGENTS.md` | `HERMES_AGENTS_PATH` (project file) | high | hermes-agent.nousresearch.com/docs/user-guide/features/context-files |
| Generic | none (project-level `AGENTS.md` only) | `GENERIC_AGENTS_PATH` | n/a | - |

## Per-harness notes

### Claude Code
- Global memory `~/.claude/CLAUDE.md`; hooks and skills live in `~/.claude/settings.json` and
  `~/.claude/agents/`, `~/.claude/skills/`.
- On Windows, `~/.claude` means `%USERPROFILE%\.claude`. `CLAUDE_CONFIG_DIR` relocates config.
- The desktop Code tab runs the same engine and reads the same files; the Chat/Cowork tab does not
  (see `docs/surfaces.md`).
- Skills and hooks are first-class; the `UserPromptSubmit` hook is the invariants channel.

### OpenAI Codex
- Global rules `$CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`), read as `AGENTS.override.md` then
  `AGENTS.md`; combined byte cap 32 KiB. Config `~/.codex/config.toml`.
- Native Windows documented; the Windows spelling of `CODEX_HOME` is not explicitly documented, so it
  resolves like other tools (`%USERPROFILE%\.codex`).
- Custom roles in `~/.codex/agents/*.toml`; a role applies only when `spawn_agent` passes its
  `agent_type` with `fork_turns="none"`.

### OpenCode
- Global rules `~/.config/opencode/AGENTS.md`; config `opencode.json` or `opencode.jsonc`; agents in
  `~/.config/opencode/agents/` (plural); skills in `~/.config/opencode/skills/`.
- Same path on macOS. On Windows, run under WSL (recommended) or use
  `%USERPROFILE%\.config\opencode`. A WSL install reads the WSL home, separate from native Windows.
- Permission keys include `read`, `edit` (gates `write`/`edit`/`apply_patch`), `bash`, `task`, `glob`,
  `grep`, `list`, `todowrite`, `webfetch`, `websearch`, `external_directory`, `lsp`, `skill`,
  `question`. Unlisted custom/MCP tools fall back to global defaults.

### Command Code
- Global rules `~/.commandcode/AGENTS.md`; project rules `./AGENTS.md`; settings and hooks in
  `~/.commandcode/settings.json`; skills and agents in `~/.commandcode/skills/` and `agents/`.
- Home is resolved from `HOME`/`USERPROFILE`, so Windows native gives `%USERPROFILE%\.commandcode`.
  Binary aliases: `cmd`/`command-code`/`commandcode` (POSIX), `cmdc` (native Windows).
- Confidence is medium because the memory path is documented but the per-OS spelling is inferred.

### Antigravity
- One rules file for all surfaces: `~/.gemini/GEMINI.md`. Workspace rules in `.agents/rules/`
  (`.agent/rules/` still accepted), activation modes Manual/Always On/Model Decision/Glob, 12,000-char
  cap per file. Workspace context also parses `AGENTS.md`.
- Per-surface app data: `~/.gemini/antigravity/` (desktop), `~/.gemini/antigravity-ide/` (IDE),
  `~/.gemini/antigravity-cli/` (CLI, with `settings.json`, `skills/`, `plugins/`). Global MCP
  `~/.gemini/config/mcp_config.json`. Hooks `hooks.json` in `.agents/` or `~/.gemini/config/`
  (`PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`); `PreInvocation` can return
  `injectSteps[].ephemeralMessage`, the invariants channel for this harness.
- Headless: `agy -p` with `--output-format text|json|stream-json`, `--effort`, `--continue`.
- Custom subagents: `.agents/agents/<name>.md` (workspace) or `~/.gemini/config/agents/<name>.md`
  (global), YAML frontmatter `name`, `description`, `tools` (exact names; a misspelled tool can hang the
  subagent), `subagent`, `mainAgent`, `model: inherit|flash|pro`, `commandExecutionPolicy`.
- The desktop vs IDE global-skills path is contradictory in upstream docs
  (`~/.gemini/config/skills/` vs `~/.gemini/antigravity/skills/`); unresolved, so skills are out of scope.

### Hermes Agent
- No global Markdown rules file. Global operational rules go in `agent.coding_instructions` (standing
  coding rules appended to the coding brief) or `agent.system_prompt` in `$HERMES_HOME/config.yaml`.
  `SOUL.md` is identity/persona (system-prompt slot 1) and is not written by this repo.
- Project context loads exactly one file, first match wins: `.hermes.md`/`HERMES.md` >
  `AGENTS.override.md` > `AGENTS.md` > `CLAUDE.md` > `.cursorrules`, plus git-root-to-CWD chain merge.
- Desktop app shares `$HERMES_HOME` with the CLI. Windows default `%LOCALAPPDATA%\hermes`; WSL uses
  `~/.hermes`. Non-interactive: `hermes chat -q`.
- Skills `$HERMES_HOME/skills/`; delegation via `delegate_task`; hooks via plugins/config.
- No per-role prompt file: delegation is configured under `delegation:` in `config.yaml`, so the six
  roles are a manual paste rather than a rendered file.
- Global rules are merged with `scripts/render-hermes --deploy`, a comment-preserving line edit that
  sets `agent.coding_instructions` and backs up `config.yaml` first.

## Unverified

- Command Code per-OS home spelling (medium).
- Antigravity native-Windows config spelling; upstream writes `~/` without a Windows variant.
- Antigravity global skills path (docs contradict).
