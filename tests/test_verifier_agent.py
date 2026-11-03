import tempfile
import unittest
from pathlib import Path

from verifier_agent import audit_saved_run


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs" / "COST_20261028_194706"


class VerifierAgentTests(unittest.TestCase):
    def test_clean_costco_report_passes(self) -> None:
        result = audit_saved_run(RUN)
        core_marks = result.marks[:11]
        self.assertTrue(result.verified)
        self.assertEqual(11, len(core_marks))
        self.assertTrue(all(mark.mark == "correct" for mark in core_marks))

    def test_seeded_eps_error_is_wrong_and_corrected(self) -> None:
        report = (RUN / "report.md").read_text(encoding="utf-8")
        old = "5. **GAAP diluted EPS:** $20.76."
        changed = report.replace(old, "5. **GAAP diluted EPS:** $21.76.", 1)
        self.assertNotEqual(report, changed)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "seeded-report.md"
            path.write_text(changed, encoding="utf-8")
            result = audit_saved_run(RUN, path)
        mark = next(item for item in result.marks if item.claim == "GAAP diluted EPS")
        self.assertFalse(result.verified)
        self.assertEqual("wrong", mark.mark)
        self.assertEqual("$20.76", mark.correction)
        self.assertIn("EarningsPerShareDiluted", mark.source)

    def test_missing_xbrl_source_is_unsupported(self) -> None:
        report = (RUN / "report.md").read_text(encoding="utf-8")
        changed = report.replace("XBRL tag `NetIncomeLoss`;", "XBRL tag omitted;", 1)
        self.assertNotEqual(report, changed)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "unsupported-report.md"
            path.write_text(changed, encoding="utf-8")
            result = audit_saved_run(RUN, path)
        mark = next(
            item for item in result.marks if item.claim == "Net income attributable to the company"
        )
        self.assertEqual("unsupported", mark.mark)
        self.assertIn("NetIncomeLoss", mark.explanation)

    def test_investment_thesis_line_is_out_of_scope(self) -> None:
        report = (RUN / "report.md").read_text(encoding="utf-8")
        changed = report.replace("### Investment Thesis", "### Investment Thesis\nUnsupported [10-K Line 999999]", 1)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "thesis-report.md"
            path.write_text(changed, encoding="utf-8")
            result = audit_saved_run(RUN, path)
        self.assertTrue(result.verified)
        self.assertFalse(any(mark.claim == "10-K Line 999999" for mark in result.marks))


if __name__ == "__main__":
    unittest.main()
