from __future__ import annotations

import re
from datetime import date

from anthropic import Anthropic

from obsidian_journal.config import Config
from obsidian_journal.models import Frontmatter, SpecNote
from obsidian_journal.spec.prompt import SPEC_SYSTEM, TITLE_FALLBACK_SYSTEM

BASELINE_TAGS = ("project-idea", "spec", "active")


def _extract_h1(body: str) -> tuple[str, str]:
    """Return (title, body_without_h1). If no H1, return ("", body)."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            remaining = "\n".join(lines[:i] + lines[i + 1 :]).lstrip("\n")
            return title, remaining
    return "", body


def _merge_tags(extra_tags: list[str]) -> list[str]:
    """Union of baseline tags and caller-provided tags, preserving order, deduped."""
    seen: set[str] = set()
    merged: list[str] = []
    for t in ("project-idea", "spec", *extra_tags, "active"):
        t_norm = t.strip()
        if not t_norm or t_norm in seen:
            continue
        seen.add(t_norm)
        merged.append(t_norm)
    return merged


def synthesize_spec(
    config: Config,
    brief: str,
    *,
    title_override: str | None = None,
    complexity: str = "M",
    priority: str = "medium",
    status: str = "planning",
    source: str = "",
    related: list[str] | None = None,
    extra_tags: list[str] | None = None,
    folder: str = "Project Ideas",
    existing_titles: list[str] | None = None,
) -> SpecNote:
    """Synthesize a SpecNote from a brief using a single Anthropic round."""

    client = Anthropic(api_key=config.anthropic_api_key)
    today = date.today().isoformat()
    titles = existing_titles or []
    titles_str = ", ".join(titles[:200])

    body_response = client.messages.create(
        model=config.model,
        max_tokens=2500,
        system=SPEC_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Brief:\n\n{brief}\n\n"
                    f"Existing note titles you may [[wikilink]] to where genuinely "
                    f"relevant: {titles_str}"
                ),
            }
        ],
    )
    body = body_response.content[0].text.strip()

    h1_title, body_without_h1 = _extract_h1(body)

    if title_override:
        title = title_override.strip()
    elif h1_title:
        title = h1_title
    else:
        title_response = client.messages.create(
            model=config.model,
            max_tokens=50,
            system=TITLE_FALLBACK_SYSTEM,
            messages=[{"role": "user", "content": f"Brief:\n\n{brief}"}],
        )
        title = title_response.content[0].text.strip()

    related_list = list(related or [])
    if titles:
        for t in titles:
            if f"[[{t}]]" in body_without_h1 and t not in related_list:
                related_list.append(t)

    extra: dict[str, str] = {}
    if status:
        extra["status"] = status
    if complexity:
        extra["complexity"] = complexity
    if priority:
        extra["priority"] = priority
    if source:
        extra["source"] = source

    front = Frontmatter(
        date=today,
        tags=_merge_tags(extra_tags or []),
        related=related_list,
        extra=extra,
    )

    return SpecNote(
        title=title,
        body=body_without_h1.strip(),
        frontmatter=front,
        folder=folder,
        complexity=complexity,
        priority=priority,
        status=status,
        source=source,
    )


def slug_for_title(title: str) -> str:
    """Lowercase-hyphenated slug; ensure `-spec` suffix."""
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    if not s.endswith("-spec"):
        s = f"{s}-spec"
    return s
