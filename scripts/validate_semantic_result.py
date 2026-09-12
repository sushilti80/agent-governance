#!/usr/bin/env python3
"""Validate and summarize GPT-5.6 Luna semantic-governance output."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ARTIFACT_DIR_NAME = ".semantic-judge"
REVIEW_ACTIONS = {
    "CONSIDER_SIMPLIFICATION",
    "CHANGE_RECOMMENDED",
    "HUMAN_DECISION_REQUIRED",
}
REVIEW_OUTCOMES = {"SIMPLIFY", "CHANGE", "ESCALATE"}
REVIEW_PRIORITIES = {"consider", "before_merge"}


def contained_child(base: Path, child_name: str, *, must_exist: bool) -> Path:
    base = base.resolve(strict=True)
    candidate = (base / child_name).resolve(strict=must_exist)
    candidate.relative_to(base)
    return candidate


def fixed_paths() -> tuple[Path, Path, Path, Path]:
    workspace = Path.cwd().resolve(strict=True)
    policy_root = contained_child(workspace, "policy", must_exist=True)
    artifact_dir = contained_child(workspace, ARTIFACT_DIR_NAME, must_exist=True)
    raw = contained_child(artifact_dir, "raw-result.json", must_exist=True)
    schemas_dir = contained_child(policy_root, "schemas", must_exist=True)
    schema = contained_child(schemas_dir, "semantic-judge-result.schema.json", must_exist=True)
    summary = contained_child(artifact_dir, "summary.md", must_exist=False)
    normalized = contained_child(artifact_dir, "result.normalized.json", must_exist=False)
    return raw, schema, summary, normalized


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def semantic_errors(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    verdict = result.get("verdict")
    findings = result.get("findings", [])
    context = result.get("context", {})
    reviewer_action = result.get("reviewer_action")
    recommended = result.get("recommended_outcome", {})
    outcome_action = recommended.get("action")
    priority = recommended.get("priority")
    blocking = [item for item in findings if item.get("severity") == "blocking"]

    if verdict == "PASS":
        if findings:
            errors.append("PASS must not contain findings")
        if context.get("sufficient") is not True:
            errors.append("PASS requires context.sufficient=true")
        if reviewer_action != "NONE":
            errors.append("PASS requires reviewer_action=NONE")
        if outcome_action != "KEEP":
            errors.append("PASS requires recommended_outcome.action=KEEP")
        if priority != "none":
            errors.append("PASS requires recommended_outcome.priority=none")

    elif verdict == "REVIEW":
        if not findings and not context.get("limitations"):
            errors.append("REVIEW requires a finding or context limitation")
        if blocking:
            errors.append("REVIEW must not contain blocking findings")
        if reviewer_action not in REVIEW_ACTIONS:
            errors.append("REVIEW requires a non-blocking actionable reviewer_action")
        if outcome_action not in REVIEW_OUTCOMES:
            errors.append("REVIEW requires recommended_outcome.action to be SIMPLIFY, CHANGE, or ESCALATE")
        if priority not in REVIEW_PRIORITIES:
            errors.append("REVIEW requires recommended_outcome.priority to be consider or before_merge")
        if not findings and context.get("limitations"):
            if reviewer_action != "HUMAN_DECISION_REQUIRED":
                errors.append("context-only REVIEW requires reviewer_action=HUMAN_DECISION_REQUIRED")
            if outcome_action != "ESCALATE":
                errors.append("context-only REVIEW requires recommended_outcome.action=ESCALATE")

    elif verdict == "FAIL":
        if not blocking:
            errors.append("FAIL requires at least one blocking finding")
        if reviewer_action != "CHANGE_REQUIRED":
            errors.append("FAIL requires reviewer_action=CHANGE_REQUIRED")
        if outcome_action != "CHANGE":
            errors.append("FAIL requires recommended_outcome.action=CHANGE")
        if priority != "required_before_merge":
            errors.append("FAIL requires recommended_outcome.priority=required_before_merge")

    for index, finding in enumerate(findings):
        recommendation = finding.get("recommendation", {})
        if recommendation.get("action") == "MOVE" and recommendation.get("target_layer") == "human_review":
            errors.append(f"finding[{index}] MOVE recommendation cannot target human_review; use ESCALATE")

    return errors


def render_summary(
    status: str,
    result: dict[str, Any] | None,
    errors: list[str],
    judge_exit_code: int | None,
) -> str:
    lines = ["## Semantic governance", ""]
    if status == "INVALID":
        lines.extend(
            [
                "**Result:** INVALID",
                "",
                "The semantic judge did not produce a valid governed result. Judge execution or result-contract failures fail this check even while semantic PASS/REVIEW/FAIL verdicts remain report-only.",
            ]
        )
        if judge_exit_code not in (None, 0):
            lines.append(f"- Copilot CLI exit code: `{judge_exit_code}`")
        for error in errors:
            lines.append(f"- {error}")
        return "\n".join(lines) + "\n"

    assert result is not None
    verdict = result["verdict"]
    assessment = result["assessment"]
    outcome = result["recommended_outcome"]
    lines.extend(
        [
            f"**Result:** {verdict} (report-only)",
            f"**Reviewer action:** {result['reviewer_action']}",
            "",
            result["summary"],
            "",
            "### Assessment",
            "",
            f"**What changed:** {assessment['what_changed']}",
            "",
            f"**Why it matters:** {assessment['why_it_matters']}",
            "",
            f"**Risk / impact:** {assessment['risk']}",
            "",
            f"**Context sufficient:** {'yes' if result['context']['sufficient'] else 'no'}",
        ]
    )
    for limitation in result["context"]["limitations"]:
        lines.append(f"- Context limitation: {limitation}")

    findings = result["findings"]
    if findings:
        lines.extend(["", "### Findings", ""])
        for index, finding in enumerate(findings, start=1):
            lines.append(f"#### {index}. {finding['principle']} — {finding['severity']}")
            lines.append(f"- **Category:** {finding['category']}")
            lines.append(f"- **Path:** `{finding['path']}`")
            lines.append(f"- **Why:** {finding['reason']}")
            rec = finding["recommendation"]
            lines.append(f"- **Recommendation:** {rec['action']} → {rec['target_layer']}")
            lines.append(f"  - {rec['suggestion']}")
            for evidence in finding["evidence"]:
                excerpt = evidence["excerpt"].replace("\n", " ").strip()
                lines.append(f"  - Evidence ({evidence['version']}): `{excerpt}`")
    else:
        lines.extend(["", "No semantic findings."])

    lines.extend(
        [
            "",
            "### Recommended outcome",
            "",
            f"- **Action:** {outcome['action']}",
            f"- **Priority:** {outcome['priority']}",
            f"- **Suggested change:** {outcome['suggested_change']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["report-only", "enforce"], required=True)
    parser.add_argument("--judge-exit-code", type=int)
    args = parser.parse_args()

    raw_path, schema_path, summary_path, normalized_path = fixed_paths()
    schema = load_json(schema_path)
    result: dict[str, Any] | None = None
    errors: list[str] = []

    if args.judge_exit_code not in (None, 0):
        errors.append(f"Copilot CLI judge execution failed with exit code {args.judge_exit_code}")

    try:
        loaded = load_json(raw_path)
        if not isinstance(loaded, dict):
            errors.append("judge output must be one JSON object")
        else:
            result = loaded
    except Exception as exc:
        errors.append(f"unable to parse judge JSON: {exc}")

    if result is not None:
        validator = Draft202012Validator(schema)
        schema_errors = sorted(
            validator.iter_errors(result), key=lambda err: list(err.absolute_path)
        )
        for error in schema_errors:
            path = "$" + "".join(
                f"[{part}]" if isinstance(part, int) else f".{part}"
                for part in error.absolute_path
            )
            errors.append(f"{path}: {error.message}")
        if not schema_errors:
            errors.extend(semantic_errors(result))

    status = "INVALID" if errors else result["verdict"]
    summary_path.write_text(
        render_summary(status, result if not errors else None, errors, args.judge_exit_code),
        encoding="utf-8",
    )

    if result is not None and not errors:
        normalized_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"semantic_verdict={result['verdict']}")
    if args.mode == "enforce" and result["verdict"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
