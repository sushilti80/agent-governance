# Changelog

All notable governance changes are recorded here. Governance release tags are immutable and use `v<VERSION>`.

## [2026.09.7] - 2026-09-08

### Changed

- Consumer governance config, validator-script, and governance-workflow changes are deterministic-only and no longer trigger Copilot/Luna semantic evaluation.
- Behavioral semantic scope now explicitly includes agents, skills, repository Copilot instructions, `.github/instructions/**`, `.github/prompts/**`, and `.github/agent-memory/**`.
- Bounded semantic context now includes instruction fragments, prompts, and agent memory while keeping `.agent/governance.yaml` out of semantic change evaluation.
- Central semantic-contract changes continue to run the Luna smoke path only when `agent-governance` itself is the target repository.
- Added regression coverage for deterministic-only versus semantic trigger scope.
- Central and example governance manifests now declare policy release `2026.09.7`; governance manifest `spec_version` remains `1`.

## [2026.09.6] - 2026-09-07

### Added

- Semantic judge result schema v2 with structured assessment, reviewer action, per-finding remediation, and an overall recommended outcome.
- Actionable recommendation vocabulary for smallest-correct-layer remediation across repository, agent, skill, deterministic code, governance, and human review.
- Semantic-contract smoke execution so changes to the constitution, semantic policy, prompt/context builders, result schema, validator, or central semantic workflow exercise the actual Luna path before merge.
- Regression coverage requiring REVIEW results to include actionable reviewer guidance, enforcing the verdict/action matrix, and ensuring summaries expose rationale and suggested changes.

### Changed

- Luna is now instructed to provide concise evidence-backed decision rationale rather than only a PASS/REVIEW/FAIL classification.
- Recommendation relocation uses one `MOVE` action plus `target_layer` as the single destination field; uncalibrated model confidence was removed from the governed result contract.
- Human-readable job summaries now render what changed, why it matters, risk/impact, findings, evidence, per-finding recommendations, and the recommended outcome.
- Deterministic validation now enforces coherent PASS/REVIEW/FAIL reviewer actions, finding severities, overall actions, and priorities; blocking findings cannot be hidden in REVIEW.
- Central and example governance manifests now declare policy release `2026.09.6`; governance manifest `spec_version` remains `1`.

## [2026.09.5] - 2026-09-07

### Fixed

- Removed `--no-banner` from the pinned Copilot CLI `1.0.83` invocation after the Aya-Flux pilot proved that stable binary rejects the option even though the current online CLI reference documents it.
- Removed the undocumented `--auth-token-env` dependency and now use GitHub's documented Copilot token environment precedence, explicitly copying `GITHUB_TOKEN` into `COPILOT_GITHUB_TOKEN` only when the dedicated secret is absent.
- Added a runtime compatibility preflight that checks the actual installed Copilot CLI help output for every nontrivial option used by semantic governance before the Luna judge is invoked.
- Regression coverage now prevents reintroducing unsupported or undocumented CLI flags into the stable semantic-judge contract.

### Changed

- Central and example governance manifests now declare policy release `2026.09.5`; `spec_version` remains `1`.

## [2026.09.4] - 2026-09-07

### Fixed

- Large semantic-governance prompts are streamed to Copilot CLI over stdin instead of being expanded into a single `-p` command-line argument, avoiding Linux `Argument list too long` failures on self-hosted runners.
- The semantic judge step now returns Copilot CLI's actual exit code so authentication, model, runtime, and invocation failures are visible as failed checks instead of false-green steps.
- The exact semantic result JSON Schema is embedded into the trusted evaluator prompt so Luna can satisfy the governed output contract without repository or filesystem read access.
- Regression coverage now forbids command-substitution prompt transport, requires stdin transport, requires real judge exit propagation, and verifies that the output schema is included as trusted prompt input.
- Semantic-governance documentation now distinguishes advisory semantic verdicts from blocking judge-execution/result-contract failures.

### Changed

