"""IA local opcional (Ollama + Qwen3-VL) que elige entre los candidatos de la heurística (PLAN 3.3).

La IA nunca inventa coordenadas: solo escoge un número entre los candidatos válidos dibujados en la foto.
Si Ollama no responde o el JSON no sirve, se usa la sugerencia básica.
"""

import base64
import io
import json
import logging
import os
import time
import urllib.error
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.placement.geometry2d import Box, overlap, project
from app.placement.heuristic import Item, Result
from app.schemas import Scene
from app.storage import scene_dir

log = logging.getLogger("santiago.vlm")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
VLM_MODEL = os.getenv("VLM_MODEL", "qwen3-vl:4b-instruct")
TIMEOUT_S = 120
COLORS = [(230, 57, 70), (29, 120, 220), (40, 170, 90), (240, 150, 20), (150, 70, 200), (20, 170, 180)]
FALLBACK_NOTE = "La IA local no respondió; se usó la sugerencia básica."


def _get(path: str, timeout: float = 3) -> dict:
    with urllib.request.urlopen(f"{OLLAMA_URL}{path}", timeout=timeout) as r:
        return json.load(r)


def status() -> dict:
    """¿Está Ollama corriendo y tiene el modelo?"""
    try:
        names = [m.get("name", "") for m in _get("/api/tags").get("models", [])]
    except (OSError, ValueError):
        return {"available": False, "model": VLM_MODEL, "reason": "Ollama no está corriendo"}
    ok = any(n == VLM_MODEL or n.split(":")[0] == VLM_MODEL for n in names)
    return {"available": ok, "model": VLM_MODEL, "reason": None if ok else f"Falta el modelo {VLM_MODEL}"}


def draw_candidates(scene: Scene, result: Result, items: list[Item]) -> tuple[bytes, dict[int, tuple[int, int]]]:
    """Foto con los candidatos numerados (1..N). Devuelve JPEG y número → (índice del item, índice del candidato)."""
    img = Image.open(scene_dir(scene.id) / "image.jpg").convert("RGB")
    img.thumbnail((1024, 1024))
    w, h = img.size
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Arial.ttf", max(14, w // 40))
    except OSError:
        font = ImageFont.load_default()
    frame = np.array(scene.floor.frame, dtype=np.float64).reshape(4, 4).T
    intr = np.array(scene.camera.intrinsics_norm)
    numbering: dict[int, tuple[int, int]] = {}
    n = 0
    for i, cands in sorted(result.candidates.items()):
        color = COLORS[i % len(COLORS)]
        for j, c in enumerate(cands):
            n += 1
            numbering[n] = (i, j)
            corners = c.box.corners()
            uv = project(np.column_stack([corners[:, 0], np.zeros(4), corners[:, 1]]), frame, intr)
            if np.isfinite(uv).all():
                draw.polygon([(u * w, v * h) for u, v in uv], outline=color, width=2)
            cu = project(np.array([[c.box.x, 0.0, c.box.z]]), frame, intr)[0]
            if np.isfinite(cu).all():
                x, y, r = cu[0] * w, cu[1] * h, max(12, w // 50)
                draw.ellipse([x - r, y - r, x + r, y + r], fill=color, outline=(255, 255, 255), width=2)
                draw.text((x, y), str(n), fill=(255, 255, 255), font=font, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue(), numbering


def build_prompt(result: Result, items: list[Item], numbering: dict[int, tuple[int, int]]) -> str:
    lines = []
    for i, it in enumerate(items):
        nums = [str(k) for k, (ii, _) in numbering.items() if ii == i]
        if nums:
            size = f"{it.w * 100:.0f} x {it.d * 100:.0f} x {it.h * 100:.0f} cm"
            lines.append(f'- item_id "{it.item_id}" ({it.category}, {size}): candidates {", ".join(nums)}')
    return (
        "You are an interior designer. The photo shows a room. Numbered circles (with their outline on the floor) "
        "are valid positions for each furniture item. Choose ONE candidate number per item so the result looks "
        "natural and livable: sofas against a wall facing the room, coffee table in front of the sofa, "
        "clear walking paths, plants and lamps in corners or beside the sofa, nothing blocking doors or windows.\n"
        "Items:\n" + "\n".join(lines) + "\n"
        'Answer ONLY with JSON: {"choices": [{"item_id": "...", "candidate": <number>, '
        '"reason": "<short reason in Spanish>"}]}'
    )


def ask_ollama(prompt: str, image_jpeg: bytes, timeout: float = TIMEOUT_S) -> dict:
    body = json.dumps({
        "model": VLM_MODEL,
        "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(image_jpeg).decode()]}],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(json.load(r)["message"]["content"])


def apply_choices(result: Result, items: list[Item], numbering: dict[int, tuple[int, int]],
                  answer: dict) -> tuple[Result, list[str]]:
    """Reemplaza la elección de la heurística por la de la IA cuando es válida y no se cruza con otra."""
    chosen: dict[int, tuple[Box, str]] = {}
    for ch in answer.get("choices", []):
        num = ch.get("candidate")
        if not isinstance(num, int) or num not in numbering:
            continue
        i, j = numbering[num]
        if items[i].item_id != ch.get("item_id") or i in chosen:
            continue
        reason = str(ch.get("reason", "")).strip()[:160]
        chosen[i] = (result.candidates[i][j].box, reason)
    out = Result(candidates=result.candidates)
    notes: list[str] = []
    placed: list[Box] = []
    heuristic = {id(it): box for it, box in result.placements}
    for i, it in enumerate(items):
        box, reason = chosen.get(i, (heuristic.get(id(it)), None))
        if box is None:
            continue
        if any(overlap(box.corners(), p.corners()) for p in placed) and id(it) in heuristic:
            box, reason = heuristic[id(it)], None  # la IA eligió algo que choca: se usa la heurística
        placed.append(box)
        out.placements.append((it, box))
        notes.append(f"{it.name}: {reason} (IA local)" if reason else f"{it.name}: sugerencia básica")
    return out, notes


def choose_with_vlm(scene: Scene, result: Result, items: list[Item]) -> tuple[Result, list[str], bool]:
    """Devuelve (resultado, notas, se_usó_la_IA)."""
    if not result.candidates or not any(result.candidates.values()):
        return result, result.notes, False
    if not status()["available"]:
        return result, [*result.notes, FALLBACK_NOTE], False
    image, numbering = draw_candidates(scene, result, items)
    t = time.perf_counter()
    try:
        answer = ask_ollama(build_prompt(result, items, numbering), image)
    except (OSError, ValueError, KeyError, urllib.error.URLError, TimeoutError):
        log.warning("Ollama falló", exc_info=True)
        return result, [*result.notes, FALLBACK_NOTE], False
    log.info("VLM respondió en %.1f s: %s", time.perf_counter() - t, answer)
    out, notes = apply_choices(result, items, numbering, answer)
    return out, notes, True
