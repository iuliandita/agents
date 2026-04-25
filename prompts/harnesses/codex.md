## Codex-Specific Notes
- Generated from this repo's `prompts/core.md` plus `prompts/harnesses/codex.md`. Edit the source fragments, then run `scripts/sync-ai-prompts`.
- Model ladder: mini/smaller GPT = lower cost/fast; current GPT = default high-capability general coding; Codex-tuned GPT = coding-specialized; Pro/Max/frontier variants = hardest long-horizon work. Verify exact model IDs and auth-plan availability before scripting; do not freeze stale names in prompts.
- Effort: Codex/OpenAI reasoning effort names and availability are model-dependent. Prefer explicit effort flags in automation when supported, but verify current CLI/docs first.
- `AGENTS.md` is Codex's project instruction file; nested or child `AGENTS.md` behavior depends on current Codex features and config.
- Invoke skills through the current Codex harness mechanism before starting relevant work.
- Automation: use `codex exec`. In scripts, prefer explicit flags such as `--json`, `-o`, `--ephemeral`, and `--skip-git-repo-check` when they improve determinism.
- `codex exec` accepts prompt plus stdin for pipelines.
- Prefer structured output for scripted Codex calls and keep prompts self-contained.
