# Delivery Artifacts

This folder contains handover material and historical validation outputs that were already present in the repository. They are preserved for delivery and auditability, but they are not the primary source of truth for current behavior.

## Current Authoritative Docs

Use these first:

- [../README.md](../README.md)
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
- [../API.md](../API.md)
- [../DEPLOYMENT.md](../DEPLOYMENT.md)
- [../reference/environment.md](../reference/environment.md)

## Contents

| Path | Notes |
|---|---|
| [handover.md](handover.md) | Project handover narrative carried forward from the repo root |
| [deployment-candidate.md](deployment-candidate.md) | Delivery snapshot for the deployment candidate |
| [reports/](reports/) | Historical status, verification, coverage, and readiness artifacts |

## Reading Guidance

- Treat the files in `reports/` as dated evidence snapshots.
- Prefer the maintained docs tree for setup, architecture, API, and operational guidance.
- If a report conflicts with a maintained doc, the maintained doc wins unless you re-run the validation and update the report.
