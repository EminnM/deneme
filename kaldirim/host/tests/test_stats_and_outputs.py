import sqlite3
from datetime import date
from pathlib import Path

from kaldirim import chart, db, stats
from kaldirim.dashboard import bar_svg
from kaldirim.post_daily import compose


def seeded(tmp_path: Path):
    con = db.connect(str(tmp_path))
    for h, n in ((8, 3), (12, 10), (19, 25), (20, 12)):
        for i in range(n):
            db.insert_event(con, f"2026-10-18T{h:02d}:{i:02d}:00+03:00", "2026-10-18", h, i, 0.8, 100, 200, None)
    db.insert_event(con, "2026-10-17T09:00:00+03:00", "2026-10-17", 9, 1, 0.9, 1, 1, None)
    return con


def test_day_stats(tmp_path):
    con = seeded(tmp_path)
    st = stats.day_stats(con, date(2026, 10, 18))
    assert st.total == 50
    assert st.peak_hour == 19
    assert st.hourly[12] == 10
    empty = stats.day_stats(con, date(2026, 1, 1))
    assert empty.total == 0 and empty.peak_hour is None


def test_daily_totals_zero_filled(tmp_path):
    con = seeded(tmp_path)
    rows = stats.daily_totals(con, date(2026, 10, 18), 3)
    assert rows == [("2026-10-16", 0), ("2026-10-17", 1), ("2026-10-18", 50)]
    assert stats.running_total(con) == 51


def test_compose_text():
    st = stats.DayStats("2026-10-18", 50, [0] * 24, 19)
    t = compose(date(2026, 10, 18), st, 51, 51, "https://example.org")
    assert "18.10.2026" in t and "50" in t and "19:00-20:00" in t and t.endswith("https://example.org")


def test_chart_png(tmp_path):
    con = seeded(tmp_path)
    st = stats.day_stats(con, date(2026, 10, 18))
    out = chart.hourly_png(st, tmp_path / "h.png", "test")
    assert out.exists() and out.stat().st_size > 5000


def test_bar_svg_has_one_rect_per_value():
    svg = bar_svg(["a", "b", "c"], [1, 0, 3], "x")
    assert svg.count("<rect") == 3 and "<title>c: 3 x</title>" in svg


def test_before_after(tmp_path):
    con = seeded(tmp_path)   # 1 event on 10-17, 50 on 10-18
    avg_b, avg_s, nb, ns = stats.before_after(con, date(2026, 10, 18), date(2026, 10, 18))
    assert (nb, ns) == (1, 1) and avg_b == 1 and avg_s == 50
    avg_b, avg_s, nb, ns = stats.before_after(con, date(2026, 10, 17), date(2026, 10, 18))
    assert avg_b is None and nb == 0 and avg_s == 25.5 and ns == 2


def test_intent_url_and_multipart(tmp_path):
    from kaldirim.deliver import _multipart, intent_url
    u = intent_url("bugün: 50\nhttps://e.org")
    assert u.startswith("https://x.com/intent/post?text=") and "50" in u and "%0A" in u
    f = tmp_path / "c.png"; f.write_bytes(b"\x89PNG....")
    body, ctype = _multipart({"chat_id": "1", "caption": "x"}, "photo", f)
    assert ctype.startswith("multipart/form-data; boundary=") and b'name="photo"; filename="c.png"' in body
    assert body.endswith(b"--\r\n") and b"\x89PNG" in body
