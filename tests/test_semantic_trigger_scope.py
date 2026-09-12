from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

POLICY_ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = POLICY_ROOT / "scripts" / "check_changed_agent_files.py"
CONTEXT_BUILDER = POLICY_ROOT / "scripts" / "build_semantic_context.py"
WORKFLOW = POLICY_ROOT / ".github" / "workflows" / "agent-governance.yml"


class SemanticTriggerScopeTests(unittest.TestCase):
    def classify(self, *paths: str) -> str:
        proc = subprocess.run(
            [sys.executable, str(CLASSIFIER), *paths],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def test_governance_config_is_deterministic_only(self) -> None:
        output = self.classify(".agent/governance.yaml")
        self.assertIn("semantic_review_required=false", output)
        self.assertIn("semantic_contract_changed=false", output)

    def test_consumer_validator_script_is_deterministic_only(self) -> None:
        output = self.classify(".github/scripts/validate-agent-governance.py")
        self.assertIn("semantic_review_required=false", output)
        self.assertIn("semantic_contract_changed=false", output)

    def test_behavioral_surfaces_require_semantic_review(self) -> None:
        for path in (
            ".github/agents/storage.agent.md",
            ".github/skills/storage/SKILL.md",
            ".github/copilot-instructions.md",
            ".github/instructions/terraform.instructions.md",
            ".github/prompts/review.prompt.md",
            ".github/agent-memory/storage/MEMORY.md",
        ):
            with self.subTest(path=path):
                output = self.classify(path)
                self.assertIn("semantic_review_required=true", output)

    def test_consumer_workflow_contract_change_is_suppressed(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('if [ "${{ job.workflow_repository }}" != "${{ github.repository }}" ]; then', workflow)
        self.assertIn("contract=false", workflow)

    def test_context_builder_covers_behavioral_directories_only(self) -> None:
        source = CONTEXT_BUILDER.read_text(encoding="utf-8")
        self.assertIn('".github/instructions"', source)
        self.assertIn('".github/prompts"', source)
        self.assertIn('".github/agent-memory"', source)
        self.assertNotIn('semantic_changed.append(".agent/governance.yaml")', source)


if __name__ == "__main__":
    unittest.main()
