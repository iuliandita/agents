# Keeping documentation current

Documentation is part of a change. A new flag needs usage docs, a changed target path or removed harness needs upgrade and rollback steps, and an overlay change needs its trust rules restated. The docs-impact guard flags those obligations. It cannot tell whether the prose is right, so review the affected behavior and say in the PR what you checked.

## Run the check

```bash
python scripts/check_docs_impact.py
python scripts/check_docs_impact.py --explain
python scripts/check_docs_impact.py --base "$(git merge-base origin/develop HEAD)"
python scripts/check_docs_links.py
```

The plain check verifies that every domain's receipt matches its current sources and still meets the `--accept` rules (so a hand-edited lock fails), that every tracked file under `agents/`, `prompts/`, `scripts/`, `skills/`, and `templates/` belongs to exactly one domain.

`check_docs_links.py` is a separate, stateless check: local Markdown links and anchors in every tracked doc must resolve to tracked files, and script commands in the current docs must name tracked scripts and flags those scripts define. Changelog entries are history and `prompts/` fragments are agent context, so the command check skips them; their links are still checked. CI and the release workflow run both scripts.

`--base` adds the range checks: docs a receipt cites must change in the range, a breaking receipt recorded earlier in the range cannot be replaced by a `breaking: none` one (only commits that change a receipt count, so merging the base branch back in is safe), and removing a harness from `scripts/render_prompts.py` needs a breaking receipt that cites `docs/legacy-harnesses.md`. CI runs it against the PR base, or the previous tip on pushes to `develop` and `main`, with full history. Findings print as `error:` lines on stderr. Exit codes for the docs-impact check only: 0 pass, 1 findings, 2 missing tooling or invalid usage. The render, deployment, and updater commands instead use 2 for usage errors and 3 for missing tooling, as documented in INSTALL.md. The check needs Git and Python 3.11 and runs offline.

## Domains

`scripts/check_docs_impact.py` defines the domains in `DOMAINS`; `--explain` prints each domain's files and allowed docs.

| Domain | Covers | Docs it can cite |
|---|---|---|
| prompts | core prompt, invariants, harness fragments | README, INSTALL, surfaces, harness contract, CHANGELOG |
| models-agents | role sources, model tiers, agent renderer | README, INSTALL, harness contract, CHANGELOG |
| harnesses | harness registry and the prompt launcher | README, INSTALL, harness contract, surfaces, legacy harnesses, CONTRIBUTING, CHANGELOG |
| deployment | update, invariants, Hermes, runtime, workflow installer | README, INSTALL, SECURITY, CONTRIBUTING, harness contract, surfaces, CHANGELOG |
| overlays-trust | overlay templates, leak lint, source scan, `.gitignore` | README, INSTALL, SECURITY, this file, CHANGELOG |
| workflow-templates | `skills/` and `templates/` | README, INSTALL, CHANGELOG |
| maintenance | `scripts/check_*.py` | this file, README, INSTALL, CONTRIBUTING, AGENTS, CHANGELOG |

`.github/`, `tests/`, and docs are outside the domains. Action pins have Renovate and actionlint, tests are not user facing, and docs are the obligation itself. New source files count once staged; untracked scratch files are ignored. Change sources and rerun the renderers; never hand-edit rendered output.

## Record a review

Update the docs, then accept the domain after the last source edit, because the receipt covers the exact source fingerprint:

```bash
python scripts/check_docs_impact.py --accept harnesses \
  --docs INSTALL.md,docs/harness-contract.md \
  --note "Document the new target path and its environment override." \
  --breaking none
```

A refactor can need no docs change. Give the specific reason:

```bash
python scripts/check_docs_impact.py --accept deployment \
  --no-impact "Extract the backup naming helper without changing paths, flags, or output." \
  --breaking none
```

Reviewers challenge that reason against the diff; a length check cannot. Generic reasons such as "docs reviewed" are rejected. Do not edit hashes by hand. When two branches touch the same domain, resolve the source, review the combined behavior, and accept again rather than picking one branch's hash.

## Breaking changes

A changed flag, target path, overlay behavior, or removed harness is breaking for anyone with a saved setup. Replace `--breaking none` with the consequence, cite `CHANGELOG.md`, and give backup, upgrade, and rollback steps:

