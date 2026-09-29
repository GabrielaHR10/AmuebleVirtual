import numpy as np
import pytest
from PIL import Image

from app.catalog.cutout import crop_to_alpha, keep_main_object, make_cutout, make_thumb, proportion_check
from app.config import SAMPLES_DIR


def test_keep_main_object_drops_small_blobs():
    alpha = np.zeros((100, 200), np.uint8)
    alpha[20:80, 20:150] = 255  # mueble
    alpha[5:15, 180:195] = 255  # planta suelta
    out = keep_main_object(alpha)
    assert out[50, 50] == 255 and out[10, 185] == 0


def test_crop_to_alpha_with_margin():
    arr = np.zeros((100, 200, 4), np.uint8)
    arr[40:60, 50:150, 3] = 255
    cut = crop_to_alpha(Image.fromarray(arr, "RGBA"))
    assert cut.size == (104, 20)  # 100×20 + 2 % de margen por lado (en 20 px redondea a 0)


def test_crop_to_alpha_empty_raises():
    with pytest.raises(ValueError, match="mueble"):
        crop_to_alpha(Image.new("RGBA", (10, 10)))


def test_thumb_is_square_rgba():
    thumb = make_thumb(Image.new("RGBA", (500, 200), (255, 0, 0, 255)))
    assert thumb.size == (256, 256) and thumb.mode == "RGBA"


def test_proportion_check():
    assert proportion_check(2.1, 210, 100) is None
    assert "de frente" in proportion_check(2.1, 203, 74)


PHOTOS = sorted(p for p in (SAMPLES_DIR / "furniture").glob("*/*.png") if "medidas" not in p.name.lower())


@pytest.mark.slow
@pytest.mark.parametrize("path", PHOTOS, ids=lambda p: p.parent.name)
def test_real_cutouts_have_alpha(path):
    cut = make_cutout(Image.open(path))
    alpha = np.asarray(cut.image)[..., 3]
    assert cut.image.mode == "RGBA" and cut.image.width > 0 and cut.image.height > 0
    assert (alpha > 127).mean() > 0.2  # el objeto ocupa buena parte del recorte
