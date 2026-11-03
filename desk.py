#!/usr/bin/env python3
"""Filing-first data desk used by the FIN 67110 CrewAI Flow."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

try:
    import requests
except ImportError:  # Calculation-only tests do not need network packages.
    requests = None  # type: ignore[assignment]

try:
    from bs4 import BeautifulSoup
except ImportError:  # Calculation-only tests do not parse filing HTML.
    BeautifulSoup = None  # type: ignore[assignment,misc]

try:
    from openai import OpenAI
except ImportError:  # Calculation-only tests do not call a model.
    OpenAI = Any  # type: ignore[assignment,misc]


SEC_WWW = "https://www.sec.gov"
SEC_DATA = "https://data.sec.gov"
TICKERS_URL = f"{SEC_WWW}/files/company_tickers.json"


FACT_SPECS: dict[str, dict[str, Any]] = {
    "total_revenue": {
        "tags": ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"],
        "unit": "USD",
        "duration": True,
    },
    "operating_income": {
        "tags": ["OperatingIncomeLoss"],
        "unit": "USD",
        "duration": True,
    },
    "net_income": {
        "tags": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
        "unit": "USD",
        "duration": True,
    },
    "diluted_eps": {
        "tags": ["EarningsPerShareDiluted"],
        "unit": "USD/shares",
        "duration": True,
    },
    "stockholders_equity": {
        "tags": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
        "unit": "USD",
        "duration": False,
    },
    "long_term_debt_noncurrent": {
        "tags": [
            "LongTermDebtNoncurrent",
            "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
            "LongTermDebtAndCapitalLeaseObligationsNoncurrent",
        ],
        "unit": "USD",
        "duration": False,
    },
    "long_term_debt_current": {
        "tags": [
            "LongTermDebtCurrent",
            "CurrentPortionOfLongTermDebt",
            "LongTermDebtAndFinanceLeaseObligationsCurrent",
            "LongTermDebtAndCapitalLeaseObligationsCurrent",
        ],
        "unit": "USD",
        "duration": False,
    },
    "cash_from_operations": {
        "tags": ["NetCashProvidedByUsedInOperatingActivities"],
        "unit": "USD",
        "duration": True,
    },
    "capital_expenditures": {
        "tags": ["PaymentsToAcquirePropertyPlantAndEquipment"],
        "unit": "USD",
        "duration": True,
    },
}


@dataclass(frozen=True)
class Company:
    ticker: str
    cik: str
    name: str


@dataclass(frozen=True)
class Filing:
    form: str
    accession: str
    filing_date: str
    report_date: str
    accepted: str
    primary_document: str
    items: str = ""

    @property
    def accession_compact(self) -> str:
        return self.accession.replace("-", "")

    def directory_url(self, cik: str) -> str:
        return f"{SEC_WWW}/Archives/edgar/data/{int(cik)}/{self.accession_compact}/"

    def index_url(self, cik: str) -> str:
        return f"{self.directory_url(cik)}{self.accession}-index.htm"

    def document_url(self, cik: str) -> str:
        return f"{self.directory_url(cik)}{self.primary_document}"


class EdgarClient:
    """Small SEC client that identifies every request with the required User-Agent."""

    def __init__(self, user_agent: str) -> None:
        if not user_agent or "@" not in user_agent:
            raise ValueError("SEC_USER_AGENT must contain your name and email address.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov",
            }
        )

    def get(self, url: str) -> requests.Response:
        headers = dict(self.session.headers)
        headers["Host"] = "data.sec.gov" if url.startswith(SEC_DATA) else "www.sec.gov"
        response = self.session.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        time.sleep(0.12)
        return response

    def json(self, url: str) -> dict[str, Any]:
        return self.get(url).json()

    def text(self, url: str) -> str:
        return self.get(url).text


def load_local_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Create it before running the desk.")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def resolve_ticker(client: EdgarClient, ticker: str) -> Company:
    ticker = ticker.upper().strip()
    rows = client.json(TICKERS_URL)
    for row in rows.values():
        if row["ticker"].upper() == ticker:
            return Company(ticker=ticker, cik=f"{int(row['cik_str']):010d}", name=row["title"])
    raise ValueError(f"Ticker {ticker!r} was not found in SEC company_tickers.json.")


def rows_from_columns(columns: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not columns:
        return []
    keys = [key for key, value in columns.items() if isinstance(value, list)]
    count = max((len(columns[key]) for key in keys), default=0)
    return [
        {key: columns[key][index] if index < len(columns[key]) else "" for key in keys}
        for index in range(count)
    ]


def filing_from_row(row: dict[str, Any]) -> Filing:
    return Filing(
        form=str(row.get("form", "")),
        accession=str(row.get("accessionNumber", "")),
        filing_date=str(row.get("filingDate", "")),
        report_date=str(row.get("reportDate", "")),
        accepted=str(row.get("acceptanceDateTime", "")),
        primary_document=str(row.get("primaryDocument", "")),
        items=str(row.get("items", "")),
    )


def all_submission_rows(client: EdgarClient, cik: str) -> list[dict[str, Any]]:
    submission = client.json(f"{SEC_DATA}/submissions/CIK{cik}.json")
    rows = rows_from_columns(submission.get("filings", {}).get("recent", {}))
    for older in submission.get("filings", {}).get("files", []):
        name = older.get("name")
        if name:
            rows.extend(rows_from_columns(client.json(f"{SEC_DATA}/submissions/{name}")))
    return rows


def select_filings(client: EdgarClient, cik: str) -> dict[str, Filing]:
    filings = [filing_from_row(row) for row in all_submission_rows(client, cik)]
    filings.sort(key=lambda item: (item.accepted, item.filing_date, item.accession), reverse=True)

    def first(predicate: Any, label: str) -> Filing:
        try:
            return next(filing for filing in filings if predicate(filing))
        except StopIteration as exc:
            raise RuntimeError(f"No {label} filing was found for CIK {cik}.") from exc

    return {
        "10-K": first(lambda item: item.form == "10-K", "10-K"),
        "10-Q": first(lambda item: item.form == "10-Q", "10-Q"),
        "earnings_8-K": first(
            lambda item: item.form == "8-K" and "2.02" in item.items,
            "Item 2.02 earnings 8-K",
        ),
    }


def accepted_from_index(client: EdgarClient, filing: Filing, cik: str) -> str:
    soup = BeautifulSoup(client.text(filing.index_url(cik)), "html.parser")
    for head in soup.select(".infoHead"):
        if head.get_text(" ", strip=True).lower() == "accepted":
            value = head.find_next_sibling(class_="info")
            if value:
                return value.get_text(" ", strip=True)
    return filing.accepted


def exhibit_url(client: EdgarClient, filing: Filing, cik: str, exhibit_type: str) -> str:
    index_url = filing.index_url(cik)
    soup = BeautifulSoup(client.text(index_url), "html.parser")
    for row in soup.select("table.tableFile tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        filing_type = cells[3].get_text(" ", strip=True).upper()
        if filing_type == exhibit_type.upper():
            link = cells[2].find("a", href=True)
            if link:
                return urljoin(index_url, link["href"])
    raise RuntimeError(f"{exhibit_type} was not found in {index_url}.")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    lines = [re.sub(r"\s+", " ", line).strip() for line in soup.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line) + "\n"


def table_rows(html: str) -> list[str]:
    if BeautifulSoup is None:
        class TableParser(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.in_cell = False
                self.cell_parts: list[str] = []
                self.current_row: list[str] = []
                self.rows: list[str] = []

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                if tag in {"td", "th"}:
                    self.in_cell = True
                    self.cell_parts = []

            def handle_data(self, data: str) -> None:
                if self.in_cell:
                    self.cell_parts.append(data)

            def handle_endtag(self, tag: str) -> None:
                if tag in {"td", "th"} and self.in_cell:
                    value = re.sub(r"\s+", " ", " ".join(self.cell_parts)).strip()
                    if value:
                        self.current_row.append(value)
                    self.in_cell = False
                elif tag == "tr" and self.current_row:
                    self.rows.append(" | ".join(self.current_row))
                    self.current_row = []

        parser = TableParser()
        parser.feed(html)
        return parser.rows

    soup = BeautifulSoup(html, "html.parser")
    rows: list[str] = []
    for row in soup.find_all("tr"):
        values = [re.sub(r"\s+", " ", cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        values = [value for value in values if value]
        if values:
            rows.append(" | ".join(values))
    return rows


def annual_points(company_facts: dict[str, Any], tag: str, unit: str) -> list[dict[str, Any]]:
    concept = company_facts.get("facts", {}).get("us-gaap", {}).get(tag, {})
    points = concept.get("units", {}).get(unit, [])
    return [
        point
        for point in points
        if point.get("form") == "10-K" and point.get("end") and point.get("val") is not None
    ]


def duration_days(point: dict[str, Any]) -> int:
    try:
        return (datetime.fromisoformat(point["end"]) - datetime.fromisoformat(point["start"])).days
    except (KeyError, TypeError, ValueError):
        return -1


def choose_tag(
    company_facts: dict[str, Any], candidates: Iterable[str], unit: str
) -> tuple[str, list[dict[str, Any]]]:
    choices: list[tuple[str, list[dict[str, Any]], str]] = []
    for candidate in candidates:
        points = annual_points(company_facts, candidate, unit)
        if points:
            choices.append((candidate, points, max(str(point["end"]) for point in points)))
    if not choices:
        raise KeyError(f"None of the candidate tags has annual {unit} facts: {', '.join(candidates)}")
    newest = max(choice[2] for choice in choices)
    # Candidate order resolves ties. For revenue, Revenues is preferred because the audit uses total revenue.
    return next((tag, points) for tag, points, latest in choices if latest == newest)


def choose_point(
    points: list[dict[str, Any]],
    period_end: str,
    accession: str,
    duration: bool,
) -> dict[str, Any]:
    matches = [point for point in points if point.get("end") == period_end]
    if not matches:
        raise KeyError(f"No 10-K fact ends on {period_end}.")
    same_filing = [point for point in matches if point.get("accn") == accession]
    pool = same_filing or matches
    if duration:
        annual = [point for point in pool if 300 <= duration_days(point) <= 400]
        pool = annual or pool
        return max(pool, key=lambda point: (duration_days(point), str(point.get("filed", ""))))
    return max(pool, key=lambda point: str(point.get("filed", "")))


def prior_period_end(
    points: list[dict[str, Any]],
    current_end: str,
    accession: str,
    duration: bool,
) -> str:
    pool = [point for point in points if point.get("end") < current_end]
    same_filing = [point for point in pool if point.get("accn") == accession]
    if same_filing:
        pool = same_filing
    if duration:
        annual = [point for point in pool if 300 <= duration_days(point) <= 400]
        pool = annual or pool
    if not pool:
        raise KeyError(f"No prior-year 10-K fact exists before {current_end}.")
    return max(str(point["end"]) for point in pool)


def extract_facts(
    company_facts: dict[str, Any],
    filing: Filing,
    fact_names: Iterable[str] | None = None,
) -> dict[str, dict[str, Any]]:
    fiscal_end = filing.report_date
    output: dict[str, dict[str, Any]] = {}
    selected_names = list(fact_names) if fact_names is not None else list(FACT_SPECS)
    for name in selected_names:
        spec = FACT_SPECS[name]
        tag, points = choose_tag(company_facts, spec["tags"], spec["unit"])
        current = choose_point(points, fiscal_end, filing.accession, spec["duration"])
        previous_end = prior_period_end(points, fiscal_end, filing.accession, spec["duration"])
        previous = choose_point(points, previous_end, filing.accession, spec["duration"])
        output[name] = {
            "tag": tag,
            "unit": spec["unit"],
            "value": current["val"],
            "prior_value": previous["val"],
            "start": current.get("start"),
            "end": current["end"],
            "prior_start": previous.get("start"),
            "prior_end": previous["end"],
            "form": current.get("form"),
            "filed": current.get("filed"),
            "accession": current.get("accn"),
            "fiscal_year": current.get("fy"),
            "fiscal_period": current.get("fp"),
        }
    return output


def extract_peer_facts(company_facts: dict[str, Any], filing: Filing) -> dict[str, dict[str, Any]]:
    """Read every main-company fact for a peer and state when a fact is unavailable."""
    output: dict[str, dict[str, Any]] = {}
    for name in FACT_SPECS:
        try:
            output.update(extract_facts(company_facts, filing, (name,)))
        except KeyError as error:
            output[name] = {
                "available": False,
                "reason": str(error),
                "form": filing.form,
                "accession": filing.accession,
                "end": filing.report_date,
            }
    for required_name in ("total_revenue", "operating_income"):
        if output[required_name].get("available") is False:
            raise KeyError(f"Peer is missing required {required_name}: {output[required_name]['reason']}")
    return output


def safe_divide(numerator: float, denominator: float, label: str) -> float:
    if denominator == 0:
        raise ZeroDivisionError(f"Cannot calculate {label}: denominator is zero.")
    return numerator / denominator


def calculate_ratios(facts: dict[str, dict[str, Any]], price: float | None) -> dict[str, dict[str, Any]]:
    revenue = float(facts["total_revenue"]["value"])
    prior_revenue = float(facts["total_revenue"]["prior_value"])
    operating_income = float(facts["operating_income"]["value"])
    net_income = float(facts["net_income"]["value"])
    equity = float(facts["stockholders_equity"]["value"])
    prior_equity = float(facts["stockholders_equity"]["prior_value"])
    debt_noncurrent = float(facts["long_term_debt_noncurrent"]["value"])
    debt_current = float(facts["long_term_debt_current"]["value"])
    operating_cash = float(facts["cash_from_operations"]["value"])
    capex = float(facts["capital_expenditures"]["value"])
    diluted_eps = float(facts["diluted_eps"]["value"])
    average_equity = (equity + prior_equity) / 2

    ratios: dict[str, dict[str, Any]] = {
        "revenue_growth": {
            "value": safe_divide(revenue, prior_revenue, "revenue growth") - 1,
            "arithmetic": f"{revenue:g} / {prior_revenue:g} - 1",
        },
        "operating_margin": {
            "value": safe_divide(operating_income, revenue, "operating margin"),
            "arithmetic": f"{operating_income:g} / {revenue:g}",
            "definition": "operating income / total revenue",
        },
        "return_on_average_equity": {
            "value": safe_divide(net_income, average_equity, "return on average equity"),
            "arithmetic": f"{net_income:g} / (({equity:g} + {prior_equity:g}) / 2)",
        },
        "debt_to_equity": {
            "value": safe_divide(debt_noncurrent + debt_current, equity, "debt to equity"),
            "arithmetic": f"({debt_noncurrent:g} + {debt_current:g}) / {equity:g}",
            "definition": "(long-term debt noncurrent + current portion) / stockholders' equity",
        },
        "free_cash_flow": {
            "value": operating_cash - capex,
            "arithmetic": f"{operating_cash:g} - {capex:g}",
            "definition": "cash from operations - additions to property and equipment",
        },
    }
    if price is not None:
        ratios["price_to_earnings"] = {
            "value": safe_divide(price, diluted_eps, "P/E"),
            "arithmetic": f"{price:g} / {diluted_eps:g}",
            "price": price,
        }
    return ratios


def calculate_additional_ratio(
    ratio_name: str,
    facts: dict[str, dict[str, Any]],
    ratios: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Calculate an approved extra ratio in code for the Financial Analyst."""
    revenue = float(facts["total_revenue"]["value"])
    calculations: dict[str, tuple[float, str, str, list[str]]] = {
        "net_margin": (
            safe_divide(float(facts["net_income"]["value"]), revenue, "net margin"),
            f"{float(facts['net_income']['value']):g} / {revenue:g}",
            "net income / total revenue",
            ["net_income", "total_revenue"],
        ),
        "free_cash_flow_margin": (
            safe_divide(float(ratios["free_cash_flow"]["value"]), revenue, "free cash flow margin"),
            f"{float(ratios['free_cash_flow']['value']):g} / {revenue:g}",
            "free cash flow / total revenue",
            ["cash_from_operations", "capital_expenditures", "total_revenue"],
        ),
        "cash_from_operations_margin": (
            safe_divide(
                float(facts["cash_from_operations"]["value"]),
                revenue,
                "cash from operations margin",
            ),
            f"{float(facts['cash_from_operations']['value']):g} / {revenue:g}",
            "cash from operations / total revenue",
            ["cash_from_operations", "total_revenue"],
        ),
        "capital_expenditure_intensity": (
            safe_divide(
                float(facts["capital_expenditures"]["value"]),
                revenue,
                "capital expenditure intensity",
            ),
            f"{float(facts['capital_expenditures']['value']):g} / {revenue:g}",
            "additions to property and equipment / total revenue",
            ["capital_expenditures", "total_revenue"],
        ),
    }
    if ratio_name not in calculations:
        raise ValueError(f"Unsupported calculator ratio: {ratio_name}")
    value, arithmetic, definition, source_fact_names = calculations[ratio_name]
    return {
        "name": ratio_name,
        "value": value,
        "arithmetic": arithmetic,
        "definition": definition,
        "source_fact_names": source_fact_names,
    }


