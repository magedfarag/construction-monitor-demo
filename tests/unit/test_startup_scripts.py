"""Regression checks for local startup scripts."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STARTUP_SCRIPTS = [
    ROOT / "tools" / "run_demo.ps1",
    ROOT / "tools" / "run_demo.sh",
    ROOT / "tools" / "run_api.ps1",
]
CELERY_SCRIPTS = [
    ROOT / "tools" / "run_worker.ps1",
    ROOT / "tools" / "run_beat.ps1",
]


def test_startup_scripts_use_module_form_for_uvicorn() -> None:
    """Startup scripts should invoke Uvicorn via ``python -m`` for Windows reliability."""
    for script_path in STARTUP_SCRIPTS:
        content = script_path.read_text(encoding="utf-8")
        assert "-m uvicorn app.main:app" in content, (
            f"{script_path.relative_to(ROOT)} should invoke uvicorn via the Python module entry point"
        )
        assert re.search(r"(?<!-m )uvicorn app\.main:app", content) is None, (
            f"{script_path.relative_to(ROOT)} should not invoke uvicorn via a bare console command"
        )


def test_celery_service_scripts_use_module_form() -> None:
    """Celery startup scripts should invoke Celery via ``python -m`` for Windows reliability."""
    for script_path in CELERY_SCRIPTS:
        content = script_path.read_text(encoding="utf-8")
        assert "-m celery -A app.workers.celery_app.celery_app" in content, (
            f"{script_path.relative_to(ROOT)} should invoke Celery via the Python module entry point"
        )
        assert re.search(r"(?<!-m )celery -A app\.workers\.celery_app\.celery_app", content) is None, (
            f"{script_path.relative_to(ROOT)} should not invoke Celery via a bare console command"
        )


def test_run_demo_bat_orchestrates_full_demo_stack() -> None:
    """The Windows demo launcher should start infra, backend, worker, and frontend services."""
    content = (ROOT / "run_demo.bat").read_text(encoding="utf-8").lower()
    assert "docker-compose.infra.yml" in content
    assert "run_api.ps1" in content
    assert "run_worker.ps1" in content
    assert "frontend" in content
    assert "pnpm dev" in content or "npm run dev" in content
    assert "argus_demo_dry_run" in content
    assert "waiting for backend api and frontend ui to become reachable" in content
    assert "ports 8000 and 5173" in content