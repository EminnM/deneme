import math
from collections import Counter, defaultdict
from statistics import median

from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import MSO_AUTO_SIZE

from .issues import Issue
from .textfit import measure, text_rect, overflow_bottom


def _bbox_union(els):
    return (min(e.left for e in els), min(e.top for e in els),
            max(e.right for e in els), max(e.bottom for e in els))


def _layout_els(els, deck):
    """Boxes that take part in layout checks (no lines, no numbers, no full-slide backgrounds)."""
    return [e for e in els if e.kind in ("text", "picture", "frame", "shape", "group")
            and not e.is_number
            and not (e.is_placeholder and e.kind == "shape" and not e.text.strip())   # empty placeholders are not content
            and not (e.width > deck.width * 0.95 and e.height > deck.height * 0.95)]


def _content(sl, deck):
    """Leaf shapes for collision checks (groups are expanded, containers excluded)."""
    return [e for e in _layout_els(sl.leaves, deck)]


def _clusters(vals, tol):
    """vals: list of (value, el). Anchored clustering: every member within tol of the cluster's first."""
    vals = sorted(vals, key=lambda v: v[0])
    out, cur = [], [vals[0]] if vals else []
    for v in vals[1:]:
        if v[0] - cur[0][0] <= tol:
            cur.append(v)
        else:
            out.append(cur)
            cur = [v]
    if cur:
        out.append(cur)
    return out


def _similar(a, b, tol):
    return abs(a.width - b.width) <= tol * max(a.width, b.width) and \
        abs(a.height - b.height) <= tol * max(a.height, b.height)


def _peer_sets(els, tol):
    sets = []
    for e in sorted(els, key=lambda x: (x.width, x.height)):
        for s in sets:
            if _similar(s[0], e, tol):
                s.append(e)
                break
        else:
            sets.append([e])
    return [s for s in sets if len(s) >= 3]


def _components(items, linked):
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if linked(items[i], items[j]):
                parent[find(i)] = find(j)
    comps = defaultdict(list)
    for i, it in enumerate(items):
        comps[find(i)].append(it)
    return [c for c in comps.values() if len(c) >= 3]


def _outliers(comp, key, cfg, limit):
    """Majority share one position; return (target, outliers). Needs a clear majority."""
    cl = max(_clusters([(key(e), e) for e in comp], cfg.peer_pos_tol), key=len)
    if len(cl) < max(2, math.ceil(len(comp) / 2)):
        return None, []
    target = median(v for v, _ in cl)
    inn = {id(e) for _, e in cl}
    out = [e for e in comp if id(e) not in inn and cfg.align_eps < abs(key(e) - target) <= limit]
    return target, out


