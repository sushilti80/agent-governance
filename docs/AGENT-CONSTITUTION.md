# Agent Constitution

## Purpose

The Agent Constitution defines the organization-wide design invariants every governed agent system must preserve. It intentionally states **what must be true**. Specialized policies define how delegation, tools, learning, semantic review, runtime efficiency, and release management operationalize those invariants.

The machine-readable constitution is `principles/agent-design.yaml`. This document is the stakeholder-oriented explanation of the architecture and governance model.

## Core model

This governance model separates responsibilities deliberately:

1. **Agent = intent and authority.** Mission, scope, evidence, mutation/external-action authority, success criteria, and escalation.
2. **Skill = procedure.** Reusable procedure and validation within authority inherited from the calling context.
3. **Repository = truth.** Current repository evidence governs factual decisions about repository state.
4. **Deterministic mechanism = deterministic work.** Formatting, parsing, validation, comparison, bounded enumeration, and enforceable mechanics belong in code/tools where practical.
5. **Evaluation = proof.** Behavioral change requires evidence that correctness, safety, scope, validation, and efficiency are preserved or improved.
6. **Learning = proposal.** Runtime learning may generate evidence and candidate changes but cannot promote its own governing behavior.

## Instruction and responsibility hierarchy

```text
Organization governance
        |
Repository-wide invariants
        |
Agent contract
        |
Requested task scope and approvals
        |
Skill procedure
        |
Delegated subtask
```

A lower layer may specialize or narrow inherited behavior. It may not broaden authority, weaken a governing invariant, or create a competing authority contract.

## Effective authority

Effective authority is an intersection:

```text
Effective authority
    = organization governance
      INTERSECT repository policy
      INTERSECT agent authority
      INTERSECT requested task scope
      INTERSECT required approvals
```

Consequences:

- difficulty never creates additional authority;
- skills and delegated agents inherit authority and may only narrow it;
- missing or ambiguous authority is not permission;
- lower layers cannot override higher-level limits; and
- contradictions are not resolved by selecting the more permissive instruction.

Example: if production mutation requires approval, an agent is mutation-capable, and the request names development only, the effective authority excludes production. A skill cannot expand that scope by saying to update all environments where useful.

## Coherent behavioral contract

All applicable instructions must be mutually satisfiable. Governance treats these as contract defects:

- conflicting goals or success criteria;
- conflicting repository/environment scope;
- inconsistent mutation or external-action authority;
- incompatible approval requirements;
- contradictory validation rules;
- incompatible delegation or stopping behavior; and
- the same behavioral rule being independently owned or redefined by multiple layers.

Repository evidence may resolve factual ambiguity where it is authoritative. Material ambiguity about authority, approval, or policy follows the escalation boundary rather than being guessed away.

## Role ownership

| Layer | Owns | Must not do |
| --- | --- | --- |
| Organization governance | Organization-wide invariants and governance contracts | Encode repository-specific procedures |
| Repository instructions | Repository-wide facts and invariants | Reimplement narrow skill procedures |
| Agent | Intent, authority, scope, evidence, success, escalation | Become a large technology runbook |
| Skill | Reusable procedure and validation | Grant or broaden authority |
| Deterministic code/tool | Deterministic mechanics and enforceable checks | Reinterpret policy through model reasoning |
| Delegated agent | Bounded independent subtask | Gain more authority than its caller |

This prevents both duplication and competing behavioral ownership.

## Constitutional principles

`principles/agent-design.yaml` defines sixteen required principles:

