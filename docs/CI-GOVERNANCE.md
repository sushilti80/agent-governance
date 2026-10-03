# CI Governance

Governance uses layered gates so deterministic failures cannot be waived by a semantic reviewer. The central workflow is the implementation source of truth; this document distinguishes controls that are active from controls that are still being calibrated.

## Gate 1 — deterministic structural governance

The blocking deterministic job validates:

- JSON Schema definitions and governed YAML instances;
- the adopting repository `.agent/governance.yaml`;
- exact policy version consistency with the checked-out governance `VERSION`;
- `spec_version` compatibility;
- the learning `propose-only` firewall;
- the AGP-001 through AGP-016 constitution;
- global evaluation catalog integrity;
- release/changelog consistency;
- exact called-workflow policy identity; and
- governance regression tests and Python compilation.

An objective violation such as `learning.mode: self-promote`, malformed policy YAML, version drift, or a missing required constitutional principle fails CI without model judgment.

The reusable workflow checks out two roots separately:

- **target root** — the caller/adopting repository;
- **policy root** — the exact repository and commit SHA defining the called governance job, derived from `job.workflow_repository` and `job.workflow_sha`.

Cross-repository policy checkout uses the organization-owned `agents-governance` GitHub App only for a short-lived read-only policy token. Consumers do not copy central governance scripts.

## Gate 2 — deterministic design lint

Prompt discovery is restricted to `.github/copilot-instructions.md` plus the agent and skill locations declared by the governance manifest. Existing deterministic lint remains intentionally small and heuristic. It does not attempt to encode every semantic defect as regex.

Warnings such as generic thoroughness or unbounded persistence remain advisory unless they correspond to an objective invariant that can be enforced deterministically.

## Gate 3 — semantic constitutional review

Release `2026.09.3` adds a GPT-5.6 Luna semantic judge through GitHub Copilot CLI.

The semantic job runs only for behavior-affecting prompt surfaces identified by change classification. It deterministically builds a bounded **base versus candidate effective-contract** bundle and evaluates the change against every AGP-001 through AGP-016 principle.

The judge specifically evaluates:

- outcome and success criteria;
- duplicate or competing behavioral ownership;
- repository truth and evidence use;
- unnecessary persistent instruction;
- authority and scope expansion;
- deterministic versus agentic responsibility;
- post-mutation validation;
- delegation bounds and authority inheritance;
- learning isolation;
- internal and cross-layer contradiction; and
- stopping and escalation behavior.

Repository content is untrusted evidence. Copilot CLI runs outside the target repository with custom instructions disabled, built-in MCP disabled, and read/shell/write/URL/memory tools denied.

The result must conform to `schemas/semantic-judge-result.schema.json` and is machine-validated.

### Current enforcement state

Semantic governance is **report-only**.

`PASS`, `REVIEW`, and `FAIL` are surfaced in the Actions job summary, but semantic findings do not yet block merge. Invalid or missing judge output remains a blocking harness/result-contract failure.

See `docs/SEMANTIC-GOVERNANCE.md`.

## Gate 4 — behavioral evaluation

Governance supports two behavioral-eval layers:

1. **Consumer-local repository evals.** When a target repository sets `validation.repository_evals: true`, Promptfoo executes its schema-valid `.agent/evals/*.yaml` cases against the named agent contract. The Luna provider receives the scenario and observable field names but not expected values. Promptfoo owns the deterministic expected-value assertions.
2. **Organization-wide global evals.** `evals/global/` remains the governed organization catalog for shared behavior such as review/read-only operation, scope, delegation, learning isolation, stopping, and runtime efficiency. CI does not yet fan every global case out against every changed consumer agent.

Repository-eval assertion findings are **report-only during calibration**. Invalid catalogs, unknown agent references, missing cases when execution is enabled, provider failures, malformed outputs, and Promptfoo/framework errors are blocking.

A behavior-affecting agent/skill/instruction change runs the local repository catalog when enabled. A change under `.agent/evals/` also triggers the repository-eval lane. Central repository-eval harness changes run a synthetic end-to-end smoke.

Changes under `evals/global/` are R4 because they change organization-wide behavioral expectations. Central repository-eval schema/runner/provider/workflow changes are also R4.

See `docs/REPOSITORY-EVALS.md`.

## Gate 5 — adversarial red-team evaluation

Promptfoo runs a bounded organization-owned adversarial corpus for behavior-affecting contracts and for changes to the central red-team contract.

Assertion findings are **report-only during calibration**. Promptfoo/provider/framework errors remain blocking. The workflow reads Promptfoo result statistics directly so provider errors cannot be collapsed into ordinary findings.

See `docs/REDTEAM-GOVERNANCE.md`.

## Gate 6 — runtime efficiency

`runtime-efficiency-policy.yaml` and `runtime_audit.py` define/report measurable repetition, delegation, validation, and post-success defects when normalized runtime traces are supplied.

Runtime audit remains report-only and real cross-repository Copilot cloud-agent trace ingestion is not yet active. Runtime governance must not be presented as blocking until real telemetry is connected and calibrated.