- Central and example governance manifests now declare policy release `2026.09.4`; `spec_version` remains `1`.

## [2026.09.3] - 2026-09-07

### Added

- Report-only GPT-5.6 Luna semantic governance for behavior-affecting agent, skill, and repository Copilot-instruction changes.
- `principles/semantic-review-policy.yaml` mapping semantic review dimensions to the full AGP-001 through AGP-016 constitution.
- A strict semantic judge result schema with deterministic cross-field validation.
- Deterministic base-versus-candidate context assembly and prompt trust-boundary construction.
- Initial PASS, FAIL, and REVIEW calibration fixtures and semantic-governance regression tests.
- Stakeholder and operator documentation for semantic-governance architecture, rollout, threat model, and future promotion criteria.

### Changed

- Change classification now emits `semantic_review_required` independently of highest governance risk so mixed R4 + agent/skill changes still receive semantic review.
- The reusable governance workflow grants `copilot-requests: write`, invokes pinned Copilot CLI `1.0.83` with `gpt-5.6-luna`, and validates the judge JSON before reporting it.
- Semantic review runs outside the target repository with custom instructions and built-in MCP disabled and read/shell/write/URL/memory tools denied.
- Semantic filesystem locations are fixed workspace children (`target/`, `policy/`, `.aya-semantic-judge/`) with containment validation; semantic scripts no longer accept target, policy, schema, input, or output paths from CLI arguments.
- Semantic `FAIL`, `REVIEW`, malformed output, and Copilot invocation failures are report-only during calibration and do not yet block merge.
- Governance Actions moved from Node-20-era `actions/checkout@v4` / `actions/setup-python@v5` to `actions/checkout@v5` / `actions/setup-python@v6`; the semantic job explicitly uses Node 24.
- Central and example governance manifests now declare policy release `2026.09.3`; `spec_version` remains `1`.

## [2026.09.2] - 2026-09-07

### Added

- AGP-013 through AGP-016 covering coherent behavioral contracts, authority non-expansion, role separation, and stop-or-escalate behavior.
- A stakeholder-oriented Aya Agent Constitution documenting the composed-agent model, instruction hierarchy, effective-authority intersection, role ownership, and governance CI roadmap.

### Changed

- Strengthened AGP-001 through AGP-012 descriptions to make outcome, instruction ownership, repository truth, minimum instruction, authority, delegation, validation, learning, and measurable-evolution expectations more explicit without moving specialized policy mechanics into the constitution.
- Deterministic governance now requires AGP-001 through AGP-016 to be present and marked `required`.
- Central and example governance manifests now declare policy release `2026.09.2`; `spec_version` remains `1` because the manifest schema contract is unchanged.
- Documentation now distinguishes active deterministic governance from planned Luna semantic evaluation and report-only runtime governance to avoid overstating enforcement maturity.

## [2026.09.1] - 2026-09-03

### Added

- AGP-001 through AGP-012 agent design principles.
- Learning, delegation, and tool governance policies.
- JSON Schemas for governance manifests, agents, skills, and LearningRecords.
- Global behavioral eval specifications for authority, mutation, scope, delegation, learning isolation, and stopping behavior.
- Reusable governance workflow, deterministic validation, and risk classification.
- Governed learning promotion firewall and repository rollout guidance.

### Hardened

- Reusable workflow now separates target and policy roots.
- Governance manifests are validated against Draft 2020-12 schemas.
- `learning.mode: self-promote` is rejected deterministically.
- Global behavioral eval changes are classified R4.
- Prompt linting is restricted to declared executable agent/skill locations.
- Regression tests cover critical governance invariants.
- Governance versioning, compatibility, release readiness, and immutable-tag policy are now self-validated.
- Reusable workflow policy checkout is derived from the exact called-job workflow repository and commit SHA, removing the duplicate policy-ref input and ref-mismatch failure mode.
- Cross-repository policy checkout now uses a short-lived, read-only token minted by the organization-owned `agents-governance` GitHub App while same-repository validation continues to use `github.token`.
