from __future__ import annotations

import json
import sys
from typing import Any

OJ_VERSION = "0.3"


def _stamp(data: Any) -> Any:
    if isinstance(data, dict):
        if "_oj_version" not in data:
            stamped = {"_oj_version": OJ_VERSION}
            stamped.update(data)
            return stamped
        return data
    if isinstance(data, list):
        return {"_oj_version": OJ_VERSION, "items": data}
    return {"_oj_version": OJ_VERSION, "value": data}


def emit_json(data: Any) -> None:
    """Emit a single JSON object to stdout. Stamps `_oj_version` for downstream pinning.

    Lists are wrapped as `{"_oj_version": ..., "items": [...]}` so every emission
    is a single object — agents can rely on parsing one top-level dict.
    """
    sys.stdout.write(json.dumps(_stamp(data), indent=2, default=str))
    sys.stdout.write("\n")
    sys.stdout.flush()


def emit_error(message: str, code: int = 1) -> None:
    """Emit a JSON error object to stdout and exit with the given code."""
    sys.stdout.write(
        json.dumps(
            {"_oj_version": OJ_VERSION, "error": message, "code": code},
        )
    )
    sys.stdout.write("\n")
    sys.stdout.flush()
    raise SystemExit(code)


def is_interactive() -> bool:
    return sys.stdin.isatty()
