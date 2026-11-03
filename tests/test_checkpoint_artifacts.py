import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_FOLDER = ROOT / "outputs" / "AAPL_20261028_202525"


class CheckpointArtifactTests(unittest.TestCase):
    def test_apple_fallback_report_is_complete(self) -> None:
        report = (RUN_FOLDER / "report.md").read_text(encoding="utf-8")
        lines = report.splitlines()
        self.assertIn("Apple Inc. (AAPL)", lines[0])
        for accession in (
            "0000320193-25-000079",
            "0000320193-26-000020",
            "0000320193-26-000018",
        ):
            self.assertIn(accession, lines[0])
        self.assertEqual(lines[1], "fallback")
        self.assertTrue(lines[2].startswith("Run time:"))

        required = (
            "## 1. Overview",
            "## 2. Market Positioning and Growth Outlook",
            "## 3. Valuation Insights",
            "## 4. Future Developments and Strategic Recommendations",
            "## 5. Investment Recommendation",
            "$416,161 million",
            "6.4255%",
            "$133,050 million",
            "31.9708%",
            "$112,010 million",
            "$7.46",
            "171.4224%",
            "1.2298x",
            "$98,767 million",
            "$109,417 million",
            "16.3565%",
            "$2.02",
            "45.3338x",
            "46.7808%",
            "32.0326%",
            "7.1773%",
        )
        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, report)

    def test_human_audit_has_no_placeholders(self) -> None:
        audit = (ROOT / "audits" / "AAPL_20261028_human_audit.md").read_text(encoding="utf-8")
        self.assertIn("Errors (wrong + unsupported): 0", audit)
        self.assertIn("Missing claims: 0", audit)
        self.assertRegex(audit, r"Partner claim 1 and mark: .+— correct")
        self.assertRegex(audit, r"Partner claim 2 and mark:\s+.+— correct")
        self.assertIn("Student name: Mrunalini Pol", audit)
        self.assertRegex(audit, r"Date:\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}")

        rows = [line for line in audit.splitlines() if re.match(r"^\|\s*\d+\s*\|", line)]
        self.assertEqual(len(rows), 17)
        allowed = {"correct", "wrong", "unsupported", "missing"}
        for row in rows:
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
            self.assertIn(cells[4].lower(), allowed)
        self.assertNotRegex(audit, r"\[(?:mark|complete|sign|date)\]")

    def test_lab03_prompt_and_program_are_company_neutral(self) -> None:
        prompt = (ROOT / "library" / "lab03_four_role_app_prompt.md").read_text(encoding="utf-8")
        for required in ("Research Analyst", "Financial Analyst", "Investment Advisor", "Strategy Manager"):
            self.assertIn(required, prompt)

        program = (ROOT / "desk.py").read_text(encoding="utf-8")
        forbidden = (
            "AAPL",
            "COST",
            "WMT",
            "TGT",
            "GOOGL",
            "MSFT",
            "DELL",
            "Apple Inc.",
            "Costco",
            "Walmart",
            "Alphabet Inc.",
            "Microsoft Corp",
            "Dell Technologies",
        )
        for company_name in forbidden:
            with self.subTest(company_name=company_name):
                self.assertNotIn(company_name, program)


if __name__ == "__main__":
    unittest.main()