def numeric_cells(row: str) -> list[float]:
    values = re.findall(r"(?<![A-Za-z])\(?\$?(\d[\d,]*(?:\.\d+)?)\)?", row)
    return [float(value.replace(",", "")) for value in values]


def release_evidence(html: str) -> dict[str, Any]:
    rows = table_rows(html)
    # Preserve the filer's label. Some issuers use "total revenue," while
    # other issuers use "total net sales" for the same top-line concept.
    total_revenue = next(
        (row for row in rows if re.search(r"\btotal (?:revenues?|net sales)\b", row, re.I)),
        "",
    )
    diluted_candidates = [row for row in rows if re.match(r"^Diluted\b", row, re.I)]
    currency_candidates = [row for row in diluted_candidates if "$" in row]
    diluted_eps = max(currency_candidates or diluted_candidates, key=len, default="")
    if not total_revenue or not diluted_eps:
        raise RuntimeError("The release table did not expose both total revenue and diluted EPS rows.")
    revenue_for_numbers = re.sub(
        r"(?i)(total (?:revenues?|net sales))\s*\(\d+\)",
        r"\1",
        total_revenue,
        count=1,
    )
    revenue_values = numeric_cells(revenue_for_numbers)
    eps_values = numeric_cells(diluted_eps)
    if len(revenue_values) < 2 or not eps_values:
        raise RuntimeError("The release rows did not contain the expected numeric values.")
    current_revenue, prior_revenue = revenue_values[:2]
    return {
        "quarter_total_revenue_line": total_revenue,
        "quarter_total_revenue": current_revenue,
        "prior_year_quarter_total_revenue": prior_revenue,
        "quarter_revenue_growth": safe_divide(current_revenue, prior_revenue, "quarter revenue growth") - 1,
        "quarter_revenue_growth_arithmetic": f"{current_revenue:g} / {prior_revenue:g} - 1",
        "quarter_diluted_eps_line": diluted_eps,
        "quarter_diluted_eps": eps_values[0],
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_filing(label: str, filing: Filing, accepted: str, cik: str) -> None:
    print(
        f"  {label}: {filing.accession} | report {filing.report_date} | "
        f"Accepted {accepted} | {filing.index_url(cik)}"
    )


def print_facts(facts: dict[str, dict[str, Any]]) -> None:
    for name, fact in facts.items():
        print(
            f"  {name}: {fact['value']} {fact['unit']} | prior {fact['prior_value']} | "
            f"tag {fact['tag']} | period {fact['end']} | {fact['form']} {fact['accession']}"
        )


def print_ratios(ratios: dict[str, dict[str, Any]]) -> None:
    for name, ratio in ratios.items():
        suffix = "%" if name in {"revenue_growth", "operating_margin", "return_on_average_equity"} else ""
        value = ratio["value"] * 100 if suffix else ratio["value"]
        print(f"  {name}: {value:.4f}{suffix} | {ratio['arithmetic']}")


RESEARCH_ANALYST_SYSTEM = (
    "You are the Research Analyst on an equity-research desk (Francis & Zhang 2026, Figure 1).\n"
    "Analyze the business model, competitive position, catalysts, and recent developments.\n"
    "Use only the provided 10-K Business and MD&A excerpts and the earnings release.\n"
    "Quote a provided line citation for every claim. Do not invent a line or claim.\n"
    "Use these exact headings:\n"
    "   ### Business Model and Operations\n"
    "   ### Competitive Position and Moat\n"
    "   ### Catalysts and Recent Developments"
)

FINANCIAL_ANALYST_SYSTEM = (
    "You are the Financial Analyst on an equity-research desk (Francis & Zhang 2026, Figure 1).\n"
    "Your task is to perform statement analysis from step 4's facts, step 5's ratios, "
    "step 6's quarter evidence, and step 7's peer data.\n"
    "State the source filing and the line, or the XBRL tag, period, and accession, for every number.\n"
    "Copy each ratio's supplied arithmetic. Do not calculate a new number in the model.\n"
    "If you need an additional approved ratio, call the calculate_ratio tool. "
    "Do not estimate or calculate the tool result yourself.\n"
    "State the definition when a filing offers two definitions.\n"
    "Cover all 11 core claims in the expected output. Use only supplied values.\n"
    "Use these exact headings:\n"
    "   ### Statement Analysis and Trends\n"
    "   ### Valuation Insights and Ratios\n"
    "   ### Latest Quarter Performance\n"
    "   ### Peer Comparisons"
)

INVESTMENT_ADVISOR_SYSTEM = (
    "You are the Investment Advisor on an equity-research desk (Francis & Zhang 2026, Figure 1).\n"
    "Your task is to synthesize the findings of the Research Analyst and the Financial Analyst into an investment thesis and recommendation.\n"
    "Use only the two analyst outputs in the context.\n"
    "State Buy, Hold, or Sell. State the one number that decides the recommendation.\n"
    "Copy that number and its source from the analyst output. Do not add external facts.\n"
    "Use these exact headings:\n"
    "   ### Investment Thesis\n"
    "   ### Recommendation\n"
    "   ### The Deciding Number"
)

STRATEGY_MANAGER_SYSTEM = (
    "You are the Strategy Manager on an equity-research desk (Francis & Zhang 2026, Figure 1).\n"
    "Check the three role outputs for completeness, source support, and consistency.\n"
    "The final report must have exactly five required parts.\n"
    "Return one JSON object with report_markdown.\n"
    "Do not select a role, route, or next step. CrewAI Flow code fixes the order, "
    "and Python has already handled the bounded revision slot.\n"
    "Do not add facts or numbers that are absent from the role outputs."
)


def extract_10k_excerpts(text: str) -> str:
    lines = text.splitlines()
    excerpts: list[str] = []

    i1_start: int | None = None
    for i, line in enumerate(lines):
        clean = line.strip()
        if re.match(r"^item\s+1[\.\:—\-\s]+business", clean, re.I) and i > 200:
            i1_start = i
            break
    if i1_start is None:
        for i, line in enumerate(lines):
            clean = line.strip()
            if re.match(r"^item\s+1[\.\:—\-]", clean, re.I) and i > 500:
                i1_start = i
                break

    if i1_start is not None:
        excerpts.append("=== 10-K ITEM 1 (BUSINESS) ===")
        count = 0
        for idx in range(i1_start, min(i1_start + 180, len(lines))):
            val = lines[idx].strip()
            if val:
                excerpts.append(f"[10-K Line {idx + 1}] {val}")
                count += 1
                if count >= 80:
                    break

    i7_start: int | None = None
    for i, line in enumerate(lines):
        clean = line.strip()
        if re.match(r"^item\s+7[\.\:—\-\s]+management", clean, re.I) and i > 200:
            i7_start = i
            break
    if i7_start is not None:
        excerpts.append("\n=== 10-K ITEM 7 (MD&A) ===")
        count = 0
        for idx in range(i7_start, min(i7_start + 180, len(lines))):
            val = lines[idx].strip()
            if val:
                excerpts.append(f"[10-K Line {idx + 1}] {val}")
                count += 1
                if count >= 80:
                    break

    if not excerpts:
        for idx, line in enumerate(lines[:120]):
            val = line.strip()
            if val:
                excerpts.append(f"[10-K Line {idx + 1}] {val}")

    return "\n".join(excerpts)


def extract_release_excerpts(text: str) -> str:
    lines = text.splitlines()
    excerpts: list[str] = ["=== EXHIBIT 99.1 (EARNINGS RELEASE) ==="]
    count = 0
    for idx, line in enumerate(lines):
        val = line.strip()
        if val:
            excerpts.append(f"[EX-99.1 Line {idx + 1}] {val}")
            count += 1
            if count >= 100:
                break
    return "\n".join(excerpts)


def format_millions(value: float | int) -> str:
    return f"{float(value) / 1_000_000:,.3f}".rstrip("0").rstrip(".")


def verified_financial_claims(
    filings: dict[str, Filing],
    facts: dict[str, dict[str, Any]],
    ratios: dict[str, dict[str, Any]],
    evidence: dict[str, Any],
    peers: dict[str, Any],
) -> str:
    """Create the sourced financial block in code. Models must not recalculate it."""
    ten_k = filings["10-K"]
    earnings_8k = filings["earnings_8-K"]

    def fact_source(name: str) -> str:
        fact = facts[name]
        return (
            f"10-K accession {fact['accession']}; XBRL tag `{fact['tag']}`; "
            f"period ended {fact['end']}"
        )

    lines = [
        "### Verified Core Claims — Copy Without Recalculation",
        "",
        f"1. **Total revenue:** ${format_millions(facts['total_revenue']['value'])} million. "
        f"Source: {fact_source('total_revenue')}.",
        f"2. **Revenue growth:** {ratios['revenue_growth']['value'] * 100:.4f}%. "
        f"Arithmetic: `{ratios['revenue_growth']['arithmetic']}`. Source: {fact_source('total_revenue')} "
        f"and prior period ended {facts['total_revenue']['prior_end']} in the same filing.",
        f"3. **Operating income and operating margin:** "
        f"${format_millions(facts['operating_income']['value'])} million and "
        f"{ratios['operating_margin']['value'] * 100:.4f}%. "
        f"Arithmetic: `{ratios['operating_margin']['arithmetic']}`. "
        f"Definition: operating income / total revenue. Source: {fact_source('operating_income')} "
        f"and {fact_source('total_revenue')}.",
        f"4. **Net income attributable to the company:** "
        f"${format_millions(facts['net_income']['value'])} million. Source: {fact_source('net_income')}.",
        f"5. **GAAP diluted EPS:** ${float(facts['diluted_eps']['value']):.2f}. "
        f"Source: {fact_source('diluted_eps')}.",
        f"6. **Return on average equity:** {ratios['return_on_average_equity']['value'] * 100:.4f}%. "
        f"Arithmetic: `{ratios['return_on_average_equity']['arithmetic']}`. "
        f"Definition: net income / average current-year and prior-year stockholders' equity. "
        f"Sources: {fact_source('net_income')} and {fact_source('stockholders_equity')}.",
        f"7. **Debt to equity:** {ratios['debt_to_equity']['value']:.4f}x. "
        f"Arithmetic: `{ratios['debt_to_equity']['arithmetic']}`. "
        f"Definition: long-term debt, including its current portion, / stockholders' equity. "
        f"Sources: {fact_source('long_term_debt_noncurrent')}; "
        f"{fact_source('long_term_debt_current')}; and {fact_source('stockholders_equity')}.",
        f"8. **Free cash flow:** ${format_millions(ratios['free_cash_flow']['value'])} million. "
        f"Arithmetic: `{ratios['free_cash_flow']['arithmetic']}`. "
        f"Definition: cash from operations - additions to property and equipment. "
        f"Sources: {fact_source('cash_from_operations')} and {fact_source('capital_expenditures')}.",
        f"9. **Latest-quarter total revenue:** ${float(evidence['quarter_total_revenue']):,.0f} million. "
        f"Source: 8-K accession {earnings_8k.accession}, Exhibit 99.1 line "
        f"`{evidence['quarter_total_revenue_line']}`.",
        f"10. **Quarter revenue growth:** {evidence['quarter_revenue_growth'] * 100:.4f}%. "
        f"Arithmetic: `{evidence['quarter_revenue_growth_arithmetic']}`. "
        f"Source: 8-K accession {earnings_8k.accession}, Exhibit 99.1 line "
        f"`{evidence['quarter_total_revenue_line']}`.",
        f"11. **Latest-quarter GAAP diluted EPS:** ${float(evidence['quarter_diluted_eps']):.2f}. "
        f"Source: 8-K accession {earnings_8k.accession}, Exhibit 99.1 line "
        f"`{evidence['quarter_diluted_eps_line']}`.",
    ]

    if "price_to_earnings" in ratios:
        ratio = ratios["price_to_earnings"]
        lines.extend(
            [
                "",
                f"**P/E:** {ratio['value']:.4f}x. Arithmetic: `{ratio['arithmetic']}`. "
                f"The price is the user-supplied dated close. EPS source: {fact_source('diluted_eps')}.",
            ]
        )

    lines.extend(["", "### Verified Peer Comparison — Total-Revenue Definition"])
    for ticker, peer in peers.items():
        revenue = peer["facts"]["total_revenue"]
        operating = peer["facts"]["operating_income"]
        margin = peer["operating_margin"]
        lines.append(
            f"- **{ticker}:** operating margin {margin['value'] * 100:.4f}%. "
            f"Arithmetic: `{margin['arithmetic']}`. Definition: operating income / total revenue. "
            f"Source: 10-K accession {peer['filing']['accession']}; period ended {revenue['end']}; "
            f"revenue tag `{revenue['tag']}`; operating-income tag `{operating['tag']}`."
        )
    return "\n".join(lines)


def get_model_client(env_path: Path) -> tuple[OpenAI, str]:
    env = load_local_env(env_path)
    api_key = env.get("API_KEY", "")
    if not api_key:
        raise ValueError("Missing API_KEY in .env")
    base_url = env.get("BASE_URL", "https://genai.rcac.purdue.edu/api")
    model = env.get("MODEL", "llama3.1:latest")
    # Purdue-hosted models can need more than 45 seconds for filing excerpts.
    # Permit one SDK retry, but keep a finite timeout so the course fallback
    # remains available when the provider is down.
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=180.0, max_retries=1)
    return client, model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="SEC ticker symbol, for example a listed company's ticker")
    parser.add_argument("--peers", default="", help="Comma-separated peer tickers")
    parser.add_argument("--price", type=float, help="Share price used only for P/E")
    parser.add_argument("--step", type=int, choices=range(1, 8), help="Run and print only one numbered step")
    parser.add_argument("--output-root", default="outputs", help="Parent folder for saved run artifacts")
    parser.add_argument("--no-roles", action="store_true", help="Skip running the four model roles after step 7")
    return parser.parse_args()


