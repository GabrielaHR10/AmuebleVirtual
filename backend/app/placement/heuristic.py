"""Sugerencia de ubicación por reglas (PLAN 3.2). Greedy: muebles de mayor a menor área."""

from dataclasses import dataclass, field

import cv2
import numpy as np

from app.geometry.occupancy import FREE, NEAR, WALL_EDGE, Occupancy
from app.placement.geometry2d import (
    Box,
    distance_score,
    dominant_angle,
    facing_camera,
    is_valid,
    local_wall_normals,
    visibility,
)

FACE_CAMERA = {"sofa", "bed", "armchair", "desk"}
SIDE_WALL = {"shelf", "wardrobe"}
CENTER = {"rug", "coffee_table", "dining_table"}
DECOR = {"lamp", "plant"}
COFFEE_GAP_M = 0.45
TOP_K = 8


@dataclass
class Item:
    item_id: str
    name: str
    category: str
    w: float  # metros, ya con scale_k
    d: float
    h: float
    against_wall: bool


@dataclass
class Candidate:
    box: Box
    score: float
    note: str


@dataclass
class Result:
    placements: list[tuple[Item, Box]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    candidates: dict[int, list[Candidate]] = field(default_factory=dict)  # índice del item → top-k


def _wall_label(box: Box) -> str:
    f = facing_camera(box)
    if f > 0.7:
        return "la pared del fondo"
    if f < -0.7:
        return "la pared de atrás de la cámara"
    return "la pared de la derecha" if box.x > 0 else "la pared de la izquierda"


class Planner:
    def __init__(self, grid: Occupancy, frame: np.ndarray, intrinsics: np.ndarray, existing: list[Box]):
        self.grid, self.frame, self.intr = grid, frame, intrinsics
        self.placed: list[Box] = list(existing)
        self.kinds: list[str] = ["existing"] * len(existing)
        self.base = dominant_angle(grid)
        rows, cols = np.nonzero(grid.state == WALL_EDGE)
        keep = (rows + cols) % 2 == 0  # la mitad de las celdas basta y va el doble de rápido
        self.wall_cells = (rows[keep], cols[keep])
        # dirección a la pared: la de la grilla (normales de MoGe); si una celda no la tiene, recta local
        dirs = grid.wall_dir[self.wall_cells]
        missing = np.linalg.norm(dirs, axis=1) < 0.5
        if missing.any():
            dirs[missing] = local_wall_normals(grid, self.wall_cells[0][missing], self.wall_cells[1][missing])
        self.wall_normals = dirs

    # ---------- generadores de candidatos ----------

    def wall_candidates(self, it: Item) -> list[tuple[Box, str]]:
        out = []
        iz, ix = self.wall_cells
        cx, cz = self.grid.center(iz, ix)
        for x, z, wd in zip(cx, cz, self.wall_normals, strict=True):
            if not np.isfinite(wd).all():
                continue
            yaw = float(np.degrees(np.arctan2(-wd[0], -wd[1]))) % 360  # frente = lejos de la pared
            wall = np.array([x, z]) + wd * self.grid.cell / 2
            c = wall - wd * (it.d / 2 + 0.05)
            box = Box(float(c[0]), float(c[1]), yaw, it.w, it.d, it.h)
            out.append((box, f"{it.name}: contra {_wall_label(box)}"))
        return out

    def free_region_candidates(self, it: Item) -> list[tuple[Box, str]]:
        free = np.isin(self.grid.state, (FREE, NEAR)).astype(np.uint8)
        n, _, stats, cents = cv2.connectedComponentsWithStats(free, connectivity=4)
        if n <= 1:
            return []
        best = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        cx, cz = self.grid.center(np.array([cents[best][1]]), np.array([cents[best][0]]))
        out = []
        for r in np.arange(0, 1.6, 0.15):
            for a in np.linspace(0, 2 * np.pi, max(1, int(r * 25)), endpoint=False):
                for yaw in (self.base, self.base + 90):
                    box = Box(float(cx[0] + r * np.cos(a)), float(cz[0] + r * np.sin(a)), yaw % 360, it.w, it.d, it.h)
                    out.append((box, f"{it.name}: en el centro del espacio libre"))
        return out

    def in_front_of(self, it: Item, host_kind: str, gap: float) -> list[tuple[Box, str]]:
        out = []
        for host, kind in zip(self.placed, self.kinds, strict=True):
            if kind != host_kind:
                continue
            for shift in (0.0, 0.15, -0.15, 0.3, -0.3):
                c = np.array([host.x, host.z]) + host.front() * (host.d / 2 + gap + it.d / 2) + host.right() * shift
                out.append((Box(float(c[0]), float(c[1]), host.yaw, it.w, it.d, it.h),
                            f"{it.name}: {int(gap * 100)} cm delante del sofá"))
        return out

    def around_table(self, it: Item) -> list[tuple[Box, str]]:
        out = []
        for host, kind in zip(self.placed, self.kinds, strict=True):
            if kind not in ("dining_table", "desk"):
                continue
            sides = [(host.front(), host.d), (-host.front(), host.d)] if kind == "dining_table" else [(host.front(), host.d)]
            if kind == "dining_table":
                sides += [(host.right(), host.w), (-host.right(), host.w)]
            for dirv, extent in sides:
                c = np.array([host.x, host.z]) + dirv * (extent / 2 + it.d / 2 - 0.1)
                yaw = float(np.degrees(np.arctan2(-dirv[0], -dirv[1])))  # mirando a la mesa
                out.append((Box(float(c[0]), float(c[1]), yaw % 360, it.w, it.d, it.h),
                            f"{it.name}: junto a la mesa"))
        return out

    def beside_sofa(self, it: Item) -> list[tuple[Box, str]]:
        out = []
        for host, kind in zip(self.placed, self.kinds, strict=True):
            if kind != "sofa":
                continue
            for side in (1, -1):
                c = np.array([host.x, host.z]) + host.right() * side * (host.w / 2 + it.w / 2 + 0.1)
                out.append((Box(float(c[0]), float(c[1]), host.yaw, it.w, it.d, it.h), f"{it.name}: al lado del sofá"))
        return out

    # ---------- puntaje ----------

    def rule_score(self, it: Item, box: Box, note: str) -> float:
        cat = it.category
        if cat in FACE_CAMERA:
            return (1 + facing_camera(box)) / 2
        if cat in SIDE_WALL:
            return 1 - abs(facing_camera(box))
        if cat == "tv_stand":
            sofas = [b for b, k in zip(self.placed, self.kinds, strict=True) if k == "sofa"]
            if sofas:
                to = np.array([sofas[0].x - box.x, sofas[0].z - box.z])
                return (1 + float(box.front() @ (to / max(np.linalg.norm(to), 1e-6)))) / 2
            return 1 - abs(facing_camera(box))
        if cat in DECOR:
            return 1.0 if "esquina" in note or "sofá" in note else 0.6
        if cat == "coffee_table":
            return 1.0 if "sofá" in note else 0.5
        return 0.6

    def score(self, it: Item, box: Box, note: str) -> float:
        return 0.4 * visibility(box, self.frame, self.intr) + 0.3 * distance_score(box) + 0.3 * self.rule_score(it, box, note)

    # ---------- plan ----------

    def candidates_for(self, it: Item) -> list[tuple[Box, str]]:
        cat = it.category
        if cat == "coffee_table":
            return self.in_front_of(it, "sofa", COFFEE_GAP_M) + self.free_region_candidates(it)
        if cat in CENTER:
            return self.free_region_candidates(it)
        if cat == "chair":
            return self.around_table(it) + self.wall_candidates(it)
        if cat in DECOR:
            corners = [(b, n.replace("contra", "en la esquina de")) for b, n in self.wall_candidates(it)
                       if self._is_corner(b)]
            return corners + self.beside_sofa(it) + self.wall_candidates(it)
        if it.against_wall:
            return self.wall_candidates(it)
        return self.free_region_candidates(it) + self.wall_candidates(it)

    def _is_corner(self, box: Box) -> bool:
        iz, ix = self.grid.cell_of(np.array([box.x]), np.array([box.z]))
        r = 3
        zs, xs = slice(max(0, iz[0] - r), iz[0] + r + 1), slice(max(0, ix[0] - r), ix[0] + r + 1)
        dirs = self.grid.wall_dir[zs, xs][self.grid.state[zs, xs] == WALL_EDGE]
        return len(dirs) > 0 and np.abs(dirs[:, 0]).max() > 0.7 and np.abs(dirs[:, 1]).max() > 0.7

    def place(self, it: Item) -> list[Candidate]:
        rug_ids = {i for i, k in enumerate(self.kinds) if k == "rug"}
        ignore = rug_ids if it.category != "rug" else set(range(len(self.placed)))
        scored = []
        for box, note in self.candidates_for(it):
            if is_valid(box, self.grid, self.placed, self.frame, self.intr, ignore_overlap_with=ignore):
                scored.append(Candidate(box, self.score(it, box, note), note))
        scored.sort(key=lambda c: -c.score)
        # quitar candidatos casi iguales para que el top-k sea variado
        top: list[Candidate] = []
        for c in scored:
            if all(np.hypot(c.box.x - t.box.x, c.box.z - t.box.z) > 0.4 or abs(c.box.yaw - t.box.yaw) > 45 for t in top):
                top.append(c)
            if len(top) == TOP_K:
                break
        return top

    def commit(self, it: Item, box: Box) -> None:
        self.placed.append(box)
        self.kinds.append(it.category)


def suggest(grid: Occupancy, items: list[Item], frame: np.ndarray, intrinsics: np.ndarray,
            existing: list[Box] | None = None) -> Result:
    planner = Planner(grid, frame, intrinsics, existing or [])
    order = sorted(range(len(items)), key=lambda i: -(items[i].w * items[i].d))
    # la mesa de centro y la decoración después del sofá, aunque sean grandes
    order.sort(key=lambda i: items[i].category in ("coffee_table", "chair", "nightstand", *DECOR))
    result = Result()
    for i in order:
        it = items[i]
        top = planner.place(it)
        result.candidates[i] = top
        if not top:
            result.notes.append(f"No encontré un lugar donde quepa {it.name}.")
            continue
        planner.commit(it, top[0].box)
        result.placements.append((it, top[0].box))
        result.notes.append(top[0].note)
    return result
