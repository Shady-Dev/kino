"""A background refresh lands in the slot it was asked for, and sees every cinema.

The service worker serves data JSON from its cache and refreshes it behind, and when a
refresh lands it posts `{fresh: path}` to the page. Two things were wrong with what the
page did next.

It re-read the file and then compared and assigned `jsonCache[state.area]` -- reading the
selection *after* the await. A reader who picked cinema B while A's read was in flight got
A's answer written into B's slot and A's programme rendered under B's name, and the
mistake stuck: B's slot held A's payload for as long as the tab lived.

And for a combined city it compared `generated`, which `loadCity` sets to the *oldest*
member's timestamp so the stale banner reports the weakest link. A newer member updating
while the oldest stayed put left that value unchanged, so the refreshed schedule was
discarded. The cooldown that guarded the handler made it worse: it dropped every message
inside sixty seconds, so the members of a city that land a second apart were mostly
thrown away too.

The handler is `makeFreshHandler(io)` and the fold is `cityPayload`, both sliced verbatim
out of index.html by tests/swr_refresh_harness.js. The rules pinned here: the area is read
once, before the await; only that area's slot is compared and written; a render happens
only if that area is still on screen; a slot emptied meanwhile stays empty and a slot
refilled meanwhile keeps the refill, because the entry is compared by identity; a city is
compared on a per-member `stamp` while its `generated` keeps reporting the oldest member;
and the re-read comes from Cache Storage, never from a fetch -- a fetch through the worker
would start another refresh and another message, which is the loop the cooldown existed
for. With no loop to hold back there is no cooldown, and a burst of member messages folds
into one extra read instead of being dropped.
"""
import json
import pathlib
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "swr_refresh_harness.js"

