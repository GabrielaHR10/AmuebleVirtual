"""Trabajos en segundo plano (hilo + estado en JSON en data/jobs/). GET /api/jobs/{id}."""

import logging
import secrets
import threading
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException

from app import storage

log = logging.getLogger("santiago.jobs")
_lock = threading.Lock()


def _path(job_id: str):
    if not job_id.startswith("job_") or not job_id[4:].isalnum():
        raise ValueError("Id de trabajo inválido")
    return storage.DATA_DIR / "jobs" / f"{job_id}.json"


def _write(job_id: str, **fields: Any) -> None:
    with _lock:
        path = _path(job_id)
        data = storage.read_json(path) if path.is_file() else {}
        data.update(fields)
        path.parent.mkdir(parents=True, exist_ok=True)
        storage.write_json_atomic(path, data)


def get(job_id: str) -> dict:
    try:
        path = _path(job_id)
    except ValueError:
        raise KeyError(job_id) from None
    if not path.is_file():
        raise KeyError(job_id)
    return storage.read_json(path)


Progress = Callable[[float, str], None]


def start(kind: str, fn: Callable[[Progress], Any]) -> str:
    """Corre fn(progreso) en un hilo. fn devuelve el `result` (JSON) o lanza una excepción con mensaje en español."""
    job_id = f"job_{secrets.token_hex(6)}"
    _write(job_id, id=job_id, kind=kind, status="queued", progress=0.0, message="En cola…", result=None)

    def progress(p: float, message: str) -> None:
        _write(job_id, status="running", progress=round(min(max(p, 0.0), 1.0), 3), message=message)

    def run() -> None:
        try:
            progress(0.0, "Empezando…")
            result = fn(progress)
            _write(job_id, status="done", progress=1.0, message="Listo", result=result)
        except Exception as e:
            log.exception("Trabajo %s falló", job_id)
            _write(job_id, status="error", message=str(e) or "Error inesperado")

    threading.Thread(target=run, daemon=True, name=job_id).start()
    return job_id


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    try:
        return get(job_id)
    except KeyError:
        raise HTTPException(404, "Trabajo no encontrado") from None
