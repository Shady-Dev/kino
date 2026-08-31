"""The venue picker's row model: what a query shows, and in which order.

Order is behavior here, not presentation: Enter in the search field picks the first
row, so a combined "Kaikki {city}" row sorting above a searched venue silently changes
what Enter selects. That is the bug an external review found on the first version --
searching "itis" put Kaikki Helsinki first because the combined row appeared whenever
any venue in the city matched -- and these tests exist so it cannot come back.

Driven through tests/venue_picker_harness.js, which extracts the pure model verbatim
from index.html and runs it in Node. Focus, inert, Escape and keyboard behavior are DOM
plumbing outside the model and stay verified live.
"""
import json
import pathlib
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "venue_picker_harness.js"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class VenuePickerModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.r = json.loads(out.stdout)

    # -- what Enter selects --------------------------------------------------------

    def test_a_venue_query_puts_the_venue_first_not_the_combined_row(self):
        """Searching "itis" must select Finnkino Itis on Enter, never Kaikki
        Helsinki. The combined row may not ride along on a venue match."""
        rows = self.r["venue_query_first_row"]
        self.assertEqual(rows, ["#Helsinki", "venue:itis"])

    def test_a_city_query_offers_the_combined_row_first(self):
        """The other side of the same rule: for "helsinki" the combined view is the
        natural pick, so there it does come first."""
        rows = self.r["city_query"]
        self.assertEqual(rows[0], "#Helsinki")
        self.assertEqual(rows[1], "all:city:Helsinki")
        self.assertIn("venue:itis", rows)

    def test_kaikki_finds_every_combined_row_and_no_venues(self):
        self.assertEqual(self.r["kaikki_query"], ["#Helsinki", "all:city:Helsinki"])

    # -- matching ------------------------------------------------------------------

    def test_diacritics_fold_both_ways(self):
        self.assertEqual(self.r["diacritics"], ["#Järvelä", "venue:ja"])

    def test_swedish_mode_matches_both_city_names(self):
        """Labels carry no city, so the haystack has to hold the raw name and the
        display name: Turku and Åbo both find the Turku venue in Swedish."""
        self.assertIn("venue:tku", self.r["sv_alias_fi_name"])
        self.assertIn("venue:tku", self.r["sv_alias_sv_name"])

    def test_no_match_yields_no_rows(self):
        self.assertEqual(self.r["none"], [])

    def test_the_highlight_lands_on_the_match(self):
        """vfold strips combining marks without changing the string length, so the
        <mark> offsets index the NFC original."""
        self.assertEqual(self.r["hl"], "<mark>Järvelä</mark>n Kino")

    # -- the pinned favourite ------------------------------------------------------

    def test_a_saved_venue_is_pinned_on_top(self):
        rows = self.r["fav_venue"]
        self.assertEqual(rows[:2], ["#Oma teatteri", "venue:ja"])

    def test_a_saved_combined_city_is_pinned_too(self):
        """city:* ids are valid favourites everywhere else (fillAreaSelect restores
        them), so the pinned section has to show them as well."""
        rows = self.r["fav_city"]
        self.assertEqual(rows[:2], ["#Oma teatteri", "all:city:Helsinki"])

    def test_the_pinned_row_obeys_the_filter(self):
        self.assertNotIn("all:city:Helsinki", self.r["fav_city_filtered_out"])
        self.assertIn("venue:tku", self.r["fav_city_filtered_out"])

    # -- the unfiltered list -------------------------------------------------------

    def test_no_query_shows_every_group_with_combined_rows_where_multi(self):
        rows = self.r["no_query"]
        self.assertEqual(rows[:4], ["#Helsinki", "all:city:Helsinki",
                                    "venue:itis", "venue:tripla"])
        self.assertIn("#Järvelä", rows)
        self.assertNotIn("all:city:Järvelä", rows, "a one-venue city has no combined row")


if __name__ == "__main__":
    unittest.main()
