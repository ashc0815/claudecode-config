---
name: ask-user-question
description: Ask the user a clarifying question using a structured multiple-choice prompt. Use when requirements are ambiguous or when the user needs to choose between options before proceeding.
---

When clarification is needed before proceeding with a task:

1. Use the AskUserQuestion tool to present structured options to the user
2. Keep questions clear and specific — one question at a time when possible
3. Provide 2–4 meaningful options that cover the likely choices
4. Include a brief description for each option explaining the trade-offs
5. Wait for the user's answer before taking action

If $ARGUMENTS is provided, use it as the question text or topic to ask about.

Always prefer AskUserQuestion over open-ended text prompts when the user needs to pick between distinct approaches.
