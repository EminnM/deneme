"""Copy one event's clip into data/exports with a sidecar note, ready to upload to the police app.

    python -m kaldirim.export_report 123
    python -m kaldirim.export_report 2026-10-18     # every event of that day

Triage before sending: pick the clear cases, not all hundred.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from . import config, db


def export(con, cfg: dict, event_id: int) -> Path | None:
    row = con.execute("SELECT id, ts, clip_path FROM events WHERE id=?", (event_id,)).fetchone()
    if not row or not row[2] or not Path(row[2]).exists():
        print(f"event {event_id}: no clip on disk")
        return None
    out_dir = Path(cfg["data_dir"], "exports")
    dst = out_dir / Path(row[2]).name
    shutil.copy2(row[2], dst)
    dst.with_suffix(".txt").write_text(
        f"Olay no: {row[0]}\nZaman: {row[1]}\nİhlal: Motosikletle kaldırımda seyir (2918 sayılı KTK)\n"
        f"Kaynak: sabit ev kamerası, kayıt yerelde tutulmaktadır.\n", encoding="utf-8")
    print(dst)
    return dst


def main() -> None:
    cfg = config.load()
    con = db.connect(cfg["data_dir"])
    arg = sys.argv[1]
    if "-" in arg:
        ids = [r[0] for r in con.execute("SELECT id FROM events WHERE day=? ORDER BY id", (arg,))]
    else:
        ids = [int(arg)]
    for i in ids:
        export(con, cfg, i)


if __name__ == "__main__":
    main()
