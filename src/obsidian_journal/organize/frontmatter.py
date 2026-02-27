from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

from obsidian_journal.config import Config
from obsidian_journal.models import Frontmatter, Note
from obsidian_journal import vault

console = Console()

# Match inline tags like "Tags: #tag1 #tag2" or "tags: #foo, #bar"
INLINE_TAGS_RE = re.compile(r"^[Tt]ags?:\s*(.+)$", re.MULTILINE)
TAG_RE = re.compile(r"#([\w/\-]+)")

# Daily note filename pattern: YYYY-MM-DD
DAILY_NOTE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def scan_frontmatter(config: Config) -> list[tuple[Note, Frontmatter]]:
    """Scan notes and return list of (note, suggested_frontmatter) for notes needing updates."""
    notes = vault.list_notes(config)
    suggestions: list[tuple[Note, Frontmatter]] = []

    for note in notes:
        new_front = _suggest_frontmatter(note)
        if new_front:
            suggestions.append((note, new_front))

    return suggestions


def _suggest_frontmatter(note: Note) -> Frontmatter | None:
    current = note.frontmatter
    changed = False
    new_front = Frontmatter(
        date=current.date,
        type=current.type,
        tags=list(current.tags),
        related=list(current.related),
        extra=dict(current.extra),
    )

    # Infer date from filename for Daily Notes
    if not new_front.date:
        match = DAILY_NOTE_RE.match(note.title)
        if match:
            new_front.date = match.group(1)
            changed = True

    # Extract inline tags from body
    inline_match = INLINE_TAGS_RE.search(note.body)
    if inline_match:
        found_tags = TAG_RE.findall(inline_match.group(1))
        for tag in found_tags:
            if tag not in new_front.tags:
                new_front.tags.append(tag)
                changed = True

    # Infer type from folder
    if not new_front.type:
        if note.folder == "Daily Notes":
            new_front.type = "daily"
            changed = True
        elif note.folder == "Journal":
            new_front.type = "journal"
            changed = True

    # If note has no frontmatter at all, suggest minimal
    if not current.date and not current.type and not current.tags and not changed:
        return None

    return new_front if changed else None


def preview_frontmatter(suggestions: list[tuple[Note, Frontmatter]]) -> None:
    if not suggestions:
        console.print("[green]All notes have complete frontmatter.[/green]")
        return

    table = Table(title=f"Frontmatter Updates ({len(suggestions)} notes)")
    table.add_column("Note", style="cyan")
    table.add_column("Folder", style="dim")
    table.add_column("Changes", style="yellow")

    for note, new_front in suggestions:
        changes = []
        if new_front.date and new_front.date != note.frontmatter.date:
            changes.append(f"date: {new_front.date}")
        if new_front.type and new_front.type != note.frontmatter.type:
            changes.append(f"type: {new_front.type}")
        new_tags = set(new_front.tags) - set(note.frontmatter.tags)
        if new_tags:
            changes.append(f"tags: +{', '.join(new_tags)}")
        table.add_row(note.title, note.folder or "(root)", "; ".join(changes))

    console.print(table)


def apply_frontmatter(config: Config, suggestions: list[tuple[Note, Frontmatter]]) -> int:
    count = 0
    for note, new_front in suggestions:
        note.frontmatter = new_front
        # Remove inline tags line from body if we extracted them
        note.body = INLINE_TAGS_RE.sub("", note.body).strip()
        vault.write_note(config, note)
        count += 1
    return count
