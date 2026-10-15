"""Applies the machine-readable fixes attached to issues. Operates on live python-pptx shapes."""
import copy
from pptx.util import Pt, Emu

from .config import Config
from .textfit import measure

EMU = 12700.0


def _by_id(slide):
    return {sh.shape_id: sh for sh in slide.shapes}


def _pin(shape):
    """Write the full inherited geometry before moving; python-pptx otherwise leaves
    ext=0 on placeholders that inherit position from the layout and the box collapses."""
    l, t, w, h = shape.left, shape.top, shape.width, shape.height
    shape.left, shape.top, shape.width, shape.height = l, t, w, h


def _set_size(shape, size):
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(size)


def _el(deck, slide_no, sid):
    for e in deck.slides[slide_no - 1].els:
        if e.id == sid:
            return e


def apply(deck, issues, cfg: Config):
    """Mutates deck.prs; returns number of fixes applied. Marks issues fixed."""
    n = 0
    moved = set()  # (slide, shape_id, axis) already positioned
    order = {"remove": 0, "font": 1, "title_size": 1, "min_font": 2, "fit": 3, "title_fit": 3,
             "title_pos": 4, "align": 5, "distribute": 6, "straighten": 7, "add_number": 8}
    todo = sorted((i for i in issues if i.fixable and i.fix), key=lambda i: order.get(i.fix["op"], 9))
    for iss in todo:
        sl = deck.slides[iss.slide - 1]
        shapes = _by_id(sl.slide)
        f = iss.fix
        op = f["op"]
        ok = False
        if op == "remove":
            sh = shapes.get(f["id"])
            if sh is not None:
                sh._element.getparent().remove(sh._element)
                ok = True
        elif op == "font":
            sh = shapes.get(f["id"])
            if sh is not None:
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        if r.font.name:
                            r.font.name = f["font"]
                ok = True
        elif op == "title_size":
            sh = shapes.get(f["id"])
            if sh is not None:
                _set_size(sh, f["size"])
                ok = True
        elif op == "min_font":
            sh = shapes.get(f["id"])
            if sh is not None:
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        if r.font.size and r.font.size.pt < cfg.min_font:
                            r.font.size = Pt(cfg.min_font)
                ok = True
        elif op in ("fit", "title_fit"):
            sh = shapes.get(f["id"])
            e = _el(deck, iss.slide, f["id"])
            if sh is not None and e is not None:
                floor = cfg.title_min_font if op == "title_fit" else cfg.min_font
                size = e.size or cfg.default_font
                limit = cfg.title_max_lines

                def good(sz):
                    m = measure(e, cfg, sz)
                    if op == "title_fit":
                        return m["lines"] <= limit
                    return m["height"] <= e.height + 1 and not m["split"]
                while size > floor and not good(size):
                    size -= 1
                if good(size):
                    _set_size(sh, size)
                    ok = True
                elif op == "fit":  # last resort: grow the box downward if there is room
                    m = measure(e, cfg, max(size, floor))
                    new_h = m["height"]
                    if e.top + new_h <= deck.height:
                        _pin(sh)
                        _set_size(sh, max(size, floor))
                        sh.height = Emu(int(new_h * EMU))
                        ok = True
        elif op == "title_pos":
            sh = shapes.get(f["id"])
            if sh is not None:
                _pin(sh)
                sh.left, sh.top = Emu(int(f["pos"][0] * EMU)), Emu(int(f["pos"][1] * EMU))
                ok = True
        elif op == "align":
            edge, target = f["edge"], f["target"]
            axis = "x" if edge in ("left", "right", "center") else "y"
            for sid in f["ids"]:
                sh = shapes.get(sid)
                if sh is None or (iss.slide, sid, axis) in moved:
                    continue
                _pin(sh)
                w, h = sh.width / EMU, sh.height / EMU
                if edge == "left":
                    sh.left = Emu(int(target * EMU))
                elif edge == "right":
                    sh.left = Emu(int((target - w) * EMU))
                elif edge == "center":
                    sh.left = Emu(int((target - w / 2) * EMU))
                elif edge == "top":
                    sh.top = Emu(int(target * EMU))
                elif edge == "bottom":
                    sh.top = Emu(int((target - h) * EMU))
                moved.add((iss.slide, sid, axis))
            ok = True
        elif op == "distribute":
            grp = [shapes[i] for i in f["ids"] if i in shapes]
            if len(grp) >= 3:
                row = f["axis"] == "row"
                key = (lambda s: s.left) if row else (lambda s: s.top)
                for s_ in grp:
                    _pin(s_)
                grp.sort(key=key)
                size = (lambda s: s.width) if row else (lambda s: s.height)
                start, end = key(grp[0]), key(grp[-1]) + size(grp[-1])
                gap = (end - start - sum(size(s) for s in grp)) / (len(grp) - 1)
                pos = start
                for s in grp:
                    if row:
                        s.left = Emu(int(pos))
                    else:
                        s.top = Emu(int(pos))
                    pos += size(s) + gap
                ok = True
        elif op == "straighten":
            sh = shapes.get(f["id"])
            if sh is not None and hasattr(sh, "begin_x"):
                dx, dy = abs(sh.end_x - sh.begin_x), abs(sh.end_y - sh.begin_y)
                if dx >= dy:
                    sh.end_y = sh.begin_y
                else:
                    sh.end_x = sh.begin_x
                ok = True
        elif op == "add_number":
            l, t, w, h = f["ref"]
            tb = sl.slide.shapes.add_textbox(Emu(int(l * EMU)), Emu(int(t * EMU)), Emu(int(w * EMU)), Emu(int(h * EMU)))
            tb.text_frame.text = str(iss.slide)
            for p in tb.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(max(cfg.min_font, 12))
            ok = True
        if ok:
            iss.status = "fixed"
            n += 1
    return n
