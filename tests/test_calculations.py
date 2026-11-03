import json
import unittest
from pathlib import Path

from desk import (
    Filing,
    calculate_additional_ratio,
    calculate_ratios,
    release_evidence,
    verified_financial_claims,
)


class CalculationTests(unittest.TestCase):
    def setUp(self) -> None:
        # Known-answer inputs from the Costco 2026 10-K. Company-specific values stay in tests.
        self.facts = {
            "total_revenue": {"value": 303_154_000_000, "prior_value": 275_235_000_000},
            "operating_income": {"value": 11_685_000_000, "prior_value": 10_383_000_000},
            "net_income": {"value": 9_226_000_000, "prior_value": 8_099_000_000},
            "diluted_eps": {"value": 20.76, "prior_value": 18.21},
            "stockholders_equity": {"value": 35_803_000_000, "prior_value": 29_164_000_000},
            "long_term_debt_noncurrent": {"value": 3_914_000_000, "prior_value": 5_713_000_000},
            "long_term_debt_current": {"value": 2_248_000_000, "prior_value": 75_000_000},
            "cash_from_operations": {"value": 15_817_000_000, "prior_value": 13_335_000_000},
            "capital_expenditures": {"value": 6_435_000_000, "prior_value": 5_498_000_000},
        }

    def test_report_audit_definitions(self) -> None:
        ratios = calculate_ratios(self.facts, 950.0)
        self.assertAlmostEqual(ratios["revenue_growth"]["value"], 303_154 / 275_235 - 1)
        self.assertAlmostEqual(ratios["operating_margin"]["value"], 11_685 / 303_154)
        self.assertAlmostEqual(
            ratios["return_on_average_equity"]["value"],
            9_226 / ((35_803 + 29_164) / 2),
        )
        self.assertAlmostEqual(ratios["debt_to_equity"]["value"], (3_914 + 2_248) / 35_803)
        self.assertEqual(ratios["free_cash_flow"]["value"], 9_382_000_000)
        self.assertAlmostEqual(ratios["price_to_earnings"]["value"], 950 / 20.76)

    def test_financial_analyst_additional_ratios_use_code(self) -> None:
        ratios = calculate_ratios(self.facts, 950.0)
        expected = {
            "net_margin": self.facts["net_income"]["value"] / self.facts["total_revenue"]["value"],
            "free_cash_flow_margin": ratios["free_cash_flow"]["value"]
            / self.facts["total_revenue"]["value"],
            "cash_from_operations_margin": self.facts["cash_from_operations"]["value"]
            / self.facts["total_revenue"]["value"],
            "capital_expenditure_intensity": self.facts["capital_expenditures"]["value"]
            / self.facts["total_revenue"]["value"],
        }
        for ratio_name, expected_value in expected.items():
            with self.subTest(ratio_name=ratio_name):
                result = calculate_additional_ratio(ratio_name, self.facts, ratios)
                self.assertAlmostEqual(result["value"], expected_value)
                self.assertIn(" / ", result["arithmetic"])
                self.assertTrue(result["source_fact_names"])

        with self.assertRaisesRegex(ValueError, "Unsupported calculator ratio"):
            calculate_additional_ratio("model_generated_ratio", self.facts, ratios)

    def test_release_evidence_accepts_singular_revenue_label(self) -> None:
        html = """
        <table>
          <tr><td>Total revenue</td><td>95,723</td><td>86,156</td></tr>
          <tr><td>Diluted</td><td>$</td><td>6.75</td><td>$</td><td>5.87</td></tr>
        </table>
        """
        evidence = release_evidence(html)
        self.assertEqual(evidence["quarter_total_revenue"], 95_723)
        self.assertAlmostEqual(evidence["quarter_revenue_growth"], 95_723 / 86_156 - 1)
        self.assertEqual(evidence["quarter_diluted_eps"], 6.75)

    def test_release_evidence_accepts_plural_revenue_label(self) -> None:
        html = """
        <table>
          <tr><td>Total revenues</td><td>187,937</td><td>177,402</td><td>5.9%</td></tr>
          <tr><td>Diluted net income per common share attributable to Walmart</td><td>0.80</td></tr>
        </table>
        """
        evidence = release_evidence(html)
        self.assertEqual(evidence["quarter_total_revenue"], 187_937)
        self.assertEqual(evidence["quarter_diluted_eps"], 0.80)

    def test_release_evidence_accepts_total_net_sales_label(self) -> None:
        html = """
        <table>
          <tr><td>Total net sales <sup>(1)</sup></td><td>$94,036</td><td>$85,777</td></tr>
          <tr><td>Diluted</td><td>$1.57</td><td>$1.40</td></tr>
          <tr><td>Diluted</td><td>14,714,676</td><td>14,948,179</td></tr>
        </table>
        """
        evidence = release_evidence(html)
        self.assertEqual(evidence["quarter_total_revenue"], 94_036)
        self.assertEqual(evidence["quarter_diluted_eps"], 1.57)

    def test_verified_costco_block_keeps_known_answers(self) -> None:
        folder = Path(__file__).resolve().parents[1] / "outputs" / "COST_20261028_194706"
        facts = json.loads((folder / "facts.json").read_text(encoding="utf-8"))
        ratios = json.loads((folder / "ratios.json").read_text(encoding="utf-8"))
        evidence = json.loads((folder / "release_evidence.json").read_text(encoding="utf-8"))
        peers = json.loads((folder / "peers.json").read_text(encoding="utf-8"))
        metadata = json.loads((folder / "run_metadata.json").read_text(encoding="utf-8"))
        filings = {name: Filing(**filing) for name, filing in metadata["filings"].items()}

        block = verified_financial_claims(filings, facts, ratios, evidence, peers)

        for expected in (
            "$303,154 million",
            "10.1437%",
            "$11,685 million",
            "3.8545%",
            "$9,226 million",
            "$20.76",
            "28.4021%",
            "0.1721x",
            "$9,382 million",
            "$95,723 million",
            "11.1043%",
            "$6.75",
            "47.7905x",
            "4.1821%",
            "4.8836%",
            "3.8057%",
        ):
            self.assertIn(expected, block)


if __name__ == "__main__":
    unittest.main()
