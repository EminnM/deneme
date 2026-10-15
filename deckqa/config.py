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
    title_gap: float = 6.0        # minimum clear space between a title's text and content below it
    overlap_min: float = 1.0      # overlap thinner than this (pt) is ignored
    peer_size_tol: float = 0.08   # same-size shapes: width/height within 8%
    peer_pos_tol: float = 1.0     # "aligned" when within this many pt
    icon_max: float = 90.0        # pictures/groups up to this size count as icons
    icon_center_tol: float = 1.0  # icon nearly centred if within 10% of panel but > this off
    icon_offset_tol: float = 1.5  # sibling panels: icon offset may differ by this much
