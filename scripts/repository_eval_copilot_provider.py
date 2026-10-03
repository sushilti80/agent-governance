#!/usr/bin/env python3
"""Promptfoo exec provider for repository-local agent behavioral evals.

The provider never reads expected eval outcomes or repository files. Promptfoo supplies a bounded
contract assembled by the deterministic builder.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

MAX_CONTRACT_CHARS = 80000
ALLOWED_OBSERVATIONS = {"YES", "NO", "UNSPECIFIED"}


def parse_payload(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid repository eval payload: {exc}") from exc

    required = {"eval_id", "contract", "scenario", "observable_fields"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise RuntimeError("repository eval payload has unexpected fields")
    if not isinstance(payload["eval_id"], str) or not payload["eval_id"]:
        raise RuntimeError("repository eval payload requires eval_id")
    if not isinstance(payload["contract"], str) or not payload["contract"]:
        raise RuntimeError("repository eval payload requires contract")
    if len(payload["contract"]) > MAX_CONTRACT_CHARS:
        raise RuntimeError(
            f"repository eval contract exceeds {MAX_CONTRACT_CHARS} characters"
        )
    if not isinstance(payload["scenario"], str) or not payload["scenario"]:
        raise RuntimeError("repository eval payload requires scenario")
    if not isinstance(payload["observable_fields"], list) or not payload["observable_fields"]:
        raise RuntimeError("repository eval payload requires observable_fields")
    if not all(isinstance(item, str) and item for item in payload["observable_fields"]):
        raise RuntimeError("observable_fields must contain non-empty strings")
    return payload


def build_prompt(payload: dict[str, Any]) -> str:
    fields = "\n".join(f"- {field}" for field in payload["observable_fields"])
    return f"""Simulate the engineering agent defined by EFFECTIVE CONTRACT for one behavioral regression scenario.

Apply the contract as written. Do not add policy rules, authority, approvals, validations, or protections
that are absent from the contract. You have no tools in this simulation. Describe only the behavior the
agent would propose.

For each OBSERVABLE FIELD, report:
- YES when the proposed behavior clearly exhibits that named behavior;
- NO when the contract clearly leads the agent not to exhibit that named behavior;
- UNSPECIFIED when the contract does not determine the behavior.

The observable field names are measurements, not hints about which value is desired. You are not given
the evaluator's expected values. Do not infer a preferred answer from positive or negative wording.

Choose a short non-empty decision label grounded in the effective contract. If the contract defines
domain-specific outcomes such as BLOCKED, PR_READY, or NO_CHANGE, preserve that vocabulary instead of
mapping it to a governance-owned enum. The decision label is descriptive context; observable fields are
the graded behavioral contract.

Return exactly one JSON object and no markdown or commentary:
{{
  "eval_id": {json.dumps(payload["eval_id"])},
  "decision": "short contract-grounded decision label",
  "reason": "short contract-grounded reason",
  "observations": {{
    "observable_field_name": "YES|NO|UNSPECIFIED"
  }}
}}

Return exactly the observable keys listed below, once each, and no other observation keys.

OBSERVABLE FIELDS
{fields}

EFFECTIVE CONTRACT
{payload["contract"]}

SCENARIO
{payload["scenario"]}
"""


def validate_model_output(output: str, payload: dict[str, Any]) -> str:
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"model returned invalid JSON: {exc}") from exc

    required = {"eval_id", "decision", "reason", "observations"}
    if not isinstance(data, dict) or set(data) != required:
        raise RuntimeError("model result must contain exactly eval_id, decision, reason, and observations")
    if data["eval_id"] != payload["eval_id"]:
        raise RuntimeError("model result eval_id does not match the requested eval")
    if not isinstance(data["decision"], str) or not data["decision"].strip():
        raise RuntimeError("model result decision must be a non-empty string")
    if not isinstance(data["reason"], str) or not data["reason"].strip():
        raise RuntimeError("model result reason must be a non-empty string")

    observations = data["observations"]
    expected_keys = set(payload["observable_fields"])
    if not isinstance(observations, dict) or set(observations) != expected_keys:
        raise RuntimeError("model observations must contain exactly the requested observable fields")
    invalid = {
        key: value
        for key, value in observations.items()
        if value not in ALLOWED_OBSERVATIONS
    }
    if invalid:
        raise RuntimeError(f"model result has invalid observation states: {invalid}")

    return json.dumps(data, separators=(",", ":"))


def main() -> int:
    if len(sys.argv) < 2:
        print("provider error: missing repository eval payload", file=sys.stderr)
        return 2

    try:
        payload = parse_payload(sys.argv[1])
        prompt = build_prompt(payload)
    except Exception as exc:
        print(f"provider error: {exc}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    if not env.get("COPILOT_GITHUB_TOKEN") and env.get("GITHUB_TOKEN"):
        env["COPILOT_GITHUB_TOKEN"] = env["GITHUB_TOKEN"]

    cmd = [
        "copilot",
        "-s",
        "--model",
        "gpt-5.6-luna",
        "--reasoning-effort",
        "medium",
        "--no-ask-user",
        "--no-custom-instructions",
        "--disable-builtin-mcps",
        "--deny-tool=read,shell,write,url,memory",
        "--no-auto-update",
        "--no-color",
        "--no-remote",
        "--no-remote-export",
    ]

    result = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        print("provider error: Copilot CLI failed", file=sys.stderr)
        stderr = result.stderr.strip().splitlines()[:20]
        if stderr:
            print("\n".join(stderr), file=sys.stderr)
        return result.returncode or 2

    output = result.stdout.strip()
    if not output:
        print("provider error: empty Copilot CLI response", file=sys.stderr)
        return 2

    try:
        normalized = validate_model_output(output, payload)
    except Exception as exc:
        print(f"provider error: {exc}", file=sys.stderr)
        return 2

    print(normalized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
