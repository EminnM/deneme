"""Approximate text layout using Liberation/DejaVu metrics (deterministic, no rendering)."""
from functools import lru_cache
from PIL import ImageFont

_REG = ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
_BOLD = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


@lru_cache(maxsize=None)
def _font(bold, size):
    for p in (_BOLD if bold else _REG):
        try:
            return ImageFont.truetype(p, max(1, int(round(size * 10))))  # 10x for precision
        except OSError:
            continue
    return ImageFont.load_default()


def text_width(s, size, bold=False):
    return _font(bold, size).getlength(s) / 10.0


def wrap(text, size, width, bold=False):
    """Return list of lines (each a list of words). Words wider than width are flagged split."""
    lines, split = [], False
    for para in text.split("\n"):
        cur, cur_w = [], 0.0
        space = text_width(" ", size, bold)
        for w in para.split():
            ww = text_width(w, size, bold)
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
    lines, split = wrap(el.text, size, width, el.bold)
    n = len(lines)
    height = n * size * cfg.line_height + mt + mb
    orphan = n >= 2 and len(lines[-1]) == 1 and len(lines[-2]) >= 3 and \
        text_width(lines[-1][0], size, el.bold) < width * 0.25
    text_w = max((text_width(" ".join(l), size, el.bold) for l in lines), default=0.0)
    return dict(lines=n, height=height, split=split, orphan=orphan, width=width,
                text_w=min(text_w, width), ml=ml, mr=mr, mt=mt, mb=mb)


def text_rect(el, cfg, size=None):
    """Absolute rectangle (l, t, r, b) the text ink is expected to occupy (alignment/anchor aware)."""
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    m = measure(el, cfg, size)
    tf = el.shape.text_frame
    ink_h = m["height"] - m["mt"] - m["mb"]
    anchor = tf.vertical_anchor
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
