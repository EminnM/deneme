# deckqa

Deterministic QA and auto-fix for `.pptx` decks. It reads shape geometry, fonts and text
directly from the file (no AI guessing), so the same deck always gives the same result.

Checks follow the 8-item QA checklist: Alignment, Spacing, Text fit, Lines and arrows,
Titles, Readability, Leftover graphics, Consistency.

```
pip install python-pptx pillow
python -m deckqa deck.pptx                                  # check, print checklist + issues
python -m deckqa deck.pptx --fix fixed.pptx --report r.md   # auto-fix safe issues, re-check, report
python -m deckqa deck.pptx --json issues.json --render out/ # JSON + PNGs with problems circled
python -m deckqa deck.pptx --fix fixed.pptx --html review.html # one-page review for the human critic
python -m unittest discover -s tests                        # tests (builds a deck with seeded defects)
```

Exit code is 1 when issues remain, so it can be used as a gate.

Auto-fixed: near-miss alignment, uneven gaps, overflowing text/titles (shrink to a floor),
tiny fonts, crooked lines, empty grey/black/coloured leftover shapes, mixed fonts, title
size/position drift, missing page numbers. Manual (reported only): line crossing text,
title/content collisions, empty bands, hanging last words.

Limits: text wrapping is estimated with Liberation Sans metrics, so exotic fonts can be off;
theme-inherited sizes fall back to defaults; groups are treated as single boxes.
Thresholds live in `deckqa/config.py`.

## What it checks (beyond the basics)

- Shapes inside groups are flattened with the group transform applied, so dense consulting-style
  slides are checked (and fixed) in real slide coordinates.
- Peer alignment: same-size shapes in a row/column must share a top/left line, even across groups;
  any outlier is flagged however far off it is. Near-miss (<= 6pt) alignment is checked per container.
- Overlaps: text over text, text over pictures, and text blocks that nearly touch.
- Icons: nearly-centred icons and icons sitting differently from the same icon in sibling panels.
- Text that is wider than, or runs past the bottom of, the panel it sits on.
- Title: wraps, collides with content, or has less than 6pt clear space above content.

## Output for the human critic

Each run gives a per-slide summary (found / auto-fixed / left, passing checks), a suggested
Accept / Fix / Reject hint (Fix = about 5 minutes or less of human work, Reject = more), and with
`--html` a page showing the original and fixed slide images with problems circled.

## Dashboard

`python -m deckqa deck.pptx --fix fixed.pptx --dashboard dashboard.html` writes one offline HTML page:
heatmap of slides x checks, original / after-fix / compare views with clickable markers, per-issue
"fix is good / wrong" decisions, per-slide reviewed ticks, final Accept / Fix / Reject, notes, and
JSON export. Browser test (42 checks): `DASH_DIR=<dir> PLAYWRIGHT_PATH=<path> node tests/e2e/dashboard.e2e.js`.

## Verification board (blind, no fixes shown)

`python -m deckqa deck.pptx --verify board.html` writes an offline page that shows the deck exactly as received.
For every slide and every one of the 8 checklist items it says what was measured and found correct (green boxes on
the slide), what needs a look (red), or that the item does not apply. It also shows a deck inventory (fonts, sizes,
colours, titles, page numbers, odd ones out flagged), an "everything on this slide" table with font, size, colours
and position per element, a coverage grid, and a tick box per item per slide so no criterion is skipped.
No fix is applied or shown, so a reviewer forms their own view first. Each item also states what it does *not*
confirm (wording, facts, chart data, images, taste). Browser test (27 checks):
`DASH_DIR=<dir> PLAYWRIGHT_PATH=<path> node tests/e2e/verify.e2e.js`.
