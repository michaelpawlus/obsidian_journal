from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from obsidian_journal.config import Config
from obsidian_journal.models import ReflectionType
from obsidian_journal.output import emit_json, emit_error

app = typer.Typer(name="oj", help="Obsidian Journal — agentic capture & vault organizer")
organize_app = typer.Typer(help="Organize your Obsidian vault")
config_app = typer.Typer(help="View and set configuration")
app.add_typer(organize_app, name="organize")
app.add_typer(config_app, name="config")

console = Console(stderr=True)

json_mode: bool = False


@app.callback()
def main(
    json: bool = typer.Option(False, "--json", help="Emit JSON output for agent consumption"),
) -> None:
    global json_mode
    json_mode = json


def say(*args, **kwargs) -> None:
    """Print to stderr, but suppressed entirely under --json."""
    if json_mode:
        return
    console.print(*args, **kwargs)


@app.command()
def journal(
    type: ReflectionType | None = typer.Option(
        None, "--type", "-t", help="Reflection type"
    ),
    quick: str | None = typer.Option(
        None, "--quick", "-q", help="Quick capture — skip conversation"
    ),
) -> None:
    """Start an agentic journal capture session."""
    # In --json mode, --quick is required (no interactive path).
    if json_mode and quick is None:
        emit_error("--quick is required when using --json", 2)

    cfg = Config.load()

    # Type picker if not provided (default to FREE_FORM for quick capture)
    if type is None and quick is not None:
        type = ReflectionType.FREE_FORM
    elif type is None:
        console.print("\n[bold]Choose a reflection type:[/bold]\n")
        for i, rt in enumerate(ReflectionType, 1):
            console.print(f"  {i}. {rt.value}")
        console.print()
        choice = typer.prompt("Selection", type=int)
        type = list(ReflectionType)[choice - 1]

    say(f"\n[bold green]Starting {type.value} reflection...[/bold green]")

    from obsidian_journal.journal.capture import run_conversation
    from obsidian_journal.journal.synthesize import synthesize_note
    from obsidian_journal import vault
    from obsidian_journal.models import ConversationMessage

    # Run conversation or use quick capture
    if quick is not None:
        messages = [ConversationMessage(role="user", content=quick)]
    else:
        messages = run_conversation(cfg, type)

    if not any(m.role == "user" for m in messages):
        if json_mode:
            emit_error("No input captured", 2)
        console.print("[yellow]No input captured. Exiting.[/yellow]")
        raise typer.Exit()

    # Synthesize note
    say("\n[dim]Synthesizing your reflection...[/dim]\n")
    existing_titles = vault.get_all_note_titles(cfg)
    note = synthesize_note(cfg, messages, type, existing_titles)

    if json_mode:
        full_path = vault.write_note(cfg, note)
        rel_path = str(full_path.relative_to(cfg.vault_path))
        emit_json({
            "path": rel_path,
            "absolute_path": str(full_path),
            "title": note.title,
            "tags": list(note.frontmatter.tags),
            "frontmatter": note.frontmatter.to_dict(),
            "related": list(note.frontmatter.related),
            "folder": note.folder,
            "body": note.body,
        })
        raise typer.Exit()

    # Preview
    console.print(f"[bold]Title:[/bold] {note.title}")
    console.print(f"[bold]Folder:[/bold] {note.folder}/")
    console.print(f"[bold]Tags:[/bold] {', '.join(note.frontmatter.tags)}")
    if note.frontmatter.related:
        console.print(f"[bold]Related:[/bold] {', '.join(note.frontmatter.related)}")
    console.print()
    console.print(Markdown(note.body))
    console.print()

    # Confirm save
    if typer.confirm("Save this note to your vault?", default=True):
        path = vault.write_note(cfg, note)
        console.print(f"\n[bold green]Saved:[/bold green] {path}")
    else:
        console.print("[yellow]Note discarded.[/yellow]")


