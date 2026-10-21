"""Hourly bar chart PNG for the nightly post. Single series, one hue, direct label on the peak only."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .stats import DayStats  # noqa: E402

SERIES = "#2a78d6"
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"


def hourly_png(st: DayStats, out: Path, title: str) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    hours = list(range(24))
    ax.bar(hours, st.hourly, width=0.72, color=SERIES, linewidth=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", colors=TEXT_2, length=0, labelsize=9)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 3)])
    ax.set_xlim(-0.6, 23.6)
    if st.peak_hour is not None:
        ax.annotate(str(st.hourly[st.peak_hour]), (st.peak_hour, st.hourly[st.peak_hour]),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9, color=TEXT)
    fig.text(0.015, 0.95, title, fontsize=13, color=TEXT, fontweight="bold", va="top")
    fig.text(0.015, 0.875, f"Toplam {st.total}  ·  saat dilimine göre", fontsize=10, color=TEXT_2, va="top")
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.06, right=0.98)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out
