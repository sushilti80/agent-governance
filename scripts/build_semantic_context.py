#!/usr/bin/env python3
"""Build bounded before/after context for semantic governance."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

MAX_TOTAL_CHARS = 180_000
MAX_FILE_CHARS = 40_000
MAX_DIFF_CHARS = 60_000
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json"}
ARTIFACT_DIR_NAME = ".semantic-judge"
FIXED_SEMANTIC_PREFIXES = (
    ".github/instructions",
    ".github/prompts",
    ".github/agent-memory",
)


def contained_child(base: Path, child_name: str, *, must_exist: bool) -> Path:
    base = base.resolve(strict=True)
    candidate = (base / child_name).resolve(strict=must_exist)
    candidate.relative_to(base)
    return candidate


def workspace_paths() -> tuple[Path, Path]:
    workspace = Path.cwd().resolve(strict=True)
    target = contained_child(workspace, "target", must_exist=True)
    artifact_dir = contained_child(workspace, ARTIFACT_DIR_NAME, must_exist=False)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return target, artifact_dir


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def show(root: Path, ref: str, path: str) -> str | None:
    result = git(root, "show", f"{ref}:{path}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def load_manifest(root: Path, ref: str) -> tuple[str | None, dict[str, Any] | None]:
    raw = show(root, ref, ".agent/governance.yaml")
    if raw is None:
        return None, None
    try:
        data = yaml.safe_load(raw)
    except Exception:
        return raw, None
    return raw, data if isinstance(data, dict) else None


def configured_paths(manifest: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not manifest:
        return None, None
    agent_path = manifest.get("agents", {}).get("path")
    skill_path = manifest.get("skills", {}).get("path")
    return (
        agent_path.rstrip("/") if isinstance(agent_path, str) and agent_path else None,
        skill_path.rstrip("/") if isinstance(skill_path, str) and skill_path else None,
    )


def list_paths(root: Path, ref: str, prefixes: list[str]) -> set[str]:
    found: set[str] = set()
    for prefix in prefixes:
        result = git(root, "ls-tree", "-r", "--name-only", ref, "--", prefix, check=False)
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            path = line.strip()
            if path and Path(path).suffix.lower() in TEXT_SUFFIXES:
                found.add(path)
    return found


def clip(text: str | None, limit: int, label: str, limitations: list[str]) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    limitations.append(f"{label} truncated from {len(text)} to {limit} characters")
    return text[:limit]


def classify_component(path: str, agent_prefixes: set[str], skill_prefixes: set[str]) -> str:
    if path == ".github/copilot-instructions.md" or path.startswith(".github/instructions/"):
        return "repository_instruction"
    if path.startswith(".github/prompts/"):
        return "prompt"
    if path.startswith(".github/agent-memory/"):
        return "memory"
    if any(path == prefix or path.startswith(prefix + "/") for prefix in agent_prefixes):
        return "agent"
    if any(path == prefix or path.startswith(prefix + "/") for prefix in skill_prefixes):
        return "skill"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    args = parser.parse_args()

    root, artifact_dir = workspace_paths()
    output = contained_child(artifact_dir, "context.json", must_exist=False)
    base_sha = args.base_sha
    head_sha = args.head_sha
    limitations: list[str] = []

    base_manifest_raw, base_manifest = load_manifest(root, base_sha)
    head_manifest_raw, head_manifest = load_manifest(root, head_sha)
    base_agent, base_skill = configured_paths(base_manifest)
    head_agent, head_skill = configured_paths(head_manifest)
    agent_prefixes = {p for p in (base_agent, head_agent) if p}
    skill_prefixes = {p for p in (base_skill, head_skill) if p}

    changed_result = git(root, "diff", "--name-only", "--diff-filter=ACMRTD", base_sha, head_sha, "--")
    changed_paths = [p for p in changed_result.stdout.splitlines() if p]

    semantic_changed: list[str] = []
    for path in changed_paths:
        kind = classify_component(path, agent_prefixes, skill_prefixes)
        if kind in {"agent", "skill", "repository_instruction", "prompt", "memory"}:
            semantic_changed.append(path)

    all_component_paths = {
        ".github/copilot-instructions.md",
        *list_paths(root, base_sha, sorted(agent_prefixes | skill_prefixes | set(FIXED_SEMANTIC_PREFIXES))),
        *list_paths(root, head_sha, sorted(agent_prefixes | skill_prefixes | set(FIXED_SEMANTIC_PREFIXES))),
    }
    all_component_paths.discard("")

    ordered_paths: list[str] = []
    seen: set[str] = set()
    for path in semantic_changed + sorted(all_component_paths):
        if path not in seen:
            ordered_paths.append(path)
            seen.add(path)

    components: list[dict[str, Any]] = []
    total_chars = 0
    omitted_paths: list[str] = []
    for path in ordered_paths:
        base_text = show(root, base_sha, path)
        candidate_text = show(root, head_sha, path)
        if base_text is None and candidate_text is None:
            continue

        remaining = max(0, MAX_TOTAL_CHARS - total_chars)
        if remaining == 0:
            omitted_paths.append(path)
            continue

        per_side = min(MAX_FILE_CHARS, max(1, remaining // 2))
        base_clipped = clip(base_text, per_side, f"{path} base", limitations)
        cand_clipped = clip(candidate_text, per_side, f"{path} candidate", limitations)
        total_chars += len(base_clipped or "") + len(cand_clipped or "")

        components.append(
            {
                "path": path,
                "kind": classify_component(path, agent_prefixes, skill_prefixes),
                "changed": path in semantic_changed,
                "base": base_clipped,
                "candidate": cand_clipped,
            }
        )

    if omitted_paths:
        limitations.append(
            f"{len(omitted_paths)} contextual file(s) omitted because the {MAX_TOTAL_CHARS}-character context budget was reached"
        )

    diff_args = ["diff", "--unified=30", base_sha, head_sha, "--", *semantic_changed]
    diff_text = git(root, *diff_args, check=False).stdout if semantic_changed else ""
    diff_text = clip(diff_text, MAX_DIFF_CHARS, "semantic diff", limitations) or ""

    bundle = {
        "schema_version": 1,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "semantic_review_required": bool(semantic_changed),
        "changed_semantic_files": sorted(set(semantic_changed)),
        "manifest": {
            "base": clip(base_manifest_raw, MAX_FILE_CHARS, "base governance manifest", limitations),
            "candidate": clip(head_manifest_raw, MAX_FILE_CHARS, "candidate governance manifest", limitations),
        },
        "components": components,
        "diff": diff_text,
        "context_limitations": limitations,
        "omitted_paths": omitted_paths,
    }

    output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"semantic_review_required={'true' if bundle['semantic_review_required'] else 'false'}")
    print(f"semantic_files={len(bundle['changed_semantic_files'])}")
    print(f"context_components={len(components)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
