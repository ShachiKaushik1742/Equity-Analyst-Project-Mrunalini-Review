"""CrewAI Flow for the fixed equity-research desk process.

The graph, not an LLM, fixes the normal execution order.  The Strategy
Manager can request at most one deterministic, code-selected revision before
the Verifier always runs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from crewai.flow import Flow, listen, start
from pydantic import BaseModel, Field

from desk import (
    FINANCIAL_ANALYST_SYSTEM,
    INVESTMENT_ADVISOR_SYSTEM,
    RESEARCH_ANALYST_SYSTEM,
    STRATEGY_MANAGER_SYSTEM,
    Filing,
    extract_10k_excerpts,
    extract_release_excerpts,
    format_millions,
    get_model_client,
    verified_financial_claims,
    write_json,
)
from verifier_agent import audit_saved_run


REQUIRED_REPORT_SECTIONS = (
    "## 1. Overview",
    "## 2. Market Positioning and Growth Outlook",
    "## 3. Valuation Insights",
    "## 4. Future Developments and Strategic Recommendations",
    "## 5. Investment Recommendation",
)


class EquityResearchState(BaseModel):
    """Typed state shared by every Flow node."""

    run_folder: str = ""
    model: str = ""
    research_output: str = ""
    financial_output: str = ""
    advisor_output: str = ""
    manager_output: str = ""
    report_path: str = ""
    verifier_path: str = ""
    revision_role: str = ""
    node_order: list[str] = Field(default_factory=list)


class EquityResearchFlow(Flow[EquityResearchState]):
    """Fixed CrewAI process: steps -> three specialists -> manager -> verifier."""

    def _folder(self) -> Path:
        folder = Path(self.state.run_folder)
        if not folder.is_dir():
            raise FileNotFoundError(f"Saved run folder does not exist: {folder}")
        return folder

    def _artifacts(self) -> dict[str, Any]:
        folder = self._folder()
        metadata = json.loads((folder / "run_metadata.json").read_text(encoding="utf-8"))
        return {
            "metadata": metadata,
            "filings": {name: Filing(**value) for name, value in metadata["filings"].items()},
            "facts": json.loads((folder / "facts.json").read_text(encoding="utf-8")),
            "ratios": json.loads((folder / "ratios.json").read_text(encoding="utf-8")),
            "evidence": json.loads((folder / "release_evidence.json").read_text(encoding="utf-8")),
            "peers": json.loads((folder / "peers.json").read_text(encoding="utf-8")),
        }

    def _record(self, node: str, input_value: Any, output_value: Any) -> None:
        folder = self._folder()
        artifact_folder = folder / "flow_artifacts"
        artifact_folder.mkdir(exist_ok=True)
        write_json(artifact_folder / f"{len(self.state.node_order):02d}_{node}_input.json", input_value)
        if isinstance(output_value, str):
            (artifact_folder / f"{len(self.state.node_order):02d}_{node}_output.md").write_text(
                output_value.rstrip() + "\n", encoding="utf-8"
            )
        else:
            write_json(artifact_folder / f"{len(self.state.node_order):02d}_{node}_output.json", output_value)
        self.state.node_order.append(node)

    def _chat(
        self,
        system: str,
        payload: dict[str, Any],
        *,
        max_tokens: int,
        temperature: float = 0.2,
        json_output: bool = False,
    ) -> str:
        client, configured_model = get_model_client(Path(__file__).with_name(".env"))
        model = self.state.model or configured_model
        self.state.model = model
        options: dict[str, Any] = {}
        if json_output:
            options["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            **options,
        )
        return response.choices[0].message.content or ""

    @start()
    def steps(self) -> str:
        """Confirm that the seven data-desk steps produced the required evidence."""
        print("Node: steps", flush=True)
        required = (
            "run_metadata.json",
            "facts.json",
            "ratios.json",
            "release_evidence.json",
            "peers.json",
            "latest_10-K.txt",
            "earnings_release_EX-99.1.txt",
        )
        missing = [name for name in required if not (self._folder() / name).exists()]
        if missing:
            raise FileNotFoundError("The seven desk steps are incomplete: " + ", ".join(missing))
        output = "Seven saved data steps are ready."
        self._record("steps", {"run_folder": self.state.run_folder}, {"status": output})
        return output

    @listen(steps)
    def research_analyst(self) -> str:
        print("Node: Research Analyst", flush=True)
        folder = self._folder()
        payload = {
            "task": "Analyze the business model, competition, catalysts, and recent developments. Cite a saved filing line for every claim.",
            "context": {
                "10-K_excerpts": extract_10k_excerpts((folder / "latest_10-K.txt").read_text(encoding="utf-8")),
                "earnings_release_excerpts": extract_release_excerpts(
                    (folder / "earnings_release_EX-99.1.txt").read_text(encoding="utf-8")
                ),
            },
            "expected_output": "Markdown with the three headings specified by the Research Analyst instructions.",
        }
        self.state.research_output = self._chat(RESEARCH_ANALYST_SYSTEM, payload, max_tokens=1400)
        self._record("research_analyst", payload, self.state.research_output)
        return self.state.research_output

    def _financial_payload(self) -> tuple[dict[str, Any], str, list[str]]:
        data = self._artifacts()
        verified = verified_financial_claims(
            data["filings"], data["facts"], data["ratios"], data["evidence"], data["peers"]
        )
        payload = {
            "task": "Analyze the saved statements and ratios. Copy the code-verified block without changing or recalculating a value.",
            "context": {
                "source_filings": {name: asdict(filing) for name, filing in data["filings"].items()},
                "verified_claims_from_calculator": verified,
                "step_4_facts": data["facts"],
                "step_5_ratios": data["ratios"],
                "step_6_quarter_evidence": data["evidence"],
                "step_7_peers": data["peers"],
            },
            "expected_output": "Markdown with statement, valuation, quarter, and peer sections plus all 11 verified claims.",
        }
        facts, ratios, evidence = data["facts"], data["ratios"], data["evidence"]
        tokens = [
            f"${format_millions(facts['total_revenue']['value'])} million",
            f"{ratios['operating_margin']['value'] * 100:.4f}%",
            f"${float(facts['diluted_eps']['value']):.2f}",
            f"${float(evidence['quarter_total_revenue']):,.0f} million",
            f"${float(evidence['quarter_diluted_eps']):.2f}",
        ]
        return payload, verified, tokens

    @listen(research_analyst)
    def financial_analyst(self) -> str:
        print("Node: Financial Analyst", flush=True)
        payload, verified, tokens = self._financial_payload()
        output = self._chat(FINANCIAL_ANALYST_SYSTEM, payload, max_tokens=2400)
        self.state.financial_output = output if all(token in output for token in tokens) else verified
        self._record("financial_analyst", payload, self.state.financial_output)
        return self.state.financial_output

    @listen(financial_analyst)
    def investment_advisor(self) -> str:
        print("Node: Investment Advisor", flush=True)
        payload = {
            "task": "Synthesize the two analyst outputs into a Buy, Hold, or Sell thesis and state one deciding number.",
            "context": {
                "research_analyst_output": self.state.research_output,
                "financial_analyst_output": self.state.financial_output,
            },
            "expected_output": "Markdown with Investment Thesis, Recommendation, and The Deciding Number.",
        }
        self.state.advisor_output = self._chat(INVESTMENT_ADVISOR_SYSTEM, payload, max_tokens=1000)
        self._record("investment_advisor", payload, self.state.advisor_output)
        return self.state.advisor_output

    def _revision_target(self) -> Literal["Research Analyst", "Financial Analyst", "Investment Advisor", ""]:
        research_ok = all(
            heading in self.state.research_output
            for heading in ("### Business Model and Operations", "### Competitive Position and Moat", "### Catalysts and Recent Developments")
        ) and ("[10-K Line" in self.state.research_output or "[EX-99.1 Line" in self.state.research_output)
        _, _, financial_tokens = self._financial_payload()
        financial_ok = all(token in self.state.financial_output for token in financial_tokens)
        advisor_lower = self.state.advisor_output.lower()
        advisor_ok = all(
            heading in self.state.advisor_output
            for heading in ("### Investment Thesis", "### Recommendation", "### The Deciding Number")
        ) and any(word in advisor_lower for word in ("buy", "hold", "sell"))
        if not research_ok:
            return "Research Analyst"
        if not financial_ok:
            return "Financial Analyst"
        if not advisor_ok:
            return "Investment Advisor"
        return ""

    @listen(investment_advisor)
    def strategy_manager(self) -> str:
        print("Node: Strategy Manager", flush=True)
        target = self._revision_target()
        self.state.revision_role = target
        if target == "Research Analyst":
            folder = self._folder()
            payload = {
                "task": "One allowed revision: restore every required heading and add a saved filing-line citation to every claim.",
                "context": {
                    "previous_draft": self.state.research_output,
                    "10-K_excerpts": extract_10k_excerpts((folder / "latest_10-K.txt").read_text(encoding="utf-8")),
                },
                "expected_output": "A corrected Research Analyst draft.",
            }
            self.state.research_output = self._chat(RESEARCH_ANALYST_SYSTEM, payload, max_tokens=1600, temperature=0.1)
        elif target == "Financial Analyst":
            payload, verified, _ = self._financial_payload()
            payload["task"] = "One allowed revision: copy the verified claims exactly and do not recalculate them."
            revised = self._chat(FINANCIAL_ANALYST_SYSTEM, payload, max_tokens=2600, temperature=0)
            self.state.financial_output = revised or verified
        elif target == "Investment Advisor":
            payload = {
                "task": "One allowed revision: include all three required headings, Buy/Hold/Sell, and one deciding number.",
                "context": {
                    "research_analyst_output": self.state.research_output,
                    "financial_analyst_output": self.state.financial_output,
                    "previous_draft": self.state.advisor_output,
                },
                "expected_output": "A corrected Investment Advisor draft.",
            }
            self.state.advisor_output = self._chat(INVESTMENT_ADVISOR_SYSTEM, payload, max_tokens=1200, temperature=0.1)

        manager_payload = {
            "task": "Compile the supplied work into the five required report parts. Return JSON with report_markdown. Do not choose the next role; code has already handled the single revision slot.",
            "context": {
                "research_analyst_output": self.state.research_output,
                "financial_analyst_output": self.state.financial_output,
                "investment_advisor_output": self.state.advisor_output,
            },
            "expected_output": {"format": "JSON", "required_report_headings": REQUIRED_REPORT_SECTIONS},
        }
        raw = self._chat(STRATEGY_MANAGER_SYSTEM, manager_payload, max_tokens=3200, temperature=0.1, json_output=True)
        try:
            report = str(json.loads(raw).get("report_markdown", "")).strip()
        except json.JSONDecodeError:
            report = ""
        if not all(section in report for section in REQUIRED_REPORT_SECTIONS):
            report = (
                f"## 1. Overview\n\n{self.state.research_output}\n\n"
                f"## 2. Market Positioning and Growth Outlook\n\n{self.state.research_output}\n\n"
                f"## 3. Valuation Insights\n\n{self.state.financial_output}\n\n"
                f"## 4. Future Developments and Strategic Recommendations\n\n{self.state.research_output}\n\n"
                f"## 5. Investment Recommendation\n\n{self.state.advisor_output}"
            )
        data = self._artifacts()
        filings = data["filings"]
        run_time = data["metadata"].get("run_time", datetime.now().astimezone().isoformat())
        header = (
            f"# Filings Read: 10-K (accession: {filings['10-K'].accession}), "
            f"10-Q (accession: {filings['10-Q'].accession}), "
            f"8-K (accession: {filings['earnings_8-K'].accession})\n"
            f"Run Time: {run_time}\n\n"
        )
        report_path = self._folder() / "report.md"
        report_path.write_text(header + report.rstrip() + "\n", encoding="utf-8")
        self.state.manager_output = report
        self.state.report_path = str(report_path)
        self._record("strategy_manager", manager_payload, {"revision_role": target, "report_markdown": report})
        return report

    @listen(strategy_manager)
    def verifier(self) -> dict[str, Any]:
        print("Node: Verifier", flush=True)
        result = audit_saved_run(self._folder())
        output = result.to_dict()
        path = self._folder() / "verification.json"
        write_json(path, output)
        self.state.verifier_path = str(path)
        self._record(
            "verifier",
            {
                "report": self.state.report_path,
                "allowed_evidence": ["facts.json", "ratios.json", "release_evidence.json", "saved filing texts"],
                "excluded": "Investment Advisor thesis",
            },
            output,
        )
        return output


def run_flow(run_folder: Path, model: str = "") -> dict[str, Any]:
    flow = EquityResearchFlow()
    result = flow.kickoff(inputs={"run_folder": str(run_folder), "model": model})
    return result if isinstance(result, dict) else {"result": str(result)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_folder", type=Path)
    parser.add_argument("--model", default="")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        result = audit_saved_run(args.run_folder)
        output = result.to_dict()
        write_json(args.run_folder / "verification.json", output)
    else:
        output = run_flow(args.run_folder, args.model)
    print(json.dumps(output, indent=2))
    return 0 if output.get("verified", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
