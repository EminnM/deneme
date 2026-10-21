from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,          -- ISO 8601 local time
    day TEXT NOT NULL,         -- YYYY-MM-DD local
    hour INTEGER NOT NULL,     -- 0..23 local
    track_id INTEGER,
    conf REAL,
    x INTEGER, y INTEGER,      -- ground point in the frame at count time
    clip_path TEXT,
    gate TEXT
);
CREATE INDEX IF NOT EXISTS events_day ON events(day);
"""


def connect(data_dir: str) -> sqlite3.Connection:
    con = sqlite3.connect(Path(data_dir, "events.sqlite"))
    con.executescript(SCHEMA)
    cols = {r[1] for r in con.execute("PRAGMA table_info(events)")}
    if "gate" not in cols:   # databases created before gates were named
        con.execute("ALTER TABLE events ADD COLUMN gate TEXT")
        con.commit()
    return con


def insert_event(con, ts, day, hour, track_id, conf, x, y, clip_path, gate=None) -> int:
    cur = con.execute(
        "INSERT INTO events (ts, day, hour, track_id, conf, x, y, clip_path, gate) VALUES (?,?,?,?,?,?,?,?,?)",
        (ts, day, hour, track_id, conf, x, y, clip_path, gate),
    )
    con.commit()
    return cur.lastrowid
