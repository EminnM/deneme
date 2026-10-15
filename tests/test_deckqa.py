import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from deckqa import model, checks, fixer
from deckqa.config import Config, CATEGORIES
import make_sample


class DeckQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "s.pptx")
        make_sample.build(cls.path)
        cls.cfg = Config()

    def found(self, path=None):
        deck = model.load(path or self.path, self.cfg)
        return deck, checks.run_all(deck, self.cfg)

    def test_every_category_detected(self):
        _, issues = self.found()
        cats = {i.category for i in issues}
        for c in CATEGORIES:
            self.assertIn(c, cats, f"{c} not detected: {[(i.slide, i.category) for i in issues]}")

    def test_clean_slide_has_no_issues(self):
        _, issues = self.found()
        self.assertEqual([i for i in issues if i.slide == 1], [])

    def test_deterministic(self):
        a = [i.to_dict() for i in self.found()[1]]
        b = [i.to_dict() for i in self.found()[1]]
        self.assertEqual(a, b)

    def test_fix_reduces_issues_and_is_idempotent(self):
        deck, issues = self.found()
        n = fixer.apply(deck, issues, self.cfg)
        self.assertGreater(n, 0)
        out = os.path.join(self.tmp, "fixed.pptx")
        deck.prs.save(out)
        _, after = self.found(out)
        self.assertLess(len(after), len(issues))
        fixable_left = [i for i in after if i.fixable]
        self.assertEqual(fixable_left, [], [(i.slide, i.category, i.message) for i in fixable_left])


if __name__ == "__main__":
    unittest.main()
