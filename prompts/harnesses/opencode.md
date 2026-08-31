## OpenCode-Specific Notes
- Generated from this repo's `prompts/core.md` plus `prompts/harnesses/opencode.md`. Edit the source fragments, then run `scripts/sync-ai-prompts`.
- Global rules file: `~/.config/opencode/AGENTS.md`. Some installs fall back to Claude-compatible files when OpenCode-specific rules are missing.
- Scripted non-interactive execution uses `opencode run`.
- Skills are native, no plugin required. Discovery spans global `~/.claude/skills`, `~/.agents/skills`, and `~/.config/opencode/skills`, then project `.claude/skills`, `.agents/skills`, and `.opencode/skills` searched upward from CWD, with later sources winning.
- Extra skill paths and model/provider settings live in `opencode.json` or `opencode.jsonc`; verify keys against the published config schema before editing.
- Prefer shared local skills unless the task explicitly requires a tool-specific skill.
