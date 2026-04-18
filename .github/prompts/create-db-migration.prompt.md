---
description: "Create an Alembic database migration for a model or schema change. Covers migration file, upgrade/downgrade steps, and data safety notes. Use when: adding a column, creating a table, changing a constraint, renaming a field."
name: "Create DB Migration"
argument-hint: "Description of the schema change (e.g. add nullable last_seen column to sites table)"
agent: "agent"
---

# Create a DB Migration

You are creating an Alembic migration for the ARGUS construction-monitor database.

Steps to follow:
1. Read `alembic/versions/` to find the latest revision and its `down_revision`.
2. Generate a new migration file following the naming convention `<timestamp>_<slug>.py`. Set `revision` and `down_revision` correctly.
3. In `upgrade()`: write the forward DDL change (add column, create table, create index, etc.).
4. In `downgrade()`: write the exact reversal so the migration is fully reversible.
5. If the change is additive (new nullable column, new table), confirm it is safe for a zero-downtime deploy.
6. If existing rows need data back-filled, add a note in the migration docstring and a separate data migration step.
7. Do not modify any SQLAlchemy model files unless explicitly asked — keep model and migration in sync as separate, confirmed steps.
8. Summarize: revision id, what changes, downgrade safety, and any deployment ordering requirements.
