"""Static dashboard: data/site/index.html with the last 30 days, built from the database.

    python -m kaldirim.dashboard

Host the site folder anywhere static (GitHub Pages, Netlify). It contains numbers only.
"""
from __future__ import annotations

import html
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, db, stats

CSS = """
:root{color-scheme:light;--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--grid:#e4e3df;--s1:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#333331;--s1:#3987e5}}
:root[data-theme=dark]{color-scheme:dark;--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#333331;--s1:#3987e5}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}
main{max-width:880px;margin:0 auto;padding:24px 16px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--ink2);margin:0 0 24px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:28px}
.tile{border:1px solid var(--grid);border-radius:10px;padding:14px 16px}
.tile .v{font-size:40px;font-weight:700;line-height:1.1}
.tile .l{color:var(--ink2);font-size:13px}
h2{font-size:16px;margin:28px 0 8px}
svg{width:100%;height:auto;display:block}
rect.bar{fill:var(--s1)}
rect.bar:hover{opacity:.8}
text{fill:var(--ink2);font-size:11px}
line.grid{stroke:var(--grid)}
table{border-collapse:collapse;width:100%;font-size:14px}
td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid)}
th{color:var(--ink2);font-weight:500}
td.n{text-align:right;font-variant-numeric:tabular-nums}
details{margin-top:12px}
.method{color:var(--ink2);font-size:14px;margin-top:32px}
"""


def bar_svg(labels: list[str], values: list[int], unit: str, step_labels: int = 1) -> str:
    """Single-series bar chart as inline SVG with a hover title per bar."""
    w, h, pad_l, pad_b, pad_t = 860, 220, 30, 24, 10
    n = len(values)
    vmax = max(values) if values and max(values) > 0 else 1
    slot = (w - pad_l) / n
    bw = max(2, slot - 2)
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(unit)}">']
    for frac in (0.5, 1.0):
        y = pad_t + (h - pad_t - pad_b) * (1 - frac)
        parts.append(f'<line class="grid" x1="{pad_l}" x2="{w}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text x="0" y="{y + 4:.1f}">{int(vmax * frac)}</text>')
    base = h - pad_b
    for i, (lab, v) in enumerate(zip(labels, values)):
        bh = (h - pad_t - pad_b) * v / vmax
        x = pad_l + i * slot + 1
        parts.append(f'<rect class="bar" x="{x:.1f}" y="{base - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2">'
                     f'<title>{html.escape(lab)}: {v} {html.escape(unit)}</title></rect>')
        if i % step_labels == 0:
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{h - 6}" text-anchor="middle">{html.escape(lab)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def build(cfg: dict) -> Path:
    tz = ZoneInfo(cfg.get("timezone", "Europe/Istanbul"))
    today = datetime.now(tz).date()
    con = db.connect(cfg["data_dir"])
    today_st = stats.day_stats(con, today)
    last30 = stats.daily_totals(con, today, 30)
    last7 = sum(v for _, v in last30[-7:])
    total = stats.running_total(con)
    first = stats.first_day(con) or today.isoformat()
    first_tr = datetime.strptime(first, "%Y-%m-%d").strftime("%d.%m.%Y")

    gates = stats.gate_counts(con, today)
    gate_html = ""
    if len(gates) > 1:
        tiles = "".join(f'<div class="tile"><div class="v">{n}</div><div class="l">{html.escape(g)}</div></div>' for g, n in gates)
        gate_html = f"<h2>Bugün, noktaya göre</h2><div class=\"tiles\">{tiles}</div>"

    cmp_html = ""
    cs = (cfg.get("post") or {}).get("campaign_start") or ""
    if cs:
        avg_b, avg_s, nb, ns = stats.before_after(con, date.fromisoformat(cs), today)
        if avg_b is not None and avg_s is not None:
            delta = (avg_s - avg_b) / avg_b * 100 if avg_b else 0.0
            cmp_html = f"""<h2>Paylaşımdan önce ve sonra</h2>
<div class="tiles">
<div class="tile"><div class="v">{avg_b:.0f}</div><div class="l">günlük ortalama, paylaşım öncesi ({nb} gün)</div></div>
<div class="tile"><div class="v">{avg_s:.0f}</div><div class="l">günlük ortalama, paylaşım sonrası ({ns} gün)</div></div>
<div class="tile"><div class="v">{delta:+.0f}%</div><div class="l">fark · ilk paylaşım {datetime.strptime(cs, '%Y-%m-%d').strftime('%d.%m.%Y')}</div></div>
</div>"""

    rows = "".join(f"<tr><td>{d}</td><td class='n'>{v}</td></tr>" for d, v in reversed(last30))
    hourly_rows = "".join(f"<tr><td>{stats.hour_label(h)}</td><td class='n'>{v}</td></tr>"
                          for h, v in enumerate(today_st.hourly) if v)
    peak = stats.hour_label(today_st.peak_hour) if today_st.peak_hour is not None else "-"

    doc = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kaldırım Sayacı</title><style>{CSS}</style></head><body><main>
<h1>Kaldırım Sayacı</h1>
<p class="sub">Bir İstanbul sokağında kaldırımdan geçen motosikletler. Sayım {first_tr} tarihinden beri. Güncelleme: {datetime.now(tz).strftime('%d.%m.%Y %H:%M')}</p>
<div class="tiles">
<div class="tile"><div class="v">{today_st.total}</div><div class="l">bugün</div></div>
<div class="tile"><div class="v">{last7}</div><div class="l">son 7 gün</div></div>
<div class="tile"><div class="v">{total}</div><div class="l">toplam</div></div>
<div class="tile"><div class="v" style="font-size:22px;padding-top:8px">{peak}</div><div class="l">bugünün en yoğun saati</div></div>
</div>
<h2>Bugün, saat dilimine göre</h2>
{bar_svg([f"{h:02d}" for h in range(24)], today_st.hourly, "geçiş", step_labels=3)}
<details><summary>Tablo</summary><table><tr><th>Saat</th><th>Geçiş</th></tr>{hourly_rows or "<tr><td colspan=2>henüz yok</td></tr>"}</table></details>
{gate_html}
{cmp_html}
<h2>Son 30 gün</h2>
{bar_svg([d[5:] for d, _ in last30], [v for _, v in last30], "geçiş", step_labels=5)}
<details><summary>Tablo</summary><table><tr><th>Gün</th><th>Geçiş</th></tr>{rows}</table></details>
<p class="method"><b>Yöntem.</b> Sabit bir kamera, nesne tanıma modeli (YOLO) ile motosikletleri izler ve her aracı kaldırım üzerindeki sanal bir çizgiyi geçtiğinde bir kez sayar. Yayınlanan tek şey sayılardır; görüntü, plaka ya da kişi paylaşılmaz. Kayıtlar yalnızca resmi ihbar için yerelde tutulur.</p>
</main></body></html>"""
    out = Path(cfg["data_dir"], "site", "index.html")
    out.write_text(doc, encoding="utf-8")
    return out


def main() -> None:
    print(build(config.load()))


if __name__ == "__main__":
    main()
