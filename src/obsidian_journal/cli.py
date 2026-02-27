from __future__ import annotations

import typer
from rich.console import Console
from rich.markdown import Markdown

from obsidian_journal.config import Config
from obsidian_journal.models import ReflectionType

app = typer.Typer(name="oj", help="Obsidian Journal — agentic capture & vault organizer")
organize_app = typer.Typer(help="Organize your Obsidian vault")
config_app = typer.Typer(help="View and set configuration")
app.add_typer(organize_app, name="organize")
app.add_typer(config_app, name="config")

console = Console()


@app.command()
def journal(
    type: ReflectionType | None = typer.Option(
        None, "--type", "-t", help="Reflection type"
    ),
) -> None:
    """Start an agentic journal capture session."""
    cfg = Config.load()

    # Type picker if not provided
    if type is None:
        console.print("\n[bold]Choose a reflection type:[/bold]\n")
        for i, rt in enumerate(ReflectionType, 1):
            console.print(f"  {i}. {rt.value}")
        console.print()
        choice = typer.prompt("Selection", type=int)
        type = list(ReflectionType)[choice - 1]

    console.print(f"\n[bold green]Starting {type.value} reflection...[/bold green]")

    from obsidian_journal.journal.capture import run_conversation
    from obsidian_journal.journal.synthesize import synthesize_note
    from obsidian_journal import vault

    # Run conversation
    messages = run_conversation(cfg, type)
    if not any(m.role == "user" for m in messages):
        console.print("[yellow]No input captured. Exiting.[/yellow]")
        raise typer.Exit()

    # Synthesize note
    console.print("\n[dim]Synthesizing your reflection...[/dim]\n")
    existing_titles = vault.get_all_note_titles(cfg)
    note = synthesize_note(cfg, messages, type, existing_titles)

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
        console.print(f"[bold]Vault path:[/bold]  {cfg.vault_path}")
        console.print(f"[bold]API key:[/bold]    {'*' * 8}...{cfg.anthropic_api_key[-4:]}")
        console.print(f"[bold]Model:[/bold]      {cfg.model}")
        console.print(f"[bold]Max rounds:[/bold] {cfg.max_rounds}")
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)


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
