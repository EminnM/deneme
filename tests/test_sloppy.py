import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import score
from deckqa import cli


class Sloppy(unittest.TestCase):
    def test_all_planted_defects_detected(self):
        tmp = tempfile.mkdtemp()
        truth, hit, miss, extra, issues = score.score(os.path.join(tmp, "s.pptx"))
        self.assertEqual(miss, [], f"missed: {miss}")
        self.assertGreaterEqual(len(truth), 25)

    def test_autofix_resolves_most_and_never_adds_garbage(self):
        tmp = tempfile.mkdtemp()
        src, out = os.path.join(tmp, "s.pptx"), os.path.join(tmp, "f.pptx")
        score.make_sloppy.build(src)
        cli.main([src, "--fix", out, "--report", os.path.join(tmp, "r.md"), "--json", os.path.join(tmp, "j.json")])
        import json
        j = json.load(open(os.path.join(tmp, "j.json")))
        self.assertGreater(len(j["before"]), 30)
        self.assertLessEqual(len(j["after"]), 12)      # what a human still has to do


if __name__ == "__main__":
    unittest.main()


class Explain(unittest.TestCase):
    def test_every_issue_gets_a_real_explanation_and_terse_notes(self):
        from deckqa import explain
        tmp = tempfile.mkdtemp()
        truth, hit, miss, extra, issues = score.score(os.path.join(tmp, "s.pptx"))
        for i in issues:
            e = explain.explain(i)
            self.assertNotEqual(e["label"], "issue", f"unclassified: {i.message}")
            self.assertTrue(e["why"] and e["fix"])
        notes = explain.notes(issues)
        self.assertIn("Slide 4: elements overlap", notes)
        self.assertRegex(notes, r"Multiple slides \(.*\): text too small to read")
