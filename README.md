# agents.

Opinionated global `AGENTS.md` / `CLAUDE.md` configuration for coding agents.

This is not a neutral baseline. It is a working config shaped by 20+ years in IT and DevOps, production incidents, code reviews, research, and ideas from people worth listening to - including Andrej Karpathy's autoresearch/autoimprove loop and writing from Boris and others. It is meant to be useful, sharp, and portable, not universal. Pick the parts that fit your workflow and ignore the rest.

## What This Repo Does

- Stores canonical prompt fragments in `prompts/`.
- Merges an optional gitignored private overlay from `prompts/private.md`.
- Renders harness-specific global files for Claude, Codex, OpenCode, Gemini, Cursor, Windsurf, Copilot, Aider, Goose, Amp, Continue, Cline, Roo, Qwen, Warp, Kiro, Augment, and OpenHands.
- Deploys rendered files to global paths with backups.
- Lints public prompt sources for private paths, token-like secrets, missing harness fragments, and non-ASCII drift.
- Provides a Karpathy-style score -> improve -> verify loop in `scripts/autoimprove-prompts`.

## Quick Start

Render all supported harness files into `build/generated/`:

```bash
scripts/sync-ai-prompts
```

Deploy to global paths:

```bash
scripts/sync-ai-prompts --deploy
```

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
  autoimprove-prompts     # score -> improve -> verify loop
tests/
  test_render_prompts.py
```

## Autoimprove

The loop is deliberately conservative:

> Score -> Improve -> Verify -> Keep or stop.

Run it in step mode:

```bash
scripts/autoimprove-prompts --iterations 3 --mode step
```

It runs lint, tests, and rendering before and after each improvement attempt. If a configured harness is available, it asks that harness for one small improvement. If verification fails, the diff is left in place for review instead of being silently accepted.

## Private Overlay

Public prompt fragments stay anonymized. Put personal paths, internal repo names, local command quirks, and private company rules in `prompts/private.md`.

```bash
cp prompts/private.example.md prompts/private.md
```

`prompts/private.md` is gitignored and appended after the shared core during render/deploy, so it can override or extend the public config without leaking into the repo.

## Supported Harnesses

List targets and global output paths:

```bash
scripts/sync-ai-prompts --list-targets
```

Each target path can be overridden with an environment variable such as `CLAUDE_AGENTS_PATH`, `CODEX_AGENTS_PATH`, `OPENCODE_AGENTS_PATH`, or `GEMINI_AGENTS_PATH`.

## Verification

```bash
python scripts/lint_prompts.py
python scripts/scan_prompt_sources.py
python -m pytest -q
bash -n scripts/sync-ai-prompts scripts/autoimprove-prompts
python -m py_compile scripts/render_prompts.py scripts/lint_prompts.py scripts/scan_prompt_sources.py
scripts/sync-ai-prompts --dry-run
```

## GitHub Actions

- `.github/workflows/ci.yml` runs the repo's prompt lint, prompt-injection scan, workflow lint, tests, shell syntax checks, Python compile checks, and dry-run render.
- `.github/workflows/security.yml` runs CodeQL, Gitleaks, and dependency review.
- `.github/workflows/promptfoo-code-scan.yml` wires in Promptfoo's LLM security scanner for prompt-sensitive PRs when `PROMPTFOO_API_KEY` is configured. The Promptfoo GitHub App is the cleaner no-key setup if you want hosted PR comments without storing a token.

## License

MIT, unless a downstream fork says otherwise.
