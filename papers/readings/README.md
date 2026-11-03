# Week 3 Reading Bundle

This folder records the Week 3 readings used to choose and implement the agent framework.

## Required readings

1. Garry Kasparov, "The Chess Master and the Computer," *The New York Review of Books*, February 11, 2010.
   - Read online: <https://www.nybooks.com/articles/2010/02/11/the-chess-master-and-the-computer/>
   - The article remains at the publisher's site. It is not copied into this public repository.
   - Lab 03 process: CrewAI Flow decorators fix every normal hand-off; Python also selects the one bounded revision target from explicit checks.
2. CrewAI first page and Flows page.
   - First page: <https://docs.crewai.com/>
   - Flows: <https://docs.crewai.com/en/concepts/flows>
   - Framework choice: **CrewAI 1.15.34**. Its official package requires Python 3.10 through 3.13, so local Python 3.13.15 is supported.
   - Implementation: [`../../crewai_flow.py`](../../crewai_flow.py)

## Optional readings

1. Anthropic, "Building effective agents" (2024).
   - Read online: <https://www.anthropic.com/research/building-effective-agents>
   - The Manager resembles the orchestrator-workers workflow when it coordinates specialist roles. The Verifier resembles the evaluator-optimizer workflow because it evaluates a draft and returns evidence-based corrections.
2. Francis and Zhang (2026), Section 3.1.
   - Local paper: [`../FRL-CanAIReplaceAnalyst.pdf`](../FRL-CanAIReplaceAnalyst.pdf)
   - One-line answer: a coordinating manager decides which role runs, when it runs, and what context it receives; a fixed graph makes those decisions in code.

## Implementation target

Replicate the paper's final evidence-checking agent as the last CrewAI Flow node.
It receives the compiled report and allowed SEC evidence and returns a
structured verification result. Python performs exact checks of values,
arithmetic, definitions, and cited filing lines.
