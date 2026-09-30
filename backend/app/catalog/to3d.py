"""Foto de un mueble → modelo 3D con TripoSR (MIT), en el computador (sin internet tras bajar los pesos).

Entrada: el recorte con fondo transparente (cutout.png). Salida: GLB con colores por vértice, +y arriba y el
frente hacia +z, apoyado en y = 0 y escalado al ANCHO de la ficha (el editor igual reescala por el ancho).
"""

import logging
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image

from app.config import resolve_device

log = logging.getLogger("santiago.to3d")
MODEL_ID = "stabilityai/TripoSR"
_lock = threading.Lock()
_model = None
_device = "cpu"


def get_model():
    global _model, _device
    with _lock:
        if _model is None:
            # TripoSR importa sus clases por nombre ("tsr.models..."): su carpeta debe estar en la ruta
            vendor = str(Path(__file__).resolve().parent.parent / "vendor")
            if vendor not in sys.path:
                sys.path.insert(0, vendor)
            from tsr.system import TSR

            m = TSR.from_pretrained(MODEL_ID, config_name="config.yaml", weight_name="model.ckpt")
            m.renderer.set_chunk_size(8192)
            _device = "mps" if resolve_device() == "mps" else resolve_device()
            try:
                _model = m.to(_device)
            except Exception:
                log.warning("TripoSR no cargó en %s; se usa CPU", _device, exc_info=True)
                _device, _model = "cpu", m.to("cpu")
        return _model, _device


