import os

from xxcli import config


def _full_credentials():
    return {
        "x_api_key": "config-key",
        "x_api_secret": "config-secret",
        "x_access_token": "config-token",
        "x_access_token_secret": "config-token-secret",
        "openai_api_key": "config-openai",
    }


def test_load_config_missing_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".xxcli")
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / ".xxcli" / "config.yaml")
    assert config.load_config() == {}


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".xxcli")
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / ".xxcli" / "config.yaml")
    payload = {"credentials": _full_credentials(), "default_repo": "~/Code/xxcli"}
    config.save_config(payload)
    assert config.load_config() == payload


def test_get_credentials_prefers_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".xxcli")
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / ".xxcli" / "config.yaml")
    config.save_config({"credentials": _full_credentials()})

    monkeypatch.setenv("X_API_KEY", "env-key")
    monkeypatch.setenv("X_API_SECRET", "env-secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "env-token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "env-token-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")

    creds = config.get_credentials()
    assert creds["x_api_key"] == "env-key"
    assert creds["openai_api_key"] == "env-openai"
