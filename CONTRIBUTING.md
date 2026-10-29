# Contributing

Open an issue before starting a bug fix or a substantial change, and reference it in the PR (`Closes #NN` for a completed fix). Branch from `develop`, keep changes small, and preserve unrelated local settings. Report suspected vulnerabilities through [SECURITY.md](SECURITY.md), not a public issue.

## Sources and generated files

Edit `prompts/`, `agents/`, and `templates/` sources. Rendered `build/` files are outputs, not source. Keep local and private overlays and generated output out of commits. Do not deploy into a contributor's global configuration as part of a test.

## Checks and documentation

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
python -m py_compile scripts/render_prompts.py scripts/render_invariants.py scripts/render_agents.py scripts/render_hermes.py scripts/update.py scripts/install_workflow.py scripts/lint_prompts.py scripts/scan_prompt_sources.py scripts/check_harness_docs.py scripts/check_harness_contract.py scripts/check_docs_impact.py scripts/check_docs_links.py
scripts/sync-ai-prompts --check
scripts/sync-ai-prompts --dry-run
scripts/render-agents --check
```

CI also runs the stack conventions checker (`python3 .github/stack/stack-check.py`), actionlint, and the macOS and Windows launcher tests. Use [maintenance guidance](docs/MAINTENANCE.md) for docs-impact receipts and exclusions: `.github/`, tests, and docs are outside receipt domains. Review compatibility, installation, update, and recovery instructions when paths, flags, overlays, or supported harnesses change. `render-agents --verify` checks role-file existence only; it does not validate model behavior.

## Releases

Feature and fix PRs target `develop` and are squash-merged. The version bump follows the conventional-commit titles since the last tag: `feat` is minor, `fix` and `deps` are patch, `!` or `BREAKING CHANGE:` is major; `docs`, `chore`, `ci`, `test`, `style` alone do not release.

1. On `develop`, move the `Unreleased` changelog entries under a new `## [X.Y.Z] - YYYY-MM-DD` heading, by PR. The version lives only in the changelog and the tag.
2. Open a PR from `develop` to `main` and merge it with a merge commit, never a squash, so `main` stays an ancestor of `develop`.
3. Tag the merge on `main` as `v<version>` and push the tag. The release workflow checks the tag is on `main`, runs the docs-impact guard from the previous tag, and publishes the release.
