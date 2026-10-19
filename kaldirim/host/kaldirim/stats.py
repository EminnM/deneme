"""Aggregates over the events table. Everything the post and dashboard show comes from here."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class DayStats:
    day: str
    total: int
    hourly: list[int]            # 24 buckets
    peak_hour: int | None        # None when total == 0


def day_stats(con: sqlite3.Connection, day: date) -> DayStats:
    d = day.isoformat()
    hourly = [0] * 24
    for hour, n in con.execute("SELECT hour, COUNT(*) FROM events WHERE day=? GROUP BY hour", (d,)):
        hourly[int(hour)] = int(n)
    total = sum(hourly)
    peak = max(range(24), key=lambda h: hourly[h]) if total else None
    return DayStats(d, total, hourly, peak)


def daily_totals(con: sqlite3.Connection, end: date, days: int) -> list[tuple[str, int]]:
    """(day, count) for the `days` days ending at `end`, zero-filled, oldest first."""
    start = end - timedelta(days=days - 1)
    rows = dict(con.execute("SELECT day, COUNT(*) FROM events WHERE day BETWEEN ? AND ? GROUP BY day",
                            (start.isoformat(), end.isoformat())))
    return [((start + timedelta(days=i)).isoformat(), int(rows.get((start + timedelta(days=i)).isoformat(), 0)))
            for i in range(days)]


def running_total(con: sqlite3.Connection) -> int:
    return int(con.execute("SELECT COUNT(*) FROM events").fetchone()[0])


def first_day(con: sqlite3.Connection) -> str | None:
    r = con.execute("SELECT MIN(day) FROM events").fetchone()[0]
    return r


def hour_label(h: int) -> str:
    return f"{h:02d}:00-{(h + 1) % 24:02d}:00"


def before_after(con: sqlite3.Connection, campaign_start: date, until: date) -> tuple[float | None, float | None, int, int]:
    """Average events per full day before the campaign and since it.

    Returns (avg_before, avg_since, days_before, days_since). The day the camera
    started is found from the data; a day with no events still counts as a day.
    """
    first = first_day(con)
    if not first:
        return None, None, 0, 0
    f = date.fromisoformat(first)
    before_days = (campaign_start - f).days
    since_days = (until - campaign_start).days + 1
    avg_b = avg_s = None
    if before_days > 0:
        n = con.execute("SELECT COUNT(*) FROM events WHERE day < ?", (campaign_start.isoformat(),)).fetchone()[0]
        avg_b = n / before_days
    if since_days > 0:
        n = con.execute("SELECT COUNT(*) FROM events WHERE day >= ? AND day <= ?",
                        (campaign_start.isoformat(), until.isoformat())).fetchone()[0]
        avg_s = n / since_days
    return avg_b, avg_s, max(0, before_days), max(0, since_days)
