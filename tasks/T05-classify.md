# T05 · Classify events into categories

**Status:** done (LLM path tested only with a fake client)
**Code:** `harness/classify.py` · **Context:** `harness/context/categories.md`, `harness/context/classify_prompt.md`

## Goal
Assign 1–3 category IDs from `categories.md` to each event. Claude does it when
`ANTHROPIC_API_KEY` is set; its reply is checked by code (JSON, known IDs,
max 3), with one retry. On error or when the call/token budget is spent, the
rule-based baseline classifies instead and the event is flagged.
Events with no category go to `needs_review.json`.

## Acceptance check
- `python -m pytest -k "parse_llm or baseline or fall_back or budget"` passes.
- On the fixture with `--classifier baseline`: SYN001 music, SYN002 sports,
  SYN003 gaming, SYN009 arts_culture, SYN011 social.
- Live LLM run: still to do (T08).
