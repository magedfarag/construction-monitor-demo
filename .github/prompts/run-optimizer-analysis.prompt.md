---
description: "Run the Copilot optimizer workflow for this repository: import data, analyze for issues, review fix plans, apply approved changes. Use when: running periodic optimizer review, investigating prompt waste, applying recommendations."
name: "Run Optimizer Analysis"
argument-hint: "Mode: live | historical. For historical, path to export file and format."
agent: "agent"
---

# Run the Optimizer Analysis Workflow

The optimizer lives at `COPILOT_OPTIMIZER_HOME` (default: `~/.copilot-optimizer`). Run bootstrap first if not already done.

```powershell
Set-Location $env:COPILOT_OPTIMIZER_HOME
# Historical
node src/index.mjs import --repo <THIS_REPO_PATH> --input <EXPORT_FILE> --format <FORMAT>
# Analyze
node src/index.mjs analyze --repo <THIS_REPO_PATH> --mode historical
# Apply approved fixes
node src/index.mjs apply-approved-fixes --repo <THIS_REPO_PATH>
# Verify
node src/index.mjs doctor --repo <THIS_REPO_PATH>
```

Review reports in `var/repos/<repo-key>/reports/` and fix plans in `var/repos/<repo-key>/fix-plans/pending/` before applying.
