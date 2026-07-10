## Codex-Specific Notes
- Generated from this repo's `prompts/core.md` plus `prompts/harnesses/codex.md`. Edit the source fragments, then run `scripts/sync-ai-prompts`.
- Model ladder: fast/affordable tier (GPT-5.6 Luna-class) = lower cost; balanced tier (Terra-class) = routine work; flagship (Sol-class, current Codex CLI default) = hardest reasoning and long-horizon work; Codex-tuned GPT = coding-specialized. Verify exact model IDs and auth-plan availability before scripting; do not freeze stale names in prompts.
- Effort: Codex/OpenAI reasoning effort names and availability are model-dependent. Prefer explicit effort flags in automation when supported, but verify current CLI/docs first.
- Codex discovers `AGENTS.md` in a stable chain: `$CODEX_HOME/AGENTS.md` (global, default `~/.codex/`), then project root down to CWD; fallback filenames and size limits are configurable.
- Invoke skills through the current Codex harness mechanism before relevant work; for automation, use `codex exec` and explicit flags such as `--json`, `-o`, `--ephemeral`, and `--skip-git-repo-check` when they improve determinism.
- `codex exec` accepts prompt plus stdin for pipelines.
- Prefer structured output for scripted Codex calls and keep prompts self-contained.
