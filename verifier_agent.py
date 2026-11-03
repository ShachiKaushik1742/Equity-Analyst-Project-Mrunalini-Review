"""Evidence-bound verifier used as the final node of the CrewAI Flow."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal


Mark = Literal["correct", "wrong", "unsupported"]


@dataclass(frozen=True)
class VerificationMark:
    claim: str
    mark: Mark
    explanation: str
    correction: str = ""
    source: str = ""


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    marks: list[VerificationMark]

    def to_dict(self) -> dict[str, Any]:
        return {"verified": self.verified, "marks": [asdict(mark) for mark in self.marks]}


@dataclass(frozen=True)
class ClaimSpec:
    label: str
    expected_tokens: tuple[str, ...]
    source_tokens: tuple[str, ...]
    correction: str
    source: str


CORE_ITEM_RE = re.compile(
    r"^\s*\d+\.\s+\*\*(?P<label>[^*]+):\*\*\s+(?P<body>.*?)(?=^\s*\d+\.\s+\*\*|\Z)",
    re.MULTILINE | re.DOTALL,
)
LINE_CITATION_RE = re.compile(r"\[(10-K|10-Q|EX-99\.1) Line (\d+)\]")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _millions(value: float) -> str:
    return f"{value / 1_000_000:,.0f}"


def _fact_source(fact: dict[str, Any]) -> str:
    return (
        f"10-K accession {fact['accession']}; XBRL tag `{fact['tag']}`; "
        f"period ended {fact['end']}"
    )


def _claim_specs(
    facts: dict[str, Any], ratios: dict[str, Any], evidence: dict[str, Any]
) -> list[ClaimSpec]:
    revenue = facts["total_revenue"]
    operating = facts["operating_income"]
    net_income = facts["net_income"]
    eps = facts["diluted_eps"]
    equity = facts["stockholders_equity"]
    debt_nc = facts["long_term_debt_noncurrent"]
    debt_cur = facts["long_term_debt_current"]
    cash = facts["cash_from_operations"]
    capex = facts["capital_expenditures"]

    return [
        ClaimSpec(
            "Total revenue",
            (f"${_millions(revenue['value'])} million",),
            (revenue["tag"], revenue["end"], revenue["accession"]),
            f"${_millions(revenue['value'])} million",
            _fact_source(revenue),
        ),
        ClaimSpec(
            "Revenue growth",
            (
                f"{ratios['revenue_growth']['value'] * 100:.4f}%",
                ratios["revenue_growth"]["arithmetic"],
            ),
            (revenue["tag"], revenue["end"], revenue["prior_end"], revenue["accession"]),
            f"{ratios['revenue_growth']['value'] * 100:.4f}%",
            _fact_source(revenue),
        ),
        ClaimSpec(
            "Operating income and operating margin",
            (
                f"${_millions(operating['value'])} million",
                f"{ratios['operating_margin']['value'] * 100:.4f}%",
                ratios["operating_margin"]["arithmetic"],
                "Definition:",
            ),
            (operating["tag"], revenue["tag"], operating["end"], operating["accession"]),
            (
                f"${_millions(operating['value'])} million and "
                f"{ratios['operating_margin']['value'] * 100:.4f}%"
            ),
            f"{_fact_source(operating)}; {_fact_source(revenue)}",
        ),
        ClaimSpec(
            "Net income attributable to the company",
            (f"${_millions(net_income['value'])} million",),
            (net_income["tag"], net_income["end"], net_income["accession"]),
            f"${_millions(net_income['value'])} million",
            _fact_source(net_income),
        ),
        ClaimSpec(
            "GAAP diluted EPS",
            (f"${float(eps['value']):.2f}",),
            (eps["tag"], eps["end"], eps["accession"]),
            f"${float(eps['value']):.2f}",
            _fact_source(eps),
        ),
        ClaimSpec(
            "Return on average equity",
            (
                f"{ratios['return_on_average_equity']['value'] * 100:.4f}%",
                ratios["return_on_average_equity"]["arithmetic"],
                "Definition:",
            ),
            (net_income["tag"], equity["tag"], equity["end"], equity["accession"]),
            f"{ratios['return_on_average_equity']['value'] * 100:.4f}%",
            f"{_fact_source(net_income)}; {_fact_source(equity)}",
        ),
        ClaimSpec(
            "Debt to equity",
            (
                f"{ratios['debt_to_equity']['value']:.4f}x",
                ratios["debt_to_equity"]["arithmetic"],
                "Definition:",
            ),
            (debt_nc["tag"], debt_cur["tag"], equity["tag"], equity["end"]),
            f"{ratios['debt_to_equity']['value']:.4f}x",
            f"{_fact_source(debt_nc)}; {_fact_source(debt_cur)}; {_fact_source(equity)}",
        ),
        ClaimSpec(
            "Free cash flow",
            (
                f"${_millions(ratios['free_cash_flow']['value'])} million",
                ratios["free_cash_flow"]["arithmetic"],
                "Definition:",
            ),
            (cash["tag"], capex["tag"], cash["end"], cash["accession"]),
            f"${_millions(ratios['free_cash_flow']['value'])} million",
            f"{_fact_source(cash)}; {_fact_source(capex)}",
        ),
        ClaimSpec(
            "Latest-quarter total revenue",
            (f"${evidence['quarter_total_revenue']:,.0f} million",),
            (evidence["quarter_total_revenue_line"],),
            f"${evidence['quarter_total_revenue']:,.0f} million",
            f"Exhibit 99.1 line `{evidence['quarter_total_revenue_line']}`",
        ),
        ClaimSpec(
            "Quarter revenue growth",
            (
                f"{evidence['quarter_revenue_growth'] * 100:.4f}%",
                evidence["quarter_revenue_growth_arithmetic"],
            ),
            (evidence["quarter_total_revenue_line"],),
            f"{evidence['quarter_revenue_growth'] * 100:.4f}%",
            f"Exhibit 99.1 line `{evidence['quarter_total_revenue_line']}`",
        ),
        ClaimSpec(
            "Latest-quarter GAAP diluted EPS",
            (f"${evidence['quarter_diluted_eps']:.2f}",),
            (evidence["quarter_diluted_eps_line"],),
            f"${evidence['quarter_diluted_eps']:.2f}",
            f"Exhibit 99.1 line `{evidence['quarter_diluted_eps_line']}`",
        ),
    ]


def _core_items(report: str) -> dict[str, str]:
    start = report.find("### Verified Core Claims")
    end = report.find("### Verified Peer Comparison", start)
    if start < 0:
        return {}
    block = report[start : end if end >= 0 else len(report)]
    return {match.group("label").strip(): match.group("body").strip() for match in CORE_ITEM_RE.finditer(block)}


def _audit_core_claims(
    report: str, facts: dict[str, Any], ratios: dict[str, Any], evidence: dict[str, Any]
) -> list[VerificationMark]:
    items = _core_items(report)
    marks: list[VerificationMark] = []
    for spec in _claim_specs(facts, ratios, evidence):
        body = items.get(spec.label)
        if body is None:
            marks.append(
                VerificationMark(
                    claim=spec.label,
                    mark="unsupported",
                    explanation="The required claim is absent from the verified core-claims block.",
                    correction=spec.correction,
                    source=spec.source,
                )
            )
            continue
        missing_values = [token for token in spec.expected_tokens if token not in body]
        missing_sources = [token for token in spec.source_tokens if token not in body]
        if missing_values:
            marks.append(
                VerificationMark(
                    claim=spec.label,
                    mark="wrong",
                    explanation="The report does not match the saved value or arithmetic: " + ", ".join(missing_values),
                    correction=spec.correction,
                    source=spec.source,
                )
            )
        elif missing_sources:
            marks.append(
                VerificationMark(
                    claim=spec.label,
                    mark="unsupported",
                    explanation="The number lacks required saved-run evidence: " + ", ".join(missing_sources),
                    correction=spec.correction,
                    source=spec.source,
                )
            )
        else:
            marks.append(
                VerificationMark(
                    claim=spec.label,
                    mark="correct",
                    explanation="The stated value, arithmetic, definition when required, and source match the saved run.",
                    source=spec.source,
                )
            )
    return marks


def _audit_line_citations(report: str, run_folder: Path) -> list[VerificationMark]:
    filing_paths = {
        "10-K": run_folder / "latest_10-K.txt",
        "10-Q": run_folder / "latest_10-Q.txt",
        "EX-99.1": run_folder / "earnings_release_EX-99.1.txt",
    }
    marks: list[VerificationMark] = []
    # The Investment Advisor's thesis is outside the verifier's scope.
    checked_report = report.split("## 5. Investment Recommendation", 1)[0]
    for filing_name, line_number_text in LINE_CITATION_RE.findall(checked_report):
        line_number = int(line_number_text)
        path = filing_paths[filing_name]
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        if 1 <= line_number <= len(lines) and lines[line_number - 1].strip():
            marks.append(
                VerificationMark(
                    claim=f"{filing_name} Line {line_number}",
                    mark="correct",
                    explanation="The cited line exists in the saved filing text.",
                    source=lines[line_number - 1].strip(),
                )
            )
        else:
            marks.append(
                VerificationMark(
                    claim=f"{filing_name} Line {line_number}",
                    mark="unsupported",
                    explanation="The cited line is absent or blank in the saved filing text.",
                )
            )
    return marks


def audit_saved_run(run_folder: Path, report_path: Path | None = None) -> VerificationResult:
    report_file = report_path or run_folder / "report.md"
    report = report_file.read_text(encoding="utf-8")
    facts = _read_json(run_folder / "facts.json")
    ratios = _read_json(run_folder / "ratios.json")
    evidence = _read_json(run_folder / "release_evidence.json")
    marks = _audit_core_claims(report, facts, ratios, evidence)
    marks.extend(_audit_line_citations(report, run_folder))
    return VerificationResult(
        verified=bool(marks) and all(mark.mark == "correct" for mark in marks),
        marks=marks,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_folder", type=Path, help="Saved run folder under outputs/")
    parser.add_argument("--report", type=Path, help="Alternate report to verify against the run evidence")
    parser.add_argument("--output", type=Path, help="Write the JSON result to this path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deterministic = audit_saved_run(args.run_folder, args.report)
    output: dict[str, Any] = {"deterministic": deterministic.to_dict()}
    rendered = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(rendered)
    return 0 if deterministic.verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
