from pathlib import Path

import pytest

from obsidian_journal.config import Config
from obsidian_journal.models import Frontmatter, Note
from obsidian_journal.vault import list_notes, read_note, write_note, get_all_note_titles


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
