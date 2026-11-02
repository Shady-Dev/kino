"""Card and sheet draw a film's tags by one rule, `sharedTags` and `ownTags` (2026-11-02).

Sliced verbatim out of index.html by tests/ticket_tags_harness.js.
"""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "ticket_tags_harness.js"
HTML = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")


def function_source(signature):
    a = HTML.index(signature)
    return HTML[a:HTML.index("\n  }\n", a)]


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class TicketTagsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.r = json.loads(out.stdout)

    def test_an_event_tag_on_one_screening_stays_on_that_ticket(self):
        self.assertEqual(self.r["afternoon_tea"],
                         {"shared": [], "own": [[], ["Afternoon Tea"], []]})
        self.assertEqual(self.r["described"]["own"][0],
                         ["Senioribio", "Kuvaileva tekstitys", "Anniskelu"])
        self.assertEqual(self.r["described"]["own"][1], [])

    def test_the_first_screening_s_formats_are_not_the_film_s(self):
        """The Odyssey's case: IMAX and 2D on the first screening, other rooms after."""
        self.assertEqual(self.r["imax_and_luxe"]["shared"], [])
        self.assertEqual(self.r["imax_and_luxe"]["own"],
                         [["Anniskelu"], ["Anniskelu"], ["Anniskelu"], []])
        self.assertEqual(self.r["imax_in_sali"]["own"], [["IMAX"], []])

    def test_a_tag_every_screening_carries_is_drawn_once(self):
        self.assertEqual(self.r["shared_35mm"], {"shared": ["35 mm"], "own": [["Senioribio"], []]})
        self.assertEqual(self.r["imax_in_sali"]["shared"], ["2D"])
        self.assertEqual(self.r["one_screening"], {"shared": ["Seniorikino"], "own": [[]]})
        self.assertEqual(self.r["order_kept"]["shared"], ["Atmos", "Event cinema"])

    def test_a_glyph_tag_never_folds(self):
        self.assertEqual(self.r["all_anniskelu"],
                         {"shared": [], "own": [["Anniskelu"], ["Anniskelu"]]})

    def test_no_screening_or_no_method_gives_no_tag(self):
        self.assertEqual(self.r["empty"], {"shared": [], "own": []})
        self.assertEqual(self.r["no_method"], {"shared": [], "own": [[], []]})


class TagRuleCallersTest(unittest.TestCase):
    """Both renderers call the one rule; pinned on the source."""

    def test_the_card_folds_through_shared_tags(self):
        src = function_source("  function render(){")
        self.assertIn("const common = sharedTags(m.times, glyphOf);", src)
        self.assertIn("const mine = ownTags(t, common);", src)

    def test_the_sheet_folds_over_all_of_its_screenings(self):
        src = function_source("  async function showSheet(")
        self.assertIn("const shared = sharedTags(all, glyphOf);", src)
        self.assertIn("const mine = ownTags(s, shared);", src)
        self.assertIn("...mine.filter(f => !glyphOf(f))", src)
        self.assertIn("mine.map(glyphOf).join('')", src)
        self.assertNotRegex(src, r"sample\.method")

    def test_one_definition_of_the_tag_split(self):
        self.assertEqual(len(re.findall(r"const tagsOf\s*=", HTML)), 1)


if __name__ == "__main__":
    unittest.main()
