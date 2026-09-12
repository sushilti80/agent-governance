# Security Policy

Maintainer: [@sushilti80](https://github.com/sushilti80)

## Reporting a vulnerability

Use GitHub **private vulnerability reporting**. Do not open a public issue, pull request, or discussion for security-sensitive findings.

https://github.com/sushilti80/agent-governance/security/advisories/new

Include:

- a description of the issue and impact;
- affected files, workflows, schemas, or scripts;
- reproduction steps or a minimized proof;
- whether credentials, production identifiers, or runtime transcripts are involved.

Please do not attach live secrets. Redact tokens, keys, and private logs.

If private reporting is not yet enabled on the repository, email is not published as a fallback. Wait until the advisory form is available, or contact [@sushilti80](https://github.com/sushilti80) without posting exploit details in public.

### Maintainer setup

GitHub → **Settings** → **Code security** → enable **Private vulnerability reporting** (and Dependabot alerts if you want dependency scanning). The advisory URL above only works after that setting is on.

## Governance-sensitive changes

Treat these as high-risk even when they are not classic CVEs:

- broadening mutation, external-action, or credential authority;
- policy bypass, self-promotion of learning, or weakening the propose-only firewall;
- copying untrusted repository content into judge instructions or CI secrets;
- encoding secrets, production identifiers, or sensitive runtime transcripts in prompts, eval fixtures, or LearningRecords.

Those changes need explicit review from [@sushilti80](https://github.com/sushilti80) before merge.

## Supported versions

Only the latest tagged governance release (`v` plus the root `VERSION` file, currently `2026.09.8`) is supported. Pin consumers to an immutable tag or commit SHA. Older pins receive fixes only by upgrading.

## CI note

Deterministic governance is blocking. Semantic Copilot/Luna review is report-only, skipped on fork pull requests, and must not waive a deterministic failure.
