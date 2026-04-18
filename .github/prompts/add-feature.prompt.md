---
description: "Add a new feature to this repository. Covers reading existing patterns, scoping the change, wiring the implementation, and writing a test stub. Use when: building a new capability, extending an existing feature, implementing a user story."
name: "Add Feature"
argument-hint: "Feature name or user story, affected layer(s) (backend / frontend / both), acceptance criteria"
agent: "agent"
---

# Add a Feature

Steps to follow:
1. Read the existing code in the area closest to the new feature. Identify naming conventions, patterns, and dependencies.
2. Scope the change: list the files that need to change and why.
3. Implement backend changes first (data model, service, API), then frontend changes (component, API call, UI wiring).
4. Add a test stub for the new behavior. Mark it passing or skip with a reason.
5. Verify no existing behavior changes beyond the stated feature scope.
6. Summarize: added behavior, changed files, test coverage, and any follow-up needed.
