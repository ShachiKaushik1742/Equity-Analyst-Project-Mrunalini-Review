# Apple Report — Human Audit

Report: `outputs/AAPL_20261028_202525/report.md`

Errors (wrong + unsupported): 0

Missing claims: 0

Partner: Shachi Kaushik

Partner claim 1 and mark: Total net sales — correct

Partner claim 2 and mark: Quarter diluted EPS — correct

Use only these marks: `correct`, `wrong`, `unsupported`, or `missing`.

| #   | Claim                           | Report value               | Filing evidence                                                                                                                                   | Human mark | Notes                             |
| ---: | ------------------------------- | --------------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------- |
| 1   | Total revenue / total net sales | $416,161 million           | 10-K; `RevenueFromContractWithCustomerExcludingAssessedTax`; 2025-09-27                                                                           | Correct    | Definition: Apple total net sales |
| 2   | Revenue growth                  | 6.4255%                    | `416161 / 391035 - 1`                                                                                                                             | Correct    | Recalculate by hand               |
| 3   | Operating income and margin     | $133,050 million; 31.9708% | 10-K; `OperatingIncomeLoss`; `133050 / 416161`                                                                                                    | Correct    | Same revenue definition           |
| 4   | Net income                      | $112,010 million           | 10-K; `NetIncomeLoss`; 2025-09-27                                                                                                                 | Correct    |                                   |
| 5   | Annual diluted EPS              | $7.46                      | 10-K; `EarningsPerShareDiluted`; 2025-09-27                                                                                                       | Correct    |                                   |
| 6   | Return on average equity        | 171.4224%                  | `112010 / ((73733 + 56950) / 2)`                                                                                                                  | Correct    | Recalculate by hand               |
| 7   | Debt to equity                  | 1.2298x                    | `(78328 + 12350) / 73733`                                                                                                                         | Correct    | Includes current portion          |
| 8   | Free cash flow                  | $98,767 million            | `111482 - 12715`                                                                                                                                  | Correct    | Defined in the report             |
| 9   | Quarter total net sales         | $109,417 million           | Exhibit 99.1: `109,417`; 8-K 0000320193-26-000018                                                                                                 | Correct    |                                   |
| 10  | Quarter revenue growth          | 16.3565%                   | `109417 / 94036 - 1`                                                                                                                              | Correct    |                                   |
| 11  | Quarter diluted EPS             | $2.02                      | Exhibit 99.1: diluted EPS row                                                                                                                     | Correct    |                                   |
| 12  | P/E                             | 45.3338x                   | `338.19 / 7.46`                                                                                                                                   | Correct    | July 29, 2026 close               |
| 13  | MSFT operating margin           | 46.7808%                   | MSFT 10-K; `155237 / 331839`                                                                                                                      | Correct    | Same total-revenue definition     |
| 14  | GOOGL operating margin          | 32.0326%                   | GOOGL 10-K; `129039 / 402836`                                                                                                                     | Correct    | Same total-revenue definition     |
| 15  | DELL operating margin           | 7.1773%                    | DELL 10-K; `8149 / 113538`                                                                                                                        | Correct    | Same total-revenue definition     |
| 16  | All 5 required report parts     | Present                    | Overview; Market Positioning and Growth Outlook; Valuation Insights; Future Developments and Strategic Recommendations; Investment Recommendation | Correct    |                                   |
| 17  | Recommendation is consistent    | HOLD                       | Report valuation evidence: 45.3338x P/E, 6.4255% annual revenue growth, 31.9708% operating margin, and 16.3565% quarterly revenue growth          | Correct    |                                   |

## Human sign-off

I opened the filings and checked the marks above. I did not rely on an AI-generated audit.

Student name: Mrunalini Pol

Date: 28 October 2026
