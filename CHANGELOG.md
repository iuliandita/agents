# Changelog

All notable changes to this project are documented here. The project uses semantic versioning once it
reaches `v1.0.0`; until then the `v0.x` line is the prerelease phase.

## [Unreleased]

### Added

- Oh My Pi (`omp`) harness: global rules at `~/.omp/agent/AGENTS.md` (follows `PI_CODING_AGENT_DIR`), and
  the six roles as task agents in `~/.omp/agent/agents/` with `@smol`/`@default`/`@slow` role aliases and
  `thinkingLevel`. The rendered `reviewer` replaces omp's bundled one.
- `max` effort level for roles, overrides, and effort maps.
- Tier entries can carry an effort: `{"model": "...", "effort": "..."}`. A harness that runs one model on
  every tier (for example DeepSeek V4.1 Flash) now varies depth by tier. Precedence is per-agent override,
  then tier, then role. `models.local.json` files that use tier objects or `max` fail on older checkouts.

### Changed

- Claude Code cheap tier is Sonnet 5 at `low` effort; Haiku 4.5 has no effort control and is near retirement.
  Claude notes describe Opus 5.5 with its `medium` default and Fable 5.1 as apex only.
- Codex tiers move to GPT-6: Luna (cheap), Sol (mid and flagship, split by effort), Astra (apex).
- Command Code defaults use its own model IDs (`deepseek/deepseek-v4.1-flash`, `claude-sonnet-5`,
  `claude-opus-5-5`) instead of stale OpenRouter IDs. OpenCode and Command Code map `max` to `high` by
  default; Claude Code and Codex pass `max` through.
- Claude notes cover the `AGENTS.md` fallback and the `"attribution": false` setting.

## [2.3.0] - 2026-09-20

### Changed

- Delegate bounded work by default, with the main model coordinating decisions, integration, and
  verification. Batch small tasks and keep trivial actions inline when delegation adds cost.
- Choose model and reasoning effort per task, accounting for context, retries, and verification costs.
- Use Jev/TypeSafe for suitable bounded decisions when a configured API key and relevant installed
  skill are available, with fallback when access, evidence, or service reliability is insufficient.

## [2.2.0] - 2026-09-17

### Changed

- The private overlay (`prompts/private.md`) is applied to Claude Code and Codex only by default. Add
  harnesses with `AGENTS_PRIVATE_HARNESSES` (comma-separated) or `prompts/private-harnesses.txt` (one
  name per line). This keeps home-lab hosts, identities, and local paths out of third-party models.
- The workflow installer uses only the standard library; installing the consolidation skill no longer
  needs PyYAML (PyYAML remains a test-only dependency).
- `scripts/check_harness_docs.py --write` regenerates the INSTALL harness table from the registry; CI
  still verifies it.

### Fixed

- The public README no longer names a specific workflow plugin in its shared guidance.

## [2.1.1] - 2026-09-17

### Fixed

- Rendered headers no longer embed `git describe`. The revision is purely content-derived, so a commit
  or tag no longer makes every deployed file report drift in `--status` or trigger redeploys.

## [2.1.0] - 2026-09-17

### Added

- `scripts/render-hermes` merges the shared core into Hermes `agent.coding_instructions` with a
  comment-preserving line edit and a backup, giving Hermes the same global-rules channel as the rest.

## [2.0.0] - 2026-09-17

### Breaking

- The supported harness set is reduced to Claude Code, Codex, OpenCode, Command Code, Antigravity,
  Hermes Agent, plus the generic project-level `AGENTS.md` target. 19 unverified harness targets were
  removed; see `docs/legacy-harnesses.md` for the re-add recipe.
- `--deploy` now requires `--target`, and a harness with no model tier map fails unless
  `--allow-inherit` is passed.

### Changed

- Cut the supported harness catalog to Claude Code, Codex, OpenCode, Command Code, Antigravity, and
  Hermes Agent, plus one generic project-level `AGENTS.md` target. Removed 19 unverified targets and
  added dated receipts in `docs/harness-contract.md`, `docs/surfaces.md`, and `docs/legacy-harnesses.md`.
- Moved model and effort defaults into the tracked `prompts/models.json`. OpenCode and Command Code now
  tier out of the box, and a harness with no tier map fails unless `--allow-inherit` is passed.
- Brought the six harness fragments to one section template and de-pluginned the public core.
- Added an Antigravity subagent renderer; Hermes roles are documented as a manual paste.
- Prompt deploys now use a content-hash revision stamp, enforce per-harness size budgets, refuse
  symlinked destinations, require `--target`, and record `build/deploy-manifest.json`.

### Added

- `--status` to report deployed files that differ from a fresh render.

### Removed

- The `scripts/autoimprove-prompts` loop and `docs/autoresearch.md`; the mechanical score measured
  validity, not improvement, and the candidate could edit its own checks.
