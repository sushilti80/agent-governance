# Aya Agent Governance

Central source of truth for the design, validation, evaluation, security testing, and controlled learning of Aya engineering agents.

For common operating questions, see [`docs/FAQ.md`](docs/FAQ.md).

## Core contract

1. **Agent = intent and authority.** Agents define mission, scope, evidence sources, mutation boundaries, success criteria, and escalation conditions.
2. **Skill = procedure.** Technology- or workflow-specific procedures belong in narrow skills rather than large agent prompts.
3. **Repository = truth.** Current repository evidence overrides examples, assumptions, and stale learned context.
4. **Evaluation = proof.** Agent behavior changes require representative evaluation; correctness, scope adherence, safety, and efficiency are all quality dimensions.
5. **Learning = proposal, not self-modification.** Runtime learning creates a candidate change. Promotion happens only through the governed SDLC.
6. **Minimum necessary instruction.** Add or retain prompt instructions only when evidence and evaluation justify them.
7. **One coherent contract.** Applicable repository, agent, skill, and delegated-task instructions must be mutually satisfiable and have clear behavioral ownership.
8. **Authority only narrows.** Effective authority is the intersection of governance, repository policy, agent authority, task scope, and approvals; lower layers cannot broaden it.
9. **Stop or escalate.** Stop after validated success; when evidence, authority, approval, or policy is insufficient, escalate rather than guessing or widening scope.

The machine-readable constitution is `principles/agent-design.yaml`. See `docs/AYA-AGENT-CONSTITUTION.md` for the stakeholder rationale and `docs/AGENT-DESIGN-PRINCIPLES.md` for implementation guidance.

## Governance layers

- **Deterministic governance — blocking:** schema, version, policy integrity, learning firewall, constitution integrity, source identity, regression checks.
- **Semantic governance — report-only:** GPT-6 Luna evaluates base-versus-candidate agent/skill/Copilot-instruction changes against AGP-001 through AGP-016.
- **Repository behavioral evals — Promptfoo report-only findings:** consumer-local `.agent/evals/*.yaml` cases execute against the declared agent contract when `validation.repository_evals: true`; provider/harness failures are blocking. Organization-wide `evals/global/` remains a governed catalog rather than an exhaustive per-agent fan-out.
- **Adversarial red-team governance — report-only findings:** Promptfoo runs a bounded Aya-owned security corpus against behavior-changing contracts; framework/provider failures remain blocking.
- **Runtime efficiency — report-only engine:** runtime enforcement is not active until real cloud-agent telemetry is connected and calibrated.

See `docs/SEMANTIC-GOVERNANCE.md`, `docs/REPOSITORY-EVALS.md`, `docs/REDTEAM-GOVERNANCE.md`, and `docs/CI-GOVERNANCE.md` for exact enforcement maturity.

## Version contract

The root `VERSION` file is the single authoritative governance release version. `spec_version` is a separate compatibility version for the manifest contract. Governed repositories must declare the exact policy version executed by CI, and published governance tags are immutable `v<VERSION>` releases.

See `docs/VERSIONING-AND-RELEASES.md` for compatibility and release rules.

## Repository layout

```text
VERSION                     Canonical governance release version
CHANGELOG.md                Release history
principles/                 Constitution and machine-readable governance policies
schemas/                    Contracts for manifests, agents, skills, learning, and semantic results
evals/global/               Organization-wide behavioral evaluation specifications
redteam/                    Bounded Promptfoo adversarial cases and configuration
scripts/                    Deterministic governance, semantic/red-team/repository-eval providers, and release checks
tests/                      Regression and calibration fixtures
docs/                       Design, semantic, red-team, learning, CI, release, and rollout guidance
examples/                   Schema-valid bootstrap examples
.github/workflows/          Reusable governance and release-guard workflows
```

## Adoption

Each governed repository contains `.agent/governance.yaml` declaring the governance specification version, exact policy version, agent/skill locations, learning mode, and evaluation requirements. Repositories may add local constraints and `.agent/evals/*.yaml` behavioral cases, but must not weaken organization invariants. Set `validation.repository_evals: true` only when a valid local eval catalog is present and should execute in PR governance.

The reusable workflow checks out the adopting repository and the governance policy into separate roots. Policy identity comes directly from `job.workflow_repository` + `job.workflow_sha`; callers provide one immutable governance reference in `uses:`.

Cross-repository policy checkout uses the organization-owned `agents-governance` GitHub App with a short-lived Contents: Read token. Semantic and red-team model evaluation use the caller workflow `GITHUB_TOKEN` with `copilot-requests: write`; no separate OpenAI API secret is required.

### Bootstrap a target repository with Copilot

Run Copilot from the root of the target repository and give it this prompt:

```text
Wire this repository to Aya central agent governance from Aya-DevOpsTeam/agent-governance.

First inspect the existing repository instructions, agents, skills, CI workflows, and any current `.agent/governance.yaml`. Preserve existing behavior and CI unless a change is required for governance adoption.

Use the latest approved immutable governance release/tag from the central repository, not `main`. Add or update `.agent/governance.yaml` with the correct profile and existing agent/skill paths, and add the reusable Agent Governance workflow using the central workflow at that same immutable release. Configure only the permissions/secrets required by the documented central workflow; do not copy central governance scripts, schemas, red-team cases, or policy files into this repository.

Validate the resulting YAML and workflow wiring, show the files changed and any required repository/org secrets or GitHub App prerequisites, and do not alter application/infrastructure code as part of governance onboarding.
```

Consumers remain on their pinned governance commit until deliberately upgraded.

See `docs/CI-GOVERNANCE.md`, `docs/ROLLOUT.md`, `docs/LEARNING-GOVERNANCE.md`, `docs/SEMANTIC-GOVERNANCE.md`, `docs/REPOSITORY-EVALS.md`, and `docs/REDTEAM-GOVERNANCE.md`.