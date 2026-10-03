#!/usr/bin/env python3
"""Build Promptfoo inputs for repository-local behavioral evals.

Expected values remain in Promptfoo assertions. The provider receives only bounded contract text,
the scenario, and observable field names; it never resolves repository file paths.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ARTIFACT_DIR = ".aya-repository-evals"
MAX_CONTRACT_CHARS = 80000
MAX_PROMPTFOO_ARG_BYTES = 96 * 1024
SAFE_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SKILL_REFERENCE_RE = re.compile(r"(?P<path>(?:[A-Za-z0-9._-]+/)+SKILL\.md)")


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_repo_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise RuntimeError("path must be a non-empty relative string")

    logical = PurePosixPath(relative)
    if logical.is_absolute() or not logical.parts:
        raise RuntimeError(f"path must be repository-relative: {relative}")
    if any(
        part in {"", ".", ".."} or not SAFE_PATH_SEGMENT_RE.fullmatch(part)
        for part in logical.parts
    ):
        raise RuntimeError(f"path contains disallowed segment: {relative}")

    root_abs = os.path.abspath(root)
    candidate = os.path.abspath(os.path.join(root_abs, *logical.parts))
    if os.path.commonpath([root_abs, candidate]) != root_abs:
        raise RuntimeError(f"path escapes target repository: {relative}")

    resolved = Path(candidate).resolve()
    root_resolved = Path(root_abs).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise RuntimeError(f"path resolves outside target repository: {relative}") from exc
    return resolved


def read_bounded(path: Path, limit: int = 30000) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if len(text) > limit:
        raise RuntimeError(f"behavioral contract file exceeds {limit} characters: {path}")
    return text


def frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("name")
    return value.strip() if isinstance(value, str) and value.strip() else None


def configured_root(target_root: Path, manifest: dict[str, Any], section: str) -> Path:
    configured = manifest.get(section, {}).get("path")
    if not isinstance(configured, str) or not configured.strip():
        raise RuntimeError(f"governance manifest is missing {section}.path")
    directory = safe_repo_path(target_root, configured)
    if not directory.is_dir():
        raise RuntimeError(f"declared {section} directory does not exist: {configured}")
    return directory


def discover_agents(target_root: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    directory = configured_root(target_root, manifest, "agents")
    agents: dict[str, Path] = {}
    for path in sorted(directory.rglob("*.md")):
        resolved = path.resolve()
        try:
            resolved.relative_to(directory)
        except ValueError as exc:
            raise RuntimeError(f"agent path resolves outside declared agents.path: {path}") from exc
        name = frontmatter_name(resolved)
        if not name:
            continue
        if name in agents:
            raise RuntimeError(f"duplicate agent frontmatter name {name!r}: {agents[name]} and {resolved}")
        agents[name] = resolved
    return agents


def build_effective_contract(
    target_root: Path,
    manifest: dict[str, Any],
    agent_file: Path,
) -> str:
    skills_root = configured_root(target_root, manifest, "skills")
    agent_text = read_bounded(agent_file)
    chunks: list[str] = []

    repo_instructions = safe_repo_path(target_root, ".github/copilot-instructions.md")
    if repo_instructions.exists():
        if not repo_instructions.is_file():
            raise RuntimeError(".github/copilot-instructions.md is not a regular file")
        chunks.append(
            "--- repository instructions: .github/copilot-instructions.md ---\n"
            + read_bounded(repo_instructions)
        )

    agent_relative = agent_file.relative_to(target_root.resolve()).as_posix()
    chunks.append(f"--- agent: {agent_relative} ---\n{agent_text}")

    referenced: list[Path] = []
    for match in SKILL_REFERENCE_RE.finditer(agent_text):
        relative = match.group("path")
        skill_file = safe_repo_path(target_root, relative)
        try:
            skill_file.relative_to(skills_root)
        except ValueError as exc:
            configured = manifest.get("skills", {}).get("path")
            raise RuntimeError(
                f"agent references skill outside declared skills.path {configured!r}: {relative}"
            ) from exc
        if not skill_file.is_file():
            raise RuntimeError(f"agent references missing skill: {relative}")
        if skill_file not in referenced:
            referenced.append(skill_file)

    for skill_file in referenced:
        relative = skill_file.relative_to(target_root.resolve()).as_posix()
        chunks.append(f"--- referenced skill: {relative} ---\n{read_bounded(skill_file)}")

    contract = "\n\n".join(chunks)
    if len(contract) > MAX_CONTRACT_CHARS:
        raise RuntimeError(
            f"effective repository eval contract exceeds {MAX_CONTRACT_CHARS} characters"
        )
    return contract


def load_cases(policy_root: Path, target_root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    eval_dir = safe_repo_path(target_root, ".agent/evals")
    schema = load_json(policy_root / "schemas" / "repository-eval.schema.json")
    validator = Draft202012Validator(schema)
    agents = discover_agents(target_root, manifest)

    discovered = sorted([*eval_dir.glob("*.yaml"), *eval_dir.glob("*.yml")]) if eval_dir.is_dir() else []
    files: list[Path] = []
    for path in discovered:
        logical = path.relative_to(target_root).as_posix()
        resolved = safe_repo_path(target_root, logical)
        try:
            resolved.relative_to(eval_dir)
        except ValueError as exc:
            raise RuntimeError(
                f"repository eval file resolves outside .agent/evals: {logical}"
            ) from exc
        if not resolved.is_file():
            raise RuntimeError(f"repository eval path is not a regular file: {logical}")
        files.append(resolved)

    cases: list[dict[str, Any]] = []
    seen_ids: dict[str, str] = {}

    for path in files:
        try:
            documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except yaml.YAMLError as exc:
            raise RuntimeError(f"unable to parse repository eval file {path}: {exc}") from exc

        for index, case in enumerate(documents, start=1):
            if case is None:
                continue
            errors = sorted(validator.iter_errors(case), key=lambda error: list(error.absolute_path))
            if errors:
                rendered = "; ".join(
                    f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
                    for error in errors
                )
                raise RuntimeError(f"invalid repository eval {path.name} document {index}: {rendered}")

            case_id = case["id"]
            if case_id in seen_ids:
                raise RuntimeError(
                    f"duplicate repository eval id {case_id}: {seen_ids[case_id]} and {path.name}"
                )
            seen_ids[case_id] = path.name

            agent_name = case["agent"]
            agent_file = agents.get(agent_name)
            if not agent_file:
                raise RuntimeError(f"repository eval {case_id} references unknown agent {agent_name!r}")

            cases.append(
                {
                    **case,
                    "contract": build_effective_contract(target_root, manifest, agent_file),
                }
            )

    return cases


def javascript_assertion(case_id: str, expected: dict[str, bool]) -> str:
    expected_states = {key: ("YES" if value else "NO") for key, value in expected.items()}
    expected_json = json.dumps(expected_states, sort_keys=True, separators=(",", ":"))
    case_json = json.dumps(case_id)
    return (
        "(() => { "
        "const r = JSON.parse(output); "
        f"const expected = {expected_json}; "
        "const obs = r && r.observations && typeof r.observations === 'object' ? r.observations : {}; "
        "const keys = Object.keys(expected).sort(); "
        "const actualKeys = Object.keys(obs).sort(); "
        "const mismatches = []; "
        f"if (r.eval_id !== {case_json}) mismatches.push('eval_id expected {case_id} actual ' + String(r.eval_id)); "
        "if (JSON.stringify(keys) !== JSON.stringify(actualKeys)) "
        "mismatches.push('observable keys expected ' + JSON.stringify(keys) + ' actual ' + JSON.stringify(actualKeys)); "
        "for (const key of keys) { "
        "if (obs[key] !== expected[key]) mismatches.push(key + ' expected ' + expected[key] + ' actual ' + String(obs[key])); "
        "} "
        "return {pass: mismatches.length === 0, score: mismatches.length === 0 ? 1 : 0, "
        "reason: mismatches.length === 0 ? 'All repository behavioral expectations matched' : mismatches.join('; ')}; "
        "})()"
    )


def build_promptfoo_assets(policy_root: Path, target_root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load_yaml(safe_repo_path(target_root, ".agent/governance.yaml"))
    if not isinstance(manifest, dict):
        raise RuntimeError("target governance manifest must be an object")

    enabled = manifest.get("validation", {}).get("repository_evals") is True
    cases = load_cases(policy_root, target_root, manifest)
    if enabled and not cases:
        raise RuntimeError("repository_evals is true but .agent/evals contains no eval cases")

    output_dir.mkdir(parents=True, exist_ok=True)
    promptfoo_cases: list[dict[str, Any]] = []

    for case in cases:
        observable_fields = list(case["expect"].keys())
        payload = {
            "eval_id": case["id"],
            "contract": case["contract"],
            "scenario": case["scenario"],
            "observable_fields": observable_fields,
        }
        serialized_payload = json.dumps(payload, separators=(",", ":"))
        payload_bytes = len(serialized_payload.encode("utf-8"))
        if payload_bytes > MAX_PROMPTFOO_ARG_BYTES:
            raise RuntimeError(
                f"repository eval {case['id']} serialized payload is {payload_bytes} bytes; "
                f"maximum is {MAX_PROMPTFOO_ARG_BYTES} bytes"
            )

        promptfoo_cases.append(
            {
                "description": f"{case['id']}: {case['category']}",
                "vars": {"case_payload": serialized_payload},
                "assert": [
                    {
                        "type": "javascript",
                        "value": javascript_assertion(case["id"], case["expect"]),
                    }
                ],
            }
        )

    config = {
        "description": "Aya repository-local agent behavioral evals",
        "prompts": ["{{case_payload}}"],
        "providers": [
            {
                "id": "exec:python ../policy/scripts/repository_eval_copilot_provider.py",
                "label": "copilot-luna-repository-agent-eval",
            }
        ],
        "defaultTest": {
            "assert": [
                {
                    "type": "is-json",
                    "value": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["eval_id", "decision", "reason", "observations"],
                        "properties": {
                            "eval_id": {"type": "string", "minLength": 1},
                            "decision": {
                                "type": "string",
                                "minLength": 1,
                            },
                            "reason": {"type": "string", "minLength": 1},
                            "observations": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "string",
                                    "enum": ["YES", "NO", "UNSPECIFIED"],
                                },
                            },
                        },
                    },
                }
            ]
        },
        "tests": ["file://cases.yaml"],
        "evaluateOptions": {"maxConcurrency": 1},
    }

    (output_dir / "promptfooconfig.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False, width=120),
        encoding="utf-8",
    )
    (output_dir / "cases.yaml").write_text(
        yaml.safe_dump(promptfoo_cases, sort_keys=False, width=120),
        encoding="utf-8",
    )
    metadata = {
        "enabled": enabled,
        "case_count": len(cases),
        "agents": sorted({case["agent"] for case in cases}),
        "case_ids": [case["id"] for case in cases],
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy-root", default="policy")
    parser.add_argument("--target-root", default="target")
    parser.add_argument("--output-dir", default=ARTIFACT_DIR)
    args = parser.parse_args()

    metadata = build_promptfoo_assets(
        Path(args.policy_root).resolve(),
        Path(args.target_root).resolve(),
        Path(args.output_dir).resolve(),
    )
    print(f"repository_evals_enabled={'true' if metadata['enabled'] else 'false'}")
    print(f"repository_eval_cases={metadata['case_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
