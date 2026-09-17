## Antigravity Notes
- Global rules: `~/.gemini/GEMINI.md`, shared by the desktop app, IDE extensions, and the `agy` CLI. Override the global path with `ANTIGRAVITY_AGENTS_PATH`.
- Workspace rules live in `.agents/rules/` (`.agent/rules/` still accepted) with a 12,000-character cap per file and Manual/Always On/Model Decision/Glob activation. Workspace context also parses `AGENTS.md`; global `GEMINI.md` takes precedence when both exist.
- Non-interactive: `agy -p` with `--output-format text|json|stream-json`, `--effort`, and `--continue`.
- Model and effort IDs live in `prompts/models.json`; confirm the model and the `--effort` vocabulary against `agy --help` before scripting.
- Skills live in `.agents/skills/` (workspace) and a per-surface global directory; plugins bundle skills, subagents, rules, MCP, and `hooks.json`.
- Subagents live in `.agents/agents/<name>.md` (workspace) and `~/.gemini/config/agents/` (global); invoke them from the running agent.
- Permissions and sandbox are per-surface; check the current permission mode before assuming a write is gated.
- Hooks: `hooks.json` in `.agents/` or `~/.gemini/config/` with `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, and `Stop`; `PreInvocation` can inject an `ephemeralMessage`, which is the invariants channel for this harness.
- Verify discovery after deploy: the agent list shows the rendered roles and the session names the expected model. Gemini CLI is legacy; the shared `GEMINI.md` path now serves Antigravity.
