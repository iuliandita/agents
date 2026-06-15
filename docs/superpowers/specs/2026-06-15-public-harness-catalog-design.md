# Public Harness Catalog Design

Date: 2026-06-15

## Purpose

This repo is public and should model broad coding-agent harness support, not only the tools installed on one machine. The renderer should cover major harnesses with operational rules files while avoiding persona, memory, identity, or assistant-profile generation.

The catalog needs enough metadata to say which targets can be deployed safely and which variants are render-only or documentation-only.

## Scope

In scope:

- Add major public harness variants backed by current primary documentation or a strong public integration catalog.
- Generate only operational rules or equivalent project guidance.
- Keep persona files out of scope, including `SOUL.md`, identity files, user memory, heartbeat files, and assistant profile files.
- Make deploy behavior safe when multiple harnesses share the same target path.
- Keep docs and tests synchronized with the renderer registry.

Out of scope:

- Installing any harness locally.
- Generating provider credentials, model settings, MCP config, skills, plugins, memory files, or persona files.
- Guessing global deploy paths for tools whose documentation only supports project-local rules.

## Support Levels

Extend the harness registry with a support level:

- `deployable`: a verified single global operational rules path exists.
- `manual`: the renderer supports the variant, but deploy needs an explicit environment override or project-local placement because no verified global path is known.
- `documented-no-target`: the entry is useful in docs as a provider, ecosystem, or watchlist item, but it is not rendered as a global operational rules file.

`scripts/sync-ai-prompts --list-targets` should show support level or otherwise make manual entries obvious. `--deploy` should deploy only entries with a safe resolved target path.

## First-Wave Harnesses

Add these as first-class renderer entries:

- Antigravity CLI / `agy`: deployable. Operational rules path: `~/.gemini/GEMINI.md`. Keep Gemini CLI as a legacy target and document the consumer transition to Antigravity. Because Antigravity and Gemini can resolve to the same path, full-catalog deploy must refuse ambiguous same-path writes unless the user selects one target or overrides paths.
- Pi Coding Agent: deployable. Operational rules path: `~/.pi/agent/AGENTS.md`.
- OpenClaw: deployable. Operational rules path: `~/.openclaw/workspace/AGENTS.md`. Do not generate `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`, `HEARTBEAT.md`, or memory files.
- Crush: deployable. Operational rules path: `~/.config/crush/CRUSH.md`.
- Kimi Code: manual. Render an `AGENTS.md` operational variant, but do not invent a global deploy path unless documentation confirms one. Project-local `AGENTS.md` and `.kimi/AGENTS.md` support should be documented.
- Hermes Agent: manual. Render a `HERMES.md` operational variant for project rules only, not `~/.hermes/SOUL.md`.
- NanoClaw: manual. Render a `CLAUDE.md` per-agent operational variant. Do not generate persona, memory, or container config.

Keep the existing broad entries, including Warp, because public support should not depend on local installation.

## Watchlist

Document, but do not necessarily render in the first wave:

- Devin for Terminal
- Junie
- Kilo Code
- iFlow CLI
- Lingma
- Mistral Vibe
- Qoder CLI
- Rovo Dev
- SHAI
- Tabnine CLI
- Trae
- CodeBuddy
- Forge

Treat Z.ai and MiniMax as provider/tool integrations unless current docs identify a standalone operational rules harness. They should not become deployable prompt targets just because their models or CLIs can be used from other agents.

## Renderer Behavior

The existing renderer remains the source of truth. The `Harness` record should gain enough metadata for:

- support level
- optional notes for deprecated or replacement targets
- target safety checks

Rendering to `build/generated/` should still include supported variants. Harnesses that share output filenames should continue rendering into per-harness subdirectories.

Deploy should fail before writing when two selected deployable harnesses resolve to the same target path. The error should name both harnesses and the colliding path.

Manual entries should render by default into `build/generated/`, but deploy only when an explicit environment override supplies a target path. Full deploy and dry-run should report skipped manual entries clearly.

Use predictable environment variable names for new targets:

- `ANTIGRAVITY_AGENTS_PATH`
- `PI_AGENTS_PATH`
- `OPENCLAW_AGENTS_PATH`
- `CRUSH_AGENTS_PATH`
- `KIMI_AGENTS_PATH`
- `HERMES_AGENTS_PATH`
- `NANOCLAW_AGENTS_PATH`

Antigravity should get its own fragment because it is the forward-looking Google harness. Gemini CLI should keep its existing fragment as a legacy target.

Kimi, Hermes, and NanoClaw should each get their own fragments. Even when the content is mostly generic operational guidance, the fragment header should explain the tool-specific file semantics so users do not confuse operational rules with persona, memory, or provider configuration.

## Documentation

Update README and INSTALL so they:

- describe public catalog support rather than local installed-tool support
- list deployable and manual targets distinctly
- explain Gemini CLI legacy status and Antigravity replacement timing as of 2026-06-15
- clarify that this repo renders operational rules only, not persona or memory files
- keep `scripts/check_harness_docs.py` authoritative against renderer metadata

## Tests

Add or update tests for:

- new harness names and display names
- support-level metadata
- docs synchronization
- render output shape with added `AGENTS.md` collisions
- deploy refusing same-path collisions
- manual targets not silently writing guessed paths
- missing fragment detection for newly registered renderable entries

Verification should include the existing suite:

```bash
python scripts/lint_prompts.py
python scripts/scan_prompt_sources.py
python scripts/check_harness_docs.py
python -m pytest -q
bash -n scripts/sync-ai-prompts scripts/autoimprove-prompts
python -m py_compile scripts/render_prompts.py scripts/lint_prompts.py scripts/scan_prompt_sources.py scripts/check_harness_docs.py
scripts/sync-ai-prompts --check
scripts/sync-ai-prompts --dry-run
```

## Source Basis

- Google Developers Blog: Gemini CLI consumer transition to Antigravity CLI on 2026-06-18.
- Antigravity documentation: project rules via `GEMINI.md` or `AGENTS.md`.
- Pi documentation: global `~/.pi/agent/AGENTS.md` and hierarchical context files.
- OpenClaw documentation: default workspace `~/.openclaw/workspace` and operational `AGENTS.md`.
- Crush documentation: `~/.config/crush/CRUSH.md` and shared `~/.config/AGENTS.md`.
- Kimi Code documentation: terminal coding agent with project `AGENTS.md` generation/loading.
- Hermes documentation: `SOUL.md` is identity, while project instructions belong in `.hermes.md`, `HERMES.md`, or `AGENTS.md`.
- NanoClaw documentation: per-agent workspace with operational `CLAUDE.md`.
- GitHub Spec Kit integration catalog: broad cross-check for public coding-agent harnesses.
