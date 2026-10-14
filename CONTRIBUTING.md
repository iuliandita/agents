# Contributing

Open an issue before starting a bug fix or a substantial change, and reference it in the PR
(`Closes #NN` for a completed fix). Keep changes small and preserve unrelated local settings.
Report suspected vulnerabilities through [SECURITY.md](SECURITY.md), not a public issue.

## Sources and generated files

Edit `prompts/`, `agents/`, and `templates/` sources. Rendered `build/` files are outputs,
not source. Keep local/private overlays and generated output out of commits. Do not deploy
into a contributor's global configuration as part of a test.

## Checks and documentation

Run the verification commands in [README.md](README.md#verification), including pytest,
render checks, syntax checks, prompt lint, source scan, harness receipts, docs-impact, and
local documentation links. CI additionally exercises macOS and Windows launchers.
Use [maintenance guidance](docs/MAINTENANCE.md) for docs-impact receipts and exclusions:
`.github/`, tests, and docs are outside receipt domains. Review compatibility, installation,
update and recovery instructions when paths, flags, overlays, or supported harnesses change.
`render-agents --verify` checks role-file existence only; it does not validate model behavior.
