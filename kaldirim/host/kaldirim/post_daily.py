"""Compose and post the day's numbers with the hourly chart. Dry run by default.

    python -m kaldirim.post_daily                # today
    python -m kaldirim.post_daily 2026-10-18     # a specific day

Schedule it nightly with cron, e.g.  5 22 * * *  cd /path/host && python -m kaldirim.post_daily
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import chart, config, db, stats


def compose(day: date, st: stats.DayStats, week: int, total: int, site_url: str) -> str:
    d = day.strftime("%d.%m.%Y")
    peak = stats.hour_label(st.peak_hour) if st.peak_hour is not None else "-"
    lines = [
        f"{d} · kaldırımdan geçen motosiklet: {st.total}",
        f"En yoğun saat: {peak}",
        f"Son 7 gün: {week} · Toplam: {total}",
        "Sadece sayı paylaşılır, görüntü paylaşılmaz. Kayıtlar resmi ihbar için saklanır.",
    ]
    if site_url:
        lines.append(site_url)
    return "\n".join(lines)


def main() -> None:
    cfg = config.load()
    tz = ZoneInfo(cfg.get("timezone", "Europe/Istanbul"))
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(tz).date()
    con = db.connect(cfg["data_dir"])
    st = stats.day_stats(con, day)
    week = sum(v for _, v in stats.daily_totals(con, day, 7))
    total = stats.running_total(con)
    p = cfg["post"]
    text = compose(day, st, week, total, p.get("site_url", ""))
    png = chart.hourly_png(st, Path(cfg["data_dir"], "site", f"hourly_{day.isoformat()}.png"),
                           f"Kaldırımdan geçen motosikletler · {day.strftime('%d.%m.%Y')}")

    print(text)
    print(f"chart: {png}")
    if p.get("dry_run", True):
        print("dry_run is true; nothing posted")
        return

    import tweepy
    k = p["x_api"]
    auth = tweepy.OAuth1UserHandler(k["consumer_key"], k["consumer_secret"], k["access_token"], k["access_token_secret"])
    media = tweepy.API(auth).media_upload(str(png))
    client = tweepy.Client(consumer_key=k["consumer_key"], consumer_secret=k["consumer_secret"],
                           access_token=k["access_token"], access_token_secret=k["access_token_secret"])
    r = client.create_tweet(text=text, media_ids=[media.media_id])
    print("posted:", r.data.get("id"))


if __name__ == "__main__":
    main()
