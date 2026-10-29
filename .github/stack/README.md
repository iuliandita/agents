# Stack conventions checker

This directory holds the shared conventions for the agents, skills, mods, and idstack repositories and an offline checker for them. This repository is the source of truth; the other three vendor copies.

| File | Role | Vendored |
|---|---|---|
| `canon.json` | Shared rules as data: README layout, stack lines, assets, CONTRIBUTING headings, workflow rules, error format, patterns. | yes |
| `stack-check.py` | The checker. Python 3.11+, standard library only, no network. | yes |
| `repo.json` | Per-repository settings: repo name, required CI job ids, installer help commands, paths to scan for error strings, allowlist. | no |
| `SOURCE` | Records the source commit and the sha256 of each vendored file. Absent in this repository. | no |

## Run

```sh
python3 .github/stack/stack-check.py
python3 .github/stack/stack-check.py --json
python3 .github/stack/stack-check.py --list-checks
python3 .github/stack/stack-check.py --only readme-title,assets
```

Run it from the repository root. Findings print to stderr, one per line, as `error: <check>: <file>[:line]: <why>; <fix>`. With `--json` the checker prints one object to stdout: `ok`, `errors` (the same lines), `findings` (check, file, line, message, fix), `checks`, and `repo`. Exit codes: 0 no findings, 1 findings, 2 usage error or invalid `canon.json` or `repo.json`, 3 git missing in a git checkout.

## What is checked

- README: first heading is the repo name, the wordmark is referenced near the top, the opening paragraph is 110-350 characters with no bold and no version number, a `Status:` line names `main` and `develop`, the `##` sections appear in the canonical order, and `Part of the stack` and `Project and support` match the canon.
- Assets: `assets/logo.png`, `assets/logo-256.png`, and `assets/wordmark.png` exist, and the two logos have the canonical pixel sizes.
- CONTRIBUTING: the shared opening paragraph, the three `##` headings in order, a `sh` block first under `Checks and documentation`, and `develop`, `main`, and `Unreleased` in `Releases`.
- Workflows (line-based, no YAML parser): the required job ids exist and are named after their id, every `uses:` is pinned to a 40-hex SHA with a `# v` comment, every job has `timeout-minutes`, and every checkout step sets `persist-credentials: false`.
- Installer help: each command in `repo.json` exits 0 on `--help`, lists its declared flags, and has `Environment` and `Exit codes` sections.
- Error strings: no upper-case `ERROR:`, and no `SystemExit("...")` or `sys.exit("...")` with a string literal that lacks an `error:`, `warning:`, or `note:` prefix, in the paths named in `repo.json`.
- Text: tracked Markdown files are ASCII, and no tracked text file holds a home-directory path, a private IPv4 address, or an e-mail address outside the allowed identifiers.
- Vendoring: when `SOURCE` exists, the vendored files match their recorded sha256.

## What is not checked

- Whether prose is accurate, concise, or in the house voice.
- Whether linked URLs resolve, or whether install pins such as `--ref main` work.
- Workflow semantics beyond the rules above: triggers, permissions, concurrency, and the content of steps.
- Error strings that are built at run time, or printed by other means than `SystemExit` and `sys.exit`.
- Binary files, and files that are neither tracked nor untracked-and-not-ignored.
- Anything in the allowlist. Every allowlist entry in `repo.json` needs a reason, and an entry that matches nothing is reported as stale.

## Vendor into another repository

1. Copy `canon.json` and `stack-check.py` unchanged into `.github/stack/` of the other repository.
2. Write that repository's own `.github/stack/repo.json`.
3. Generate `SOURCE` from the commit of this repository you copied from:

   ```sh
   python3 .github/stack/stack-check.py --print-source <40-hex commit> > .github/stack/SOURCE
   ```

4. Run `python3 .github/stack/stack-check.py` in CI.

To update, copy both files again from a newer commit of this repository and regenerate `SOURCE`. Do not edit a vendored file: the checker reports any file whose sha256 differs from `SOURCE`. Change the canon here, then re-vendor.
