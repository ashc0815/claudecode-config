---
name: find
description: Find files and code patterns in the codebase. Use when the user wants to search for specific files, functions, classes, variables, or code patterns.
---

When the user asks to find something, search the codebase thoroughly:

1. Use Glob to find files by name pattern (e.g., `**/*.ts`, `**/config.*`)
2. Use Grep to search file contents for keywords, function names, class names, etc.
3. Report exact file paths and line numbers for each match
4. If $ARGUMENTS is provided, search for that specific term or pattern
5. Summarize what was found concisely

Search strategy:
- Start broad, then narrow down
- Check both file names and file contents
- Include relevant context around matches
