# agents.

Portable instructions, subagent roles, and context-consolidation workflows for coding agents, with shared and private project context.

This is an opinionated toolkit shaped by 20+ years in IT and DevOps, production incidents, code reviews, research, and ideas from people worth listening to - including Andrej Karpathy's autoresearch/autoimprove loop and writing from Boris and others. Pick the parts that fit your workflow: global prompts, specialized subagents, project instruction templates, or context consolidation. Each is maintained here and installed separately.

## What This Repo Does

- Stores canonical prompt fragments in `prompts/`.
- Merges an optional gitignored private overlay from `prompts/private.md`.
- Renders public operational-rule variants for Claude Code, OpenAI Codex, OpenCode, Command Code, Gemini CLI, Antigravity CLI, Cursor, Windsurf, GitHub Copilot CLI, Aider, Goose, Amp, Continue, Cline, Roo Code, Qwen Code, Warp, Kiro, Augment, OpenHands, Pi Coding Agent, OpenClaw, Crush, Kimi Code, Hermes Agent, and NanoClaw.
- Separates deployable global targets from manual project-local targets when no verified global operational rules path is known.
- Does not generate persona, identity, memory, provider credential, model settings, MCP, plugin, or assistant-profile files.
- Deploys rendered files to resolved global paths with backups.
- Renders six reusable subagent roles from `agents/` into four harness formats.
- Provides opt-in shared/local project instruction templates and a portable context-consolidation skill.
- Lints public prompt sources, including `prompts/private.example.md`, for private paths, token-like secrets, missing harness fragments, and non-ASCII drift.
- Provides a Karpathy-style score -> improve -> verify loop in `scripts/autoimprove-prompts`.

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

Full-catalog deploy can fail when deployable harnesses share a target, such as Gemini CLI and Antigravity CLI both using `~/.gemini/GEMINI.md`. Use `--target` for routine deploys, or override one shared path with its `*_AGENTS_PATH` env var.

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
  private.example.md      # tracked template for private local rules
  private.md              # optional gitignored local overlay
  private-patterns.example.txt  # template for local leak-check markers
  harnesses/
    claude.md             # prepended to Claude output
    codex.md              # prepended to Codex output
    opencode.md           # prepended to OpenCode output
    AGENTS.md             # generic fragment for tools without a bespoke one (Warp)
    ...
scripts/
  render_prompts.py       # renderer and deploy logic
  sync-ai-prompts         # wrapper for render/deploy
  render_invariants.py    # invariants hook/subagent-block renderer
  render-invariants       # wrapper for the invariants renderer
  render-agents           # wrapper for the subagent renderer
  render_agents.py        # subagent renderer
  install_workflow.py     # explicit-destination consolidation skill installer
  lint_prompts.py         # prompt-source linter
  scan_prompt_sources.py  # prompt-injection scanner
  check_harness_docs.py   # README/INSTALL harness-table drift check
  autoimprove-prompts     # score -> improve -> verify loop
