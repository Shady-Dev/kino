"""A screening's language is the screening's, not the film's (2026-09-20).

The Helsinki card read "espanja · tekstitys: suomi/ruotsi" for Autofiktio while the film
details beside the booking choices said nothing at all, and the card's value came from
whichever screening `{ ...s }` copied first. Measured over the committed data that day:
1469 (area, film) pairs, 73.3% agreeing on one non-empty value, 24.7% publishing none,
and 2.0% disagreeing. Kojootti vs. ACME is the case that costs a reader something, running
dubbed (FI-A) beside subtitled (EN-A, FI-S, SV-S) in one cinema on one day.

`langSplit` decides it: agreement puts one line above the schedule, disagreement puts each
screening's own on its ticket, and a screening that published nothing never inherits a
neighbour's. It is sliced verbatim out of index.html by tests/lang_split_harness.js.
"""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "lang_split_harness.js"
HTML = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class LangSplitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.r = json.loads(out.stdout)

    def test_no_case_threw(self):
        threw = {k: v for k, v in self.r.items() if "threw" in v}
        self.assertEqual(threw, {}, "langSplit must survive every shape the render path passes")

    def test_agreement_is_shared_and_not_repeated(self):
        for key, code in (("all_same", "FI-A"),
                          ("all_same_three", "EN-A, FI-S, SV-S"),
                          ("single_known", "ES-A, FI-S, SV-S")):
            with self.subTest(key):
                self.assertEqual(self.r[key], {"shared": code, "perShow": False})

    def test_nothing_published_shows_nothing_anywhere(self):
        for key in ("all_missing", "all_absent_key", "single_missing",
                    "empty_list", "null_list", "undefined_list"):
            with self.subTest(key):
                self.assertEqual(self.r[key], {"shared": "", "perShow": False})

    def test_differing_values_move_onto_each_screening(self):
        self.assertEqual(self.r["mixed_values"], {"shared": "", "perShow": True})
        self.assertEqual(self.r["spacing_differs"], {"shared": "", "perShow": True})

    def test_a_missing_value_never_inherits_a_neighbours(self):
        """The requirement the old fold broke, in both orders and for an absent key."""
        for key in ("known_then_missing", "missing_then_known",
                    "absent_key_then_known", "null_member"):
            with self.subTest(key):
                self.assertEqual(self.r[key], {"shared": "", "perShow": True},
                                 "a screening that published nothing must stay unknown")

    def test_the_card_no_longer_folds_lang_off_the_first_screening(self):
        """The line this replaced read `if(!m.lang && s.lang) m.lang = s.lang;`."""
        self.assertNotIn("if(!m.lang && s.lang)", HTML)
        self.assertIn("for(const m of movies) m.lang = langSplit(m.times).shared;", HTML)

    def test_both_render_paths_ask_langSplit(self):
        """The card and the sheet each draw the shared line and the per-screening one."""
        self.assertIn("langSplit(m.times).perShow", HTML)
        self.assertIn("const lsplit = langSplit(all);", HTML)
        self.assertEqual(len(re.findall(r'class="slang"', HTML)), 2,
                         "one per-screening language line on the card stub and one on the sheet stub")

    def test_the_language_line_is_the_last_item_in_its_compartment(self):
        """`.slang` takes a full row, so anything after it lands on a third line."""
        for m in re.finditer(r'<span class="aud\$\{[^"]*?"[^>]*>(.*?)</span><span class="price"',
                             HTML, re.S):
            body = m.group(1)
            if 'class="slang"' not in body:
                continue
            self.assertGreater(body.index('class="slang"'), body.index("glyphRow"),
                               "the language line must follow the glyph row")

    def test_the_shared_line_sits_with_the_genres_in_the_sheet_head(self):
        self.assertIn("const sheetMeta2 = [", HTML)
        self.assertIn("lsplit.shared ? `<span>${esc(langTxt(lsplit.shared))}</span>` : ''", HTML)

    def test_the_glyph_centres_on_the_whole_compartment_not_its_first_row(self):
        """Reported 2026-09-20: the Anniskelu A looked high on a ticket whose language
        line made the compartment two rows. A flex item centres inside its own wrapped
        row, so it sat 8 px above the ticket's middle in Chromium and WebKit alike at 390
        and 1200. Taken out of the flow and centred on the compartment; measured 0 after."""
        rule = re.search(r"\.stub \.aud\.twoline \.glyphs\{(.*?)\}", HTML, re.S).group(1)
        flat = rule.replace(" ", "").replace("\n", "")
        self.assertIn("position:absolute", flat)
        self.assertIn("top:50%", flat)
        self.assertIn("translateY(-50%)", flat)

    def test_the_room_cannot_run_under_that_glyph(self):
        """`.stubs.grid .stub .aud` sets padding at a higher specificity, so the
        reservation has to be stated at that level too or it is simply ignored."""
        self.assertIn(".stubs.grid .stub .aud.twoline{position:relative; padding-right:24px}",
                      HTML)
        self.assertIn(".stub .aud.twoline,\n", HTML)

    def test_it_reuses_the_existing_translation_helper(self):
        """No second language table: langTxt already localises fi, sv and en."""
        self.assertEqual(len(re.findall(r"const LW = \{", HTML)), 1)
        self.assertIn("esc(langTxt(t.lang))", HTML)
        self.assertIn("esc(langTxt(s.lang))", HTML)


if __name__ == "__main__":
    unittest.main()
