---
description: "Add a new FastAPI endpoint to the construction-monitor backend. Covers route handler, Pydantic models, service wiring, DB access, and test stub. Use when: adding a REST API route, creating a new endpoint, wiring a new service method to an HTTP route."
name: "Add API Endpoint"
argument-hint: "HTTP method and path (e.g. POST /api/v1/sites/{id}/alerts), brief description of what it does"
agent: "agent"
---

# Add an API Endpoint

You are working on the ARGUS construction-monitor backend (FastAPI, Python, Alembic, async SQLAlchemy).

Steps to follow:
1. Read the existing router file closest to the feature area.
2. Define the Pydantic request/response models in `app/models/` following existing naming conventions.
3. Add the route handler in the appropriate `app/routers/` file. Keep the handler thin — delegate to a service method.
4. Add or extend the service method in `app/services/`. Handle validation, DB access, and error mapping there.
5. If the endpoint reads or writes a new DB entity, check `alembic/versions/` for the latest migration and describe what a new migration would need — do not generate the migration file unless explicitly asked.
6. Write a pytest stub in the relevant test file. Mark it `@pytest.mark.skip("not implemented")` if the full implementation is out of scope.
7. Summarize: added routes, changed service contracts, migration requirements, and test coverage gaps.
