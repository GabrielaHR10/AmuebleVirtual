import numpy as np

from app.geometry.occupancy import WALL_EDGE
from app.placement.geometry2d import facing_camera, overlap
from app.placement.heuristic import Item, suggest
from tests.test_occupancy import _grid

SOFA = Item("sofa", "Sofá", "sofa", 2.0, 0.9, 0.85, True)
COFFEE = Item("mesa", "Mesa de centro", "coffee_table", 1.1, 0.6, 0.4, False)
PLANT = Item("planta", "Planta", "plant", 0.5, 0.5, 0.9, False)
SHELF = Item("estante", "Estantería", "shelf", 1.0, 0.35, 1.6, True)



def test_sofa_against_wall_and_coffee_table_in_front():
    grid, frame = _grid()
    fy = 0.5 / np.tan(np.radians(70) / 2)
    intr = np.array([[fy * 360 / 270, 0, 0.5], [0, fy, 0.5], [0, 0, 1]])
    res = suggest(grid, [COFFEE, SOFA, PLANT, SHELF], frame, intr)
    placed = {it.item_id: box for it, box in res.placements}
    assert set(placed) == {"sofa", "mesa", "planta", "estante"}, res.notes

    sofa = placed["sofa"]
    # espalda del sofá pegada a una pared: el punto 15 cm detrás del respaldo es pared/borde de pared
    back = np.array([sofa.x, sofa.z]) - sofa.front() * (sofa.d / 2 + 0.1)
    iz, ix = grid.cell_of(np.array([back[0]]), np.array([back[1]]))
    assert grid.state[iz[0], ix[0]] in (WALL_EDGE, 4)
    assert facing_camera(sofa) > 0.7  # contra la pared del fondo, mirando a la cámara

    mesa = placed["mesa"]
    gap = (np.array([mesa.x, mesa.z]) - np.array([sofa.x, sofa.z])) @ sofa.front() - sofa.d / 2 - mesa.d / 2
    assert abs(gap - 0.45) < 0.05 and abs(mesa.yaw - sofa.yaw) < 1

    boxes = list(placed.values())
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not overlap(boxes[i].corners(), boxes[j].corners())
    assert any("delante del sofá" in n for n in res.notes)


def test_reports_when_nothing_fits():
    grid, frame = _grid()
    fy = 0.5 / np.tan(np.radians(70) / 2)
    intr = np.array([[fy * 360 / 270, 0, 0.5], [0, fy, 0.5], [0, 0, 1]])
    huge = Item("gigante", "Mueble gigante", "wardrobe", 6.0, 1.0, 2.0, True)
    res = suggest(grid, [huge], frame, intr)
    assert res.placements == [] and "No encontré" in res.notes[0]
