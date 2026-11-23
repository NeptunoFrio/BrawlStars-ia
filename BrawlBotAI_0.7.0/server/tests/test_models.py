import os
from pathlib import Path
from brawlbot import models


def test_register_trained_model(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAWLBOT_DATA_DIR", str(tmp_path))

    fake = tmp_path / "fake_ppo.zip"
    fake.write_bytes(b"PK\x03\x04" + b"x" * 100)

    item = models.register_trained_model(
        source_path=fake,
        brain_type="ppo",
        description="test model",
        version="0.0.1-test",
        filename="test_ppo.zip",
        activate=False,
    )

    assert item["id"]
    assert item["brain_type"] == "ppo"
    assert item["version"] == "0.0.1-test"
    assert Path(item["path"]).exists()

    registry = models.list_models()
    assert any(m["id"] == item["id"] for m in registry["models"])
    assert registry["active_model"] is None


def test_register_and_activate(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAWLBOT_DATA_DIR", str(tmp_path))
    fake = tmp_path / "fake2.zip"
    fake.write_bytes(b"PK\x03\x04" + b"y" * 100)

    item = models.register_trained_model(
        source_path=fake,
        brain_type="ppo",
        activate=True,
    )
    registry = models.list_models()
    assert registry["active_model"] == item["id"]