def run() -> Path | None:
    args = parse_args()
    env_path = Path(__file__).with_name(".env")
    env = load_local_env(env_path)
    client = EdgarClient(env.get("SEC_USER_AGENT", ""))
    ticker = args.ticker.upper()
    target = args.step

    company = resolve_ticker(client, ticker)
    if target in (None, 1):
        print(f"Step 1 — Resolve ticker\n  {company.ticker} | CIK {company.cik} | {company.name}")
    if target == 1:
        return None

    filings = select_filings(client, company.cik)
    accepted = {
        label: accepted_from_index(client, filing, company.cik)
        for label, filing in filings.items()
    }
    if target in (None, 2):
        print("Step 2 — Select filings")
        print_filing("latest 10-K", filings["10-K"], accepted["10-K"], company.cik)
        print_filing("latest 10-Q", filings["10-Q"], accepted["10-Q"], company.cik)
        print_filing("latest Item 2.02 8-K", filings["earnings_8-K"], accepted["earnings_8-K"], company.cik)
    if target == 2:
        return None

    run_time = datetime.now().astimezone()
    run_folder = Path(args.output_root) / f"{ticker}_{run_time:%Y%m%d_%H%M%S}"
    run_folder.mkdir(parents=True, exist_ok=False)
    metadata = {
        "company": asdict(company),
        "run_time": run_time.isoformat(),
        "arguments": {
            "ticker": ticker,
            "peers": [peer.strip().upper() for peer in args.peers.split(",") if peer.strip()],
            "price": args.price,
            "step": args.step,
        },
        "filings": {label: asdict(filing) for label, filing in filings.items()},
        "accepted_from_index": accepted,
    }

    release_html = ""
    if target in (None, 3, 6):
        ten_k_html = client.text(filings["10-K"].document_url(company.cik))
        ten_q_html = client.text(filings["10-Q"].document_url(company.cik))
        earnings_8k_html = client.text(filings["earnings_8-K"].document_url(company.cik))
        release_url = exhibit_url(client, filings["earnings_8-K"], company.cik, "EX-99.1")
        release_html = client.text(release_url)
        metadata["release_url"] = release_url
        if target in (None, 3):
            (run_folder / "latest_10-K.txt").write_text(html_to_text(ten_k_html), encoding="utf-8")
            (run_folder / "latest_10-Q.txt").write_text(html_to_text(ten_q_html), encoding="utf-8")
            (run_folder / "earnings_8-K.txt").write_text(html_to_text(earnings_8k_html), encoding="utf-8")
            (run_folder / "earnings_release_EX-99.1.txt").write_text(html_to_text(release_html), encoding="utf-8")
            print(f"Step 3 — Download and save filing text\n  Saved 10-K, 10-Q, earnings 8-K, and EX-99.1 in {run_folder}")
    if target == 3:
        write_json(run_folder / "run_metadata.json", metadata)
        return run_folder

    company_facts_json: dict[str, Any] = {}
    facts: dict[str, dict[str, Any]] = {}
    if target in (None, 4, 5, 7):
        company_facts_json = client.json(f"{SEC_DATA}/api/xbrl/companyfacts/CIK{company.cik}.json")
        facts = extract_facts(company_facts_json, filings["10-K"])
        write_json(run_folder / "facts.json", facts)
        if target in (None, 4):
            print("Step 4 — Read latest fiscal-year XBRL facts")
            print_facts(facts)
    if target == 4:
        write_json(run_folder / "run_metadata.json", metadata)
        return run_folder

    if target in (None, 5):
        ratios = calculate_ratios(facts, args.price)
        write_json(run_folder / "ratios.json", ratios)
        print("Step 5 — Calculate ratios in code")
        print_ratios(ratios)
    if target == 5:
        write_json(run_folder / "run_metadata.json", metadata)
        return run_folder

    if target in (None, 6):
        if not release_html:
            release_url = exhibit_url(client, filings["earnings_8-K"], company.cik, "EX-99.1")
            release_html = client.text(release_url)
            metadata["release_url"] = release_url
        evidence = release_evidence(release_html)
        write_json(run_folder / "release_evidence.json", evidence)
        print("Step 6 — Read quarter evidence from Exhibit 99.1")
        print(f"  Total revenue: {evidence['quarter_total_revenue_line']}")
        print(
            f"  Quarter revenue growth: {evidence['quarter_revenue_growth'] * 100:.4f}% | "
            f"{evidence['quarter_revenue_growth_arithmetic']}"
        )
        print(f"  Diluted EPS: {evidence['quarter_diluted_eps_line']}")
    if target == 6:
        write_json(run_folder / "run_metadata.json", metadata)
        return run_folder

    if target in (None, 7):
        peers = [peer.strip().upper() for peer in args.peers.split(",") if peer.strip()]
        peer_results: dict[str, Any] = {}
        print("Step 7 — Read peers on the same total-revenue definition")
        if not peers:
            print("  No peers supplied.")
        for peer_ticker in peers:
            peer_company = resolve_ticker(client, peer_ticker)
            peer_filings = select_filings(client, peer_company.cik)
            peer_company_facts = client.json(f"{SEC_DATA}/api/xbrl/companyfacts/CIK{peer_company.cik}.json")
            peer_facts = extract_peer_facts(peer_company_facts, peer_filings["10-K"])
            peer_revenue = float(peer_facts["total_revenue"]["value"])
            peer_operating_income = float(peer_facts["operating_income"]["value"])
            operating_margin = {
                "value": safe_divide(peer_operating_income, peer_revenue, "peer operating margin"),
                "arithmetic": f"{peer_operating_income:g} / {peer_revenue:g}",
                "definition": "operating income / total revenue",
            }
            peer_results[peer_ticker] = {
                "company": asdict(peer_company),
                "filing": asdict(peer_filings["10-K"]),
                "facts": peer_facts,
                "operating_margin": operating_margin,
            }
            print(f"  {peer_ticker}:")
            for fact_name, fact in peer_facts.items():
                if fact.get("available") is False:
                    print(f"    {fact_name}: unavailable | {fact['reason']}")
                else:
                    print(
                        f"    {fact_name}: {fact['value']} {fact['unit']} | "
                        f"tag {fact['tag']} | period {fact['end']} | {fact['form']} {fact['accession']}"
                    )
            print(
                f"    operating_margin: {operating_margin['value'] * 100:.4f}% | "
                f"{operating_margin['arithmetic']} | {operating_margin['definition']}"
            )
        write_json(run_folder / "peers.json", peer_results)

    write_json(run_folder / "run_metadata.json", metadata)
    print(f"Saved run folder: {run_folder}")

    if target is None and not args.no_roles:
        # Import here to avoid a module cycle: the Flow reuses the data-desk
        # evidence helpers above. CrewAI's decorators fix the role order.
        from crewai_flow import run_flow

        run_flow(run_folder)

    return run_folder


if __name__ == "__main__":
    run()
