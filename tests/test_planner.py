import json
import tempfile
import unittest
from pathlib import Path

import agent_eval_planner
from agent_eval_planner.errors import InputError

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "agent_contract.md")


class TestPlanner(unittest.TestCase):
    def test_generate_plan(self) -> None:
        result = agent_eval_planner.generate(
            input_path=FIXTURE_PATH,
            team="Platform Team",
            tools=["funnel_analytics", "open_service_center_ticket"],
        )

        self.assertIn("# Platform Team — Plano de Ação de Eval de Agente", result.plan)
        self.assertIn("SCOPE-01", result.plan)
        self.assertIn("INJECT-01", result.plan)
        self.assertIn("ROLE-01", result.plan)
        self.assertIn("bolo de cenoura", result.plan)

    def test_suite_fills_forbidden_tools(self) -> None:
        result = agent_eval_planner.generate(
            input_path=FIXTURE_PATH,
            tools=["funnel_analytics", "open_service_center_ticket"],
        )
        rows = [json.loads(line) for line in result.suite.splitlines() if line.strip()]
        smoke = next(row for row in rows if row["metadata"]["plan_id"] == "SCOPE-01")
        self.assertIn("funnel_analytics", smoke["expected"]["forbidden_tools"])
        self.assertTrue(smoke["expected"]["refusal"])

    def test_remediations_include_quick_wins(self) -> None:
        result = agent_eval_planner.generate(input_path=FIXTURE_PATH)
        self.assertIn("Quick wins", result.remediations)
        self.assertIn("SCOPE-01", result.remediations)

    def test_invalid_input_path(self) -> None:
        with self.assertRaises(InputError):
            agent_eval_planner.generate(input_path="nonexistent.md")

    def test_generate_plan_helper(self) -> None:
        plan = agent_eval_planner.generate_plan(input_path=FIXTURE_PATH, team="Platform Team")
        self.assertIn("Plano de Ação de Eval de Agente", plan)


class TestSuiteValidator(unittest.TestCase):
    def test_accepts_valid_generated_suite(self) -> None:
        result = agent_eval_planner.generate(
            input_path=FIXTURE_PATH,
            tools=["funnel_analytics"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "suite.jsonl"
            path.write_text(result.suite, encoding="utf-8")
            errors = agent_eval_planner.validate_suite(
                str(path),
                known_tools=["funnel_analytics"],
            )
            self.assertEqual(errors, [])

    def test_hard_fails_empty_forbidden_tools_on_guardrail_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "bad-1",
                        "expected": {"forbidden_tools": [], "refusal": True},
                        "metadata": {
                            "intent": "out_of_scope_refusal",
                            "tags": ["scope"],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            errors = agent_eval_planner.validate_suite(
                str(path),
                known_tools=["funnel_analytics"],
            )
            joined = "\n".join(errors)
            self.assertTrue("HARD FAIL" in joined or "forbidden_tools" in joined)


if __name__ == "__main__":
    unittest.main()
