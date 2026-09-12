#!/usr/bin/env python3
"""Deterministic governance checks for this policy and adopting repositories."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REQUIRED_PRINCIPLES = {f"AGP-{n:03d}" for n in range(1, 17)}
REQUIRED_GLOBAL_EVALS = {
    "REVIEW-001",
    "FIX-001",
    "SCOPE-001",
    "DELEGATION-001",
    "DELEGATION-002",
    "LEARNING-001",
    "STOP-001",
}
VERSION_RE = re.compile(r"^20[0-9]{2}\.(0[1-9]|1[0-2])\.[0-9]+$")


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def format_validation_path(error: Any) -> str:
    if not error.absolute_path:
        return "$"
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path
    )


def check_version(policy_root: Path, failures: list[str]) -> str | None:
    path = policy_root / "VERSION"
    if not path.is_file():
        fail("policy root is missing VERSION", failures)
        return None
    version = path.read_text(encoding="utf-8").strip()
    if not VERSION_RE.fullmatch(version):
        fail(f"VERSION must use YYYY.MM.PATCH format, found {version!r}", failures)
        return None
    print(f"PASS: canonical governance version is {version}")
    return version


def check_schemas(policy_root: Path, failures: list[str]) -> None:
    schema_dir = policy_root / "schemas"
    if not schema_dir.is_dir():
        fail("policy root is missing schemas/", failures)
        return
    for path in sorted(schema_dir.glob("*.json")):
        try:
            schema = load_json(path)
            Draft202012Validator.check_schema(schema)
            print(f"PASS: valid Draft 2020-12 schema {path.relative_to(policy_root)}")
        except Exception as exc:
            fail(f"invalid schema {path.relative_to(policy_root)}: {exc}", failures)


def check_versioning_contract(policy_root: Path, failures: list[str]) -> None:
    policy_path = policy_root / "principles" / "versioning-policy.yaml"
    schema_path = policy_root / "schemas" / "governance-manifest.schema.json"
    try:
        policy = load_yaml(policy_path)
        schema = load_json(schema_path)
    except Exception as exc:
        fail(f"unable to load versioning contract: {exc}", failures)
        return

    expected = {
        "source": "VERSION",
        "format": "calendar",
        "tag_prefix": "v",
        "compatibility": "exact",
        "immutable_tags": True,
    }
    governance_version = policy.get("governance_version", {}) if isinstance(policy, dict) else {}
    for key, value in expected.items():
        if governance_version.get(key) != value:
            fail(f"versioning policy governance_version.{key} must be {value!r}", failures)

    spec = policy.get("spec_version", {}) if isinstance(policy, dict) else {}
    current = spec.get("current")
    supported = spec.get("supported", [])
    schema_const = schema.get("properties", {}).get("spec_version", {}).get("const")
    if current not in supported:
        fail("current spec_version must be listed as supported", failures)
    if schema_const != current:
        fail(
            f"governance manifest schema spec_version {schema_const!r} does not match versioning policy {current!r}",
            failures,
        )
    if spec.get("breaking_change_requires_increment") is not True:
        fail("versioning policy must require a spec_version increment for breaking changes", failures)

    release = policy.get("release", {}) if isinstance(policy, dict) else {}
    if release.get("changelog_required") is not True:
        fail("versioning policy must require a changelog", failures)
    if release.get("protected_tag_required") is not True:
        fail("versioning policy must require protected release tags", failures)

    if not failures:
        print("PASS: versioning and compatibility contract is internally consistent")


def validate_yaml_against_schema(
    instance_path: Path,
    schema_path: Path,
    policy_root: Path,
    label: str,
    failures: list[str],
) -> Any | None:
    if not instance_path.exists():
        fail(f"missing {label}: {instance_path}", failures)
        return None
    try:
        instance = load_yaml(instance_path)
        schema = load_json(schema_path)
    except Exception as exc:
        fail(f"unable to load {label} {instance_path}: {exc}", failures)
        return None

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.absolute_path))
    if errors:
        for error in errors:
            fail(
                f"{label} {instance_path}: {format_validation_path(error)}: {error.message}",
                failures,
            )
        return None

    try:
        shown = instance_path.relative_to(policy_root)
    except ValueError:
        shown = instance_path
    print(f"PASS: {label} conforms to {schema_path.name}: {shown}")
    return instance


def check_manifest_policy_version(
    manifest: dict[str, Any] | None,
    canonical_version: str | None,
    label: str,
    failures: list[str],
) -> None:
    if not manifest or not canonical_version:
        return
    actual = manifest.get("governance", {}).get("version")
    if actual != canonical_version:
        fail(
            f"{label} policy version mismatch: manifest declares {actual!r}, policy checkout is {canonical_version!r}",
            failures,
        )
    else:
        print(f"PASS: {label} policy version matches {canonical_version}")


def check_target_manifest(
    policy_root: Path,
    target_root: Path,
    canonical_version: str | None,
    failures: list[str],
) -> dict[str, Any] | None:
    manifest = validate_yaml_against_schema(
        target_root / ".agent" / "governance.yaml",
        policy_root / "schemas" / "governance-manifest.schema.json",
        policy_root,
        "governance manifest",
        failures,
    )
    result = manifest if isinstance(manifest, dict) else None
    check_manifest_policy_version(result, canonical_version, "target governance manifest", failures)
    return result


def check_policy_examples(policy_root: Path, canonical_version: str | None, failures: list[str]) -> None:
    example_manifest = validate_yaml_against_schema(
        policy_root / "examples" / ".agent" / "governance.yaml",
        policy_root / "schemas" / "governance-manifest.schema.json",
        policy_root,
        "example governance manifest",
        failures,
    )
    check_manifest_policy_version(
        example_manifest if isinstance(example_manifest, dict) else None,
        canonical_version,
        "example governance manifest",
        failures,
    )

    examples = [
        (
            policy_root / "examples" / "agents" / "example-agent.yaml",
            policy_root / "schemas" / "agent.schema.json",
            "example agent metadata",
        ),
        (
            policy_root / "examples" / "skills" / "example-skill.yaml",
            policy_root / "schemas" / "skill.schema.json",
            "example skill metadata",
        ),
    ]
    examples.extend(
        (
            path,
            policy_root / "schemas" / "learning-record.schema.json",
            "example LearningRecord",
        )
        for path in sorted((policy_root / "examples" / "learning").glob("*.yaml"))
    )
    for instance_path, schema_path, label in examples:
        validate_yaml_against_schema(instance_path, schema_path, policy_root, label, failures)


def check_target_learning_records(policy_root: Path, target_root: Path, failures: list[str]) -> None:
    candidates: set[Path] = set()
    for directory in (target_root / ".agent" / "learning", target_root / "learning"):
        if directory.is_dir():
            candidates.update(directory.rglob("*.yaml"))
    for path in sorted(candidates):
        validate_yaml_against_schema(
            path,
            policy_root / "schemas" / "learning-record.schema.json",
            policy_root,
            "LearningRecord",
            failures,
        )


def check_principles(policy_root: Path, failures: list[str]) -> None:
    path = policy_root / "principles" / "agent-design.yaml"
    try:
        policy = load_yaml(path)
    except Exception as exc:
        fail(f"unable to load agent design principles: {exc}", failures)
        return
    principles = policy.get("principles", {}) if isinstance(policy, dict) else {}
    found = set(principles) if isinstance(principles, dict) else set()
    missing = REQUIRED_PRINCIPLES - found
    if missing:
        fail(f"missing design principles: {sorted(missing)}", failures)
        return
    non_required = sorted(
        principle_id
        for principle_id in REQUIRED_PRINCIPLES
        if not isinstance(principles.get(principle_id), dict)
        or principles[principle_id].get("severity") != "required"
    )
    if non_required:
        fail(f"design principles must remain required: {non_required}", failures)
        return
    print("PASS: AGP-001..AGP-016 present and required")


def check_learning_firewall(policy_root: Path, failures: list[str]) -> None:
    path = policy_root / "principles" / "learning-policy.yaml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    required = ["mode: propose-only", "runtime_self_modification: prohibited", "promotion_firewall: true"]
    missing = [token for token in required if token not in text]
    for token in missing:
        fail(f"learning firewall missing '{token}'", failures)
    if not missing:
        print("PASS: learning promotion firewall declared")


def prompt_candidates(target_root: Path, manifest: dict[str, Any] | None) -> list[Path]:
    candidates: set[Path] = set()
    copilot = target_root / ".github" / "copilot-instructions.md"
    if copilot.is_file():
        candidates.add(copilot)

    if manifest:
        for key in ("agents", "skills"):
            configured = manifest.get(key, {}).get("path")
            if not configured:
                continue
            directory = target_root / configured
            if directory.is_dir():
                for path in directory.rglob("*"):
                    if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
                        candidates.add(path)
    return sorted(candidates)


def lint_prompts(target_root: Path, manifest: dict[str, Any] | None) -> None:
    warning_patterns = {
        "generic thoroughness": re.compile(r"\b(be|remain)\s+thorough\b", re.I),
        "unbounded persistence": re.compile(r"continue\s+until\s+(fully|completely|certain|confident)", re.I),
        "full picture instruction": re.compile(r"full\s+picture", re.I),
    }
    candidates = prompt_candidates(target_root, manifest)
    for path in candidates:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in warning_patterns.items():
            if pattern.search(text):
                print(
                    f"WARN: {path.relative_to(target_root)}: possible {name}; "
                    "justify with an eval if intentional"
                )
    print(f"PASS: prompt lint scanned {len(candidates)} declared agent/skill file(s)")


def check_eval_ids(policy_root: Path, failures: list[str]) -> None:
    ids: dict[str, Path] = {}
    for path in sorted((policy_root / "evals" / "global").rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        matches = list(re.finditer(r"^id:\s*([A-Z]+-[0-9]{3})\s*$", text, re.MULTILINE))
        if not matches:
            fail(f"global eval is missing an id: {path.relative_to(policy_root)}", failures)
        for match in matches:
            eid = match.group(1)
            if eid in ids:
                fail(f"duplicate eval id {eid}: {ids[eid]} and {path}", failures)
            ids[eid] = path
    missing = REQUIRED_GLOBAL_EVALS - ids.keys()
    if missing:
        fail(f"missing global evals: {sorted(missing)}", failures)
    else:
        print(f"PASS: required global eval catalog present ({len(ids)} cases)")


def check_release_metadata(policy_root: Path, canonical_version: str | None, failures: list[str]) -> None:
    if not canonical_version:
        return
    changelog = policy_root / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8") if changelog.is_file() else ""
    pattern = rf"^## \[{re.escape(canonical_version)}\] - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$"
    if not re.search(pattern, text, re.MULTILINE):
        fail(f"CHANGELOG.md must contain a dated entry for {canonical_version}", failures)
    else:
        print(f"PASS: CHANGELOG contains release entry for {canonical_version}")


def check_workflow_contract(policy_root: Path, failures: list[str]) -> None:
    workflow = policy_root / ".github" / "workflows" / "agent-governance.yml"
    text = workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
    if re.search(r"v20[0-9]{2}\.[0-9]{2}\.[0-9]+", text):
        fail("agent-governance workflow must not hard-code a governance release version", failures)
    if "GOVERNANCE_RELEASE_REF" in text or "GOVERNANCE_REPOSITORY" in text:
        fail("agent-governance workflow must not maintain duplicate governance source constants", failures)
    if "governance_ref" in text:
        fail("agent-governance workflow must not accept a duplicate governance_ref input", failures)
    required = [
        "repository: ${{ job.workflow_repository }}",
        "ref: ${{ job.workflow_sha }}",
    ]
    for token in required:
        if token not in text:
            fail(f"agent-governance workflow must derive policy source from job identity: missing {token}", failures)
    if not failures:
        print("PASS: reusable workflow derives policy checkout from its exact defining workflow SHA")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy-root", default=".", help="Root containing central principles, schemas, evals, and scripts")
    parser.add_argument("--target-root", default=".", help="Root of the repository being governed")
    args = parser.parse_args()

    policy_root = Path(args.policy_root).resolve()
    target_root = Path(args.target_root).resolve()
    failures: list[str] = []

    canonical_version = check_version(policy_root, failures)
    check_schemas(policy_root, failures)
    check_versioning_contract(policy_root, failures)
    check_principles(policy_root, failures)
    check_learning_firewall(policy_root, failures)
    check_eval_ids(policy_root, failures)
    check_policy_examples(policy_root, canonical_version, failures)
    check_release_metadata(policy_root, canonical_version, failures)
    check_workflow_contract(policy_root, failures)
    manifest = check_target_manifest(policy_root, target_root, canonical_version, failures)
    check_target_learning_records(policy_root, target_root, failures)
    lint_prompts(target_root, manifest)

    if failures:
        print(f"\nGovernance validation failed with {len(failures)} issue(s).")
        return 1
    print("\nGovernance validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
