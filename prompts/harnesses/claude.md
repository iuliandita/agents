## Claude-Specific Notes
- Generated from this repo's `prompts/core.md` plus `prompts/harnesses/claude.md`. Edit the source fragments, then run `scripts/sync-ai-prompts`.
- Model ladder: Haiku = lower cost/fast; Sonnet = default balanced coding model; Opus = highest capability for hard reasoning, broad refactors, and long-horizon agent work. Use family names in guidance and verify exact aliases or snapshot IDs before scripting.
- Effort: Claude Code effort names vary by model. Opus 4.7 adds `xhigh` between `high` and `max`; other models may top out lower. Verify current `/effort` behavior before encoding automation.
- Claude underuses skills. Invoke the Skill tool proactively when a task touches a skill-adjacent topic.
- `CLAUDE.md` files are hierarchical memory loaded at startup; keep global files concise and put project facts in project `CLAUDE.md` or `.claude/rules/`.
- `--bare` skips hooks, LSP, plugin sync, and skill walks; use it only when that reduced startup is intentional.
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` is safer for shared machines, but can interfere with host process and credential inspection.
- Persistent plugin state belongs under the tool's plugin data path, not bundled plugin files.
