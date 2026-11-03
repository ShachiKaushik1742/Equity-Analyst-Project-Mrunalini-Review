# Lab 02 Validation

Run date: 2026-10-27

## Commands used

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python desk.py COST --peers WMT,TGT,BJ --price 904.70
.venv/bin/python desk.py WMT --peers COST,TGT,BJ
```

All three automated tests that existed on the run date passed. The current
submission suite contains nine tests. Both full runs printed Steps 1 through 7
and ended with a saved folder.

## Costco known-answer check

Filings selected by the desk:

- 10-K: accession `0000909832-26-000093`, fiscal year ended 2026-08-30.
- 10-Q: accession `0000909832-26-000051`, quarter ended 2026-05-10.
- Earnings 8-K: accession `0000909832-26-000084`, accepted 2026-09-24, Item 2.02, with Exhibit 99.1.

The figures below use USD millions except per-share data and ratios. The annual facts all have period end 2026-08-30 and come from the selected 10-K accession.

| # | Core claim | Filing fact or arithmetic | Check |
|---:|---|---|---|
| 1 | Total revenue | 303,154; tag `RevenueFromContractWithCustomerExcludingAssessedTax` | Correct |
| 2 | Revenue growth | 303,154 / 275,235 - 1 = 10.1437% | Correct |
| 3 | Operating income and margin | 11,685; 11,685 / 303,154 = 3.8545% | Correct |
| 4 | Net income attributable to Costco | 9,226; tag `NetIncomeLoss` | Correct |
| 5 | GAAP diluted EPS | $20.76; tag `EarningsPerShareDiluted` | Correct |
| 6 | Return on average equity | 9,226 / ((35,803 + 29,164) / 2) = 28.4021% | Correct |
| 7 | Debt to equity | (3,914 + 2,248) / 35,803 = 0.1721 | Correct |
| 8 | Free cash flow | 15,817 - 6,435 = 9,382 | Correct |
| 9 | Latest-quarter total revenue | 95,723 | Correct |
| 10 | Quarter revenue growth | 95,723 / 86,156 - 1 = 11.1043% | Correct |
| 11 | Latest-quarter GAAP diluted EPS | $6.75 | Correct |

The P/E run used $904.70, the September 23, 2026 close immediately before the September 24 earnings release: $904.70 / $20.76 = 43.5790. This price came from [an external historical-price source](https://stockanalysis.com/stocks/cost/history/), not EDGAR. Replace it if the instructor used another assigned price.

## Peer-definition check

Each peer uses its own latest 10-K, its own fiscal-year end, and operating income divided by total revenue:

| Company | Fiscal-year end | Total-revenue tag | Total revenue | Operating income | Operating margin |
|---|---|---|---:|---:|---:|
| Walmart | 2026-01-31 | `Revenues` | 713,163 | 29,825 | 4.1821% |
| Target | 2026-01-31 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 104,780 | 5,117 | 4.8836% |
| BJ's Wholesale | 2026-01-31 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 21,457.274 | 816.604 | 3.8057% |

The Walmart portability run independently returned total revenue of 713,163, operating income of 29,825, and an operating margin of 4.1821%. It also accepted Walmart's plural label, “Total revenues,” without treating it as a different definition.

## Definition trap

Costco reports net sales and membership fees separately. The desk uses total revenue, not net sales, for revenue growth and operating margin. Mixing Costco net sales with a peer's total revenue would make the comparison inconsistent.

## Later completion

- Mrunalini confirmed that Shachi Kaushik saw the live evidence and completed
  the required partner checks.
- The required in-person explanation was completed.
- The Apple Checkpoint 1 run uses the assigned dated close of $338.19.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex helped build and test the filing reader. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
