"""Plain-English explanations of each issue: what is wrong, where, why it matters, how to fix it.
Also builds reviewer notes in the terse style graders are asked for ("Slide 2: icons misaligned")."""
import re
from collections import OrderedDict, defaultdict

# (regex on Issue.message, short label, why it matters, how to fix, severity)
RULES = [
    (r"same-size shapes in a (row|column) are off the shared", "shapes misaligned in a {0}",
     "Elements that belong together should sit on one line; one stray element breaks the grid and looks careless.",
     "Move the stray shape onto the line the others share.", "medium"),
    (r"edges of \d+ shapes are off by up to", "edges slightly misaligned",
     "A near-miss of a few points is visible as a wobble but looks accidental rather than designed.",
     "Snap the edges to one common line.", "low"),
    (r"Icon .* sits .* from where the icon sits", "icon misaligned vs the other icons",
     "Icons repeated across panels must sit in the same spot, otherwise the slide looks uneven.",
     "Move the icon to the same offset as in the sibling panels.", "medium"),
    (r"off the centre of its panel", "icon not centred on its panel",
     "An icon that is almost, but not quite, centred reads as a mistake.",
     "Centre the icon on its panel.", "low"),
    (r"too (wide|narrow|tall|short) compared with", "same-size cards/shapes are different sizes",
     "Peers in a set should be identical in size; small differences look like errors.",
     "Resize it to match its peers.", "low"),
    (r"Uneven gaps", "uneven spacing between elements",
     "Unequal gaps between items in a row or column look unplanned.",
     "Redistribute the items so every gap is equal.", "medium"),
    (r"overlaps '", "elements overlap",
     "Overlapping content hides text or graphics and makes the slide hard to read.",
     "Move or resize one of them so they no longer overlap.", "high"),
    (r"nearly touch", "text blocks almost touching",
     "Text with no breathing room looks cramped and can collide once edited.",
     "Add space between the blocks or narrow one of them.", "medium"),
    (r"Empty horizontal band", "large empty gap on the slide",
     "A big unexplained gap makes the layout look unbalanced or unfinished.",
     "Redistribute the content or fill/reduce the gap.", "low"),
    (r"Text needs .*spills out", "text overflows its box",
     "Text running outside its container can be clipped or collide with other elements.",
     "Shrink the text, shorten it, or enlarge the box.", "high"),
    (r"word is wider than its box", "word breaks mid-word",
     "A word split across lines is a typographic error and hard to read.",
     "Widen the box or reduce the font size.", "high"),
    (r"single hanging word", "single word hanging on the last line (orphan)",
     "A lone word on the last line looks unpolished.",
     "Reword or resize so the last line has more than one word.", "low"),
    (r"wider than its panel", "text box sticks out of its panel",
     "Text should stay inside the card or panel it belongs to.",
     "Trim the text box to the panel width.", "medium"),
    (r"past the bottom of its panel", "text runs past the bottom of its panel",
     "Text hanging outside its card looks broken and may overlap what is below.",
     "Shorten the text or enlarge the panel.", "high"),
    (r"degrees off the horizontal/vertical", "line/arrow is crooked",
     "A line that is a few degrees off looks like a mistake rather than a design choice.",
     "Straighten the line so it is exactly horizontal or vertical.", "low"),
    (r"A line crosses through", "line crosses through text",
     "A line through text makes the text hard to read.",
     "Move the line or the text so they do not intersect.", "high"),
    (r"Title wraps to", "title too long (more than 2 lines)",
     "Long titles crowd the slide and push into the content.",
     "Shorten the title to at most two lines.", "medium"),
    (r"Title collides with", "title overlaps the content",
     "A title crashing into content makes both hard to read.",
     "Move the content down or shorten/shrink the title.", "high"),
    (r"Title text is only", "title too close to the content below",
     "A title with no clear space above the content looks cramped.",
     "Add at least 6pt of space under the title.", "medium"),
    (r"Text is [\d.]+pt \(minimum", "text too small to read",
     "Text under about 10pt is unreadable when presented.",
     "Increase the font size or cut the text.", "medium"),
    (r"grey/black box", "leftover grey/black box",
     "An empty box with no content is a forgotten placeholder.", "Delete it.", "medium"),
    (r"coloured blob", "leftover coloured shape",
     "An empty coloured shape with no purpose looks like a stray artefact.", "Delete it.", "medium"),
    (r"Empty placeholder", "empty placeholder left on the slide",
     "An empty placeholder can show 'Click to add text' to the audience.", "Fill or delete it.", "medium"),
    (r"sits completely off the slide", "shape left off the slide",
     "A shape outside the slide is a forgotten leftover.", "Delete it or move it onto the slide.", "low"),
    (r"^Font .* differs from", "inconsistent font",
     "Mixed fonts make a deck look stitched together.", "Use the deck's font.", "medium"),
    (r"Title is [\d.]+pt; (other|most)", "title size inconsistent across slides",
     "Titles should look the same on every slide.", "Set the title to the size used on the other slides.", "medium"),
    (r"Title position", "title position inconsistent across slides",
     "A title that jumps position between slides looks sloppy when paging through.",
     "Put the title in the same position as the other slides.", "medium"),
    (r"no page number", "page number missing on this slide",
     "Page numbers should be on every slide or on none.", "Add the page number like on the other slides.", "low"),
    (r"Fill colour .* slightly different shade", "shape colour slightly off from its matching shapes",
     "A shade that is almost, but not exactly, the same is invisible to the eye in isolation but shows as a mismatch across a set.",
     "Set it to exactly the same colour as the other shapes in the set.", "medium"),
    (r"Text colour .* slightly different shade", "text colour slightly off from matching text",
     "Near-identical text colours look like a theme mistake and break consistency.",
     "Use exactly the same text colour as the others.", "low"),
    (r"Text block sits .* sibling panels", "text block positioned differently from the same text in sibling panels",
     "Repeated panels should place their text identically; a few points of drift reads as sloppy.",
     "Move the text to the same offset as in the other panels.", "medium"),
    (r"same-size boxes on this slide use", "text size inconsistent between similar boxes",
     "Similar text boxes (e.g. columns) should use the same font size.", "Use the same font size in all of them.", "medium"),
]
_COMPILED = [(re.compile(r), l, w, f, s) for r, l, w, f, s in RULES]
GENERIC = ("issue", "Does not meet the checklist item.", "Review and correct it.", "medium")


