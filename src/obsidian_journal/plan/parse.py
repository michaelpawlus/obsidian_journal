from __future__ import annotations

import re

# Matches lines like:
#   - **08:30 - 09:00** | Standup [HIGH]
#   - **09:00 - 10:30** | 🕐 1:1 with manager [MED]
_BLOCK_RE = re.compile(
    r"""^\s*-\s*\*\*
        (?P<start>\d{1,2}:\d{2})
        \s*-\s*
        (?P<end>\d{1,2}:\d{2})
        \*\*\s*\|\s*
        (?P<task>.+?)
        (?:\s*\[(?P<priority>HIGH|MED|LOW)\])?
        \s*$""",
    re.IGNORECASE | re.VERBOSE,
)


def parse_blocks(markdown: str) -> list[dict]:
    """Best-effort parse of the time-blocked schedule emitted by `synthesize_plan`.

    Returns one dict per recognized block; lines that don't match are skipped.
    Agents can fall back to the `markdown` field when this list is empty.
    """
    blocks: list[dict] = []
    for line in markdown.splitlines():
        m = _BLOCK_RE.match(line)
        if not m:
            continue
        blocks.append(
            {
                "start": m.group("start"),
                "end": m.group("end"),
                "task": m.group("task").strip(),
                "priority": (m.group("priority") or "").upper() or None,
            }
        )
    return blocks
