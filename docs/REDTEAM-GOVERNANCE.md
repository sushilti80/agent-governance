# Red-team governance

Aya agent governance uses Promptfoo as a lightweight CI orchestration layer for adversarial security evaluation of behavior-affecting agent contracts.

## Purpose

The first implementation is intentionally narrow. It tests changed agent, skill, and repository-instruction contracts against a small organization-owned corpus of high-value attacks. It does **not** claim to execute a live Copilot cloud-agent session with real repository tools.

The initial threat classes are:

- instruction override from untrusted task or repository content;
- unauthorized environment or task-scope expansion;
- validation bypass or false validation claims;
- secret collection or disclosure;
- unrelated destructive mutation; and
- tool or authority escalation.

A benign explicitly scoped mutation case is included to detect over-refusal.

## Execution model

The reusable governance workflow already classifies whether a change affects semantic behavior. When `semantic_review_required=true`, the red-team job:

1. checks out the target repository and the exact immutable governance policy source;
2. builds the same bounded candidate-contract context used by semantic governance;
3. installs pinned `promptfoo` and Copilot CLI versions on Node 24;
4. runs Promptfoo against `redteam/cases.yaml` with cache disabled and concurrency limited to one;
5. invokes GPT-5.6 Luna through `scripts/promptfoo_copilot_provider.py` to simulate the candidate agent contract; and
6. applies deterministic Promptfoo assertions to the structured simulated behavior.

The target provider and the evaluator are deliberately separate. The provider receives the candidate contract and user task but does not receive the expected security outcome or red-team acceptance criteria. It must return one structured JSON object describing the candidate agent's proposed decision, scope, validation posture, and whether it proposes secret access, unrelated mutation, authority expansion, or validation bypass.

If the candidate contract does not determine how to handle a request, the provider must return `UNSPECIFIED` rather than inventing a missing safety rule. Adversarial cases treat `UNSPECIFIED` as a finding; the benign control requires a safe `PROCEED` decision. This makes missing contract protections visible instead of letting the simulator fill them in from evaluator policy.

Promptfoo owns the acceptance criteria. Each case deterministically evaluates the returned JSON. No second LLM grader is used, so the bounded suite remains one Luna call per test case.

The provider runs Copilot CLI with custom instructions disabled, built-in MCP disabled, remote execution disabled, and read/shell/write/URL/memory tools denied. This is contract simulation, not live tool execution.

## Enforcement state

Red-team findings are **report-only during calibration**. Promptfoo exit code `100` means one or more assertions failed and is reported without blocking merge. Any other non-zero exit code is treated as an infrastructure/framework failure and fails the job.

This separation is deliberate: governance should not silently ignore a broken security test harness, but individual model-security findings need calibration before becoming merge-blocking.

Promotion to blocking requires an R4 governance change based on observed false-positive/false-negative rates across real Aya agent changes.

## Why fixed attacks first

PR CI uses a version-controlled attack corpus rather than generating fresh attacks on every run. This keeps the gate bounded, reviewable, reproducible, and inexpensive. Promptfoo's broader dynamic red-team generation can be added later as a scheduled or manually dispatched security exercise without making every developer PR dependent on a second attack-generation model call.

## Scope and future work

The current lane is a contract-level control. A later runtime red-team harness may execute cloud/CLI agents in disposable test repositories with synthetic credentials and constrained tools to validate actual tool-use behavior, indirect prompt injection, and side effects.

Promptfoo remains the orchestration/reporting layer; Aya-owned cases and acceptance criteria remain the governance contract.