@app.command()
def plan(
    quick: str | None = typer.Option(
        None, "--quick", "-q", help="Quick plan — list tasks, skip conversation"
    ),
) -> None:
    """Create a structured daily plan for today."""
    from datetime import date

    if json_mode and quick is None:
        emit_error("--quick is required when using --json", 2)

    cfg = Config.load()
    today = date.today().isoformat()
    say(f"\n[bold green]Planning your day: {today}[/bold green]")

    # Fetch weather (graceful failure)
    weather = None
    if cfg.location_lat is not None and cfg.location_lon is not None:
        from obsidian_journal.plan.weather import fetch_weather

        say("[dim]Checking weather...[/dim]")
        weather = fetch_weather(cfg.location_lat, cfg.location_lon)
        if weather:
            say(f"[dim]Weather: {weather.summary}[/dim]")
        else:
            say("[dim]Could not fetch weather — continuing without it.[/dim]")
    else:
        say(
            "[dim]No location set — skipping weather. "
            "Set OJ_LOCATION_LAT and OJ_LOCATION_LON for weather-aware planning.[/dim]"
        )

    from obsidian_journal.plan.capture import run_plan_conversation
    from obsidian_journal.plan.synthesize import synthesize_plan
    from obsidian_journal import vault
    from obsidian_journal.models import ConversationMessage

    # Check for existing daily note content
    existing_note = vault.read_daily_note(cfg, today)
    existing_content = existing_note.body if existing_note else None

    # Run conversation or use quick capture
    if quick is not None:
        messages = [ConversationMessage(role="user", content=quick)]
    else:
        messages = run_plan_conversation(cfg, weather, existing_content)

    if not any(m.role == "user" for m in messages):
        if json_mode:
            emit_error("No input captured", 2)
        console.print("[yellow]No input captured. Exiting.[/yellow]")
        raise typer.Exit()

    # Synthesize plan
    say("\n[dim]Building your daily plan...[/dim]\n")
    plan_markdown = synthesize_plan(cfg, messages, weather, today)

    if json_mode:
        full_path = vault.write_daily_plan(cfg, today, plan_markdown)
        rel_path = str(full_path.relative_to(cfg.vault_path))
        from obsidian_journal.plan.parse import parse_blocks

        result: dict = {
            "path": rel_path,
            "absolute_path": str(full_path),
            "date": today,
            "frontmatter": {
                "date": today,
                "type": "daily-note",
                "tags": ["daily"],
            },
            "blocks": parse_blocks(plan_markdown),
            "markdown": plan_markdown,
            "weather": weather.to_dict() if weather else None,
        }
        emit_json(result)
        raise typer.Exit()

    # Preview
    console.print(Markdown(plan_markdown))
    console.print()

    # Confirm save
    if typer.confirm("Save this plan to your daily note?", default=True):
        path = vault.write_daily_plan(cfg, today, plan_markdown)
        console.print(f"\n[bold green]Saved:[/bold green] {path}")
    else:
        console.print("[yellow]Plan discarded.[/yellow]")


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


