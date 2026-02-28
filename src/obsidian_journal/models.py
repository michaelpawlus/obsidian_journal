from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReflectionType(str, Enum):
    END_OF_DAY = "end-of-day"
    END_OF_PROJECT = "end-of-project"
    PODCAST = "podcast"
    MEETING = "meeting"
    READING = "reading"
    FREE_FORM = "free-form"


@dataclass
class Frontmatter:
    date: str = ""
    type: str = ""
    tags: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.date:
            d["date"] = self.date
        if self.type:
            d["type"] = self.type
        if self.tags:
            d["tags"] = self.tags
        if self.related:
            d["related"] = self.related
        d.update(self.extra)
        return d


@dataclass
class Note:
    title: str
    body: str
    frontmatter: Frontmatter = field(default_factory=Frontmatter)
    folder: str = ""

    @property
    def filename(self) -> str:
        return f"{self.title}.md"


@dataclass
class ConversationMessage:
    role: str  # "user" or "assistant"
    content: str
