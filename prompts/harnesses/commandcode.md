## Command Code Notes
- Global rules: `~/.commandcode/AGENTS.md`; project rules `./AGENTS.md` (scaffold with `/init`); settings and hooks in `~/.commandcode/settings.json`; skills in `~/.commandcode/skills/`, agents in `~/.commandcode/agents/`. Override with `COMMANDCODE_AGENTS_PATH`.
- Home resolves from `HOME`/`USERPROFILE`, so native Windows uses `%USERPROFILE%\.commandcode`; the binary is `cmd`/`command-code`/`commandcode` on POSIX and `cmdc` on native Windows.
- Non-interactive: `cmd -p`; verify the current flag against `--help`. Hooks are gated by `~/.commandcode/trusted-hooks.json`.
- Model and effort IDs live in `prompts/models.json` (`reasoningEffort`; per-task models via `/configure-models`). Verify supported levels before scripting.
- Command Code learns a per-user "taste" from past sessions. Manage durable context with `/memory` and refresh style with `/learn-taste`; keep operational rules here, not in taste.
- Agents render as markdown in `~/.commandcode/agents/`. Command Code ignores custom files that reuse a built-in name, so the six role names must stay distinct.
- Skills and agents load from `~/.commandcode/skills/` and `~/.commandcode/agents/`; prefer shared local skills unless a task needs a tool-specific one, and deliver hard rules through the configured hooks rather than repeating them per prompt.
- Treat configured hooks and trusted-hook entries as trusted input; confirm the supported event names before adding automation.
- Verify discovery after deploy: the agent list shows the six roles and `/configure-models` shows the expected per-task models.
