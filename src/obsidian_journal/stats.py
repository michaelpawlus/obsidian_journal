from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from itertools import pairwise
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from obsidian_journal.models import Note


def _note_date(note: Note) -> date | None:
    """Best-effort calendar date for a note.

    Prefer `frontmatter.date` (YYYY-MM-DD); fall back to the date portion of
    `modified_at` (ISO-8601) when the frontmatter date is empty or unparseable.
    Returns None when neither yields a valid date.
    """
    raw = (note.frontmatter.date or "").strip()
    if raw:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            pass
    if note.modified_at:
        try:
            return datetime.fromisoformat(note.modified_at).date()
        except ValueError:
            pass
    return None


def _bucket_key(d: date, by: str) -> str:
    if by == "day":
        return d.isoformat()
    if by == "month":
        return d.strftime("%Y-%m")
    # default: ISO week
    return d.strftime("%G-W%V")


def _streaks(active_dates: list[date], today: date) -> tuple[int, int]:
    """Return (current_streak_days, longest_streak_days) for sorted distinct dates."""
    if not active_dates:
        return 0, 0

    # Longest run of consecutive days.
    longest = 1
    run = 1
    for prev, cur in pairwise(active_dates):
        if (cur - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)

    # Current streak: consecutive days ending at the last active day, but only
    # "current" if that last day is today or yesterday.
    last = active_dates[-1]
    if (today - last).days > 1:
        current = 0
    else:
        current = 1
        idx = len(active_dates) - 1
        while idx > 0 and (active_dates[idx] - active_dates[idx - 1]).days == 1:
            current += 1
            idx -= 1

    return current, longest


def compute_stats(
    notes: list[Note],
    by: str = "week",
    today: date | None = None,
    since: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    """Aggregate journal activity over a collection of notes.

    Pure function — no vault I/O — so it is unit-testable in isolation. Callers
    are expected to have already applied window/folder/type/tag filters (via
    ``vault.search_notes``); this only tallies.

    Args:
        notes: notes to aggregate.
        by: timeline bucket granularity — ``day``, ``week`` (ISO week), or ``month``.
        today: reference date for the current-streak calculation (defaults to
            the system date; injectable for tests).
        since: requested window start (echoed into ``window.since``; defaults
            all-time → None).
        until: requested window end (echoed into ``window.until``).
    """
    if today is None:
        today = date.today()

    by_type: Counter[str] = Counter()
    by_tag: Counter[str] = Counter()
    by_folder: Counter[str] = Counter()
    timeline: Counter[str] = Counter()
    note_dates: list[date] = []

    for note in notes:
        ntype = note.frontmatter.type or "untyped"
        by_type[ntype] += 1
        by_folder[note.folder or "(root)"] += 1
        for tag in note.frontmatter.tags:
            by_tag[tag] += 1
        d = _note_date(note)
        if d is not None:
            note_dates.append(d)
            timeline[_bucket_key(d, by)] += 1

    active_dates = sorted(set(note_dates))
    current_streak, longest_streak = _streaks(active_dates, today)

    def _ordered(counter: Counter[str]) -> dict[str, int]:
        # Sort by count desc, then key asc for stable output.
        return {
            k: v
            for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        }

    return {
        "window": {"since": since, "until": until},
        "total_notes": len(notes),
        "by_type": _ordered(by_type),
        "by_tag": _ordered(by_tag),
        "by_folder": _ordered(by_folder),
        "timeline": [
            {"bucket": b, "count": timeline[b]} for b in sorted(timeline)
        ],
        "first_note_date": active_dates[0].isoformat() if active_dates else None,
        "last_note_date": active_dates[-1].isoformat() if active_dates else None,
        "active_days": len(active_dates),
        "current_streak_days": current_streak,
        "longest_streak_days": longest_streak,
    }
