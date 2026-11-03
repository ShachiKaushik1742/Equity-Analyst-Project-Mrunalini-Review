# Lab 03 Notes

## Gap check

The Financial Analyst is the role most likely to get a number wrong. A model can recalculate a supplied ratio, produce a plausible rounded answer, and omit the source definition. The first trial did this: it changed verified revenue growth from 10.1437% to 9.99% and quarter revenue growth from 11.1043% to 10.11%.

The harness now gives the role a calculator-built block and refuses a draft that changes or omits a required value. It permits one revision. If that revision still fails, the harness uses the calculator-built block instead of the rejected model text.

For literal compliance with the Lab 03 request, each role input JSON contains
only `task`, `context`, and `expected_output`. The Financial Analyst can request
an allowlisted additional ratio through the official SDK's calculator tool.
Python returns the value, arithmetic, definition, and source fact names. The
model does not calculate the ratio.

## Human sign-off

Anthropic's financial-services repository says its agents draft analyst work for review by a qualified professional. The agents do not make investment recommendations, execute transactions, bind risk, post to a ledger, or approve onboarding. Every output is staged for human sign-off.

Those agents add domain skills, data connectors, workflow-specific controls, and an explicit professional-review boundary. This desk had EDGAR data and a calculator, but it initially lacked a strong refusal check between plausible model prose and a report ready for review.

Source: <https://github.com/anthropics/financial-services>

## Costco run

- Report: `outputs/COST_20261028_194706/report.md`
- Tuesday close supplied to the desk: $992.13 on 2026-10-27.
- P/E: 47.7905x, calculated as `992.13 / 20.76`.
- The five required parts are present.
- The eleven core claims are present with filing accessions, XBRL tags or Exhibit 99.1 lines, periods, definitions, and arithmetic.
- The human audit template is `audits/COST_20261028_human_audit.md`.

## Completed student and partner work for Checkpoint 1

1. Apple was the instructor-approved Checkpoint 1 company.
2. The desk was run on Apple with MSFT, GOOGL, and DELL as peers and with a dated close.
3. Mrunalini completed the Apple human audit without AI supplying the marks.
4. Shachi Kaushik checked two core claims: total net sales and quarter diluted EPS.
5. Both partner marks are recorded at the top of `audits/AAPL_20261028_human_audit.md`.

## Apple assignment run

- Apple was the assigned company. The command used was
  `.venv/bin/python desk.py AAPL --peers MSFT,GOOGL,DELL --price 338.19`.
- The $338.19 input is Apple's unadjusted July 29, 2026 close, the last close
  before the July 30 earnings release. Source: <https://investor.apple.com/stock-price/>.
- The latest Item 2.02 earnings 8-K available during the run was accession
  `0000320193-26-000018`, accepted July 30, 2026 at 16:30:28.
- Apple calls its top line “Total net sales.” The release reader now accepts
  that label and excludes footnote markers from the arithmetic.
- The saved run is `outputs/AAPL_20261028_202525`.
- The Purdue provider timed out on the Research Analyst request at both the
  original limit and one 180-second retry. The report is therefore labeled
  `fallback`, as the course instructions require when the provider is down.
- The report has the five required parts, 11 core claims, P/E, and the MSFT,
  GOOGL, and DELL peer margins.
- The human audit is `audits/AAPL_20261028_human_audit.md`.
