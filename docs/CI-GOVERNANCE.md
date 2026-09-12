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

`PASS`, `REVIEW`, and `FAIL` are surfaced in the Actions job summary, but semantic findings do not yet block merge. Invalid or missing judge output is reported as `INVALID` and also remains non-blocking during calibration.

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
    uses: Aya-DevOpsTeam/agent-governance/.github/workflows/agent-governance.yml@<immutable-governance-ref>
    secrets:
      governance_app_client_id: ${{ secrets.AGENT_GOVERNANCE_APP_CLIENT_ID }}
      governance_app_private_key: ${{ secrets.AGENT_GOVERNANCE_APP_PRIVATE_KEY }}
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

`COPILOT_GITHUB_TOKEN` is optional during the report-only rollout. When supplied, it is injected only into the Luna invocation step and Copilot CLI is explicitly told to authenticate from that environment variable. This reuses the same dedicated Copilot credential pattern already used by Aya agent-dispatch workflows without exposing that credential to checkout, Python, or governance-validation steps.

If the dedicated Copilot token is not supplied, the semantic job falls back to the short-lived Actions `GITHUB_TOKEN`; that fallback requires `copilot-requests: write`. GitHub currently recommends the built-in token for organization-owned automation because it is short-lived and organization-metered. A supplied personal Copilot token instead authenticates as its owning user and consumes that user's Copilot entitlements. Choose deliberately based on billing and credential-lifecycle policy.

The caller does not provide a second governance ref. The policy checkout uses the exact called-workflow identity, keeping workflow code, schemas, scripts, policies, and dependencies on one immutable governance commit.

The target `.agent/governance.yaml` must declare the policy version represented by that checkout.

## Runner and cost model

The central governance workflow and release guard run on the Aya-owned `aya-devops-rs` self-hosted runner instead of `ubuntu-latest`. This avoids GitHub-hosted Actions minute charges; Aya remains responsible for the underlying runner infrastructure. GitHub's current billing documentation states that self-hosted runner usage itself is free in GitHub Actions.

The reusable governance workflow selects its runner directly with `runs-on: aya-devops-rs`. A repository's `.github/workflows/copilot-setup-steps.yml` does **not** select the runner for this reusable CI workflow.

`copilot-setup-steps.yml` belongs to a different execution surface: GitHub Copilot cloud agent and Copilot code review. For cloud-agent sessions, Aya should prefer the organization-level Copilot Cloud agent runner setting when one runner policy applies broadly, and use repository `copilot-setup-steps.yml` for repository-specific dependency/environment preparation or an allowed runner override. `infrastructure-live` already uses `runs-on: aya-devops-rs` in its setup workflow.

Moving work to Aya-owned runners changes compute billing only. Copilot CLI model usage and premium-request/AI-credit accounting remain separate from GitHub Actions runner cost.

For Copilot cloud agent on self-hosted infrastructure, GitHub recommends ephemeral, single-use runners rather than long-lived shared runners. That recommendation should be treated as a security requirement for future production-scale cloud-agent rollout, particularly because cloud agents can execute repository code and access configured resources.

## Workflow runtime maintenance

The governance and release workflows use Node-24-generation GitHub actions:

- `actions/checkout@v5`;
- `actions/setup-python@v6`; and
- `actions/setup-node@v5` where the semantic job installs Copilot CLI on Node 24.

The GitHub App token action remains `actions/create-github-app-token@v3`.

## Promotion to blocking semantic governance

Semantic enforcement requires a separate R4 policy change after calibration. Before promotion, review real Aya PR results and the fixture corpus for false positives, false negatives, ambiguity handling, cost, and latency.

Deterministic gates remain blocking throughout. Semantic judgment must never be allowed to waive a deterministic failure.
