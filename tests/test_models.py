from obsidian_journal.models import Frontmatter, Note, ReflectionType


def test_reflection_type_values():
    assert ReflectionType.END_OF_DAY.value == "end-of-day"
    assert ReflectionType.MEETING.value == "meeting"
    assert ReflectionType.READING.value == "reading"
    assert ReflectionType.FREE_FORM.value == "free-form"


def test_all_reflection_types_have_opening_questions():
    from obsidian_journal.journal.prompts import OPENING_QUESTIONS

    for rt in ReflectionType:
        assert rt in OPENING_QUESTIONS, f"Missing opening question for {rt.name}"


def test_frontmatter_to_dict_minimal():
    f = Frontmatter()
    assert f.to_dict() == {}


def test_frontmatter_to_dict_full():
    f = Frontmatter(
        date="2026-01-15",
        type="journal",
        tags=["daily", "work"],
        related=["Note A"],
        extra={"custom": "value"},
    )
    d = f.to_dict()
    assert d["date"] == "2026-01-15"
    assert d["type"] == "journal"
    assert d["tags"] == ["daily", "work"]
    assert d["related"] == ["Note A"]
    assert d["custom"] == "value"


def test_note_filename():
    n = Note(title="2026-01-15 My Reflection", body="content")
    assert n.filename == "2026-01-15 My Reflection.md"
