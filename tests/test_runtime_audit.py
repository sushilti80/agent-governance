import importlib.util
import sys
import unittest
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "runtime_audit",
    ROOT / "scripts" / "runtime_audit.py",
)
RUNTIME_AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = RUNTIME_AUDIT
SPEC.loader.exec_module(RUNTIME_AUDIT)


class RuntimeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = yaml.safe_load(
            (ROOT / "principles" / "runtime-efficiency-policy.yaml").read_text()
        )
        cls.schema = RUNTIME_AUDIT.read_json_within_workspace(
            "schemas/agent-run-trace.schema.json",
            ROOT,
        )

    def load_trace(self, name):
        return RUNTIME_AUDIT.read_yaml_within_workspace(
            Path("tests") / "fixtures" / "run-traces" / name,
            ROOT,
        )

    def test_all_trace_fixtures_conform_to_schema(self):
        validator = Draft202012Validator(self.schema)
        for path in (ROOT / "tests" / "fixtures" / "run-traces").glob("*.yaml"):
            trace = yaml.safe_load(path.read_text())
            self.assertEqual(list(validator.iter_errors(trace)), [], path.name)

    def test_runtime_eval_catalog_is_present(self):
        text = (ROOT / "evals" / "global" / "runtime-efficiency.yaml").read_text()
        for eval_id in (
            "DELEGATION-003",
            "DELEGATION-004",
            "STOP-002",
            "STOP-003",
            "EFFICIENCY-001",
        ):
            self.assertIn(f"id: {eval_id}", text)

    def test_cloudflare_loop_is_detected(self):
        metrics, findings = RUNTIME_AUDIT.audit(
            self.load_trace("cloudflare-loop.yaml"),
            self.policy,
        )
        codes = {finding.code for finding in findings}
        self.assertGreater(metrics["total_delegations"], 3)
        self.assertIn("AGP-RUNTIME-DELEGATIONS", codes)
        self.assertIn("AGP-RUNTIME-REPEAT-DELEGATION", codes)
        self.assertIn("AGP-RUNTIME-REPEAT-ACTION", codes)
        self.assertIn("AGP-RUNTIME-REPEAT-VALIDATOR", codes)
        self.assertIn("AGP-RUNTIME-POST-SUCCESS", codes)

    def test_bounded_parallelism_passes(self):
        metrics, findings = RUNTIME_AUDIT.audit(
            self.load_trace("bounded-parallel.yaml"),
            self.policy,
        )
        self.assertEqual(metrics["max_parallel_agents"], 3)
        self.assertEqual(metrics["max_depth"], 1)
        self.assertEqual(findings, [])

    def test_cloudflare_gate1_passes_without_delegation(self):
        metrics, findings = RUNTIME_AUDIT.audit(
            self.load_trace("cloudflare-gate1.yaml"),
            self.policy,
        )
        self.assertEqual(metrics["total_delegations"], 0)
        self.assertEqual(metrics["total_actions"], 1)
        self.assertEqual(metrics["repeated_validators_without_state_change"], 0)
        self.assertEqual(findings, [])

    def test_success_outcome_requires_success_event(self):
        trace = deepcopy(self.load_trace("bounded-parallel.yaml"))
        trace["events"] = [
            event for event in trace["events"] if event["type"] != "success"
        ]
        errors = list(Draft202012Validator(self.schema).iter_errors(trace))
        self.assertTrue(errors)

    def test_malformed_root_and_sequence_values_do_not_crash_validation(self):
        root_errors = RUNTIME_AUDIT.validate_trace(["not", "an", "object"], self.schema)
        self.assertTrue(root_errors)

        trace = {
            "spec_version": 1,
            "run": {"repository": "example/repo", "agent": "test", "task": "bad seq"},
            "outcome": "failure",
            "events": [
                {
                    "seq": 1,
                    "type": "action",
                    "category": "read",
                    "equivalence_key": "read-target",
                    "evidence_delta": False,
                    "state_change": False,
                },
                {
                    "seq": "2",
                    "type": "action",
                    "category": "read",
                    "equivalence_key": "read-target",
                    "evidence_delta": False,
                    "state_change": False,
                },
            ],
        }
        seq_errors = RUNTIME_AUDIT.validate_trace(trace, self.schema)
        self.assertTrue(seq_errors)

    def test_validator_evidence_does_not_reset_state_change_requirement(self):
        trace = {
            "spec_version": 1,
            "run": {
                "repository": "example/repo",
                "agent": "test",
                "task": "validator repetition",
            },
            "outcome": "success",
            "events": [
                {
                    "seq": 1,
                    "type": "action",
                    "category": "validator",
                    "equivalence_key": "validate-target",
                    "evidence_delta": True,
                    "state_change": False,
                },
                {
                    "seq": 2,
                    "type": "action",
                    "category": "validator",
                    "equivalence_key": "validate-target",
                    "evidence_delta": False,
                    "state_change": False,
                },
                {"seq": 3, "type": "success", "criteria": ["validated"]},
            ],
        }
        metrics, findings = RUNTIME_AUDIT.audit(trace, self.policy)
        self.assertEqual(metrics["repeated_validators_without_state_change"], 1)
        self.assertIn(
            "AGP-RUNTIME-REPEAT-VALIDATOR",
            {finding.code for finding in findings},
        )

    def test_state_change_allows_validator_rerun(self):
        trace = {
            "spec_version": 1,
            "run": {
                "repository": "example/repo",
                "agent": "test",
                "task": "validator after edit",
            },
            "outcome": "success",
            "events": [
                {
                    "seq": 1,
                    "type": "action",
                    "category": "validator",
                    "equivalence_key": "validate-target",
                    "evidence_delta": True,
                    "state_change": False,
                },
                {
                    "seq": 2,
                    "type": "action",
                    "category": "edit",
                    "equivalence_key": "edit-target",
                    "evidence_delta": False,
                    "state_change": True,
                },
                {
                    "seq": 3,
                    "type": "action",
                    "category": "validator",
                    "equivalence_key": "validate-target",
                    "evidence_delta": True,
                    "state_change": False,
                },
                {"seq": 4, "type": "success", "criteria": ["validated after edit"]},
            ],
        }
        metrics, findings = RUNTIME_AUDIT.audit(trace, self.policy)
        self.assertEqual(metrics["repeated_validators_without_state_change"], 0)
        self.assertNotIn(
            "AGP-RUNTIME-REPEAT-VALIDATOR",
            {finding.code for finding in findings},
        )

    def test_workspace_path_rejects_escape(self):
        outside = ROOT.parent / "outside-runtime-trace.yaml"
        with self.assertRaises(ValueError):
            RUNTIME_AUDIT.resolve_workspace_path(
                outside,
                ROOT,
                must_exist=False,
            )


if __name__ == "__main__":
    unittest.main()
