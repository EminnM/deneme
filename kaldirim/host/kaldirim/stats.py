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
