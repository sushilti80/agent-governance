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

Cross-repository policy checkout uses a GitHub App token only when the governance repository is private and App secrets are supplied. Public policy checkouts use the caller token. Consumers do not copy central governance scripts.

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

`PASS`, `REVIEW`, and `FAIL` are surfaced in the Actions job summary, but semantic findings do not yet block merge. Invalid or missing judge output is reported as `INVALID` and also remains non-blocking during calibration.

The Copilot/Luna job is skipped on fork pull requests. Deterministic governance remains blocking on every pull request.

See `docs/SEMANTIC-GOVERNANCE.md`.

## Gate 4 — behavioral evaluation

The repository contains organization-wide behavioral evaluation **specifications** for review/read-only behavior, mutation/validation, scope adherence, delegation, learning isolation, stopping, and runtime efficiency.

Their presence and IDs are governed deterministically. Do not describe the current system as executing every global behavioral case against every changed consumer agent; that complete behavioral harness is a follow-on capability.

Changes under `evals/global/` are R4 because they change organization-wide behavioral expectations.

## Gate 5 — runtime efficiency

`runtime-efficiency-policy.yaml` and `runtime_audit.py` define/report measurable repetition, delegation, validation, and post-success defects when normalized runtime traces are supplied.

Runtime audit remains report-only and real cross-repository Copilot cloud-agent trace ingestion is not yet active. Runtime governance must not be presented as blocking until real telemetry is connected and calibrated.

## Gate 6 — ownership and change risk

Changes are risk-classified:

- **R0** documentation/comments;
- **R1** non-behavioral examples or reporting;
- **R2** skill procedure;
- **R3** agent behavior, authority, or tool access;
- **R4** global principles, schemas, global behavioral evals, governance versions, promotion policy, governance dependencies, scripts/tests, or governance CI.

R4 changes should receive the strongest platform-owner review.

## Calling the reusable workflow

Consumers pin one central immutable workflow reference:

```yaml
permissions:
  contents: read
  copilot-requests: write

jobs:
  agent-governance:
    uses: sushilti80/agent-governance/.github/workflows/agent-governance.yml@<immutable-governance-ref>
    with:
      semantic_model: gpt-5.6-luna
    secrets:
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

When the governance repository is private, also pass `governance_app_client_id` and `governance_app_private_key`. Those secrets are optional for a public policy repository because GitHub-hosted jobs can check out public policy without an App token.

`semantic_model` is optional and defaults to the currently governed `gpt-5.6-luna`. Set it to a lower-cost model identifier supported by Copilot CLI when desired; no workflow edit is required. Model changes should be calibrated against the semantic fixtures before becoming the new default.

`COPILOT_GITHUB_TOKEN` is optional during the report-only rollout. When supplied, it is injected only into the model invocation step. Copilot CLI authenticates from that environment variable. The secret is not exposed to checkout, Python, or governance-validation steps.

If the dedicated Copilot token is not supplied, the semantic job falls back to the short-lived Actions `GITHUB_TOKEN`; that fallback requires `copilot-requests: write`. GitHub currently recommends the built-in token for organization-owned automation because it is short-lived and organization-metered. A supplied personal Copilot token instead authenticates as its owning user and consumes that user's Copilot entitlements. Choose deliberately based on billing and credential-lifecycle policy.

The caller does not provide a second governance ref. The policy checkout uses the exact called-workflow identity, keeping workflow code, schemas, scripts, policies, and dependencies on one immutable governance commit.

The target `.agent/governance.yaml` must declare the policy version represented by that checkout.

## Runner and cost model

The central governance workflow and release guard run on GitHub-hosted `ubuntu-latest` runners. A repository's `.github/workflows/copilot-setup-steps.yml` does **not** select the runner for this reusable CI workflow.

`copilot-setup-steps.yml` belongs to a different execution surface: GitHub Copilot cloud agent and Copilot code review. Use it for repository-specific dependency or environment preparation, not to pin this reusable workflow's runner.

GitHub Actions compute cost is separate from Copilot CLI model usage and premium-request/AI-credit accounting.

## Workflow runtime maintenance

The governance and release workflows use Node-24-generation GitHub actions:

- `actions/checkout@v5`;
- `actions/setup-python@v6`; and
- `actions/setup-node@v5` where the semantic job installs Copilot CLI on Node 24.

The GitHub App token action remains `actions/create-github-app-token@v3`.

## Promotion to blocking semantic governance

Semantic enforcement requires a separate R4 policy change after calibration. Before promotion, review real PR results and the fixture corpus for false positives, false negatives, ambiguity handling, cost, and latency.

Deterministic gates remain blocking throughout. Semantic judgment must never be allowed to waive a deterministic failure.
