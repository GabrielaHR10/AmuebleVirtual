"""App FastAPI: API en /api, datos en /files y el frontend compilado en /."""

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__, jobs, scenes, videos
from app.catalog import routes as catalog_routes
from app.config import DATA_DIR, STATIC_DIR, resolve_device
from app.video import clips

app = FastAPI(title="Estudio Virtual — Santiago Muebles", version=__version__)

api = APIRouter(prefix="/api")


@api.get("/health")
def health() -> dict:
    return {"ok": True, "device": resolve_device(), "version": __version__}


api.include_router(scenes.router)
api.include_router(catalog_routes.router)
api.include_router(videos.router)
api.include_router(clips.router)
api.include_router(jobs.router)
app.include_router(api)

DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=DATA_DIR), name="files")


if (STATIC_DIR / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets", check_dir=False), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        # Rutas de la API desconocidas no deben devolver la SPA
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Ruta no encontrada")
        candidate = (STATIC_DIR / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR):
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
