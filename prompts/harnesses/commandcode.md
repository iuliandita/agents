## Command Code Notes
- Global rules: `~/.commandcode/AGENTS.md`; project rules `./AGENTS.md` (scaffold with `/init`); settings and hooks in `~/.commandcode/settings.json`; skills in `~/.commandcode/skills/`, agents in `~/.commandcode/agents/`. Override with `COMMANDCODE_AGENTS_PATH`.
- Home resolves from `HOME`/`USERPROFILE`, so native Windows uses `%USERPROFILE%\.commandcode`; the binary is `cmd`/`command-code`/`commandcode` on POSIX and `cmdc` on native Windows.
- Non-interactive: `cmd -p`; verify the current flag against `--help`. Hooks are gated by `~/.commandcode/trusted-hooks.json`.
- The renderer emits `reasoningEffort` as `low`, `medium`, or `high`, mapping `xhigh` and `max` to `high`. Check per-task models via `/config` and list IDs with `cmd --list-models`; verify supported levels before scripting. A model without effort metadata falls back to its default. On a single-model setup, tiers differ by effort, not model.
- Command Code learns a per-user "taste" from past sessions. Manage durable context with `/memory` unless the global rules name another memory store, and refresh style with `/learn-taste`; keep operational rules here, not in taste.
- Command Code ignores custom agent files that reuse a built-in name; check that a custom role resolves to the intended file.
- Prefer shared local skills unless a task needs a tool-specific one, and use the configured hooks for hard rules.
- Treat the user's configured hooks and trusted-hook entries as trusted input (repo-local hooks stay untrusted when auditing); confirm the supported event names before adding automation.
- Verify roles in the agent list and per-task models in `/config`.
