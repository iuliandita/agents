# Install And Deploy

## Render

```bash
scripts/sync-ai-prompts
```

Rendered files go to `build/generated/`. Harnesses that share the same output filename are rendered into per-harness subdirectories.

## Deploy

```bash
scripts/sync-ai-prompts --deploy
```

Existing files are backed up under `.backups/` before replacement.

If `prompts/private.md` exists, it is merged into every rendered/deployed file after the shared core. Use `prompts/private.example.md` as the template.

## Dry Run

```bash
scripts/sync-ai-prompts --dry-run
```

## Target One Harness

```bash
scripts/sync-ai-prompts --target claude --deploy
scripts/sync-ai-prompts --target codex,opencode --deploy
```

## Override Paths

Use env vars when a tool's real global rules path differs from the default:

```bash
CODEX_AGENTS_PATH="$HOME/.codex/AGENTS.md" scripts/sync-ai-prompts --target codex --deploy
WINDSURF_AGENTS_PATH="$HOME/.codeium/windsurf/AGENTS.md" scripts/sync-ai-prompts --target windsurf --deploy
```

## Default Targets

| Harness | Default target |
|---|---|
| Claude | `~/.claude/CLAUDE.md` |
| Codex | `~/AGENTS.md` |
| OpenCode | `~/.config/opencode/AGENTS.md` |
| Gemini | `~/.gemini/GEMINI.md` |
| Cursor | `~/.cursor/AGENTS.md` |
| Windsurf | `~/.windsurf/AGENTS.md` |
| Copilot | `~/.copilot/AGENTS.md` |
| Aider | `~/.aider/AGENTS.md` |
| Goose | `~/.config/goose/AGENTS.md` |
| Amp | `~/.amp/AGENTS.md` |
| Continue | `~/.continue/AGENTS.md` |
| Cline | `~/.cline/AGENTS.md` |
| Roo | `~/.roo/AGENTS.md` |
| Qwen | `~/.qwen/AGENTS.md` |
| Warp | `~/.warp/AGENTS.md` |
| Kiro | `~/.kiro/AGENTS.md` |
| Augment | `~/.augment/AGENTS.md` |
| OpenHands | `~/.openhands/AGENTS.md` |