# ---------------------------------------------------------------- 1 Alignment
def _peer_alignment(sl, deck, cfg, els, edge_sets, out, skip=frozenset()):
    """Same-size shapes laid out as a row/column: a shape that stands alone off the line shared by
    two or more of its peers is flagged, whatever the distance (up to 1.5x its size)."""
    for ps in _peer_sets([e for e in els if e.kind != "line"], cfg.peer_size_tol):
        for axis in ("row", "col"):
            key = (lambda e: e.top) if axis == "row" else (lambda e: e.left)
            span = max(e.height for e in ps) if axis == "row" else max(e.width for e in ps)
            buckets = [[e for _, e in c] for c in _clusters([(key(e), e) for e in ps], cfg.peer_pos_tol)]
            anchors = [b for b in buckets if len(b) >= 2]
            if not anchors:
                continue

            def beside(e, grp):   # side by side (row) / stacked (col): no overlap along the layout axis
                for o in grp:
                    if axis == "row" and min(e.right, o.right) - max(e.left, o.left) > 0.5:
                        return False
                    if axis == "col" and min(e.bottom, o.bottom) - max(e.top, o.top) > 0.5:
                        return False
                return True
            groups = defaultdict(list)
            for b in buckets:
                if len(b) != 1 or b[0].id in skip:
                    continue
                e = b[0]
                near = [a for a in anchors if 0 < abs(key(e) - median(key(x) for x in a)) <= 1.5 * span and beside(e, a)]
                if near:
                    best = min(near, key=lambda a: abs(key(e) - median(key(x) for x in a)))
                    groups[id(best)].append((e, best))
            for items in groups.values():
                best = items[0][1]
                target = median(key(x) for x in best)
                odd = [e for e, _ in items if abs(key(e) - target) > cfg.align_eps]
                if not odd:
                    continue
                edge = "top" if axis == "row" else "left"
                edge_sets.append(((("top", "bottom") if axis == "row" else ("left", "right", "center")),
                                  frozenset(x.id for x in best + odd)))
                word = "row" if axis == "row" else "column"
                out.append(Issue(sl.no, "Alignment",
                                 f"{len(odd)} of {len(best) + len(odd)} same-size shapes in a {word} are off the shared "
                                 f"{edge} line ({', '.join(f'{key(e) - target:+.0f}pt' for e in odd)}).",
                                 [e.id for e in odd], _bbox_union(odd), True,
                                 dict(op="align", edge=edge, target=target, ids=[e.id for e in odd])))


def _size_mismatch(sl, cfg, els, out):
    """Cards/pictures that are almost, but not exactly, the size of their peers."""
    solid = [e for e in els if e.kind in ("picture", "frame") or (e.kind == "shape" and e.fill is not None)]
    for ps in _peer_sets(solid, cfg.peer_size_tol):
        for dim, label in (("width", "wide"), ("height", "tall")):
            vals = [(getattr(e, dim), e) for e in ps]
            cl = max(_clusters(vals, cfg.peer_pos_tol), key=len)
            if len(cl) < max(2, math.ceil(len(ps) / 2)):
                continue
            target = median(v for v, _ in cl)
            inn = {id(e) for _, e in cl}
            for v, e in vals:
                if id(e) not in inn and abs(v - target) > cfg.align_eps:
                    out.append(Issue(sl.no, "Alignment",
                                     f"'{e.name}' is {abs(v - target):.0f}pt too {'wide' if (dim == 'width' and v > target) else 'narrow' if dim == 'width' else 'tall' if v > target else 'short'}"
                                     f" compared with its {len(ps) - 1} same-size peers.",
                                     [e.id], e.bbox, e.kind != "picture" and True,
                                     dict(op="resize", id=e.id, **{dim: target})))


def _icon_ids(sl, cfg):
    """Icons: pictures, or small text-free groups, below icon_max in size."""
    icons = []
    for e in sl.all:
        if max(e.width, e.height) > cfg.icon_max or min(e.width, e.height) < 6:
            continue
        if e.kind == "picture" or (e.kind == "group" and not e.group_has_text and e.n_leaves >= 1):
            icons.append(e)
    icon_groups = {e.id for e in icons if e.kind == "group"}
    return [e for e in icons if e.parent not in icon_groups]   # skip parts of an icon group


