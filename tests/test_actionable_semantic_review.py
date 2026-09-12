from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

POLICY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = POLICY_ROOT / "scripts" / "validate_semantic_result.py"
PROMPT_BUILDER = POLICY_ROOT / "scripts" / "build_semantic_prompt.py"
SCHEMA = POLICY_ROOT / "schemas" / "semantic-judge-result.schema.json"


class ActionableSemanticReviewTests(unittest.TestCase):
    def valid_review(self) -> dict:
        return {
            "schema_version": 2,
            "verdict": "REVIEW",
            "summary": "Authority is preserved, but the same invariant is repeated across layers.",
            "reviewer_action": "CONSIDER_SIMPLIFICATION",
            "context": {"sufficient": True, "limitations": []},
            "assessment": {
                "what_changed": "Authority non-expansion was reinforced in repository, agent, and skill surfaces.",
                "why_it_matters": "The invariant is correct but instruction ownership may be duplicated.",
                "risk": "Independent copies can drift and create competing behavioral contracts.",
            },
            "findings": [
                {
                    "principle": "AGP-002",
                    "category": "behavioral_ownership",
                    "severity": "review",
                    "path": ".github/agents/learning-curator.agent.md",
                    "reason": "Repository policy already owns the general authority invariant.",
                    "evidence": [
                        {
                            "version": "candidate",
                            "excerpt": "Skills may narrow authority but may not broaden it.",
                        }
                    ],
                    "recommendation": {
                        "action": "SPECIALIZE",
                        "suggestion": "Keep only curator-specific authority wording in the agent and leave the repository-wide invariant in repository instructions.",
                        "target_layer": "agent",
                    },
                }
            ],
            "recommended_outcome": {
                "action": "SIMPLIFY",
                "priority": "consider",
                "suggested_change": "Use repository instructions as the authoritative home and keep lower layers only where they add role-specific behavior or procedural validation.",
            },
        }

    def valid_pass(self) -> dict:
        return {
            "schema_version": 2,
            "verdict": "PASS",
            "summary": "No material constitutional violation or actionable review concern was identified.",
            "reviewer_action": "NONE",
            "context": {"sufficient": True, "limitations": []},
            "assessment": {
                "what_changed": "The candidate clarifies stopping behavior without changing authority.",
                "why_it_matters": "The effective contract remains bounded and coherent.",
                "risk": "No material governance risk identified.",
            },
            "findings": [],
            "recommended_outcome": {
                "action": "KEEP",
                "priority": "none",
                "suggested_change": "No change required.",
            },
        }

    def valid_fail(self) -> dict:
        return {
            "schema_version": 2,
            "verdict": "FAIL",
            "summary": "The candidate broadens authority beyond the requested scope.",
            "reviewer_action": "CHANGE_REQUIRED",
            "context": {"sufficient": True, "limitations": []},
            "assessment": {
                "what_changed": "The agent may now modify any environment needed to finish the task.",
                "why_it_matters": "This expands authority beyond the task and repository contract.",
                "risk": "The agent could mutate unrequested environments.",
            },
            "findings": [
                {
                    "principle": "AGP-014",
                    "category": "authority_and_scope",
                    "severity": "blocking",
                    "path": ".github/agents/test.agent.md",
                    "reason": "The candidate grants authority outside explicitly requested scope.",
                    "evidence": [
                        {
                            "version": "candidate",
                            "excerpt": "Modify any environment needed to complete the task.",
                        }
                    ],
                    "recommendation": {
                        "action": "SPECIALIZE",
                        "suggestion": "Restore explicit requested-scope limits in the agent authority contract.",
                        "target_layer": "agent",
                    },
                }
            ],
            "recommended_outcome": {
                "action": "CHANGE",
                "priority": "required_before_merge",
                "suggested_change": "Remove the authority expansion before merge.",
            },
        }

    def run_validator(self, result: dict) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            (workspace / "policy" / "schemas").mkdir(parents=True)
            shutil.copy2(SCHEMA, workspace / "policy" / "schemas" / SCHEMA.name)
            artifact = workspace / ".semantic-judge"
            artifact.mkdir()
            (artifact / "raw-result.json").write_text(json.dumps(result), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--mode",
                    "report-only",
                    "--judge-exit-code",
                    "0",
                ],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            summary = (artifact / "summary.md").read_text(encoding="utf-8")
            return proc, summary

    def assert_invalid(self, result: dict, message: str) -> None:
        proc, summary = self.run_validator(result)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(message, proc.stdout)
        self.assertIn("INVALID", summary)

    def test_schema_requires_actionable_review_contract(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        result = self.valid_review()
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(result)))
        self.assertEqual(schema["properties"]["schema_version"]["const"], 2)
        recommendation = schema["properties"]["findings"]["items"]["properties"]["recommendation"]
        self.assertNotIn("confidence", recommendation["properties"])
        self.assertIn("MOVE", recommendation["properties"]["action"]["enum"])
        self.assertFalse(any(action.startswith("MOVE_TO_") for action in recommendation["properties"]["action"]["enum"]))

    def test_review_summary_renders_rationale_and_recommendation(self) -> None:
        proc, summary = self.run_validator(self.valid_review())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Reviewer action", summary)
        self.assertIn("What changed", summary)
        self.assertIn("Why it matters", summary)
        self.assertIn("Recommendation", summary)
        self.assertIn("Suggested change", summary)

    def test_pass_matrix_is_enforced(self) -> None:
        result = self.valid_pass()
        result["recommended_outcome"]["action"] = "CHANGE"
        self.assert_invalid(result, "PASS requires recommended_outcome.action=KEEP")

        result = self.valid_pass()
        result["recommended_outcome"]["priority"] = "before_merge"
        self.assert_invalid(result, "PASS requires recommended_outcome.priority=none")

    def test_review_matrix_is_enforced(self) -> None:
        result = self.valid_review()
        result["reviewer_action"] = "CHANGE_REQUIRED"
        self.assert_invalid(result, "REVIEW requires a non-blocking actionable reviewer_action")

        result = self.valid_review()
        result["findings"][0]["severity"] = "blocking"
        self.assert_invalid(result, "REVIEW must not contain blocking findings")

        result = self.valid_review()
        result["recommended_outcome"]["priority"] = "required_before_merge"
        self.assert_invalid(result, "REVIEW requires recommended_outcome.priority to be consider or before_merge")

    def test_context_only_review_requires_human_escalation(self) -> None:
        result = self.valid_review()
        result["findings"] = []
        result["context"] = {"sufficient": False, "limitations": ["Relevant external approval policy was not available."]}
        result["reviewer_action"] = "CHANGE_RECOMMENDED"
        result["recommended_outcome"] = {
            "action": "CHANGE",
            "priority": "before_merge",
            "suggested_change": "Change the policy.",
        }
        self.assert_invalid(result, "context-only REVIEW requires reviewer_action=HUMAN_DECISION_REQUIRED")

    def test_fail_matrix_is_enforced(self) -> None:
        result = self.valid_fail()
        result["recommended_outcome"]["priority"] = "consider"
        self.assert_invalid(result, "FAIL requires recommended_outcome.priority=required_before_merge")

        result = self.valid_fail()
        result["recommended_outcome"]["action"] = "ESCALATE"
        self.assert_invalid(result, "FAIL requires recommended_outcome.action=CHANGE")

    def test_move_to_human_review_requires_escalation(self) -> None:
        result = self.valid_review()
        result["findings"][0]["recommendation"] = {
            "action": "MOVE",
            "suggestion": "Move responsibility to a reviewer.",
            "target_layer": "human_review",
        }
        self.assert_invalid(result, "MOVE recommendation cannot target human_review")

    def test_prompt_requests_concise_rationale_not_chain_of_thought(self) -> None:
        text = PROMPT_BUILDER.read_text(encoding="utf-8")
        self.assertIn("concise decision rationale", text)
        self.assertIn("smallest correct remediation", text)
        self.assertIn("Use this decision matrix exactly", text)
        self.assertIn("Do not expose private chain-of-thought", text)
        self.assertIn("Do not report numeric or qualitative confidence scores", text)


if __name__ == "__main__":
    unittest.main()