def prepare_input(cutout: Image.Image, size: int = 512, fill: float = 0.85) -> Image.Image:
    """Recorte RGBA → cuadrado con fondo gris 50 % y el objeto ocupando `fill` (como espera TripoSR)."""
    rgba = cutout.convert("RGBA")
    rgba.thumbnail((int(size * fill), int(size * fill)), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", (size, size), (127, 127, 127, 255))
    bg.alpha_composite(rgba, ((size - rgba.width) // 2, (size - rgba.height) // 2))
    return bg.convert("RGB")


def photo_to_mesh(cutout: Image.Image, resolution: int = 256) -> trimesh.Trimesh:
    import torch

    model, device = get_model()
    img = prepare_input(cutout)
    t = time.perf_counter()
    with torch.no_grad():
        codes = model([img], device=device)
        mesh = model.extract_mesh(codes, True, resolution=resolution)[0]
    log.info("TripoSR: %.1f s en %s", time.perf_counter() - t, device)
    return mesh


def align_yaw(xz: np.ndarray) -> float:
    """Giro (grados, alrededor de +y) que pone el lado largo de la huella a lo largo de x.

    TripoSR deja el objeto como se ve en la foto (p. ej. en 3/4, girado ~30°). De los dos giros que alinean
    la huella, se toma el más pequeño: así el frente que vio la cámara sigue mirando hacia +z.
    """
    lo, hi = np.percentile(xz, [1, 99], axis=0)
    core = xz[((xz >= lo) & (xz <= hi)).all(1)]
    (_, _), (w, h), angle = cv2.minAreaRect(core.astype(np.float32))
    long_angle = angle if w >= h else angle + 90  # ángulo del lado largo respecto a +x, en el plano (x, z)
    # Ry(θ) lleva (cos a, sin a) del plano (x, z) a (cos(a − θ), …): para dejarlo sobre +x, θ = a
    return float((long_angle + 90) % 180 - 90)  # entre −90 y 90: el giro más pequeño


# Cámara con la que TripoSR "ve" la foto (tsr/system.py: render(), acimut 0): desde +x, a 1.9, fov vertical 40°,
# z arriba; a la derecha de la imagen está +y.
COND_DISTANCE = 1.9
COND_FOVY_DEG = 40.0
INPUT_SIZE = 512
INPUT_FILL = 0.85


def project_to_photo(vertices: np.ndarray, normals: np.ndarray, cutout_size: tuple[int, int],
                     alpha: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Vértices (coords de TripoSR) → (uv en el recorte [0..1], visible desde la cámara de la foto)."""
    f = 0.5 / np.tan(np.radians(COND_FOVY_DEG) / 2)
    depth = COND_DISTANCE - vertices[:, 0]
    u = 0.5 + f * vertices[:, 1] / depth  # en la imagen cuadrada de entrada (0..1)
    v = 0.5 - f * vertices[:, 2] / depth
    # imagen de entrada → píxel del recorte (mismo encuadre que prepare_input)
    cw, ch = cutout_size
    scale = min(INPUT_SIZE * INPUT_FILL / cw, INPUT_SIZE * INPUT_FILL / ch, 1e9)
    tw, th = cw * scale, ch * scale
    px = (u * INPUT_SIZE - (INPUT_SIZE - tw) / 2) / tw
    py = (v * INPUT_SIZE - (INPUT_SIZE - th) / 2) / th
    # visibilidad: mira hacia la cámara y es lo más cercano en su píxel (z-buffer de 256×256)
    to_cam = np.array([COND_DISTANCE, 0, 0]) - vertices
    facing = (normals * to_cam).sum(1) > 0.0  # incluye superficies vistas en ángulo rasante (asientos)
    g = 512
    iu = np.clip((u * g).astype(int), 0, g - 1)
    iv = np.clip((v * g).astype(int), 0, g - 1)
    zbuf = np.full((g, g), np.inf)
    np.minimum.at(zbuf, (iv, iu), depth)
    # tolerancia amplia: la foto suele tomarse desde arriba y TripoSR asume cámara horizontal; solo se
    # descartan oclusiones grandes (en telas uniformes, un pequeño error de proyección no se nota)
    visible = facing & (depth <= zbuf[iv, iu] + 0.15) & (px >= 0) & (px <= 1) & (py >= 0) & (py <= 1)
    if alpha is not None:  # solo donde la foto realmente muestra el mueble (no el fondo transparente)
        ax = np.clip((px * (alpha.shape[1] - 1)).astype(int), 0, alpha.shape[1] - 1)
        ay = np.clip((py * (alpha.shape[0] - 1)).astype(int), 0, alpha.shape[0] - 1)
        visible &= alpha[ay, ax] > 200
    return np.column_stack([px, 1 - py]), visible  # uv con origen abajo-izquierda (convención de trimesh)


def bleed_edges(cutout: Image.Image) -> Image.Image:
    """RGB del recorte con el fondo transparente rellenado con el color vecino (evita bordes claros al muestrear)."""
    arr = np.asarray(cutout.convert("RGBA"))
    rgb, a = arr[..., :3].copy(), arr[..., 3]
    hole = (a < 128).astype(np.uint8)
    small = cv2.resize(rgb, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    small_hole = cv2.resize(hole, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    filled = cv2.inpaint(small, small_hole, 5, cv2.INPAINT_TELEA)
    up = cv2.resize(filled, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
    rgb[hole > 0] = up[hole > 0]
    return Image.fromarray(rgb)


def match_colors_to_photo(mesh: trimesh.Trimesh, uv: np.ndarray, vis: np.ndarray, photo: np.ndarray) -> None:
    """Calibra los colores que inventó TripoSR con la foto real (ajuste lineal por canal en los vértices que
    se ven en la foto) y lo aplica a todos: así la parte sin foto no queda como un parche de otro tono."""
    colors = mesh.visual.vertex_colors[:, :3].astype(np.float64)
    if vis.sum() < 100:
        return
    h, w = photo.shape[:2]
    px = np.clip((uv[vis, 0] * (w - 1)).astype(int), 0, w - 1)
    py = np.clip(((1 - uv[vis, 1]) * (h - 1)).astype(int), 0, h - 1)
    target = photo[py, px].astype(np.float64)
    source = colors[vis]
    out = colors.copy()
    for c in range(3):
        a, b = np.polyfit(source[:, c], target[:, c], 1)
        a = float(np.clip(a, 0.3, 3.0))
        b = float(np.median(target[:, c] - a * source[:, c]))  # intercepto robusto
        out[:, c] = a * colors[:, c] + b
    vc = mesh.visual.vertex_colors.copy()
    vc[:, :3] = np.clip(out, 0, 255).astype(np.uint8)
    mesh.visual.vertex_colors = vc


def with_photo_texture_uv(mesh: trimesh.Trimesh, uv: np.ndarray, vis: np.ndarray,
                          cutout: Image.Image) -> trimesh.Scene:
    """Parte visible en la foto → textura con la foto real (nítida); el resto → colores del modelo."""
    # suavizar: una cara cuenta como "vista en la foto" si la mayoría de sus vecinas también (evita parches)
    face_vis = vis[mesh.faces].all(1)
    adj = mesh.face_adjacency
    for _ in range(2):
        votes = np.zeros(len(face_vis))
        count = np.zeros(len(face_vis))
        np.add.at(votes, adj[:, 0], face_vis[adj[:, 1]])
        np.add.at(votes, adj[:, 1], face_vis[adj[:, 0]])
        np.add.at(count, adj.ravel(), 1)
        face_vis = np.where(count > 0, votes / np.maximum(count, 1) >= 0.5, face_vis)
    photo = bleed_edges(cutout)
    match_colors_to_photo(mesh, uv, vis, np.asarray(photo))
    scene = trimesh.Scene()
    for name, mask in (("foto", face_vis), ("modelo", ~face_vis)):
        if not mask.any():
            continue
        sub = mesh.submesh([np.nonzero(mask)[0]], append=True)
        if name == "foto":
            # submesh conserva los vértices usados en orden: recuperar su índice original para el uv
            idx = np.unique(mesh.faces[mask])
            remap = {int(o): i for i, o in enumerate(idx)}
            sub = trimesh.Trimesh(vertices=mesh.vertices[idx], faces=np.vectorize(remap.get)(mesh.faces[mask]),
                                  process=False)
            # glTF asume metálico = 1 si no se dice: se declara tela mate (si no, se ve negro)
            mat = trimesh.visual.material.PBRMaterial(baseColorTexture=photo, metallicFactor=0.0, roughnessFactor=1.0)
            sub.visual = trimesh.visual.TextureVisuals(uv=uv[idx], material=mat)
        else:
            sub.visual = trimesh.visual.ColorVisuals(sub, vertex_colors=sub.visual.vertex_colors)
            sub.visual.material = trimesh.visual.material.PBRMaterial(metallicFactor=0.0, roughnessFactor=1.0)
        scene.add_geometry(sub, geom_name=name)
    return scene


def normalize(mesh: trimesh.Trimesh, dims_m: tuple[float, float, float]) -> trimesh.Trimesh:
    """TripoSR (z arriba) → glTF (+y arriba, frente +z), alineado, apoyado en y = 0 y con las medidas REALES.

    dims_m = (ancho, fondo, alto) de la tabla: cada eje se escala por separado (la foto en ángulo deja la
    profundidad y el alto inciertos; las medidas del mueble son la fuente de verdad).
    """
    m = mesh.copy()
    rot = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)  # (x, y, z)_tsr → (y, z, x): ver prueba visual
    m.vertices = m.vertices @ rot.T
    yaw = np.radians(align_yaw(m.vertices[:, [0, 2]]))
    c, s = np.cos(yaw), np.sin(yaw)
    m.vertices = m.vertices @ np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]).T
    # recortar el 0.5 % de puntos extremos al medir (colas sueltas de la malla)
    lo, hi = np.percentile(m.vertices, [0.5, 99.5], axis=0)
    m.vertices -= [(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2]
    size = np.maximum(hi - lo, 1e-6)
    w, d, h = dims_m
    m.vertices *= np.array([w, h, d]) / size
    return m


TARGET_FACES = 25_000  # ~100k caras hacían lento el editor (y la GPU de equipos modestos)


def simplify(mesh: trimesh.Trimesh, target_faces: int = TARGET_FACES) -> trimesh.Trimesh:
    """Reduce caras conservando la forma; los colores se toman del vértice original más cercano."""
    if len(mesh.faces) <= target_faces:
        return mesh
    small = mesh.simplify_quadric_decimation(face_count=target_faces)
    _, idx = mesh.kdtree.query(small.vertices)
    small.visual = trimesh.visual.ColorVisuals(small, vertex_colors=mesh.visual.vertex_colors[idx])
    return small


def photo_to_glb(cutout_path: Path, out: Path, dims_m: tuple[float, float, float]) -> Path:
    with Image.open(cutout_path) as im:
        cutout = im.convert("RGBA")
    raw = simplify(photo_to_mesh(cutout))
    # la textura se proyecta en coords de TripoSR; normalize solo mueve vértices (mismo orden)
    uv, vis = project_to_photo(raw.vertices, raw.vertex_normals, cutout.size, np.asarray(cutout)[..., 3])
    mesh = normalize(raw, dims_m)
    scene = with_photo_texture_uv(mesh, uv, vis, cutout)
    out.write_bytes(scene.export(file_type="glb", include_normals=True))  # sin normales se ve facetado
    return out


def generate_for_item(item_id: str, progress=None) -> dict:
    """Genera data/catalog/<id>/model.glb desde el recorte y deja el mueble en modo 3D (se puede volver al recorte)."""
    from app import storage
    from app.catalog import service

    item = service.get_item(item_id)
    if item is None:
        raise KeyError(item_id)
    folder = service.item_dir(item_id)
    cutout = folder / "cutout.png"
    if not cutout.is_file():
        raise ValueError("Este mueble no tiene foto recortada para convertir a 3D.")
    if progress:
        progress(0.1, "Creando el modelo 3D desde la foto… (~30 s)")
    d = item.dimensions_cm
    glb = photo_to_glb(cutout, folder / "model.glb", (d.width / 100, d.depth / 100, d.height / 100))
    note = "Modelo 3D generado automáticamente con TripoSR a partir de la foto (forma aproximada, medidas reales)."
    notes = [n for n in item.notes if not n.startswith("Modelo 3D generado")] + [note]
    updated = item.model_copy(update={
        "glb_url": storage.file_url(glb), "preferred_mode": "3d", "yaw_offset_deg": 0, "notes": notes,
    })
    service.save_item(updated)
    return updated.model_dump()
