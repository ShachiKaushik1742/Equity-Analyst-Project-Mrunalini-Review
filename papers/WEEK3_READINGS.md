# Week 3 Reading Bundle

This folder records the Week 3 readings used to choose and implement the agent framework.

## Required readings

1. Garry Kasparov, "The Chess Master and the Computer," *The New York Review of Books*, February 11, 2010.
   - Read online: <https://www.nybooks.com/articles/2010/02/11/the-chess-master-and-the-computer/>
   - The article remains at the publisher's site. It is not copied into this public repository.
   - Lab 03 process: Python fixes the normal role order, but the Strategy Manager model can select one role for one revision; code executes that bounded retry.
2. OpenAI Agents SDK first page.
   - Read online: <https://openai.github.io/openai-agents-python/>
   - Local licensed copy: [`openai-agents-sdk/FIRST_PAGE.md`](openai-agents-sdk/FIRST_PAGE.md)
   - Framework choice: **OpenAI Agents SDK**. The local Python version is 3.13.15, and the current SDK supports Python 3.10 or later.
   - Financial research example: <https://github.com/openai/openai-agents-python/tree/main/examples/financial_research_agent>
   - Local verifier reference: [`openai-agents-sdk/financial_research_agent/verifier_agent.py`](openai-agents-sdk/financial_research_agent/verifier_agent.py)

The local OpenAI source files are from the official MIT-licensed repository. The included `LICENSE` file preserves the upstream terms.

## Optional readings

1. Anthropic, "Building effective agents" (2024).
   - Read online: <https://www.anthropic.com/research/building-effective-agents>
   - The Manager resembles the orchestrator-workers workflow when it coordinates specialist roles. The Verifier resembles the evaluator-optimizer workflow because it evaluates a draft and returns evidence-based corrections.
2. Francis and Zhang (2026), Section 3.1.
   - Local paper: [`../FRL-CanAIReplaceAnalyst.pdf`](../FRL-CanAIReplaceAnalyst.pdf)
   - One-line answer: a coordinating manager decides which role runs, when it runs, and what context it receives; a fixed graph makes those decisions in code.

## Implementation target

Replicate the OpenAI financial-research `VerificationAgent` for this desk. Keep its core pattern: a final agent receives a report plus allowed evidence and returns a structured verification result. Adapt the checks to SEC filing text, XBRL facts, and calculated ratios. Code performs exact numeric checks before the model judges whether a cited line supports the number's period and definition.
