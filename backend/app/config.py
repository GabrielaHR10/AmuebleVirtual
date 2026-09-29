"""Rutas del proyecto, dispositivo de cómputo y lectura de .env."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
APP_DIR = BACKEND_DIR / "app"
STATIC_DIR = APP_DIR / "static"
DATA_DIR = REPO_DIR / "data"
SAMPLES_DIR = REPO_DIR / "samples"

load_dotenv(REPO_DIR / ".env")

MOGE_MODEL = os.getenv("MOGE_MODEL", "Ruicheng/moge-2-vitb-normal")

HOST = "127.0.0.1"
PORT = 8000

log = logging.getLogger("santiago")


def resolve_device() -> str:
    """DEVICE=auto|cpu|mps|cuda. En auto: cuda si existe, si no mps, si no cpu."""
    wanted = os.getenv("DEVICE", "auto").strip().lower()
    if wanted in {"cpu", "mps", "cuda"}:
        return wanted
    try:
        import torch  # opcional hasta la Fase 1
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
