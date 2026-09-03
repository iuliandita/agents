# Prompt Guide Refresh Design

Date: 2026-09-03

## Purpose

Bring the global prompt sources and subagent roster in line with the current
vendor prompting guides: Anthropic's Claude Fable 5.1, Fable 5, and Opus 5
guides plus the cross-model best practices, and OpenAI's "Using GPT-5.6" and
AGENTS.md guidance. GPT-6 / Astra had no release or guide at the time of
writing, so nothing is carried over from it.

The goal is better final-message clarity, a verb-level autonomy policy that
works on every harness, less subagent overtriggering, and formatting rules
that fit models which now under-format rather than over-format. The vendor
guides agree on one meta-rule: subtract before adding. Core stays at or below
its 100-line cap.

## Scope

In scope:

- `prompts/core.md`: lead-with-outcome and re-grounding rules, an Autonomy
  section with the verb policy, finish-the-task and batching rules, positive
  formatting rule, mannered-prose anti-pattern, effort baseline rule, sharper
  stale-name verification, delegation damping, verifier scoped to noisy checks.
- `prompts/harnesses/claude.md`: replace the Fable narration sentence now in
  core with the long-output effort note and the safeguard false-positive
  phrasing.
- `prompts/harnesses/codex.md`: one sentence on GPT-5.6 leanness, effort
  comparison one level lower, and exposing only the tools a task needs.
- `agents/explorer.md`, `agents/researcher.md`: batch independent reads and
  searches in one response; researcher also searches the name as written.
- `agents/verifier.md`: redact base64 blobs alongside secrets.
- README subagent roster: verifier scoping sentence.
- Tests pinning the new phrases.

Out of scope, tracked as follow-ups:

- Compaction-preservation instruction for the `handoff` skill (skills repo).
- Memory lesson-recording rule for the private overlay.
- Mapping the `cheap` tier to Fable 5.1 at low effort as a local experiment.
- Any change to `opencode.md`, `commandcode.md`, builder, planner, reviewer.

## Decisions

- Autonomy, finish-the-task, and batching rules live in core in compact form.
  Claude Code injects similar text itself; the duplication is a few lines and
  buys coverage on Codex, OpenCode, and Command Code, which have none.
- `verifier` stays in the dispatch list but is scoped to checks whose output
  would flood the main context. Short checks run inline. This reconciles the
  Opus 5 guidance against verifying through subagents with the roster's
  purpose.
- Core adopts the selectivity rule for brevity (drop detail, not sentences).
  The local caveman hook remains a per-session override and is not addressed
  here.
- Line budget is paid by merging bullets that carry one idea across two lines,
  not by dropping rules. Every pinned test phrase survives.

## Core Changes

Tone: "Keep replies short unless the task needs depth" becomes lead with the
outcome, then evidence, caveat, next action; shorten by selectivity, not
fragments. Add the cadence rule: one line before the first tool call, updates
only on findings or direction changes, final message written for a reader who
saw none of the work in full sentences with no working shorthand.

Autonomy (new section): answer, explain, review, or a problem described aloud
means inspect and report; change, build, fix means do it and validate without
confirmation for safe local actions; external, destructive, costly, or
scope-expanding actions need confirmation. Check evidence before a
state-changing command. Finish the whole task; a blocked part does not scale
down the rest. Do not end a turn on a plan or promise. Batch independent tool
calls.

Formatting: positive rule for when lists apply; literal phrase over metaphor.

Model Selection: vendor default as baseline, compare one level lower, long
deliverables at the default effort.

Verification: recognizing a name is not knowing its current state; search the
name as written for models and developer tools.

Delegation: no delegation for work that fits in a handful of tool calls; one
agent over several; keep working while subagents run and intervene on drift;
verifier only for noisy checks.

## Verification

- `python scripts/lint_prompts.py` clean, no WARN lines.
- `python scripts/scan_prompt_sources.py`, `python scripts/check_harness_docs.py`.
- `python -m pytest -q` with new phrase pins.
- `scripts/sync-ai-prompts --check`, `scripts/render-agents --check`, and
  `scripts/sync-ai-prompts --dry-run` before local deploy.