def _icon_alignment(sl, deck, cfg, out):
    icons = _icon_ids(sl, cfg)
    icon_set = {e.id for e in icons}
    panels = [e for e in sl.leaves if e.kind in ("shape", "text") and e.id not in icon_set
              and not e.is_title and not e.is_number]
    pairs = []
    for ic in icons:
        best = None
        for p in panels:
            if p.width * p.height < 1.8 * ic.width * ic.height:
                continue
            if p.left - 1 <= ic.left and p.top - 1 <= ic.top and p.right + 1 >= ic.right and p.bottom + 1 >= ic.bottom:
                if best is None or p.width * p.height < best.width * best.height:
                    best = p
        if best:
            pairs.append((ic, best))
    flagged = set()
    # sibling panels of the same size: the icon should sit at the same offset in each
    by_size = []
    for ic, p in pairs:
        for grp in by_size:
            if _similar(grp[0][1], p, cfg.peer_size_tol):
                grp.append((ic, p))
                break
        else:
            by_size.append([(ic, p)])
    for grp in by_size:
        if len(grp) < 3:
            continue
        offs = [(ic.left - p.left, ic.top - p.top, ic, p) for ic, p in grp]
        cl = max(_clusters([(o[0] + 1000 * o[1], o) for o in offs], 0.0), key=len)  # exact-offset buckets
        # bucket by rounded offset instead (x and y together)
        buckets = defaultdict(list)
        for o in offs:
            buckets[(round(o[0] / cfg.icon_offset_tol), round(o[1] / cfg.icon_offset_tol))].append(o)
        main = max(buckets.values(), key=len)
        if len(main) < max(2, math.ceil(len(offs) / 2)):
            continue
        mdx, mdy = median(o[0] for o in main), median(o[1] for o in main)
        for dx, dy, ic, p in offs:
            if ic.id in {m[2].id for m in main}:
                continue
            ex, ey = dx - mdx, dy - mdy
            if max(abs(ex), abs(ey)) <= cfg.align_eps or max(abs(ex), abs(ey)) > 0.4 * max(p.width, p.height):
                continue
            flagged.add(ic.id)
            out.append(Issue(sl.no, "Alignment",
                             f"Icon '{ic.name}' sits {ex:+.0f},{ey:+.0f}pt from where the icon sits in sibling panels.",
                             [ic.id, p.id], _bbox_union([ic, p]), True,
                             dict(op="place", id=ic.id, left=p.left + mdx, top=p.top + mdy)))
    # icon nearly (but not quite) centred on its panel
    for ic, p in pairs:
        if ic.id in flagged:
            continue
        dx, dy = ic.cx - p.cx, ic.cy - p.cy
        fix = {}
        if cfg.icon_center_tol < abs(dx) <= 0.1 * p.width:
            fix["left"] = p.cx - ic.width / 2
        if cfg.icon_center_tol < abs(dy) <= 0.1 * p.height:
            fix["top"] = p.cy - ic.height / 2
        if fix:
            out.append(Issue(sl.no, "Alignment",
                             f"Icon '{ic.name}' is {dx:+.1f},{dy:+.1f}pt off the centre of its panel.",
                             [ic.id, p.id], _bbox_union([ic, p]), True, dict(op="place", id=ic.id, **fix)))


def _contains(a, b, pad=1.0):
    return a.left - pad <= b.left and a.top - pad <= b.top and a.right + pad >= b.right and a.bottom + pad >= b.bottom


def alignment(deck, cfg):
    out = []
    edges = {"left": lambda e: e.left, "right": lambda e: e.right, "top": lambda e: e.top,
             "bottom": lambda e: e.bottom, "center": lambda e: e.cx}
    for sl in deck.slides:
        # peers are compared slide-wide: the same tab in six different groups must still line up
        leaves = [e for e in _layout_els(sl.leaves, deck) if not e.is_title]
        edge_sets = []
        icon_issues = []
        _icon_alignment(sl, deck, cfg, icon_issues)
        icon_ids = {i for iss in icon_issues for i in iss.ids}
        _peer_alignment(sl, deck, cfg, leaves, edge_sets, out, icon_ids)
        _size_mismatch(sl, cfg, leaves, out)
        near = []   # (edge, spread, issue) collected, then thinned: a repeated offset is a design system
        for parent, kids in sl.siblings().items():
            els = [e for e in _layout_els(kids, deck) if not e.is_title]
            seen = set()  # same shapes already reported on another edge -> don't repeat
            for edge, fn in edges.items():
                if len(els) < 2:
                    continue
                for cl in _clusters([(fn(e), e) for e in els], cfg.align_tol):
                    vs = [v for v, _ in cl]
                    if len(cl) < 2 or max(vs) - min(vs) <= cfg.align_eps:
                        continue
                    members = [e for _, e in cl]
                    # a label inset inside its panel is deliberate, not a near-miss
                    members = [m for m in members if not any(o is not m and _contains(o, m) for o in members)]
                    if len(members) < 2:
                        continue
                    vs = [fn(e) for e in members]
                    if max(vs) - min(vs) <= cfg.align_eps:
                        continue
                    target = median(vs)
                    key = frozenset(e.id for e in members)
                    if key in seen or any(edge in es and key <= ids for es, ids in edge_sets):
                        continue
                    seen.add(key)
                    near.append(((edge, round(max(vs) - min(vs), 1), len(members)), Issue(
                        sl.no, "Alignment",
                        f"{edge} edges of {len(members)} shapes are off by up to "
                        f"{max(vs) - min(vs):.1f}pt (should share one {edge} line).",
                        [e.id for e in members], _bbox_union(members), True,
                        dict(op="align", edge=edge, target=target, ids=[e.id for e in members]))))
        sig = Counter(k for k, _ in near)
        out.extend(i for k, i in near if sig[k] < 3)
        _icon_alignment(sl, deck, cfg, out)
    return out


