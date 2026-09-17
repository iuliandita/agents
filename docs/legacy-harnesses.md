# Legacy Harnesses

These targets were removed from the registry so the repo only claims harnesses whose rules path was
verified against upstream docs. The fragments remain in git history. To bring one back, restore its
fragment and follow the steps below.

## Removed

| Harness | Removed fragment | Notes |
|---|---|---|
| Aider | `prompts/harnesses/aider.md` | No global AGENTS.md; conventions load via `read:` in `.aider.conf.yml`. |
| Amp | `prompts/harnesses/amp.md` | Global path is `~/.config/amp/AGENTS.md`, not `~/.amp/`. |
| Augment | `prompts/harnesses/augment.md` | User rules live in `~/.augment/rules/`, not a single file. |
| Cline | `prompts/harnesses/cline.md` | Global rules in `~/Documents/Cline/Rules`. |
| Continue | `prompts/harnesses/continue.md` | Rules in `~/.continue/rules/*.md` + `config.yaml`. |
| GitHub Copilot CLI | `prompts/harnesses/copilot.md` | Global file is `~/.copilot/copilot-instructions.md`. |
| Crush | `prompts/harnesses/crush.md` | Path was correct; removed by scope decision. |
| Cursor | `prompts/harnesses/cursor.md` | No global AGENTS.md; user rules live in Settings. |
| Gemini CLI | `prompts/harnesses/gemini.md` | Legacy; superseded by Antigravity (shared path). |
| Goose | `prompts/harnesses/goose.md` | No user-level instruction file documented. |
| Kimi Code | `prompts/harnesses/kimi.md` | Removed by scope decision; path was unverified. |
| Kiro | `prompts/harnesses/kiro.md` | Global rules in `~/.kiro/steering/*.md`. |
| NanoClaw | `prompts/harnesses/nanoclaw.md` | Render-only; no verified target. |
| OpenClaw | `prompts/harnesses/openclaw.md` | Removed by scope decision. |
| OpenHands | `prompts/harnesses/openhands.md` | No global AGENTS.md; repo microagents only. |
| Pi Coding Agent | `prompts/harnesses/pi.md` | Removed by scope decision. |
| Qwen Code | `prompts/harnesses/qwen.md` | Global memory is `~/.qwen/QWEN.md`. |
| Roo Code | `prompts/harnesses/roo.md` | Global rules in `~/.roo/rules/`. |
| Windsurf | `prompts/harnesses/windsurf.md` | Global rules at `~/.codeium/windsurf/memories/global_rules.md`, 6k cap. |
| Warp | `prompts/harnesses/AGENTS.md` (generic fragment) | Global rules live in Warp Drive, not a file. |

## Re-adding a harness

1. Restore the fragment from git history: `git log --all --diff-filter=D -- prompts/harnesses/<name>.md`
   then `git show <commit>^:prompts/harnesses/<name>.md > prompts/harnesses/<name>.md`.
2. Add a registry row in `scripts/render_prompts.py:HARNESSES` with `source_url`, `verified_on`, and
   `confidence`.
3. Record the path and precedence in `docs/harness-contract.md` and `docs/surfaces.md`.
4. Update the harness tables in `README.md` and `INSTALL.md`.
5. Add or update tests in `tests/test_render_prompts.py` and `tests/test_harness_docs.py`.

Removing a harness from the registry never rewrites history and never deletes a deployed file; it only
stops the repo from rendering or claiming it.
