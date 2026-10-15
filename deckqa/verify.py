"""Verification board data.

For every slide and every checklist item this says what was MEASURED and found correct (green), what looks
wrong (red), or that the item does not apply (grey), with the boxes on the slide each statement refers to.
It looks at the deck as received: no fix is applied and none is shown, so a reviewer forms their own view first.
"""
import math
from collections import Counter, defaultdict
from statistics import median

from .config import CATEGORIES
from . import checks as C
from .explain import explain
from .textfit import measure, text_rect, overflow_bottom

# what each item can and cannot confirm (shown to the reviewer so a green tick is never over-trusted)
LIMITS = {
    "Alignment": "Measures edges, centres and same-size peers. It cannot tell intentional staggering or optical alignment from a mistake.",
    "Spacing": "Measures gaps, overlaps and empty bands. It does not judge whether the whitespace looks balanced.",
    "Text fit": "Wraps text with font metrics (Liberation Sans stand-in), so unusual fonts can be a few points off. Text inside charts and tables is not measured.",
    "Lines and arrows": "Checks angle and crossings of straight lines. It does not check arrowheads or that a connector joins the right shapes.",
    "Titles": "Checks line count and spacing. It does not judge whether the title says the right thing.",
    "Readability": "Checks font size only. Colour contrast, text over images and chart/table text are not checked.",
    "Leftover graphics": "Finds empty shapes and placeholders. It cannot see stray items inside images, charts or hidden shapes.",
    "Consistency": "Compares fonts, sizes, positions, page numbers and exact colours. It cannot judge style intent or whether icons look alike.",
}
GLOBAL_LIMITS = ("Not checked at all: wording and spelling, facts and numbers, whether charts show the right data, "
                 "image content and quality, and overall taste. A green tick means the tool measured the item "
                 "under the stated rule and found no defect - not that the slide is perfect.")


def _r(v):
    return round(v, 1)


def _box(e_or_rect, label="", kind="ok"):
    b = e_or_rect.bbox if hasattr(e_or_rect, "bbox") else e_or_rect
    return dict(b=[_r(v) for v in b], t=label, k=kind)


def _name(e, n=26):
    if e.kind == "text":
        t = " ".join(e.text.split())
        return f"'{t[:n]}{'..' if len(t) > n else ''}'"
    if e.kind == "picture":
        return "a picture"
    if e.kind == "frame":
        return "a table/chart"
    import re
    return "a " + (re.sub(r"\s*\d+$", "", e.name).lower() or "shape")


def _pt(v):
    return f"{v:.0f}pt" if abs(v - round(v)) < 0.05 else f"{v:.1f}pt"


def _hex(c):
    return "#%02X%02X%02X" % tuple(c)


def _ev(item, ok=None, flags=None, na=None):
    """Assemble one criterion's evidence. flags win over ok; na only when nothing applies."""
    ok, flags = ok or [], flags or []
    if flags:
        status, summary = "flag", f"{len(flags)} thing(s) need a look" + (f"; {len(ok)} confirmed correct" if ok else "")
    elif na:
        status, summary = "na", na
    else:
        first = ok[0]["text"]
        first = first if len(first) <= 92 else first[:90] + ".."
        status, summary = "pass", first + (f"  (+{len(ok) - 1} more confirmed)" if len(ok) > 1 else "")
    return dict(item=item, status=status, summary=summary, ok=ok, flags=flags, limits=LIMITS[item])


def _flags_from(issues, category, deck):
    out = []
    for i in issues:
        if i.category != category:
            continue
        e = explain(i, deck.width, deck.height)
        boxes = [_box(m[:4], "", "flag") for m in (i.marks or [])] or ([_box(i.bbox, "", "flag")] if i.bbox else [])
        out.append(dict(text=e["label"] + ": " + i.message, why=e["why"], sev=e["severity"], boxes=boxes))
    return out


