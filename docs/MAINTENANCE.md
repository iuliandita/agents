# Keeping documentation current

Documentation is part of a change. A new flag needs usage docs, a changed target path or removed harness needs upgrade and rollback steps, and an overlay change needs its trust rules restated. The docs-impact guard flags those obligations. It cannot tell whether the prose is right, so review the affected behavior and say in the PR what you checked.

## Run the check

```bash
python scripts/check_docs_impact.py
python scripts/check_docs_impact.py --explain
python scripts/check_docs_impact.py --base "$(git merge-base origin/main HEAD)"
```

The plain check verifies that every domain's receipt matches its current sources, that every tracked file under `agents/`, `prompts/`, `scripts/`, `skills/`, and `templates/` belongs to exactly one domain, that local Markdown links and anchors resolve to tracked files, and that script commands in the docs name tracked scripts and flags those scripts define. Changelog entries are history, so the command check skips them; their links are still checked.

`--base` adds the range checks: docs a receipt cites must change in the range, a breaking receipt recorded earlier in the range cannot be replaced by a `breaking: none` one, and removing a harness from `scripts/render_prompts.py` needs a breaking receipt that cites `docs/legacy-harnesses.md`. CI runs it against the PR base with full history. Exit codes: 0 pass, 1 findings, 2 missing tooling or invalid usage. The check needs Git and Python 3.11 and runs offline.

## Domains

`scripts/check_docs_impact.py` defines the domains in `DOMAINS`; `--explain` prints each domain's files and allowed docs.

| Domain | Covers | Docs it can cite |
|---|---|---|
| prompts | core prompt, invariants, harness fragments | README, INSTALL, surfaces, CHANGELOG |
| models-agents | role sources, model tiers, agent renderer | README, INSTALL, harness contract, CHANGELOG |
| harnesses | harness registry and the prompt launcher | README, INSTALL, harness contract, surfaces, legacy harnesses, CHANGELOG |
| deployment | update, invariants, Hermes, runtime, workflow installer | README, INSTALL, SECURITY, CHANGELOG |
| overlays-trust | overlay templates, leak lint, source scan, `.gitignore` | README, INSTALL, SECURITY, CHANGELOG |
| workflow-templates | `skills/` and `templates/` | README, INSTALL, CHANGELOG |
| maintenance | `scripts/check_*.py` | this file, README, CHANGELOG |

`.github/`, `tests/`, and docs are outside the domains. Action pins have Dependabot and actionlint, tests are not user facing, and docs are the obligation itself. New source files count once staged; untracked scratch files are ignored. Change sources and rerun the renderers; never hand-edit rendered output.

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

The release workflow runs the guard on the tagged commit with `--base` set to the previous tag and `--release-tag`, which requires a dated `## [X.Y.Z] - YYYY-MM-DD` section in `CHANGELOG.md`. It publishes the release from that same tag. A green guard is not a release qualification: also run the full verification list and read the changelog, upgrade notes, and deployment instructions.

## Private context

`python scripts/lint_prompts.py` already fails when a local leak marker from `prompts/private-patterns.txt` appears in any tracked file, and `--check` renders validate the outputs. The guard does not read overlays. Keep private overlays out of receipts and notes; they are tracked.

## Limits

The link check handles common inline links and GitHub heading anchors; it is not a full CommonMark renderer and skips remote links. The command check matches literal flags in a script and the Python module its wrapper runs; it cannot follow dynamically built options. Fingerprints detect a review obligation, not correctness. The initial lock is an explicit baseline, not proof that every existing doc was verified; `--init` only creates a missing lock, and baseline receipts cannot replace an existing one. Changing the domain set or lock schema needs an explicit lock migration with tests.
