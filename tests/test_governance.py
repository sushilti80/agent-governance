from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

POLICY_ROOT = Path(__file__).resolve().parents[1]
CHECKER = POLICY_ROOT / "scripts" / "governance_check.py"
CLASSIFIER = POLICY_ROOT / "scripts" / "check_changed_agent_files.py"
RELEASE_CHECKER = POLICY_ROOT / "scripts" / "release_check.py"
VALID_MANIFEST = (POLICY_ROOT / "examples" / ".agent" / "governance.yaml").read_text(encoding="utf-8")
VERSION = (POLICY_ROOT / "VERSION").read_text(encoding="utf-8").strip()


class GovernanceRegressionTests(unittest.TestCase):
    def run_checker(
        self,
        manifest: str | None,
        policy_root: Path = POLICY_ROOT,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            if manifest is not None:
                (target / ".agent").mkdir(parents=True)
                (target / ".agent" / "governance.yaml").write_text(manifest, encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(policy_root / "scripts" / "governance_check.py"),
                    "--policy-root",
                    str(policy_root),
                    "--target-root",
                    str(target),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

    def classify(self, path: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLASSIFIER), path],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_valid_adoption_manifest_passes(self) -> None:
        result = self.run_checker(VALID_MANIFEST)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_manifest_is_rejected(self) -> None:
        result = self.run_checker(None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing governance manifest", result.stdout)

    def test_self_promote_manifest_is_rejected(self) -> None:
        invalid = VALID_MANIFEST.replace("mode: propose-only", "mode: self-promote")
        result = self.run_checker(invalid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("propose-only", result.stdout)

    def test_wrong_policy_name_is_rejected(self) -> None:
        invalid = VALID_MANIFEST.replace("policy: aya-agent-governance", "policy: other-governance")
        result = self.run_checker(invalid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("aya-agent-governance", result.stdout)

    def test_wrong_spec_version_is_rejected(self) -> None:
        invalid = VALID_MANIFEST.replace("spec_version: 1", "spec_version: 2")
        result = self.run_checker(invalid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("1 was expected", result.stdout)

    def test_wrong_governance_version_is_rejected(self) -> None:
        invalid = VALID_MANIFEST.replace(f'version: "{VERSION}"', 'version: "2099.01.1"')
        result = self.run_checker(invalid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("policy version mismatch", result.stdout)

    def test_policy_version_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            policy_copy = Path(directory) / "policy"
            shutil.copytree(POLICY_ROOT, policy_copy, ignore=shutil.ignore_patterns(".git"))
            (policy_copy / "VERSION").write_text("2026.09.99\n", encoding="utf-8")
            result = self.run_checker(VALID_MANIFEST, policy_copy)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("policy version mismatch", result.stdout)
        self.assertIn("CHANGELOG.md", result.stdout)

    def test_calendar_format_policy_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            policy_copy = Path(directory) / "policy"
            shutil.copytree(POLICY_ROOT, policy_copy, ignore=shutil.ignore_patterns(".git"))
            path = policy_copy / "principles" / "versioning-policy.yaml"
            text = path.read_text(encoding="utf-8").replace("format: calendar", "format: semver")
            path.write_text(text, encoding="utf-8")
            result = self.run_checker(VALID_MANIFEST, policy_copy)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("governance_version.format must be 'calendar'", result.stdout)

    def test_workflow_policy_checkout_uses_defining_job_identity(self) -> None:
        workflow = (POLICY_ROOT / ".github" / "workflows" / "agent-governance.yml").read_text(encoding="utf-8")
        self.assertNotIn("governance_ref", workflow)
        self.assertIn("repository: ${{ job.workflow_repository }}", workflow)
        self.assertIn("ref: ${{ job.workflow_sha }}", workflow)

    def test_release_tag_must_match_version(self) -> None:
        good = subprocess.run(
            [sys.executable, str(RELEASE_CHECKER), "--root", str(POLICY_ROOT), "--tag", f"v{VERSION}"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)

        bad = subprocess.run(
            [sys.executable, str(RELEASE_CHECKER), "--root", str(POLICY_ROOT), "--tag", "v2099.01.1"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("does not match canonical", bad.stdout)

    def test_risk_classification_matrix(self) -> None:
        cases = {
            "README.md": "R0",
            "examples/report.yaml": "R1",
            ".github/skills/storage/SKILL.md": "R2",
            ".github/agents/iac.agent.md": "R3",
            ".agent/governance.yaml": "R3",
            "VERSION": "R4",
            "requirements-governance.txt": "R4",
            "evals/global/review-readonly.yaml": "R4",
            "principles/agent-design.yaml": "R4",
            "schemas/governance-manifest.schema.json": "R4",
            ".github/workflows/agent-governance.yml": "R4",
            "scripts/governance_check.py": "R4",
            "tests/test_governance.py": "R4",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                result = self.classify(path)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"{expected}\t{path}", result.stdout)
                self.assertIn(f"highest_risk={expected}", result.stdout)


if __name__ == "__main__":
    unittest.main()
