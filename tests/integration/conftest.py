"""Integration test conftest — restores real credentials from .env for integration tests.

The root tests/conftest.py blanks all credentials for unit test isolation.
This conftest runs directly after it (pytest loads conftests root→leaf) and
restores DATABASE_URL and API keys before any integration test module is
imported, so module-level skip guards like ``_SKIP = not _DB_URL`` evaluate
correctly.
"""
from __future__ import annotations

import os
from pathlib import Path

# Integration tests rely on the base tests/conftest.py defaults for
# APP_MODE/auth/Redis isolation. Only restore the live credentials that
# specific integration modules need.
_RESTORE_KEYS = {
    "DATABASE_URL",
    "SENTINEL2_CLIENT_ID",
    "SENTINEL2_CLIENT_SECRET",
    "SENTINEL2_TOKEN_URL",
    "LANDSAT_USERNAME",
    "LANDSAT_PASSWORD",
    "MAXAR_API_KEY",
    "PLANET_API_KEY",
    "ACLED_EMAIL",
    "ACLED_PASSWORD",
}

# Load .env values into the environment before integration test modules import
_env_file = Path(__file__).parents[2] / ".env"
if _env_file.exists():
    with _env_file.open(encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _, _val = _line.partition("=")
            _key = _key.strip()
            _val = _val.strip()
            if _key not in _RESTORE_KEYS:
                continue
            # Only restore if not already set by a higher-priority source
            if _key and _key not in os.environ or not os.environ.get(_key):
                os.environ[_key] = _val
