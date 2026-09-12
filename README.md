# Aya Agent Governance

Central source of truth for the design, validation, evaluation, and controlled learning of Aya engineering agents.

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
- **Semantic governance — report-only:** GPT-5.6 Luna evaluates base-versus-candidate agent/skill/Copilot-instruction changes against AGP-001 through AGP-016.
- **Behavioral eval specifications — governed catalog:** current CI protects the specifications but does not yet execute every case against every changed consumer agent.
- **Runtime efficiency — report-only engine:** runtime enforcement is not active until real cloud-agent telemetry is connected and calibrated.

See `docs/SEMANTIC-GOVERNANCE.md` and `docs/CI-GOVERNANCE.md` for exact enforcement maturity.

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
scripts/                    Deterministic governance, semantic context/result, and release checks
tests/                      Regression and calibration fixtures
docs/                       Design, semantic, learning, CI, release, and rollout guidance
examples/                   Schema-valid bootstrap examples
.github/workflows/          Reusable governance and release-guard workflows
```

## Adoption

Each governed repository contains `.agent/governance.yaml` declaring the governance specification version, exact policy version, agent/skill locations, learning mode, and evaluation requirements. Repositories may add local constraints and evals, but must not weaken organization invariants.

The reusable workflow checks out the adopting repository and the governance policy into separate roots. Policy identity comes directly from `job.workflow_repository` + `job.workflow_sha`; callers provide one immutable governance reference in `uses:`.

Cross-repository policy checkout uses the organization-owned `agents-governance` GitHub App with a short-lived Contents: Read token. Semantic review uses the caller workflow `GITHUB_TOKEN` with `copilot-requests: write`; no separate OpenAI API secret is required.

Consumers remain on their pinned governance commit until deliberately upgraded.

See `docs/CI-GOVERNANCE.md`, `docs/ROLLOUT.md`, `docs/LEARNING-GOVERNANCE.md`, and `docs/SEMANTIC-GOVERNANCE.md`.
