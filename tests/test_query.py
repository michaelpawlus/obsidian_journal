from pathlib import Path

import pytest

from obsidian_journal.config import Config
from obsidian_journal.models import Frontmatter, Note
from obsidian_journal.vault import search_notes


@pytest.fixture
def search_vault(tmp_path):
    """Create a vault with diverse notes for search testing."""
    journal = tmp_path / "Journal"
    journal.mkdir()
    meetings = tmp_path / "Meetings"
    meetings.mkdir()

    (journal / "2026-01-10 Morning thoughts.md").write_text(
        "---\ndate: '2026-01-10'\ntype: end-of-day\ntags:\n  - daily\n  - work\n---\nThinking about career goals.\n"
    )
    (journal / "2026-02-01 Project retro.md").write_text(
        "---\ndate: '2026-02-01'\ntype: end-of-project\ntags:\n  - work\n  - career\n---\nRetrospective on the data pipeline project.\n"
    )
    (journal / "2026-02-15 Free thoughts.md").write_text(
        "---\ndate: '2026-02-15'\ntype: free-form\ntags:\n  - personal\n---\nJust a free-form reflection.\n"
    )
    (meetings / "2026-02-10 Team sync.md").write_text(
        "---\ndate: '2026-02-10'\ntype: meeting\ntags:\n  - work\n  - career\n---\nDiscussed roadmap and hiring.\n"
    )
    return tmp_path


@pytest.fixture
def search_config(search_vault):
    return Config(vault_path=search_vault, anthropic_api_key="test-key")


def test_search_all(search_config):
    notes = search_notes(search_config)
    assert len(notes) == 4


def test_search_by_folder(search_config):
    notes = search_notes(search_config, folder="Meetings")
    assert len(notes) == 1
    assert notes[0].title == "2026-02-10 Team sync"


def test_search_by_type(search_config):
    notes = search_notes(search_config, note_type="meeting")
    assert len(notes) == 1
    assert notes[0].title == "2026-02-10 Team sync"


def test_search_by_tags(search_config):
    notes = search_notes(search_config, tags=["career"])
    assert len(notes) == 2
    titles = {n.title for n in notes}
    assert "2026-02-01 Project retro" in titles
    assert "2026-02-10 Team sync" in titles


def test_search_by_since(search_config):
    notes = search_notes(search_config, since="2026-02-01")
    assert len(notes) == 3
    for n in notes:
        assert n.frontmatter.date >= "2026-02-01"


def test_search_by_until(search_config):
    notes = search_notes(search_config, until="2026-01-31")
    assert len(notes) == 1
    assert notes[0].frontmatter.date == "2026-01-10"


def test_search_by_date_range(search_config):
    notes = search_notes(search_config, since="2026-02-01", until="2026-02-10")
    assert len(notes) == 2


def test_search_by_text(search_config):
    notes = search_notes(search_config, text="career")
    assert len(notes) == 1
    assert notes[0].title == "2026-01-10 Morning thoughts"


def test_search_text_in_title(search_config):
    notes = search_notes(search_config, text="Team sync")
    assert len(notes) == 1


def test_search_with_limit(search_config):
    notes = search_notes(search_config, limit=2)
    assert len(notes) == 2


def test_search_sorted_by_date_descending(search_config):
    notes = search_notes(search_config)
    dates = [n.frontmatter.date for n in notes]
    assert dates == sorted(dates, reverse=True)


def test_search_combined_filters(search_config):
    notes = search_notes(search_config, tags=["work"], since="2026-02-01")
    assert len(notes) == 2
    for n in notes:
        assert "work" in n.frontmatter.tags
        assert n.frontmatter.date >= "2026-02-01"


def test_search_no_results(search_config):
    notes = search_notes(search_config, note_type="podcast")
    assert notes == []


def test_note_to_dict():
    note = Note(
        title="Test Note",
        body="Some content",
        frontmatter=Frontmatter(date="2026-01-15", type="meeting", tags=["work"]),
        folder="Meetings",
    )
    d = note.to_dict()
    assert d["title"] == "Test Note"
    assert d["folder"] == "Meetings"
    assert d["filename"] == "Test Note.md"
    assert d["frontmatter"]["date"] == "2026-01-15"
    assert d["frontmatter"]["type"] == "meeting"
    assert d["body"] == "Some content"


def test_note_to_dict_minimal():
    note = Note(title="Minimal", body="")
    d = note.to_dict()
    assert d["title"] == "Minimal"
    assert d["folder"] == ""
    assert d["frontmatter"] == {}
    assert d["body"] == ""