def where(bbox, W, H):
    if not bbox:
        return "slide-wide"
    cx, cy = (bbox[0] + bbox[2]) / 2 / W, (bbox[1] + bbox[3]) / 2 / H
    wide = (bbox[2] - bbox[0]) / W > 0.6
    v = "top" if cy < 0.33 else "middle" if cy < 0.67 else "bottom"
    h = "left" if cx < 0.33 else "centre" if cx < 0.67 else "right"
    return f"across the {v} of the slide" if wide else f"{v} {h}" if v != "middle" or h != "centre" else "centre of the slide"


def explain(issue, W=960, H=540):
    msg = issue.message
    for rx, label, why, fix, sev in _COMPILED:
        m = rx.search(msg)
        if m:
            label = label.format(*m.groups()) if m.groups() else label
            return dict(item=issue.category, label=label, where=where(issue.bbox, W, H), what=msg,
                        why=why, fix=fix, severity=sev)
    return dict(item=issue.category, label=GENERIC[0], where=where(issue.bbox, W, H), what=msg,
                why=GENERIC[1], fix=GENERIC[2], severity=GENERIC[3])


def _ranges(nums):
    nums = sorted(set(nums))
    return ", ".join(str(n) for n in nums)


def notes(issues, W=960, H=540, only_open=False):
    """Terse reviewer notes: one line per problem type, cross-slide repeats merged
    ("Multiple slides (1, 3, 4): title overlaps the content")."""
    groups = OrderedDict()
    for i in sorted(issues, key=lambda i: (i.slide, i.category)):
        if only_open and i.status == "fixed":
            continue
        e = explain(i, W, H)
        groups.setdefault(e["label"], set()).add(i.slide)
    lines = []
    for label, slides in sorted(groups.items(), key=lambda kv: (min(kv[1]), kv[0])):
        s = sorted(slides)
        lines.append(f"Slide {s[0]}: {label}" if len(s) == 1 else f"Multiple slides ({_ranges(s)}): {label}")
    return "\n".join(lines)


def detailed(issues, W=960, H=540):
    """Full write-up per issue, grouped by slide."""
    by = defaultdict(list)
    for i in issues:
        by[i.slide].append(i)
    out = []
    for s in sorted(by):
        out.append(f"Slide {s}")
        for i in by[s]:
            e = explain(i, W, H)
            out += [f"  [{e['severity'].upper()}] {e['item']} - {e['label']} ({e['where']})",
                    f"    What: {e['what']}", f"    Why it matters: {e['why']}", f"    Fix: {e['fix']}"]
    return "\n".join(out)
