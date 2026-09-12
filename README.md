# Agent Governance

Central source of truth for the design, validation, evaluation, and controlled learning of engineering agents.

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

The machine-readable constitution is `principles/agent-design.yaml`. See `docs/AGENT-CONSTITUTION.md` for the stakeholder rationale and `docs/AGENT-DESIGN-PRINCIPLES.md` for implementation guidance.

## Governance layers

- **Deterministic governance — blocking:** schema, version, policy integrity, learning firewall, constitution integrity, source identity, regression checks.
- **Semantic governance — report-only:** GPT-5.6 Luna evaluates base-versus-candidate agent/skill/Copilot-instruction changes against AGP-001 through AGP-016.
- **Behavioral eval specifications — governed catalog:** current CI protects the specifications but does not yet execute every case against every changed consumer agent.
- **Runtime efficiency — report-only engine:** runtime enforcement is not active until real cloud-agent telemetry is connected and calibrated.

See `docs/SEMANTIC-GOVERNANCE.md` and `docs/CI-GOVERNANCE.md` for exact enforcement maturity.

## Version contract

The root `VERSION` file is the single authoritative governance release version. `spec_version` is a separate compatibility version for the manifest contract. Governed repositories must declare the exact policy version executed by CI, and published governance tags are immutable `v<VERSION>` releases.

See `docs/VERSIONING-AND-RELEASES.md` for compatibility and release rules.

## Use in your repository

An organization that wants to **own** policy should fork or mirror this repository **once** into their org, release their own immutable tags, and point every product repo at that copy. Product repos should not clone or vendor the policy; they only pin the reusable workflow.

Paste this prompt in a consumer/product repo (`OWNER/agent-governance` is this public repo or your org’s policy fork; keep the version and tag in lockstep):

> Wire Agent Governance: add `.agent/governance.yaml` with `policy: agent-governance`, `version: "2026.09.8"`, `spec_version: 1`, `learning.mode: propose-only`, `validation.global_evals: true`, and `agents.path` / `skills.path` pointing at `.github/agents` and `.github/skills`; add a caller workflow that `uses: OWNER/agent-governance/.github/workflows/agent-governance.yml@v2026.09.8` with `permissions: contents: read` and `copilot-requests: write`. Keep Copilot agents and skills in those GitHub paths; pin the same immutable tag/SHA until you upgrade; do not copy scripts or schemas into this product repo.

If the policy repository is private, also pass the `agents-governance` GitHub App secrets. Details: `docs/CI-GOVERNANCE.md`, `docs/ROLLOUT.md`, `examples/.agent/governance.yaml`.

## License

This repository is licensed under the [MIT License](LICENSE).

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for local checks, CODEOWNERS review, fork CI, and how to send feedback.

See [SECURITY.md](SECURITY.md) to report vulnerabilities privately. Do not file public issues for security-sensitive findings. Maintainer: [@sushilti80](https://github.com/sushilti80).

Semantic Copilot/Luna review requires Copilot access and is skipped on fork pull requests. Deterministic governance remains blocking. Semantic verdicts are report-only until a later explicit promotion.
