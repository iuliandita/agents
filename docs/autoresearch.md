# Autoresearch Workflow

This repo uses a small version of the Karpathy autoimprove pattern:

1. Score the current repo.
2. Ask an agent for one bounded improvement.
3. Verify the result.
4. Report a verified candidate, or stop and leave a failed diff for inspection.

The score is intentionally mechanical today:

- `python scripts/lint_prompts.py`
- `python scripts/scan_prompt_sources.py`
- `python -m pytest -q`
- `python scripts/render_prompts.py --out-dir build/generated`

These gates check known private-path and secret patterns, line endings, suspicious
prompt instructions, Unicode payloads, harness fragments, tested behavior, and output
generation. They do not prove that arbitrary prompt changes are safe or better.
Review the diff before accepting it, and run the full [repository checks](../README.md#verification)
before shipping; the loop's score is not the complete release checklist.

`prompts/private.md` is intentionally ignored by git. The loop may read it during local render checks, but public improvements should go into `prompts/core.md`, `prompts/harnesses/`, docs, tests, or scripts.

## Run

```bash
scripts/autoimprove-prompts --iterations 3 --mode step
```

`step` mode stops after the first verified diff so a human can review it. `auto` mode keeps going until the iteration cap, a no-change result, or a verification failure.

## Harness Selection

The script checks for `claude`, then `codex`, then `opencode`, then Command Code
(`commandcode`, `command-code`, or `cmd`) unless overridden:

```bash
scripts/autoimprove-prompts --harness codex
AGENTS_AUTOIMPROVE_HARNESS=claude scripts/autoimprove-prompts
```

`AGENTS_AUTOIMPROVE_MODE` also sets `step` or `auto`. An explicit CLI flag takes
precedence over its environment setting. A missing or failed harness stops the run
with a nonzero exit; it does not count as a successful improvement.

The prompt asks for small improvements only. This repo is configuration, not application code, so big rewrites are usually a regression.

## Keep Or Stop

The current script does not silently revert failed attempts. It leaves the diff in place and stops. That is intentional: prompt changes are subjective enough that failed verification should be inspected, not erased without context.

The wrapper does not itself commit, push, or deploy, but it does not prohibit those
actions in the invoked harness. Review that harness's permissions and approval policy
before running the loop. `auto` runs bounded improvement attempts; it is not a scheduled
monitor. Start from a reviewed worktree so candidate edits are easy to distinguish
from existing work.
