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
    path: str = ""  # Relative path within the vault, e.g. "Journal/2026-04-27 Foo.md"
    modified_at: str = ""  # ISO-8601 mtime, populated by vault loaders

    @property
    def filename(self) -> str:
        return f"{self.title}.md"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "title": self.title,
            "folder": self.folder,
            "filename": self.filename,
            "frontmatter": self.frontmatter.to_dict(),
            "body": self.body,
        }
        if self.path:
            d["path"] = self.path
        if self.modified_at:
            d["modified_at"] = self.modified_at
        return d

    def to_summary_dict(self) -> dict[str, Any]:
        """Slim shape for `oj list --json`: path, title, modified_at, tags."""
        return {
            "path": self.path,
            "title": self.title,
            "modified_at": self.modified_at,
            "tags": list(self.frontmatter.tags),
            "date": self.frontmatter.date,
            "type": self.frontmatter.type,
        }


@dataclass
class SpecNote(Note):
    """A project-idea / feature spec written by `oj spec`.

    Spec-specific fields live on the dataclass; they're mirrored into
    `frontmatter.extra` at write time so they round-trip through `Frontmatter.to_dict()`.
    """

    complexity: str = ""
    priority: str = ""
    status: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        if self.complexity:
            d["complexity"] = self.complexity
        if self.priority:
            d["priority"] = self.priority
        if self.status:
            d["status"] = self.status
        if self.source:
            d["source"] = self.source
        return d


@dataclass
class ConversationMessage:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class WeatherInfo:
    temperature_high_f: float
    temperature_low_f: float
    condition: str
    precipitation_chance: int
    wind_speed_mph: float
    sunrise: str
    sunset: str
    best_outdoor_window: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "temperature_high_f": self.temperature_high_f,
            "temperature_low_f": self.temperature_low_f,
            "condition": self.condition,
            "precipitation_chance": self.precipitation_chance,
            "wind_speed_mph": self.wind_speed_mph,
            "sunrise": self.sunrise,
            "sunset": self.sunset,
            "best_outdoor_window": self.best_outdoor_window,
            "summary": self.summary,
        }
