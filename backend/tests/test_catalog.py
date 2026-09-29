import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.catalog import cutout, service
from app.main import app
from app.schemas import CatalogItem


def _png() -> bytes:
    buf = io.BytesIO()
    Image.fromarray(np.full((300, 500, 3), 200, np.uint8)).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def fake_cutout(monkeypatch):
    """El recorte real (rembg) es lento: se simula con un rectángulo 2.3:1."""
    def fake(photo):
        img = Image.new("RGBA", (460, 200), (90, 90, 90, 255))
        return cutout.Cutout(image=img, thumb=cutout.make_thumb(img), ratio=2.3)
    monkeypatch.setattr(cutout, "make_cutout", fake)


def _form(**over):
    data = {"name": "Sofá Gris 3P", "category": "sofa", "width_cm": "210", "depth_cm": "90", "height_cm": "85"}
    data.update(over)
    return data


def test_slugify():
    assert service.slugify("MesaGretel") == "mesa-gretel"
    assert service.slugify("Sofá Gris 3P") == "sofa-gris-3p"
    assert service.slugify("MuebleAzulEdingburgh") == "mueble-azul-edingburgh"


def test_create_list_delete(data_dir):
    client = TestClient(app)
    assert client.get("/api/catalog").json() == []
    res = client.post("/api/catalog", data=_form(), files={"photo": ("s.png", _png(), "image/png")})
    assert res.status_code == 200, res.text
    item = res.json()
    assert item["id"] == "sofa-gris-3p" and item["user_created"] and item["against_wall"]
    assert item["dimensions_cm"] == {"width": 210, "depth": 90, "height": 85}
    folder = data_dir / "catalog" / "sofa-gris-3p"
    for name in ("foto.jpg", "cutout.png", "thumb.png"):
        assert (folder / name).is_file(), name
    assert item["cutout_url"] == "/files/catalog/sofa-gris-3p/cutout.png"
    assert item["cutout_ratio"] == 2.3
    assert item["photo_warning"] is None  # tabla 210/85 = 2.47 vs. recorte 2.3 → 7 %
    assert [i["id"] for i in client.get("/api/catalog").json()] == ["sofa-gris-3p"]

    again = client.post("/api/catalog", data=_form(), files={"photo": ("s.png", _png(), "image/png")})
    assert again.json()["id"] == "sofa-gris-3p-2"

    assert client.delete("/api/catalog/sofa-gris-3p").json() == {"ok": True}
    assert [i["id"] for i in client.get("/api/catalog").json()] == ["sofa-gris-3p-2"]
    assert client.delete("/api/catalog/no-existe").status_code == 404


def test_rejects_bad_input(data_dir):
    client = TestClient(app)
    bad_dims = client.post("/api/catalog", data=_form(height_cm="350"),
                           files={"photo": ("s.png", _png(), "image/png")})
    assert bad_dims.status_code == 422 and "Medidas" in bad_dims.json()["detail"]
    bad_photo = client.post("/api/catalog", data=_form(), files={"photo": ("s.png", b"nada", "image/png")})
    assert bad_photo.status_code == 400


def test_cannot_delete_seed_items(data_dir):
    service.save_item(CatalogItem(
        id="mesa-x", name="Mesa X", category="dining_table",
        dimensions_cm={"width": 80, "depth": 140, "height": 75}, dimensions_source="tabla_medidas",
        against_wall=False, source="prueba", license="prueba"))
    assert TestClient(app).delete("/api/catalog/mesa-x").status_code == 403


def test_build_skips_invalid_specs(data_dir):
    (data_dir / "catalog" / "roto").mkdir(parents=True)
    (data_dir / "catalog" / "roto" / "mueble.json").write_text("{}")
    assert service.build_catalog() == []


def test_proportion_warning_and_table_image(data_dir):
    client = TestClient(app)
    res = client.post("/api/catalog", data=_form(name="Silla", category="chair", width_cm="45",
                                                 depth_cm="50", height_cm="90"),
                      files={"photo": ("m.png", _png(), "image/png"), "table_image": ("t.png", _png(), "image/png")})
    assert res.status_code == 200, res.text
    item = res.json()
    assert "de frente" in item["photo_warning"]  # recorte 2.3 vs. tabla 0.5
    assert (data_dir / "catalog" / "silla" / "medidas.jpg").is_file()
    assert not item["against_wall"]
