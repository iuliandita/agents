# agents.

Portable instructions, subagent roles, and context-consolidation workflows for coding agents, with shared and private project context.

This is an opinionated toolkit shaped by 20+ years in IT and DevOps, production incidents, code reviews, and research. Pick the parts that fit your workflow: global prompts, specialized subagents, project instruction templates, or context consolidation. Each is maintained here and installed separately.

## Set Up With an Agent

Point your coding agent at this repository and ask it to set things up, for example:

> Set up https://github.com/iuliandita/agents for the coding agents I use, following its INSTALL.md
> "Agent-Driven Setup" runbook, and keep it updated daily.

The runbook is written for an agent to follow step by step: clone, detect installed harnesses, confirm
the target list and any private-overlay trust with you, preview, deploy, verify, and schedule
`scripts/update`, which pulls, checks, redeploys, and fails loudly. Everything it deploys is backed up
first, and nothing outside the listed harnesses is touched.

## What This Repo Does

- Stores canonical prompt fragments in `prompts/`.
- Merges two optional gitignored overlays: `prompts/local.md` for every harness and `prompts/private.md` for the harnesses you trust.
- Renders public operational-rule variants for Claude Code, OpenAI Codex, OpenCode, Command Code, Antigravity, Oh My Pi, and Hermes Agent, plus a generic project-level `AGENTS.md` target for other tools.
- Separates deployable global targets from manual project-local targets when no verified global operational rules path is known.
- Does not generate persona, identity, memory, provider credential, model settings, MCP, plugin, or assistant-profile files.
- Deploys rendered files to resolved global paths with backups.
- Renders six reusable subagent roles from `agents/` into six harness formats.
- Provides opt-in shared/local project instruction templates and a portable context-consolidation skill.
- Lints public prompt sources, including `prompts/private.example.md`, for private paths, token-like secrets, missing harness fragments, and non-ASCII drift.

## Quick Start

