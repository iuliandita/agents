# Security Policy

## Supported Versions

Security fixes target `develop` and reach users through `main` and the next tagged release. The only long-lived branches are `develop` and `main`, so fixes are not backported to older releases.

## Reporting a Vulnerability

Report suspected vulnerabilities privately through
[GitHub private security reporting](https://github.com/iuliandita/agents/security/advisories/new)
(Security tab -> Report a vulnerability), or by email to iulian.dita@gmail.com. Do not open a public
issue for a security problem.

Include the affected file or script, a reproduction, and the impact.

## Scope

This repository ships prompt fragments, prompt-rendering scripts, a subagent renderer, the invariants
hook and Hermes config installers, the updater, and the consolidation skill with its installer. Relevant
issues include:

- a prompt or rendered output that can be used to exfiltrate secrets
- injection-scan bypasses
- unsafe deploy behavior, such as writing through symlinks or clobbering unrelated files
- consolidation steps that delete or clear files outside their backup manifest
- dependency vulnerabilities in the pinned tooling

## Updater Trust Model

The updater trusts the configured upstream of an allowed branch (`main` or `develop`, narrowed by
`AGENTS_UPDATE_BRANCHES`) and runs the scripts it pulls. It does not verify commit or tag signatures
yet. A compromised upstream can therefore execute code and change deployed prompts. With `--no-pull`,
the updater skips branch and upstream checks and trusts the checkout as it is.

## Not in Scope

- The behavior of third-party agent harnesses themselves.
- The contents of `prompts/local.md` and `prompts/private.md` after they are rendered and deployed; the
  overlays are local by design and are never committed. Which harnesses receive `private.md` is the
  user's trust list. Environment-selected prompt and Hermes config paths inside Git worktrees
  withhold both overlays; default global paths retain them even in dotfiles worktrees.

## Disclosure Expectations

Expect an acknowledgement within a few days; this is a personal project without a guaranteed response
time. Please give me reasonable time to validate the report and ship a fix before sharing details
publicly.
