import base64, html, os
from collections import defaultdict
from .config import CATEGORIES

MIN_MANUAL = 1.5    # minutes a human needs per issue the tool cannot fix
MIN_REVIEW = 0.25   # minutes to eyeball an auto-fixed / auto-fixable change


def deck_verdict(before, after):
    """Accept: nothing found. Fix: everything left is <= 5 minutes of work. Reject: more than that."""
    if not before:
        return "Accept", 0.0
    todo = after if after is not None else before
    mins = sum(MIN_MANUAL for i in todo if not i.fixable) \
        + MIN_REVIEW * sum(1 for i in before if i.fixable) \
        + MIN_MANUAL * sum(1 for i in todo if i.fixable and after is not None)   # auto-fix failed -> manual
    return ("Fix" if mins <= 5 else "Reject"), mins


def slide_rows(deck, before, after):
    """Per-slide summary: what passed, what was fixed, what is left."""
    rows = []
    for sl in deck.slides:
        b = [i for i in before if i.slide == sl.no]
        left = [i for i in (after if after is not None else before) if i.slide == sl.no]
        fixed = [i for i in b if i.status == "fixed"]
        failing = {i.category for i in left}
        rows.append(dict(
            slide=sl.no, ok=[c for c in CATEGORIES if c not in failing and c not in {i.category for i in b}],
            clean=[c for c in CATEGORIES if c not in failing],
            fixed=fixed, left=left, found=b,
            status=("clean" if not b else "fixed" if not left else "attention")))
    return rows