# ----------------------------------------------------------------- 2 Spacing
def _overlap_rect(a, b):
    l, t = max(a[0], b[0]), max(a[1], b[1])
    r, bt = min(a[2], b[2]), min(a[3], b[3])
    return (l, t, r, bt) if r > l and bt > t else None


def _same_art_group(a, b, sl_by_id):
    return a.parent is not None and a.parent == b.parent and not sl_by_id[a.parent].group_has_text


def overlaps(deck, cfg):
    """Content that physically collides (text over text, text over picture)."""
    out = []
    for sl in deck.slides:
        by_id = {e.id: e for e in sl.all}
        items = []
        for e in sl.leaves:
            if e.is_title or e.is_number or e.kind not in ("text", "picture", "frame"):
                continue
            rect = text_rect(e, cfg) if e.kind == "text" else e.bbox
            items.append((e, rect))
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (a, ra), (b, rb) = items[i], items[j]
                if _same_art_group(a, b, by_id):
                    continue
                ov = _overlap_rect(ra, rb)
                if not ov and a.kind == "text" and b.kind == "text":
                    pad = 3.0   # not overlapping, but practically touching
                    if _overlap_rect((ra[0] - pad, ra[1] - pad, ra[2] + pad, ra[3] + pad), rb):
                        out.append(Issue(sl.no, "Spacing",
                                         f"Text blocks '{a.text.strip()[:20]}..' and '{b.text.strip()[:20]}..' nearly touch (<{pad:g}pt).",
                                         [a.id, b.id], _bbox_union([a, b]), False))
                    continue
                if not ov:
                    continue
                w, h = ov[2] - ov[0], ov[3] - ov[1]
                if min(w, h) < cfg.overlap_min:
                    continue
                area = w * h
                small = min((ra[2] - ra[0]) * (ra[3] - ra[1]), (rb[2] - rb[0]) * (rb[3] - rb[1]))
                if small <= 0:
                    continue
                share = area / small
                both_text = a.kind == "text" and b.kind == "text"
                if both_text:
                    if min(w, h) < 2.0 or area < 30:
                        continue
                elif "frame" in (a.kind, b.kind):
                    if min(w, h) < 6 or area < 300:     # tables/charts: even a thin overlap is a defect
                        continue
                elif share < 0.3:
                    continue
                label = lambda e: (e.text.strip().replace("\n", " ")[:24] + "..") if e.kind == "text" else e.name
                out.append(Issue(sl.no, "Spacing",
                                 f"'{label(a)}' overlaps '{label(b)}' ({w:.0f} x {h:.0f}pt, {share:.0%} of the smaller).",
                                 [a.id, b.id], _bbox_union([a, b]), False))
    return out


