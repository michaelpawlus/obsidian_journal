from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

from obsidian_journal.config import Config
from obsidian_journal.models import Note
from obsidian_journal.organize.analyze import analyze_content
from obsidian_journal import vault

console = Console()

# Keyword-based folder heuristics
FOLDER_KEYWORDS: dict[str, list[str]] = {
    "AI Adoption": ["ai", "gpt", "llm", "claude", "gemini", "copilot", "machine learning", "artificial intelligence"],
    "Documentation": ["documentation", "guide", "how to", "setup", "install", "tutorial"],
    "Daily Notes": [],  # Only matched by filename pattern
}

CLASSIFY_PROMPT = """\
You are an Obsidian vault organizer. Given a note's title and content, and a list of \
existing folders, suggest which folder the note best belongs in.

Rules:
- Only suggest a move if there's a clear fit
- If the note doesn't clearly belong anywhere, respond with "NONE"
- Respond with ONLY the folder name or "NONE"

Existing folders: {folders}
"""


@dataclass
class MoveSuggestion:
    note: Note
    current_folder: str
    suggested_folder: str
    reason: str


def scan_structure(config: Config, deep: bool = False) -> list[MoveSuggestion]:
    notes = vault.list_notes(config)
    suggestions: list[MoveSuggestion] = []

    # Get existing folders
    existing_folders = set()
    for note in notes:
        if note.folder:
            existing_folders.add(note.folder.split("/")[0])

    # Only look at root-level notes
    root_notes = [n for n in notes if not n.folder]

    for note in root_notes:
        if deep:
            suggestion = _classify_deep(config, note, existing_folders)
        else:
            suggestion = _classify_heuristic(note)

        if suggestion:
            suggestions.append(suggestion)

    return suggestions


def _classify_heuristic(note: Note) -> MoveSuggestion | None:
    body_lower = note.body.lower()
    title_lower = note.title.lower()
    combined = f"{title_lower} {body_lower}"

    for folder, keywords in FOLDER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                return MoveSuggestion(
                    note=note,
                    current_folder="(root)",
                    suggested_folder=folder,
                    reason=f"keyword match: '{keyword}'",
                )
    return None


def _classify_deep(config: Config, note: Note, folders: set[str]) -> MoveSuggestion | None:
    folders_str = ", ".join(sorted(folders))
    prompt = CLASSIFY_PROMPT.format(folders=folders_str)
    result = analyze_content(
        config,
        prompt,
        f"Title: {note.title}\n\nContent:\n{note.body[:1500]}",
    )
    result = result.strip().strip('"').strip("'")
    if result and result != "NONE" and result in folders:
        return MoveSuggestion(
            note=note,
            current_folder="(root)",
            suggested_folder=result,
            reason="classified by Claude",
        )
    return None


def preview_structure(suggestions: list[MoveSuggestion]) -> None:
    if not suggestions:
        console.print("[green]All notes are well-organized.[/green]")
        return

    table = Table(title=f"Structure Suggestions ({len(suggestions)})")
    table.add_column("Note", style="cyan")
    table.add_column("Current", style="dim")
    table.add_column("Suggested", style="yellow")
    table.add_column("Reason", style="dim")

    for s in suggestions:
        table.add_row(s.note.title, s.current_folder, s.suggested_folder, s.reason)

    console.print(table)


def apply_structure(config: Config, suggestions: list[MoveSuggestion]) -> int:
    count = 0
    for s in suggestions:
        src = Path(s.note.filename)
        dest = Path(s.suggested_folder) / s.note.filename
        vault.move_note(config, src, dest)
        count += 1
    return count
