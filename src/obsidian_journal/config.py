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
        return cls(
            vault_path=vault_path,
            anthropic_api_key=api_key,
            model=os.environ.get("OJ_MODEL", "claude-sonnet-4-20250514"),
            max_rounds=int(os.environ.get("OJ_MAX_ROUNDS", "4")),
        )
