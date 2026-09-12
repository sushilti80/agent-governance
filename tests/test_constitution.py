from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

POLICY_ROOT = Path(__file__).resolve().parents[1]
CHECKER = POLICY_ROOT / "scripts" / "governance_check.py"
EXPECTED_NAMES = {
    "AGP-001": "outcome_first",
    "AGP-002": "instruction_once",
    "AGP-003": "repository_is_truth",
    "AGP-004": "minimum_necessary_instruction",
    "AGP-005": "bounded_autonomy",
    "AGP-006": "deterministic_before_agentic",
    "AGP-007": "validate_after_mutation",
    "AGP-008": "bounded_delegation",
    "AGP-009": "learning_propose_only",
    "AGP-010": "evidence_before_learning",
    "AGP-011": "smallest_correct_layer",
    "AGP-012": "measurable_evolution",
    "AGP-013": "coherent_behavioral_contract",
    "AGP-014": "authority_non_expansion",
    "AGP-015": "role_separation",
    "AGP-016": "stop_or_escalate",
}


class ConstitutionRegressionTests(unittest.TestCase):
    def load_principles(self) -> dict[str, dict[str, str]]:
        data = yaml.safe_load((POLICY_ROOT / "principles" / "agent-design.yaml").read_text(encoding="utf-8"))
        return data["principles"]

    def test_constitution_has_exact_required_principles(self) -> None:
        principles = self.load_principles()
        self.assertEqual(set(principles), set(EXPECTED_NAMES))
        for principle_id, expected_name in EXPECTED_NAMES.items():
            with self.subTest(principle_id=principle_id):
                self.assertEqual(principles[principle_id]["name"], expected_name)
                self.assertEqual(principles[principle_id]["severity"], "required")
                self.assertTrue(principles[principle_id]["description"].strip())

    def test_checker_rejects_missing_constitution_principle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            policy_copy = Path(directory) / "policy"
            shutil.copytree(POLICY_ROOT, policy_copy, ignore=shutil.ignore_patterns(".git"))
            path = policy_copy / "principles" / "agent-design.yaml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            del data["principles"]["AGP-016"]
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(policy_copy / "scripts" / "governance_check.py"),
                    "--policy-root",
                    str(policy_copy),
                    "--target-root",
                    str(policy_copy),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGP-016", result.stdout)

    def test_checker_rejects_optional_constitution_principle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            policy_copy = Path(directory) / "policy"
            shutil.copytree(POLICY_ROOT, policy_copy, ignore=shutil.ignore_patterns(".git"))
            path = policy_copy / "principles" / "agent-design.yaml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["principles"]["AGP-014"]["severity"] = "recommended"
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(policy_copy / "scripts" / "governance_check.py"),
                    "--policy-root",
                    str(policy_copy),
                    "--target-root",
                    str(policy_copy),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGP-014", result.stdout)


if __name__ == "__main__":
    unittest.main()
