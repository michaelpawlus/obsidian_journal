from __future__ import annotations

import re
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from obsidian_journal.config import Config
from obsidian_journal.models import Note
from obsidian_journal.organize.analyze import analyze_content
from obsidian_journal import vault

console = Console()

# Match existing wikilinks to avoid double-linking
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

DEEP_LINK_PROMPT = """\
You are an Obsidian vault organizer. Given a note's content and a list of other note \
titles in the vault, suggest which titles should be linked as [[wikilinks]] based on \
semantic relevance — not just exact text matches.

Return ONLY a JSON array of title strings that should be linked. Example: ["Title A", "Title B"]
If no links are warranted, return [].
"""


@dataclass
class LinkSuggestion:
    note: Note
    title_to_link: str
    context: str  # The line where the mention appears


def scan_links(config: Config, deep: bool = False) -> list[LinkSuggestion]:
    notes = vault.list_notes(config)
    all_titles = vault.get_all_note_titles(config)
    suggestions: list[LinkSuggestion] = []

    for note in notes:
        existing_links = set(WIKILINK_RE.findall(note.body))

        # Pass 1: exact title mentions not already linked
        for title in all_titles:
            if title == note.title:
                continue
            if title in existing_links:
                continue
            if len(title) < 3:
                continue
            # Look for the title as a whole word in the body
            pattern = re.compile(r"\b" + re.escape(title) + r"\b", re.IGNORECASE)
            match = pattern.search(note.body)
            if match:
                # Get the line for context
                line_start = note.body.rfind("\n", 0, match.start()) + 1
                line_end = note.body.find("\n", match.end())
                if line_end == -1:
                    line_end = len(note.body)
                context_line = note.body[line_start:line_end].strip()
                suggestions.append(
                    LinkSuggestion(
                        note=note, title_to_link=title, context=context_line
                    )
                )

        # Pass 2: deep semantic analysis via Claude
        if deep and note.body.strip():
            try:
                titles_str = "\n".join(
                    t for t in all_titles if t != note.title and t not in existing_links
                )
                result = analyze_content(
                    config,
                    DEEP_LINK_PROMPT,
                    f"Note title: {note.title}\n\nNote content:\n{note.body}\n\n"
                    f"Available titles:\n{titles_str}",
                )
                # Parse JSON array from response
                import json

                try:
                    deep_titles = json.loads(result)
                    if isinstance(deep_titles, list):
                        already_suggested = {s.title_to_link for s in suggestions if s.note.title == note.title}
                        for dt in deep_titles:
                            if dt in all_titles and dt not in already_suggested and dt not in existing_links:
                                suggestions.append(
                                    LinkSuggestion(
                                        note=note,
                                        title_to_link=dt,
                                        context="(semantic match via Claude)",
                                    )
                                )
                except json.JSONDecodeError:
                    pass
            except Exception:
                pass

    return suggestions


def preview_links(suggestions: list[LinkSuggestion]) -> None:
    if not suggestions:
        console.print("[green]No new wikilinks to suggest.[/green]")
        return

    table = Table(title=f"Wikilink Suggestions ({len(suggestions)})")
    table.add_column("Note", style="cyan")
    table.add_column("Link To", style="yellow")
    table.add_column("Context", style="dim", max_width=60)

    for s in suggestions:
        table.add_row(s.note.title, f"[[{s.title_to_link}]]", s.context)

    console.print(table)


def apply_links(config: Config, suggestions: list[LinkSuggestion]) -> int:
    # Group suggestions by note
    by_note: dict[str, list[LinkSuggestion]] = {}
    for s in suggestions:
        key = f"{s.note.folder}/{s.note.title}" if s.note.folder else s.note.title
        by_note.setdefault(key, []).append(s)

    count = 0
    for _, note_suggestions in by_note.items():
        note = note_suggestions[0].note
        body = note.body
        for s in note_suggestions:
            if s.context.startswith("(semantic"):
                # For semantic matches, append a related links section
                if "## Related" not in body:
                    body += "\n\n## Related\n"
                body += f"- [[{s.title_to_link}]]\n"
            else:
                # Replace first exact match with wikilink
                pattern = re.compile(r"\b" + re.escape(s.title_to_link) + r"\b")
                body = pattern.sub(f"[[{s.title_to_link}]]", body, count=1)
            count += 1
        note.body = body
        vault.write_note(config, note)

    return count
