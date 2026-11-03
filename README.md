# Equity Research Desk

This repository contains the filing-first data desk and four-role report app for FIN 67110 Labs 02 and 03.

## Setup

Create an isolated Python environment and install the declared packages:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The local `.env` file must contain:

```text
API_KEY=your-model-provider-key
SEC_USER_AGENT="Your Name your-email@purdue.edu"
BASE_URL="https://genai.rcac.purdue.edu/api"
MODEL="llama3.1:latest"
```

The `.env` file is ignored by Git. Never force-add it.

## Run the seven steps and four roles

```bash
.venv/bin/python desk.py COST --peers WMT,TGT,BJ --price 992.13
```

The example uses Costco's October 27, 2026 close. Replace it with the dated price assigned by the instructor if that price differs. SEC filings do not contain a market price.

The full command runs the seven data steps. It then runs the Research Analyst, Financial Analyst, Investment Advisor, and Strategy Manager. It saves `report.md` and `role_outputs.json` in the run folder.

Each role receives only `task`, `context`, and `expected_output` in its JSON
input. The Financial Analyst can call an allowlisted Python calculator for an
additional ratio. The model does not calculate that result.

Run only the seven data steps:

```bash
.venv/bin/python desk.py COST --peers WMT,TGT,BJ --price 992.13 --no-roles
```

Run one numbered step:

```bash
.venv/bin/python desk.py COST --step 4
```

Run the tests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Apple assignment command:

```bash
.venv/bin/python desk.py AAPL --peers MSFT,GOOGL,DELL --price 338.19
```

The Apple price is the unadjusted July 29, 2026 close. The saved Apple report is
marked `fallback` because the Purdue model endpoint timed out twice. The Lab 03
instructions state that a labeled fallback report counts when the provider is down.

Each full run saves filing text, facts, calculations, release evidence, peer facts, and source metadata under `outputs/`.

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex helped build and test the filing reader. Human audit
marks remain the student's responsibility.

Any remaining errors are my own.
