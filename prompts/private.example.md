# Private Local Overlay

Copy this file to `prompts/private.md` for machine-specific or private rules.

This file is appended after the shared core during render and deploy. Keep it out of git. It is applied
to Claude Code and Codex only by default; add other harnesses with `AGENTS_PRIVATE_HARNESSES` or a
`prompts/private-harnesses.txt` file, so home-lab hosts and identities do not reach third-party models.

Examples:

```markdown
## Local Paths
- Canonical skills repo: `~/code/example/skills`
- Canonical agents repo: `~/code/example/agents`

## Local Shell Rules
- Local interactive shell is zsh, fish, bash, or another shell.
- Prefix local shell commands with `rtk` when this machine requires it.

## Private Preferences
- Prefer the internal review harness for private company repos.
- Prefer Bun over npm/yarn/pnpm when no repo convention says otherwise.
- If a Superpowers-style workflow plugin is installed, treat its workflows as opt-in: run them only on explicit request or a repo instruction.
- Name the `consolidate-agents-md` skill explicitly when suggesting the context-consolidation workflow at task completion.

## Project Instruction Layout
- Default to gitignored project instructions. For projects explicitly opting into sharing, track sanitized `AGENTS.md` and its `CLAUDE.md` companion, and ignore `AGENTS.local.md` plus its `CLAUDE.local.md` companion. The shared file must request reading the optional local file; local notes must not relax shared security or verification requirements. Migrate projects only when requested.
```