- **AGP-001 Outcome First** — define the outcome and observable success criteria.
- **AGP-002 Instruction Once** — give each behavioral rule one authoritative home.
- **AGP-003 Repository Is Truth** — current repository evidence overrides stale assumptions.
- **AGP-004 Minimum Necessary Instruction** — persistent instructions require evidence or a real invariant.
- **AGP-005 Bounded Autonomy** — authority is explicit, bounded, and no broader than required.
- **AGP-006 Deterministic Before Agentic** — deterministic work belongs in deterministic mechanisms where practical.
- **AGP-007 Validate After Mutation** — mutation requires relevant deterministic validation before success.
- **AGP-008 Bounded Delegation** — delegate independent work without recursive fan-out or authority amplification.
- **AGP-009 Learning Propose Only** — learning cannot directly promote or modify governing behavior.
- **AGP-010 Evidence Before Learning** — behavioral learning requires evidence and evaluation or an explicit invariant.
- **AGP-011 Smallest Correct Layer** — fix the layer that actually owns the failure.
- **AGP-012 Measurable Evolution** — behavioral changes must preserve or improve representative quality dimensions.
- **AGP-013 Coherent Behavioral Contract** — all applicable instructions must be mutually satisfiable.
- **AGP-014 Authority Non-Expansion** — effective authority is an intersection and only narrows down the stack.
- **AGP-015 Role Separation** — repository policy, agents, skills, deterministic tools, and delegates have distinct responsibilities.
- **AGP-016 Stop or Escalate** — stop on validated success; escalate when evidence, authority, approval, or policy is insufficient.

## Specialized policies

The constitution remains small by delegating mechanics:

- `delegation-policy.yaml` operationalizes delegation limits and primary-agent responsibility;
- `tool-policy.yaml` governs tool exposure, mutation authority, and deterministic validation;
- `learning-policy.yaml` governs propose-only learning and promotion evidence;
- `semantic-review-policy.yaml` governs the design-time LLM judge;
- `runtime-efficiency-policy.yaml` defines measurable runtime repetition/delegation/stopping signals; and
- `versioning-policy.yaml` defines release and compatibility rules.

## Governance CI

Governance CI is layered.

### Deterministic layer — active and blocking

The central workflow validates schemas, governance versions, policy integrity, the learning firewall, AGP-001 through AGP-016, global eval catalog integrity, workflow identity, regression tests, and release metadata.

Objective failures remain deterministic. An LLM cannot waive them.

### Semantic layer — active, report-only

Release `2026.09.3` introduces GPT-5.6 Luna through GitHub Copilot CLI for design-time semantic review of agent, skill, and repository Copilot-instruction changes.

The judge compares the **base effective behavioral contract** with the **candidate effective behavioral contract** and evaluates all sixteen principles, including:

- authority expansion;
- contradictory instructions;
- competing behavioral ownership;
- wrong-layer responsibility;
- weakened validation;
- delegation or learning-boundary changes; and
- stopping/escalation changes.

Repository content is untrusted evidence. The judge runs from an isolated directory with repository custom instructions disabled, built-in MCP disabled, and read/shell/write/URL/memory tools denied.

Luna returns a strict JSON result (`PASS`, `REVIEW`, or `FAIL`) that deterministic code validates.

During calibration semantic results do **not** block merge. This prevents an uncalibrated probabilistic control from becoming an arbitrary gatekeeper.

See `docs/SEMANTIC-GOVERNANCE.md`.

### Behavioral eval layer — partially implemented

Global behavioral evaluation specifications exist and are protected as R4 governance artifacts. Their catalog is checked deterministically.

The current system does not yet claim that every changed consumer agent executes every semantic behavioral case. A complete behavioral execution harness is a separate milestone.

### Runtime layer — report-only engine, ingestion not active

Runtime efficiency policy and audit logic exist. Real cross-repository Copilot cloud-agent telemetry ingestion is not yet active, so runtime governance must not be described as a blocking control.

## Change-management model

Global governance changes are R4 and are versioned/reviewed through the same governed PR process.

Consumer repositories execute an immutable pinned governance reference. A central change does not silently alter a consumer; adoption happens through explicit repinning.

`spec_version` changes only when the manifest compatibility contract breaks. Governance releases may advance without changing `spec_version`.

## Current maturity statement

After release `2026.09.3`, this governance can accurately claim:

- deterministic central governance is active;
- the sixteen-principle Agent Constitution is active;
- cross-repository policy checkout uses a GitHub App token only when the governance repository is private and App secrets are supplied;
- GPT-5.6 Luna semantic review is active for behavior-affecting prompt changes **when consumers adopt the release**, but remains report-only;
- semantic output is schema-validated and cannot override deterministic failures;
- runtime efficiency auditing exists but real cloud-agent trace ingestion is not yet broadly active; and
- semantic blocking requires calibration and a later explicit R4 promotion decision.

Those distinctions are intentional so stakeholder communication matches actual enforcement maturity.
