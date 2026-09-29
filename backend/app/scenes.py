"""Análisis de una foto (MoGe → piso → oclusión) y endpoints /api/scenes."""

import logging
import shutil
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field

from app.config import MOGE_MODEL
from app.geometry.coords import cv_to_three, floor_frame, fov_y_deg, to_column_major
from app.geometry.floor import FloorResult, detect_floor, draw_floor_debug
from app.geometry.moge_runner import UnsupportedImageError, load_image, run_moge
from app.geometry.occlusion import build_occlusion_mesh, export_glb
from app.geometry.occupancy import build_occupancy, occupancy_png
from app.geometry.room import draw_grid, estimate_room, room_text
from app.schemas import CameraInfo, FloorInfo, ImageInfo, Placement, RoomEstimate, Scene
from app.storage import SCENES_DIR, file_url, new_scene_id, read_json, scene_dir, write_json_atomic

SAVE_MAX_SIDE = 2560
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
IDENTITY = to_column_major(np.eye(4))

log = logging.getLogger("santiago.scenes")

_analysis_lock = threading.Lock()  # una foto a la vez (el modelo usa toda la GPU/CPU)
_save_lock = threading.Lock()


def _limit_size(img: Image.Image, max_side: int) -> Image.Image:
    scale = max_side / max(img.size)
    if scale >= 1:
        return img
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)


def depth_png(depth: np.ndarray, valid: np.ndarray) -> Image.Image:
    """Profundidad en gris (cerca = claro)."""
    out = np.zeros(depth.shape, dtype=np.uint8)
    ok = valid & np.isfinite(depth)
    if ok.any():
        lo, hi = np.percentile(depth[ok], [1, 99])
        norm = np.clip((depth - lo) / max(hi - lo, 1e-6), 0, 1)
        out[ok] = (255 * (1 - norm[ok])).astype(np.uint8)
    return Image.fromarray(out)


def _floor_info(floor: FloorResult) -> FloorInfo:
    if not floor.found:
        return FloorInfo(found=False)
    return FloorInfo(
        found=True,
        normal=[round(float(v), 5) for v in floor.normal],
        d=round(floor.d, 4),
        inlier_ratio=round(floor.inlier_ratio, 4),
        frame=to_column_major(floor_frame(floor.normal, floor.d)),
    )


def analyze_photo(src: Path, scene_id: str | None = None) -> Scene:
    """Procesa una foto y guarda todo en data/scenes/<id>/. Devuelve la Scene."""
    img = load_image(src)
    scene_id = scene_id or new_scene_id()
    out = scene_dir(scene_id)
    out.mkdir(parents=True, exist_ok=True)

    saved = _limit_size(img, SAVE_MAX_SIDE)
    saved.save(out / "image.jpg", quality=90)
    w, h = saved.size

    with _analysis_lock:
        r = run_moge(img)
    t0 = time.perf_counter()
    points = cv_to_three(r.points)
    normals = cv_to_three(r.normal) if r.normal is not None else None
    floor = detect_floor(points, r.mask, normals)
    t1 = time.perf_counter()
    mesh = build_occlusion_mesh(points, r.mask, floor.mask)
    export_glb(mesh, out / "occlusion.glb")
    t2 = time.perf_counter()
    frame = floor_frame(floor.normal, floor.d) if floor.found else None
    room = estimate_room(points, r.mask, normals, floor, frame)
    t3 = time.perf_counter()
    # Geometría para recalcular la grilla de ocupación después (sugerencias, piso manual)
    np.savez_compressed(out / "geometry.npz", points=points.astype(np.float16), valid=r.mask,
                        normals=(normals if normals is not None else np.zeros_like(points)).astype(np.float16),
                        floor_mask=floor.mask if floor.mask is not None else np.zeros(r.mask.shape, bool),
                        intrinsics=r.intrinsics)
    if frame is not None:
        grid = build_occupancy(points, r.mask, floor.mask, frame, r.intrinsics, normals)
        Image.fromarray(occupancy_png(grid)).save(out / "occupancy.png")

    fmask = floor.mask if floor.mask is not None else np.zeros(r.mask.shape, bool)
    Image.fromarray(fmask.astype(np.uint8) * 255).resize((w, h), Image.Resampling.NEAREST) \
        .save(out / "floor_mask.png")
    depth_png(r.depth, r.mask).save(out / "depth.png")
    grid = (lambda im: draw_grid(im, fmask, frame, r.intrinsics)) if frame is not None else None
    debug = draw_floor_debug(np.asarray(saved), floor, grid, room_text(room) if floor.found else None)
    Image.fromarray(debug).save(out / "debug.jpg", quality=88)

    scene = Scene(
        id=scene_id,
        image=ImageInfo(url=file_url(out / "image.jpg"), width=w, height=h),
        camera=CameraInfo(
            fov_y_deg=round(fov_y_deg(r.intrinsics), 3),
            intrinsics_norm=[[round(float(v), 6) for v in row] for row in r.intrinsics],
            matrix_world=IDENTITY,
        ),
        floor=_floor_info(floor),
        camera_height_m=round(floor.d, 3) if floor.found else None,
        room_estimate=RoomEstimate.model_validate(room),
        warnings=floor.warnings,
        assets={
            "occlusion_glb": file_url(out / "occlusion.glb"),
            "floor_mask_png": file_url(out / "floor_mask.png"),
            "depth_preview_png": file_url(out / "depth.png"),
            "debug_jpg": file_url(out / "debug.jpg"),
        },
        model=MOGE_MODEL,
        timings_ms={
            "load": r.load_ms, "infer": r.infer_ms,
            "floor": round((t1 - t0) * 1000), "mesh": round((t2 - t1) * 1000),
            "room": round((t3 - t2) * 1000),
        },
        created_at=datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
    )
    write_json_atomic(out / "scene.json", scene.model_dump())
    return scene


