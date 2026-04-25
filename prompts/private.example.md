# Private Local Overlay

Copy this file to `prompts/private.md` for machine-specific or private rules.

This file is appended after the shared core during render and deploy. Keep it out of git.

Examples:

```markdown
## Local Paths
- Canonical skills repo: `~/priv/code/example/skills`
- Canonical agents repo: `~/priv/code/example/agents`

## Local Shell Rules
- Local interactive shell is zsh, fish, bash, or another shell.
- Prefix local shell commands with `rtk` when this machine requires it.

## Private Preferences
- Prefer the internal review harness for private company repos.
```
