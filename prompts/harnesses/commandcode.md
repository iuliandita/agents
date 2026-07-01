## Command Code-Specific Notes
- Generated from this repo's `prompts/core.md` plus `prompts/harnesses/commandcode.md`. Edit the source fragments, then run `scripts/sync-ai-prompts`.
- Global rules file: `~/.commandcode/AGENTS.md`; project rules live in `./AGENTS.md` (scaffold with `/init`).
- Command Code learns a per-user "taste" from past sessions. Manage durable context with `/memory` and refresh style with `/learn-taste`; keep operational rules here, not in taste.
- Models are per-task: set the main model and feature models (compaction, title generation, tool descriptions) via `/configure-models`. Use family names in guidance and verify current model IDs before scripting.
- Hooks are configured in `~/.commandcode/settings.json` (for example `PreToolUse`, `PostToolUse`, `Stop`) and gated by `~/.commandcode/trusted-hooks.json`; confirm the supported event names before wiring automation.
- Skills and agents load from `~/.commandcode/skills/` and `~/.commandcode/agents/`; prefer shared local skills unless a task needs a tool-specific one.
- Binaries: `cmd`, `command-code`, `commandcode`. Verify non-interactive/exec flags against current CLI help before relying on them in scripts.
