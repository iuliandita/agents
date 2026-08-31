## Claude-Specific Notes
- Generated from this repo's `prompts/core.md` plus `prompts/harnesses/claude.md`. Edit the source fragments, then run `scripts/sync-ai-prompts`.
- Model ladder: Haiku = lower cost/fast; Sonnet = balanced default; Opus = flagship for hard reasoning, broad refactors, and long-horizon agent work; Fable = tier above Opus for the hardest reasoning. Effort is a real lever: `/effort xhigh` for most coding work, `max` only when correctness outweighs cost. Effort names vary by model, so verify exact model IDs and aliases before scripting.
- Claude underuses skills. Invoke the Skill tool proactively when a task touches a skill-adjacent topic.
- `CLAUDE.md` files are hierarchical memory loaded at startup; keep global files concise and put project facts in project `CLAUDE.md` or `.claude/rules/`.
- `--bare` skips hooks, LSP, plugin sync, and skill walks; `--safe-mode` disables all customizations for troubleshooting. Use either only when that reduced startup is intentional.
- Auto mode is the default permission mode, so assume risky actions are classifier-gated rather than always prompted; deny rules are absolute and can match tool parameters. Subagents and forked side tasks run in the background by default: report them as `[waiting]` and do not close the turn on unfinished agent work.
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` is safer for shared machines but can hide host process and credential detail; persistent plugin state belongs under the tool's plugin data path, not bundled plugin files.
