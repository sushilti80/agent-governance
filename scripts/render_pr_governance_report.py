#!/usr/bin/env python3
"""Render a bounded sticky pull-request governance report from machine outputs."""
from __future__ import annotations

import argparse

MARKER = "<!-- aya-agent-governance-report -->"
JOB_RESULTS = {"success", "failure", "cancelled", "skipped"}
SEMANTIC_VERDICTS = {"PASS", "REVIEW", "FAIL", "INVALID", "NOT_REQUIRED"}
REDTEAM_OUTCOMES = {"PASS", "FINDINGS", "ERROR", "NOT_REQUIRED"}
REPOSITORY_EVAL_OUTCOMES = {"PASS", "FINDINGS", "ERROR", "NOT_ENABLED", "NOT_REQUIRED"}


def as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"expected true or false, got {value!r}")


def icon(result: str) -> str:
    return {
        "success": "✅ PASS",
        "failure": "❌ FAIL",
        "cancelled": "⚠️ CANCELLED",
        "skipped": "➖ SKIPPED",
    }.get(result, "❌ INVALID")


def overall_result(
    deterministic_result: str,
    classification_result: str,
    semantic_required: bool,
    semantic_job_result: str,
    semantic_verdict: str,
    redteam_required: bool,
    redteam_job_result: str,
    redteam_outcome: str,
    repository_eval_required: bool,
    repository_eval_job_result: str,
    repository_eval_outcome: str,
) -> str:
    if deterministic_result != "success" or classification_result != "success":
        return "BLOCKED"

    if semantic_required:
        if semantic_job_result != "success" or semantic_verdict not in {"PASS", "REVIEW", "FAIL"}:
            return "BLOCKED"

    if redteam_required:
        if redteam_job_result != "success" or redteam_outcome not in {"PASS", "FINDINGS"}:
            return "BLOCKED"

    if repository_eval_required:
        if repository_eval_job_result != "success" or repository_eval_outcome not in {"PASS", "FINDINGS"}:
            return "BLOCKED"

    if semantic_required and semantic_verdict in {"REVIEW", "FAIL"}:
        return "ATTENTION"
    if redteam_required and redteam_outcome == "FINDINGS":
        return "ATTENTION"
    if repository_eval_required and repository_eval_outcome == "FINDINGS":
        return "ATTENTION"
    return "PASS"


def semantic_display(required: bool, job_result: str, verdict: str) -> str:
    if not required:
        return "➖ NOT REQUIRED"
    if job_result != "success" or verdict == "INVALID":
        return "❌ ERROR (blocking)"
    return {
        "PASS": "✅ PASS (report-only verdict)",
        "REVIEW": "⚠️ REVIEW (report-only)",
        "FAIL": "⚠️ FAIL (report-only)",
    }.get(verdict, "❌ INVALID (blocking)")


def redteam_display(required: bool, job_result: str, outcome: str) -> str:
    if not required:
        return "➖ NOT REQUIRED"
    if job_result != "success" or outcome == "ERROR":
        return "❌ ERROR (blocking)"
    return {
        "PASS": "✅ PASS",
        "FINDINGS": "⚠️ FINDINGS (report-only)",
    }.get(outcome, "❌ INVALID (blocking)")


def repository_eval_display(required: bool, job_result: str, outcome: str) -> str:
    if not required:
        return "➖ NOT REQUIRED"
    if job_result != "success" or outcome == "ERROR":
        return "❌ ERROR (blocking)"
    return {
        "PASS": "✅ PASS",
        "FINDINGS": "⚠️ FINDINGS (report-only)",
    }.get(outcome, "❌ INVALID (blocking)")


