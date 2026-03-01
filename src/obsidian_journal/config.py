from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    vault_path: Path
    anthropic_api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_rounds: int = 4
    location_lat: float | None = None
    location_lon: float | None = None
    daily_notes_folder: str = "Daily Notes"

    @classmethod
    def load(cls) -> Config:
        load_dotenv()
        vault_path_str = os.environ.get("OBSIDIAN_VAULT_PATH", "")
        if not vault_path_str:
            raise ValueError("OBSIDIAN_VAULT_PATH not set in environment or .env")
        vault_path = Path(vault_path_str)
        if not vault_path.is_dir():
            raise ValueError(f"Vault path does not exist: {vault_path}")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment or .env")

        lat_str = os.environ.get("OJ_LOCATION_LAT", "")
        lon_str = os.environ.get("OJ_LOCATION_LON", "")
        location_lat = float(lat_str) if lat_str else None
        location_lon = float(lon_str) if lon_str else None

        return cls(
            vault_path=vault_path,
            anthropic_api_key=api_key,
            model=os.environ.get("OJ_MODEL", "claude-sonnet-4-20250514"),
            max_rounds=int(os.environ.get("OJ_MAX_ROUNDS", "4")),
            location_lat=location_lat,
            location_lon=location_lon,
            daily_notes_folder=os.environ.get("OJ_DAILY_NOTES_FOLDER", "Daily Notes"),
        )
