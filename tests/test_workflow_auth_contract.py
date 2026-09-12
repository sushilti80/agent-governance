from __future__ import annotations

import unittest
from pathlib import Path

POLICY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = POLICY_ROOT / ".github" / "workflows" / "agent-governance.yml"


class WorkflowAuthContractTests(unittest.TestCase):
    def test_cross_repository_policy_checkout_uses_github_app_token(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("governance_app_client_id", workflow)
        self.assertIn("governance_app_private_key", workflow)
        self.assertEqual(workflow.count("uses: actions/create-github-app-token@v3"), 3)
        self.assertEqual(workflow.count("permission-contents: read"), 3)
        self.assertEqual(workflow.count("if: ${{ job.workflow_repository != github.repository }}"), 3)
        self.assertEqual(workflow.count("token: ${{ steps.governance-token.outputs.token || github.token }}"), 3)
        self.assertEqual(workflow.count("persist-credentials: false"), 3)

    def test_policy_identity_remains_defined_by_called_workflow(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("governance_ref", workflow)
        self.assertEqual(workflow.count("repository: ${{ job.workflow_repository }}"), 3)
        self.assertEqual(workflow.count("ref: ${{ job.workflow_sha }}"), 3)

    def test_semantic_job_uses_documented_stable_cli_contract(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("COPILOT_GITHUB_TOKEN:", workflow)
        self.assertEqual(workflow.count("copilot-requests: write"), 1)
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
        self.assertIn("--model gpt-5.6-luna", workflow)
        self.assertIn("< prompt.txt", workflow)
        self.assertNotIn('-p "$(cat prompt.txt)"', workflow)
        self.assertIn('exit "$code"', workflow)
        self.assertIn("--no-custom-instructions", workflow)
        self.assertIn("--disable-builtin-mcps", workflow)
        self.assertIn("--deny-tool='read,shell,write,url,memory'", workflow)
        self.assertNotIn("continue-on-error: true", workflow)

    def test_governance_workflows_use_aya_self_hosted_runner(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        release = (POLICY_ROOT / ".github" / "workflows" / "release-guard.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("runs-on: aya-devops-rs"), 3)
        self.assertEqual(release.count("runs-on: aya-devops-rs"), 1)
        self.assertNotIn("runs-on: ubuntu-latest", workflow)
        self.assertNotIn("runs-on: ubuntu-latest", release)

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
