import numpy as np
import pytest
from PIL import Image

from app.geometry.moge_runner import UnsupportedImageError, load_image, resize_for_inference


def test_load_image_applies_exif_orientation(tmp_path):
    path = tmp_path / "rotada.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # rotar 90° al mostrar
    Image.fromarray(np.zeros((40, 80, 3), np.uint8)).save(path, exif=exif)
    assert load_image(path).size == (40, 80)


def test_load_image_rejects_non_image(tmp_path):
    path = tmp_path / "foto.heic"
    path.write_bytes(b"no es una imagen")
    with pytest.raises(UnsupportedImageError, match="JPG o PNG"):
        load_image(path)


def test_resize_for_inference_keeps_aspect():
    small = resize_for_inference(Image.new("RGB", (960, 1280)))
    assert small.size == (768, 1024)
    assert resize_for_inference(Image.new("RGB", (500, 300))).size == (500, 300)
