import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from deckqa import model, verify
from deckqa.config import Config, CATEGORIES
import make_subtle, make_dense


class Verify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.cfg = Config()
        cls.sub = os.path.join(cls.tmp, "sub.pptx")
        make_subtle.build(cls.sub)
        cls.clean = os.path.join(cls.tmp, "clean.pptx")
        make_dense.build(cls.clean, defects=False)

    def data(self, path):
        return verify.build(model.load(path, self.cfg), self.cfg)

    def test_every_slide_accounts_for_all_eight_items_in_order(self):
        d = self.data(self.sub)
        for s in d["slides"]:
            self.assertEqual([i["item"] for i in s["items"]], CATEGORIES)
            for i in s["items"]:
                self.assertIn(i["status"], ("pass", "flag", "na"))
                self.assertTrue(i["limits"])

    def test_flags_match_the_seeded_defects(self):
        d = self.data(self.sub)
        st = lambda sl, item: next(i for i in d["slides"][sl - 1]["items"] if i["item"] == item)["status"]
        self.assertEqual(st(2, "Alignment"), "flag")
        self.assertEqual(st(2, "Consistency"), "flag")
        self.assertEqual(st(3, "Lines and arrows"), "flag")
        self.assertEqual(st(3, "Readability"), "flag")
        self.assertEqual(st(4, "Titles"), "flag")
        self.assertEqual(st(5, "Text fit"), "flag")

    def test_clean_slide_gets_positive_evidence_and_no_flags(self):
        d = self.data(self.clean)
        items = d["slides"][0]["items"]
        self.assertFalse([i for i in items if i["status"] == "flag"], [i["summary"] for i in items])
        passed = [i for i in items if i["status"] == "pass"]
        self.assertGreaterEqual(len(passed), 5)
        for i in passed:
            self.assertTrue(i["ok"], i["item"])           # a pass always says what was confirmed
        boxes = [b for i in passed for o in i["ok"] for b in o["boxes"]]
        self.assertTrue(boxes)                            # and points at things on the slide

    def test_blind_board_contains_no_fix_information(self):
        txt = json.dumps(self.data(self.sub)).lower()
        for banned in ('"fix"', "auto-fix", '"how"', "after fix", '"after"'):
            self.assertNotIn(banned, txt)

    def test_inventory_lists_fonts_sizes_colours_and_flags_rare_ones(self):
        inv = self.data(self.sub)["inventory"]
        self.assertEqual(inv["fonts"][0]["value"], "Calibri")
        rare = [f["value"] for f in inv["fonts"] if f["rare"]]
        self.assertIn("Arial", rare)                      # the one Arial box on slide 3
        self.assertTrue(inv["fills"] and inv["sizes"] and inv["titles"])

    def test_element_table_lists_font_size_and_colour(self):
        d = self.data(self.sub)
        els = d["slides"][1]["elements"]
        lever2 = next(e for e in els if e["label"].startswith("'Lever 2'"))
        self.assertEqual(lever2["fill"], "#2E5A7A")       # the off-by-8 colour is visible to the reviewer
        self.assertEqual(lever2["font"], "Calibri")


if __name__ == "__main__":
    unittest.main()
