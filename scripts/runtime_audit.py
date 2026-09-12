#!/usr/bin/env python3
"""Report-only runtime audit for agent delegation, progress, and stopping behavior."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    observed: int
    allowed: int


def resolve_workspace_path(
    raw_path: str | Path,
    workspace_root: Path,
    *,
    must_exist: bool,
) -> Path:
    """Resolve a CLI-supplied path while preventing escape from the workspace root."""
    root = workspace_root.resolve(strict=True)
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes workspace root: {raw_path}") from exc
    if must_exist and not resolved.is_file():
        raise ValueError(f"path is not a file: {raw_path}")
    return resolved


def read_yaml_within_workspace(raw_path: str | Path, workspace_root: Path) -> Any:
    path = resolve_workspace_path(raw_path, workspace_root, must_exist=True)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_json_within_workspace(raw_path: str | Path, workspace_root: Path) -> Any:
    path = resolve_workspace_path(raw_path, workspace_root, must_exist=True)
    return json.loads(path.read_text(encoding="utf-8"))


def write_text_within_workspace(raw_path: str | Path, workspace_root: Path, content: str) -> None:
    path = resolve_workspace_path(raw_path, workspace_root, must_exist=False)
    path.write_text(content, encoding="utf-8")


def validate_trace(trace: Any, schema: dict[str, Any]) -> list[str]:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(trace),
        key=lambda e: list(e.absolute_path),
    )
    result = []
    for error in errors:
        path = "$" + "".join(
            f"[{p}]" if isinstance(p, int) else f".{p}"
            for p in error.absolute_path
        )
        result.append(f"{path}: {error.message}")

    if not isinstance(trace, dict):
        return result
    events = trace.get("events")
    if not isinstance(events, list):
        return result

    seqs: list[int] = []
    all_real_integers = True
    for event in events:
        if not isinstance(event, dict):
            all_real_integers = False
            break
        seq = event.get("seq")
        if isinstance(seq, bool) or not isinstance(seq, int):
            all_real_integers = False
            break
        seqs.append(seq)

    if all_real_integers:
        if seqs and seqs != sorted(seqs):
            result.append("$.events: seq values must be monotonically increasing")
        if len(seqs) != len(set(seqs)):
            result.append("$.events: seq values must be unique")
    return result


def audit(trace: dict[str, Any], policy: dict[str, Any]) -> tuple[dict[str, int | None], list[Finding]]:
    active: set[str] = set()
    total_delegations = max_depth = max_parallel = total_actions = 0
    repeated_delegations = repeated_actions = repeated_validators = actions_after_success = 0
    success_reached = False
    progress_epoch = 0
    delegation_seen: dict[str, int] = {}
    action_seen: dict[str, int] = {}
    validator_seen: set[str] = set()

    for event in trace["events"]:
        etype = event["type"]
        if etype == "success":
            success_reached = True
            continue
        if etype in {"delegation_start", "action"} and success_reached:
            actions_after_success += 1
        if etype == "delegation_start":
            total_delegations += 1
            max_depth = max(max_depth, event["depth"])
            active.add(event["delegate_id"])
            max_parallel = max(max_parallel, len(active))
            key = event["equivalence_key"]
            if delegation_seen.get(key) == progress_epoch:
                repeated_delegations += 1
            delegation_seen[key] = progress_epoch
            continue
        if etype == "delegation_end":
            active.discard(event["delegate_id"])
            if event["evidence_delta"]:
                progress_epoch += 1
            continue
        if etype == "action":
            total_actions += 1
            key = event["equivalence_key"]
            made_progress = event["evidence_delta"] or event["state_change"]
            if action_seen.get(key) == progress_epoch and not made_progress:
                repeated_actions += 1
            action_seen[key] = progress_epoch

            if event["category"] == "validator":
                if key in validator_seen and not event["state_change"]:
                    repeated_validators += 1
                validator_seen.add(key)

            if event["state_change"]:
                validator_seen.clear()
            if made_progress:
                progress_epoch += 1

    metrics: dict[str, int | None] = {
        "total_delegations": total_delegations,
        "max_depth": max_depth,
        "max_parallel_agents": max_parallel,
        "total_actions": total_actions,
        "repeated_equivalent_delegations_without_progress": repeated_delegations,
        "repeated_equivalent_actions_without_progress": repeated_actions,
        "repeated_validators_without_state_change": repeated_validators,
        "actions_after_success": actions_after_success,
        "total_tokens": trace.get("usage", {}).get("total_tokens"),
    }
    limits = {
        "AGP-RUNTIME-DEPTH": ("max_depth", policy["delegation"]["max_depth"]),
        "AGP-RUNTIME-PARALLEL": ("max_parallel_agents", policy["delegation"]["max_parallel_agents"]),
        "AGP-RUNTIME-DELEGATIONS": ("total_delegations", policy["delegation"]["max_total_delegations"]),
        "AGP-RUNTIME-REPEAT-DELEGATION": (
            "repeated_equivalent_delegations_without_progress",
            policy["delegation"]["repeated_equivalent_objective_without_progress"],
        ),
        "AGP-RUNTIME-REPEAT-ACTION": (
            "repeated_equivalent_actions_without_progress",
            policy["progress"]["repeated_equivalent_action_without_progress"],
        ),
        "AGP-RUNTIME-REPEAT-VALIDATOR": (
            "repeated_validators_without_state_change",
            policy["validation"]["repeated_validator_without_state_change"],
        ),
        "AGP-RUNTIME-POST-SUCCESS": (
            "actions_after_success",
            policy["completion"]["actions_after_success"],
        ),
    }
    findings = []
    for code, (metric_name, allowed) in limits.items():
        observed = metrics[metric_name]
        if isinstance(observed, int) and observed > allowed:
            findings.append(
                Finding(code, metric_name.replace("_", " "), observed, allowed)
            )
    return metrics, findings


def render_markdown(
    trace: dict[str, Any],
    policy: dict[str, Any],
    metrics: dict[str, int | None],
    findings: list[Finding],
) -> str:
    run = trace["run"]
    lines = [
        "# Agent Runtime Governance Audit",
        "",
        f"- Repository: `{run['repository']}`",
        f"- Agent: `{run['agent']}`",
        f"- Task: {run['task']}",
        f"- Outcome: `{trace['outcome']}`",
        f"- Mode: `{policy.get('mode', 'report-only')}`",
        "",
        "## Metrics",
        "",
        "| Metric | Observed |",
        "| --- | ---: |",
    ]
    for name, value in metrics.items():
        lines.append(f"| {name} | {'not reported' if value is None else value} |")
    lines.extend(["", "## Findings", ""])
    if findings:
        lines.extend(
            [
                "| Control | Observation | Allowed |",
                "| --- | ---: | ---: |",
            ]
        )
        for finding in findings:
            lines.append(
                f"| {finding.code}: {finding.message} | "
                f"{finding.observed} | {finding.allowed} |"
            )
    else:
        lines.append("No runtime budget or progress findings detected.")
    lines.extend(["", "## Result", ""])
    if (
        findings
        and trace["outcome"] == "success"
        and policy.get("quality", {}).get("efficiency_is_correctness")
    ):
        lines.append(
            "`FAIL-QUALITY` - correct outcome with governance efficiency violations."
        )
    elif findings:
        lines.append("`FINDINGS` - review before enforcement or release calibration.")
    else:
        lines.append("`PASS` - no configured runtime findings.")
    lines.extend(
        [
            "",
            "Report-only mode does not fail CI unless `--enforce` is explicitly supplied.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace")
    parser.add_argument("--policy", default="principles/runtime-efficiency-policy.yaml")
    parser.add_argument("--schema", default="schemas/agent-run-trace.schema.json")
    parser.add_argument("--output")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    workspace_root = Path.cwd().resolve(strict=True)
    try:
        trace = read_yaml_within_workspace(args.trace, workspace_root)
        policy = read_yaml_within_workspace(args.policy, workspace_root)
        schema = read_json_within_workspace(args.schema, workspace_root)
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"FAIL: unable to load audit input: {exc}")
        return 2

    errors = validate_trace(trace, schema)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 2

    metrics, findings = audit(trace, policy)
    report = render_markdown(trace, policy, metrics, findings)
    if args.output:
        try:
            write_text_within_workspace(
                args.output,
                workspace_root,
                report + "\n",
            )
        except (OSError, ValueError) as exc:
            print(f"FAIL: unable to write audit output: {exc}")
            return 2
    print(report)
    return 1 if args.enforce and findings else 0


if __name__ == "__main__":
    sys.exit(main())
