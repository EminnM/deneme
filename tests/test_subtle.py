import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from deckqa import model, checks, cli
from deckqa.config import Config
import make_subtle


class Subtle(unittest.TestCase):
    def test_subtle_defects_found(self):
        tmp = tempfile.mkdtemp()
        truth = make_subtle.build(os.path.join(tmp, "s.pptx"))
        cfg = Config()
        issues = checks.run_all(model.load(os.path.join(tmp, "s.pptx"), cfg), cfg)
        miss = [t for t in truth if not [i for i in issues if i.slide == t[0] and i.category == t[1]]]
        self.assertEqual(miss, [])

    def test_subtle_fixes_resolve_what_is_fixable(self):
        tmp = tempfile.mkdtemp()
        src, out, js = (os.path.join(tmp, n) for n in ("s.pptx", "f.pptx", "j.json"))
        make_subtle.build(src)
        cli.main([src, "--fix", out, "--json", js])
        import json
        after = json.load(open(js))["after"]
        self.assertEqual([a for a in after if a["fixable"]], [])


if __name__ == "__main__":
    unittest.main()
