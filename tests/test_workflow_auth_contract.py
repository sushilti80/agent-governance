from __future__ import annotations

import unittest
from pathlib import Path

import yaml

POLICY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = POLICY_ROOT / ".github" / "workflows" / "agent-governance.yml"

POLICY_CHECKOUT_JOBS = {
    "deterministic-governance",
    "classify-change",
    "semantic-governance",
    "redteam-governance",
    "repository-evals",
    "pr-governance-report",
}
MODEL_EVALUATION_JOBS = {
    "semantic-governance",
    "redteam-governance",
    "repository-evals",
}


def load_workflow() -> tuple[str, dict]:
    text = WORKFLOW.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)
    return text, parsed["jobs"]


class WorkflowAuthContractTests(unittest.TestCase):
    def test_cross_repository_policy_checkout_uses_github_app_token(self) -> None:
        workflow, jobs = load_workflow()
        self.assertIn("governance_app_client_id", workflow)
        self.assertIn("governance_app_private_key", workflow)

        self.assertTrue(POLICY_CHECKOUT_JOBS.issubset(jobs))
        for job_name in POLICY_CHECKOUT_JOBS:
            with self.subTest(job=job_name):
                steps = jobs[job_name]["steps"]
                token_steps = [
                    step for step in steps
                    if step.get("uses") == "actions/create-github-app-token@v3"
                ]
                self.assertEqual(len(token_steps), 1)
                token_step = token_steps[0]
                self.assertEqual(
                    token_step.get("if"),
                    "${{ job.workflow_repository != github.repository }}",
                )
                self.assertEqual(token_step.get("with", {}).get("permission-contents"), "read")

                policy_checkouts = [
                    step for step in steps
                    if step.get("uses") == "actions/checkout@v5"
                    and step.get("with", {}).get("repository") == "${{ job.workflow_repository }}"
                ]
                self.assertEqual(len(policy_checkouts), 1)
                checkout = policy_checkouts[0]["with"]
                self.assertEqual(checkout.get("ref"), "${{ job.workflow_sha }}")
                self.assertEqual(
                    checkout.get("token"),
                    "${{ steps.governance-token.outputs.token || github.token }}",
                )
                self.assertFalse(checkout.get("persist-credentials"))

    def test_policy_identity_remains_defined_by_called_workflow(self) -> None:
        workflow, jobs = load_workflow()
        self.assertNotIn("governance_ref", workflow)
        for job_name in POLICY_CHECKOUT_JOBS:
            with self.subTest(job=job_name):
                steps = jobs[job_name]["steps"]
                checkout = next(
                    step for step in steps
                    if step.get("uses") == "actions/checkout@v5"
                    and step.get("with", {}).get("repository") == "${{ job.workflow_repository }}"
                )
                self.assertEqual(checkout["with"].get("ref"), "${{ job.workflow_sha }}")

    def test_model_evaluation_jobs_use_documented_stable_cli_contract(self) -> None:
        workflow, jobs = load_workflow()
        self.assertIn("COPILOT_GITHUB_TOKEN:", workflow)
        self.assertTrue(MODEL_EVALUATION_JOBS.issubset(jobs))

        for job_name in MODEL_EVALUATION_JOBS:
            with self.subTest(job=job_name):
                self.assertEqual(
                    jobs[job_name].get("permissions", {}).get("copilot-requests"),
                    "write",
                )

        self.assertIn("name: semantic-governance-report", workflow)
        self.assertIn("name: promptfoo-redteam-report", workflow)
        self.assertIn("name: promptfoo-repository-evals-report", workflow)
        self.assertIn('export COPILOT_GITHUB_TOKEN="$GITHUB_TOKEN"', workflow)
        self.assertNotIn("--auth-token-env", workflow)
        self.assertNotIn("--no-banner", workflow)
        self.assertIn("copilot --help > copilot-help.txt", workflow)
        for option in (
            "--silent",
            "--model",
            "--reasoning-effort",
            "--no-ask-user",
            "--no-custom-instructions",
            "--disable-builtin-mcps",
            "--deny-tool",
            "--no-auto-update",
            "--no-color",
            "--no-remote",
            "--no-remote-export",
        ):
            self.assertIn(f"'{option}'", workflow)
        policy = yaml.safe_load(
            (POLICY_ROOT / "principles" / "semantic-review-policy.yaml").read_text(encoding="utf-8")
        )
        semantic_commands = "\n".join(
            step.get("run", "") for step in jobs["semantic-governance"]["steps"]
        )
        self.assertIn(f"--model {policy['judge']['model']} ", semantic_commands)
        self.assertIn("< prompt.txt", workflow)
        self.assertNotIn('-p "$(cat prompt.txt)"', workflow)
        self.assertIn('exit "$code"', workflow)
        self.assertIn("--deny-tool='read,shell,write,url,memory'", workflow)
        self.assertNotIn("continue-on-error: true", workflow)

    def test_pr_reporting_has_least_privilege_and_stale_head_guard(self) -> None:
        workflow, jobs = load_workflow()
        top_permissions = workflow.split("jobs:", 1)[0]
        self.assertNotIn("issues: write", top_permissions)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("pull-requests: read", workflow)
        self.assertEqual(
            jobs["pr-governance-report"].get("permissions", {}).get("pull-requests"),
            "write",
        )
        for job_name, job in jobs.items():
            if job_name != "pr-governance-report":
                self.assertNotEqual(job.get("permissions", {}).get("pull-requests"), "write")
        self.assertIn("name: pr-governance-report", workflow)
        self.assertIn("current.data.head.sha !== evaluatedSha", workflow)
        self.assertIn("comment.user.login === 'github-actions[bot]'", workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)

    def test_governance_workflows_use_aya_self_hosted_runner(self) -> None:
        _, jobs = load_workflow()
        release = yaml.safe_load(
            (POLICY_ROOT / ".github" / "workflows" / "release-guard.yml").read_text(encoding="utf-8")
        )
        for job_name, job in jobs.items():
            with self.subTest(job=job_name):
                self.assertEqual(job.get("runs-on"), "aya-devops-rs")
        for job_name, job in release["jobs"].items():
            with self.subTest(release_job=job_name):
                self.assertEqual(job.get("runs-on"), "aya-devops-rs")

    def test_workflows_use_node24_generation_actions(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        release = (POLICY_ROOT / ".github" / "workflows" / "release-guard.yml").read_text(encoding="utf-8")
        combined = workflow + "\n" + release
        self.assertNotIn("actions/checkout@v4", combined)
        self.assertNotIn("actions/setup-python@v5", combined)
        self.assertIn("actions/checkout@v5", combined)
        self.assertIn("actions/setup-python@v6", combined)


if __name__ == "__main__":
    unittest.main()
