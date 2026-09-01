"""A deep link opened the right cinema once, then lost it on reload.

Reproduced: star Finnkino Cine Atlas, open a generated Tapio page, follow its
`/?area=sk-tapio` link. Tapio opens. The app then deletes the parameter from the URL, so
the next load has nothing to go on, falls through to the stored restore, and the favourite
beats the last-browsed area -- the tab lands on Cine Atlas and the reader has to find
Tapio again in the picker they followed a link to avoid.

The deletion was deliberate and its reasoning is in the old comment: leaving the parameter
in place would override the picker on every reload. That is a real problem and it has a
narrower answer than throwing the parameter away -- keep it while it is the answer, and
rewrite it when the reader picks something else.

`startupArea` and `areaParamAfterSelect` are sliced verbatim out of index.html by
tests/area_routing_harness.js and run on their own, the way `healthState`, `venueRows` and
`priceLabel` are. Both are pure; the harness runs the shipped code rather than a copy.
"""
import json
import pathlib
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "area_routing_harness.js"

FAV = "fi-cine-atlas"
DEEP = "sk-tapio"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class AreaRoutingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        payload = json.loads(out.stdout)
        cls.r = payload["routing"]
        cls.u = payload["urls"]

    # -- the seven behaviours the fix has to hold ----------------------------------------

    def test_favourite_and_no_deep_link_opens_the_favourite(self):
        self.assertEqual(self.r["fav_only_no_deep"]["area"], FAV)

    def test_a_deep_link_beats_the_favourite(self):
        self.assertEqual(self.r["fav_and_deep"]["area"], DEEP)

    def test_reloading_the_deep_linked_tab_still_opens_the_deep_link(self):
        """The defect. The second load sees the same parameter because the first one no
        longer deletes it, so it decides again instead of falling through to the
        favourite."""
        self.assertEqual(self.r["reload_with_deep"]["area"], DEEP)

    def test_the_deep_link_is_kept_in_the_url_while_it_is_the_answer(self):
        """`keepParam` is what stops the first load from erasing its own reason."""
        self.assertTrue(self.r["fav_and_deep"]["keepParam"])
        self.assertTrue(self.r["reload_with_deep"]["keepParam"])

    def test_arriving_by_deep_link_never_touches_the_favourite(self):
        """`remember` writes the last-browsed slot and the caller passes it to
        `prefs.set({area})`. Nothing in this path writes `fav`, so following a link
        cannot restar somebody's cinema -- which is the whole reason the favourite still
        wins on a later ordinary visit."""
        self.assertTrue(self.r["fav_and_deep"]["remember"])
        self.assertEqual(self.r["fav_only_no_deep"]["area"], FAV)

    def test_picking_another_cinema_rewrites_the_parameter(self):
        """Otherwise the next reload bounces back to the venue the reader navigated away
        from, which is the failure the old delete-on-apply was avoiding."""
        self.assertEqual(self.u["deep_then_pick"], "area=sk-maxim")

    def test_a_city_deep_link_behaves_the_same(self):
        self.assertEqual(self.r["city_deep"]["area"], "city:Helsinki")
        self.assertTrue(self.r["city_deep"]["keepParam"])

    def test_an_unknown_deep_link_falls_through(self):
        self.assertEqual(self.r["unknown_deep"]["area"], FAV)
        self.assertEqual(self.r["unknown_deep_no_fav"]["area"], "sk-maxim")
        self.assertIsNone(self.r["unknown_deep_nothing"]["area"])

    # -- and the URL never contradicts the picker -----------------------------------------

    def test_a_link_that_decided_nothing_is_taken_out_of_the_url(self):
        """`keepParam` false with a parameter present is the caller's signal to strip
        it. A URL saying `?area=sk-gone` beside a picker showing Cine Atlas is the
        disagreement this rule exists to prevent."""
        self.assertFalse(self.r["unknown_deep"]["keepParam"])
        self.assertFalse(self.r["unknown_deep_nothing"]["keepParam"])

    def test_an_ordinary_visit_never_grows_a_parameter(self):
        """Using the picker on `/` must not start writing `?area=` into the URL. Only a
        parameter that is already there gets rewritten."""
        self.assertIsNone(self.u["no_param"])
        self.assertIsNone(self.u["other_params_only"])

    def test_other_query_parameters_survive_the_rewrite(self):
        self.assertEqual(self.u["deep_with_other_params"], "area=sk-maxim&lang=en")

    def test_picking_the_venue_you_arrived_on_leaves_the_link_intact(self):
        self.assertEqual(self.u["deep_then_pick_same"], f"area={DEEP}")

    def test_a_city_selection_is_encoded_into_the_parameter(self):
        """The colon is percent-encoded on the way out and URLSearchParams decodes it on
        the way back in, so the round trip is what matters rather than the spelling."""
        self.assertEqual(self.u["deep_then_pick_city"], "area=city%3AHelsinki")

    def test_an_empty_area_parameter_is_filled_rather_than_ignored(self):
        """`?area=` is present but names nothing; the reader is in a tab that carries the
        parameter, so a selection belongs in it."""
        self.assertEqual(self.u["empty_area_param"], "area=sk-maxim")

    # -- the rest of the restore, unchanged ------------------------------------------------

    def test_the_favourite_still_beats_the_stored_area(self):
        self.assertEqual(self.r["fav_beats_stored"]["area"], "br-redi")

    def test_the_stored_area_is_used_when_nothing_is_starred(self):
        self.assertEqual(self.r["stored_only"]["area"], "sk-maxim")

    def test_a_first_visit_decides_nothing_and_leaves_it_to_the_caller(self):
        """null rather than a guess: the caller falls back to `areas[0].id`, which this
        function cannot know."""
        self.assertIsNone(self.r["nothing_at_all"]["area"])
        self.assertIsNone(self.r["stale_stored"]["area"])

    def test_a_city_with_one_venue_is_not_a_valid_area(self):
        """`known()` only accepts a `city:` id where the city has more than one venue,
        and a deep link naming a single-venue city falls through like any stale id."""
        self.assertEqual(self.r["city_deep_single_venue"]["area"], FAV)


if __name__ == "__main__":
    unittest.main()
