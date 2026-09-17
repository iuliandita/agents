## OpenCode Notes
- Global rules: `~/.config/opencode/AGENTS.md`; config `opencode.json`/`opencode.jsonc`; agents in `~/.config/opencode/agents/`; skills in `~/.config/opencode/skills/`. Override with `OPENCODE_AGENTS_PATH` or `OPENCODE_CONFIG_DIR`.
- Same paths on macOS; on Windows run under WSL (recommended) or use `%USERPROFILE%\.config\opencode`. A WSL install reads the WSL home, separate from native Windows.
- Non-interactive: `opencode run`; add `--format json` or `--continue` for pipelines. List models with `opencode models` and agents with `opencode agent list`.
- Model and effort IDs live in `prompts/models.json` (`reasoningEffort` per agent). Routed and self-hosted providers ignore unsupported levels, so confirm the resolved model in the session header before trusting a tier.
- Skills are native, no plugin required. Discovery spans global `~/.claude/skills`, `~/.agents/skills`, and `~/.config/opencode/skills`, then project `.claude/skills`, `.agents/skills`, and `.opencode/skills` searched upward from CWD, with later sources winning.
- Subagents are markdown in `agents/`; invoke with `@name` or the Task tool. Deny `task` in a subagent to stop nested delegation.
- Permissions use `permission:` keys (`read`, `edit`, `bash`, `task`, `todowrite`, `webfetch`, `websearch`, `external_directory`, `lsp`, `skill`, `question`); unlisted custom and MCP tools fall back to global config, so a read-only role needs an explicit deny-all before its allowances.
- Hooks and plugins can inject rules per turn; keep the hard rules in `prompts/invariants.md` and let the hook deliver them instead of repeating them per prompt.
- Verify discovery after deploy: `opencode agent list` shows the rendered roles and the session header names the expected model. The TUI, CLI, and desktop app share this config.