@app.command()
def spec(
    quick: str | None = typer.Option(
        None, "--quick", "-q", help="Brief / problem statement to expand into a spec"
    ),
    title: str | None = typer.Option(
        None, "--title", help="Override the auto-generated title"
    ),
    complexity: str | None = typer.Option(
        None,
        "--complexity",
        help="Complexity tier (S, M, L, week, multi-week)",
    ),
    priority: str | None = typer.Option(
        None,
        "--priority",
        help="Priority (low, medium, high)",
    ),
    related: str | None = typer.Option(
        None, "--related", help="Comma-separated list of related note titles"
    ),
    tag: str | None = typer.Option(
        None, "--tag", help="Comma-separated extra tags (added to baseline tags)"
    ),
    source: str | None = typer.Option(
        None, "--source", help="Provenance — who or what asked for this spec"
    ),
    status: str | None = typer.Option(
        None, "--status", help="Spec status (default: planning)"
    ),
    folder: str | None = typer.Option(
        None, "--folder", help="Override target folder (default: 'Project Ideas')"
    ),
) -> None:
    """Synthesize and write a project / feature spec note."""
    if json_mode and quick is None:
        emit_error("--quick is required when using --json", 2)

    cfg = Config.load()

    brief = quick
    if brief is None:
        console.print("\n[bold]Describe the spec idea[/bold] (one or two paragraphs):")
        brief = typer.prompt("Brief")
        if not brief.strip():
            console.print("[yellow]No brief provided. Exiting.[/yellow]")
            raise typer.Exit()

    if complexity is None:
        complexity = "M" if json_mode else typer.prompt(
            "Complexity (S/M/L/week/multi-week)", default="M"
        )
    if priority is None:
        priority = "medium" if json_mode else typer.prompt(
            "Priority (low/medium/high)", default="medium"
        )
    if status is None:
        status = "planning"

    if source is None:
        source = " ".join(sys.argv)

    target_folder = folder or "Project Ideas"

    say(f"\n[bold green]Drafting spec...[/bold green]")

    from obsidian_journal.spec.synthesize import synthesize_spec, slug_for_title
    from obsidian_journal import vault

    existing_titles = vault.get_all_note_titles(cfg)
    spec_note = synthesize_spec(
        cfg,
        brief,
        title_override=title,
        complexity=complexity,
        priority=priority,
        status=status,
        source=source,
        related=_split_csv(related),
        extra_tags=_split_csv(tag),
        folder=target_folder,
        existing_titles=existing_titles,
    )

    slug = slug_for_title(spec_note.title)

    if json_mode:
        full_path = vault.write_spec(cfg, spec_note, slug)
        rel_path = str(full_path.relative_to(cfg.vault_path))
        emit_json({
            "path": rel_path,
            "absolute_path": str(full_path),
            "title": spec_note.title,
            "folder": spec_note.folder,
            "frontmatter": spec_note.frontmatter.to_dict(),
            "body": spec_note.body,
        })
        raise typer.Exit()

    # Preview
    console.print(f"[bold]Title:[/bold] {spec_note.title}")
    console.print(f"[bold]Folder:[/bold] {spec_note.folder}/")
    console.print(f"[bold]Slug:[/bold] {slug}.md")
    console.print(f"[bold]Tags:[/bold] {', '.join(spec_note.frontmatter.tags)}")
    console.print(
        f"[bold]Status:[/bold] {status}  "
        f"[bold]Complexity:[/bold] {complexity}  "
        f"[bold]Priority:[/bold] {priority}"
    )
    if spec_note.frontmatter.related:
        console.print(f"[bold]Related:[/bold] {', '.join(spec_note.frontmatter.related)}")
    console.print()
    console.print(Markdown(spec_note.body))
    console.print()

    if typer.confirm("Save this spec to your vault?", default=True):
        path = vault.write_spec(cfg, spec_note, slug)
        console.print(f"\n[bold green]Saved:[/bold green] {path}")
    else:
        console.print("[yellow]Spec discarded.[/yellow]")


@app.command("list")
def list_notes(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of notes to show"),
    folder: str = typer.Option("Journal", "--folder", "-f", help="Folder to list"),
) -> None:
    """List recent journal notes."""
    cfg = Config.load()
    from obsidian_journal import vault

    notes = vault.list_journal_notes(cfg, folder=folder, limit=limit)

    if json_mode:
        emit_json({"folder": folder, "count": len(notes), "items": [n.to_summary_dict() for n in notes]})
        raise typer.Exit()

    if not notes:
        console.print(f"[yellow]No notes found in {folder}/[/yellow]")
        raise typer.Exit()

    console.print(f"\n[bold]Recent notes in {folder}/[/bold]\n")
    for note in notes:
        date = note.frontmatter.date or "no date"
        # Strip date prefix from title for display
        title = note.title
        if title.startswith(date):
            title = title[len(date):].lstrip(" -")
        tags = ", ".join(note.frontmatter.tags) if note.frontmatter.tags else ""
        tag_str = f"  [dim]({tags})[/dim]" if tags else ""
        console.print(f"  {date}  {title}{tag_str}")
    console.print()


