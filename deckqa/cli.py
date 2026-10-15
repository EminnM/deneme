import argparse, json, sys

from .config import Config
from . import model, checks, fixer, report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="deckqa", description="Deterministic deck QA with optional auto-fix")
    ap.add_argument("deck")
    ap.add_argument("--fix", metavar="OUT.pptx", help="apply safe auto-fixes and save to this file")
    ap.add_argument("--report", metavar="FILE.md", help="write markdown report")
    ap.add_argument("--json", metavar="FILE.json", help="write machine-readable issues")
    ap.add_argument("--render", metavar="DIR", help="render slides to PNG with problems circled")
    ap.add_argument("--html", metavar="FILE.html", help="self-contained review page with annotated slide images")
    ap.add_argument("--dashboard", metavar="FILE.html", help="interactive reviewer dashboard (self-contained HTML)")
    ap.add_argument("--notes", metavar="FILE.txt", help="reviewer notes (terse + detailed what/why/fix for every issue)")
    ap.add_argument("--dpi", type=int, default=80, help="resolution of rendered slide images (higher = sharper, bigger files)")
    ap.add_argument("--min-font", type=float)
    a = ap.parse_args(argv)
    cfg = Config()
    if a.min_font:
        cfg.min_font = a.min_font

    deck = model.load(a.deck, cfg)
    before = checks.run_all(deck, cfg)
    after = None
    final_path = a.deck
    if a.fix:
        # fixes interact (moving one shape changes another's gaps), so repeat until nothing more is fixable
        pending, seen = before, {(i.slide, i.category, i.message) for i in before}
        for _ in range(4):
            n = fixer.apply(deck, pending, cfg)
            deck.prs.save(a.fix)
            deck = model.load(a.fix, cfg)
            after = checks.run_all(deck, cfg)
            pending = [i for i in after if i.fixable]
            if not n or not pending:
                break
            fresh = [i for i in pending if (i.slide, i.category, i.message) not in seen]
            seen.update((i.slide, i.category, i.message) for i in fresh)
            before.extend(fresh)   # uncovered by earlier fixes; marked when fixed on the next pass
        final_path = a.fix
    md = report.markdown(deck, before, after)
    if a.report:
        open(a.report, "w").write(md)
    else:
        print(md)
    if a.notes:
        open(a.notes, "w").write(report.explanations_text(deck, before))
    if a.json:
        json.dump(dict(before=[i.to_dict() for i in before],
                       after=[i.to_dict() for i in after] if after is not None else None),
                  open(a.json, "w"), indent=2)
    if a.render:
        from .render import render
        render(final_path, after if after is not None else before, deck, a.render, a.dpi)
    if a.html or a.dashboard:
        import tempfile, os
        from .render import render
        from . import report as rep
        with tempfile.TemporaryDirectory() as tmp:
            orig = model.load(a.deck, cfg)
            img_b = render(a.deck, before, orig, os.path.join(tmp, "b"), a.dpi)
            img_a = render(final_path, after, deck, os.path.join(tmp, "a"), a.dpi) if after is not None else {}
            if a.html:
                open(a.html, "w").write(rep.html_report(deck, before, after, img_b, img_a))
            if a.dashboard:
                from . import dashboard   # the dashboard draws its own interactive markers, so use clean renders
                cb = render(a.deck, before, orig, os.path.join(tmp, "cb"), a.dpi, annotate=False)
                ca = render(final_path, after, deck, os.path.join(tmp, "ca"), a.dpi, annotate=False) if after is not None else {}
                open(a.dashboard, "w").write(dashboard.html(deck, before, after, cb, ca, os.path.basename(a.deck)))
    remaining = after if after is not None else before
    return 1 if remaining else 0


if __name__ == "__main__":
    sys.exit(main())
