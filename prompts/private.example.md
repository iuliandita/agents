# Private Local Overlay

Copy this file to `prompts/private.md` for machine-specific or private rules.

This file is appended after the shared core during render and deploy. Keep it out of git.

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

## Project Instruction Layout
- Default to gitignored project instructions. For projects explicitly opting into sharing, track sanitized `AGENTS.md` and its `CLAUDE.md` companion, and ignore `AGENTS.local.md` plus its `CLAUDE.local.md` companion. The shared file must request reading the optional local file; local notes must not relax shared security or verification requirements. Migrate projects only when requested.
```
