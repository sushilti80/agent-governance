from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

POLICY_ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = POLICY_ROOT / "scripts" / "check_changed_agent_files.py"
WORKFLOW = POLICY_ROOT / ".github" / "workflows" / "agent-governance.yml"
CONFIG = POLICY_ROOT / "redteam" / "promptfooconfig.yaml"
CASES = POLICY_ROOT / "redteam" / "cases.yaml"
PROVIDER = POLICY_ROOT / "scripts" / "promptfoo_copilot_provider.py"


class RedteamGovernanceTests(unittest.TestCase):
    def classify(self, *paths: str) -> str:
        proc = subprocess.run(
            [sys.executable, str(CLASSIFIER), *paths],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def test_redteam_contract_is_r4_and_has_dedicated_trigger(self) -> None:
        for path in (
            "redteam/promptfooconfig.yaml",
            "redteam/cases.yaml",
            "scripts/promptfoo_copilot_provider.py",
            ".github/workflows/agent-governance.yml",
        ):
            with self.subTest(path=path):
                output = self.classify(path)
                self.assertIn("highest_risk=R4", output)
        self.assertIn("redteam_contract_changed=true", self.classify("redteam/cases.yaml"))

    def test_redteam_assets_exist_and_are_bounded(self) -> None:
        self.assertTrue(CONFIG.is_file())
        self.assertTrue(CASES.is_file())
        self.assertTrue(PROVIDER.is_file())
        config = CONFIG.read_text(encoding="utf-8")
        cases = CASES.read_text(encoding="utf-8")
        self.assertIn("maxConcurrency: 1", config)
        self.assertIn("type: is-json", config)
        self.assertIn("type: javascript", cases)
        self.assertIn("decision === 'PROCEED'", cases)
        self.assertIn("['REFUSE', 'ESCALATE']", cases)

    def test_benign_scope_assertion_is_semantic_not_exact_string_match(self) -> None:
        cases = CASES.read_text(encoding="utf-8")
        self.assertNotIn("JSON.stringify(r.proposed_scope) === JSON.stringify(['dev'])", cases)
        self.assertIn("hasDevScope", cases)
        self.assertIn("widenedMarkers", cases)
        self.assertIn("widened === false", cases)

    def test_promptfoo_exec_provider_path_resolves_from_config_directory(self) -> None:
        config = CONFIG.read_text(encoding="utf-8")
        expected = "../scripts/promptfoo_copilot_provider.py"
        self.assertIn(f"exec:python {expected}", config)
        resolved = (CONFIG.parent / expected).resolve()
        self.assertEqual(resolved, PROVIDER.resolve())
        self.assertTrue(resolved.is_file())

    def test_target_provider_does_not_embed_redteam_answers(self) -> None:
        source = PROVIDER.read_text(encoding="utf-8")
        self.assertIn("Simulate the engineering agent defined by CANDIDATE CONTRACT", source)
        self.assertIn("UNSPECIFIED", source)
        self.assertIn("Do not add policy rules", source)
        for forbidden in (
            "You are a security evaluator",
            "DECISION RULE",
            "REJECT when the attack attempts",
            "ALLOW only when",
        ):
            self.assertNotIn(forbidden, source)

    def test_provider_keeps_copilot_toolless(self) -> None:
        source = PROVIDER.read_text(encoding="utf-8")
        for option in (
            "--no-custom-instructions",
            "--disable-builtin-mcps",
            "--deny-tool=read,shell,write,url,memory",
            "--no-remote",
            "--no-remote-export",
        ):
            self.assertIn(option, source)

    def test_workflow_pins_promptfoo_and_separates_findings_from_errors(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("promptfoo@0.123.0", workflow)
        self.assertIn("PROMPTFOO_DISABLE_TELEMETRY", workflow)
        self.assertIn("data.get('results', {}).get('stats', {})", workflow)
        self.assertIn('[ "$errors" -gt 0 ]', workflow)
        self.assertIn("outcome=FINDINGS", workflow)
        self.assertIn("outcome=ERROR", workflow)
        self.assertIn("findings report-only during calibration", workflow)


if __name__ == "__main__":
    unittest.main()
