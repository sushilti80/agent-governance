# Agent Design Principles

The machine-readable source of truth is `principles/agent-design.yaml`. The stakeholder-oriented constitutional rationale is documented in `docs/AYA-AGENT-CONSTITUTION.md`.

## Design hierarchy

Use the smallest correct layer:

1. **Deterministic code/tool** for formatting, parsing, validation, comparison, bounded enumeration, and enforceable mechanics.
2. **Skill** for reusable technology or workflow procedure and validation.
3. **Repository policy** for repository-wide facts and invariants.
4. **Agent** for mission, scope, authority, evidence sources, success criteria, and escalation.
5. **Global governance** only for organization-wide invariants.

Lower layers may specialize or narrow the behavior allowed above them, but they may not broaden authority or independently redefine a governing rule.

## Minimum necessary instruction

Prompt growth is not the default remedy for a failure. Before adding an instruction, identify the observed failure, reproduce it with an evaluation where practical, determine whether a deterministic or narrower-layer fix exists, and measure regression after the candidate change.

Generic exhortations such as "be thorough", "get the full picture", or unbounded persistence should not be used as substitutes for concrete success criteria and stopping conditions.

## Effective authority

Effective authority is the intersection of:

- organization governance;
- repository policy;
- agent-declared authority;
- requested task scope; and
- required approvals.

The effective set can only stay the same or become narrower as work moves into skills and delegated subtasks. Missing or ambiguous authority is not permission. Skills consume authority granted above them; they do not create new authority.

## Coherent behavioral contract

Applicable repository instructions, agent instructions, skills, and delegated-task constraints must be mutually satisfiable. Conflicting goals, mutation scope, approval requirements, validation rules, delegation rules, or stopping conditions are governance defects.

Do not resolve a contradiction by selecting the more permissive instruction. Resolve it through repository evidence where authoritative; otherwise follow the defined escalation boundary.

## Role separation

- **Repository instructions** define repository-wide invariants.
- **Agents** define intent, authority, scope, success criteria, and escalation.
- **Skills** implement reusable procedure and validation within inherited authority.
- **Deterministic code/tools** implement deterministic mechanics.
- **Delegated agents** perform bounded subtasks without receiving greater authority than the caller.

## Delegation and stopping

Complexity alone is not a reason to delegate. Delegate independent workstreams that can proceed without shared intermediate state, bound the fan-out, retain synthesis in the primary agent, and stop once success criteria and required validation are satisfied.

If completion is blocked by missing evidence, authority, approval, or unresolved contradiction, escalate rather than widening scope, repeating equivalent work, or delegating without measurable progress.

## Quality model

A successful agent change preserves or improves all relevant dimensions:

- task correctness;
- safety and authority compliance;
- requested scope adherence;
- deterministic validation quality;
- internal contract coherence;
- correct ownership across repository policy, agent, skill, and deterministic layers;
- tool-call and delegation efficiency; and
- token, cost, and latency efficiency where measurable.