Use Git, Python 3.11+, and Bash; GitHub CLI is optional. Start with the
[environment setup](INSTALL.md#prerequisites), including the macOS interpreter
selection notes. The launchers use the checkout's `.venv` when present and also
work with `python3` alone on PATH. No global `python` alias is needed.

Render all supported harness files into `build/generated/`:

```bash
scripts/sync-ai-prompts
```

Harnesses that share an output filename, such as `AGENTS.md`, render into per-harness subdirectories so targets do not overwrite each other.

Preview and deploy only the harnesses you use:

```bash
scripts/sync-ai-prompts --target claude,codex --dry-run
scripts/sync-ai-prompts --target claude,codex --deploy
```

Real deploys refuse when two selected harnesses resolve to the same path, for example after overriding a path with its `*_AGENTS_PATH` env var. Use `--target` for routine deploys so only the harnesses you use are written.

Preview deploy paths without writing:

```bash
scripts/sync-ai-prompts --dry-run
```

Render only a few harnesses:

```bash
scripts/sync-ai-prompts --target claude,codex,opencode
```

## Layout

```text
agents/                   # tool-agnostic subagent sources
prompts/
  core.md                 # shared rules
  invariants.md           # non-negotiable rules for hook/subagent reinforcement
  local.example.md        # tracked template for the local overlay
  local.md                # optional gitignored overlay, every harness
  private.example.md      # tracked template for the private overlay
  private.md              # optional gitignored overlay, trusted harnesses only
  private-patterns.example.txt  # template for local leak-check markers
  harnesses/
    claude.md             # prepended to Claude output
    codex.md              # prepended to Codex output
    opencode.md           # prepended to OpenCode output
    AGENTS.md             # generic fragment for project-level AGENTS.md targets
    ...
scripts/
  render_prompts.py       # renderer and deploy logic
  sync-ai-prompts         # wrapper for render/deploy
  render_invariants.py    # invariants hook/subagent-block renderer
  render-invariants       # wrapper for the invariants renderer
  render-agents           # wrapper for the subagent renderer
  render_agents.py        # subagent renderer
  render_hermes.py        # Hermes global-rules merger (agent.coding_instructions)
  render-hermes           # wrapper for the Hermes merger
  update.py               # pull, check, and redeploy everything for saved targets (cron-safe)
  update                  # wrapper for the updater (update.ps1 on native Windows)
  python-runtime.sh       # POSIX interpreter selection (sourced by bash wrappers)
  python-runtime.ps1      # PowerShell interpreter selection (sourced by .ps1 wrappers)
  sync-ai-prompts.ps1     # PowerShell counterparts of the bash launchers (native Windows)
  render-agents.ps1
  render-invariants.ps1
  render-hermes.ps1
  install_workflow.py     # explicit-destination consolidation skill installer
  lint_prompts.py         # prompt-source linter
  scan_prompt_sources.py  # prompt-injection scanner
  check_harness_docs.py   # README/INSTALL harness-table drift check
  check_harness_contract.py  # harness receipt completeness check
skills/consolidate-agents-md/  # portable project context workflow
templates/project/        # opt-in shared and private instruction examples
tests/                    # render, deploy, installer, lint, and CI regression tests
docs/                     # harness contract, surfaces, legacy harnesses, design specs
```

## Local and Private Overlays

Public prompt fragments stay anonymized. Your own rules go in two gitignored overlays, appended after the
shared core in this order:

| Overlay | Holds | Reaches |
|---|---|---|
| `prompts/local.md` | Operational preferences safe for any provider: shell quirks, deploy lists, branch and release habits, tool preferences | Every harness you render or deploy |
| `prompts/private.md` | Sensitive context: hosts, networks, identities, machine paths, company rules | Only harnesses you list as trusted |

```bash
cp prompts/local.example.md prompts/local.md
cp prompts/private.example.md prompts/private.md
printf '%s\n' claude codex > prompts/private-harnesses.txt   # only harnesses whose provider you trust; 'all' for every one
```

The harness is not the trust boundary, the model provider behind it is, and only you know which provider
each harness uses. So there is no built-in trust list: `prompts/private.md` reaches only the harnesses named
in `prompts/private-harnesses.txt` (one per line) or `AGENTS_PRIVATE_HARNESSES` (comma-separated), and `all`
covers every supported harness. Unknown names fail the render. When the private overlay exists but is
withheld from a selected harness, render and deploy print a notice naming it. Project-level targets
(`generic`, and Hermes through `HERMES_AGENTS_PATH`) never receive either overlay, because those files can
end up committed; Hermes' global `agent.coding_instructions` merge does.

Rendered output can contain overlay content. Do not publish generated files or copy them into tracked
project instructions.

To keep your own hosts, domains, and names out of a fork or a contribution, list them as leak markers:
copy `prompts/private-patterns.example.txt` to `prompts/private-patterns.txt` (gitignored) and replace the
placeholders, or set `AGENTS_PRIVATE_PATTERNS` to comma- or newline-separated markers. `python
scripts/lint_prompts.py` then fails if any tracked file, not only the prompt sources, contains one. Without
a local list the scan is skipped, so CI on a clean fork is unaffected.

## Workflow Activation

The shared prompt makes workflow-style skills opt-in: use them only on an explicit request for that workflow or a repository instruction, including aliases and calls from other skills. Ordinary brainstorming and implementation requests do not opt in. Other skills are selected when requested or when they materially help the task. This changes the rendered guidance, not installed skill files or discovery metadata; higher-priority harness requirements can still trigger workflows. It is not a runtime disable switch.

This first conservative pass preserves the operational safeguards and model settings. Source and render checks verify that the policy is present; they do not measure model behavior or token savings. Compare representative tasks at the same model and effort before further consolidation or effort changes.

## Project Instructions

For project instructions shared with colleagues, use the optional [shared and local layout](INSTALL.md#project-instructions-shared-or-private). It keeps `AGENTS.md` in version control and developer-specific details in ignored `AGENTS.local.md`, with companions for Claude. Existing private-only projects need no migration.

## Context Consolidation

The portable [consolidate-agents-md skill](skills/consolidate-agents-md/SKILL.md)
keeps project instructions lean, aligns companion files, and consolidates then clears
project memory after verified backups and writes. It preserves shared/local separation.
The global prompt suggests it once at task completion when durable discoveries or drift
warrant it; only explicit invocation runs it. See [installation and invocation](INSTALL.md#context-consolidation-workflow).
Prompt deployment does not install this skill. Run its installer separately; installing
it does not consolidate or clear memory.

## Invariants Reinforcement

Global memory files are advisory: harnesses drift on them deep in long sessions, and memory loading varies by agent (Claude Code's built-in Explore and Plan subagents skip `CLAUDE.md` entirely; custom and general-purpose subagents load it but still drift). `prompts/invariants.md` holds a short block of non-negotiable rules for the cases where that drift is expensive.

```bash
scripts/render-invariants
```

This renders five artifacts into `build/generated/invariants/` from the single source:

- `invariants-userpromptsubmit.sh` - a Claude Code `UserPromptSubmit` hook. Its stdout is injected into the main loop every turn, so the invariants survive context compaction.
- `claude-settings-snippet.json` - the hook wiring, for reference or manual merge.
- `subagent-block.md` - paste into custom subagent definitions; reinforcement that holds regardless of which memory files a given agent type loads.
- `invariants-preinvocation.sh` - an Antigravity `PreInvocation` hook that emits `injectSteps.ephemeralMessage` JSON; Antigravity's documented per-turn channel.
- `antigravity-hooks-snippet.json` - the `hooks.json` entry for the Antigravity hook, for manual merge into `~/.gemini/config/hooks.json`.

Install the Claude hook the same way prompts deploy - dry-run first, then deploy:

```bash
scripts/render-invariants --dry-run
scripts/render-invariants --deploy
```

`--deploy` copies the hook to `~/.claude/hooks/` and **idempotently appends** its entry to `hooks.UserPromptSubmit` in `~/.claude/settings.json`, backing up anything it overwrites into `.backups/`. It refuses symlinked destinations and shell-quotes the hook path. It never removes or rewrites existing hooks, so an already-configured `UserPromptSubmit` (or any other setting) is preserved; re-running is a no-op. Override targets for testing with `CLAUDE_HOOKS_DIR`, `CLAUDE_SETTINGS_PATH`, `--hooks-dir`, or `--settings-path`. The Antigravity artifacts are render-only today; merge the snippet into `hooks.json` by hand.

Per-turn injection is intentional: `SessionStart` runs once and gets buried, whereas `UserPromptSubmit` re-asserts the rules each turn for roughly 60 tokens. `UserPromptSubmit` fires on user prompts in the main loop, not on subagent dispatches; that is why the subagent block is a separate delivery path and stays a manual paste. Per-turn injection support varies by harness: Claude Code (`UserPromptSubmit`) and Antigravity (`PreInvocation`) have a documented per-turn channel; OpenCode, Codex, Hermes, and Command Code expose hooks or context files whose injection semantics are not yet confirmed here, so treat their rules-reinforcement as advisory. Verify current support before relying on it.

## Subagent Roster

Specialized subagents beat general-purpose ones for two reasons: a clean context window per dispatch, and a fixed compact output the main thread can consume cheaply. `agents/*.md` defines six roles once, tool-agnostic; `scripts/render-agents` emits native definitions for Claude Code, Codex, OpenCode, Command Code, Antigravity, and Oh My Pi. Hermes has no per-role prompt file (delegation is configured under `delegation:` in `config.yaml`), so its six roles are a documented manual paste rather than a rendered file.

| agent | tier | effort | tools | returns |
|---|---|---|---|---|
| explorer | cheap | low | read, search, shell-ro | `path:line` rows with symbol and anchor line |
| researcher | cheap | medium | read, search, web | cited brief, facts separated from inference |
| builder | mid | medium | read, search, edit, write, shell | diff receipt for named files and named checks |
| verifier | mid | low | read, shell | per-command exit, classification, redacted excerpt |
| reviewer | flagship | high | read, search, shell-ro | one severity-tagged line per finding |
| planner | flagship | high | read, search, web | numbered `action -> verify: command` steps |

The core prompt delegates bounded work by default. The main model coordinates scope, priorities, decisions, integration, and the final answer; workers handle research, investigation, implementation, checks, and review. Related small tasks are batched, independent work runs in parallel, and trivial actions stay inline when dispatch would cost more than doing them. Each worker gets explicit ownership and concise context, and the main model checks its evidence.

Model and reasoning effort are chosen separately for each task, using the cheapest capable model and escalating when difficulty or observed failures warrant it. Total cost includes context, retries, delegation overhead, and verification. Role defaults remain starting points, subject to the harness's supported controls and explicit user overrides.

When a configured Jev/TypeSafe API key and a relevant installed skill such as `typesafe-ai` or `jevify` are available, the prompt calls for proactive Jev use for suitable bounded decisions, including routing, triage, ranking, and context selection, when it improves cost or speed at the required quality. Credentials stay private, exact rules remain deterministic, and uncertain results or service failures fall back to the main model or a worker. Missing access does not block the task.

Tiers map to models per harness: Claude Code `sonnet` at `low` effort for `cheap`, `sonnet`, `opus`, and `fable` for `apex`; Codex `gpt-6-luna`, `gpt-6-sol` for both `mid` and `flagship` (split by role effort), and `gpt-6-astra` for `apex`; Antigravity `flash` and `pro`. OpenCode and Command Code get working defaults from the tracked `prompts/models.json` (`opencode-go/...` and Command Code's own model IDs), so tiering is on out of the box. A tier can carry an effort (`{"model": "...", "effort": "max"}`), so a harness that runs one model on every tier still varies depth by tier. Effort levels run `low`, `medium`, `high`, `xhigh`, `max`. `prompts/models.local.json` overrides any tier, effort map, or single agent without touching tracked files; copy `prompts/models.local.example.json` to start. A harness with no tier map fails loudly unless you pass `--allow-inherit`.

```bash
scripts/render-agents                # build/agents/<harness>/
scripts/render-agents --check
scripts/render-agents --dry-run
scripts/render-agents --target claude,codex --deploy
scripts/render-agents --target claude,codex --verify   # after --deploy: confirm the roles landed
```

Deploy backs up overwritten files into `.backups/` and removes only stale files that carry the generated marker. Hand-written agents with other names are left alone, but a hand-written file with the same name as a role (for example your own `reviewer.md`) is replaced after its backup; `--dry-run` reports those as `would replace unmanaged`, so rename yours first if you want both. After a deploy, `scripts/render-agents --target <list> --verify` checks that all six role files exist in each selected harness's agent directory. Prune old backups with `scripts/sync-ai-prompts --prune-backups 50 --dry-run` (drop `--dry-run` to delete). The hard invariants are rendered into every agent from `prompts/invariants.md`, so the manual subagent paste is only needed for agents defined outside this repo.

`shell-ro` is rendered only when the harness can enforce it as a real sandbox boundary. Codex maps it to shell access under `sandbox_mode = "read-only"`. Claude Code, OpenCode, Command Code, and Antigravity omit shell access for `shell-ro` agents and retain their native read and search tools. This costs explorer and reviewer direct git-history access on those harnesses, but keeps the read-only contract honest. Full `shell` roles are unchanged.

Codex only uses a custom role when the parent calls `spawn_agent` with `agent_type` set to the role name, and a full-history fork (`fork_turns = "all"`) inherits the parent's model and effort regardless of the role file. The rendered Codex prompt tells the root agent to pass `agent_type` and `fork_turns = "none"`; task prompts must therefore be self-contained.

## Supported Harnesses

Seven harnesses are supported, each with a rules path verified against upstream docs, plus one generic
project-level target. Receipts, overrides, and per-surface behavior live in
[docs/harness-contract.md](docs/harness-contract.md) and [docs/surfaces.md](docs/surfaces.md).

| Harness | Support | Global rules file |
|---|---|---|
| Claude Code | deployable | `~/.claude/CLAUDE.md` |
| OpenAI Codex | deployable | `~/.codex/AGENTS.md` |
| OpenCode | deployable | `~/.config/opencode/AGENTS.md` |
| Command Code | deployable | `~/.commandcode/AGENTS.md` |
| Antigravity | deployable | `~/.gemini/GEMINI.md` |
| Oh My Pi | deployable | `~/.omp/agent/AGENTS.md` |
| Hermes Agent | manual | project `HERMES.md` / `$HERMES_HOME/config.yaml` |
| Generic AGENTS.md | manual | project `AGENTS.md` only |

`docs/surfaces.md` explains which CLI, IDE, and desktop surfaces read these files. The supported
tools' coding surfaces, including Claude Desktop's Code tab, the Codex integration in the ChatGPT
desktop app, OpenCode desktop, Antigravity's desktop/IDE/CLI, and the Hermes desktop app, share the
deployed file; the account-synced chat surfaces do not.

List targets, support levels, and resolved paths:

```bash
scripts/sync-ai-prompts --list-targets
```

Each target can be overridden with its environment variable, such as `CLAUDE_AGENTS_PATH`,
`CODEX_AGENTS_PATH`, `ANTIGRAVITY_AGENTS_PATH`, or `HERMES_AGENTS_PATH`. Manual targets
(`hermes`, `generic`) require an explicit override before deploy writes anything. Harnesses removed
from the catalog are listed in [docs/legacy-harnesses.md](docs/legacy-harnesses.md) with a re-add recipe.

Hermes has no global Markdown rules file. Its global operational rules live in `agent.coding_instructions`
in `$HERMES_HOME/config.yaml`; merge the shared core there with `scripts/render-hermes --dry-run` then
`scripts/render-hermes --deploy`. The merge is a comment-preserving line edit with a backup, so unrelated
settings and comments are kept.

## Verification

Inside a virtual environment, install test dependencies first:

```bash
python -m pip install -r requirements-dev.txt
```

```bash
python scripts/lint_prompts.py
python scripts/scan_prompt_sources.py
python scripts/check_harness_docs.py
python scripts/check_harness_contract.py
python -m pytest -q
bash -n scripts/sync-ai-prompts scripts/render-invariants scripts/render-agents scripts/render-hermes scripts/update
python -m py_compile scripts/render_prompts.py scripts/render_invariants.py scripts/render_agents.py scripts/install_workflow.py scripts/lint_prompts.py scripts/scan_prompt_sources.py scripts/check_harness_docs.py scripts/check_harness_contract.py scripts/render_hermes.py scripts/update.py
scripts/sync-ai-prompts --check
scripts/sync-ai-prompts --dry-run
scripts/sync-ai-prompts --target claude,codex --status
scripts/render-agents --check
```

## GitHub Actions

- `.github/workflows/ci.yml` runs the repo's prompt lint, prompt-injection scan, contract check, workflow lint, tests, shell syntax checks, Python compile checks, and dry-run render on a Python 3.11/3.13 matrix.
- `.github/workflows/security.yml` runs CodeQL and Gitleaks.
- `.github/workflows/release.yml` creates or updates a GitHub release from generated notes when a `v*` tag is pushed.
- `.github/workflows/promptfoo-code-scan.yml` wires in Promptfoo's LLM security scanner for prompt-sensitive PRs when `PROMPTFOO_API_KEY` is configured. The Promptfoo GitHub App is the cleaner no-key setup if you want hosted PR comments without storing a token.

## License

MIT, unless a downstream fork says otherwise.
