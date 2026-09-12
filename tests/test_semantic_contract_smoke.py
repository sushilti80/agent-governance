from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

POLICY_ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = POLICY_ROOT / "scripts" / "check_changed_agent_files.py"
WORKFLOW = POLICY_ROOT / ".github" / "workflows" / "agent-governance.yml"


class SemanticContractSmokeTests(unittest.TestCase):
    def classify(self, *paths: str) -> str:
        proc = subprocess.run(
            [sys.executable, str(CLASSIFIER), *paths],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def test_semantic_contract_files_request_smoke_execution(self) -> None:
        for path in (
            ".github/workflows/agent-governance.yml",
            "principles/agent-design.yaml",
            "principles/semantic-review-policy.yaml",
            "schemas/semantic-judge-result.schema.json",
            "scripts/build_semantic_context.py",
            "scripts/build_semantic_prompt.py",
            "scripts/validate_semantic_result.py",
        ):
            with self.subTest(path=path):
                output = self.classify(path)
                self.assertIn("highest_risk=R4", output)
                self.assertIn("semantic_contract_changed=true", output)

    def test_normal_behavior_change_does_not_claim_contract_change(self) -> None:
        output = self.classify(".github/agents/storage.agent.md")
        self.assertIn("semantic_review_required=true", output)
        self.assertIn("semantic_contract_changed=false", output)

    def test_docs_only_change_requests_neither_semantic_path(self) -> None:
        output = self.classify("docs/SEMANTIC-GOVERNANCE.md")
        self.assertIn("semantic_review_required=false", output)
        self.assertIn("semantic_contract_changed=false", output)

    def test_workflow_reuses_semantic_job_for_contract_smoke(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("semantic_contract_changed: ${{ steps.classify.outputs.semantic_contract_changed }}", workflow)
        self.assertIn("semantic_review_required == 'true' || needs.classify-change.outputs.semantic_contract_changed == 'true'", workflow)
        self.assertIn("Build semantic contract smoke context", workflow)
        self.assertIn("semantic-contract-smoke-base", workflow)
        self.assertIn("python policy/scripts/build_semantic_prompt.py", workflow)
        self.assertIn("python policy/scripts/validate_semantic_result.py", workflow)


if __name__ == "__main__":
    unittest.main()
