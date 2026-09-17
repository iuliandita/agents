## Hermes Notes
- Global operational rules: `agent.coding_instructions` (or `agent.system_prompt`) in `$HERMES_HOME/config.yaml`, defaulting to `~/.hermes/config.yaml` (`%LOCALAPPDATA%\hermes` on native Windows). Override the whole tree with `HERMES_HOME`.
- Project rules load exactly one file, first match wins: `.hermes.md`/`HERMES.md`, then `AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`, then `.cursorrules`; `AGENTS.md` also merges as a git-root-to-CWD chain.
- Deploy project rules with `HERMES_AGENTS_PATH` pointing at `HERMES.md` or `AGENTS.override.md`. Leave `SOUL.md` alone: it is identity and persona, slot 1 of the prompt, and outside this repo's scope.
- The desktop app shares `$HERMES_HOME` with the CLI (same config, sessions, skills, memory). Non-interactive: `hermes chat -q`, or `--oneshot`/`-Q` for programmatic runs.
- Skills live in `$HERMES_HOME/skills/` and become slash commands; preload with `hermes -s name`.
- Delegation uses the `delegate_task` tool, configured under `delegation:` in `config.yaml`; subagents get their own conversation and terminal.
- Hooks are plugin, gateway, shell, or webhook hooks configured in `config.yaml`; deliver the hard rules through a hook instead of repeating them per prompt.
- Context files are injection-scanned and truncated (dynamic cap, floor 20,000 chars); keep the global rules short.
- Verify discovery after deploy: `/context` lists the loaded files and `hermes config get agent.coding_instructions` shows the merged rules.
