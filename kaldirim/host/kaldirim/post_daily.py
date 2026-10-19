"""Compose and post the day's numbers with the hourly chart. Dry run by default.

    python -m kaldirim.post_daily                # today
    python -m kaldirim.post_daily 2026-10-18     # a specific day

Schedule it nightly with cron, e.g.  5 22 * * *  cd /path/host && python -m kaldirim.post_daily

X API access is pay-per-use since February 2026: a developer account with a payment method,
then roughly a cent per post. Posts containing a link are billed much higher, so leave
post.site_url empty and put the dashboard link in the account bio instead.
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
    media_id = upload_media(k, png)
    client = tweepy.Client(consumer_key=k["consumer_key"], consumer_secret=k["consumer_secret"],
                           access_token=k["access_token"], access_token_secret=k["access_token_secret"])
    r = client.create_tweet(text=text, media_ids=[media_id])
    print("posted:", r.data.get("id"))


def upload_media(k: dict, png: Path) -> str:
    """Upload one image and return its media id.

    Tries the v2 endpoint first (POST /2/media/upload), which is what X runs now, and falls back
    to the v1.1 upload through tweepy if v2 is refused, since tweepy has no v2 upload helper yet.
    """
    from requests_oauthlib import OAuth1
    import requests
    auth = OAuth1(k["consumer_key"], k["consumer_secret"], k["access_token"], k["access_token_secret"])
    with png.open("rb") as f:
        r = requests.post("https://api.x.com/2/media/upload", auth=auth,
                          data={"media_category": "tweet_image", "media_type": "image/png"},
                          files={"media": (png.name, f, "image/png")}, timeout=60)
    if r.ok:
        return str(r.json()["data"]["id"])
    print(f"v2 media upload refused ({r.status_code}); trying v1.1")
    import tweepy
    api = tweepy.API(tweepy.OAuth1UserHandler(k["consumer_key"], k["consumer_secret"],
                                              k["access_token"], k["access_token_secret"]))
    return str(api.media_upload(str(png)).media_id)


if __name__ == "__main__":
    main()
