import argparse
import sys
import unittest
from pathlib import Path

POLICY_ROOT = Path(__file__).resolve().parents[1]
if str(POLICY_ROOT) not in sys.path:
    sys.path.insert(0, str(POLICY_ROOT))

from scripts.render_pr_governance_report import render


def args(**overrides):
    base = dict(
        deterministic_result="success",
        classification_result="success",
        highest_risk="R3",
        semantic_required="true",
        semantic_job_result="success",
        semantic_verdict="PASS",
        reviewer_action="NONE",
        semantic_findings=0,
        redteam_required="true",
        redteam_job_result="success",
        redteam_outcome="PASS",
        redteam_successes=7,
        redteam_failures=0,
        redteam_errors=0,
        repository_eval_required="true",
        repository_eval_job_result="success",
        repository_eval_outcome="PASS",
        repository_eval_successes=7,
        repository_eval_failures=0,
        repository_eval_errors=0,
        repository_eval_diagnostic="",
        head_sha="0123456789abcdef",
        run_url="https://github.com/org/repo/actions/runs/1",
    )
    base.update(overrides)
    return argparse.Namespace(**base)


class RenderPrGovernanceReportTests(unittest.TestCase):
    def test_clean_behavioral_change_passes(self):
        text = render(args())
        self.assertIn("**Overall:** PASS", text)
        self.assertIn("| Semantic governance | ✅ PASS", text)
        self.assertIn("| Adversarial red team | ✅ PASS", text)
        self.assertIn("| Repository behavioral evals | ✅ PASS", text)

    def test_docs_only_change_marks_model_lanes_not_required(self):
        text = render(
            args(
                highest_risk="R0",
                semantic_required="false",
                semantic_job_result="skipped",
                semantic_verdict="NOT_REQUIRED",
                redteam_required="false",
                redteam_job_result="skipped",
                redteam_outcome="NOT_REQUIRED",
                redteam_successes=0,
                repository_eval_required="false",
                repository_eval_job_result="skipped",
                repository_eval_outcome="NOT_REQUIRED",
                repository_eval_successes=0,
            )
        )
        self.assertIn("**Overall:** PASS", text)
        self.assertEqual(text.count("➖ NOT REQUIRED"), 3)

    def test_semantic_review_is_attention_not_blocked(self):
        text = render(args(semantic_verdict="REVIEW", reviewer_action="CHANGE_RECOMMENDED", semantic_findings=2))
        self.assertIn("**Overall:** ATTENTION", text)
        self.assertIn("Reviewer action: `CHANGE_RECOMMENDED`", text)
        self.assertIn("Findings: `2`", text)

    def test_semantic_fail_is_attention_because_verdict_is_report_only(self):
        text = render(args(semantic_verdict="FAIL", reviewer_action="CHANGE_REQUIRED", semantic_findings=1))
        self.assertIn("**Overall:** ATTENTION", text)
        self.assertIn("⚠️ FAIL (report-only)", text)

    def test_semantic_invalid_blocks(self):
        text = render(args(semantic_job_result="failure", semantic_verdict="INVALID"))
        self.assertIn("**Overall:** BLOCKED", text)
        self.assertIn("❌ ERROR (blocking)", text)

    def test_redteam_findings_are_attention(self):
        text = render(args(redteam_outcome="FINDINGS", redteam_successes=6, redteam_failures=1))
        self.assertIn("**Overall:** ATTENTION", text)
        self.assertIn("⚠️ FINDINGS (report-only)", text)
        self.assertIn("Findings: `1`", text)

    def test_redteam_provider_error_blocks(self):
        text = render(args(redteam_job_result="failure", redteam_outcome="ERROR", redteam_errors=1))
        self.assertIn("**Overall:** BLOCKED", text)
        self.assertIn("Harness/provider errors: `1`", text)

    def test_repository_eval_findings_are_attention(self):
        text = render(
            args(
                repository_eval_outcome="FINDINGS",
                repository_eval_successes=6,
                repository_eval_failures=1,
            )
        )
        self.assertIn("**Overall:** ATTENTION", text)
        self.assertIn("### Repository behavioral evals", text)
        self.assertIn("Findings: `1`", text)

    def test_repository_eval_diagnostic_is_rendered(self):
        text = render(
            args(
                repository_eval_job_result="failure",
                repository_eval_outcome="ERROR",
                repository_eval_failures=1,
                repository_eval_diagnostic="SMOKE-HUMAN-GATE-001: escalate expected YES actual UNSPECIFIED",
            )
        )
        self.assertIn("Diagnostic:", text)
        self.assertIn("SMOKE-HUMAN-GATE-001", text)
        self.assertIn("expected YES actual UNSPECIFIED", text)

    def test_repository_eval_provider_error_blocks(self):
        text = render(
            args(
                repository_eval_job_result="failure",
                repository_eval_outcome="ERROR",
                repository_eval_errors=1,
            )
        )
        self.assertIn("**Overall:** BLOCKED", text)
        self.assertIn("Harness/provider errors: `1`", text)

    def test_deterministic_failure_blocks(self):
        text = render(args(deterministic_result="failure"))
        self.assertIn("**Overall:** BLOCKED", text)

    def test_classification_failure_blocks(self):
        text = render(args(classification_result="failure"))
        self.assertIn("**Overall:** BLOCKED", text)

    def test_comment_is_bounded_and_contains_only_machine_summary(self):
        text = render(args(semantic_findings=30, redteam_failures=7))
        self.assertLess(len(text), 8000)
        self.assertTrue(text.startswith("<!-- aya-agent-governance-report -->"))
        self.assertIn("[View detailed governance run]", text)
        self.assertNotIn("Semantic assessment", text)


if __name__ == "__main__":
    unittest.main()