def spacing(deck, cfg):
    out = []
    for sl in deck.slides:
        els = [e for e in _layout_els(sl.els, deck) if not e.is_title]
        # uneven gaps in rows and columns
        for axis in ("row", "col"):
            used = set()
            for e in els:
                if id(e) in used:
                    continue
                grp = [o for o in els if (
                    (min(e.bottom, o.bottom) - max(e.top, o.top) > min(e.height, o.height) * 0.5) if axis == "row"
                    else (min(e.right, o.right) - max(e.left, o.left) > min(e.width, o.width) * 0.5))]
                for g in grp:
                    used.add(id(g))
                if len(grp) < 3:
                    continue
                grp.sort(key=lambda s: s.left if axis == "row" else s.top)
                gaps = [(grp[i + 1].left - grp[i].right) if axis == "row" else (grp[i + 1].top - grp[i].bottom)
                        for i in range(len(grp) - 1)]
                if any(g < -0.5 for g in gaps):
                    continue  # overlapping layout, not a spacing row
                # members must really line up as a row/column, or "distributing" them would scatter unrelated shapes
                cross = [(g.cy if axis == "row" else g.cx) for g in grp]
                span = max((g.height if axis == "row" else g.width) for g in grp)
                if max(cross) - min(cross) > 0.35 * span:
                    continue
                if max(gaps) - min(gaps) > cfg.gap_tol:
                    out.append(Issue(
                        sl.no, "Spacing",
                        f"Uneven gaps in a {axis} of {len(grp)} shapes "
                        f"({', '.join(f'{g:.0f}' for g in gaps)}pt).",
                        [s.id for s in grp], _bbox_union(grp), True,
                        dict(op="distribute", axis=axis, ids=[s.id for s in grp])))
        # empty band
        if els:
            srt = sorted(els, key=lambda s: s.top)
            reach = srt[0].bottom
            for s in srt[1:]:
                if s.top - reach > deck.height * cfg.band_ratio:
                    out.append(Issue(sl.no, "Spacing",
                                     f"Empty horizontal band of {s.top - reach:.0f}pt between content blocks.",
                                     [s.id], (0, reach, deck.width, s.top)))
                reach = max(reach, s.bottom)
    out.extend(overlaps(deck, cfg))
    return out


# ---------------------------------------------------------------- 3 Text fit
def text_fit(deck, cfg):
    out = []
    for sl in deck.slides:
        for e in sl.leaves:
            if e.kind != "text" or e.is_number or e.is_title:
                continue  # titles are judged by the Titles check
            tf = e.shape.text_frame
            m = measure(e, cfg)
            if tf.word_wrap is not False and m["split"]:
                out.append(Issue(sl.no, "Text fit", "A word is wider than its box and will split mid-word.",
                                 [e.id], e.bbox, True, dict(op="fit", id=e.id)))
            auto = tf.auto_size in (MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT, MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE)
            if overflow_bottom(e, cfg) > e.height + 1.0 and not auto and e.height >= 1.0:  # height 0 = auto-growing box
                out.append(Issue(sl.no, "Text fit",
                                 f"Text needs ~{overflow_bottom(e, cfg):.0f}pt but box is {e.height:.0f}pt tall (spills out).",
                                 [e.id], e.bbox, True, dict(op="fit", id=e.id)))
            elif m["orphan"]:
                out.append(Issue(sl.no, "Text fit", "Last line has a single hanging word.",
                                 [e.id], e.bbox, False))
    return out


