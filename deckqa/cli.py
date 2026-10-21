import argparse, json, sys

from .config import Config
from . import model, checks, fixer, report


def _safe_render(*args, **kw):
    """Slide images need LibreOffice + poppler. If they are missing, carry on without images."""
    from .render import render
    try:
        return render(*args, **kw)
    except Exception as e:
        if not getattr(_safe_render, "warned", False):
            _safe_render.warned = True
            print("note: slide images were skipped (" + str(e) + "). Boards still work and show element outlines; "
                  "install LibreOffice and poppler to get slide pictures.", file=sys.stderr)
        return {}


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
    ap.add_argument("--verify", metavar="FILE.html", help="blind verification board: what is measured and correct on every slide, per checklist item (no fixes shown)")
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
    from . import textfit
    md = report.markdown(deck, before, after)
    if textfit.FALLBACKS:
        note = ("Note: these fonts are not installed here, so text was measured with a stand-in and text-fit/overlap "
                "results for them are approximate: " + ", ".join(sorted(set(textfit.FALLBACKS))))
        md = md.replace("\n\n", "\n\n" + note + "\n\n", 1)
        print(note, file=sys.stderr)
    if a.report:
        open(a.report, "w", encoding="utf-8").write(md)
    else:
        print(md)
    if a.verify:
        import tempfile, os
        from . import verify, verify_html
        orig = model.load(a.deck, cfg)
        data = verify.build(orig, cfg)
        with tempfile.TemporaryDirectory() as tmp:
            imgs = _safe_render(a.deck, [], orig, os.path.join(tmp, "v"), a.dpi if a.dpi != 80 else 110, annotate=False)
            open(a.verify, "w", encoding="utf-8").write(verify_html.html(data, imgs, os.path.basename(a.deck)))
    if a.notes:
        open(a.notes, "w", encoding="utf-8").write(report.explanations_text(deck, before))
    if a.json:
        json.dump(dict(before=[i.to_dict() for i in before],
                       after=[i.to_dict() for i in after] if after is not None else None),
                  open(a.json, "w", encoding="utf-8"), indent=2)
    if a.render:
        _safe_render(final_path, after if after is not None else before, deck, a.render, a.dpi)
    if a.html or a.dashboard:
        import tempfile, os
        from . import report as rep
        with tempfile.TemporaryDirectory() as tmp:
            orig = model.load(a.deck, cfg)
            img_b = _safe_render(a.deck, before, orig, os.path.join(tmp, "b"), a.dpi)
            img_a = _safe_render(final_path, after, deck, os.path.join(tmp, "a"), a.dpi) if after is not None else {}
            if a.html:
                open(a.html, "w", encoding="utf-8").write(rep.html_report(deck, before, after, img_b, img_a))
            if a.dashboard:
                from . import dashboard   # the dashboard draws its own interactive markers, so use clean renders
                cb = _safe_render(a.deck, before, orig, os.path.join(tmp, "cb"), a.dpi, annotate=False)
                ca = _safe_render(final_path, after, deck, os.path.join(tmp, "ca"), a.dpi, annotate=False) if after is not None else {}
                open(a.dashboard, "w", encoding="utf-8").write(dashboard.html(deck, before, after, cb, ca, os.path.basename(a.deck)))
    remaining = after if after is not None else before
    return 1 if remaining else 0


if __name__ == "__main__":
    sys.exit(main())
