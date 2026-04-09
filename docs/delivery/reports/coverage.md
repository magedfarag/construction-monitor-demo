# Test Coverage Report

**Generated:** 2026-04-05 (Release-grade quality pass)
**Suite:** full suite (`tests/unit/` + `tests/integration/`)
**Packages measured:** `app/` + `src/`

## Summary

| Metric | Value |
|--------|-------|
| Backend tests passing | 1682 |
| Backend tests skipped | 11 |
| Backend tests failing | 0 |
| Frontend e2e tests | 184 (18 spec files, all 184 discovered, 7 spec files run-validated) |
| Overall line coverage | **74%** |
| Statements covered | ~7 952 / 10 725 |

## How to regenerate

```bash
python -m pytest tests/unit/ \
  --cov=app --cov=src \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  -q
```

HTML report is written to `htmlcov/index.html` (git-ignored).

## CI coverage gate

The CI pipeline (`ci.yml`) enforces `--cov-fail-under=60` as release floor.
Coverage HTML is uploaded as a GitHub Actions artifact (`coverage-report-<app_mode>`)
for each matrix run (`demo` / `staging` / `production`).

## Module coverage highlights

| Module | Coverage |
|--------|---------|
| `src/models/analytics.py` | 100% |
| `src/models/aoi.py` | 100% |
| `src/models/compare.py` | 100% |
| `src/models/event_search.py` | 100% |
| `src/services/aoi_store.py` | 100% |
| `src/connectors/gdelt.py` | 97% |
| `src/services/telemetry_store.py` | 98% |
| `src/models/canonical_event.py` | 99% |
| `app/resilience/circuit_breaker.py` | 97% |
| `src/storage/database.py` | 0% (requires live PostGIS — skipped in CI) |
| `src/storage/models.py` | 0% (requires live PostGIS — skipped in CI) |

> **Note:** `src/storage/` is intentionally 0% in unit tests.
> Integration coverage is obtained when a live PostGIS instance is available.
> See `tests/integration/test_db_schema.py` (4 tests, skipped without DB).
