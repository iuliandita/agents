# Changelog

All notable changes to this project are documented here. The project uses semantic versioning once it
reaches `v1.0.0`; until then the `v0.x` line is the prerelease phase.

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
