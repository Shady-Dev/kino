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

`startupLang` and `langParamAfterSelect` are the language half of the same link (2026-09-02).
The generated pages exist in Finnish and English, and the app read its language from prefs
alone, so an English landing page opened a Finnish app for any reader without a stored
choice. The rules mirror the venue's: the parameter wins on arrival, stays in the URL while
it is the answer, is rewritten when the reader toggles, and is stripped when it names a
language the app does not have.
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
        cls.l = payload["lang"]
        cls.lu = payload["langUrls"]

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

    # -- the language half of the link ----------------------------------------------------

    def test_the_link_language_beats_the_stored_one(self):
        """An English landing page opens the English app whatever the reader had before."""
        self.assertEqual(self.l["en_link_fi_stored"]["lang"], "en")
        self.assertEqual(self.l["fi_link_en_stored"]["lang"], "fi")

    def test_the_link_language_opens_the_app_for_a_reader_with_nothing_stored(self):
        """The case the pages were shipped without: no preference, English page, and the
        app used to default to Finnish."""
        self.assertEqual(self.l["en_link_nothing_stored"]["lang"], "en")

    def test_the_link_language_is_kept_in_the_url_while_it_is_the_answer(self):
        """Same reason as the venue: a reload has to be able to decide again."""
        for case in ("en_link_fi_stored", "en_link_nothing_stored", "sv_link_fi_stored"):
            with self.subTest(case=case):
                self.assertTrue(self.l[case]["keepParam"])

    def test_a_stored_choice_is_never_overwritten_by_a_link(self):
        """`remember` is false when something valid is stored. Following one English link
        must not switch a Finnish reader's app for good."""
        self.assertFalse(self.l["en_link_fi_stored"]["remember"])
        self.assertFalse(self.l["fi_link_en_stored"]["remember"])

    def test_a_first_visit_keeps_the_language_it_arrived_in(self):
        """Nothing valid stored: the link seeds the preference, so a later plain visit
        stays in the language of the page the reader came through."""
        self.assertTrue(self.l["en_link_nothing_stored"]["remember"])
        self.assertTrue(self.l["en_link_bad_stored"]["remember"])

    def test_only_a_supported_value_decides_anything(self):
        """Exact match against LANGS: `EN` and `xx` fall through to the stored language,
        and `keepParam` false tells the caller to strip them."""
        for case, expect in (("upper_case_param", "fi"), ("bad_param_en_stored", "en")):
            with self.subTest(case=case):
                self.assertEqual(self.l[case]["lang"], expect)
                self.assertFalse(self.l[case]["keepParam"])
                self.assertFalse(self.l[case]["remember"])

    def test_with_nothing_valid_anywhere_the_default_is_finnish(self):
        for case in ("bad_param_nothing_stored", "no_param_nothing_stored",
                     "no_param_bad_stored"):
            with self.subTest(case=case):
                self.assertEqual(self.l[case]["lang"], "fi")
                self.assertFalse(self.l[case]["keepParam"])

    def test_without_a_parameter_the_stored_language_applies_as_before(self):
        self.assertEqual(self.l["no_param_en_stored"]["lang"], "en")
        self.assertFalse(self.l["no_param_en_stored"]["keepParam"])
        self.assertFalse(self.l["no_param_en_stored"]["remember"])

    def test_swedish_is_a_supported_value(self):
        """The pages never write it, but the app has it, so a hand-written link may."""
        self.assertEqual(self.l["sv_link_fi_stored"]["lang"], "sv")

    def test_the_language_decision_never_touches_the_venue_or_the_favourite(self):
        """The result carries only its own three fields; nothing here can reach `fav`
        or `area`."""
        for case, r in self.l.items():
            with self.subTest(case=case):
                self.assertEqual(set(r), {"lang", "remember", "keepParam"})

    def test_toggling_the_language_rewrites_the_parameter(self):
        """Otherwise the value the reader arrived with would put them back on reload."""
        self.assertEqual(self.lu["deep_lang_then_toggle"], "area=sk-tapio&lang=fi")
        self.assertEqual(self.lu["lang_only_then_toggle"], "lang=sv")

    def test_toggling_never_grows_a_language_parameter(self):
        self.assertIsNone(self.lu["area_only_then_toggle"])
        self.assertIsNone(self.lu["plain_visit_then_toggle"])

    def test_an_empty_language_parameter_is_filled_rather_than_ignored(self):
        self.assertEqual(self.lu["empty_lang_param"], "lang=en")


if __name__ == "__main__":
    unittest.main()
