from pathlib import Path

import pytest

from obsidian_journal.config import Config
from obsidian_journal.models import Frontmatter, Note
from obsidian_journal.vault import (
    list_notes,
    list_journal_notes,
    read_note,
    write_note,
    get_all_note_titles,
)


@pytest.fixture
def tmp_vault(tmp_path):
    """Create a temporary vault with a few notes."""
    # Root note
    (tmp_path / "Root Note.md").write_text(
        "---\ntags:\n  - test\n---\nHello world\n"
    )
    # Daily note
    daily = tmp_path / "Daily Notes"
    daily.mkdir()
    (daily / "2026-01-15.md").write_text("Today was good.\n")
    # .obsidian should be skipped
    obs = tmp_path / ".obsidian"
    obs.mkdir()
    (obs / "config.md").write_text("skip me")
    return tmp_path


@pytest.fixture
def config(tmp_vault):
    return Config(
        vault_path=tmp_vault,
        anthropic_api_key="test-key",
    )


def test_list_notes(config):
    notes = list_notes(config)
    titles = [n.title for n in notes]
    assert "Root Note" in titles
    assert "2026-01-15" in titles
    # .obsidian should be skipped
    assert "config" not in titles


def test_read_note(config):
    note = read_note(config, "Root Note.md")
    assert note is not None
    assert note.title == "Root Note"
    assert "test" in note.frontmatter.tags
    assert "Hello world" in note.body


def test_read_note_not_found(config):
    note = read_note(config, "Does Not Exist.md")
    assert note is None


def test_write_note(config):
    note = Note(
        title="New Note",
        body="Some content here.",
        frontmatter=Frontmatter(date="2026-02-26", tags=["new"]),
        folder="Journal",
    )
    path = write_note(config, note)
    assert path.exists()
    assert "Journal" in str(path)
    content = path.read_text()
    assert "Some content here." in content
    assert "date: '2026-02-26'" in content or "date: 2026-02-26" in content


def test_get_all_note_titles(config):
    titles = get_all_note_titles(config)
    assert "Root Note" in titles
    assert "2026-01-15" in titles
    assert "config" not in titles


@pytest.fixture
def vault_with_journal(tmp_path):
    """Create a vault with journal notes for list_journal_notes tests."""
    journal = tmp_path / "Journal"
    journal.mkdir()
    (journal / "2026-01-10 Morning thoughts.md").write_text(
        "---\ndate: '2026-01-10'\ntags:\n  - morning\n---\nContent A\n"
    )
    (journal / "2026-01-15 Project retro.md").write_text(
        "---\ndate: '2026-01-15'\ntags:\n  - work\n---\nContent B\n"
    )
    (journal / "2026-01-20 Evening reflection.md").write_text(
        "---\ndate: '2026-01-20'\ntags:\n  - evening\n---\nContent C\n"
    )
    return tmp_path


@pytest.fixture
def journal_config(vault_with_journal):
    return Config(vault_path=vault_with_journal, anthropic_api_key="test-key")


def test_list_journal_notes_reverse_order(journal_config):
    notes = list_journal_notes(journal_config)
    titles = [n.title for n in notes]
    assert titles == [
        "2026-01-20 Evening reflection",
        "2026-01-15 Project retro",
        "2026-01-10 Morning thoughts",
    ]


def test_list_journal_notes_limit(journal_config):
    notes = list_journal_notes(journal_config, limit=2)
    assert len(notes) == 2
    assert notes[0].title == "2026-01-20 Evening reflection"


def test_list_journal_notes_missing_folder(journal_config):
    notes = list_journal_notes(journal_config, folder="NonExistent")
    assert notes == []
