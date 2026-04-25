# Autoresearch Workflow

This repo uses a small version of the Karpathy autoimprove pattern:

1. Score the current repo.
2. Ask an agent for one bounded improvement.
3. Verify the result.
4. Keep the diff only when verification passes.

The score is intentionally mechanical today:

- `python scripts/lint_prompts.py`
- `python scripts/scan_prompt_sources.py`
- `python -m pytest -q`
- `python scripts/render_prompts.py --out-dir build/generated`

That gives the loop a hard floor: no private path leaks, no token-looking strings, no CRLF line endings, no injected override or exfiltration instructions, no zero-width or Unicode-tag payloads, all harness fragments present, renderer behavior intact, and output generation still works.

`prompts/private.md` is intentionally ignored by git. The loop may read it during local render checks, but public improvements should go into `prompts/core.md`, `prompts/harnesses/`, docs, tests, or scripts.

## Run

```bash
scripts/autoimprove-prompts --iterations 3 --mode step
```

`step` mode stops after the first verified diff so a human can review it. `auto` mode keeps going until the iteration cap, a no-change result, or a verification failure.

## Harness Selection

The script checks for `claude`, then `codex`, then `opencode` unless overridden:

```bash
scripts/autoimprove-prompts --harness codex
AGENTS_AUTOIMPROVE_HARNESS=claude scripts/autoimprove-prompts
```

The prompt asks for small improvements only. This repo is configuration, not application code, so big rewrites are usually a regression.

## Keep Or Stop

The current script does not silently revert failed attempts. It leaves the diff in place and stops. That is intentional: prompt changes are subjective enough that failed verification should be inspected, not erased without context.
