# Install And Deploy

## Prerequisites

Use Git, Python 3.11+, and Bash. GitHub CLI (`gh`) is not required to clone,
render, or deploy. Clone this repository using its HTTPS URL from GitHub's Code
menu, then run commands from the checkout root:

```sh
python3 --version
python3 -m venv .venv
. .venv/bin/activate
```

Check the version before creating the environment. On macOS, `python3` may resolve
to an older system interpreter even when a newer Homebrew Python is installed.
If you use Homebrew, install Python if needed with `brew install python`, then
select it explicitly when creating the environment:

```sh
"$(brew --prefix python)/bin/python3" --version
"$(brew --prefix python)/bin/python3" -m venv .venv
. .venv/bin/activate
```

This avoids hardcoding Apple Silicon or Intel installation paths. See
[Homebrew's Python guidance](https://docs.brew.sh/Homebrew-and-Python) and
[Python virtual environments](https://docs.python.org/3/library/venv.html).
Do not install packages into the system Python or create a global `python` alias.

Prompt, subagent, and invariants rendering use the Python standard library.
For the consolidation workflow and development checks, install the dependencies
inside the activated environment:

```sh
python -m pip install -r requirements-dev.txt
```

PyYAML is required by the workflow installer; pytest is used for verification.
Missing PyYAML does not block global prompt deployment. The `.venv/` directory
is gitignored. The full test suite uses the CI Python version recorded in
[ci.yml](.github/workflows/ci.yml).

The shell launchers select `AGENTS_PYTHON` when set, then the checkout's
`.venv/bin/python`, then `python`, then `python3` on PATH. They reject Python
versions below 3.11 with setup guidance. Unsupported PATH candidates are skipped;
an invalid explicit override or checkout environment fails without fallback. Activation is optional for these
launchers; use it for the direct `python` commands in this guide. To use an
environment elsewhere, supply its executable path, not a shell command:

```sh
AGENTS_PYTHON="$HOME/my environments/agents/bin/python" scripts/sync-ai-prompts --target claude --dry-run
```

If `python` is not found, activate the environment or use the shell launcher.
If `import yaml` fails in the workflow installer, run the dependency command
above using the same interpreter that will run the installer.

## Windows (Native PowerShell)

The bash wrappers are POSIX-only; on native Windows use the shipped PowerShell
launchers. They resolve the same interpreter order as the bash launchers
(`AGENTS_PYTHON`, then the checkout `.venv`, then `python`/`python3`, then the
`py -3` launcher) and mirror their behavior:

```powershell
./scripts/sync-ai-prompts.ps1 --check
./scripts/render-agents.ps1 --check
./scripts/render-invariants.ps1 --dry-run
```

PowerShell 7+ (`pwsh`) is expected. Rendered writes are LF and backup names are
Windows-safe. If you prefer to call the Python scripts directly, pass
`--repo-root .`. Run inside WSL to use the bash wrappers unchanged; a WSL install
reads the WSL home, separate from a native Windows install. Point both at one
home with the native env var (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `HERMES_HOME`)
if you want a shared config.

Deployment is separate for each component; none of these commands installs the others:

| Component | Command | Details |
|---|---|---|
| Global prompts | `scripts/sync-ai-prompts` | [Render and deploy](#render) |
| Subagent definitions | `scripts/render-agents` | [Agent targets](#agent-targets) |
| Invariants hook | `scripts/render-invariants` | [Hook setup](README.md#invariants-reinforcement) |
| Consolidation skill | `python scripts/install_workflow.py` | [Workflow installation](#context-consolidation-workflow) |
| Shared/local project files | Manual opt-in | [Project instructions](#project-instructions-shared-or-private) |

## Render

```bash
scripts/sync-ai-prompts
```

Rendered files go to `build/generated/`. Harnesses that share the same output filename are rendered into per-harness subdirectories.

## Deploy

```bash
scripts/sync-ai-prompts --target claude,codex --dry-run
scripts/sync-ai-prompts --target claude,codex --deploy
```

Existing files are backed up under `.backups/` before replacement. Deploy writes only to harnesses with resolved target paths. Manual harnesses are skipped unless their environment variable points at a project or per-agent operational rules file.

Real deploys refuse when two selected harnesses resolve to the same path, for example after overriding a path with its `*_AGENTS_PATH` env var. Use `--target` for routine deploys so only the harnesses you use are written.

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
HERMES_AGENTS_PATH="$PWD/HERMES.md" scripts/sync-ai-prompts --target hermes --deploy
GENERIC_AGENTS_PATH="$PWD/AGENTS.md" scripts/sync-ai-prompts --target generic --deploy
```

## List Targets

```bash
scripts/sync-ai-prompts --list-targets
```

Use this before deploys when checking the current harness names, support levels, and resolved paths.

## Override Paths

Use env vars when a tool's real operational rules path differs from the default:

```bash
CODEX_AGENTS_PATH="$CODEX_HOME/AGENTS.md" scripts/sync-ai-prompts --target codex --deploy
OPENCODE_AGENTS_PATH="$HOME/.config/opencode/AGENTS.md" scripts/sync-ai-prompts --target opencode --deploy
ANTIGRAVITY_AGENTS_PATH="$HOME/.gemini/GEMINI.md" scripts/sync-ai-prompts --target antigravity --deploy
```

## Default Targets

| Harness | Support | Target | Notes |
|---|---|---|---|
| Claude Code | deployable | `~/.claude/CLAUDE.md` |  |
| OpenAI Codex | deployable | `~/.codex/AGENTS.md` | Global path follows $CODEX_HOME (default ~/.codex); set CODEX_AGENTS_PATH when CODEX_HOME is customized. |
| OpenCode | deployable | `~/.config/opencode/AGENTS.md` | Same home-relative path on macOS; on Windows run under WSL or use %USERPROFILE%\.config\opencode. |
| Command Code | deployable | `~/.commandcode/AGENTS.md` |  |
| Antigravity | deployable | `~/.gemini/GEMINI.md` | Desktop, IDE, and CLI share ~/.gemini/GEMINI.md; workspace rules live in .agents/rules/ (12k char cap per file). |
| Hermes Agent | manual | `manual override via HERMES_AGENTS_PATH` | Global rules merge into agent.coding_instructions in $HERMES_HOME/config.yaml; project rules deploy to HERMES.md or AGENTS.override.md via HERMES_AGENTS_PATH. |
| Generic AGENTS.md | manual | `manual override via GENERIC_AGENTS_PATH` | Project-level AGENTS.md for tools with no verified global rules path; deploy with GENERIC_AGENTS_PATH pointing at a project file. |

## Agent Targets

Select only the harnesses you use. Prompt deployment does not deploy these definitions:

```bash
scripts/render-agents --target claude,codex --dry-run
scripts/render-agents --target claude,codex --deploy
```

Deployment writes one file per agent into these directories. Override with the environment variable when a harness home is customized.

| Harness | Directory | Override |
|---|---|---|
| Claude Code | `~/.claude/agents/` | `CLAUDE_AGENTS_DIR` |
| OpenAI Codex | `~/.codex/agents/` | `CODEX_AGENTS_DIR` |
| OpenCode | `~/.config/opencode/agents/` | `OPENCODE_AGENTS_DIR` |
| Command Code | `~/.commandcode/agents/` | `COMMANDCODE_AGENTS_DIR` |
| Antigravity | `~/.gemini/config/agents/` | `ANTIGRAVITY_AGENTS_DIR` |

Hermes has no per-role prompt file, so its six roles are a manual paste; delegation is configured under `delegation:` in `~/.hermes/config.yaml`.

After a real deploy, `scripts/render-agents --verify` confirms all six role files exist in each harness's agent directory.

`shell-ro` becomes shell access only on Codex, where `sandbox_mode = "read-only"` enforces the boundary. Claude Code, OpenCode, Command Code, and Antigravity omit shell access for those agents and keep their native read and search tools.

Existing `shell_ro_wrappers` settings are accepted for compatibility but no longer grant shell access. Redeploying the agents removes their references to the old `agents-shell-ro-guard.py` hook; the previously deployed hook file is left in place and is unused by the updated agents.

Model tiers and effort maps come from the tracked `prompts/models.json`; `prompts/models.local.json` overrides them. Copy `prompts/models.local.example.json` to start. A harness with no tier map fails unless `--allow-inherit` is passed.

## Project Instructions: Shared Or Private

Choose per project. The default private-only layout keeps `AGENTS.md` and its
`CLAUDE.md` companion gitignored. Opt into the following layout when colleagues
should share the project instructions:

| File | Version control | Purpose |
|---|---|---|
| `AGENTS.md` | Tracked | Portable project context, conventions, and required checks |
| `CLAUDE.md` | Tracked symlink to `AGENTS.md` | Shared Claude instructions |
| `AGENTS.local.md` | Ignored | Optional developer and machine details |
| `CLAUDE.local.md` | Ignored symlink to `AGENTS.local.md` | Local Claude instructions |

Start with [the shared template](templates/project/AGENTS.md.example) and
[the local template](templates/project/AGENTS.local.md.example). Fill in real
project context and verification commands before using the shared template.
Do not copy globally rendered output into the shared file: it can contain the
private overlay from `prompts/private.md`.

Claude loads `CLAUDE.local.md` alongside `CLAUDE.md`. Codex's documented discovery
loads at most one instruction file per directory; `AGENTS.override.md` replaces
that directory's `AGENTS.md`, and fallback filenames do not append another file.
The shared template therefore explicitly asks Codex to read the optional local
file. This is model-followed guidance, not a native import or enforced hook.
See [Claude memory](https://code.claude.com/docs/en/memory) and
[Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

For an existing project:

1. Back up the current instruction files outside the tracked tree. Review their
   content and move private paths, environment details, and preferences into
   `AGENTS.local.md`; retain portable project rules in `AGENTS.md`.
2. Add the optional-local-file paragraph from the shared template to `AGENTS.md`.
3. Remove root ignore entries for the shared `AGENTS.md` and `CLAUDE.md`. Add:

   ```gitignore
   /AGENTS.local.md
   /CLAUDE.local.md
   ```

4. Keep an existing correct `CLAUDE.md` symlink. Where companions do not yet exist,
   create relative links from the project root:

   ```sh
   ln -s AGENTS.md CLAUDE.md
   ln -s AGENTS.local.md CLAUDE.local.md
   ```

   Create the local companion only when the local target exists. Do not overwrite
   existing companions blindly. Where symlinks are unsuitable, use regular
   `CLAUDE.md` and `CLAUDE.local.md` files containing `@AGENTS.md` and
   `@AGENTS.local.md`, respectively; keep the latter ignored.
5. Verify with `git check-ignore -v AGENTS.local.md CLAUDE.local.md` and
   `git status --short`. If the shared files still stay ignored, inspect global
   excludes and `.git/info/exclude` with `git check-ignore -v AGENTS.md CLAUDE.md`.
   Stage only the sanitized shared files and `.gitignore`, then inspect the staged
   diff before committing. Ignore rules do not untrack previously committed files.
6. Start fresh sessions. Ask Codex to identify the instruction files it actually
   read, including the local file. In Claude, check `/memory`. Test with and
   without local files; missing local configuration must not block ordinary work.

Each developer or worktree supplies its own ignored files. Keep cross-project
preferences global and secret values out of instruction files. Local notes may
adjust paths and preferences, but must not weaken shared security or required checks.

This repository keeps its own root instruction files private. These templates
are opt-in examples, not an automatic migration or part of global deployment.

## Context Consolidation Workflow

`skills/consolidate-agents-md/SKILL.md` is the canonical workflow. It retains the
original command's memory consolidation, transcript review, and clearing behavior,
with recoverable file backups, secret redaction, and verification before clearing.
It operates on the selected project only and preserves shared versus local instructions.
The installer installs instructions; it does not run consolidation or touch project memory.

Install into explicit skill directories (Python and the existing PyYAML dependency required):

```sh
python scripts/install_workflow.py --skills-dir "$HOME/.agents/skills" --skills-dir "$HOME/.claude/skills"
python scripts/install_workflow.py --skills-dir "$HOME/.agents/skills" --skills-dir "$HOME/.claude/skills" --deploy
```

The default is a dry run. All destinations are checked before writes; symlinks and
file/directory collisions are refused. Changed regular files are backed up under
`.backups/workflow-*`; identical files are untouched. For a symlinked skill root,
inspect it and pass its intended real directory explicitly. Do not overwrite a link blindly.

To migrate an existing Claude command as well, add
`--legacy-command "$HOME/.claude/commands/consolidate-agents-md.md"` to both commands.
This backs up and replaces the old command with the same portable content; future
updates use the same installer. No separate command implementation is maintained.

Codex and OpenCode discover user skills in `~/.agents/skills`; Claude uses
`~/.claude/skills`. See [Codex skills](https://learn.chatgpt.com/docs/build-skills),
[OpenCode skills](https://opencode.ai/docs/skills), and
[Claude skills](https://code.claude.com/docs/en/skills).
For another harness, either install into its verified skill directory or give it the
absolute path to the installed `SKILL.md` and ask it to read and follow the workflow.
Native Command Code skill discovery is not assumed; the explicit-file route works
with a file-capable agent and can be recorded in the private overlay.

Invoke with `/consolidate-agents-md [repo-path]` in Claude or
`$consolidate-agents-md` in Codex, naming the target in your request. In other
harnesses, ask to run `consolidate-agents-md` through their skill mechanism or
the explicit-file route. The singular spelling `consolidate-agent-md` is a
natural-language alias in the description, not a second installed slash command.

End-of-work prompting is advisory, not a lifecycle hook: the agent suggests the
workflow only when useful and does not consolidate automatically. Explicitly invoke
it for edits and memory clearing, or request review-only/no-memory behavior to narrow
the scope. Existing local policies that prohibit memory access remain effective unless
the user explicitly overrides them. Restart the harness after installing and verify
discovery; installation checks alone do not prove model execution behavior.

## Operational Rules Only

The prompt renderer writes operational coding-agent rules, not persona, identity,
memory stores, provider credentials, model settings, MCP, plugins, or assistant profiles.
The separately installed consolidation workflow can edit project instructions and
clear verified project memory only when explicitly invoked.