A_GEN = "2026-09-05T06:00:00+00:00"     # the oldest member, and the one that stays put
B_GEN = "2026-09-05T07:00:00+00:00"
B_NEW = "2026-09-05T08:00:00+00:00"
A_NEW = "2026-09-05T09:00:00+00:00"
A_RELOAD = "2026-09-05T10:00:00+00:00"  # what loadSchedule refilled the slot with
A_LATEST = "2026-09-05T11:00:00+00:00"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class BackgroundRefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.r = json.loads(out.stdout)

    # -- the slot a late answer lands in ------------------------------------------------------

    def test_a_late_answer_for_a_never_touches_b(self):
        """The reader switched to B during A's read. B's slot is byte-for-byte what it was."""
        r = self.r["late_answer_after_switch"]
        self.assertEqual(r["B"]["generated"], B_GEN)
        self.assertEqual([s["theatre"] for s in r["B"]["shows"]], ["B"])

    def test_a_late_answer_for_a_is_kept_for_a(self):
        """The payload is not thrown away: A's slot takes it, so returning to A serves the
        refreshed programme without another fetch."""
        r = self.r["late_answer_after_switch"]
        self.assertEqual(r["A"]["generated"], A_NEW)
        self.assertEqual([s["theatre"] for s in r["A"]["shows"]], ["A"])

    def test_a_late_answer_for_a_does_not_redraw_b(self):
        """B is on screen and B did not change. A render here would flash B's own data
        back at the reader for no reason -- or, in the old code, draw A's under B."""
        self.assertEqual(self.r["late_answer_after_switch"]["applied"], 0)

    def test_a_refresh_for_the_cinema_on_screen_is_applied_and_drawn(self):
        r = self.r["answer_still_selected"]
        self.assertEqual(r["A"]["generated"], A_NEW)
        self.assertEqual(r["applied"], 1)
        self.assertEqual(r["B"]["generated"], B_GEN)

    def test_the_same_generated_changes_nothing(self):
        r = self.r["unchanged"]
        self.assertEqual(r["applied"], 0)
        self.assertEqual(r["A"]["generated"], A_GEN)

    def test_a_file_outside_the_selection_reads_nothing(self):
        r = self.r["not_a_hit"]
        self.assertEqual(r["reads"], [])
        self.assertEqual(r["applied"], 0)

    def test_a_selection_with_nothing_loaded_is_left_to_load_schedule(self):
        r = self.r["nothing_held"]
        self.assertEqual(r["reads"], [])
        self.assertEqual(r["keys"], ["B"])

    def test_a_slot_emptied_during_the_read_stays_empty(self):
        """refreshAll clears the whole cache and reloads the selection. A late write here
        would race that reload; the answer is to leave the slot to it."""
        r = self.r["invalidated_during_read"]
        self.assertEqual(r["keys"], [])
        self.assertEqual(r["applied"], 0)

    def test_a_slot_refilled_during_the_read_keeps_the_refill(self):
        """refreshAll emptied A and loadSchedule refilled it with a 10:00 schedule before
        the read answered with a 09:00 snapshot. The refill is the newer one and stays;
        an existence check after the await let the snapshot overwrite it."""
        r = self.r["refilled_during_read"]
        self.assertEqual(r["A"]["generated"], A_RELOAD)
        self.assertEqual([s["title"] for s in r["A"]["shows"]], ["Film at A, reloaded"])
        self.assertEqual(r["applied"], 0)

    def test_a_follow_up_read_compares_against_the_refill(self):
        """A message queued behind the discarded read still gets its follow-up, and that
        follow-up measures against the refilled entry: a newer copy is applied."""
        r = self.r["refilled_then_follow_up"]
        self.assertEqual(r["duringFirst"], 1, "the queued message started no read of its own")
        self.assertEqual(r["afterFirst"]["applied"], 0)
        self.assertEqual(r["afterFirst"]["generated"], A_RELOAD)
        self.assertEqual(r["afterFirst"]["reads"], 2, "exactly one follow-up read")
        self.assertEqual(r["A"]["generated"], A_LATEST)
        self.assertEqual(r["applied"], 1)
        self.assertEqual(r["pending"], 0)

    def test_a_follow_up_for_an_emptied_slot_reads_nothing(self):
        """Emptied and not refilled: there is nothing to compare a read against, so the
        queued message costs no read and the slot is left to whoever emptied it."""
        r = self.r["emptied_then_follow_up"]
        self.assertEqual(r["reads"], 1)
        self.assertEqual(r["applied"], 0)
        self.assertEqual(r["keys"], ["B"])
        self.assertEqual(r["pending"], 0)

    # -- the fold: freshness stays the oldest member's ------------------------------------------

    def test_a_city_reports_its_oldest_member(self):
        """The stale banner's contract, unchanged: the weakest link and its provider."""
        f = self.r["fold"]
        self.assertEqual((f["both"]["generated"], f["both"]["oldest"]), (A_GEN, "p1"))
        self.assertEqual((f["a_newer"]["generated"], f["a_newer"]["oldest"]), (B_GEN, "p2"))
        self.assertEqual((f["a_missing"]["generated"], f["a_missing"]["oldest"]), (B_GEN, "p2"))
        self.assertEqual(f["a_missing"]["missing"], ["A"])
        self.assertEqual((f["none"]["generated"], f["none"]["missing"]), ("", ["A", "B"]))

    def test_the_change_key_is_not_the_freshness_timestamp(self):
        """One member changing must move the key even when `generated` cannot move."""
        f = self.r["fold"]
        self.assertNotEqual(f["both"]["key"], f["a_newer"]["key"])
        self.assertNotEqual(f["both"]["key"], f["a_missing"]["key"])
        self.assertNotEqual(f["both"]["key"], f["none"]["key"])
        self.assertTrue(f["none"]["key"], "an empty city still has a key to compare against")

    # -- the reported defect ----------------------------------------------------------------------

    def test_a_newer_member_updating_is_adopted(self):
        """Cinema A's timestamp is fixed and stays the oldest; cinema B refreshes with a new
        timestamp and a new show. The combined view must take B's update."""
        r = self.r["newer_member_updates"]
        self.assertEqual(r["applied"], 1)
        self.assertIn("Film at b, later", r["city"]["titles"])
        self.assertNotIn("Film at b", r["city"]["titles"])
        self.assertIn("Film at a", r["city"]["titles"])

    def test_the_adopted_view_still_reports_a_for_freshness(self):
        """B moved, A did not, so the banner keeps naming A's age and A's provider."""
        r = self.r["newer_member_updates"]
        self.assertEqual(r["city"]["generated"], A_GEN)
        self.assertEqual(r["city"]["oldest"], "p1")
        self.assertEqual(r["A"]["generated"], A_GEN, "a city refresh must not write into a venue's slot")

    def test_the_oldest_member_updating_moves_the_freshness_source(self):
        r = self.r["oldest_member_updates"]
        self.assertEqual(r["applied"], 1)
        self.assertEqual((r["city"]["generated"], r["city"]["oldest"]), (B_GEN, "p2"))
        self.assertIn("Film at a, later", r["city"]["titles"])

    def test_a_member_dropping_out_or_coming_back_is_a_change(self):
        gone = self.r["member_goes_missing"]
        self.assertEqual(gone["applied"], 1)
        self.assertEqual(gone["city"]["missing"], ["B"])
        self.assertEqual(gone["city"]["titles"], ["Film at a"])
        back = self.r["member_comes_back"]
        self.assertEqual(back["applied"], 1)
        self.assertEqual(back["city"]["missing"], [])
        self.assertEqual(sorted(back["city"]["titles"]), ["Film at a", "Film at b"])

    def test_a_city_where_nothing_moved_is_left_alone(self):
        r = self.r["city_unchanged"]
        self.assertEqual(r["applied"], 0)

    # -- the cooldown's replacement --------------------------------------------------------------

    def test_messages_during_a_read_fold_into_one_more_read(self):
        """Three messages while the first read runs: one read in flight, none started for
        the second and third, exactly one follow-up read after the first settles, and that
        follow-up sees the member that landed late."""
        r = self.r["burst"]
        self.assertEqual(r["afterFirst"], 2, "the first read fetched both members")
        self.assertEqual(r["duringFirst"], 2, "messages during the read start nothing")
        self.assertEqual(r["afterSecondStarted"], 4, "one follow-up read, not one per message")
        self.assertEqual(r["settled"], 4)
        self.assertIn("Film at b, later", r["city"]["titles"])
        self.assertIn("Film at a, later", r["city"]["titles"])

    def test_a_burst_renders_each_time_something_changed(self):
        """The first read carried a's update, the follow-up b's; the read after the drain
        found nothing new and drew nothing."""
        self.assertEqual(self.r["burst"]["applied"], 2)

    def test_after_the_drain_a_new_message_reads_again(self):
        """Nothing is dropped and nothing is swallowed once the drain is over."""
        r = self.r["burst"]
        self.assertEqual(r["afterFourth"], 6)
        self.assertEqual(r["pending"], 0)

    def test_the_re_read_comes_from_cache_storage_not_the_network(self):
        """A fetch through the worker would start another background refresh and another
        message -- the loop the cooldown used to hold back. The harness has no fetch at
        all, so a reader that reached for one would have failed above."""
        r = self.r["read_cached"]
        self.assertEqual(r["hit"]["generated"], A_GEN)
        self.assertIn("not cached", r["miss"])
        self.assertFalse(r["fetchDefined"])


if __name__ == "__main__":
    unittest.main()
