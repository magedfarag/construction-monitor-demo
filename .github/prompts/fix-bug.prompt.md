---
description: "Debug and fix a reported bug. Covers root cause tracing, minimal patch, regression test, and change summary. Use when: investigating a defect, patching an error, resolving unexpected behavior."
name: "Fix a Bug"
argument-hint: "Bug description or error message, affected feature or file path if known"
agent: "agent"
---

# Fix a Bug

Steps to follow:
1. Read the error message or symptom. Identify the impacted layer.
2. Trace the call path from the entry point to the failure site. Read each file in the path before writing code.
3. State the root cause explicitly.
4. Write the minimal patch — do not refactor surrounding code unless it is the direct cause.
5. Add or update a test that would have caught this bug.
6. Summarize: root cause, files changed, test added, regression risk.
