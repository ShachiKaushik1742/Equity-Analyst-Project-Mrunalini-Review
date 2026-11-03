import ast
import unittest
from pathlib import Path


FLOW_PATH = Path(__file__).parents[1] / "crewai_flow.py"


class CrewAIFlowStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tree = ast.parse(FLOW_PATH.read_text(encoding="utf-8"))
        cls.flow_class = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "EquityResearchFlow"
        )

    def test_fixed_decorator_chain(self) -> None:
        methods = {
            node.name: node
            for node in self.flow_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        expected = {
            "steps": ("start", None),
            "research_analyst": ("listen", "steps"),
            "financial_analyst": ("listen", "research_analyst"),
            "investment_advisor": ("listen", "financial_analyst"),
            "strategy_manager": ("listen", "investment_advisor"),
            "verifier": ("listen", "strategy_manager"),
        }
        for method_name, (decorator_name, predecessor) in expected.items():
            decorator = methods[method_name].decorator_list[0]
            self.assertIsInstance(decorator, ast.Call)
            self.assertEqual(decorator.func.id, decorator_name)
            if predecessor:
                self.assertEqual(decorator.args[0].id, predecessor)

    def test_no_router_can_change_the_normal_order(self) -> None:
        imported = {
            alias.name
            for node in self.tree.body
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        self.assertNotIn("router", imported)

    def test_verifier_excludes_advisor_thesis(self) -> None:
        source = FLOW_PATH.read_text(encoding="utf-8")
        self.assertIn('"excluded": "Investment Advisor thesis"', source)


if __name__ == "__main__":
    unittest.main()
