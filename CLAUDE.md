# CLAUDE.md
Two-person course project building an agentic workflow (see SPEC.md).

## Checks
No application code yet, so there are no checks to run. Update this section when tests or lint are added.

## Rules
- Never edit anything in `eval/` without asking first.
- No personal data in code, fixtures, logs or prompts.
- Secrets live in `.env`, which is never committed or read. Copy it from `.env.example`.
- Log notable prompts in `docs/prompt-log.md`.