```bash
python scripts/check_docs_impact.py --accept harnesses \
  --docs CHANGELOG.md,INSTALL.md,docs/legacy-harnesses.md \
  --note "Move the removed harness to the legacy list with a re-add recipe." \
  --breaking "Deploys that pass --target for the removed harness now fail." \
  --migration "Back up the deployed rules file, upgrade by dropping the target from saved commands, roll back by checking out the previous tag and redeploying."
```

The example is illustrative; use the real consequence. A breaking change cannot use `--no-impact`. Before a release, review the range from the previous tag: the lock keeps only the latest receipt per domain, so the release check fails until a breaking assessment made earlier in the range is carried into the final receipt.

## Releases

`develop` is the default and nightly branch and `main` is the stable channel. Feature and fix PRs squash into `develop`. A release is a PR from `develop` to `main` merged with a merge commit, never a squash, so every `develop` commit stays in `main`'s history and the next release PR carries only new work. After that merge, tag the commit on `main` as `v<version>` and push the tag. [CONTRIBUTING.md](../CONTRIBUTING.md#releases) has the steps and the version bump rule.

The release workflow fails when the tagged commit is not on `main`. It runs the guard on the tagged commit with `--base` set to the previous tag and `--release-tag`, which requires a dated `## [X.Y.Z] - YYYY-MM-DD` section in `CHANGELOG.md`. It publishes the release from that same tag. A green guard is not a release qualification: also run the full verification list and read the changelog, upgrade notes, and deployment instructions.

## Private context

CI runs the generic private-pattern checks (private IP addresses, home paths, and non-allowlisted email addresses) through `check_private_patterns` in `.github/stack/stack-check.py`. The custom marker list stays local by design: `python scripts/lint_prompts.py` reads `prompts/private-patterns.txt` and `AGENTS_PRIVATE_PATTERNS`, then checks tracked text files with case-insensitive matching. The marker example file is excluded from that custom scan.

The linter checks public prompts, role sources, `skills/**/SKILL.md`, text files under `templates/`, and `prompts/models.json` for token-like secrets and non-ASCII text. It also fails if Git tracks a private overlay or an editor copy. `.gitignore` covers overlay backup and swap names, including local and private Markdown suffix variants. `--check` renders validate outputs. The docs-impact guard does not read overlays. Keep private overlays out of tracked receipts and notes.

`python scripts/scan_prompt_sources.py` checks prompt sources and the non-Markdown render inputs `prompts/models.json` and `prompts/*.txt`. It detects hidden Unicode format characters, variation selectors, joining characters, and tag characters, and scans both individual lines and paragraphs with wrapped lines joined. Its network-to-shell rule covers shell and Python interpreters, sudo environment preservation, shell substitutions, and PowerShell pipelines. Commas and colons terminate negation clauses. A negation that removes a check instead of forbidding the command, such as "never ask before you run", does not exempt it. `*.md.example` templates are scanned as prompt sources, since users copy them into place. Directory and filename exclusions apply at the repository root; explicit local documentation subtrees remain excluded. Dependency trees (`node_modules`, virtualenvs, `__pycache__`) are skipped at any depth, and in a git checkout gitignored files are skipped too, except the overlays under `prompts/`, which are deployed and always scanned.

## Limits

The link check handles common inline links and GitHub heading anchors; it is not a full CommonMark renderer and skips remote links. The command check matches literal flags in a script and the Python module its wrapper runs, joins backslash continuations, and skips `prompts/` fragments and the changelog; it cannot follow dynamically built options. A cited doc counts as updated if it changed at all in the range, and re-accepting with an unchanged no-impact reason passes, so reviewers still read the diff. A lock-only PR that drops a breaking receipt from earlier in the release cycle passes its PR check and is caught by the release check. Root-level files and `.github/` are outside the domains. Fingerprints detect a review obligation, not correctness. The initial lock is an explicit baseline, not proof that every existing doc was verified; `--init` only creates a missing lock, and baseline receipts cannot replace an existing one. Changing the domain set or lock schema needs an explicit lock migration with tests.
