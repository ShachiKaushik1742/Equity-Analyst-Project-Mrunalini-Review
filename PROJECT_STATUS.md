# Project Status and Session Handoff

Last updated: 2026-10-28

Read this file at the start of the next session. It records the verified project state. Do not put API keys or other secret values in this file.

## Repository

- Local folder: `/Users/mrunalinipol/Documents/Codex/2026-10-22/hel`
- Public GitHub repository: <https://github.com/mrunalinipol/Equity-Analyst-Project>
- Branch: `main`
- Student: Mrunalini Pol
- Purdue email: `pol0@purdue.edu`
- Lab partner: Shachi Kaushik

## Secret status

- `.env` exists locally and is ignored by Git.
- `.env` contains `SEC_USER_AGENT` and a Purdue GenAI Studio API key.
- Do not print, quote, commit, or upload the API key.
- The previously exposed key was replaced directly in `.env` on 2026-10-28.
- The public GitHub URL for `.env` returned HTTP 404 during the last verification.

## Completed work

### Lab 01

- `hello.md` exists.
- `AGENTS.md` contains the required explanation instruction.
- `check_env.py` reads `.env` and prints only the first four API-key characters followed by `...`, plus `SEC_USER_AGENT`.
- `.gitignore` excludes `.env`, `.env.*`, `.emv`, `.venv/`, Python cache files, and local application downloads.
- The repository is public and was verified without `.env`.
- The Session 1 Brightspace checkout was previously submitted.

### Week 2 pre-work

- Reading answers and the Costco filing check are in `WEEK2_PREWORK.md`.
- The paper-tool answer identifies EDGAR as the free filings reader.
- Figure 1 is identified as a workflow because code fixes its roles, hand-offs, checks, and revision path.
- The autonomy-slider answer and the unseen-company earnings-prediction limitation are recorded.
- Costco's 2026 10-K check matched net income of $9,226 million and diluted EPS of $20.76 to the XBRL facts for 2026-08-30.

### Lab 02

- `desk.py` implements the seven required data-desk steps without a hard-coded company.
- Required arguments: positional ticker.
- Optional arguments: `--peers`, `--price`, and `--step`.
- The program reads `SEC_USER_AGENT` from `.env` and sends it on SEC requests.
- The program selects the latest 10-K, 10-Q, and Item 2.02 8-K.
- The program saves the filing texts, Exhibit 99.1, facts, ratios, release evidence, peer data, and source metadata.
- Candidate XBRL tags are selected by the newest available fiscal year.
- All main-company facts use the 10-K fiscal-year end selected for revenue.
- Ratio arithmetic is calculated in code and printed.
- `Total revenue`, `Total revenues`, and Apple's `Total net sales` release labels are supported.
- The full audit is in `LAB02_VALIDATION.md`.

Verified Costco run:

- Folder: `outputs/COST_20261027_092436`
- 10-K fiscal-year end: 2026-08-30
- Total revenue: $303.154 billion
- Operating income: $11.685 billion
- Revenue growth: 10.1437%
- Operating margin: 3.8545%
- Return on average equity: 28.4021%
- Debt to equity: 0.1721
- Free cash flow: $9.382 billion
- Diluted EPS: $20.76
- Price used: $904.70 on 2026-09-23
- P/E: 43.5790
- Latest-quarter total revenue: $95.723 billion
- Latest-quarter revenue growth: 11.1043%
- Latest-quarter diluted EPS: $6.75

Verified Walmart portability run:

- Folder: `outputs/WMT_20261027_092443`
- 10-K fiscal-year end: 2026-01-31
- Total revenue: $713.163 billion
- Operating income: $29.825 billion
- Operating margin: 4.1821%
- The run completed all seven steps with Costco, Target, and BJ's Wholesale as peers.

Validation state:

- Python version: 3.13.15.
- Nine automated tests pass.
- `python -m compileall` passes.
- `git diff --check` passes.
- A public GitHub check returned HTTP 200 for the code, validation file, and Costco facts.
- A public GitHub check returned HTTP 404 for `.env`.
- Live run evidence was verified with partner Shachi Kaushik, and partner initials were obtained.
- The two-minute explanation was completed in person.
- The closing price was verified.

### Saved course material

- `papers/FRL-CanAIReplaceAnalyst.pdf` is the 9-page paper titled “Can AI match professional analysts? Evidence from a multi-agent system.”
- The uploaded PDF checksum matched the copy in Downloads.
- `library/lab02_equity_research_desk_prompt.md` contains the reconstructed Lab 02 prompt written approximately 80% toward ASD-STE100.
- `library/lab03_four_role_app_prompt.md` contains the reconstructed Lab 03
  four-role prompt written approximately 80% toward ASD-STE100.

