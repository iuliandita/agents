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

All rendering and deploy tooling, including the workflow installer, uses only
the Python standard library. Install the development dependencies to run the
checks (pytest, plus PyYAML for tests that parse rendered YAML):

```sh
python -m pip install -r requirements-dev.txt
```

The `.venv/` directory is gitignored. The full test suite uses the CI Python
version recorded in [ci.yml](.github/workflows/ci.yml).

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
The workflow installer needs no third-party packages; a missing `import yaml`
now affects only the test suite, not installation.

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

Each component deploys separately. `scripts/update` runs the prompt, Hermes, subagent, and invariants-hook deploys in order for the harnesses in `prompts/deploy-targets.txt`; the consolidation skill and project files stay manual:

| Component | Command | Details |
|---|---|---|
| Everything for saved targets | `scripts/update` | [Agent-driven setup](#agent-driven-setup) |
| Global prompts | `scripts/sync-ai-prompts` | [Render and deploy](#render) |
| Subagent definitions | `scripts/render-agents` | [Agent targets](#agent-targets) |
| Invariants hook | `scripts/render-invariants` | [Hook setup](README.md#invariants-reinforcement) |
| Consolidation skill | `python scripts/install_workflow.py` | [Workflow installation](#context-consolidation-workflow) |
| Shared/local project files | Manual opt-in | [Project instructions](#project-instructions-shared-or-private) |

## Agent-Driven Setup

This runbook is for a coding agent setting the repo up on its user's machine. Run each step, check its
result, and stop on any failure. Steps marked **ask** need the user's answer; do not guess them.

1. **Clone** with git (not a zip download; updates use `git pull --ff-only`) to a stable location, for
   example `~/code/agents`, then `cd` into it. Check: `git status` shows a clean `main`.
2. **Python**: follow [Prerequisites](#prerequisites). Check: `python3 --version` is 3.11 or newer.
   Rendering and deploying need only the standard library.
3. **Detect** installed harnesses: `scripts/update --detect` (`./scripts/update.ps1 --detect` on native
   Windows). It prints one supported harness per line with the evidence found (a binary on PATH, or the
   config home this repo would deploy to, including customized homes such as `CODEX_HOME`). A harness it
   misses can still be listed by hand in the next step.
4. **ask** which harnesses to manage, then write them to `prompts/deploy-targets.txt`, one per line
   (gitignored). Show the user where each will be written and get a yes before going on:
   `scripts/sync-ai-prompts --list-targets` (rules files) and `scripts/render-agents --list-targets`
   (subagent dirs). Customized homes (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `OPENCODE_CONFIG_DIR`,
   `PI_CODING_AGENT_DIR`, `OMP_PROFILE`, `HERMES_HOME`) are honored when they are set in this shell.
   Hermes is different: its global rules merge into `agent.coding_instructions` in `$HERMES_HOME/config.yaml`
   (default `~/.hermes/config.yaml`), shown by `scripts/render-hermes --dry-run`; ignore the `HERMES.md`
   project-file line in `--list-targets`. Every other target is one rules file plus six subagent files.
5. **Optional overlays** (see [Local and private overlays](README.md#local-and-private-overlays)): copy
   `prompts/local.example.md` to `prompts/local.md` for preferences that are safe with any model provider.
   **ask** before creating `prompts/private.md` or `prompts/private-harnesses.txt`: which harnesses may
   receive hosts, identities, and paths depends on the model provider behind each one, which only the
   user knows. Never write `all` without the user saying so, and check that `AGENTS_PRIVATE_HARNESSES` is
   not already set in the environment, since it overrides the file. If the user will edit or contribute
   to the repo, offer to list their private hosts and names in `prompts/private-patterns.txt` so lint
   catches them in any tracked file.
6. **Preview**: `scripts/update --no-pull --dry-run`. It prints the effective overlay trust (`private
   overlay: sent to ...` and where the list came from), then every file it would write. Check: it ends with
   `update complete` and names only the confirmed targets. **ask** before continuing if any line says
   `would replace unmanaged`: that is content the user wrote (their own `CLAUDE.md`, `reviewer.md`, or
   Hermes `coding_instructions`), which deploy replaces after backing it up.
7. **Deploy**: `scripts/update --no-pull`. Existing files are backed up to `.backups/` first. Check: it
   ends with `update complete`; its last steps are `--verify` (every role file present) and `--status`
   (every rules file in sync).
8. **Schedule** a daily run. **ask** which scheduler, what time (local timezone), and how failures should
   reach the user (log file, syslog/journal, or mail); default to the platform's native scheduler, 06:30,
   and the scheduler's own failure log if they have no preference. `scripts/update` pulls fast-forward only, never prompts (git runs
   non-interactively with a timeout), refuses to run over local tracked edits or alongside another run, and
   exits non-zero on any failure. Schedulers start with a minimal environment: copy into the job every
   variable the setup relied on (`AGENTS_PYTHON`, customized homes from step 4, `*_AGENTS_PATH` or
   `*_AGENTS_DIR` overrides, `AGENTS_PRIVATE_HARNESSES`). Replace `<checkout>` with the real absolute path.

   ```bash
   # cron (Linux/macOS): daily at 06:30; failures also go to syslog
   mkdir -p "$HOME/.cache"
   crontab -l 2>/dev/null | { cat; echo '30 6 * * * cd "<checkout>" && scripts/update >> "$HOME/.cache/agents-update.log" 2>&1 || logger -t agents-update "update failed, see ~/.cache/agents-update.log"'; } | crontab -
   ```

   ```ini
   # systemd user units (Linux): two files, then
   #   systemctl --user daemon-reload && systemctl --user enable --now agents-update.timer
   # Failures show in `systemctl --user status agents-update` and `journalctl --user -u agents-update`.

   # ~/.config/systemd/user/agents-update.service
   [Service]
   Type=oneshot
   WorkingDirectory=<checkout>
   ExecStart=<checkout>/scripts/update
   # Environment=CODEX_HOME=/path/if/customized

   # ~/.config/systemd/user/agents-update.timer
   [Timer]
   OnCalendar=daily
   Persistent=true

   [Install]
   WantedBy=timers.target
   ```

   ```powershell
   # Windows Task Scheduler (PowerShell 7); the inner quotes keep paths with spaces intact
   $script = "<checkout>\scripts\update.ps1"
   schtasks /Create /SC DAILY /ST 06:30 /TN agents-update /TR "pwsh -NoProfile -File `"$script`""
   ```

   Check: trigger the scheduled job itself once (`systemctl --user start agents-update.service`,
   `schtasks /Run /TN agents-update`, or the cron command in a minimal shell such as `env -i HOME="$HOME"
   sh -c '...'`) and confirm it exits 0 and `--status` reports every target in sync.

Report to the user what was deployed where, the backup location, and when the schedule runs. To change
targets later, edit `prompts/deploy-targets.txt`; the next run applies it. `AGENTS_DEPLOY_TARGETS` or
`--targets` override the file for one run.

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

If `prompts/local.md` exists, it is merged into every rendered and deployed file after the shared core. If `prompts/private.md` exists, it follows `local.md`, but only for harnesses listed in `prompts/private-harnesses.txt` (one name per line) or `AGENTS_PRIVATE_HARNESSES` (comma-separated); `all` lists every supported harness, and there is no default. A withheld private overlay prints a notice. Project-level targets (`generic`, and `hermes` through `HERMES_AGENTS_PATH`) never receive either overlay; the global Hermes merge through `scripts/render-hermes` follows the same rules as the other harnesses. Start from `prompts/local.example.md` and `prompts/private.example.md`.

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

### Hermes Global Rules

Hermes has no global rules file. Merge the shared core into `agent.coding_instructions` in
`$HERMES_HOME/config.yaml` (default `~/.hermes/config.yaml`):

```bash
scripts/render-hermes --dry-run
scripts/render-hermes --deploy
```

The merge is a comment-preserving line edit and backs the config up first, so unrelated settings and
comments are kept. Override the target with `--path` or `HERMES_CONFIG_PATH`, and the home with
`HERMES_HOME`.

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

<!-- harness-targets:start -->
| Harness | Support | Target | Notes |
|---|---|---|---|
| Claude Code | deployable | `~/.claude/CLAUDE.md` |  |
| OpenAI Codex | deployable | `~/.codex/AGENTS.md` | Global path follows $CODEX_HOME (default ~/.codex); set CODEX_AGENTS_PATH when CODEX_HOME is customized. |
| OpenCode | deployable | `~/.config/opencode/AGENTS.md` | Same home-relative path on macOS; on Windows run under WSL or use %USERPROFILE%\.config\opencode. |
| Command Code | deployable | `~/.commandcode/AGENTS.md` |  |
| Antigravity | deployable | `~/.gemini/GEMINI.md` | Desktop, IDE, and CLI share ~/.gemini/GEMINI.md; workspace rules live in .agents/rules/ (12k char cap per file). |
| Oh My Pi | deployable | `~/.omp/agent/AGENTS.md` | Global path follows PI_CODING_AGENT_DIR (default ~/.omp/agent); named profiles use ~/.omp/profiles/<name>/agent. |
| Hermes Agent | manual | `manual override via HERMES_AGENTS_PATH` | Global rules merge into agent.coding_instructions in $HERMES_HOME/config.yaml; project rules deploy to HERMES.md or AGENTS.override.md via HERMES_AGENTS_PATH. |
| Generic AGENTS.md | manual | `manual override via GENERIC_AGENTS_PATH` | Project-level AGENTS.md for tools with no verified global rules path; deploy with GENERIC_AGENTS_PATH pointing at a project file. |
<!-- harness-targets:end -->

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
| Oh My Pi | `~/.omp/agent/agents/` | `OMP_AGENTS_DIR` |

Oh My Pi reads task agents from `~/.omp/agent/agents`, or `~/.omp/profiles/<name>/agent/agents` when
`OMP_PROFILE` (or `PI_PROFILE`) names a profile, even when `PI_CODING_AGENT_DIR` moves its rules file. The
renderers follow the same profile resolution; `OMP_AGENTS_DIR` overrides it.

Hermes has no per-role prompt file, so its six roles are a manual paste; delegation is configured under `delegation:` in `~/.hermes/config.yaml`.

After a real deploy, `scripts/render-agents --verify` confirms all six role files exist in each harness's agent directory.

`shell-ro` becomes shell access only on Codex, where `sandbox_mode = "read-only"` enforces the boundary. Claude Code, OpenCode, Command Code, Antigravity, and Oh My Pi omit shell access for those agents and keep their native read and search tools.

Existing `shell_ro_wrappers` settings are accepted for compatibility but no longer grant shell access. Redeploying the agents removes their references to the old `agents-shell-ro-guard.py` hook; the previously deployed hook file is left in place and is unused by the updated agents.

Model tiers and effort maps come from the tracked `prompts/models.json`; `prompts/models.local.json` overrides them. Copy `prompts/models.local.example.json` to start. A harness with no tier map fails unless `--allow-inherit` is passed.

A tier value is a model string, `null` (inherit the session model), or an object `{"model": "<id or null>", "effort": "<level>"}`. The object form is for single-model setups: point every tier at the same model and let the tier set the depth. Effort resolves in this order: `agents.<name>.effort` in the override file, then the tier's `effort`, then the role's own `effort`; `effort_map` then translates the level into the harness's vocabulary. A tier in `models.local.json` replaces the whole default entry, so a plain string there drops a default tier effort. A missing `apex` falls back to `flagship`, effort included; an explicit `"apex": null` inherits instead. Tier objects and the `max` level need this version or later; older checkouts reject them.

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
local and private overlays (`prompts/local.md`, `prompts/private.md`).

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

Install into explicit skill directories (Python 3.11+ required):

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
