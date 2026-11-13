# Changelog

All notable changes to this project are documented here. Versions follow semantic versioning.

## [Unreleased]

- Renderer polish: dry-run identifies unmanaged hooks, unreadable role targets fail, unsupported turn caps produce one notice per harness, and byte comparisons rewrite CRLF output to LF. Heading detection ignores fenced code; render checks reject empty cores, missing headers or core text, and leftover optional markers. Relative output and backup directories follow `--repo-root`; Windows drive-qualified `PI_CONFIG_DIR` stays under the home directory. Bash and PowerShell launchers follow symlink chains. Quoted role descriptions decode escapes and doubled apostrophes; native YAML tests validate nested output. Null flagship fallback notices explain session-model inheritance. Writes refuse symlinks and Windows junctions in ancestors as well as final destinations. Breaking: relative artifact paths move under the selected repo, linked ancestors and malformed quoted fields fail, unmanaged hook previews report `would-replace-unmanaged`, and turn-cap notices identify the harness. Back up artifacts, role sources, and consumers before upgrading, use absolute directory overrides for previous locations and real paths instead of links, escape embedded quotes, recognize the new action and harness prefix, and restore the previous checkout and backups to roll back (#224).

- Stack checks validate the canon version, honor configured checkout values, share directory exclusions at every depth, and remove unused canon metadata. Model defaults omit redundant effort mappings without changing rendered roles. Installation docs clarify environment overrides, the 06:30 systemd schedule, and the Hermes status exclusion; tests cover every bundled skill installer target and drop redundant configuration pins (#224).

- Error contract: unexpected failures now report an error without a traceback and retain completed JSON records. Every JSON result includes a mode and records list, including parser and runtime failures; direct entry points reject Python older than 3.11 with exit 3. Breaking: invalid target selections, missing deploy targets, and negative backup counts now exit 2 instead of 1; conflicting modes and abbreviated options are rejected. Back up saved commands before upgrading, spell options in full, select one mode (keeping `--deploy --dry-run` valid), and handle usage failures as exit 2. Restore the saved commands and previous checkout to roll back (#217).

- CI runs the full suite on Linux, macOS, and Windows, expands Python coverage, isolates test homes and Git config, verifies hashed dependencies, and requires tagged-commit checks before release. Windows setup includes virtual environments and runbook commands (#218).

- Deploy safety: preflight all selected prompt and role renders, replace files atomically, record each completed file in the deploy manifest, and preserve corrupt manifests. Unmanaged prompt, role, and hook files now require `--adopt`; back up and review them before upgrading, or restore the affected backup and previous checkout to roll back. Environment-selected targets inside Git worktrees withhold local and private overlays; default global paths keep them. Backups use private permissions, bounded filenames, and retention per source path, including new workflow bundles (#216).

- Correct documentation drift and the consolidation clear loop (#219).

- Prompt rules now align on destructive-action confirmation, subagent blockers, and secrets. Harness notes keep runtime checks and config paths, describe rendered effort values, and require a Codex context cap of at least 40 KiB. Public prompts drop repeated rules and optional routing policy; the line-limit test rejects lint warnings (#204).

- Prompt source scan: dependency trees are skipped at any depth and gitignored local files are skipped in a git checkout, while the deployed overlays under `prompts/` are still scanned (#214).

- Leak and injection scanning now covers skills, templates, model metadata, wrapped instructions, hidden Unicode, and more network-to-interpreter commands; private markers match without case sensitivity, tracked overlays fail lint, and editor copies are ignored (#205).

- OpenCode read-only roles deny unlisted tools; all roles gain budgets, blocker output, and shared data handling. The renderer rejects empty tool expansions, reports unsupported turn caps, and omits unused effort from Antigravity hashes (#201).

- Docs impact check: a breaking receipt that a commit did not change no longer fails the range, so merging the base branch into a feature branch no longer reports a stale breaking change (#212).

- Invariants deployment now installs and refreshes both Claude and Antigravity hooks, validates settings before merging, preserves Unicode, and updates managed hook paths in place. `--harness` selects a channel and `--antigravity-config-dir` relocates Antigravity config (#203).

- Updater: require an allowed branch with an upstream before pulling, allow narrowing with `AGENTS_UPDATE_BRANCHES`, and report Windows lock contention cleanly (#200).

- Hermes merges recognize quoted keys and column-zero comments, refuse duplicate or lost keys and symlinked configs, and withhold overlays from environment-selected configs inside Git worktrees; installation docs include the native Windows default (#202).

- Roles and pipeline (#198).
  - The planner returns `Need the goal: <what is missing>.` instead of asking.
  - The reviewer reviews named files when no diff is given, and puts its `Coverage: partial` line after the findings line.
  - The prompt linter and the tests share one line cap: 100 for core and 20 for a harness fragment.
  - `sync-ai-prompts --deploy` and `--dry-run` report a `bytes` object per harness in `--json`, with the total and a list of rendered sections.

- Core prompt and harness notes: tighter wording with the same behavior, and repeated paths and maintainer notes removed; the Codex render drops from 32,700 to 32,047 bytes (#196).
  - Invariants: only rewriting pushed history needs confirmation, so a local rebase of an unpushed branch does not.

- Core prompt and harness notes: removed rules that contradicted each other (#194).
  - Model routing now has one stated precedence, and the Claude and Codex ladders drop prices and version numbers.
  - The Claude auto-mode note no longer reads as skipping confirmation.
  - The secret ban is unconditional, and the private-infrastructure rule is scoped to public repos.
  - Task-end branch cleanup belongs to the main thread.
  - The Command Code memory and hook notes are scoped.
  - Git: work on a branch rather than the default or release branch unless the repo or user says otherwise, and flag it before committing there.

- Core prompt: the Writing Voice rules now cover commits and PRs/MRs. Both take a `type(scope): description` title, commit bodies are at most three short lines of why, and PR/MR bodies are capped at ten lines. Quick dev text may be lower-case; email, wikis, and external docs are capitalized and proofread (#192).

## [5.2.1] - 2026-11-06

- Core prompt: the marker and question rules say the same in about 600 fewer bytes, so the Codex render fits its 32 KiB budget with personal overlays (#188).

## [5.2.0] - 2026-11-06

- Clarified closing markers, optional sections, and native question tools.

## [5.1.0] - 2026-11-04

- Removed the retired Paperclip harness target.
- Core prompt: agents no longer use `pkill -f` with a literal pattern, which killed their own shell (#180).

## [5.0.1] - 2026-11-03

### Added

- The shared stack check verifies the tracked `AGENTS.md` entry point and the `CLAUDE.md` symlink.

### Changed

- The Antigravity fragment no longer mentions Gemini CLI, and the legacy harness list drops its row. Paths
  and the `GEMINI.md` rules file are unchanged.

## [5.0.0] - 2026-10-29

### Breaking

- Errors, warnings, and notes print as lower-case `error:`, `warning:`, and `note:` lines on stderr, one line
  each. The old upper-case `ERROR:` and `WARN:` lines on stdout, the `notice:` prefix (now `note:`), and
  unprefixed exit texts are gone. This covers the renderers, `scripts/update`, `install_workflow.py`, and the
  `check_*.py`, `lint_prompts.py`, and `scan_prompt_sources.py` checks. To adapt, read stderr instead of
  stdout and match the lower-case prefixes; the exit codes of these paths did not change.
- A missing Python 3.11+ in the launchers, or a missing git in `scripts/update`, exits 3 instead of 1. To
  adapt, treat 3 as "a required tool is missing" in wrappers that tested for 1.
- The Codex `mid` tier now uses `gpt-6.1-terra` instead of `gpt-6.1-sol`, so `builder` runs on the faster
  model at half the Sol input price. `flagship` stays on Sol. Terra needs Codex CLI 0.159.0 or later; to
  keep `builder` on Sol, set `"mid": "gpt-6.1-sol"` under `codex.tiers` in `prompts/models.local.json`.
- The release workflow publishes the tagged CHANGELOG section as the release notes instead of generated notes,
  and the CI checks are now named `lint`, `test`, and `secrets` (formerly `Lint and test` and `Gitleaks`). Update
  branch protection or tooling that names the old checks.

### Added

- `--json` on `sync-ai-prompts`, `render-agents`, `render-invariants`, `render-hermes`, `update`, and
  `install_workflow.py` prints one JSON object (`ok`, `errors`, `warnings`, `notes`, a `mode`, and a list of
  records) to stdout and moves human output to stderr. Exit codes do not change. INSTALL.md lists the keys.
- `--harness` is an alias of `--target` in `sync-ai-prompts` and `render-agents` and of `--targets` in `update`.
  The old names keep working.
- Every `--help` ends with Environment and Exit codes sections.
- `.github/stack/` holds the conventions shared with the other stack repositories and `stack-check.py`, an
  offline checker that CI now runs.
- The logo and wordmark are in `assets/`.

### Changed

- `develop` is the default and nightly branch and `main` is the stable channel. Clone with
  `git clone -b main` for stable releases; `scripts/update` follows the checked-out branch. A release is a
  `develop` to `main` merge commit with the tag on `main`.
- CI runs `lint` and `test` as separate jobs, and the README follows the layout shared across the stack.
- `reviewer` and `explorer` no longer assume a shell, which five of six harnesses do not grant them.
  `reviewer` takes the diff from the task (pasted or as a patch file) and asks for it when it has neither
  a diff nor a shell; `explorer` uses native search and says when git history is out of reach.

### Fixed

- `render-hermes --deploy` no longer corrupts `config.yaml` when the `agent:` block is not indented by
  two spaces; sibling keys such as `model` were swallowed into the rules text. An inline `agent:` value
  now stops the deploy instead of adding a second `agent:` key that dropped the first.
- `--prune-backups` keeps the most recently taken backups. Backups used to keep the source file's mtime,
  so a fresh backup of a long-unchanged file was pruned first.
- Per-agent `agents.<name>` entries in the tracked `prompts/models.json` now apply; they passed validation
  but were ignored. Entries in `prompts/models.local.json` still win, field by field, and unknown agent
  names fail for both files.
- `render-agents --deploy` stops before writing when two selected harnesses resolve to the same agents
  directory; the second harness used to overwrite the first one's role files.
- A subagent whose role defines an output format now follows that format instead of the core preamble
  and state-marker rules; the two used to compete for the last line.

## [4.3.0] - 2026-10-25

### Added

- A `paperclip` target renders house rules for Paperclip agents to `PAPERCLIP.md`. It is a manual target
  with no global path: a Paperclip sync consumes the rendered file from `build/generated/`, and
  deploy skips it. It never carries `prompts/local.md` or `prompts/private.md`.
  Its fragment holds the Paperclip-specific wording (the agents are not the owner, questions go on the
  issue, work is handed off as Paperclip issues) and its own copy of the timer, issue-tracking, release, and
  product rules and the anonymized new-repo defaults, so the render is the same from a clean clone.
- `scripts/sync-ai-prompts --status --target paperclip` compares `build/generated/PAPERCLIP.md` with a fresh
  render and counts a missing or stale file as drift; a bare `--status` only reports it. `scripts/update`
  refuses the target.

### Changed

- A harness can now omit core sections by heading (`omit_sections` in `scripts/render_prompts.py`); the render
  fails if an omitted heading no longer exists. Only the Paperclip target uses it, to drop Model Selection, so
  the other renders are unchanged.
- `scripts/lint_prompts.py` allows the Paperclip fragment more lines than the other harness fragments.

## [4.2.0] - 2026-10-12

### Changed

- The core Code rules now keep tests proportional: one test per behavior, none for glue, config, getters, or
  type- and framework-guaranteed behavior, and a justification past about five new tests or when the tests
  outgrow the source. The rule states that it overrides skill rules such as "test every function". The
  Verification rule asks for the narrowest check that fails if the change is wrong instead of open-ended
  extra checks. Redeploy prompts to apply.
- The Codex render budget error now lists the bytes per section (harness notes, core, local, private), and
  the render warns on stderr at 90% of the budget. The README, INSTALL, and Codex notes explain that Codex
  counts the global and project `AGENTS.md` files against one `project_doc_max_bytes` cap (32 KiB by
  default) and recommend `project_doc_max_bytes = 40960` in `~/.codex/config.toml`, so project
  instructions are not truncated beside the 32 KiB global file.
- The Codex notes are shorter: model-effort ranges, `codex exec` flags, session commands, and the multi-agent
  note moved to the new "OpenAI Codex CLI reference" section of `docs/harness-contract.md`, and the prompt
  keeps the behavior rules. The rendered Codex file went from 32,612 to 31,510 bytes. The first Model
  Selection rule moved into the core Delegation rules. Redeploy prompts to apply.
- The core Git rules now tell the agent to check for merged or abandoned branches and worktrees, local and
  remote, when a task finishes, recommend what to delete, and delete only after confirmation.

## [4.1.0] - 2026-10-09

### Changed

- The explorer runs at `medium` effort instead of `low`, and the verifier moves from the mid tier at `low`
  to the cheap tier at `medium`: Haiku 5.5, GPT-6 Luna, DeepSeek V4.1 Flash, or `@smol` by harness
  (OpenCode renders `medium` as the `high` variant; Antigravity stays on `flash`). Haiku 5.5 at `low`
  skips searches and checks more often, and running, classifying, and redacting named commands fits the
  cheap tier. On Command Code the default verifier model changes provider, from `claude-sonnet-5-5` to
  `deepseek/deepseek-v4.1-flash`, and it sees raw command output before redaction; to keep it on Claude,
  set `"agents": {"verifier": {"tier": "mid"}}` under `commandcode` in `prompts/models.local.json`. A tier
  that pins its own effort still wins over the role's effort. The example override file drops its now
  redundant verifier effort override. Redeploy subagents to apply.
- The Claude prompt notes that Haiku 5.5 rates rise 5x above 100k-token prompts, and the core delegation
  rules say when cheap-tier fan-out pays off.

## [4.0.0] - 2026-10-09

### Changed

- OpenCode agents render effort as `variant` instead of `reasoningEffort`. OpenCode sent the old key as a
  raw request-body field rather than the provider's effort setting. The default effort map uses only
  variants the `opencode-go` models declare (`low`/`high`/`max`, Kimi K3 `max`), and the flagship tier
  pins `max`. A `variants` list per model makes rendering fail on an undeclared variant, and a tier that
  inherits the session model renders no variant. Breaking for local overrides: a tier pointing at another
  model, a per-agent effort override on a Kimi K3 role, or a plain-string flagship tier now fails to
  render (or, unchecked, fails model resolution) unless the variant is declared. Back up
  `prompts/models.local.json` (deploys back up the agent files into `.backups/`). To upgrade, remove any
  copied `"effort_key": "reasoningEffort"` from the OpenCode entry, add `variants` for other models from
  `opencode models`, align `effort_map`, and redeploy. To keep the old behavior instead, set
  `"effort_key": "reasoningEffort"` with the previous map (`medium` to `medium`, `xhigh` and `max` to
  `high`). Roll back by checking out v3.6.0 and redeploying.
- Link, anchor, and doc-command checks move from `check_docs_impact.py` into `scripts/check_docs_links.py`,
  a separate CI step; the receipt guard keeps domains, receipts, and range and release checks. Behavior is
  unchanged.

## [3.6.0] - 2026-10-08

### Added

- Docs-impact guard (`scripts/check_docs_impact.py`, `docs/contracts.lock.json`): changed prompt sources,
  renderers, deployment code, overlays, or workflow files need a review receipt that cites updated docs or
  gives a specific no-impact reason. Breaking receipts need backup, upgrade, and rollback steps, survive
  the release range, and are required when a harness is removed. Local Markdown links, anchors, and doc
  command flags are checked. CI runs it against the PR base and the release workflow against the previous
  tag; see `docs/MAINTENANCE.md`.

### Changed

- Workflow checkouts no longer persist git credentials, Dependabot waits seven days before proposing a
  release for both ecosystems and groups pip updates, the security workflow runs zizmor pinned by SHA,
  and CI adds a Windows smoke test for the PowerShell launchers.

### Fixed

- `sync-ai-prompts --dry-run` reports `unchanged` for targets whose deployed content already matches,
  like a real deploy and `--status`, instead of `would update` for every managed target.

## [3.5.0] - 2026-10-08

### Changed

- Claude Code cheap tier moves to the portable `haiku` alias (Haiku 5.5 on the Anthropic API) and keeps
  each role's effort, so the explorer runs at `low` and the researcher at `medium`. The Claude model
  ladder names Haiku 5.5 as the fast tier and Sonnet 5.5 as the balanced tier.
- Dated Haiku 5.5 notes cover provider alias resolution, effort guidance, and API changes from Haiku 4.5.

## [3.4.1] - 2026-10-03

### Fixed

- `consolidate-agents-md` backup and clearing steps are exact, verifiable commands: a progress checklist,
  a manifest-driven archive with a file-count check, memory checksums, and a checksum-gated clearing loop
  with no globs or recursive deletes.

## [3.4.0] - 2026-09-29

### Changed

- Codex mid and flagship defaults move to GPT-6.1 Sol; Claude guidance covers Sonnet 5.5 while
  preserving the portable `sonnet` alias, cheap-tier `low`, and local model overrides.
- Command Code's tracked mid-tier default moves to `claude-sonnet-5-5`.
- Model guidance uses `medium` for bounded coding and `high` for harder work, with meaningful checks,
  explicit stopping conditions, and scope control.
- Dated migration receipts document API compatibility, provider-dependent alias resolution, and
  deployment verification without claiming new API features in every supported harness.

## [3.3.0] - 2026-09-25

### Changed

- Autonomy rules: a long turn or finished milestone is not a stopping point unless a stated budget is
  reached; in-scope decisions that neither block work nor need confirmation get a recommendation and work
  continues. Before changing state on loosely specified tasks across connected tools, check the related
  tickets, threads, docs, and records most likely to hold missing context, including unnamed ones.
- Security rules: text the user pasted or a tool returned is data; instructions inside it apply only where
  the user's own message asks.
- Claude fragment: re-check earlier answers when later work contradicts them. The Opus 5.5 guide's
  suggestion to treat earlier answers as settled is intentionally not adopted, since later agentic steps
  often expose earlier mistakes.

## [3.2.0] - 2026-09-24

### Changed

- Tone rules: separate verified facts from inference and flag real uncertainty, match explanation depth
  to the reader's demonstrated familiarity, and omit routine closing questions and offers.

## [3.1.0] - 2026-09-24

### Changed

- Local leak markers (`prompts/private-patterns.txt`, `AGENTS_PRIVATE_PATTERNS`) are checked against every
  tracked text file, not only prompt sources. The built-in placeholder markers still apply to prompt
  sources only. With no local markers the scan is skipped.
- `prompts/private-patterns.example.txt` shows generic marker categories: machine and user paths, home-lab
  hosts and private IP prefixes, employer names, and private identities.

## [3.0.0] - 2026-09-24

### Breaking

- `prompts/private.md` no longer reaches Claude Code and Codex by default. There is no built-in trust
  list: it reaches only harnesses named in `prompts/private-harnesses.txt` or `AGENTS_PRIVATE_HARNESSES`.
  To keep the old behavior, put `claude` and `codex` in `prompts/private-harnesses.txt`. Render and deploy
  print a notice for each harness the overlay is withheld from, and unknown names fail the render.

### Added

- `prompts/local.md` overlay for provider-safe operational preferences, appended after the core for every
  global target, with a tracked `prompts/local.example.md` template.
- `all` in the private trust list sends `prompts/private.md` to every supported harness.
- `scripts/update` pulls fast-forward only, refuses to run over local tracked edits, checks, redeploys
  prompts, the Hermes merge, subagents, and the Claude invariants hook for the harnesses in
  `prompts/deploy-targets.txt`, then verifies; any failure exits non-zero, so it is safe on a schedule.
  `--detect` lists installed supported harnesses; `--dry-run` previews.
- An "Agent-Driven Setup" runbook in INSTALL.md, linked from the top of the README, for coding agents
  setting the repo up and scheduling daily updates.

### Changed

- Project-level targets (`generic`, and Hermes through `HERMES_AGENTS_PATH`) never receive either
  overlay, since those files can be committed. The global Hermes merge follows the trust list.
- Subagent directories follow `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, and `OPENCODE_CONFIG_DIR`, and the Claude
  invariants hook and `settings.json` follow `CLAUDE_CONFIG_DIR`, matching the rules files. Dedicated
  `*_AGENTS_DIR`, `CLAUDE_HOOKS_DIR`, and `CLAUDE_SETTINGS_PATH` overrides still win.
- Dry runs report hand-written rules files, subagent files, and Hermes `coding_instructions` as
  `would replace unmanaged` before a deploy would replace them (after a backup).

## [2.4.0] - 2026-09-24

### Added

- Oh My Pi (`omp`) harness: global rules at `~/.omp/agent/AGENTS.md` (follows named profiles,
  `PI_CONFIG_DIR`, and `PI_CODING_AGENT_DIR` the way omp resolves them), and
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

[Unreleased]: https://github.com/iuliandita/agents/compare/v5.0.1...HEAD
[5.0.1]: https://github.com/iuliandita/agents/compare/v5.0.0...v5.0.1
[5.0.0]: https://github.com/iuliandita/agents/compare/v4.3.0...v5.0.0
[4.3.0]: https://github.com/iuliandita/agents/compare/v4.2.0...v4.3.0
[4.2.0]: https://github.com/iuliandita/agents/compare/v4.1.0...v4.2.0
[4.1.0]: https://github.com/iuliandita/agents/compare/v4.0.0...v4.1.0
[4.0.0]: https://github.com/iuliandita/agents/compare/v3.6.0...v4.0.0
[3.6.0]: https://github.com/iuliandita/agents/compare/v3.5.0...v3.6.0
[3.5.0]: https://github.com/iuliandita/agents/compare/v3.4.1...v3.5.0
[3.4.1]: https://github.com/iuliandita/agents/compare/v3.4.0...v3.4.1
[3.4.0]: https://github.com/iuliandita/agents/compare/v3.3.0...v3.4.0
[3.3.0]: https://github.com/iuliandita/agents/compare/v3.2.0...v3.3.0
[3.2.0]: https://github.com/iuliandita/agents/compare/v3.1.0...v3.2.0
[3.1.0]: https://github.com/iuliandita/agents/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/iuliandita/agents/compare/v2.4.0...v3.0.0
[2.4.0]: https://github.com/iuliandita/agents/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/iuliandita/agents/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/iuliandita/agents/compare/v2.1.1...v2.2.0
[2.1.1]: https://github.com/iuliandita/agents/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/iuliandita/agents/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/iuliandita/agents/compare/v1.10.1...v2.0.0