def panel_fit(deck, cfg):
    """Text that pokes out of the filled panel/card it sits on."""
    out = []
    for sl in deck.slides:
        panels = [p for p in sl.leaves if p.kind == "shape" and not p.text.strip() and p.fill is not None
                  and min(p.width, p.height) >= 20 and not (p.width > deck.width * 0.9 and p.height > deck.height * 0.9)]
        for t in (e for e in sl.leaves if e.kind == "text" and not e.is_title and not e.is_number):
            host = [p for p in panels if p.left <= t.cx <= p.right and p.top <= t.top + min(t.height, 30) / 2 <= p.bottom
                    and p.width * p.height >= 0.5 * t.width * t.height and p.id != t.id]
            if not host:
                continue
            p = min(host, key=lambda x: x.width * x.height)
            if t.left < p.left - 2 or t.right > p.right + 2:
                out.append(Issue(sl.no, "Text fit",
                                 f"Text box is wider than its panel by {max(p.left - t.left, t.right - p.right):.0f}pt.",
                                 [t.id, p.id], _bbox_union([t, p]), True,
                                 dict(op="clamp", id=t.id, l=p.left, r=p.right)))
            ink = text_rect(t, cfg)
            if ink[3] > p.bottom + 1:
                out.append(Issue(sl.no, "Text fit",
                                 f"Text runs {ink[3] - p.bottom:.0f}pt past the bottom of its panel.",
                                 [t.id, p.id], _bbox_union([t, p]), False))
    return out


# --------------------------------------------------------- 4 Lines and arrows
def _seg_hits_rect(x1, y1, x2, y2, r):
    l, t, rr, b = r
    # Liang-Barsky
    dx, dy = x2 - x1, y2 - y1
    p = [-dx, dx, -dy, dy]
    q = [x1 - l, rr - x1, y1 - t, b - y1]
    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return False
        else:
            t_ = qi / pi
            if pi < 0:
                u1 = max(u1, t_)
            else:
                u2 = min(u2, t_)
    return u1 < u2 and (u2 - u1) > 0.02


def _inside(x, y, r, pad):
    return r[0] - pad <= x <= r[2] + pad and r[1] - pad <= y <= r[3] + pad


def lines_arrows(deck, cfg):
    out = []
    for sl in deck.slides:
        texts = [e for e in sl.leaves if e.kind == "text" and not e.is_number]
        for ln in (e for e in sl.leaves if e.kind == "line"):
            x1, y1, x2, y2 = ln.line
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 1:
                continue
            ang = math.degrees(math.atan2(abs(dy), abs(dx)))  # 0 horiz .. 90 vert
            off = min(ang, 90 - ang)
            if 0.2 < off <= cfg.angle_tol:
                out.append(Issue(sl.no, "Lines and arrows", f"Line is {off:.1f} degrees off the horizontal/vertical (crooked).",
                                 [ln.id], ln.bbox, True, dict(op="straighten", id=ln.id)))
            hit = []
            for t in texts:
                r = (t.left + 2, t.top + 2, t.right - 2, t.bottom - 2)
                if _inside(x1, y1, t.bbox, 2) or _inside(x2, y2, t.bbox, 2):
                    continue  # attached to the box, not crossing it
                if _seg_hits_rect(x1, y1, x2, y2, r):
                    hit.append(t)
            if hit:
                names = ", ".join(f"'{t.text.strip()[:18]}'" for t in hit[:3])
                out.append(Issue(sl.no, "Lines and arrows",
                                 f"A line crosses through {len(hit)} text box(es): {names}{'...' if len(hit) > 3 else ''}.",
                                 [ln.id] + [t.id for t in hit], _bbox_union([ln] + hit)))
    return out


