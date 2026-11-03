# Reconstructed Lab 03 Prompt — Four-Role Equity-Research App

When you explain something to me, write 80% of the way to ASD-STE100. Keep every number, condition, and hedge.

Add the 4 roles from Figure 1 of Francis & Zhang (2026) on top of my existing 7-step equity-research desk.

Use the official OpenAI Python SDK. Read the model key from `API_KEY` in the `.env` file in this folder. Do not print, save, or log the key.

Use a separate model call for each role. Each role must have its own instructions. The Strategy Manager must send each role one JSON object with only these fields:

- `task`: the work that the role must do.
- `context`: the information that the role may use.
- `expected_output`: the required structure and content.

A role must not use information that is not in its JSON context.

## 1. Research Analyst

Analyze the business model, competitive position, catalysts, and recent developments.

Use only:

- The Business section of the latest 10-K.
- The MD&A section of the latest 10-K.
- The latest earnings release selected by the 7-step desk.

Every claim must quote the applicable filing line. Do not add an unsupported claim.

## 2. Financial Analyst

Perform the statement analysis using only:

- The facts from step 4.
- The ratios from step 5.
- The latest-quarter evidence from step 6.
- The peer facts and operating margins from step 7.

For every number, state the filing and the filing line, or state the XBRL tag, period, and accession number. For every ratio, show the arithmetic that the calculator used.

If a filing gives 2 possible definitions, state the definition beside the number. For example, distinguish total revenue from net sales.

The Financial Analyst can request an additional ratio from the calculator. The model must not calculate a ratio by itself. The calculator must calculate it in code and return the value and arithmetic.

## 3. Investment Advisor

Use only the Research Analyst output and the Financial Analyst output.

Write:

- An investment thesis.
- A `Buy`, `Hold`, or `Sell` recommendation.
- The 1 number that determines the recommendation.

Do not introduce a fact, number, or source that is absent from the 2 role outputs.

## 4. Strategy Manager

Check that the report has these 5 parts:

1. Overview
2. Market Positioning and Growth Outlook
3. Valuation Insights
4. Future Developments and Strategic Recommendations
5. Investment Recommendation

Check that the 5 parts are complete and consistent. If a part fails, send it back to the responsible role once. Give that role the failed requirement and the correction required. After the 1 permitted revision, compile the report. Do not silently add a missing number or unsupported claim.

## Program behavior

- Print each role name when that role runs.
- Keep the ticker as a command-line argument.
- Keep the optional `--peers` list and optional `--price` number.
- Do not put a company name anywhere in the program code.
- Save the final report as Markdown in the current run folder.
- On the report's first line, name every filing read and give its accession number.
- On the report's second line, give the run time.
- Print the saved report path when the program finishes.
- Preserve the source files, facts, ratios, release evidence, peer evidence, role outputs, and Manager checks in the run folder.

When the work is complete, give me:

1. The exact command to install every required package.
2. The exact command to run the desk on a ticker with peers and a price.

Use this Apple example command:

```bash
.venv/bin/python desk.py AAPL --peers MSFT,GOOGL,DELL --price 338.19
```
