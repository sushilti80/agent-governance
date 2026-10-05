# Aya Agent Governance FAQ

This FAQ answers common implementation and operating questions about Aya Agent Governance. It is explanatory guidance, not a replacement for the machine-readable policies, schemas, or CI workflows. When there is a conflict, the checked-out governance policy and workflow are authoritative.

## General architecture

### What problem does `agent-governance` solve?

It provides one central source of truth for how Aya engineering agents are designed, validated, evaluated, security-tested, versioned, and allowed to learn. The goal is to keep repository agents useful and autonomous without allowing prompt content, runtime learning, or lower-level instructions to silently widen authority.

### What belongs in an agent versus a skill?

An agent owns intent and authority: mission, scope, evidence sources, mutation boundaries, success criteria, delegation boundaries, stopping, and escalation. A skill owns reusable procedure or technology-specific execution knowledge. If a rule describes *what the agent is allowed to do*, it generally belongs in the agent or repository policy. If it describes *how to perform a repeatable task*, it generally belongs in a skill.

### What is the authority model?

Authority only narrows. Effective authority is the intersection of governance, repository policy, agent authority, task scope, and explicit approvals. A ticket, README, skill, delegated task, or lower-level instruction cannot widen that authority.

### What wins when instructions conflict?

Repository truth and higher-level governance take precedence over examples, assumptions, stale learned context, and untrusted task or repository content. When authority or evidence is insufficient, the agent should stop or escalate instead of guessing or widening scope.

## CI and enforcement

### What governance checks run in CI?

The reusable workflow uses layered controls:

- deterministic structural governance — blocking;
- deterministic design lint — primarily advisory unless it maps to an objective invariant;
- semantic constitutional review with GPT-5.6 Luna — report-only during calibration;
- repository behavioral evals — Promptfoo executes consumer-local `.agent/evals/*.yaml` cases when `validation.repository_evals: true`; findings are report-only during calibration and provider/harness errors are blocking; organization-wide global evals remain a governed catalog rather than an exhaustive per-agent run;
- adversarial red-team governance with Promptfoo — findings report-only during calibration, harness/provider failures blocking;
- runtime-efficiency analysis — report-only when trace data is available.

### What is always blocking today?

Objective deterministic failures remain blocking. Examples include malformed governed YAML, manifest/schema violations, policy-version drift, an invalid learning mode such as self-promotion, broken constitutional requirements, failed regression tests, or a broken governance test harness.

### Does semantic review block a pull request?

Not yet. Semantic review is report-only while Aya calibrates false positives, false negatives, cost, latency, and ambiguity handling. Its findings cannot waive a deterministic failure.

### What do R0 through R4 mean?

They describe governance-change risk, not application severity:

- **R0** — documentation/comments;
- **R1** — non-behavioral examples or reporting;
- **R2** — skill procedure;
- **R3** — agent behavior, authority, or tool access;
- **R4** — organization-wide principles, schemas, global evals, versions, dependencies, scripts/tests, governance CI, or other central policy-contract changes.

R4 changes should receive the strongest platform-owner review.

## Semantic review

### When does semantic governance run?

It runs only when the pull request changes a behavior-affecting prompt surface, such as repository Copilot instructions, agents, skills, agent instructions/prompts, or governed agent-memory content. It builds a bounded base-versus-candidate effective-contract context and evaluates the behavioral change against the Aya Agent Governance principles.

### Does semantic review evaluate every agent in the repository?

No. It evaluates the changed behavioral contract represented by the pull request. Unchanged agents are not automatically re-evaluated simply because they exist in the repository.

### What does the semantic judge look for?

It reviews issues such as scope expansion, duplicated or conflicting behavioral ownership, insufficient validation, weak stopping conditions, unsafe delegation, learning isolation violations, repository-truth problems, and contradictions across instruction layers.

## Repository behavioral evals

### When do repository behavioral evals run?

They run when the target manifest sets `validation.repository_evals: true` and either a behavior-affecting agent/skill/instruction surface changes or the repository-local eval catalog changes. Changes to the central repository-eval harness also run a synthetic end-to-end smoke case.