# -------------------------------------------------------------------- 5 Titles
def titles(deck, cfg):
    out = []
    for sl in deck.slides:
        for t in (e for e in sl.leaves if e.is_title and e.kind == "text"):
            m = measure(t, cfg)
            if m["lines"] > cfg.title_max_lines:
                out.append(Issue(sl.no, "Titles", f"Title wraps to ~{m['lines']} lines (max {cfg.title_max_lines}).",
                                 [t.id], t.bbox, True, dict(op="title_fit", id=t.id)))
            tl, tt, tr, tb = text_rect(t, cfg)
            tight = []
            for o in _content(sl, deck):
                if o is t or o.is_title:
                    continue
                bare = o.kind == "shape" and not o.text.strip()
                if bare and (o.fill is None or o.top < tt):
                    continue  # panels/outlines behind a title are background, not content
                horiz = min(tr, o.right) - max(tl, o.left)
                if horiz <= 0 or o.bottom <= tt:
                    continue
                oy = text_rect(o, cfg)[1] if o.kind == "text" else o.top
                if oy < tb - 0.5 and not bare:
                    out.append(Issue(sl.no, "Titles", f"Title collides with '{o.name}'.",
                                     [t.id, o.id], _bbox_union([t, o])))
                elif oy - tb < cfg.title_gap and oy >= tb - 0.5 and o.top > t.top:
                    tight.append((oy - tb, o))
            if tight:
                gap, nearest = min(tight, key=lambda x: x[0])
                more = f" and {len(tight) - 1} other shape(s)" if len(tight) > 1 else ""
                out.append(Issue(sl.no, "Titles",
                                 f"Title text is only {gap:.1f}pt above '{nearest.name}'{more} (min {cfg.title_gap:g}pt).",
                                 [t.id] + [o.id for _, o in tight], _bbox_union([t] + [o for _, o in tight])))
    return out


# --------------------------------------------------------------- 6 Readability
def readability(deck, cfg):
    out = []
    for sl in deck.slides:
        for e in sl.leaves:
            if e.kind != "text":
                continue
            small = [s for s in e.sizes if s < cfg.min_font]
            if small:
                out.append(Issue(sl.no, "Readability",
                                 f"Text is {min(small):g}pt (minimum {cfg.min_font:g}pt).",
                                 [e.id], e.bbox, True, dict(op="min_font", id=e.id)))
    return out


# ------------------------------------------------------------ 7 Leftover graphics
def _grey_or_black(rgb):
    if rgb is None:
        return False
    r, g, b = rgb
    return max(r, g, b) - min(r, g, b) <= 14


_AUTO_PH = (PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.DATE, PP_PLACEHOLDER.SLIDE_NUMBER)


def leftovers(deck, cfg):
    out = []
    for sl in deck.slides:
        for e in sl.leaves:
            if e.kind == "picture" or e.kind == "line":
                continue
            if e.left + e.width < 0 or e.top + e.height < 0 or e.left > deck.width or e.top > deck.height:
                out.append(Issue(sl.no, "Leftover graphics", f"'{e.name}' sits completely off the slide.",
                                 [e.id], e.bbox, True, dict(op="remove", id=e.id)))
                continue
            if e.kind == "shape" and not e.text.strip():
                if e.is_placeholder and e.ph_type in _AUTO_PH:
                    continue  # footer/date/number placeholders are empty by design
                if e.is_placeholder:
                    out.append(Issue(sl.no, "Leftover graphics", f"Empty placeholder '{e.name}'.",
                                     [e.id], e.bbox, True, dict(op="remove", id=e.id)))
                elif not e.in_group and min(e.width, e.height) >= 6 and e.fill is not None:
                    why = "grey/black box" if _grey_or_black(e.fill) else "coloured blob"
                    out.append(Issue(sl.no, "Leftover graphics",
                                     f"Empty {why} '{e.name}' with no text or content.",
                                     [e.id], e.bbox, True, dict(op="remove", id=e.id)))
    return out


