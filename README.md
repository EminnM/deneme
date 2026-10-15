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
