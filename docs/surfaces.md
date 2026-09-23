# Surfaces: CLI, IDE, and Desktop

Which surfaces read the rendered rules files, and which do not. Verified 2026-09-17 against upstream
docs. The practical rule: the CLI-integrated coding surfaces share the global files this repo deploys,
so there is no separate desktop deployment; the account-synced chat surfaces are not file-deployable.

| Tool | Surface | Reads the deployed global file? | Source |
|---|---|---|---|
| Claude Code | CLI, IDE, Desktop Code tab | Yes - "desktop and CLI read the same configuration files"; same engine | code.claude.com/docs/en/desktop |
| Claude | Desktop Chat/Cowork tab | No - skills/plugins/connectors sync through the claude.ai account, not `~/.claude` | code.claude.com/docs/en/desktop |
| OpenAI Codex | CLI, IDE, ChatGPT Desktop Codex | Yes - the desktop Personalization box edits global `AGENTS.md`; shared Codex home and auth | developers.openai.com/codex/app/settings |
| ChatGPT | Desktop Chat/Work (non-Codex) | No - uses Memories/personality, separate from `~/.codex` | developers.openai.com/codex/app/settings |
| OpenCode | TUI, CLI, desktop, GitHub Action | Yes - config "applies across all interfaces" | opencode.ai/docs/config |
| Antigravity | Desktop 2.0, IDE extensions, `agy` CLI | Yes for rules/MCP/workspace - all share `~/.gemini/GEMINI.md` and `.agents/` | antigravity.google/docs/rules-workflows |
| Hermes | CLI and desktop | Yes - desktop shares `HERMES_HOME` (same config, sessions, skills, memory) | hermes-agent.nousresearch.com/docs/user-guide/desktop |
| Oh My Pi | CLI/TUI, `omp acp` (editor server) | Yes - all surfaces read the same `~/.omp/agent/AGENTS.md`; no desktop app | installed omp 18.2.11 source (omp.sh) |

## Domain-specific extras (not deployed by this repo)

- Claude Desktop: `claude_desktop_config.json` adds Desktop-only MCP servers; two managed browser
  settings are Desktop-only.
- ChatGPT Desktop: Memories and personality are an additive layer; they are not documented as reaching
  Codex threads.
- Antigravity: per-surface skills/plugins directories (`~/.gemini/antigravity*`), bundled plugins.

## Per-OS paths

The supported tools all use a home-relative dotdir; only the home prefix changes.

| Harness | Linux / macOS | Windows (native) | Windows (WSL) |
|---|---|---|---|
| Claude Code | `~/.claude/` | `%USERPROFILE%\.claude\` | WSL home |
| OpenAI Codex | `~/.codex/` | `%USERPROFILE%\.codex\` | WSL home |
| OpenCode | `~/.config/opencode/` | `%USERPROFILE%\.config\opencode\` (WSL recommended) | WSL home |
| Command Code | `~/.commandcode/` | `%USERPROFILE%\.commandcode\` | WSL home |
| Antigravity | `~/.gemini/` | `%USERPROFILE%\.gemini\` (unverified, inferred) | WSL home |
| Hermes | `~/.hermes/` | `%LOCALAPPDATA%\hermes\` | WSL home |
| Oh My Pi | `~/.omp/` | `%USERPROFILE%\.omp\` (unverified, inferred) | WSL home |

A tool installed inside WSL reads the WSL home, separate from the native Windows install; no vendor
documents cross-reading `%USERPROFILE%`. Point both at one home with the native env var
(`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `HERMES_HOME`, ...) if you want a shared config.

## Desktop/IDE rule-file precedence

- Claude Code: hierarchical `CLAUDE.md` (global then project); `CLAUDE.local.md` alongside.
- Codex: `AGENTS.override.md` replaces the directory's `AGENTS.md`; at most one instruction file per
  directory.
- Antigravity: global `~/.gemini/GEMINI.md` plus workspace `.agents/rules/` (activation modes).
- Hermes: exactly one project context file, first match wins (see `docs/harness-contract.md`).
- Oh My Pi: `.omp/AGENTS.md` (nearest non-empty `.omp` dir only) > `.claude/CLAUDE.md` > `.agent(s)/AGENTS.md` >
  standalone `AGENTS.md`/`CLAUDE.md` walked up from cwd.
