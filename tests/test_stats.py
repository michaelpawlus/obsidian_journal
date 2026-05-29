from datetime import date

from obsidian_journal.models import Frontmatter, Note
from obsidian_journal.stats import compute_stats


def _note(date_str="", type_="", tags=None, folder="Journal", modified_at=""):
    return Note(
        title=f"note-{date_str or modified_at}",
        body="",
        frontmatter=Frontmatter(date=date_str, type=type_, tags=tags or []),
        folder=folder,
        modified_at=modified_at,
    )


def test_empty_input():
    result = compute_stats([])
    assert result["total_notes"] == 0
    assert result["by_type"] == {}
    assert result["by_tag"] == {}
    assert result["by_folder"] == {}
    assert result["timeline"] == []
    assert result["active_days"] == 0
    assert result["current_streak_days"] == 0
    assert result["longest_streak_days"] == 0
    assert result["first_note_date"] is None
    assert result["last_note_date"] is None


def test_type_tally():
    notes = [
        _note("2026-01-01", "free-form"),
        _note("2026-01-02", "free-form"),
        _note("2026-01-03", "gratitude"),
    ]
    result = compute_stats(notes)
    assert result["total_notes"] == 3
    assert result["by_type"] == {"free-form": 2, "gratitude": 1}


def test_untyped_falls_back():
    result = compute_stats([_note("2026-01-01")])
    assert result["by_type"] == {"untyped": 1}


def test_tag_tally_explodes_lists():
    notes = [
        _note("2026-01-01", tags=["work", "running"]),
        _note("2026-01-02", tags=["work"]),
        _note("2026-01-03", tags=["running", "reading"]),
    ]
    result = compute_stats(notes)
    assert result["by_tag"] == {"running": 2, "work": 2, "reading": 1}


def test_folder_tally():
    notes = [
        _note("2026-01-01", folder="Journal"),
        _note("2026-01-02", folder="Journal"),
        _note("2026-01-03", folder="Project Ideas"),
    ]
    result = compute_stats(notes)
    assert result["by_folder"] == {"Journal": 2, "Project Ideas": 1}


def test_root_folder_label():
    result = compute_stats([_note("2026-01-01", folder="")])
    assert result["by_folder"] == {"(root)": 1}


def test_week_bucketing():
    # 2026-01-05 and 2026-01-06 are both ISO week 2026-W02.
    # 2026-01-12 is 2026-W03.
    notes = [
        _note("2026-01-05"),
        _note("2026-01-06"),
        _note("2026-01-12"),
    ]
    result = compute_stats(notes, by="week")
    assert result["timeline"] == [
        {"bucket": "2026-W02", "count": 2},
        {"bucket": "2026-W03", "count": 1},
    ]


def test_month_bucketing():
    notes = [
        _note("2026-01-05"),
        _note("2026-01-20"),
        _note("2026-02-03"),
    ]
    result = compute_stats(notes, by="month")
    assert result["timeline"] == [
        {"bucket": "2026-01", "count": 2},
        {"bucket": "2026-02", "count": 1},
    ]


def test_day_bucketing():
    notes = [_note("2026-01-05"), _note("2026-01-05"), _note("2026-01-06")]
    result = compute_stats(notes, by="day")
    assert result["timeline"] == [
        {"bucket": "2026-01-05", "count": 2},
        {"bucket": "2026-01-06", "count": 1},
    ]


def test_modified_at_fallback_for_date():
    notes = [_note("", modified_at="2026-03-09T12:00:00+00:00")]
    result = compute_stats(notes, by="day")
    assert result["first_note_date"] == "2026-03-09"
    assert result["timeline"] == [{"bucket": "2026-03-09", "count": 1}]


def test_streak_current_ending_today():
    notes = [
        _note("2026-05-25"),
        _note("2026-05-26"),
        _note("2026-05-27"),
        _note("2026-05-28"),
    ]
    result = compute_stats(notes, today=date(2026, 5, 28))
    assert result["current_streak_days"] == 4
    assert result["longest_streak_days"] == 4
    assert result["active_days"] == 4


def test_streak_broken_by_gap():
    # A run of 3, a gap, then a run of 2 ending today.
    notes = [
        _note("2026-05-10"),
        _note("2026-05-11"),
        _note("2026-05-12"),
        _note("2026-05-27"),
        _note("2026-05-28"),
    ]
    result = compute_stats(notes, today=date(2026, 5, 28))
    assert result["longest_streak_days"] == 3
    assert result["current_streak_days"] == 2


def test_streak_not_current_when_stale():
    notes = [_note("2026-05-01"), _note("2026-05-02")]
    result = compute_stats(notes, today=date(2026, 5, 28))
    assert result["current_streak_days"] == 0
    assert result["longest_streak_days"] == 2


def test_streak_counts_yesterday_as_current():
    notes = [_note("2026-05-26"), _note("2026-05-27")]
    result = compute_stats(notes, today=date(2026, 5, 28))
    assert result["current_streak_days"] == 2


def test_distinct_days_dedup_streak():
    # Two notes on the same day count as one active day.
    notes = [_note("2026-05-28"), _note("2026-05-28")]
    result = compute_stats(notes, today=date(2026, 5, 28))
    assert result["active_days"] == 1
    assert result["current_streak_days"] == 1


def test_window_echoes_filter_args():
    notes = [_note("2026-04-05"), _note("2026-04-10")]
    result = compute_stats(notes, since="2026-04-01", until="2026-05-28")
    assert result["window"] == {"since": "2026-04-01", "until": "2026-05-28"}
    # first/last note dates derive from actual notes, not the window.
    assert result["first_note_date"] == "2026-04-05"
    assert result["last_note_date"] == "2026-04-10"


def test_window_defaults_none():
    result = compute_stats([_note("2026-04-05")])
    assert result["window"] == {"since": None, "until": None}
