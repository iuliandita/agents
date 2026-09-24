# Private Overlay

Copy this file to `prompts/private.md` for sensitive local context: hosts, networks, identities, and
machine paths. It stays out of git and is appended after the shared core and `prompts/local.md`, but only
for the harnesses you trust. The model provider behind a harness is your choice, so there is no default:
list trusted harnesses one per line in `prompts/private-harnesses.txt`, or comma-separated in
`AGENTS_PRIVATE_HARNESSES`. Use `all` to send it to every harness. Rendering prints a notice for each
harness it is withheld from.

```text
# prompts/private-harnesses.txt
claude
codex
```

```markdown
## System
- Host `workstation`: Linux, zsh; dotfiles managed from `~/code/example/dotfiles`.

## Local Paths
- Canonical skills repo: `~/code/example/skills`
- Canonical agents repo: `~/code/example/agents`

## Networks
- Home lab `*.lab.example` resolves through the lab DNS server; reachable only over the lab VPN.

## Git Identities
- Personal repos under `~/code/personal/` commit as the personal identity via `includeIf`.
```
