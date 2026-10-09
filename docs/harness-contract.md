# Harness Contract

This is the single source of truth for the supported harnesses: global rules path, override, and the
receipts behind the claim. If a harness is not here, the repo does not claim to support it; use the
generic project-level `AGENTS.md` target instead.

Verified 2026-09-17 against upstream docs; omp verified 2026-09-24 from installed source. `confidence`
reflects whether the vendor documents the path directly (`high`), it is inferred from a consistent
pattern (`medium`), or it is not vendored (`n/a`).

| Harness | Global rules file | Override | Confidence | Source |
|---|---|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` (+ `~/.claude/settings.json`) | `CLAUDE_AGENTS_PATH`, `CLAUDE_CONFIG_DIR` | high | code.claude.com/docs/en/memory |
| OpenAI Codex | `$CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`) | `CODEX_AGENTS_PATH`, `CODEX_HOME` | high | developers.openai.com/codex/agent-configuration/agents-md |
| OpenCode | `~/.config/opencode/AGENTS.md` (+ `opencode.json`) | `OPENCODE_AGENTS_PATH`, `OPENCODE_CONFIG_DIR` | high | opencode.ai/docs/rules/ |
| Command Code | `~/.commandcode/AGENTS.md` (+ `settings.json`) | `COMMANDCODE_AGENTS_PATH` | medium | commandcode.ai/docs/memory |
| Antigravity | `~/.gemini/GEMINI.md`; workspace `.agents/rules/` | `ANTIGRAVITY_AGENTS_PATH`, none native | high | antigravity.google/docs/rules-workflows/ |
| Hermes Agent | `agent.coding_instructions` in `$HERMES_HOME/config.yaml`; project `.hermes.md`/`HERMES.md` > `AGENTS.override.md` > `AGENTS.md` | `HERMES_AGENTS_PATH` (project file) | high | hermes-agent.nousresearch.com/docs/user-guide/features/context-files |
| Oh My Pi | `~/.omp/agent/AGENTS.md` (`<agentDir>/AGENTS.md`, follows `PI_CODING_AGENT_DIR`) | `OMP_AGENTS_PATH`, `PI_CODING_AGENT_DIR` | high | installed omp 18.2.11 source (omp.sh) |
| Generic | none (project-level `AGENTS.md` only) | `GENERIC_AGENTS_PATH` | n/a | - |

## Per-harness notes

### Claude Code
- Global memory `~/.claude/CLAUDE.md`; hooks and skills live in `~/.claude/settings.json` and
  `~/.claude/agents/`, `~/.claude/skills/`.
- On Windows, `~/.claude` means `%USERPROFILE%\.claude`. `CLAUDE_CONFIG_DIR` relocates config.
- The desktop Code tab runs the same engine and reads the same files; the Chat/Cowork tab does not
  (see `docs/surfaces.md`).
- Skills and hooks are first-class; the `UserPromptSubmit` hook is the invariants channel.

### OpenAI Codex
- Global rules `$CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`), read as `AGENTS.override.md` then
  `AGENTS.md`; combined byte cap 32 KiB. Config `~/.codex/config.toml`.
- Native Windows documented; the Windows spelling of `CODEX_HOME` is not explicitly documented, so it
  resolves like other tools (`%USERPROFILE%\.codex`).
- Custom roles in `~/.codex/agents/*.toml`; a role applies only when `spawn_agent` passes its
  `agent_type` with `fork_turns="none"`.

### OpenCode
- Global rules `~/.config/opencode/AGENTS.md`; config `opencode.json` or `opencode.jsonc`; agents in
  `~/.config/opencode/agents/` (plural); skills in `~/.config/opencode/skills/`.
- Same path on macOS. On Windows, run under WSL (recommended) or use
  `%USERPROFILE%\.config\opencode`. A WSL install reads the WSL home, separate from native Windows.
- Permission keys include `read`, `edit` (gates `write`/`edit`/`apply_patch`), `bash`, `task`, `glob`,
  `grep`, `list`, `todowrite`, `webfetch`, `websearch`, `external_directory`, `lsp`, `skill`,
  `question`. Unlisted custom/MCP tools fall back to global defaults.

### Command Code
- Global rules `~/.commandcode/AGENTS.md`; project rules `./AGENTS.md`; settings and hooks in
  `~/.commandcode/settings.json`; skills and agents in `~/.commandcode/skills/` and `agents/`.
- Home is resolved from `HOME`/`USERPROFILE`, so Windows native gives `%USERPROFILE%\.commandcode`.
  Binary aliases: `cmd`/`command-code`/`commandcode` (POSIX), `cmdc` (native Windows).
- Confidence is medium because the memory path is documented but the per-OS spelling is inferred.

### Antigravity
- One rules file for all surfaces: `~/.gemini/GEMINI.md`. Workspace rules in `.agents/rules/`
  (`.agent/rules/` still accepted), activation modes Manual/Always On/Model Decision/Glob, 12,000-char
  cap per file. Workspace context also parses `AGENTS.md`.
- Per-surface app data: `~/.gemini/antigravity/` (desktop), `~/.gemini/antigravity-ide/` (IDE),
  `~/.gemini/antigravity-cli/` (CLI, with `settings.json`, `skills/`, `plugins/`). Global MCP
  `~/.gemini/config/mcp_config.json`. Hooks `hooks.json` in `.agents/` or `~/.gemini/config/`
  (`PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`); `PreInvocation` can return
  `injectSteps[].ephemeralMessage`, the invariants channel for this harness.
- Headless: `agy -p` with `--output-format text|json|stream-json`, `--effort`, `--continue`.
- Custom subagents: `.agents/agents/<name>.md` (workspace) or `~/.gemini/config/agents/<name>.md`
  (global), YAML frontmatter `name`, `description`, `tools` (exact names; a misspelled tool can hang the
  subagent), `subagent`, `mainAgent`, `model: inherit|flash|pro`, `commandExecutionPolicy`.
- The desktop vs IDE global-skills path is contradictory in upstream docs
  (`~/.gemini/config/skills/` vs `~/.gemini/antigravity/skills/`); unresolved, so skills are out of scope.

### Hermes Agent
- No global Markdown rules file. Global operational rules go in `agent.coding_instructions` (standing
  coding rules appended to the coding brief) or `agent.system_prompt` in `$HERMES_HOME/config.yaml`.
  `SOUL.md` is identity/persona (system-prompt slot 1) and is not written by this repo.
- Project context loads exactly one file, first match wins: `.hermes.md`/`HERMES.md` >
  `AGENTS.override.md` > `AGENTS.md` > `CLAUDE.md` > `.cursorrules`, plus git-root-to-CWD chain merge.
- Desktop app shares `$HERMES_HOME` with the CLI. Windows default `%LOCALAPPDATA%\hermes`; WSL uses
  `~/.hermes`. Non-interactive: `hermes chat -q`.
- Skills `$HERMES_HOME/skills/`; delegation via `delegate_task`; hooks via plugins/config.
- No per-role prompt file: delegation is configured under `delegation:` in `config.yaml`, so the six
  roles are a manual paste rather than a rendered file.
- Global rules are merged with `scripts/render-hermes --deploy`, a comment-preserving line edit that
  sets `agent.coding_instructions` and backs up `config.yaml` first.

### Oh My Pi
- Global rules `~/.omp/agent/AGENTS.md` (`<agentDir>/AGENTS.md`); `agentDir` defaults to
  `~/.omp/agent` and follows `PI_CODING_AGENT_DIR`. Named profiles (`--profile`, `OMP_PROFILE`) move it
  to `~/.omp/profiles/<name>/agent` and win over `PI_CODING_AGENT_DIR`; the renderers follow the same order
  (`OMP_AGENTS_PATH`/`OMP_AGENTS_DIR`, then the profile, then `PI_CODING_AGENT_DIR` for the rules file,
  ignoring a value that a parent's profile switch left behind). `PI_CONFIG_DIR` renames `~/.omp` for every path.
- Also reads cross-harness user files `~/.agent/AGENTS.md` and `~/.agents/AGENTS.md`; `~/.claude` user
  sources only when opted in (`skills.enableClaudeUser`).
- Project context priority: `.omp/AGENTS.md` (from the nearest non-empty `.omp` dir; a nearer settings-only `.omp` hides a parent's) > `.claude/CLAUDE.md` >
  `.agent(s)/AGENTS.md` > standalone `AGENTS.md`/`CLAUDE.md` walked up from cwd.
- Config `~/.omp/agent/config.yml`, model roles under `modelRoles` (`default`, `smol`, `slow`, plus
  `task`, `plan`, etc).
- Task agents: user `~/.omp/agent/agents/*.md`, project `.omp/agents/*.md`; markdown with YAML
  frontmatter `name`, `description`, `tools`, `model` (`@role` alias or provider/model id),
  `thinkingLevel`, `spawns`. Precedence project > user > bundled (scout, reviewer, security-reviewer,
  task, sonic); a user `reviewer` shadows the bundled one. User task agents resolve from HOME
  (`~/.omp/agent/agents`, or the profile's `agent/agents`) and ignore `PI_CODING_AGENT_DIR`; this repo's
  override is `OMP_AGENTS_DIR`. `.claude/agents` is not read as omp task
  agents.
- Skills `~/.omp/agent/skills`, `.omp/skills`, `~/.agents/skills`/`.agents/skills`; `~/.claude/skills`
  only when opted in. Hooks `~/.omp/agent/hooks/pre|post` and `.omp/hooks/pre|post`; extensions in
  `<configDir>/extensions`. No documented invariants-injection channel is wired by this repo (advisory,
  like OpenCode/Codex).
- Non-interactive: `omp -p`, `--mode json|rpc`; thinking depth via `--thinking <level>`. Surfaces:
  CLI/TUI, plus `omp acp` (Agent Client Protocol server) for editors; no desktop app.
- Linux/macOS `~/.omp/`; Windows native unverified (inferred `%USERPROFILE%\.omp\`); WSL reads the WSL
  home. Plain `pi` (the upstream project omp forks) stays in `docs/legacy-harnesses.md`.

## OpenCode effort variants (2026-10-09)

Read from the OpenCode v2.0.25 source and the models.dev catalog it loads. Rendered OpenCode agents now
carry effort as `variant`, not `reasoningEffort`.

- A v1-style agent's unknown frontmatter keys are collected into `options` (`packages/core/src/v1/config/agent.ts`),
  and `migrateAgent` sends `options` verbatim as `request.body` (`packages/core/src/v1/config/migrate.ts`). A
  `reasoningEffort` key therefore reached the provider as a raw camelCase body field, not as its effort setting.
- The known `variant` field joins the model as `provider/model#variant`. For OpenAI-compatible providers,
  including `opencode-go`, the variant ID is the effort value and sets the provider's `reasoningEffort`
  setting (`packages/core/src/variant.ts`).
- Variants come from each model's catalog `reasoning_options`: DeepSeek V4.1 Flash, GLM-5.3, and GLM-5.3
  Flash declare `low`, `high`, and `max`; Kimi K3 declares only `max`. An undeclared variant fails with
  `VariantUnavailableError` (`packages/core/src/model-resolver.ts`).

The default effort map renders `low` as `low`, `medium` and `high` as `high`, and `xhigh` and `max` as
`max`; the flagship tier (Kimi K3) pins `max`. `variants` in `prompts/models.json` lists each model's
declared names, and rendering fails when a mapped variant is missing from it. A tier left to inherit the
session model renders no variant, since the session model may not declare it. Changes that need care in
`models.local.json`: a tier pointing at another model (add its `variants` entry and a matching
`effort_map`), a per-agent effort override on a Kimi K3 role, and replacing the flagship object with a
plain model string (both drop the pinned `max`). The old behavior needs `"effort_key": "reasoningEffort"`
and the previous map (`medium` to `medium`, `xhigh` and `max` to `high`). That the provider ignores the
raw body key is inferred, not observed.

## Claude Haiku 5.5 (2026-10-08)

The API model ID is `claude-haiku-5-5`, released 2026-10-07. Current Claude Code resolves `haiku` to
Haiku 5.5 on the Anthropic API; Bedrock, Google Cloud, Microsoft Foundry, and Claude Platform on AWS
resolve it to Haiku 4.5, which has no effort control. The Claude `cheap` tier is now the plain `haiku`
alias, so each role keeps its own effort: explorer at `low`, researcher at `medium`. See
[Claude Code model configuration](https://code.claude.com/docs/en/model-config). Since 2026-10-09 the
explorer runs at `medium` and the verifier moved to the cheap tier at `medium`; the README roster has
current values.

Haiku 5.5 is the first Haiku with adaptive thinking and effort (`medium` default, `low` through
`max`), a 1M-token context, and 128k output. Pricing is $0.10 / $0.50 per MTok (cache read $0.01) for
prompts up to 100k tokens and $0.50 / $2.50 (cache read $0.05) above, so its edge over Opus 5.5
($4 / $20) drops from about 40x to 8x once a worker's context passes 100k. The [Haiku 5.5 prompting guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5)
reports that at `low` it is more likely to skip a search, stop early in long agent prompts, or report
a code change without checking it; `medium` roughly halves early stopping at about twice the output
tokens. Search tasks should carry the current date. For `xhigh` and `max`, compare against Sonnet 5.5
on cost and speed.

API integrations must account for these changes from Haiku 4.5, per
[What's new in Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/whats-new-haiku-5-5):

- Manual `budget_tokens`, non-default `temperature`/`top_p`/`top_k`, and assistant prefill return
  errors. Thinking is adaptive and on by default, counts toward `max_tokens`, and can be disabled only
  at `high` effort or below.
- Responses can begin with `thinking` blocks; select blocks by `type`. Thinking text is omitted unless
  `thinking.display` is `"summarized"`.
- Changing earlier turns invalidates thinking blocks, and thinking blocks replay only in the producing
  or a linked account.
- The newer tokenizer counts the same text as about 30% more tokens than Haiku 4.5.
- Safety classifiers can return `stop_reason: "refusal"`, with no server-side fallback.
- Computer use on the Claude API and Google Cloud needs `computer_toolset_20260801`.

On 2026-10-08, installed Command Code returned exit 0 from `commandcode --no-auto-update --list-models`
and listed `claude-haiku-5-5`. Its tracked cheap tier is unchanged; set it in `models.local.json` to
use Haiku there.

## Model migration compatibility (2026-09-29)

These model-specific receipts cover the Sonnet 5.5 and GPT-6.1 Sol migration, not a fresh verification
of every harness above. This repo renders prompts and role definitions; API requirements below apply
to integrations that send requests. They do not establish that every supported harness implements the
new APIs or beta features.

### Claude Sonnet 5.5

The API model ID is `claude-sonnet-5-5`. Current Claude Code resolves `sonnet` to Sonnet 5.5 on the
Anthropic API; other providers can resolve an older version, and environment overrides can pin it.
Keep the portable alias; the Haiku 5.5 notes above replace the cheap tier. Start bounded coding at `medium`, harder work at
`high`, and routine lookup at `low`; recalibrate on representative tasks. The adaptive API default of
`high` is not a coding-effort recommendation. See [Claude Code model configuration](https://code.claude.com/docs/en/model-config)
and the [Sonnet 5.5 prompting guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5).

API integrations must account for five compatibility changes:

- Thinking cannot be disabled, and manual token budgets are rejected. Adaptive thinking is the
  default; `between_tools` is the lowest mode without up-front thinking and accepts `low`, `medium`,
  or `high`, with no extra display, budget, or binding fields and no mid-conversation effort changes.
  `xhigh` and `max` require adaptive thinking.
- Forced `tool_choice` values `any` and `tool` are rejected; use `auto` or `none`.
- Thinking is bound to the model, account, and conversation. Replaying it after editing system
  instructions, tools, or history can return HTTP 400; new accounts default to enforcement from
  August 31, 2026. Keep history append-only or use documented binding/drop controls. Preserve signed
  compaction blocks rather than arbitrarily rewriting history.
- Longer progress updates can appear in thinking. Adaptive display updates are a beta option for
  user-facing notes; shorter text is unaffected. Prompt instructions cannot fix a renderer that
  does not expose these updates.
- The old computer tool is rejected on the Claude API and Google Cloud, with a Bedrock exception.
  Advisor pairings cannot use older Opus 4.8, Opus 4.7, or Sonnet 5 models.

These requirements and provider exceptions come from [What's new in Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5).
Per-message effort, signed compaction, and inline tool additions are API/beta opportunities: enable
them only after verifying the harness and provider support. This migration adds no API integration.

### OpenAI GPT-6.1 Sol

Codex `mid` and `flagship` tiers use `gpt-6.1-sol`, split by role effort. The API accepts `low`,
`medium` (default), `high`, `xhigh`, and `max`; it rejects `none` and `minimal`. Tool calling requires
the Responses API. See the [GPT-6.1 Sol model reference](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

Native Responses multi-agent is beta and shares the model and tools across agents; it is separate
from Codex custom roles with independent model, effort, and tool settings. Async execution and
mid-turn steering are existing GPT-6 family features, not new GPT-6.1 features. See the
[Responses multi-agent guide](https://developers.openai.com/api/docs/guides/responses-multi-agent).
Cache-preserving effort changes through `configuration_update` apply only to standard single-agent
mode, not native multi-agent. Verify harness support before relying on this API control; see the
[reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#change-reasoning-mid-conversation).

### Deployment receipt

On 2026-09-29, installed Command Code v1.70.0 returned exit 0 from
`commandcode --no-auto-update --list-models`, listing `claude-sonnet-5-5` as recommended and
`claude-sonnet-5` as previous. This confirms its advertised model ID, not API compatibility.

Preview the selected targets, then verify the rendered and deployed role files with
`scripts/render-agents --target <list> --check` and `scripts/render-agents --target <list> --verify`.
Also inspect the running harness's resolved model, provider, supported effort, and account access;
role-file presence alone does not prove model availability or alias resolution. Local model and
effort overrides intentionally win over tracked defaults. Record the effective configuration in a
private deployment receipt rather than publishing local override values.

## Unverified

- Command Code per-OS home spelling (medium).
- Antigravity native-Windows config spelling; upstream writes `~/` without a Windows variant.
- Antigravity global skills path (docs contradict).
- Oh My Pi native-Windows home spelling; inferred `%USERPROFILE%\.omp\`, not vendor-documented.
