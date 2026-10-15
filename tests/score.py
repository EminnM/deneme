"""Score the tool against make_sloppy's ground truth (coarse: slide + category)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from deckqa import model, checks
from deckqa.config import Config
import make_sloppy


def score(path):
    truth = make_sloppy.build(path)
    cfg = Config()
    deck = model.load(path, cfg)
    issues = checks.run_all(deck, cfg)
    hit, miss = [], []
    used = set()
    for sl, cat, note in truth:
        m = [i for i in issues if i.slide == sl and i.category == cat]
        (hit if m else miss).append((sl, cat, note))
        used.update(id(i) for i in m)
    extra = [i for i in issues if id(i) not in used]
    return truth, hit, miss, extra, issues


if __name__ == "__main__":
    truth, hit, miss, extra, issues = score(sys.argv[1])
    print(f"planted {len(truth)} | detected {len(hit)} | missed {len(miss)} | other findings {len(extra)}")
    for m in miss:
        print("MISSED:", m)
    for i in extra:
        print("OTHER :", i.slide, i.category, "-", i.message)
