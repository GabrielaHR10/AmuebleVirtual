import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.catalog import extract
from app.config import SAMPLES_DIR
from app.main import app
from app.placement import vlm


def test_endpoint_prefills_from_vlm(monkeypatch, data_dir):
    monkeypatch.setattr(vlm, "status", lambda: {"available": True})
    monkeypatch.setattr(vlm, "ask_ollama", lambda *a, **k: {
        "raw_table": {"Medidas": "Alto: 74 Ancho: 203 Profundidad: 88"},
        "width_cm": 203, "depth_cm": 88, "height_cm": 74, "extra_dimensions_cm": {"asiento": 0}, "units_detected": "cm"})
    img = SAMPLES_DIR / "furniture" / "MuebleBlancoClickclack" / "medidasclickclack.png"
    res = TestClient(app).post("/api/catalog/extract-dimensions", files={"table_image": ("t.png", img.read_bytes(), "image/png")})
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["width_cm"], body["depth_cm"], body["height_cm"]) == (203, 88, 74)
    assert body["extra_dimensions_cm"] == {}  # valores ≤ 0 se descartan


def test_endpoint_without_ollama_says_to_type(monkeypatch):
    monkeypatch.setattr(vlm, "status", lambda: {"available": False})
    img = SAMPLES_DIR / "furniture" / "MesaGretel" / "mesaGretelmedidas.png"
    res = TestClient(app).post("/api/catalog/extract-dimensions", files={"table_image": ("t.png", img.read_bytes(), "image/png")})
    assert res.status_code == 503 and "a mano" in res.json()["detail"]


def test_absurd_values_rejected(monkeypatch):
    monkeypatch.setattr(vlm, "status", lambda: {"available": True})
    monkeypatch.setattr(vlm, "ask_ollama", lambda *a, **k: {"width_cm": 2030, "depth_cm": 88, "height_cm": 74})
    with pytest.raises(extract.ExtractionError):
        extract.extract_dimensions(Image.new("RGB", (10, 10)))


TABLES = sorted(p for p in (SAMPLES_DIR / "furniture").glob("*/*") if "medidas" in p.name.lower())


@pytest.mark.slow
@pytest.mark.skipif(not vlm.status()["available"], reason="IA local (Ollama) no disponible")
def test_real_tables_against_verified_specs():
    """PLAN 3.6: comparar la extracción con los mueble.json verificados (±1 cm)."""
    hits, total, report = 0, 0, []
    for table in TABLES:
        spec = json.loads((table.parent / "mueble.json").read_text())
        got = extract.extract_dimensions(Image.open(table))
        want = spec["dimensions_cm"]
        for key, val in (("width", got.width_cm), ("depth", got.depth_cm), ("height", got.height_cm)):
            ok = abs(val - want[key]) <= 1
            hits += ok
            total += 1
            report.append(f"{Path(table).parent.name} {key}: {val} vs {want[key]} {'OK' if ok else 'X'}")
    print(f"\\nAciertos {hits}/{total}\\n" + "\\n".join(report))
    assert hits / total >= 0.66
