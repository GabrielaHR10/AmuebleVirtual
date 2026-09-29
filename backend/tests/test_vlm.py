import numpy as np

from app.placement import vlm
from app.placement.heuristic import Item, suggest
from tests.test_occupancy import _grid

SOFA = Item("sofa", "Sofá", "sofa", 2.0, 0.9, 0.85, True)
PLANT = Item("planta", "Planta", "plant", 0.5, 0.5, 0.9, False)


def _result():
    grid, frame = _grid()
    fy = 0.5 / np.tan(np.radians(70) / 2)
    intr = np.array([[fy * 360 / 270, 0, 0.5], [0, fy, 0.5], [0, 0, 1]])
    items = [SOFA, PLANT]
    return suggest(grid, items, frame, intr), items


def _numbering(res):
    out, n = {}, 0
    for i, cands in sorted(res.candidates.items()):
        for j in range(len(cands)):
            n += 1
            out[n] = (i, j)
    return out


def test_apply_valid_choice():
    res, items = _result()
    numbering = _numbering(res)
    second_sofa = next(k for k, (i, j) in numbering.items() if i == 0 and j == 1)
    out, notes = vlm.apply_choices(res, items, numbering, {"choices": [
        {"item_id": "sofa", "candidate": second_sofa, "reason": "Junto a la ventana"}]})
    sofa_box = next(b for it, b in out.placements if it.item_id == "sofa")
    assert sofa_box is res.candidates[0][1].box
    assert "Junto a la ventana (IA local)" in notes[0]


def test_ignores_invented_numbers_and_wrong_items():
    res, items = _result()
    numbering = _numbering(res)
    out, notes = vlm.apply_choices(res, items, numbering, {"choices": [
        {"item_id": "sofa", "candidate": 999}, {"item_id": "planta", "candidate": 1}]})
    assert [b for _, b in out.placements] == [b for _, b in res.placements]
    assert all("sugerencia básica" in n for n in notes)


def test_falls_back_when_ollama_is_off(monkeypatch):
    res, items = _result()
    monkeypatch.setattr(vlm, "OLLAMA_URL", "http://127.0.0.1:9")  # puerto cerrado
    out, notes, used = vlm.choose_with_vlm(None, res, items)
    assert not used and out is res and notes[-1] == vlm.FALLBACK_NOTE
