import time

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app import videos
from app.main import app
from app.video.keyframes import extract_keyframes, sharpness


def make_video(path, seconds=4, fps=10, size=(160, 120)):
    """Video sintético: cuadros borrosos y, cada tanto, uno nítido (tablero de ajedrez)."""
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    rng = np.random.default_rng(0)
    for i in range(seconds * fps):
        img = np.full((size[1], size[0], 3), 120, np.uint8)
        if i % 7 == 3:
            img[::8, :] = 250
            img[:, ::8] = 10
        else:
            img[:] = cv2.GaussianBlur(rng.integers(90, 150, img.shape, dtype=np.uint8), (0, 0), 6)
        w.write(img)
    w.release()


def test_sharpness_prefers_edges():
    flat = np.full((50, 50), 128, np.uint8)
    grid = flat.copy()
    grid[::5] = 255
    assert sharpness(grid) > sharpness(flat)


def test_extract_keyframes_windows(tmp_path):
    path = tmp_path / "v.mp4"
    make_video(path)
    windows = extract_keyframes(path, n=4, per_window=2, min_gap_s=0.5)
    assert 1 <= len(windows) <= 4
    for w in windows:
        assert 1 <= len(w) <= 2
        assert w[0].sharpness >= w[-1].sharpness


def _wait(client, job_id, timeout=30):
    t = time.time()
    while time.time() - t < timeout:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.1)
    raise AssertionError("el trabajo no terminó")


def test_upload_video_creates_keyframes(tmp_path, data_dir, monkeypatch):
    monkeypatch.setattr(videos, "floor_score", lambda img: 0.2)
    path = tmp_path / "v.mp4"
    make_video(path)
    client = TestClient(app)
    res = client.post("/api/videos", files={"file": ("tour.mp4", path.read_bytes(), "video/mp4")})
    assert res.status_code == 200, res.text
    job = _wait(client, res.json()["job_id"])
    assert job["status"] == "done", job
    meta = client.get(f"/api/videos/{res.json()['video_id']}").json()
    assert meta["keyframes"] and all(k["url"].endswith(".jpg") for k in meta["keyframes"])


def test_video_errors(tmp_path, data_dir):
    client = TestClient(app)
    assert client.post("/api/videos", files={"file": ("x.avi", b"x", "video/x")}).status_code == 400
    bad = client.post("/api/videos", files={"file": ("x.mp4", b"no es video", "video/mp4")})
    assert bad.status_code == 400 and "video" in bad.json()["detail"].lower()
    assert client.get("/api/jobs/job_noexiste").status_code == 404
    assert client.get("/api/videos/vid_noexiste").status_code == 404
