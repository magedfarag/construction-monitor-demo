# Testing Strategy

The repository contains backend tests, frontend unit tests, frontend build validation, and Playwright end-to-end coverage.

This page documents the commands and expectations that are still supported by the current codebase without freezing old pass counts into the docs.

## Backend

The backend test harness is intentionally isolated:

- `tests/conftest.py` forces `APP_MODE=staging`
- Redis, database, and live provider credentials are disabled by default
- `API_KEY` is cleared unless a specific test overrides it

Run the full backend suite:

```powershell
.\.venv\Scripts\python -m pytest tests -q
```

Useful follow-up commands:

```powershell
.\.venv\Scripts\python -m pytest tests\unit -q
.\.venv\Scripts\python -m pytest tests\integration -q
```

## Frontend

From `frontend/`:

```powershell
npm install
npm run test
npm run build
```

What those commands validate:

- `npm run test` runs Vitest against `src/**/*.{test,spec}.{ts,tsx}`
- `npm run build` runs `tsc -b` and then the Vite production build

## End-To-End

From `frontend/`:

```powershell
npm run test:e2e
```

Before running Playwright, make sure the backend is available on `http://127.0.0.1:8000` unless you override `ARGUS_BACKEND_TARGET`.

See [playwright-e2e.md](playwright-e2e.md) for execution modes and artifact locations.

## Recommended Validation Order

1. Backend tests
2. Frontend unit tests
3. Frontend build
4. Targeted Playwright scenarios
5. Full Playwright regression when doing release or delivery work

## Reporting

Historical verification reports remain available under [../delivery/README.md](../delivery/README.md). They are useful evidence, but the source of truth for current behavior is always the code, the active test configuration, and the commands above.
