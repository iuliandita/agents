# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub Security Advisories for this repository
(Security tab -> Report a vulnerability), or by email to iulian.dita@gmail.com. Do not open a public
issue for a security problem.

Include the affected file or script, a reproduction, and the impact. Expect an acknowledgement within
a few days; this is a personal project without a guaranteed response time.

## Scope

This repository ships prompt fragments, prompt-rendering scripts, and a subagent renderer. Relevant
issues include a prompt or rendered output that can be used to exfiltrate secrets, injection-scan
bypasses, unsafe deploy behavior (writing through symlinks, clobbering unrelated files), and
dependency vulnerabilities in the pinned tooling.

## Not in scope

- The behavior of third-party agent harnesses themselves.
- The contents of `prompts/private.md` after it is rendered and deployed; the overlay is local by
  design and is never committed.
