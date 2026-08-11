from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> str:
    return os.environ.get("DATA_DIR", "/data")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: str = _default_data_dir()
    api_token: str = ""
    timezone: str = "Europe/Vienna"
    dev_mode: bool = False

    @property
    def database_url(self) -> str:
        path = Path(self.data_dir)
        path.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path / 'booking.db'}"


def _load_hass_options(settings: Settings) -> Settings:
    """Overlay Home Assistant add-on options when present."""
    options_path = Path("/data/options.json")
    if not options_path.exists():
        return settings
    try:
        options = json.loads(options_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings
    updates: dict = {}
    if options.get("api_token"):
        updates["api_token"] = options["api_token"]
    if options.get("timezone"):
        updates["timezone"] = options["timezone"]
    if updates:
        return settings.model_copy(update=updates)
    return settings


@lru_cache
def get_settings() -> Settings:
    raw = Settings(
        data_dir=os.environ.get("DATA_DIR", "/data"),
        api_token=os.environ.get("API_TOKEN", ""),
        timezone=os.environ.get("TZ", os.environ.get("TIMEZONE", "Europe/Vienna")),
        dev_mode=os.environ.get("DEV_MODE", "0") in ("1", "true", "True", "yes"),
    )
    return _load_hass_options(raw)
