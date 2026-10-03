#!/usr/bin/env python3
"""Classify changed files into governance risk bands and semantic/red-team scope."""
from __future__ import annotations

import argparse

R4_PREFIXES = (
    "principles/",
    "schemas/",
    "evals/global/",
    "redteam/",
    ".github/workflows/",
    "scripts/",
    "tests/",
)
R4_FILES = {"VERSION", "requirements-governance.txt"}
R3 = (
    ".github/agents/",
    ".agent/",
    ".github/copilot-instructions.md",
    ".github/instructions/",
    ".github/prompts/",
    ".github/agent-memory/",
)
R2 = (".github/skills/", "skills/")
SEMANTIC_CONTRACT_FILES = {
    ".github/workflows/agent-governance.yml",
    "principles/agent-design.yaml",
    "principles/semantic-review-policy.yaml",
    "schemas/semantic-judge-result.schema.json",
    "scripts/build_semantic_context.py",
    "scripts/build_semantic_prompt.py",
    "scripts/validate_semantic_result.py",
}
REDTEAM_CONTRACT_FILES = {
    ".github/workflows/agent-governance.yml",
    "scripts/build_semantic_context.py",
    "scripts/promptfoo_copilot_provider.py",
    "redteam/promptfooconfig.yaml",
    "redteam/cases.yaml",
}


REPOSITORY_EVAL_CONTRACT_FILES = {
    ".github/workflows/agent-governance.yml",
    "schemas/repository-eval.schema.json",
    "scripts/build_repository_evals.py",
    "scripts/repository_eval_copilot_provider.py",
    "scripts/governance_check.py",
}


def classify(path: str) -> str:
    if path in R4_FILES or any(path.startswith(prefix) for prefix in R4_PREFIXES):
        return "R4"
    if path == ".github/copilot-instructions.md" or any(path.startswith(prefix) for prefix in R3):
        return "R3"
    if any(path.startswith(prefix) for prefix in R2):
        return "R2"
    if path.endswith(".md") or path.startswith("docs/"):
        return "R0"
    return "R1"


def requires_semantic_review(path: str) -> bool:
    return (
        path == ".github/copilot-instructions.md"
        or path.endswith(".agent.md")
        or path.endswith("/SKILL.md")
        or path.startswith(".github/agents/")
        or path.startswith(".github/skills/")
        or path.startswith("skills/")
        or path.startswith(".github/instructions/")
        or path.startswith(".github/prompts/")
        or path.startswith(".github/agent-memory/")
    )


def changes_semantic_contract(path: str) -> bool:
    return path in SEMANTIC_CONTRACT_FILES


def changes_redteam_contract(path: str) -> bool:
    return path in REDTEAM_CONTRACT_FILES or path.startswith("redteam/")


def changes_repository_eval_catalog(path: str) -> bool:
    return path.startswith(".agent/evals/")


def changes_repository_eval_contract(path: str) -> bool:
    return path in REPOSITORY_EVAL_CONTRACT_FILES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()
    rank = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4}
    highest = "R0"
    semantic = False
    semantic_contract = False
    redteam_contract = False
    repository_eval_catalog = False
    repository_eval_contract = False
    for file in args.files:
        risk = classify(file)
        semantic = semantic or requires_semantic_review(file)
        semantic_contract = semantic_contract or changes_semantic_contract(file)
        redteam_contract = redteam_contract or changes_redteam_contract(file)
        repository_eval_catalog = repository_eval_catalog or changes_repository_eval_catalog(file)
        repository_eval_contract = repository_eval_contract or changes_repository_eval_contract(file)
        if rank[risk] > rank[highest]:
            highest = risk
        print(f"{risk}\t{file}")
    print(f"highest_risk={highest}")
    print(f"semantic_review_required={'true' if semantic else 'false'}")
    print(f"semantic_contract_changed={'true' if semantic_contract else 'false'}")
    print(f"redteam_contract_changed={'true' if redteam_contract else 'false'}")
    print(f"repository_eval_catalog_changed={'true' if repository_eval_catalog else 'false'}")
    print(f"repository_eval_contract_changed={'true' if repository_eval_contract else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