# -------------------------------------------------------------- 8 Consistency
def consistency(deck, cfg):
    out = []
    # fonts (an explicit font equal to the theme font counts as the theme font)
    tf = set(deck.theme_fonts) | {"+mn-lt", "+mj-lt"}
    norm = lambda f: "<theme>" if f in tf else f
    fonts = Counter(norm(f) for sl in deck.slides for e in sl.leaves for f in e.fonts)
    fonts["<theme>"] += sum(e.implicit_runs for sl in deck.slides for e in sl.leaves)
    if fonts:
        dom = fonts.most_common(1)[0][0]
        label = "the theme font" if dom == "<theme>" else dom
        for sl in deck.slides:
            for e in sl.leaves:
                odd = sorted({f for f in e.fonts if norm(f) != dom})
                if odd:
                    out.append(Issue(sl.no, "Consistency",
                                     f"Font {', '.join(odd)} differs from {label}.",
                                     [e.id], e.bbox, True,
                                     dict(op="font", id=e.id, font=None if dom == "<theme>" else dom)))
    # body text size: same-size text boxes (e.g. the columns of one slide) should use the same size
    for sl in deck.slides:
        texts = [e for e in sl.leaves if e.kind == "text" and not e.is_title and not e.is_number and e.sizes]
        for ps in _peer_sets(texts, cfg.peer_size_tol):
            cl = max(_clusters([(e.size, e) for e in ps], 0.5), key=len)
            if len(cl) < max(2, math.ceil(len(ps) / 2)):
                continue
            tgt = median(v for v, _ in cl)
            for e in ps:
                if abs(e.size - tgt) >= 1.0:
                    out.append(Issue(sl.no, "Consistency",
                                     f"Text is {e.size:g}pt but {len(cl)} same-size boxes on this slide use {tgt:g}pt.",
                                     [e.id], e.bbox, False))
    # title size: compare across all content slides (title-slide layouts excluded)
    content_titles = [(sl, e) for sl in deck.slides for e in sl.leaves if e.is_title and e.kind == "text"
                      and not any(x.ph_type == PP_PLACEHOLDER.CENTER_TITLE for x in sl.leaves)]
    if len(content_titles) >= 3:
        dom_size = Counter(e.size for _, e in content_titles).most_common(1)[0][0]
        for sl, e in content_titles:
            shrunk = e.size < dom_size and measure(e, cfg, dom_size)["lines"] > cfg.title_max_lines
            if e.size != dom_size and not shrunk:
                out.append(Issue(sl.no, "Consistency",
                                 f"Title is {e.size:g}pt; most other slides use {dom_size:g}pt.",
                                 [e.id], e.bbox, True, dict(op="title_size", id=e.id, size=dom_size)))
    # title position: only against slides sharing the same layout
    by_layout = defaultdict(list)
    for sl in deck.slides:
        for e in sl.leaves:
            if e.is_title and e.kind == "text":
                by_layout[sl.layout].append((sl, e))
    for layout, ts in by_layout.items():
        if len(ts) < 3:
            continue
        dom_pos = Counter((round(e.left), round(e.top)) for _, e in ts).most_common(1)[0][0]
        for sl, e in ts:
            if max(abs(e.left - dom_pos[0]), abs(e.top - dom_pos[1])) > cfg.pos_tol:
                out.append(Issue(sl.no, "Consistency",
                                 f"Title position ({e.left:.0f},{e.top:.0f}) differs from other '{layout}' slides {dom_pos}.",
                                 [e.id], e.bbox, True, dict(op="title_pos", id=e.id, pos=dom_pos)))
    # page numbers: present on all or none (title slide exempt)
    body = deck.slides[1:] if len(deck.slides) > 2 else deck.slides
    have = [sl for sl in body if any(e.is_number for e in sl.all)]
    if have and len(have) < len(body) and len(have) >= len(body) / 2:
        ref = next(e for e in have[0].all if e.is_number)
        for sl in body:
            if sl not in have:
                out.append(Issue(sl.no, "Consistency", "Slide has no page number but other slides do.",
                                 [], (ref.left, ref.top, ref.right, ref.bottom), True,
                                 dict(op="add_number", ref=(ref.left, ref.top, ref.width, ref.height))))
    return out


ALL = [alignment, spacing, text_fit, panel_fit, lines_arrows, titles, readability, leftovers, consistency]


def run_all(deck, cfg):
    issues = []
    for fn in ALL:
        issues.extend(fn(deck, cfg))
    return sorted(issues, key=lambda i: (i.slide, i.category))
