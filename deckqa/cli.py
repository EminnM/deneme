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
        fixer.apply(deck, before, cfg)
        deck.prs.save(a.fix)
        final_path = a.fix
        deck = model.load(a.fix, cfg)
        after = checks.run_all(deck, cfg)
    md = report.markdown(deck, before, after)
    if a.report:
        open(a.report, "w").write(md)
    else:
        print(md)
    if a.json:
        json.dump(dict(before=[i.to_dict() for i in before],
                       after=[i.to_dict() for i in after] if after is not None else None),
                  open(a.json, "w"), indent=2)
    if a.render:
        from .render import render
        render(final_path, after if after is not None else before, deck, a.render)
    remaining = after if after is not None else before
    return 1 if remaining else 0


if __name__ == "__main__":
    sys.exit(main())
