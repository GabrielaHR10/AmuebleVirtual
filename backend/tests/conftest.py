import pytest

from app import scenes, storage


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """data/ temporal para no ensuciar el repo."""
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "SCENES_DIR", tmp_path / "scenes")
    monkeypatch.setattr(scenes, "SCENES_DIR", tmp_path / "scenes")
    return tmp_path