def load_scene(scene_id: str) -> Scene:
    try:
        path = scene_dir(scene_id) / "scene.json"
    except ValueError:
        raise HTTPException(404, "Escena no encontrada") from None
    if not path.is_file():
        raise HTTPException(404, "Escena no encontrada")
    return Scene.model_validate(read_json(path))


router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.post("", response_model=Scene)
def create_scene(file: Annotated[UploadFile, File()]) -> Scene:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in {".heic", ".heif"}:
        raise HTTPException(400, "Las fotos HEIC no se aceptan todavía. Usa JPG o PNG "
                                 "(al compartirla por WhatsApp ya queda en JPG).")
    with tempfile.NamedTemporaryFile(suffix=suffix or ".jpg", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp, length=1024 * 1024)
        tmp_path = Path(tmp.name)
    try:
        if tmp_path.stat().st_size > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "La foto es muy grande (máximo 40 MB).")
        return analyze_photo(tmp_path)
    except UnsupportedImageError as e:
        raise HTTPException(400, str(e)) from None
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("", response_model=list[Scene])
def list_scenes() -> list[Scene]:
    if not SCENES_DIR.is_dir():
        return []
    scenes = []
    for path in sorted(SCENES_DIR.glob("scn_*/scene.json"), reverse=True):
        try:
            scenes.append(Scene.model_validate(read_json(path)))
        except (OSError, ValueError):  # escena a medio escribir o de una versión vieja
            log.warning("Se omite la escena %s (no se pudo leer)", path.parent.name, exc_info=True)
    return scenes


@router.get("/{scene_id}", response_model=Scene)
def get_scene(scene_id: str) -> Scene:
    return load_scene(scene_id)


class ManualFloorBody(BaseModel):
    normal: list[float] = Field(min_length=3, max_length=3)
    d: float = Field(gt=0.1, lt=10.0)


@router.put("/{scene_id}/floor", response_model=Scene)
def put_floor(scene_id: str, body: ManualFloorBody) -> Scene:
    """Piso definido a mano con 3 clics (PLAN 2.9). Plano en coords three de la cámara."""
    n = np.asarray(body.normal, dtype=np.float64)
    if np.linalg.norm(n) < 1e-6:
        raise HTTPException(422, "Plano inválido")
    n = n / np.linalg.norm(n)
    try:
        frame = floor_frame(n, body.d)
    except ValueError as e:
        raise HTTPException(422, "Ese plano no sirve como piso: marca 3 puntos del piso más separados.") from e
    with _save_lock:
        scene = load_scene(scene_id)
        floor = FloorInfo(found=True, normal=[round(float(v), 5) for v in n], d=round(body.d, 4),
                          inlier_ratio=0.0, frame=to_column_major(frame))
        warnings = [w for w in scene.warnings if w != "piso_no_encontrado"] + ["piso_manual"]
        scene = scene.model_copy(update={"floor": floor, "camera_height_m": round(body.d, 3),
                                         "warnings": sorted(set(warnings))})
        write_json_atomic(scene_dir(scene_id) / "scene.json", scene.model_dump())
    return scene


class SuggestBody(BaseModel):
    item_ids: list[str] = Field(min_length=1, max_length=12)
    use_vlm: bool = False
    replace_uids: list[str] = Field(default_factory=list)


class SuggestResponse(BaseModel):
    placements: list[Placement]
    notes: list[str]


@router.get("/vlm/status")
def vlm_status() -> dict:
    """¿Está disponible la IA local (Ollama) para las sugerencias?"""
    from app.placement.vlm import status

    return status()


@router.post("/{scene_id}/suggest", response_model=SuggestResponse)
def post_suggest(scene_id: str, body: SuggestBody) -> SuggestResponse:
    """Sugerir dónde ubicar los muebles (PLAN 3.2/3.3). No guarda nada: el editor muestra "fantasmas"."""
    from app.placement.service import run_suggest, to_placements

    scene = load_scene(scene_id)
    try:
        result, items = run_suggest(scene, body.item_ids, body.replace_uids)
    except ValueError as e:
        raise HTTPException(409, str(e)) from None
    except KeyError as e:
        raise HTTPException(404, str(e.args[0])) from None
    notes = list(result.notes)
    source = "heuristic"
    if body.use_vlm:
        from app.placement.vlm import choose_with_vlm

        result, vlm_notes, used = choose_with_vlm(scene, result, items)
        notes = vlm_notes
        source = "vlm" if used else "heuristic"
    return SuggestResponse(placements=to_placements(result, source), notes=notes)


class PlacementsBody(BaseModel):
    placements: list[Placement]
    scale_k: float = Field(default=1.0, gt=0.2, lt=5.0)


@router.put("/{scene_id}/placements", response_model=Scene)
def put_placements(scene_id: str, body: PlacementsBody) -> Scene:
    """Guarda los muebles ubicados y la escala calibrada (autoguardado del editor)."""
    with _save_lock:
        scene = load_scene(scene_id)
        scene = scene.model_copy(update={"placements": body.placements, "scale_k": body.scale_k})
        write_json_atomic(scene_dir(scene_id) / "scene.json", scene.model_dump())
    return scene
