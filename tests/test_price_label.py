"""A provider that publishes its own floor price had it thrown away.

`priceLabel()` read every price with `parseFloat`, which accepts a number only at the
start of the string. Cinema Orion writes "alkaen 10€" -- the cinema's own way of saying
the cheapest ticket type is 10 -- and that came back NaN, was filtered out as unpriced,
and rendered nothing at all. Counted against the committed data on 2026-09-01: **23 of
Orion's 29 price-bearing showtimes showed no price**, and the six that did were the ones
whose string happened to begin with a digit. Every other provider was unaffected, because
all 1014 of their price strings start with the number.

Two questions had been collapsed into one. What the cheapest price is, and whether it
should be introduced as a floor. The second used to be answered only by "this list holds
two different amounts", which cannot see a source that already said so.

Extracted verbatim by tests/price_label_harness.js the way `healthState` and `venueRows`
are. The harness reads the three real `from` translations out of index.html rather than
retyping them, so the localisation is exercised against what actually ships.
"""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "price_label_harness.js"
EUR = "€"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class PriceLabelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.r = json.loads(out.stdout)

    # -- the defect --------------------------------------------------------------------

    def test_a_source_that_says_alkaen_renders_a_price(self):
        """The reported case. It used to render the empty string."""
        self.assertEqual(self.r["orion_floor_only"], f"alkaen 10{EUR}")

    def test_the_same_floor_repeated_is_still_a_floor(self):
        """Three screenings all at "alkaen 10€" agree on the number, so the old
        two-different-amounts rule would call it exact even once the number parsed.
        The source said floor and that has to survive."""
        self.assertEqual(self.r["orion_floor_repeated"], f"alkaen 10{EUR}")

    def test_the_other_orion_floor_parses_too(self):
        self.assertEqual(self.r["orion_floor_twelve"], f"alkaen 12{EUR}")

    def test_orions_real_mix_takes_the_cheapest(self):
        """The three strings Orion actually publishes, together: 10 as a floor, 10
        exact, 8.5 exact. The label is the cheapest of them, introduced as a floor."""
        self.assertEqual(self.r["orion_real_mix"], f"alkaen 8.50{EUR}")

    # -- what already worked, and must keep working ---------------------------------------

    def test_a_single_exact_price_has_no_prefix(self):
        self.assertEqual(self.r["exact_single"], f"13{EUR}")

    def test_the_same_exact_price_twice_has_no_prefix(self):
        """The case a shape-based floor test could break: `13€` twice is still exact,
        and nothing in either string is a floor marker."""
        self.assertEqual(self.r["exact_repeated"], f"13{EUR}")

    def test_two_different_amounts_are_introduced_as_a_floor(self):
        self.assertEqual(self.r["two_amounts"], f"alkaen 10{EUR}")

    def test_both_decimal_separators_read_the_same(self):
        self.assertEqual(self.r["decimal_comma"], f"8.50{EUR}")
        self.assertEqual(self.r["decimal_point"], f"8.50{EUR}")

    def test_a_whole_number_written_with_decimals_loses_them(self):
        self.assertEqual(self.r["whole_from_decimal"], f"12{EUR}")

    def test_a_space_before_the_currency_is_not_a_floor_marker(self):
        """`13 €` and `13&nbsp;€` are exact prices that happen to have something after
        the number. A floor test that only asked "is there anything left" would call
        both of these floors and prefix every price on the site."""
        self.assertEqual(self.r["spaced_currency"], f"13{EUR}")
        self.assertEqual(self.r["nbsp_currency"], f"13{EUR}")

    # -- nothing to say ------------------------------------------------------------------

    def test_no_rows_and_no_prices_render_nothing(self):
        self.assertEqual(self.r["empty_list"], "")
        self.assertEqual(self.r["no_prices"], "")

    def test_a_price_with_no_number_renders_nothing(self):
        """"Vapaa pääsy" is free admission, and Orion has published it. It is not 0€
        and it is not a floor; the price cell stays empty and the row says nothing."""
        self.assertEqual(self.r["words_only"], "")

    def test_zero_and_negative_are_refused(self):
        """The guard the old `v > 0` provided, kept. Pulling the number out of the
        middle of a string nearly lost it: without the sign in the match, `-5€` matched
        as 5 and came back as a price."""
        self.assertEqual(self.r["zero"], "")
        self.assertEqual(self.r["negative"], "")

    def test_a_free_screening_beside_a_paid_one_reports_the_paid_price(self):
        """Pinned rather than argued. The free row carries no number so it is not part
        of the range, and the label describes what a ticket costs."""
        self.assertEqual(self.r["mixed_free_and_priced"], f"10{EUR}")

    # -- and the prefix is the language's ---------------------------------------------------

    def test_the_floor_prefix_is_localised(self):
        want = self.r["__from"]
        self.assertEqual(self.r["floor_fi"], f"{want['fi']} 10{EUR}")
        self.assertEqual(self.r["floor_sv"], f"{want['sv']} 10{EUR}")
        self.assertEqual(self.r["floor_en"], f"{want['en']} 10{EUR}")

    def test_a_range_uses_the_same_localised_prefix(self):
        want = self.r["__from"]
        self.assertEqual(self.r["range_fi"], f"{want['fi']} 10{EUR}")
        self.assertEqual(self.r["range_sv"], f"{want['sv']} 10{EUR}")
        self.assertEqual(self.r["range_en"], f"{want['en']} 10{EUR}")

    def test_the_three_translations_are_actually_different(self):
        """Guards the harness rather than the code: if `translation()` silently returned
        the same string three times, every localisation test above would pass."""
        want = self.r["__from"]
        self.assertEqual(len({want["fi"], want["sv"], want["en"]}), 3, want)


class PricePlacementTest(unittest.TestCase):
    """The price is the screening's, never the film's (2026-09-02). `priceLabel` over a
    film's screenings skips the unpriced ones, so Autofiktio in Tampere read "11€" on the
    card from Cinema Niagara's 16:15 while Finnkino's 17:30 and 20:15 published none. The
    rendering is DOM work and stays verified live; what can be pinned here is the source:
    every call folds one row, and every stub renderer carries the price element."""

    HTML = (pathlib.Path(_ctx.ROOT) / "index.html").read_text(encoding="utf-8")

    def test_price_label_is_only_ever_asked_about_one_screening(self):
        calls = re.findall(r"priceLabel\(([^)]*)\)", self.HTML)
        self.assertEqual(sorted(calls), ["[s]", "[s]", "[t]", "rows"])   # definition + 3 renderers

    def test_the_card_and_the_sheet_carry_no_folded_price(self):
        self.assertNotIn("priceLabel(m.times)", self.HTML)
        self.assertNotIn("priceLabel(all)", self.HTML)
        self.assertNotIn("sheetPrice", self.HTML)

    def test_each_stub_renderer_emits_the_price_element_inside_the_stub(self):
        stubs = re.findall(r'<a class="stub\$\{cls\}.*?</a>', self.HTML, re.S)
        self.assertEqual(len(stubs), 3)
        for stub in stubs:
            with self.subTest(stub=stub[:60]):
                self.assertIn('<span class="price">${esc(own_price)}</span>', stub)
                self.assertIn('<span class="time">', stub)
        self.assertRegex(self.HTML, r"\.stub \.price\{[^}]*white-space:nowrap")
        self.assertRegex(self.HTML, r'grid-template-areas:"time aud price"')


if __name__ == "__main__":
    unittest.main()