def render(args: argparse.Namespace) -> str:
    semantic_required = as_bool(args.semantic_required)
    redteam_required = as_bool(args.redteam_required)
    repository_eval_required = as_bool(args.repository_eval_required)

    semantic_verdict = args.semantic_verdict or ("INVALID" if semantic_required else "NOT_REQUIRED")
    redteam_outcome = args.redteam_outcome or ("ERROR" if redteam_required else "NOT_REQUIRED")
    repository_eval_outcome = args.repository_eval_outcome or (
        "ERROR" if repository_eval_required else "NOT_REQUIRED"
    )

    overall = overall_result(
        args.deterministic_result,
        args.classification_result,
        semantic_required,
        args.semantic_job_result,
        semantic_verdict,
        redteam_required,
        args.redteam_job_result,
        redteam_outcome,
        repository_eval_required,
        args.repository_eval_job_result,
        repository_eval_outcome,
    )

    lines = [
        MARKER,
        "## 🛡️ Aya Agent Governance",
        "",
        f"**Overall:** {overall}",
        f"**Evaluated commit:** `{args.head_sha[:12]}`",
        f"**Highest risk:** `{args.highest_risk or 'unknown'}`",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Deterministic governance | {icon(args.deterministic_result)} |",
        f"| Change classification | {icon(args.classification_result)} |",
        f"| Semantic governance | {semantic_display(semantic_required, args.semantic_job_result, semantic_verdict)} |",
        f"| Adversarial red team | {redteam_display(redteam_required, args.redteam_job_result, redteam_outcome)} |",
        f"| Repository behavioral evals | {repository_eval_display(repository_eval_required, args.repository_eval_job_result, repository_eval_outcome)} |",
    ]

    if semantic_required:
        lines.extend(
            [
                "",
                "### Semantic review",
                "",
                f"- Verdict: `{semantic_verdict}`",
                f"- Reviewer action: `{args.reviewer_action or 'NONE'}`",
                f"- Findings: `{max(args.semantic_findings, 0)}`",
            ]
        )

    if redteam_required:
        lines.extend(
            [
                "",
                "### Red-team review",
                "",
                f"- Outcome: `{redteam_outcome}`",
                f"- Cases passed: `{max(args.redteam_successes, 0)}`",
                f"- Findings: `{max(args.redteam_failures, 0)}`",
                f"- Harness/provider errors: `{max(args.redteam_errors, 0)}`",
            ]
        )

    if repository_eval_required:
        lines.extend(
            [
                "",
                "### Repository behavioral evals",
                "",
                f"- Outcome: `{repository_eval_outcome}`",
                f"- Cases passed: `{max(args.repository_eval_successes, 0)}`",
                f"- Findings: `{max(args.repository_eval_failures, 0)}`",
                f"- Harness/provider errors: `{max(args.repository_eval_errors, 0)}`",
            ]
        )
        if args.repository_eval_diagnostic:
            lines.extend(
                [
                    f"- Diagnostic: `{args.repository_eval_diagnostic[:4000]}`",
                ]
            )

    lines.extend(
        [
            "",
            "### Interpretation",
            "",
            "- `PASS` — blocking controls passed and no report-only findings were detected.",
            "- `ATTENTION` — blocking controls passed, but semantic, red-team, or repository-eval findings need review.",
            "- `BLOCKED` — a blocking deterministic, classification, judge-contract, provider, harness, or reporting prerequisite failed.",
            "",
            "### Evidence",
            "",
            f"[View detailed governance run]({args.run_url})",
            "",
            "_This comment is updated in place by Aya Agent Governance. Full findings, evidence, and raw logs remain in GitHub Actions._",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deterministic-result", choices=sorted(JOB_RESULTS), required=True)
    parser.add_argument("--classification-result", choices=sorted(JOB_RESULTS), required=True)
    parser.add_argument("--highest-risk", default="")
    parser.add_argument("--semantic-required", choices=("true", "false"), required=True)
    parser.add_argument("--semantic-job-result", choices=sorted(JOB_RESULTS), required=True)
    parser.add_argument("--semantic-verdict", choices=sorted(SEMANTIC_VERDICTS), default="NOT_REQUIRED")
    parser.add_argument("--reviewer-action", default="NONE")
    parser.add_argument("--semantic-findings", type=int, default=0)
    parser.add_argument("--redteam-required", choices=("true", "false"), required=True)
    parser.add_argument("--redteam-job-result", choices=sorted(JOB_RESULTS), required=True)
    parser.add_argument("--redteam-outcome", choices=sorted(REDTEAM_OUTCOMES), default="NOT_REQUIRED")
    parser.add_argument("--redteam-successes", type=int, default=0)
    parser.add_argument("--redteam-failures", type=int, default=0)
    parser.add_argument("--redteam-errors", type=int, default=0)
    parser.add_argument("--repository-eval-required", choices=("true", "false"), required=True)
    parser.add_argument("--repository-eval-job-result", choices=sorted(JOB_RESULTS), required=True)
    parser.add_argument(
        "--repository-eval-outcome",
        choices=sorted(REPOSITORY_EVAL_OUTCOMES),
        default="NOT_REQUIRED",
    )
    parser.add_argument("--repository-eval-successes", type=int, default=0)
    parser.add_argument("--repository-eval-failures", type=int, default=0)
    parser.add_argument("--repository-eval-errors", type=int, default=0)
    parser.add_argument("--repository-eval-diagnostic", default="")
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()

    print(render(args), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
