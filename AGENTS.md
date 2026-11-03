# agents

Canonical global prompt rules and subagent roles for coding agents, rendered per harness (Claude Code, Codex, OpenCode, and others) with backed-up deploys. `develop` is the default and nightly branch, `main` is stable.

If `AGENTS.local.md` exists beside this file, read it too. It holds local paths and preferences and never relaxes the rules here.

## Commands

```sh
python -m pip install -r requirements-dev.txt
python scripts/lint_prompts.py
python scripts/scan_prompt_sources.py
python scripts/check_harness_docs.py
python scripts/check_harness_contract.py
python scripts/check_docs_impact.py
python scripts/check_docs_links.py
python -m pytest -q
bash -n scripts/sync-ai-prompts scripts/render-invariants scripts/render-agents scripts/render-hermes scripts/update scripts/python-runtime.sh
python -m py_compile scripts/*.py
scripts/sync-ai-prompts --check
scripts/sync-ai-prompts --dry-run
scripts/render-agents --check
python3 .github/stack/stack-check.py
scripts/sync-ai-prompts && scripts/render-agents
```

CI also runs actionlint, gitleaks, zizmor, CodeQL, and the macOS and Windows launcher tests. The last line renders into `build/generated/`; it never deploys.

## Layout

- Sources: `prompts/` (core, invariants, `harnesses/*.md` fragments), `agents/` (role sources), `templates/`, `skills/`. `prompts/harnesses/AGENTS.md` is the generic-harness fragment, not this file.
- `build/` and everything rendered from it are outputs; never hand-edit them. Overlays `prompts/local.md`, `prompts/private.md`, `prompts/private-harnesses.txt`, and `prompts/models.local.json` are gitignored.
- `scripts/render_prompts.py` holds the harness registry; `scripts/render_agents.py`, `render_invariants.py`, `render_hermes.py`, and `update.py` are the other entry points. Tests are in `tests/`.
- `.github/stack/canon.json` and `stack-check.py` are the source for the vendored copies in the sibling repos (skills, mods, idstack); see `.github/stack/README.md`.
- Docs: [README.md](README.md), [INSTALL.md](INSTALL.md), [CONTRIBUTING.md](CONTRIBUTING.md), [docs/MAINTENANCE.md](docs/MAINTENANCE.md). Adding or removing a harness: [docs/legacy-harnesses.md](docs/legacy-harnesses.md) and [docs/harness-contract.md](docs/harness-contract.md).

## Rules

- Issue first, branch from `develop`, PR into `develop`, conventional commits, `Closes #NN`. Never commit to `main` or `develop`.
- No AI attribution in commits, PRs, tags, or files.
- No private hosts, domains, IPs, machine paths, or work context in tracked files.
- Never deploy to global config paths (`--deploy`) unless the user asks, and always pass `--target`.
- `paperclip` is render-only; project-level targets never receive `local.md` or `private.md`.
- Source changes need a docs-impact receipt: update the docs, then `python scripts/check_docs_impact.py --accept <domain> ...` (see `docs/MAINTENANCE.md`).
- Keep public prompt fragments anonymized and portable; the leak linter and the injection scan gate them.

## For agents

- Every user-facing script takes `--json` (one JSON object on stdout, human output on stderr); keys are in [INSTALL.md](INSTALL.md#messages-exit-codes-and-json-output).
- Messages are lower-case `error:`, `warning:`, `note:` lines on stderr. Exit codes: 0 done, 1 failed or out of sync, 2 usage error, 3 a required tool is missing.
- `scripts/sync-ai-prompts --list-targets` and `scripts/render-agents --list-targets` list harnesses and paths; `sync-ai-prompts --status` and `render-agents --verify` check deployed files.
- The checks under Commands are the full pre-push set; `python3 .github/stack/stack-check.py --list-checks` lists the convention checks.
