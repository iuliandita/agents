## OpenCode-Specific Notes
- Generated from this repo's `prompts/core.md` plus `prompts/harnesses/opencode.md`. Edit the source fragments, then run `scripts/sync-ai-prompts`.
- Global rules file: `~/.config/opencode/AGENTS.md`. Some installs fall back to Claude-compatible files when OpenCode-specific rules are missing.
- Scripted non-interactive execution uses `opencode run`.
- Skill discovery may include repo-local `.opencode/skills/`, `.claude/skills/`, `.agents/skills/` and global OpenCode or shared skill paths.
- Prefer shared local skills unless the task explicitly requires a tool-specific skill.