@app.command()
def query(
    type: str | None = typer.Option(None, "--type", "-t", help="Filter by note type"),
    tags: str | None = typer.Option(None, "--tags", help="Filter by tags (comma-separated, OR logic)"),
    since: str | None = typer.Option(None, "--since", help="Filter notes from this date (YYYY-MM-DD)"),
    until: str | None = typer.Option(None, "--until", help="Filter notes until this date (YYYY-MM-DD)"),
    folder: str | None = typer.Option(None, "--folder", "-f", help="Filter by folder"),
    search: str | None = typer.Option(None, "--search", "-s", help="Text search in title and body"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Max number of results"),
) -> None:
    """Query notes with structured filters. Primary entry point for agent consumption."""
    cfg = Config.load()
    from obsidian_journal import vault

    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    notes = vault.search_notes(
        cfg,
        folder=folder,
        note_type=type,
        tags=tag_list,
        since=since,
        until=until,
        text=search,
        limit=limit,
    )

    if json_mode:
        emit_json({"count": len(notes), "items": [n.to_dict() for n in notes]})
        raise typer.Exit()

    if not notes:
        console.print("[yellow]No matching notes found.[/yellow]")
        raise typer.Exit(2)

    table = Table(title=f"Query results ({len(notes)} notes)")
    table.add_column("Date", style="dim")
    table.add_column("Title")
    table.add_column("Folder", style="dim")
    table.add_column("Type", style="dim")
    table.add_column("Tags", style="dim")
    for note in notes:
        table.add_row(
            note.frontmatter.date or "",
            note.title,
            note.folder,
            note.frontmatter.type,
            ", ".join(note.frontmatter.tags),
        )
    console.print(table)


@app.command()
def get(
    title: str = typer.Argument(help="Note title (exact match, then partial)"),
) -> None:
    """Retrieve a single note by title."""
    cfg = Config.load()
    from obsidian_journal import vault

    all_notes = vault.list_notes(cfg)

    # Exact match first
    match = next((n for n in all_notes if n.title == title), None)
    # Partial match fallback
    if match is None:
        title_lower = title.lower()
        match = next((n for n in all_notes if title_lower in n.title.lower()), None)

    if match is None:
        if json_mode:
            emit_error("Note not found", 2)
        console.print(f"[red]Note not found:[/red] {title}")
        raise typer.Exit(2)

    if json_mode:
        emit_json(match.to_dict())
        raise typer.Exit()

    console.print(f"\n[bold]Title:[/bold] {match.title}")
    console.print(f"[bold]Folder:[/bold] {match.folder or '(root)'}")
    if match.frontmatter.date:
        console.print(f"[bold]Date:[/bold] {match.frontmatter.date}")
    if match.frontmatter.type:
        console.print(f"[bold]Type:[/bold] {match.frontmatter.type}")
    if match.frontmatter.tags:
        console.print(f"[bold]Tags:[/bold] {', '.join(match.frontmatter.tags)}")
    console.print()
    console.print(Markdown(match.body))


@organize_app.command("links")
def organize_links(
    apply: bool = typer.Option(False, "--apply", help="Apply changes (default: preview only)"),
    deep: bool = typer.Option(False, "--deep", help="Use Claude for semantic link suggestions (costs API)"),
) -> None:
    """Scan notes for potential wikilinks between existing notes."""
    cfg = Config.load()
    from obsidian_journal.organize.links import scan_links, preview_links, apply_links

    console.print("[dim]Scanning for wikilink opportunities...[/dim]\n")
    suggestions = scan_links(cfg, deep=deep)

    if json_mode:
        data = [
            {"note": s.note.title, "link": s.title_to_link, "context": s.context}
            for s in suggestions
        ]
        if apply and suggestions:
            count = apply_links(cfg, suggestions)
            emit_json({"applied": count, "suggestions": data})
        else:
            emit_json({"applied": 0, "suggestions": data})
        raise typer.Exit()

    preview_links(suggestions)

    if apply and suggestions:
        count = apply_links(cfg, suggestions)
        console.print(f"\n[bold green]Applied {count} wikilinks.[/bold green]")
    elif suggestions:
        console.print("\n[dim]Run with --apply to make changes.[/dim]")


@organize_app.command("frontmatter")
def organize_frontmatter(
    apply: bool = typer.Option(False, "--apply", help="Apply changes (default: preview only)"),
) -> None:
    """Standardize YAML frontmatter across notes."""
    cfg = Config.load()
    from obsidian_journal.organize.frontmatter import (
        scan_frontmatter,
        preview_frontmatter,
        apply_frontmatter,
    )

    console.print("[dim]Scanning frontmatter...[/dim]\n")
    suggestions = scan_frontmatter(cfg)

    if json_mode:
        data = [
            {"note": note.title, "suggested_frontmatter": front.to_dict()}
            for note, front in suggestions
        ]
        if apply and suggestions:
            count = apply_frontmatter(cfg, suggestions)
            emit_json({"applied": count, "suggestions": data})
        else:
            emit_json({"applied": 0, "suggestions": data})
        raise typer.Exit()

    preview_frontmatter(suggestions)

    if apply and suggestions:
        count = apply_frontmatter(cfg, suggestions)
        console.print(f"\n[bold green]Updated {count} notes.[/bold green]")
    elif suggestions:
        console.print("\n[dim]Run with --apply to make changes.[/dim]")


@organize_app.command("structure")
def organize_structure(
    apply: bool = typer.Option(False, "--apply", help="Apply changes (default: preview only)"),
    deep: bool = typer.Option(False, "--deep", help="Use Claude for classification (costs API)"),
) -> None:
    """Suggest folder reorganization for root-level notes."""
    cfg = Config.load()
    from obsidian_journal.organize.structure import (
        scan_structure,
        preview_structure,
        apply_structure,
    )

    console.print("[dim]Analyzing vault structure...[/dim]\n")
    suggestions = scan_structure(cfg, deep=deep)

    if json_mode:
        data = [
            {
                "note": s.note.title,
                "current_folder": s.current_folder,
                "suggested_folder": s.suggested_folder,
                "reason": s.reason,
            }
            for s in suggestions
        ]
        if apply and suggestions:
            count = apply_structure(cfg, suggestions)
            emit_json({"applied": count, "suggestions": data})
        else:
            emit_json({"applied": 0, "suggestions": data})
        raise typer.Exit()

    preview_structure(suggestions)

    if apply and suggestions:
        count = apply_structure(cfg, suggestions)
        console.print(f"\n[bold green]Moved {count} notes.[/bold green]")
    elif suggestions:
        console.print("\n[dim]Run with --apply to make changes.[/dim]")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    try:
        cfg = Config.load()
    except ValueError as e:
        if json_mode:
            emit_error(str(e), 1)
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)

    if json_mode:
        emit_json({
            "vault_path": str(cfg.vault_path),
            "api_key": f"{'*' * 8}...{cfg.anthropic_api_key[-4:]}",
            "model": cfg.model,
            "max_rounds": cfg.max_rounds,
            "location_lat": cfg.location_lat,
            "location_lon": cfg.location_lon,
            "daily_notes_folder": cfg.daily_notes_folder,
        })
        raise typer.Exit()

    console.print(f"[bold]Vault path:[/bold]  {cfg.vault_path}")
    console.print(f"[bold]API key:[/bold]    {'*' * 8}...{cfg.anthropic_api_key[-4:]}")
    console.print(f"[bold]Model:[/bold]      {cfg.model}")
    console.print(f"[bold]Max rounds:[/bold] {cfg.max_rounds}")
    if cfg.location_lat is not None:
        console.print(f"[bold]Location:[/bold]   {cfg.location_lat}, {cfg.location_lon}")
    else:
        console.print("[bold]Location:[/bold]   (not set)")
    console.print(f"[bold]Daily folder:[/bold] {cfg.daily_notes_folder}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Config key (e.g. OBSIDIAN_VAULT_PATH)"),
    value: str = typer.Argument(help="Config value"),
) -> None:
    """Set a configuration value in .env file."""
    from pathlib import Path

    env_path = Path.cwd() / ".env"
    lines: list[str] = []
    found = False

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)

    if not found:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n")
    console.print(f"[green]Set {key} in .env[/green]")


if __name__ == "__main__":
    app()
