from collections import defaultdict
from .config import CATEGORIES


def checklist_matrix(deck, issues):
    by = defaultdict(set)
    for i in issues:
        by[i.slide].add(i.category)
    rows = ["| Slide | " + " | ".join(CATEGORIES) + " |", "|---|" + "---|" * len(CATEGORIES)]
    for sl in deck.slides:
        rows.append(f"| {sl.no} | " + " | ".join("FAIL" if c in by[sl.no] else "ok" for c in CATEGORIES) + " |")
    return "\n".join(rows)


def markdown(deck, before, after=None, title="Deck QA report"):
    out = [f"# {title}", ""]
    out.append(f"Slides: {len(deck.slides)}  |  issues found: {len(before)}")
    if after is not None:
        fixed = sum(1 for i in before if i.status == "fixed")
        out.append(f"Auto-fixed: {fixed}  |  remaining after re-check: {len(after)}")
    out += ["", "## Checklist (per slide)", "", checklist_matrix(deck, after if after is not None else before), ""]
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
        tag = ("auto-fix could not resolve" if i.fixable else "manual") if after is not None else ("auto-fixable" if i.fixable else "manual")
        out.append(f"- **{i.category}** ({tag}): {i.message}")
    if not todo:
        out.append("Nothing found.")
    return "\n".join(out) + "\n"
