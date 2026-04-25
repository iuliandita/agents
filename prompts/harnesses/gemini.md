## Gemini-Specific Notes
- Generated from this repo's `prompts/core.md` plus `prompts/harnesses/gemini.md`. Edit the source fragments, then run `scripts/sync-ai-prompts`.
- Model ladder: Flash-Lite = lower cost/high throughput; Flash = balanced speed and capability; Pro = strongest reasoning and long-context work. Use family names in guidance and verify exact model codes before scripting.
- Effort/thinking: Gemini exposes thinking controls differently across models and products; verify the current CLI/API support before assuming a reasoning-effort flag.
- Global instruction file target: `~/.gemini/GEMINI.md`.
- `GEMINI.md` participates in Gemini CLI hierarchical memory; `/memory show` can inspect the concatenated loaded context.
- Use `@file.md` imports when modularizing large Gemini memory files.
- Activate relevant skills through Gemini's current skill mechanism before starting skill-adjacent work.
