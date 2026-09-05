"""A background refresh must land in the slot it was asked for, not the one on screen.

The service worker serves data JSON from its cache and refreshes it behind, and when a
refresh lands it posts `{fresh: path}` to the page. The page's handler re-read the file
and then compared and assigned `jsonCache[state.area]` -- reading the selection *after*
the await. A reader who picked cinema B while A's read was in flight got A's answer
written into B's slot and A's programme rendered under B's name, and the mistake stuck:
B's slot now held A's payload for as long as the tab lived.

The handler is `makeFreshHandler(io)`, sliced verbatim out of index.html by
tests/swr_refresh_harness.js and driven with reads the scenario settles by hand -- that is
the only way to put "switched during the await" under test. The rule it pins: the area is
read once, before the await; only that area's slot is compared and written; a render
happens only if that area is still the one on screen; and a slot emptied meanwhile stays
empty, because whoever emptied it is reloading it.
"""
import json
import pathlib
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "swr_refresh_harness.js"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class BackgroundRefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.r = json.loads(out.stdout)

    # -- the reported defect ------------------------------------------------------------

    def test_a_late_answer_for_a_never_touches_b(self):
        """The reader switched to B during A's read. B's slot is byte-for-byte what it was."""
        r = self.r["late_answer_after_switch"]
        self.assertEqual(r["B"]["generated"], "2026-09-05T07:00:00+00:00")
        self.assertEqual([s["theatre"] for s in r["B"]["shows"]], ["B"])

    def test_a_late_answer_for_a_is_kept_for_a(self):
        """The payload is not thrown away: A's slot takes it, so returning to A serves the
        refreshed programme without another fetch."""
        r = self.r["late_answer_after_switch"]
        self.assertEqual(r["A"]["generated"], "2026-09-05T09:00:00+00:00")
        self.assertEqual([s["theatre"] for s in r["A"]["shows"]], ["A"])

    def test_a_late_answer_for_a_does_not_redraw_b(self):
        """B is on screen and B did not change. A render here would flash B's own data
        back at the reader for no reason -- or, in the old code, draw A's under B."""
        self.assertEqual(self.r["late_answer_after_switch"]["applied"], 0)

    # -- the ordinary case, unchanged ------------------------------------------------------

    def test_a_refresh_for_the_cinema_on_screen_is_applied_and_drawn(self):
        r = self.r["answer_still_selected"]
        self.assertEqual(r["A"]["generated"], "2026-09-05T09:00:00+00:00")
        self.assertEqual(r["applied"], 1)
        self.assertEqual(r["B"]["generated"], "2026-09-05T07:00:00+00:00")

    def test_the_same_generated_changes_nothing(self):
        r = self.r["unchanged"]
        self.assertEqual(r["applied"], 0)
        self.assertEqual(r["A"]["generated"], "2026-09-05T06:00:00+00:00")

    def test_a_member_file_refreshes_the_selected_city(self):
        r = self.r["city_member"]
        self.assertEqual(r["reads"], ["data/area-a.json", "data/area-b.json"])
        self.assertEqual(r["applied"], 1)
        self.assertEqual(r["A"]["generated"], "2026-09-05T06:00:00+00:00",
                         "a city refresh must not write into a venue's slot")

    def test_a_file_outside_the_selection_reads_nothing(self):
        r = self.r["not_a_hit"]
        self.assertEqual(r["reads"], [])
        self.assertEqual(r["applied"], 0)

    def test_a_selection_with_nothing_loaded_is_left_to_load_schedule(self):
        r = self.r["nothing_held"]
        self.assertEqual(r["reads"], [])
        self.assertEqual(r["keys"], ["B"])

    # -- invalidation during the await ----------------------------------------------------

    def test_a_slot_emptied_during_the_read_stays_empty(self):
        """refreshAll clears the whole cache and reloads the selection. A late write here
        would race that reload; the answer is to leave the slot to it."""
        r = self.r["invalidated_during_read"]
        self.assertEqual(r["keys"], [])
        self.assertEqual(r["applied"], 0)


if __name__ == "__main__":
    unittest.main()
