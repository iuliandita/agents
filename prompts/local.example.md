# Local Overlay

Copy this file to `prompts/local.md` for operational preferences that are safe to send to any model
provider. It is appended after the shared core for every harness you render or deploy, and it stays out
of git. Hosts, IPs, identities, and anything else sensitive belong in `prompts/private.md` instead, which
only reaches the harnesses you trust (see `prompts/private.example.md`).

Examples:

```markdown
## Local Shell
- Local interactive shell is zsh, fish, bash, or another shell.
- Prefix local shell commands with `rtk` when this machine requires it.

## Local Deploy
- Deploy prompts to the harnesses in use: `scripts/sync-ai-prompts --target claude,opencode --deploy`.

## Preferences
- Prefer Bun over npm/yarn/pnpm when no repo convention says otherwise.
- If a Superpowers-style workflow plugin is installed, treat its workflows as opt-in: run them only on explicit request or a repo instruction.
- Name the `consolidate-agents-md` skill explicitly when suggesting the context-consolidation workflow at task completion.

## Project Instruction Layout
- Default to gitignored project instructions. For projects explicitly opting into sharing, track sanitized `AGENTS.md` and its `CLAUDE.md` companion, and ignore `AGENTS.local.md` plus its `CLAUDE.local.md` companion. The shared file must request reading the optional local file; local notes must not relax shared security or verification requirements. Migrate projects only when requested.
```