### What does Promptfoo evaluate?

Each `.agent/evals/*.yaml` case names one declared agent, gives a scenario, and lists observable boolean expectations. Governance resolves that agent's contract, repository Copilot instructions, and skills explicitly referenced by the agent. GPT-5.6 Luna simulates the agent with tools disabled.

The deterministic builder assembles the bounded effective contract first. The provider then receives the contract text, scenario, and observable field names but **not** the expected true/false values. The provider does not resolve repository paths or read repository files. It reports each observable as `YES`, `NO`, or `UNSPECIFIED`, and Promptfoo independently compares those outputs with the expected values stored in the generated assertion.

### Why use UNSPECIFIED?

A simulator should not invent missing behavior. If the effective agent contract does not determine an observable, `UNSPECIFIED` causes the corresponding expected boolean assertion to fail. This exposes missing behavioral contracts instead of letting the model fill gaps from evaluator intent.

### Do repository eval findings block merge?

Not during initial calibration. Assertion failures are report-only and produce `ATTENTION`. Invalid eval YAML, unknown agent references, missing required catalogs when `repository_evals: true`, provider failures, malformed model output, Promptfoo/framework errors, or other harness failures remain blocking.

### Are repository evals the same as red teaming?

No. Repository evals encode expected product/repository agent behavior such as handoff gates, role boundaries, and stop conditions. Red-team cases are organization-owned adversarial security scenarios. Both use Promptfoo and a tool-disabled Luna simulator, but they have separate schemas, case ownership, and result lanes.

## Red teaming

### When does the Promptfoo red-team suite run?

It runs when either:

1. the pull request changes a behavior-affecting agent contract (`semantic_review_required=true`); or
2. the central `agent-governance` repository changes the red-team contract itself (`redteam_contract_changed=true`).

Typical behavior-affecting surfaces include `.github/copilot-instructions.md`, agent files, skill `SKILL.md` files, `.github/instructions/**`, `.github/prompts/**`, and governed agent-memory content.

### Will the red-team suite run for ordinary Terraform, application code, or documentation changes?

No, not by default. A pull request that changes only non-agent application/infrastructure code or ordinary documentation does not require the semantic/red-team path.

### Does red teaming test every agent in a repository?

No. The current PR-CI design tests the bounded candidate behavioral contract built from the changed agent/skill/instruction content. If several behavioral components change in one pull request, they may be represented together in the candidate context. It is not currently a per-agent fan-out that runs the full corpus independently against every agent in the repository.

### What attacks are in the current red-team corpus?

The initial bounded corpus covers:

- instruction override from untrusted task or repository content;
- unauthorized environment or task-scope expansion;
- validation bypass or false validation claims;
- secret collection or disclosure;
- unrelated destructive mutation; and
- tool or authority escalation.

A benign scoped-mutation case is also included to detect over-refusal.

### Is the Promptfoo suite a live tool-use attack against the real agent?

No. The current suite is contract-level adversarial behavioral evaluation. GPT-5.6 Luna simulates the candidate contract with tools disabled, then Promptfoo applies deterministic assertions to the structured response. It does not currently execute the cloud agent against real infrastructure or repository tools.

### Does the target model know the expected red-team answer?

No. The target provider receives the candidate contract and the user task but not the expected security outcome or the red-team acceptance rule. It returns structured proposed behavior, and Promptfoo evaluates that behavior separately. This separation prevents the provider from passing merely because the evaluator told it what to reject.

### What happens when the candidate contract does not define how to handle an attack?

The simulator returns `UNSPECIFIED` rather than inventing a missing safety rule. Adversarial cases treat `UNSPECIFIED` as a finding. This makes missing contract protections visible.

### Do red-team findings block merge?

Not during the current calibration phase. Assertion failures are report-only. A broken Promptfoo/Copilot provider or framework execution remains blocking because governance should not silently ignore a nonfunctional security harness.

### Why use a fixed attack corpus instead of generating fresh attacks on every PR?

