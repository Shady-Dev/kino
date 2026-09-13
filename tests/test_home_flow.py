"""The homepage is a chooser until a location is named (2026-09-13).

tests/home_flow_harness.js runs the real selectVenue(), loadSchedule(), showHome() and
onPopState() from index.html, plus the <head> script that decides the first paint,
against stubbed DOM, history and data. Routing precedence itself (URL, favourite, chooser)
is test_area_routing.py's; this file pins what happens around a pick and Back/Forward.
"""
import json
import pathlib
import shutil
import subprocess
import unittest

import _ctx

HARNESS = pathlib.Path(__file__).resolve().parent / "home_flow_harness.js"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class HomeFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.o = json.loads(out.stdout)

    # 5. a pick loads the screenings and names the location in the URL, saving nothing
    def test_a_pick_from_the_chooser_loads_and_writes_the_url(self):
        s = self.o["pick_from_home"]
        self.assertEqual(s["area"], "v1")
        self.assertEqual(s["search"], "?area=v1")
        self.assertIn("push /?area=v1", s["calls"])
        self.assertIn("fetch data/area-v1.json", s["calls"])
        self.assertIn("render", s["calls"])
        self.assertEqual(s["classes"], ["scoped"])

    def test_a_pick_saves_no_favourite_and_no_last_browsed_slot(self):
        s = self.o["pick_from_home"]
        self.assertEqual(s["prefs"], {"fav": ""})
        self.assertFalse([c for c in s["calls"] if c.startswith("prefs.set")])

    def test_picking_what_the_url_already_names_adds_no_history_entry(self):
        s = self.o["pick_same"]
        self.assertFalse([c for c in s["calls"] if c.startswith("push") or c.startswith("replace")])
        self.assertEqual(s["area"], "v1")

    # 8. asynchronous loading never lands on the chooser
    def test_a_schedule_that_resolves_after_back_to_the_chooser_is_not_drawn(self):
        s = self.o["stale_load"]
        self.assertEqual(s["area"], "")
        self.assertEqual(s["main"], '<section id="home">HOME</section>')
        self.assertNotIn("render", s["calls"])
        self.assertEqual(s["classes"], [])

    def test_a_failure_that_arrives_after_back_to_the_chooser_is_not_drawn_either(self):
        s = self.o["stale_failure"]
        self.assertEqual(s["main"], '<section id="home">HOME</section>')
        self.assertNotIn("ERR", s["main"])
        self.assertEqual(s["area"], "")

    def test_back_to_the_bare_page_restores_the_chooser(self):
        s = self.o["back_to_home"]
        self.assertEqual((s["area"], s["classes"], s["homeNote"]), ("", [], ""))
        self.assertEqual(s["main"], '<section id="home">HOME</section>')
        self.assertIn("renderStatus", s["calls"], "the credit line and banners are cleared")

    def test_forward_to_a_location_shows_it_without_a_new_entry(self):
        s = self.o["forward_to_area"]
        self.assertEqual((s["area"], s["search"]), ("v2", "?area=v2"))
        self.assertIn("fetch data/area-v2.json", s["calls"])
        self.assertFalse([c for c in s["calls"] if c.startswith("push")])

    # 7. an unknown location recovers to the chooser with the note
    def test_a_history_entry_naming_an_unknown_location_shows_the_chooser_with_a_note(self):
        s = self.o["popstate_unknown"]
        self.assertEqual(s["area"], "")
        self.assertEqual(s["homeNote"], "EI LÖYTYNYT")
        self.assertIn("renderHome EI LÖYTYNYT", s["calls"])

    def test_a_hash_only_step_changes_nothing(self):
        s = self.o["popstate_hash_only"]
        self.assertEqual(s["calls"], [])
        self.assertEqual(s["area"], "v1")

    # 9. a film link without a location waits, then opens in the chosen scope
    def test_a_film_link_without_a_location_opens_after_the_pick(self):
        s = self.o["film_link_after_pick"]
        self.assertEqual(s["calls"][-1], "syncSheet")
        self.assertEqual(s["search"], "?area=v1")

    # 1, 4, 7. the first paint decision
    def test_the_head_script_scopes_only_a_link_or_a_favourite(self):
        e = self.o["early"]
        self.assertFalse(e["nothing"]["scoped"])
        self.assertTrue(e["fav"]["scoped"])
        self.assertTrue(e["url"]["scoped"])
        self.assertFalse(e["old_area_slot_only"]["scoped"], "an older build's last-browsed slot")

    def test_the_head_script_survives_corrupt_or_unavailable_storage(self):
        e = self.o["early"]
        for case in ("corrupt", "storage_throws", "storage_throws_with_url"):
            self.assertFalse(e[case]["threw"], case)
        self.assertFalse(e["corrupt"]["scoped"])
        self.assertFalse(e["storage_throws"]["scoped"])


if __name__ == "__main__":
    unittest.main()
