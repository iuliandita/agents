# Install And Deploy

## Render

```bash
scripts/sync-ai-prompts
```

Rendered files go to `build/generated/`. Harnesses that share the same output filename are rendered into per-harness subdirectories.

## Deploy

```bash
scripts/sync-ai-prompts --target claude,codex --deploy
```

Existing files are backed up under `.backups/` before replacement. Deploy writes only to harnesses with resolved target paths. Manual harnesses are skipped unless their environment variable points at a project or per-agent operational rules file.

Full-catalog deploy can fail when deployable harnesses share a target, such as Gemini CLI and Antigravity CLI both using `~/.gemini/GEMINI.md`. Use `--target` for routine deploys, or override one shared path with its `*_AGENTS_PATH` env var.

If `prompts/private.md` exists, it is merged into every rendered/deployed file after the shared core. Use `prompts/private.example.md` as the template.

## Dry Run

```bash
scripts/sync-ai-prompts --dry-run
```

Dry runs report manual skips and same-path collisions without writing files.

## Target One Harness

```bash
scripts/sync-ai-prompts --target claude --deploy
scripts/sync-ai-prompts --target codex,opencode --deploy
scripts/sync-ai-prompts --target antigravity --deploy
```

## Manual Targets

Manual targets render by default, but deploy only with an explicit path:

```bash
KIMI_AGENTS_PATH="$PWD/.kimi/AGENTS.md" scripts/sync-ai-prompts --target kimi --deploy
HERMES_AGENTS_PATH="$PWD/HERMES.md" scripts/sync-ai-prompts --target hermes --deploy
NANOCLAW_AGENTS_PATH="$PWD/agents/nano/CLAUDE.md" scripts/sync-ai-prompts --target nanoclaw --deploy
```

## List Targets

```bash
scripts/sync-ai-prompts --list-targets
```

Use this before deploys when checking the current harness names, support levels, and resolved paths.

## Override Paths

Use env vars when a tool's real operational rules path differs from the default:

```bash
CODEX_AGENTS_PATH="$HOME/.codex/AGENTS.md" scripts/sync-ai-prompts --target codex --deploy
WINDSURF_AGENTS_PATH="$HOME/.codeium/windsurf/AGENTS.md" scripts/sync-ai-prompts --target windsurf --deploy
ANTIGRAVITY_AGENTS_PATH="$HOME/.gemini/ANTIGRAVITY.md" scripts/sync-ai-prompts --target antigravity --deploy
```

## Default Targets

| Harness | Support | Target | Notes |
|---|---|---|---|
| Claude Code | deployable | `~/.claude/CLAUDE.md` |  |
| OpenAI Codex | deployable | `~/AGENTS.md` |  |
| OpenCode | deployable | `~/.config/opencode/AGENTS.md` |  |
| Command Code | deployable | `~/.commandcode/AGENTS.md` |  |
| Gemini CLI | deployable | `~/.gemini/GEMINI.md` | Legacy Google CLI target; consumer Gemini CLI users transition to Antigravity CLI after 2026-06-18. |
| Antigravity CLI | deployable | `~/.gemini/GEMINI.md` | Forward Google CLI target; shares the default GEMINI.md path with Gemini CLI. |
| Cursor | deployable | `~/.cursor/AGENTS.md` |  |
| Windsurf | deployable | `~/.windsurf/AGENTS.md` |  |
| GitHub Copilot CLI | deployable | `~/.copilot/AGENTS.md` |  |
| Aider | deployable | `~/.aider/AGENTS.md` |  |
| Goose | deployable | `~/.config/goose/AGENTS.md` |  |
| Amp | deployable | `~/.amp/AGENTS.md` |  |
| Continue | deployable | `~/.continue/AGENTS.md` |  |
| Cline | deployable | `~/.cline/AGENTS.md` |  |
| Roo Code | deployable | `~/.roo/AGENTS.md` |  |
| Qwen Code | deployable | `~/.qwen/AGENTS.md` |  |
| Warp | deployable | `~/.warp/AGENTS.md` |  |
| Kiro | deployable | `~/.kiro/AGENTS.md` |  |
| Augment | deployable | `~/.augment/AGENTS.md` |  |
| OpenHands | deployable | `~/.openhands/AGENTS.md` |  |
| Pi Coding Agent | deployable | `~/.pi/agent/AGENTS.md` |  |
| OpenClaw | deployable | `~/.openclaw/workspace/AGENTS.md` |  |
| Crush | deployable | `~/.config/crush/CRUSH.md` |  |
| Kimi Code | manual | `manual override via KIMI_AGENTS_PATH` | Render-only unless KIMI_AGENTS_PATH points at a project AGENTS.md or .kimi/AGENTS.md file. |
| Hermes Agent | manual | `manual override via HERMES_AGENTS_PATH` | Render-only unless HERMES_AGENTS_PATH points at a project HERMES.md, .hermes.md, or AGENTS.md file. |
| NanoClaw | manual | `manual override via NANOCLAW_AGENTS_PATH` | Render-only unless NANOCLAW_AGENTS_PATH points at a per-agent CLAUDE.md file. |

## Operational Rules Only

This repo renders operational coding-agent rules. It does not generate persona, identity, memory, provider credential, model settings, MCP, plugin, or assistant-profile files.
