from __future__ import annotations

import unittest
from pathlib import Path

POLICY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = POLICY_ROOT / ".github" / "workflows" / "agent-governance.yml"
PROMPT_BUILDER = POLICY_ROOT / "scripts" / "build_semantic_prompt.py"


class SemanticRuntimeTransportTests(unittest.TestCase):
    def test_large_semantic_prompt_uses_stdin_not_argv(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("< prompt.txt", workflow)
        self.assertNotIn('-p "$(cat prompt.txt)"', workflow)
        self.assertNotIn("$(cat prompt.txt)", workflow)

    def test_judge_step_propagates_real_cli_exit_code(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('echo "exit_code=$code" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn('exit "$code"', workflow)

    def test_prompt_embeds_exact_output_schema_as_trusted_input(self) -> None:
        prompt_builder = PROMPT_BUILDER.read_text(encoding="utf-8")
        self.assertIn('semantic-judge-result.schema.json', prompt_builder)
        self.assertIn("TRUSTED OUTPUT SCHEMA", prompt_builder)
        self.assertIn("json.dumps(result_schema", prompt_builder)


if __name__ == "__main__":
    unittest.main()
