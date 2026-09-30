import numpy as np

from app.video.clips import DEPTH_FAR_M, compose_frame, unpack_depth


def pack(meters: float) -> list[int]:
    """Misma codificación que el shader del frontend (base 255 en RGB)."""
    v = meters / DEPTH_FAR_M
    enc = np.array([1.0, 255.0, 65025.0]) * v
    enc = enc - np.floor(enc)
    enc[:2] -= enc[1:] / 255.0
    return [round(x * 255) for x in enc]


def test_unpack_roundtrip():
    for m in (0.5, 1.234, 3.7, 12.0):
        rgba = np.array([[pack(m) + [255]]], np.uint8)
        assert abs(unpack_depth(rgba)[0, 0] - m) < 0.01
    assert unpack_depth(np.zeros((1, 1, 4), np.uint8))[0, 0] == 0


def test_compose_hides_furniture_behind_real_objects():
    photo = np.full((4, 4, 3), 100, np.uint8)
    color = np.zeros((4, 4, 4), np.uint8)
    color[..., :3] = 200
    color[..., 3] = 255
    furn = np.full((4, 4), 3.0)
    scene = np.full((4, 4), 5.0, np.float32)
    scene[:, :2] = 1.0  # una pared real más cerca en la mitad izquierda
    out = compose_frame(photo, color, furn, scene)
    assert out[1, 0, 0] < 130  # tapado: queda la foto
    assert out[1, 3, 0] > 170  # visible: el mueble
