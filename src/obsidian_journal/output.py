from __future__ import annotations

import json
import sys


def emit_json(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def emit_error(message: str, code: int = 1) -> None:
    print(json.dumps({"error": message, "code": code}))
    raise SystemExit(code)


def is_interactive() -> bool:
    return sys.stdin.isatty()
