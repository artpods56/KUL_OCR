import pytest

from backend import dependencies


def test_get_file_storage_unsupported_raises(monkeypatch):
    class DummyConfig:
        storage_type = "unknown"
        storage_root = "/tmp"

    dependencies.get_config.cache_clear()
    dependencies.get_file_storage.cache_clear()

    def fake_get_config():
        return DummyConfig()

    monkeypatch.setattr(dependencies, "get_config", fake_get_config)

    with pytest.raises(NotImplementedError):
        dependencies.get_file_storage()
