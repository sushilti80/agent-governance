# Rollout Plan

## Phase 1 — bootstrap this repository

- Merge principles, schemas, global eval specifications, deterministic checks, docs, and reusable workflow.
- Protect governance files with CODEOWNERS (`@sushilti80`) and enable required pull-request review from code owners on `main`.
- Keep the initial workflow deterministic and dependency-light.

## Phase 2 — observe organization repositories

- Add `.agent/governance.yaml` to selected IaC repositories.
- Inventory existing `copilot-instructions.md`, agents, and skills.
- Run governance in non-blocking/evaluate mode.
- Record false positives, missing evals, and baseline efficiency.

## Phase 3 — clean existing agents

For each repository, remove duplicated global rules, move procedures to skills, move deterministic operations to tools/CI, add explicit authority/success criteria where missing, and add regression cases for observed failures.

## Phase 4 — enforce

Configure a GitHub organization ruleset requiring the central governance workflow for target repositories. Require CODEOWNER review by risk level and protect changes to rulesets/workflows from ordinary agent automation.

## Phase 5 — governed learning

Allow runtime agents to emit `LearningRecord` candidates. Candidates enter normal PR review and must satisfy the promotion firewall. Track both additions and retirement of instructions.

## Mirror strategy

If this governance source is maintained in more than one GitHub location, nominate exactly one authoritative upstream. Mirror only reviewed commits/tags to the secondary location. Do not independently edit both copies; that creates policy split-brain. CI should compare the mirrored governance version or commit SHA before publishing releases.
