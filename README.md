# agents.

Opinionated global `AGENTS.md` / `CLAUDE.md` configuration for coding agents.

This is not a neutral baseline. It is a working config shaped by 20+ years in IT and DevOps, production incidents, code reviews, research, and ideas from people worth listening to - including Andrej Karpathy's autoresearch/autoimprove loop and writing from Boris and others. It is meant to be useful, sharp, and portable, not universal. Pick the parts that fit your workflow and ignore the rest.

## What This Repo Does

- Stores canonical prompt fragments in `prompts/`.
- Merges an optional gitignored private overlay from `prompts/private.md`.
- Renders public operational-rule variants for Claude Code, OpenAI Codex, OpenCode, Gemini CLI, Antigravity CLI, Cursor, Windsurf, GitHub Copilot CLI, Aider, Goose, Amp, Continue, Cline, Roo Code, Qwen Code, Warp, Kiro, Augment, OpenHands, Pi Coding Agent, OpenClaw, Crush, Kimi Code, Hermes Agent, and NanoClaw.
- Separates deployable global targets from manual project-local targets when no verified global operational rules path is known.
- Does not generate persona, identity, memory, provider credential, model settings, MCP, plugin, or assistant-profile files.
- Deploys rendered files to resolved global paths with backups.
- Lints public prompt sources, including `prompts/private.example.md`, for private paths, token-like secrets, missing harness fragments, and non-ASCII drift.
- Provides a Karpathy-style score -> improve -> verify loop in `scripts/autoimprove-prompts`.

## Quick Start

Render all supported harness files into `build/generated/`:

```bash
scripts/sync-ai-prompts
```

Harnesses that share an output filename, such as `AGENTS.md`, render into per-harness subdirectories so targets do not overwrite each other.

Deploy selected harnesses to global paths:

```bash
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
prompts/
  core.md                 # shared rules
  private.example.md      # tracked template for private local rules
  private.md              # optional gitignored local overlay
  harnesses/
    claude.md             # prepended to Claude output
    codex.md              # prepended to Codex output
    opencode.md           # prepended to OpenCode output
    ...
scripts/
  render_prompts.py       # renderer and deploy logic
  sync-ai-prompts         # wrapper for render/deploy
  lint_prompts.py         # prompt-source linter
  scan_prompt_sources.py  # prompt-injection scanner
  autoimprove-prompts     # score -> improve -> verify loop
tests/
  test_lint_prompts.py
  test_render_prompts.py
  test_scan_prompt_sources.py
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

`prompts/private.md` is gitignored and appended after the shared core during render/deploy, so it can override or extend the public config without leaking into the repo.

For local leak checks that should not be committed, copy `prompts/private-patterns.example.txt` to `prompts/private-patterns.txt` or set `AGENTS_PRIVATE_PATTERNS` to comma- or newline-separated markers.

## Invariants Reinforcement

Global memory files are advisory: harnesses drift on them deep in long sessions, and subagents never receive them at all (a subagent's system prompt is its own definition plus the dispatch prompt, not your `CLAUDE.md`). `prompts/invariants.md` holds a short block of non-negotiable rules for the cases where that drift is expensive.

```bash
scripts/render-invariants
```

This renders three artifacts into `build/generated/invariants/` from the single source:

- `invariants-userpromptsubmit.sh` — a Claude Code `UserPromptSubmit` hook. Its stdout is injected into the main loop every turn, so the invariants survive context compaction.
- `claude-settings-snippet.json` — the hook wiring, for reference or manual merge.
- `subagent-block.md` — paste into custom subagent definitions, the only channel that reaches subagents.

Install the hook the same way prompts deploy — dry-run first, then deploy:

```bash
scripts/render-invariants --dry-run
scripts/render-invariants --deploy
```

`--deploy` copies the hook to `~/.claude/hooks/` and **idempotently appends** its entry to `hooks.UserPromptSubmit` in `~/.claude/settings.json`, backing up anything it overwrites into `.backups/`. It never removes or rewrites existing hooks, so an already-configured `UserPromptSubmit` (or any other setting) is preserved; re-running is a no-op. Override targets for testing with `CLAUDE_HOOKS_DIR`, `CLAUDE_SETTINGS_PATH`, `--hooks-dir`, or `--settings-path`.

Per-turn injection is intentional: `SessionStart` runs once and gets buried, whereas `UserPromptSubmit` re-asserts the rules each turn for roughly 60 tokens. Hooks fire on main-loop events only, so they do not reach subagents; that is why the subagent block is a separate delivery path and stays a manual paste. Per-prompt injection support varies by harness (Claude Code and OpenCode have it; Codex, Gemini/Antigravity, Cursor, Windsurf, and Aider expose context/rules files but no programmatic per-turn hook) — verify current support before relying on it.

## Supported Harnesses

This is a public catalog, not a reflection of what is installed on one machine. Deployable targets have verified default operational-rule paths. Manual targets render into `build/generated/`, but deploy only when their `*_AGENTS_PATH` environment variable points at a project or per-agent rules file.

Gemini CLI remains in the catalog as a legacy Google target. As of 2026-06-15, the forward Google CLI target is Antigravity CLI; both use `GEMINI.md` by default, so real deploys refuse that same-path collision unless you select one target or override one path.

List targets, support levels, and resolved paths:

```bash
scripts/sync-ai-prompts --list-targets
```

Each deployable target path can be overridden with an environment variable such as `CLAUDE_AGENTS_PATH`, `CODEX_AGENTS_PATH`, `ANTIGRAVITY_AGENTS_PATH`, or `PI_AGENTS_PATH`. Manual targets require an explicit override such as `KIMI_AGENTS_PATH`, `HERMES_AGENTS_PATH`, or `NANOCLAW_AGENTS_PATH` before deploy writes anything.

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
bash -n scripts/sync-ai-prompts scripts/autoimprove-prompts
python -m py_compile scripts/render_prompts.py scripts/lint_prompts.py scripts/scan_prompt_sources.py scripts/check_harness_docs.py
scripts/sync-ai-prompts --check
scripts/sync-ai-prompts --dry-run
```

## GitHub Actions

- `.github/workflows/ci.yml` runs the repo's prompt lint, prompt-injection scan, workflow lint, tests, shell syntax checks, Python compile checks, and dry-run render.
- `.github/workflows/security.yml` runs CodeQL and Gitleaks.
- `.github/workflows/promptfoo-code-scan.yml` wires in Promptfoo's LLM security scanner for prompt-sensitive PRs when `PROMPTFOO_API_KEY` is configured. The Promptfoo GitHub App is the cleaner no-key setup if you want hosted PR comments without storing a token.

## License

MIT, unless a downstream fork says otherwise.
