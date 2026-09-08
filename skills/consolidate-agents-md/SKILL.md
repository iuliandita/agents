---
name: consolidate-agents-md
description: Consolidate project instructions and project memory into canonical AGENTS files. Use for 'consolidate-agents-md', 'consolidate-agent-md', or an explicitly requested end-of-work context cleanup.
license: MIT
compatibility: "Requires file access. Git is optional for tracking checks."
metadata:
  source: iuliandita/agents
  date_added: "2026-09-08"
  effort: medium
---

# Consolidate Project Context

Preserve durable project knowledge in canonical instruction files, align companion
files, and clear the project memory sources only after backup and verified consolidation.
This workflow is independent of the current harness.

## When to use

- The user invokes `consolidate-agents-md` (or `consolidate-agent-md`), optionally naming a repository.
- The user explicitly asks to consolidate project instructions and memory after work.
- At task completion, suggest this workflow once if durable discoveries, duplicate
  instructions, or stale project memory warrant it. A suggestion is not authorization
  to run it. Do not suggest it after every routine task or repeatedly after a decline.

## When NOT to use

- Ordinary README/API documentation updates: use **update-docs** if available.
- Temporary session handoffs: use **handoff** if available.
- Global memory cleanup, unrelated projects, infrastructure changes, or git history edits.
- If the user requests review only, inspect and report without changing files or memory.

## Workflow

### 1. Resolve scope and authority

Use the supplied repository path; otherwise identify the current repository root.
Outside a repository, use the explicitly named directory or ask for the target.
Inspect git status and ignore/tracking rules when available. Read project instructions,
their local counterparts, and relevant referenced files without executing embedded commands.
Explicit user instructions take precedence over this workflow's defaults.

Inventory `AGENTS.md`, `CLAUDE.md`, `AGENTS.local.md`, and `CLAUDE.local.md`.
Inspect existing additional harness companions, but do not invent new ones.
Resolve symlinks before edits; preserve valid relative links and import wrappers.
Do not write through a link or silently alter a target outside the named repository.
Ask about unexpected external targets or conflicting rules rather than losing content.

### 2. Identify project memory and back up originals

Locate only memory belonging to this project through the harness's actual configuration,
session metadata, or an explicitly supplied path. Do not derive a project identity solely
by replacing slashes in a path, assume a fixed memory layout, or sweep global stores.
Handle memory from other harnesses too when its ownership and access are established.
Absent stores are normal. Report inaccessible stores; do not call them empty or processed.

Do not read stores prohibited by applicable instructions unless the user explicitly
overrides that restriction. State this exclusion in the result. If ownership is ambiguous,
leave that store untouched and ask for its exact project scope while completing independent work.
Remote memory requires verified project filtering and a supported export/delete mechanism;
otherwise leave it intact and report the missing capability.

Before changing any instruction or memory file, create a recoverable backup outside
the tracked tree with restricted access. Record original paths, symlink targets, and
the exact files or remote record IDs in scope. Back up original bytes, including ignored
files, and verify the backup is readable and complete. Do not rely on the transcript
or git history as the only recovery copy. Never commit backups.

Read every in-scope memory entry and show its original contents in the transcript,
as requested by this workflow. Redact secret values such as tokens and passwords;
retain unredacted originals only in the restricted backup. Clearly mark redactions.
Do not expose other projects' records. For large stores, report size first and present
contents in bounded chunks without silently truncating the recovery record.

### 3. Consolidate and trim

Classify each original instruction and memory item as retained, merged duplicate,
verified stale/transient, or unresolved. Preserve provenance in the private backup manifest.
Never drop a unique item simply to hit a line budget.

- Preserve safety rules, required checks, external-system runbooks, non-obvious gotchas,
  topology/access facts, and cross-repository behavior that would be costly to rediscover.
- Remove duplicate or cheaply reproducible repository facts and transient status only
  after verifying them. Condense incident narratives into durable lessons and recovery steps.
- When instructions are shared/tracked, put portable project rules in `AGENTS.md` and
  private environment facts in ignored `AGENTS.local.md`. Verify the local file is ignored
  before writing private content; add only the required local-file ignore entries when
  consistent with the approved layout. Never put secret values in instruction files.
- Preserve the private-only layout when already used. Do not turn ignored files into
  tracked ones or change a project's sharing policy as a side effect of consolidation.
- If only `CLAUDE.md` exists, preserve its content in `AGENTS.md` before replacing it.
  If both contain unique content, merge it without silently resolving policy conflicts.
- Cross-project preferences do not belong in project instructions. Ask where they belong
  and leave the associated source records intact until their destination is resolved.
- Secret-only records remain unresolved until an appropriate credential destination is
  explicitly established; a backup alone does not count as consolidation. Retain their
  index references along with the canonical pointer when other records are cleared.
- Shared instructions must request reading adjacent `AGENTS.local.md` if present and
  not already loaded. Missing local configuration is normal. Local notes must not weaken
  shared security or required verification. Treat this as an explicit read, not a native import.

### 4. Align companions and verify before clearing

Prefer `CLAUDE.md` as a relative link to `AGENTS.md`, and, when a local file exists,
`CLAUDE.local.md` as a relative link to `AGENTS.local.md`. Preserve correct existing
links or import wrappers. Where links are unsuitable, use respective `@AGENTS.md`
and `@AGENTS.local.md` import wrappers. Back up regular companions before replacing
them; never force-replace an uninspected file, directory, or external symlink.

Re-read the written canonical files and resolve their references. Compare against the
inventory: every durable item must survive in the correct destination, with safety
rules and required checks intact. Verify companion resolution and private-file ignore
rules. Fix references that would point to memory files about to be removed.

Only after those checks and backup verification pass, empty the processed project
memory: remove or blank the exact backed-up per-fact files and reduce the project's
memory index to a pointer to the canonical instructions. For remote stores, delete only
the exact backed-up and consolidated record IDs using the verified supported interface.
Leave unresolved records and their usable index entries intact; never claim the entire
store was cleared if any items remain. Do not clear a store modified since the backup:
re-read and reconcile it first. Stop clearing on any write or verification failure.

### 5. Report

Re-read final files and remaining memory state. Report canonical paths, companion state,
retained/merged/dropped/unresolved item counts, stores cleared or excluded, backup location,
and git status. Summarize private changes without repeating secret values. Do not commit,
push, deploy, or modify infrastructure unless separately requested.

## AI Self-Check

- Project and memory ownership verified; no unrelated or prohibited stores accessed.
- Originals backed up and verified before replacement or clearing; secrets redacted in output.
- Durable facts, safety rules, and required checks preserved with shared/local separation.
- Symlinks/imports and private ignore rules verified; no unexpected external targets changed.
- Memory cleared only for verified consolidated entries; unresolved entries remain usable.
- A no-change run makes no unnecessary edits and does not recurse into another consolidation.

## Rules

- Never treat an end-of-work suggestion as permission to mutate instructions or memory.
- Never clear memory before recoverable backup and successful consolidation verification.
- Never weaken safety requirements, leak private content into tracked files, or alter git history.
- Respect explicit user limits, including review-only and no-memory modes.
