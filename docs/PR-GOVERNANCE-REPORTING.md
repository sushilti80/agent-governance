# Pull Request Governance Reporting

Aya Agent Governance publishes one bounded, sticky pull-request comment as the primary human-facing summary while retaining full evidence in GitHub Actions.

## Status model

The PR report uses three top-level states:

- **PASS** — blocking controls passed and no report-only semantic, repository-eval, or adversarial findings were detected.
- **ATTENTION** — blocking controls passed, but semantic, repository-eval, or red-team report-only findings need human review.
- **BLOCKED** — a blocking deterministic, classification, semantic judge/result-contract, repository-eval/red-team Promptfoo provider/harness, or reporting prerequisite failed.

A semantic `FAIL` remains report-only during calibration, so it produces `ATTENTION`, not `BLOCKED`. A malformed/missing semantic result is a harness/result-contract failure and produces `BLOCKED`. Promptfoo assertion findings likewise produce `ATTENTION`; provider/framework errors produce `BLOCKED`.

## Report contents

The sticky comment intentionally contains only bounded machine-derived metadata:

- evaluated commit SHA;
- highest change-risk class;
- deterministic and classification job outcomes;
- semantic verdict, reviewer action, and finding count when required;
- red-team outcome and pass/finding/error counts when required; and
- a link to the detailed Actions run.

Full model-generated rationale, evidence excerpts, raw Promptfoo output, and logs stay in GitHub Actions. Repository-derived text is not copied into the PR comment.

The marker `<!-- aya-agent-governance-report -->` identifies the report. The workflow updates an existing comment only when it was created by `github-actions[bot]`; otherwise it creates a new report comment.

Before publishing, the workflow verifies that the PR head SHA still matches the evaluated SHA so an older run cannot overwrite a newer report.

## Permissions

Consumer workflows adopting a release with PR reporting must grant the reusable workflow the permissions it needs:

```yaml
permissions:
  contents: read
  pull-requests: write
  copilot-requests: write
```

`pull-requests: write` is used only by the final `pr-governance-report` job. It covers reading the current PR head and creating/updating the sticky PR conversation comment. Deterministic, classification, semantic, and red-team jobs keep narrower job-level permissions and do not receive PR-write access.

Fork pull requests do not receive a sticky comment because their token context may not safely provide write permission. Their governance result remains available in Actions summaries and logs.

## Idempotency

The workflow publishes one marker-based comment per pull request. Subsequent governance runs update that comment in place rather than adding a new comment for each push.

## Enforcement

The PR comment is a reporting surface; it does not independently change merge enforcement. Blocking behavior remains owned by the underlying governance jobs and repository branch/ruleset configuration.
