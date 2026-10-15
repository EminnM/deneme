"""Flat, unit-normalised (points) view of a PPTX deck."""
import re
from dataclasses import dataclass, field
from typing import Optional

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

EMU = 12700.0
TITLE_TYPES = (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)


@dataclass
class El:
    shape: object
    slide: int
    id: int
    name: str
    left: float
    top: float
    width: float
    height: float
    kind: str                      # text | picture | line | shape | group | other
    is_title: bool = False
    is_placeholder: bool = False
    is_number: bool = False
    text: str = ""
    sizes: list = field(default_factory=list)
    fonts: list = field(default_factory=list)
    bold: bool = False
    fill: Optional[tuple] = None
    line: Optional[tuple] = None   # (x1, y1, x2, y2) for connectors

    @property
    def right(self): return self.left + self.width
    @property
    def bottom(self): return self.top + self.height
    @property
    def cx(self): return self.left + self.width / 2
    @property
    def bbox(self): return (self.left, self.top, self.right, self.bottom)

    @property
    def size(self):
        return max(self.sizes) if self.sizes else None


def _fill(shape):
    try:
        if shape.fill.type == 1:  # solid
            c = shape.fill.fore_color
            if c.type is not None and hasattr(c, "rgb") and c.rgb is not None:
                return tuple(c.rgb)
    except Exception:
        pass
    return None


def _runs(shape):
    if not getattr(shape, "has_text_frame", False):
        return
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            yield r


def load_element(shape, slide_no, cfg, slide_h):
    try:
        l, t, w, h = shape.left, shape.top, shape.width, shape.height
    except Exception:
        return None
    if None in (l, t, w, h):
        return None
    st = shape.shape_type
    is_ph = shape.is_placeholder
    ph_type = shape.placeholder_format.type if is_ph else None
    kind = "other"
    if st == MSO_SHAPE_TYPE.LINE or shape.__class__.__name__ == "Connector":
        kind = "line"
    elif st == MSO_SHAPE_TYPE.GROUP:
        kind = "group"
    elif st == MSO_SHAPE_TYPE.PICTURE or ph_type == PP_PLACEHOLDER.PICTURE:
        kind = "picture"
    elif getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip():
        kind = "text"
    elif st in (MSO_SHAPE_TYPE.AUTO_SHAPE, MSO_SHAPE_TYPE.TEXT_BOX, MSO_SHAPE_TYPE.PLACEHOLDER):
        kind = "shape"
    el = El(shape, slide_no, shape.shape_id, shape.name, l / EMU, t / EMU, w / EMU, h / EMU, kind)
    el.is_placeholder = is_ph
    el.is_title = is_ph and ph_type in TITLE_TYPES
    text = shape.text_frame.text if getattr(shape, "has_text_frame", False) else ""
    el.text = text
    el.is_number = (is_ph and ph_type == PP_PLACEHOLDER.SLIDE_NUMBER) or (
        bool(re.fullmatch(r"\s*\d{1,3}\s*", text)) and el.top > slide_h * 0.85)
    for r in _runs(shape):
        if r.font.size:
            el.sizes.append(r.font.size.pt)
        if r.font.name:
            el.fonts.append(r.font.name)
        if r.font.bold:
            el.bold = True
    if el.kind == "text" and not el.sizes:
        el.sizes = [cfg.default_title_font if el.is_title else cfg.default_font]
    el.fill = _fill(shape) if kind in ("shape", "text") else None
    if kind == "line":
        try:
            el.line = (shape.begin_x / EMU, shape.begin_y / EMU, shape.end_x / EMU, shape.end_y / EMU)
        except Exception:
            el.line = (el.left, el.top, el.right, el.bottom)
    return el


@dataclass
class Slide:
    no: int
    slide: object
    els: list


@dataclass
class Deck:
    prs: object
    width: float
    height: float
    slides: list


def load(path, cfg):
    prs = Presentation(path)
    return build(prs, cfg)


def build(prs, cfg):
    W, H = prs.slide_width / EMU, prs.slide_height / EMU
    slides = []
    for i, s in enumerate(prs.slides, 1):
        els = [e for e in (load_element(sh, i, cfg, H) for sh in s.shapes) if e]
        slides.append(Slide(i, s, els))
    return Deck(prs, W, H, slides)