skills/consolidate-agents-md/  # portable project context workflow
templates/project/        # opt-in shared and private instruction examples
tests/                    # render, deploy, installer, lint, and CI regression tests
docs/                     # autoresearch guide and historical design specs
```

## Autoimprove

The loop is deliberately conservative:

> Score -> Improve -> Verify -> Keep or stop.

Run it in step mode:

```bash
scripts/autoimprove-prompts --iterations 3 --mode step
```

It runs lint, prompt-source scanning, tests, and rendering before and after each improvement attempt. If a configured harness is available, it asks that harness for one small improvement. If verification fails, the diff is left in place for review instead of being silently accepted.

## Private Overlay

Public prompt fragments stay anonymized. Put personal paths, internal repo names, local command quirks, and private company rules in `prompts/private.md`.

```bash
cp prompts/private.example.md prompts/private.md
```

`prompts/private.md` is gitignored and appended after the shared core during render/deploy.
It can extend the public config locally, but rendered output can contain private content.
Do not publish generated files or copy them into tracked project instructions.

For local leak checks that should not be committed, copy `prompts/private-patterns.example.txt` to `prompts/private-patterns.txt` or set `AGENTS_PRIVATE_PATTERNS` to comma- or newline-separated markers.

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

This renders three artifacts into `build/generated/invariants/` from the single source:

- `invariants-userpromptsubmit.sh` - a Claude Code `UserPromptSubmit` hook. Its stdout is injected into the main loop every turn, so the invariants survive context compaction.
- `claude-settings-snippet.json` - the hook wiring, for reference or manual merge.
- `subagent-block.md` - paste into custom subagent definitions; reinforcement that holds regardless of which memory files a given agent type loads.

Install the hook the same way prompts deploy - dry-run first, then deploy:

```bash
scripts/render-invariants --dry-run
scripts/render-invariants --deploy
```

`--deploy` copies the hook to `~/.claude/hooks/` and **idempotently appends** its entry to `hooks.UserPromptSubmit` in `~/.claude/settings.json`, backing up anything it overwrites into `.backups/`. It never removes or rewrites existing hooks, so an already-configured `UserPromptSubmit` (or any other setting) is preserved; re-running is a no-op. Override targets for testing with `CLAUDE_HOOKS_DIR`, `CLAUDE_SETTINGS_PATH`, `--hooks-dir`, or `--settings-path`.

Per-turn injection is intentional: `SessionStart` runs once and gets buried, whereas `UserPromptSubmit` re-asserts the rules each turn for roughly 60 tokens. `UserPromptSubmit` fires on user prompts in the main loop, not on subagent dispatches; that is why the subagent block is a separate delivery path and stays a manual paste. Per-prompt injection support varies by harness (Claude Code, OpenCode, and current Codex expose lifecycle hooks; Gemini/Antigravity, Cursor, Windsurf, and Aider expose context/rules files but no programmatic per-turn hook) - verify current support before relying on it.

## Subagent Roster

Specialized subagents beat general-purpose ones for two reasons: a clean context window per dispatch, and a fixed compact output the main thread can consume cheaply. `agents/*.md` defines six roles once, tool-agnostic; `scripts/render-agents` emits native definitions for Claude Code, Codex, OpenCode, and Command Code.

| agent | tier | effort | tools | returns |
|---|---|---|---|---|
| explorer | cheap | low | read, search, shell-ro | `path:line` rows with symbol and anchor line |
| researcher | cheap | medium | read, search, web | cited brief, facts separated from inference |
| builder | mid | medium | read, search, edit, write, shell | diff receipt for named files and named checks |
| verifier | mid | low | read, shell | per-command exit, classification, redacted excerpt |
| reviewer | flagship | high | read, search, shell-ro | one severity-tagged line per finding |
| planner | flagship | high | read, search, web | numbered `action -> verify: command` steps |

The core prompt dispatches `verifier` only when check output would flood the main context (full suites, builds); short checks run inline, and work that fits in a handful of tool calls is never delegated.

Tiers map to models per harness: Claude Code `haiku`, `sonnet`, `opus`, and `fable` for `apex`; Codex `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, and `gpt-6-astra` for `apex`. OpenCode and Command Code have no generic aliases and are often self-hosted or routed, so they inherit the session model until `prompts/models.local.json` names provider IDs. Copy `prompts/models.local.example.json` to start; it can also promote one agent to a higher tier or effort locally without touching tracked files.

```bash
scripts/render-agents                # build/agents/<harness>/
scripts/render-agents --check
scripts/render-agents --dry-run
scripts/render-agents --target claude,codex --deploy
```

Deploy backs up overwritten files into `.backups/` and removes only stale files that carry the generated marker; hand-written agents in the same directory are left alone. The hard invariants are rendered into every agent from `prompts/invariants.md`, so the manual subagent paste is only needed for agents defined outside this repo.

`shell-ro` is rendered only when the harness can enforce it as a real sandbox boundary. Codex maps it to shell access under `sandbox_mode = "read-only"`. Claude Code, OpenCode, and Command Code omit shell access for `shell-ro` agents and retain their native read and search tools. This costs explorer and reviewer direct git-history access on those harnesses, but keeps the read-only contract honest. Full `shell` roles are unchanged.

Codex only uses a custom role when the parent calls `spawn_agent` with `agent_type` set to the role name, and a full-history fork (`fork_turns = "all"`) inherits the parent's model and effort regardless of the role file. The rendered Codex prompt tells the root agent to pass `agent_type` and `fork_turns = "none"`; task prompts must therefore be self-contained.

## Supported Harnesses

This is a public catalog, not a reflection of what is installed on one machine. Deployable targets have verified default operational-rule paths. Manual targets render into `build/generated/`, but deploy only when their `*_AGENTS_PATH` environment variable points at a project or per-agent rules file.

Gemini CLI remains in the catalog as a legacy Google target. Since June 2026 the forward Google CLI target is Antigravity CLI; both use `GEMINI.md` by default, so real deploys refuse that same-path collision unless you select one target or override one path.

List targets, support levels, and resolved paths:

```bash
scripts/sync-ai-prompts --list-targets
```

Each deployable target path can be overridden with an environment variable such as `CLAUDE_AGENTS_PATH`, `CODEX_AGENTS_PATH`, `ANTIGRAVITY_AGENTS_PATH`, or `PI_AGENTS_PATH`. Manual targets require an explicit override such as `HERMES_AGENTS_PATH` or `NANOCLAW_AGENTS_PATH` before deploy writes anything.

## Watchlist

These tools are tracked for future operational-rule support, but are not first-wave deploy targets: Devin for Terminal, Junie, Kilo Code, iFlow CLI, Lingma, Mistral Vibe, Qoder CLI, Rovo Dev, SHAI, Tabnine CLI, Trae, CodeBuddy, and Forge.

Z.ai and MiniMax are treated as providers/tool integrations until their docs identify standalone operational rules harnesses. They should not become deployable prompt targets just because their models or CLIs can be used from other agents.

## Verification

Inside a virtual environment, install test dependencies first:

```bash
python -m pip install -r requirements-dev.txt
```

```bash
python scripts/lint_prompts.py
python scripts/scan_prompt_sources.py
python scripts/check_harness_docs.py
python -m pytest -q
bash -n scripts/sync-ai-prompts scripts/autoimprove-prompts scripts/render-invariants scripts/render-agents
python -m py_compile scripts/render_prompts.py scripts/render_invariants.py scripts/render_agents.py scripts/install_workflow.py scripts/lint_prompts.py scripts/scan_prompt_sources.py scripts/check_harness_docs.py
scripts/sync-ai-prompts --check
scripts/sync-ai-prompts --dry-run
scripts/render-agents --check
```

## GitHub Actions

- `.github/workflows/ci.yml` runs the repo's prompt lint, prompt-injection scan, workflow lint, tests, shell syntax checks, Python compile checks, and dry-run render.
- `.github/workflows/security.yml` runs CodeQL and Gitleaks.
- `.github/workflows/promptfoo-code-scan.yml` wires in Promptfoo's LLM security scanner for prompt-sensitive PRs when `PROMPTFOO_API_KEY` is configured. The Promptfoo GitHub App is the cleaner no-key setup if you want hosted PR comments without storing a token.

## License

MIT, unless a downstream fork says otherwise.