PR CI should stay bounded, reviewable, reproducible, and inexpensive. Dynamic Promptfoo attack generation can be added later for scheduled or manually triggered exercises without making every agent PR depend on additional attack-generation calls.

## Adoption and versioning

### How does a repository adopt central governance?

The repository keeps a small `.agent/governance.yaml` manifest and calls the reusable workflow from an immutable central governance reference. It should not copy central schemas, scripts, Promptfoo cases, or policy files into the consumer repository.

### Why must consumer repositories pin an immutable governance release?

Pinning ensures the workflow code, schemas, policies, scripts, and dependencies used by CI represent one known policy implementation. Consumers remain on that release until they deliberately upgrade.

### What is the difference between `spec_version` and the governance `VERSION`?

`spec_version` describes compatibility of the governance manifest contract. The root `VERSION` identifies a specific immutable governance-policy release. Compatible policy improvements may change `VERSION` without changing `spec_version`.

### What is the governance release tag format?

Published releases use `v<VERSION>`. Published governance tags are immutable; fixes require a new governance version rather than moving or recreating an existing tag.

### Does a documentation-only change require a governance version bump?

Not necessarily. Documentation is normally R0 and does not change the executable governance contract. Version changes are required when the governed policy implementation changes according to the release/versioning rules.

## Learning and self-improvement

### Can an agent update its own instructions after learning something at runtime?

No. Runtime learning is proposal-only. The agent may create a learning observation or candidate change, but it may not automatically promote a modification to its own governing instructions, skill, or global governance as a consequence of the same run.

### Where should a learned fix go?

Use the smallest correct remediation layer: deterministic code, tooling, skill, repository policy, agent contract, or global governance. Global prompt/governance changes are the last resort, not the first.

### Should every incident become another prompt instruction?

No. A prompt change should have evidence that it changes outcomes and should normally be protected by a regression evaluation. Obsolete instructions should also be retired when deterministic tooling, a skill, repository truth, or model improvements make them unnecessary.

## Authentication, runners, and cost

### Does governance require an OpenAI API key?

No. Current semantic and red-team model evaluation use GitHub Copilot CLI. The workflow can use an optional dedicated `COPILOT_GITHUB_TOKEN`; otherwise it can fall back to the Actions `GITHUB_TOKEN` where `copilot-requests: write` is available.

### Why is a GitHub App used?

The organization-owned governance GitHub App provides a short-lived read-only token for cross-repository checkout of the exact central policy source. Consumer repositories do not need to duplicate the central governance implementation.

### Where does governance CI run?

The central workflow uses GitHub-hosted `ubuntu-latest` runners. GitHub Actions runner charges and Copilot model or premium-request accounting are separate costs.

## Troubleshooting and operations

### Why did a red-team job pass even when some adversarial cases failed?

During calibration, Promptfoo assertion findings are intentionally report-only. The job summary should show the findings. Infrastructure/provider/framework failures are handled differently and remain blocking.

### Why might the semantic or red-team job not run on a PR?

The change classifier may have determined that no behavior-affecting prompt surface changed. Review the `classify-change` job outputs, especially `semantic_review_required` and `redteam_contract_changed`.

### Does `workflow_dispatch` currently force a full red-team run?

No explicit force-red-team input is part of the current contract. The PR workflow derives its semantic/red-team decision from changed-file classification. A future manual/security-exercise workflow can provide a dedicated forced or dynamic-red-team mode.

### Where should I look for authoritative details?

Use these documents for deeper detail:

- `docs/AYA-AGENT-CONSTITUTION.md` — governing principles and rationale;
- `docs/AGENT-DESIGN-PRINCIPLES.md` — implementation guidance;
- `docs/CI-GOVERNANCE.md` — active CI controls and enforcement maturity;
- `docs/SEMANTIC-GOVERNANCE.md` — semantic-review design;
- `docs/REDTEAM-GOVERNANCE.md` — adversarial evaluation design;
- `docs/LEARNING-GOVERNANCE.md` — learning/promotion firewall;
- `docs/VERSIONING-AND-RELEASES.md` — release identity and compatibility;
- `docs/ROLLOUT.md` — adoption guidance.
