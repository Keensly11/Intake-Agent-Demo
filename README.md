# Lab Sample Intake Agent

A single-agent workflow that reads lab sample submission forms, extracts structured fields using a local LLM, validates them against business rules, and returns either a clean record or a flagged one for human review.

Built as a focused demo of core agentic workflow design: **extract → validate → decide**, with an explicit distinction between "confidently correct" and "needs a human" — rather than silently trusting every LLM output.

## Why this design

Two decisions worth calling out, since they reflect how I think about agentic systems generally, not just this demo:

1. **Validation is a separate, deterministic step — not part of the LLM call.** The LLM's job is only to extract what's on the page (including empty fields when a value is genuinely missing — it's explicitly instructed not to invent data). A plain Python function then checks the result against real rules: required fields present, dates fully specified, priority/sample-type values from an approved set. Keeping this separate means the validation logic is testable, predictable, and auditable — not dependent on the LLM's judgment call each time.

2. **Every record gets a status, not just a pass/fail.** `CLEAN` records can flow straight through; `NEEDS_REVIEW` records carry a specific, human-readable list of what's wrong. This mirrors a pattern I used in a previous project (an AI lead-enrichment pipeline) after discovering that silently trusting uncertain AI output is a real production risk — it's better for an agent to say "I'm not sure, here's why" than to confidently pass along something wrong.

## How it works

```
Document (.txt) → LLM extraction (structured JSON, local model via Ollama)
                        ↓
        Deterministic validation (required fields, date format, allowed values)
                        ↓
        CLEAN record  OR  NEEDS_REVIEW record + specific issues list
```

## Tech stack

- **LLM**: Llama 3.1 8B, run locally via [Ollama](https://ollama.com) — no API keys, no rate limits, fully reproducible for anyone running this demo
- **Language**: Python

## Setup

```bash
pip install ollama
ollama pull llama3.1:8b
python intake_agent.py
```

Processes every form in `sample_forms/`, prints a summary per form, and writes full structured results to `processed_records.json`.

## Test cases included

- `form_1_clean.txt` — all fields present and valid → `CLEAN`
- `form_2_missing_field.txt` — storage condition left blank → flags missing required field
- `form_3_bad_value.txt` — incomplete date (`07/2026`) and invalid priority (`"Whenever is fine"`) → flags both

## Possible extensions

- PDF/scanned document support (OCR pre-processing before extraction)
- Configurable validation rules per document type, rather than hardcoded constants
- Confidence scoring on individual extracted fields, not just rule-based validation
