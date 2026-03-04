from obsidian_journal.models import Frontmatter, Note, ReflectionType, WeatherInfo


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


def test_note_to_dict():
    n = Note(
        title="My Note",
        body="Hello",
        frontmatter=Frontmatter(date="2026-01-15", tags=["daily"]),
        folder="Journal",
    )
    d = n.to_dict()
    assert d["title"] == "My Note"
    assert d["folder"] == "Journal"
    assert d["filename"] == "My Note.md"
    assert d["frontmatter"]["date"] == "2026-01-15"
    assert d["body"] == "Hello"


def test_note_to_dict_empty():
    n = Note(title="Empty", body="")
    d = n.to_dict()
    assert d["title"] == "Empty"
    assert d["frontmatter"] == {}


def test_weather_info_to_dict():
    w = WeatherInfo(
        temperature_high_f=75.0,
        temperature_low_f=55.0,
        condition="Sunny",
        precipitation_chance=10,
        wind_speed_mph=5.0,
        sunrise="6:30 AM",
        sunset="7:45 PM",
        best_outdoor_window="10 AM - 2 PM",
        summary="Clear skies all day",
    )
    d = w.to_dict()
    assert d["temperature_high_f"] == 75.0
    assert d["temperature_low_f"] == 55.0
    assert d["condition"] == "Sunny"
    assert d["precipitation_chance"] == 10
    assert d["wind_speed_mph"] == 5.0
    assert d["sunrise"] == "6:30 AM"
    assert d["sunset"] == "7:45 PM"
    assert d["best_outdoor_window"] == "10 AM - 2 PM"
    assert d["summary"] == "Clear skies all day"
