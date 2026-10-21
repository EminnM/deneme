"""Approximate text layout using Liberation/DejaVu metrics (deterministic, no rendering)."""
from functools import lru_cache
from PIL import ImageFont

import os
import re
import sys

_DIRS = []
if sys.platform.startswith("win"):
    _DIRS = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
elif sys.platform == "darwin":
    _DIRS = ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
else:
    _DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts")]

# font name -> file stems to try (first hit wins); metric-compatible open fonts are listed as stand-ins
_ALIASES = {
    "calibri": ["calibri", "carlito"], "calibrilight": ["calibril", "carlito"], "arial": ["arial", "liberationsans", "arimo"],
    "helvetica": ["arial", "liberationsans", "helvetica"], "helveticaneue": ["arial", "liberationsans"],
    "timesnewroman": ["times", "liberationserif", "timesnewroman"], "times": ["times", "liberationserif"],
    "cambria": ["cambria", "caladea"], "couriernew": ["cour", "liberationmono", "couriernew"],
    "segoeui": ["segoeui"], "verdana": ["verdana", "dejavusans"], "tahoma": ["tahoma"], "georgia": ["georgia", "gelasio"],
    "trebuchetms": ["trebuc"], "arialnarrow": ["arialn", "liberationsansnarrow"], "consolas": ["consola"],
    "aptos": ["aptos", "calibri", "carlito"], "aptosdisplay": ["aptosdisplay", "aptos", "calibri", "carlito"],
}
_GENERIC = ["arial", "liberationsans", "arimo", "dejavusans", "helvetica", "verdana"]
_INDEX = None
_WARNED = set()


def _norm(n):
    return re.sub(r"[^a-z0-9]", "", (n or "").lower())


def _index():
    global _INDEX
    if _INDEX is None:
        _INDEX = {}
        for d in _DIRS:
            for root, _dirs, files in os.walk(d) if os.path.isdir(d) else []:
                for f in files:
                    if f.lower().endswith((".ttf", ".otf")):
                        _INDEX.setdefault(_norm(os.path.splitext(f)[0]), os.path.join(root, f))
    return _INDEX


def _find(stem, bold):
    idx = _index()
    names = ([stem + "b", stem + "bd", stem + "bold", stem + "boldmt"] if bold else [stem, stem + "regular", stem + "mt"])
    for n in names:
        if n in idx:
            return idx[n]
    return None


def resolve_font(name, bold):
    """-> (path or None, exact: bool). exact=False means a stand-in was used for a named font."""
    key = _norm(name)
    for stem in (_ALIASES.get(key, [key]) if key else []):
        p = _find(stem, bold)
        if p:
            return p, True          # the font itself or a metric-compatible stand-in
    for stem in _GENERIC:
        p = _find(stem, bold)
        if p:
            return p, not key
    return None, False


@lru_cache(maxsize=None)
def _font(bold, size, name=None):
    path, exact = resolve_font(name, bold)
    if name and not exact and (name, bold) not in _WARNED:
        _WARNED.add((name, bold))
        FALLBACKS.append(name)
    if path:
        try:
            return ImageFont.truetype(path, max(1, int(round(size * 10))))  # 10x for precision
        except OSError:
            pass
    return None


FALLBACKS = []   # fonts that had to be approximated; reported to the user


def text_width(s, size, bold=False, name=None):
    f = _font(bold, size, name)
    if f is None:                       # no usable font on this machine: average-width estimate
        return len(s) * size * 0.52
    return f.getlength(s) / 10.0


def wrap(text, size, width, bold=False, name=None):
    """Return list of lines (each a list of words). Words wider than width are flagged split."""
    lines, split = [], False
    for para in text.split("\n"):
        cur, cur_w = [], 0.0
        space = text_width(" ", size, bold, name)
        for w in para.split():
            ww = text_width(w, size, bold, name)
            if ww > width:
                split = True
            add = ww if not cur else cur_w + space + ww
            if cur and add > width:
                lines.append(cur)
                cur, cur_w = [w], ww
            else:
                cur.append(w)
                cur_w = add
        lines.append(cur)
    return lines, split


def measure(el, cfg, size=None):
    """-> dict(lines, height, split, orphan) for a text element at font size."""
    tf = el.shape.text_frame
    size = size or el.size or cfg.default_font
    ml = (tf.margin_left if tf.margin_left is not None else 91440) / 12700.0
    mr = (tf.margin_right if tf.margin_right is not None else 91440) / 12700.0
    mt = (tf.margin_top if tf.margin_top is not None else 45720) / 12700.0
    mb = (tf.margin_bottom if tf.margin_bottom is not None else 45720) / 12700.0
    width = max(1.0, el.width - ml - mr)
    lines, split = wrap(el.text, size, width, el.bold, el.font_name)
    n = len(lines)
    height = n * size * cfg.line_height + mt + mb
    orphan = n >= 2 and len(lines[-1]) == 1 and len(lines[-2]) >= 3 and \
        text_width(lines[-1][0], size, el.bold, el.font_name) < width * 0.25
    text_w = max((text_width(" ".join(l), size, el.bold, el.font_name) for l in lines), default=0.0)
    return dict(lines=n, height=height, split=split, orphan=orphan, width=width,
                text_w=min(text_w, width), ml=ml, mr=mr, mt=mt, mb=mb)


def anchor_of(el):
    """Vertical anchor, inherited from the layout/master placeholder when not set on the shape."""
    sh = el.shape
    for _ in range(4):
        try:
            a = sh.text_frame.vertical_anchor
        except Exception:
            return None
        if a is not None:
            return a
        sh = getattr(sh, "_base_placeholder", None)
        if sh is None:
            return None
    return None


def overflow_bottom(el, cfg, size=None):
    """Where the text bottom lands relative to the box top (top margin + text height)."""
    m = measure(el, cfg, size)
    return m["mt"] + (m["height"] - m["mt"] - m["mb"])


def text_rect(el, cfg, size=None):
    """Absolute rectangle (l, t, r, b) the text ink is expected to occupy (alignment/anchor aware)."""
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    m = measure(el, cfg, size)
    tf = el.shape.text_frame
    ink_h = m["height"] - m["mt"] - m["mb"]
    anchor = anchor_of(el)
    if anchor == MSO_ANCHOR.MIDDLE:
        top = el.top + (el.height - ink_h) / 2
    elif anchor == MSO_ANCHOR.BOTTOM:
        top = el.bottom - m["mb"] - ink_h
    else:
        top = el.top + m["mt"]
    al = tf.paragraphs[0].alignment if tf.paragraphs else None
    if al == PP_ALIGN.CENTER:
        left = el.cx - m["text_w"] / 2
    elif al == PP_ALIGN.RIGHT:
        left = el.right - m["mr"] - m["text_w"]
    else:
        left = el.left + m["ml"]
    return (left, top, left + m["text_w"], top + ink_h)