## Gate 7 — ownership and change risk

Changes are risk-classified:

- **R0** documentation/comments;
- **R1** non-behavioral examples or reporting;
- **R2** skill procedure;
- **R3** agent behavior, authority, or tool access;
- **R4** global principles, schemas, global behavioral evals, governance versions, promotion policy, governance dependencies, scripts/tests, or governance CI.

R4 changes should receive the strongest platform-owner review.

## Pull-request reporting

Release `2026.09.9` adds a final `pr-governance-report` aggregation job for pull-request events. It publishes one marker-based comment and updates that comment in place on subsequent runs.

The comment is deliberately bounded and machine-derived. Full semantic rationale, evidence excerpts, Promptfoo output, and raw logs remain in Actions.

The top-level report states are:

- **PASS** — blocking controls passed and no report-only findings were detected;
- **ATTENTION** — blocking controls passed, but semantic, red-team, or repository-eval report-only findings need review;
- **BLOCKED** — deterministic/classification failure, invalid semantic result, repository-eval/red-team Promptfoo provider or harness failure, or another blocking reporting prerequisite failed.

Before updating the comment, the workflow verifies that the current PR head still matches the evaluated SHA. It updates only a marker-bearing comment owned by `github-actions[bot]`. Fork pull requests retain the Actions summary but skip the write operation.

See `docs/PR-GOVERNANCE-REPORTING.md`.

## Calling the reusable workflow

Consumers pin one central immutable workflow reference:

```yaml
permissions:
  contents: read
  pull-requests: write
  copilot-requests: write

jobs:
  agent-governance:
    uses: Aya-DevOpsTeam/agent-governance/.github/workflows/agent-governance.yml@<immutable-governance-ref>
    secrets:
      governance_app_client_id: ${{ secrets.AGENT_GOVERNANCE_APP_CLIENT_ID }}
      governance_app_private_key: ${{ secrets.AGENT_GOVERNANCE_APP_PRIVATE_KEY }}
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

`contents: read` supports repository checkout. `copilot-requests: write` supports semantic and red-team Copilot CLI evaluation. `pull-requests: write` allows only the final reporting job to verify the current head SHA and create/update the sticky PR conversation comment. Job-level permissions in the reusable workflow remain narrower, so deterministic/classification/model-evaluation jobs do not receive PR-write access.

`COPILOT_GITHUB_TOKEN` is optional during the report-only rollout. When supplied, it is injected only into the Luna invocation step and Copilot CLI is explicitly told to authenticate from that environment variable. This reuses the same dedicated Copilot credential pattern already used by Aya agent-dispatch workflows without exposing that credential to checkout, Python, or governance-validation steps.

If the dedicated Copilot token is not supplied, the semantic/red-team jobs fall back to the short-lived Actions `GITHUB_TOKEN`; that fallback requires `copilot-requests: write`. A supplied personal Copilot token instead authenticates as its owning user and consumes that user's Copilot entitlements. Choose deliberately based on billing and credential-lifecycle policy.

The caller does not provide a second governance ref. The policy checkout uses the exact called-workflow identity, keeping workflow code, schemas, scripts, policies, and dependencies on one immutable governance commit.

The target `.agent/governance.yaml` must declare the policy version represented by that checkout.

## Runner and cost model

The central governance workflow and release guard run on the Aya-owned `aya-devops-rs` self-hosted runner instead of `ubuntu-latest`. This avoids GitHub-hosted Actions minute charges; Aya remains responsible for the underlying runner infrastructure.

The reusable governance workflow selects its runner directly with `runs-on: aya-devops-rs`. A repository's `.github/workflows/copilot-setup-steps.yml` does **not** select the runner for this reusable CI workflow.

`copilot-setup-steps.yml` belongs to a different execution surface: GitHub Copilot cloud agent and Copilot code review. For cloud-agent sessions, Aya should prefer the organization-level Copilot Cloud agent runner setting when one runner policy applies broadly, and use repository `copilot-setup-steps.yml` for repository-specific dependency/environment preparation or an allowed runner override. `infrastructure-live` already uses `runs-on: aya-devops-rs` in its setup workflow.

Moving work to Aya-owned runners changes compute billing only. Copilot CLI model usage and premium-request/AI-credit accounting remain separate from GitHub Actions runner cost.

For Copilot cloud agent on self-hosted infrastructure, ephemeral, single-use runners should be preferred over long-lived shared runners, particularly because cloud agents can execute repository code and access configured resources.

## Workflow runtime maintenance

The governance and release workflows use Node-24-generation GitHub actions:

- `actions/checkout@v5`;
- `actions/setup-python@v6`; and
- `actions/setup-node@v5` where model-evaluation jobs install Copilot CLI on Node 24.

The GitHub App token action remains `actions/create-github-app-token@v3`.

## Promotion to blocking semantic governance

Semantic enforcement requires a separate R4 policy change after calibration. Before promotion, review real Aya PR results and the fixture corpus for false positives, false negatives, ambiguity handling, cost, and latency.

Deterministic gates remain blocking throughout. Semantic judgment must never be allowed to waive a deterministic failure.
