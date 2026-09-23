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
        self.assertIn("? slangHtml(t.lang) : ''", HTML)          # the card's stub
        self.assertIn("? slangHtml(s.lang) : ''", HTML)          # the sheet's stub
        self.assertEqual(len(re.findall(r'class="slang"', HTML)), 1, "one builder for both")

    def test_the_language_line_is_the_last_item_in_its_compartment(self):
        """`.slang` takes a full row, so anything after it lands on a third line."""
        seen = 0
        for m in re.finditer(r'<span class="aud\$\{[^"]*?"[^>]*>(.*?)</span><span class="price"',
                             HTML, re.S):
            body = m.group(1)
            if "slangHtml(" not in body:
                continue
            seen += 1
            self.assertGreater(body.index("slangHtml("), body.index("glyphRow"),
                               "the language line must follow the glyph row")
        self.assertEqual(seen, 2, "both stubs checked")

    def test_the_shared_line_sits_with_the_genres_in_the_sheet_head(self):
        self.assertIn("const sheetMeta2 = [", HTML)
        self.assertIn("lsplit.shared ? `<span>${esc(langTxt(lsplit.shared))}</span>` : ''", HTML)

    def test_the_glyph_centres_on_the_whole_compartment_not_its_first_row(self):
        """Reported 2026-09-20: the Anniskelu A looked high on a ticket whose language
        line made the compartment two rows, because a flex item centres inside its own
        wrapped row. The glyphs now have a grid column spanning both rows, centred on it.
        Explicit rows and `span 2`: a negative line counts from the explicit grid in
        WebKit, which broke the landing pages on 2026-09-18."""
        rule = re.search(r"\.stub \.aud\.twoline \.glyphs\{(.*?)\}", HTML, re.S).group(1)
        flat = rule.replace(" ", "").replace("\n", "")
        self.assertIn("grid-column:2", flat)
        self.assertIn("grid-row:1/span2", flat)
        self.assertIn("align-self:center", flat)
        self.assertNotIn("position:absolute", flat)

    def test_the_room_and_language_cannot_run_under_the_glyphs(self):
        """Reported 2026-09-23: an absolute glyph behind a fixed 24 px reservation fitted
        one glyph, and A with 18+ covered the room and the language in the film view at
        1200 in both engines. The text takes the first column, the glyphs the second, so
        the reservation is whatever the glyphs measure. Both selectors, because
        `.stubs.grid .stub .aud` sets display at a higher specificity."""
        self.assertIn(".stub .aud.twoline,\n  .stubs.grid .stub .aud.twoline{display:grid; "
                      "grid-template-columns:minmax(0,1fr) auto;", HTML)
        self.assertIn(".stub .aud.twoline .loc{grid-column:1; grid-row:1}", HTML)
        self.assertIn(".stub .aud.twoline .slang{grid-column:1; grid-row:2}", HTML)
        self.assertNotIn("padding-right:24px", HTML)

    def test_it_reuses_the_existing_translation_helper(self):
        """No second language table: langTxt already localises fi, sv and en."""
        self.assertEqual(len(re.findall(r"const LW = \{", HTML)), 1)
        self.assertIn("function langTxt(code, lead = true){ return langParts(code, lead).join(' · '); }",
                      HTML)
        self.assertIn("langParts(code).map(p => `<span>${esc(p)}</span>`)", HTML)

    def test_a_narrow_ticket_breaks_between_the_spoken_and_the_subtitle_part(self):
        """Asked for 2026-09-23: when the line does not fit, the spoken language keeps its
        line and the subtitles take the next, with no dot left at either end. Measured
        that day on Helsinki in Chromium and WebKit: at 393 px 6 of 10 card lines stack
        and 4 fit on one, at 1200 all fit; the dot shows exactly when the parts share a
        line. The dot is the later part's ::before, clipped when that part starts a line."""
        self.assertIn(".stub .slang{overflow:hidden; min-width:0}", HTML)
        self.assertIn(".stub .slang .lp{display:flex; flex-wrap:wrap; margin-left:-.9em}", HTML)
        self.assertIn(".stub .slang .lp > span{position:relative; padding-left:.9em; min-width:0}",
                      HTML)
        self.assertIn(".stub .slang .lp > span + span::before{content:'\\b7'; position:absolute; "
                      "left:.25em}", HTML)


if __name__ == "__main__":
    unittest.main()