def checklist_matrix(deck, issues, before=None):
    by = defaultdict(set)
    for i in issues:
        by[i.slide].add(i.category)
    fixed_by = defaultdict(set)
    for i in (before or []):
        if i.status == "fixed":
            fixed_by[i.slide].add(i.category)
    rows = ["| Slide | " + " | ".join(CATEGORIES) + " |", "|---|" + "---|" * len(CATEGORIES)]
    for sl in deck.slides:
        cells = []
        for c in CATEGORIES:
            cells.append("FAIL" if c in by[sl.no] else "fixed" if c in fixed_by[sl.no] else "ok")
        rows.append(f"| {sl.no} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def markdown(deck, before, after=None, title="Deck QA report"):
    verdict, mins = deck_verdict(before, after)
    out = [f"# {title}", ""]
    out.append(f"Slides: {len(deck.slides)}  |  issues found: {len(before)}")
    if after is not None:
        fixed = sum(1 for i in before if i.status == "fixed")
        out.append(f"Auto-fixed: {fixed}  |  remaining after re-check: {len(after)}")
    out.append(f"Suggested verdict: **{verdict}** (~{mins:.1f} min of human work; "
               "Fix = 5 min or less, Reject = more). This is a hint for the human reviewer.")
    out += ["", "## Per-slide summary", ""]
    out += ["| Slide | State | Found | Auto-fixed | Left for a human | Passing checks |", "|---|---|---|---|---|---|"]
    for r in slide_rows(deck, before, after):
        out.append(f"| {r['slide']} | {r['status']} | {len(r['found'])} | {len(r['fixed'])} | "
                   f"{len(r['left'])} | {len(r['clean'])}/{len(CATEGORIES)} |")
    out += ["", "## Checklist (per slide)", "",
            checklist_matrix(deck, after if after is not None else before, before if after is not None else None), ""]
    if after is not None:
        out += ["## Fixed", ""]
        for i in before:
            if i.status == "fixed":
                out.append(f"- Slide {i.slide} / {i.category}: {i.message}")
        out.append("")
    todo = after if after is not None else before
    out += ["## Needs human attention" if after is not None else "## Issues", ""]
    cur = None
    for i in todo:
        if i.slide != cur:
            cur = i.slide
            out.append(f"### Slide {cur}")
        tag = ("auto-fix could not resolve" if i.fixable else "manual") if after is not None \
            else ("auto-fixable" if i.fixable else "manual")
        out.append(f"- **{i.category}** ({tag}): {i.message}")
    if not todo:
        out.append("Nothing found.")
    return "\n".join(out) + "\n"


def describe_fix(i):
    """One plain-English line saying what the auto-fix did (or would do) for this issue."""
    f = i.fix or {}
    op = f.get("op")
    n = len(f.get("ids", [])) or 1
    return {
        "align": lambda: f"Moved {n} shape(s) so their {f.get('edge')} edge sits on one line ({f.get('target', 0):.0f}pt).",
        "place": lambda: "Moved the icon to match where it sits in the sibling panels / the panel centre.",
        "resize": lambda: "Resized the shape to match its same-size peers.",
        "distribute": lambda: f"Re-spaced {n} shapes evenly along the {f.get('axis')}.",
        "fit": lambda: "Shrank the text, widened or grew the box so the text fits.",
        "title_fit": lambda: "Shrank the title until it fits on two lines (not below 20pt).",
        "min_font": lambda: "Raised the text to the minimum readable size (grew the box if needed).",
        "remove": lambda: "Deleted the empty/leftover shape.",
        "font": lambda: "Set the font back to the deck/theme font.",
        "title_size": lambda: f"Set the title to {f.get('size', 0):g}pt like the other slides.",
        "title_pos": lambda: "Moved the title to the position used on the other slides.",
        "straighten": lambda: "Straightened the line.",
        "add_number": lambda: "Added a page number matching the other slides.",
        "clamp": lambda: "Trimmed the text box so it stays inside its panel.",
    }.get(op, lambda: "")()


def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def html_report(deck, before, after, img_before, img_after, title="Deck QA review"):
    """Self-contained page: per slide the annotated image(s), what passed, what was fixed, what is left."""
    verdict, mins = deck_verdict(before, after)
    css = ("body{font:15px system-ui,sans-serif;margin:0;background:#f4f5f7;color:#1b2030}"
           "header{padding:20px 24px;background:#0c1430;color:#fff}h1{margin:0;font-size:20px}"
           ".sub{opacity:.8;margin-top:6px}.slide{background:#fff;margin:18px auto;max-width:1100px;border-radius:12px;"
           "padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,.1)}.slide h2{margin:0 0 10px;font-size:17px}"
           ".badge{font-size:12px;padding:2px 9px;border-radius:99px;margin-left:8px;color:#fff}"
           ".clean{background:#2e8b57}.fixed{background:#3d53c6}.attention{background:#c0392b}"
           ".imgs{display:flex;gap:12px;flex-wrap:wrap}.imgs figure{margin:0;flex:1 1 440px}"
           "img{width:100%;border:1px solid #d8dbe3;border-radius:6px}figcaption{font-size:12px;color:#555;margin-top:4px}"
           "ul{margin:8px 0;padding-left:20px}.ok{color:#2e8b57}.bad{color:#c0392b}.fx{color:#3d53c6}")
    parts = [f"<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title><style>{css}</style>",
             f"<header><h1>{html.escape(title)}</h1><div class=sub>{len(deck.slides)} slides | "
             f"{len(before)} issues found | suggested verdict: <b>{verdict}</b> (~{mins:.1f} min human work)</div></header>"]
    for r in slide_rows(deck, before, after):
        n = r["slide"]
        parts.append(f"<section class=slide><h2>Slide {n}<span class='badge {r['status']}'>{r['status']}</span></h2>")
        figs = []
        if n in img_before:
            figs.append(("Original (problems circled)", img_before[n]))
        if after is not None and n in img_after:
            figs.append(("After auto-fix (remaining problems circled)", img_after[n]))
        if figs:
            parts.append("<div class=imgs>" + "".join(
                f"<figure><img src='data:image/png;base64,{_b64(p)}'><figcaption>{c}</figcaption></figure>"
                for c, p in figs) + "</div>")
        parts.append("<ul>")
        for i in r["fixed"]:
            parts.append(f"<li class=fx>Fixed - {html.escape(i.category)}: {html.escape(i.message)}</li>")
        for i in r["left"]:
            tag = "auto-fix could not resolve" if (i.fixable and after is not None) else ("auto-fixable" if i.fixable else "manual")
            parts.append(f"<li class=bad>{html.escape(i.category)} ({tag}): {html.escape(i.message)}</li>")
        if r["clean"]:
            parts.append(f"<li class=ok>Passing: {html.escape(', '.join(r['clean']))}</li>")
        parts.append("</ul></section>")
    return "".join(parts)
