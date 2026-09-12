# Learning Governance

## Promotion firewall

**Agents may generate learning; they may not promote their own learning.** Runtime discoveries become candidate records. Promotion is a pull-request event subject to validation, evaluation, ownership, and review.

```text
runtime -> observation -> LearningRecord -> classify -> eval -> candidate change -> PR -> CI/review -> promotion -> measure
```

The agent that encounters a failure must not directly modify its governing instructions, governing skill, or global policy as an automatic consequence of that same run.

## Classification before change

Classify the smallest correct remediation layer:

- `code` — deterministic implementation defect;
- `tool` — deterministic capability or validation defect;
- `skill` — reusable procedure or technology knowledge;
- `repository-policy` — repository-specific invariant;
- `agent` — mission, authority, scope, stopping, or orchestration defect;
- `global-governance` — organization-wide invariant.

Global prompt changes are the last resort, not the first.

## Evidence and eval requirement

Behavioral prompt learning normally requires a failing evaluation before promotion and a passing result after the candidate change. An explicit organization-wide safety/governance invariant may be introduced without a historical failure, but should still have a protective regression evaluation.

Global promotion additionally requires evidence that the issue spans contexts, is a serious governance defect, or is an explicit organizational invariant; analysis of lower-level alternatives; duplication analysis; and regression results.

## Retirement is learning

The loop also removes obsolete instructions. Candidate deletion is appropriate when a rule no longer changes outcomes, a deterministic tool enforces it, a skill now owns it, or a model upgrade passes the same evals without it.
