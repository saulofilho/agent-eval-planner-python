import unittest
from pathlib import Path

from agent_eval_planner.contract_analyzer import ContractAnalyzer

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "agent_contract.md")


class TestContractAnalyzer(unittest.TestCase):
    def test_extracts_agent_name_and_tools(self) -> None:
        analyzer = ContractAnalyzer(source_path=FIXTURE_PATH)
        self.assertEqual(analyzer.agent_name, "analytics")
        self.assertIn("funnel_analytics", analyzer.tools)
        self.assertIn("open_service_center_ticket", analyzer.tools)
        self.assertTrue(analyzer.has_tools())
        self.assertTrue(analyzer.multi_specialist())
        self.assertTrue(analyzer.analytics_domain())

    def test_raw_contract_without_file(self) -> None:
        analyzer = ContractAnalyzer(
            raw="# Agent\nagent_name: docs\n- search_docs\n",
            agent_name="docs",
            tools=["search_docs"],
        )
        self.assertEqual(analyzer.agent_name, "docs")
        self.assertEqual(analyzer.tools, ["search_docs"])


if __name__ == "__main__":
    unittest.main()