### Lab 03 — completed in the app

- Purdue GenAI Studio is configured through the official OpenAI Python SDK.
- The local `.env` defines `BASE_URL` and `MODEL` in addition to the secret key and SEC User-Agent.
- The live provider test succeeded with `llama3.1:latest`.
- `desk.py` runs four model roles after the seven data steps: Research Analyst, Financial Analyst, Investment Advisor, and Strategy Manager.
- Each role receives a JSON object with its task, allowed context, and expected output.
- Each role input JSON contains exactly `task`, `context`, and `expected_output`.
- The Financial Analyst can call an allowlisted Python calculator tool for an
  additional ratio; the model does not calculate the result.
- The Financial Analyst receives a calculator-built block and must not recalculate it.
- The harness permits one revision when a Financial Analyst draft changes or omits a verified value.
- The harness rejects a Strategy Manager compilation that omits the five parts, the verified values, a research citation, or a sourced deciding number.
- The verified Costco report is `outputs/COST_20261028_194706/report.md`.
- The report uses Costco's 2026-10-27 close of $992.13 and reports P/E of 47.7905x.
- The report states all eleven core claims with filing accessions, XBRL tags or Exhibit 99.1 lines, periods, definitions, and arithmetic.
- Raw role outputs and Manager checks are in `outputs/COST_20261028_194706/role_outputs.json`.
- The blank human audit is `audits/COST_20261028_human_audit.md`. Its marks are intentionally blank.
- `LAB03_NOTES.md` records the observed Financial Analyst error and the human-sign-off reading.

Apple assignment run:

- Command: `.venv/bin/python desk.py AAPL --peers MSFT,GOOGL,DELL --price 338.19`.
- Saved folder: `outputs/AAPL_20261028_202525`.
- Fiscal 2025 total net sales: $416.161 billion.
- Operating income: $133.050 billion.
- Operating margin: 31.9708%.
- Latest-quarter total net sales: $109.417 billion.
- Latest-quarter diluted EPS: $2.02.
- Price: $338.19, the unadjusted July 29, 2026 close.
- P/E: 45.3338x.
- Peers: MSFT, GOOGL, and DELL.
- The Purdue model endpoint timed out twice. The saved report is explicitly
  labeled `fallback`, which the Lab 03 instructions permit when the provider is down.
- Apple report: `outputs/AAPL_20261028_202525/report.md`.
- Apple human-audit worksheet: `audits/AAPL_20261028_human_audit.md`.
- The student confirmed that Apple is the instructor-approved Checkpoint 1 company.
- The student confirmed that Shachi completed both required partner checks.
- The audit names both checked claims and records both marks.
- The Apple peer evidence now attempts all 9 Step 4 concepts for each peer and
  explicitly records a concept as unavailable when EDGAR has no candidate tag.
- Checkpoint 1 was submitted in Brightspace on 2026-10-28 at 8:33 PM.
- Brightspace submission ID: `23584866`.
- Submitted commit permalink:
  <https://github.com/mrunalinipol/Equity-Analyst-Project/commit/c25b468906b1dec8dc66181ca4b9245e2fd23c69>.
- On 2026-10-28, the student instructed the agent to delete this submission and
  never submit coursework again. Brightspace gives learners no delete control.
  The instructor must delete submission `23584866`.
- Permanent operating rule: prepare files only. Do not submit, upload, send,
  publish, or turn in coursework unless the student explicitly reverses this rule.

## Main commands

Create the environment and install packages:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run Costco:

```bash
.venv/bin/python desk.py COST --peers WMT,TGT,BJ --price 904.70
```

Run Walmart:

```bash
.venv/bin/python desk.py WMT --peers COST,TGT,BJ
```

Run one step:

```bash
.venv/bin/python desk.py COST --step 4
```

Run the tests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Remaining actions

1. Ask the instructor to delete Brightspace submission `23584866`.
2. Confirm that `.env` is absent from the public final commit.
3. Submit the final commit permalink in Brightspace. The agent must not perform
   this submission.

## Working rules for the next session

- Keep company-specific known answers in tests and saved evidence. Do not hard-code a company in `desk.py`.
- Keep every financial number tied to a filing line or to an XBRL tag, period, and accession.
- Use the same definition across peer comparisons.
- Do not claim that partner checks or in-person work are complete unless the student confirms them.
- Update this file before the next session ends.