# --------------------------------------------------------------------------- deck-wide inventory
def inventory(deck, cfg):
    tf = set(deck.theme_fonts) | {"+mn-lt", "+mj-lt"}
    theme_label = (deck.theme_fonts[1] if len(deck.theme_fonts) > 1 else "(theme font)")
    norm = lambda f: theme_label if f in tf else f
    fonts, sizes, fills, tcols = Counter(), Counter(), Counter(), Counter()
    f_sl, s_sl, fi_sl, tc_sl = (defaultdict(set) for _ in range(4))
    titles, numbers, assumed = [], {}, 0
    for sl in deck.slides:
        for e in sl.leaves:
            for f in e.fonts:
                fonts[norm(f)] += 1; f_sl[norm(f)].add(sl.no)
            if e.implicit_runs:
                fonts[theme_label] += e.implicit_runs; f_sl[theme_label].add(sl.no)
            if e.kind == "text":
                if e.size_assumed:
                    assumed += 1
                for z in e.sizes:
                    sizes[z] += 1; s_sl[z].add(sl.no)
            if e.fill is not None and e.kind in ("shape", "text"):
                fills[e.fill] += 1; fi_sl[e.fill].add(sl.no)
            if e.text_color is not None and e.kind == "text":
                tcols[e.text_color] += 1; tc_sl[e.text_color].add(sl.no)
        t = [e for e in sl.leaves if e.is_title and e.kind == "text"]
        titles.append(dict(slide=sl.no, size=t[0].size if t else None,
                           pos=[_r(t[0].left), _r(t[0].top)] if t else None,
                           lines=measure(t[0], cfg)["lines"] if t else None,
                           text=" ".join(t[0].text.split())[:60] if t else ""))
        nums = [e for e in sl.all if e.is_number]
        numbers[sl.no] = [_r(nums[0].left), _r(nums[0].top)] if nums else None
    total_runs = sum(fonts.values()) or 1

    def rows(cnt, slides, fmt, rare_limit):
        out = []
        for k, n in cnt.most_common():
            out.append(dict(value=fmt(k), count=n, slides=sorted(slides[k]), rare=(len(slides[k]) == 1 and n <= rare_limit and len(cnt) > 1),
                            swatch=_hex(k) if isinstance(k, tuple) else None))
        return out
    return dict(
        fonts=rows(fonts, f_sl, str, max(1, total_runs // 20)),
        sizes=rows(sizes, s_sl, lambda z: f"{z:g}pt", 1),
        fills=rows(fills, fi_sl, _hex, 1),
        text_colours=rows(tcols, tc_sl, _hex, 1),
        titles=titles, page_numbers=numbers, assumed_size_boxes=assumed,
        theme_fonts=list(deck.theme_fonts), n_slides=len(deck.slides))


# --------------------------------------------------------------------------- per-slide evidence
def _alignment(deck, sl, cfg, issues):
    els = [e for e in C._layout_els(sl.leaves, deck) if not e.is_title and e.kind != "line"]
    flags = _flags_from(issues, "Alignment", deck)
    ok = []
    if len(els) >= 2:
        edges = {"left": lambda e: e.left, "right": lambda e: e.right, "top": lambda e: e.top,
                 "bottom": lambda e: e.bottom, "centre": lambda e: e.cx}
        seen, groups = set(), []
        for edge, fn in edges.items():
            for cl in C._clusters([(fn(e), e) for e in els], cfg.align_eps):
                members = [e for _, e in cl]
                if len(members) < 2:
                    continue
                key = frozenset(id(m) for m in members)
                if key in seen:
                    continue
                seen.add(key)
                groups.append((len(members), edge, median(v for v, _ in cl), members))
        for n, edge, v, members in sorted(groups, key=lambda g: -g[0])[:6]:
            names = ", ".join(_name(m, 18) for m in members[:3]) + ("..." if len(members) > 3 else "")
            ok.append(dict(text=f"{n} elements share exactly the same {edge} edge ({_pt(v)}): {names}",
                           boxes=[_box(m, "", "ok") for m in members]))
    na = None if (ok or flags) else ("fewer than two layout elements to compare" if len(els) < 2
                                      else f"{len(els)} elements checked; none close enough to need aligning")
    if not ok and not flags and len(els) >= 2:
        ok.append(dict(text=f"{len(els)} elements compared: none is a near-miss or an outlier from its same-size peers", boxes=[]))
        na = None
    return _ev("Alignment", ok, flags, na)


def _spacing(deck, sl, cfg, issues):
    els = [e for e in C._layout_els(sl.els, deck) if not e.is_title]
    ok, flags = [], _flags_from(issues, "Spacing", deck)
    for axis, grp, gaps in C.row_col_groups(els):
        if max(gaps) - min(gaps) <= cfg.gap_tol:
            marks = C.gap_marks(axis, grp)
            ok.append(dict(text=f"{len(grp)} shapes in a {axis} are evenly spaced: every gap is {_pt(median(gaps))} (largest difference {max(gaps) - min(gaps):.1f}pt)",
                           boxes=[_box(m, f"{g:.0f}pt", "ok") for m, g in zip(marks, gaps)]))
    items = [e for e in sl.leaves if not e.is_title and not e.is_number and e.kind in ("text", "picture", "frame")]
    n_pairs = len(items) * (len(items) - 1) // 2
    has_overlap = any("overlap" in f["text"] or "nearly touch" in f["text"] for f in flags)
    if len(items) >= 2 and not has_overlap:
        ok.append(dict(text=f"{len(items)} text/picture/table blocks compared in pairs ({n_pairs} pairs): none overlap and none touch",
                       boxes=[_box(e, "", "ok") for e in items]))
    content = [e for e in C._layout_els(sl.leaves, deck) if not e.is_title and e.kind != "line"]
    if content:
        W, H = deck.width, deck.height
        m = min(min(e.left, e.top, W - e.right, H - e.bottom) for e in content)
        ok.append(dict(text=f"content stays inside the slide: the closest element is {_pt(m)} from an edge", boxes=[]))
    if not any("empty horizontal band" in f["text"] for f in flags) and len(els) >= 2:
        ok.append(dict(text=f"no empty horizontal band taller than {cfg.band_ratio:.0%} of the slide", boxes=[]))
    na = None if (ok or flags) else "nothing to space on this slide"
    return _ev("Spacing", ok, flags, na)


def _text_fit(deck, sl, cfg, issues):
    texts = [e for e in sl.leaves if e.kind == "text" and not e.is_number]
    flags = _flags_from(issues, "Text fit", deck)
    ok = []
    if texts:
        rows = []
        for e in texts:
            if e.height < 1:
                rows.append((None, e)); continue
            rows.append((overflow_bottom(e, cfg) / e.height, e))
        fit = [(r, e) for r, e in rows if r is not None and r <= 1.0 + 1.0 / max(e.height, 1)]
        grow = [e for r, e in rows if r is None]
        if fit:
            tight = sorted(fit, key=lambda x: -x[0])[:3]
            tt = "; ".join(f"{_name(e, 16)} {r:.0%}" for r, e in tight)
            ok.append(dict(text=f"{len(fit)} text box(es) fit inside their boxes with no spill (fullest: {tt})",
                           boxes=[_box(e, f"{r:.0%} full", "ok") for r, e in fit]))
        if grow:
            ok.append(dict(text=f"{len(grow)} text box(es) are auto-growing boxes (height 0), so they cannot overflow", boxes=[_box(e, "auto-grow", "ok") for e in grow]))
        splits = [e for e in texts if measure(e, cfg)["split"] and e.shape.text_frame.word_wrap is not False]
        if not splits:
            ok.append(dict(text="no word is wider than its box, so no word splits across lines", boxes=[]))
    return _ev("Text fit", ok, flags, None if (ok or flags) else "no text on this slide")


def _lines(deck, sl, cfg, issues):
    lines = [e for e in sl.leaves if e.kind == "line"]
    flags = _flags_from(issues, "Lines and arrows", deck)
    ok = []
    if lines:
        straight = []
        for ln in lines:
            x1, y1, x2, y2 = ln.line
            ang = math.degrees(math.atan2(abs(y2 - y1), abs(x2 - x1)))
            if min(ang, 90 - ang) < 0.2:
                straight.append(ln)
        if straight:
            ok.append(dict(text=f"{len(straight)} of {len(lines)} line(s)/arrow(s) are exactly horizontal or vertical",
                           boxes=[_box(l, "straight", "ok") for l in straight]))
        if not any("crosses" in f["text"] for f in flags):
            ok.append(dict(text="no line passes through a text box", boxes=[]))
    return _ev("Lines and arrows", ok, flags, None if (ok or flags) else "no lines or arrows on this slide")


def _titles(deck, sl, cfg, issues):
    flags = _flags_from(issues, "Titles", deck)
    ok = []
    ts = [e for e in sl.leaves if e.is_title and e.kind == "text"]
    for t in ts:
        m = measure(t, cfg)
        if m["lines"] <= cfg.title_max_lines:
            ok.append(dict(text=f"title {_name(t, 30)} fits on {m['lines']} line(s) at {t.size:g}pt (limit {cfg.title_max_lines})", boxes=[_box(t, "title", "ok")]))
        tl, tt, tr, tb = text_rect(t, cfg)
        gaps = []
        for o in C._content(sl, deck):
            if o is t or o.is_title or o.kind == "line":
                continue
            if o.kind == "shape" and not o.text.strip() and o.fill is None:
                continue
            if min(tr, o.right) - max(tl, o.left) <= 0:
                continue
            oy = text_rect(o, cfg)[1] if o.kind == "text" else o.top
            if oy >= tb - 0.5 and o.top > t.top:
                gaps.append((oy - tb, o))
        if gaps:
            g, o = min(gaps, key=lambda x: x[0])
            if g >= cfg.title_gap and not any("too close" in f["text"] or "title overlaps" in f["text"] for f in flags):
                ok.append(dict(text=f"clear space under the title: the next content ({_name(o, 18)}) starts {_pt(g)} below the title text (minimum {cfg.title_gap:g}pt)",
                               boxes=[_box(t, "", "ok"), _box(o, "", "ok")]))
        elif not any("title overlaps" in f["text"] for f in flags):
            ok.append(dict(text="nothing sits under or over the title text", boxes=[]))
    return _ev("Titles", ok, flags, None if (ok or flags) else "no title detected on this slide - check it yourself")


def _readability(deck, sl, cfg, issues):
    flags = _flags_from(issues, "Readability", deck)
    ok = []
    texts = [e for e in sl.leaves if e.kind == "text" and e.sizes]
    if texts:
        smallest = min(texts, key=lambda e: min(e.sizes))
        mn = min(smallest.sizes)
        if mn >= cfg.min_font:
            ok.append(dict(text=f"smallest text is {mn:g}pt ({_name(smallest, 24)}); the minimum is {cfg.min_font:g}pt",
                           boxes=[_box(smallest, f"{mn:g}pt", "ok")]))
        cnt = Counter(z for e in texts for z in e.sizes)
        ok.append(dict(text="font sizes used here: " + ", ".join(f"{z:g}pt x{n}" for z, n in sorted(cnt.items(), reverse=True)) +
                       (" (some sizes are assumed from the theme: not stated in the file)" if any(e.size_assumed for e in texts) else ""), boxes=[]))
    return _ev("Readability", ok, flags, None if (ok or flags) else "no text on this slide")


def _leftovers(deck, sl, cfg, issues):
    flags = _flags_from(issues, "Leftover graphics", deck)
    leaves = [e for e in sl.leaves if e.kind in ("text", "shape", "picture", "frame")]
    ok = []
    if leaves:
        text_n = sum(1 for e in leaves if e.kind == "text")
        pic_n = sum(1 for e in leaves if e.kind in ("picture", "frame"))
        bare = [e for e in leaves if e.kind == "shape" and not e.text.strip()]
        panels, accents, other = [], [], []
        for e in bare:
            holds = [o for o in leaves if o is not e and o.parent == e.parent and C._contains(e, o)] if hasattr(C, "_contains") else []
            if holds:
                panels.append(e)
            elif min(e.width, e.height) < 12:
                accents.append(e)
            else:
                other.append(e)
        flagged_ids = {i for f in issues if f.category == "Leftover graphics" for i in f.ids}
        other = [e for e in other if e.id not in flagged_ids]
        parts = [f"{text_n} with text", f"{pic_n} picture/table/chart"]
        if panels:
            parts.append(f"{len(panels)} panel(s) with content on them")
        if accents:
            parts.append(f"{len(accents)} thin accent bar(s)")
        if other:
            parts.append(f"{len(other)} other empty shape(s) (look at these yourself)")
        if not flags:
            ok.append(dict(text=f"{len(leaves)} elements inspected; none is an orphan: " + ", ".join(parts),
                           boxes=[_box(e, "panel", "ok") for e in panels] + [_box(e, "accent", "ok") for e in accents] +
                                 [_box(e, "empty?", "flag") for e in other]))
        W, H = deck.width, deck.height
        if not any("off the slide" in f["text"] for f in flags):
            ok.append(dict(text="nothing sits outside the slide", boxes=[]))
    return _ev("Leftover graphics", ok, flags, None if (ok or flags) else "nothing on this slide")


def _consistency(deck, sl, cfg, issues, inv):
    flags = _flags_from(issues, "Consistency", deck)
    ok = []
    theme_label = (deck.theme_fonts[1] if len(deck.theme_fonts) > 1 else "(theme font)")
    tf = set(deck.theme_fonts) | {"+mn-lt", "+mj-lt"}
    used = Counter()
    for e in sl.leaves:
        for f in e.fonts:
            used[theme_label if f in tf else f] += 1
        if e.implicit_runs:
            used[theme_label] += e.implicit_runs
    deck_font = inv["fonts"][0]["value"] if inv["fonts"] else None
    if used:
        names = ", ".join(sorted(used))
        if set(used) == {deck_font}:
            ok.append(dict(text=f"every run of text uses {deck_font}, the font used across the deck", boxes=[_box(e, "", "ok") for e in sl.leaves if e.kind == "text"]))
        elif not any("inconsistent font" in f["text"] for f in flags):
            ok.append(dict(text=f"fonts on this slide: {names}", boxes=[]))
    t = next((x for x in inv["titles"] if x["slide"] == sl.no), None)
    sizes = [x["size"] for x in inv["titles"] if x["size"] is not None and x["slide"] != 1]
    if t and t["size"] is not None and sizes and sl.no != 1:
        mode = Counter(sizes).most_common(1)[0][0]
        if t["size"] == mode and not any("title size" in f["text"] for f in flags):
            ok.append(dict(text=f"title size {t['size']:g}pt matches the title size on the other slides", boxes=[]))
    nums = inv["page_numbers"]
    have = [n for n, v in nums.items() if v]
    if have and sl.no != 1:
        if nums.get(sl.no) and not any("page number" in f["text"] for f in flags):
            ok.append(dict(text=f"page number present at {nums[sl.no][0]:.0f},{nums[sl.no][1]:.0f}pt, like {len(have) - 1} other slide(s)",
                           boxes=[_box(e, "page no.", "ok") for e in sl.all if e.is_number]))
    # exact colour sharing among same-size shapes
    filled = [e for e in sl.leaves if e.kind in ("shape", "text") and e.fill is not None and not e.is_title and min(e.width, e.height) >= 12]
    for ps in C._peer_sets(filled, cfg.peer_size_tol):
        cnt = Counter(e.fill for e in ps)
        col, n = cnt.most_common(1)[0]
        if n == len(ps):
            ok.append(dict(text=f"{n} same-size shapes all use exactly the same fill colour {_hex(col)}", boxes=[_box(e, _hex(col), "ok") for e in ps]))
    if not ok and not flags:
        return _ev("Consistency", ok, flags, "nothing to compare on this slide")
    return _ev("Consistency", ok, flags)


def elements(deck, sl, inv_theme):
    """Everything on the slide with the facts the reviewer wants to eyeball: font, size, colours, position."""
    tf = set(deck.theme_fonts) | {"+mn-lt", "+mj-lt"}
    rows = []
    for e in sl.leaves:
        fonts = sorted({(inv_theme if f in tf else f) for f in e.fonts})
        if e.implicit_runs and inv_theme not in fonts:
            fonts.append(inv_theme)
        rows.append(dict(
            label=_name(e, 30), kind=e.kind + (" (title)" if e.is_title else " (page no.)" if e.is_number else ""),
            font=", ".join(fonts) if e.kind == "text" else "-",
            size=(", ".join(f"{z:g}pt" for z in sorted(set(e.sizes), reverse=True)) + (" (assumed)" if e.size_assumed else "")) if e.kind == "text" else "-",
            colour=_hex(e.text_color) if e.text_color else "-", fill=_hex(e.fill) if e.fill else "-",
            x=_r(e.left), y=_r(e.top), w=_r(e.width), h=_r(e.height), b=[_r(v) for v in e.bbox]))
    return rows


def build(deck, cfg, issues=None):
    """issues = checks.run_all(deck, cfg) on the deck AS RECEIVED."""
    issues = C.run_all(deck, cfg) if issues is None else issues
    inv = inventory(deck, cfg)
    slides = []
    for sl in deck.slides:
        mine = [i for i in issues if i.slide == sl.no]
        items = [_alignment(deck, sl, cfg, mine), _spacing(deck, sl, cfg, mine), _text_fit(deck, sl, cfg, mine),
                 _lines(deck, sl, cfg, mine), _titles(deck, sl, cfg, mine), _readability(deck, sl, cfg, mine),
                 _leftovers(deck, sl, cfg, mine), _consistency(deck, sl, cfg, mine, inv)]
        assert [i["item"] for i in items] == CATEGORIES
        theme_label = (deck.theme_fonts[1] if len(deck.theme_fonts) > 1 else "(theme font)")
        slides.append(dict(no=sl.no, items=items, elements=elements(deck, sl, theme_label)))
    return dict(slides=slides, inventory=inv, global_limits=GLOBAL_LIMITS, cats=CATEGORIES, w=deck.width, h=deck.height)
