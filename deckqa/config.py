from dataclasses import dataclass

CATEGORIES = [
    "Alignment", "Spacing", "Text fit", "Lines and arrows",
    "Titles", "Readability", "Leftover graphics", "Consistency",
]


@dataclass
class Config:
    # all lengths in points
    align_tol: float = 6.0        # edges closer than this (but not equal) count as "almost aligned"
    align_eps: float = 0.25       # ignore differences below this (float noise)
    gap_tol: float = 4.0          # allowed difference between sibling gaps
    band_ratio: float = 0.22      # empty vertical band bigger than this share of slide height
    min_font: float = 10.0        # smaller text is flagged unreadable
    title_max_lines: int = 2
    title_min_font: float = 20.0  # auto-fix never shrinks titles below this
    pos_tol: float = 2.0          # title/page-number position drift across slides
    angle_tol: float = 5.0        # lines within this many degrees of axis but not on it are crooked
    line_height: float = 1.2
    default_font: float = 18.0
    default_title_font: float = 32.0
