"""Configuration helpers for xxcli."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path.home() / ".xxcli"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

_ENV_TO_CONFIG_KEY = {
    "X_API_KEY": "x_api_key",
    "X_API_SECRET": "x_api_secret",
    "X_ACCESS_TOKEN": "x_access_token",
    "X_ACCESS_TOKEN_SECRET": "x_access_token_secret",
    "OPENAI_API_KEY": "openai_api_key",
}


def load_config() -> dict[str, Any]:
    """Read config.yaml and never raise on missing or corrupt data."""
    if not CONFIG_FILE.exists():
        return {}

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):
        return {}

    return data if isinstance(data, dict) else {}


def save_config(data: dict[str, Any]) -> None:
    """Persist config.yaml, creating the data directory if needed."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def get_credentials() -> dict[str, str] | None:
    """Resolve credentials with env vars taking precedence over config values."""
    config = load_config()
    stored = config.get("credentials", {})
    if not isinstance(stored, dict):
        stored = {}

    resolved = {}
    for env_name, config_key in _ENV_TO_CONFIG_KEY.items():
        value = os.environ.get(env_name) or stored.get(config_key)
        if not value:
            return None
        resolved[config_key] = value

    return resolved


def get_default_repo() -> str | None:
    """Return the configured default repo path, if present."""
    default_repo = load_config().get("default_repo")
    return default_repo if isinstance(default_repo, str) and default_repo else None


def get_streak() -> dict[str, Any]:
    """Return normalized streak data."""
    streak = load_config().get("streak", {})
    if not isinstance(streak, dict):
        streak = {}
    return {
        "last_digest_run": streak.get("last_digest_run"),
        "consecutive_days": int(streak.get("consecutive_days", 0) or 0),
    }


def update_streak() -> dict[str, Any]:
    """Update the digest streak based on the last recorded run."""
    config = load_config()
    streak = get_streak()
    now = datetime.now(timezone.utc)
    consecutive_days = streak["consecutive_days"]

    last_run_raw = streak.get("last_digest_run")
    last_run = _parse_datetime(last_run_raw)
    if last_run is None:
        consecutive_days = 1
    else:
        delta_days = (now.date() - last_run.date()).days
        if delta_days == 0:
            consecutive_days = consecutive_days or 1
        elif delta_days == 1:
            consecutive_days = (consecutive_days or 0) + 1
        else:
            consecutive_days = 1

    updated = {
        "last_digest_run": now.isoformat().replace("+00:00", "Z"),
        "consecutive_days": consecutive_days,
    }
    config["streak"] = updated
    save_config(config)
    return updated


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
