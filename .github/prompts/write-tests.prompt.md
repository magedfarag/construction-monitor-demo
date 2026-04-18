---
description: "Write tests for a specific change. Covers unit, integration, and e2e levels. Use when: adding test coverage for new code, verifying a bug fix, hardening an existing module."
name: "Write Tests"
argument-hint: "What to test (file or feature), test type (unit / integration / e2e), acceptance bar"
agent: "agent"
---

# Write Tests

Steps to follow:
1. Read the target file or feature. Identify the functions, endpoints, or flows to cover.
2. Reuse existing fixtures, helpers, and mocks. Do not introduce new test infrastructure unless nothing suitable exists.
3. Generate only the minimum test set for the stated acceptance bar.
4. Keep assertions explicit and deterministic.
5. Summarize: new test files, reused fixtures, coverage gaps remaining out of scope.
