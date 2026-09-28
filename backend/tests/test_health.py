from fastapi.testclient import TestClient

from app import __version__
from app.main import app


def test_health():
    res = TestClient(app).get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["device"] in {"cpu", "mps", "cuda"}
    assert body["version"] == __version__


def test_unknown_api_route_is_404():
    assert TestClient(app).get("/api/no-existe").status_code == 404
