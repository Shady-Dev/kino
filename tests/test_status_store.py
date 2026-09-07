"""How /status/ stays current: one path may reach the network and the other may not.

The loop this pins down shipped on 2026-09-07 and rate-limited the origin. sw.js posts
`{fresh: path}` to every window client after a successful revalidation, including one that
changed nothing; the page answered by loading again, which refetched all 38 metadata files
and produced 38 more messages, in every open tab at once. Five messages took the request
count from 38 to 228.

The source-text checks that were already here did not catch it, because the code read
correctly and the comment above it asserted the opposite of what it did. These drive the
real store through a stubbed `io` and count requests, which is the only thing that would
have failed.
"""
import json
import pathlib
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "status_store_harness.js"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class StatusStoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.r = json.loads(out.stdout)

    # -- the deliberate path -------------------------------------------------------------

    def test_the_first_load_reads_the_list_and_every_file_it_names(self):
        r = self.r["first_load"]
        self.assertEqual(r["paths"], ["/data/providers.json", "/data/areas.json",
                                      "/data/venues-orion.json", "/data/venues-kinometso.json"])
        self.assertEqual(r["providers"], 3)
        self.assertEqual(r["metaKeys"], ["finnkino", "kinometso", "orion"])
        self.assertEqual(r["renders"], 1)

    def test_the_first_load_reads_no_cache(self):
        """It goes through the worker, which serves the cache itself. Reading Cache Storage
        here as well would double every request the page makes."""
        self.assertEqual(self.r["first_load"]["cache"], 0)

    # -- the loop ---------------------------------------------------------------------------

    def test_worker_messages_add_no_network_requests(self):
        """The whole defect in one number. sw.js messages after every revalidation,
        unchanged responses included, so this has to hold for messages that carry nothing
        new: five of them took 38 requests to 228."""
        r = self.r["unchanged_messages"]
        self.assertEqual(r["added"], 0)
        self.assertEqual(r["netAfterMessages"], r["netAfterLoad"])

    def test_worker_messages_are_answered_from_cache_storage(self):
        """Not answered at all would also add no requests, so the cache reads are what
        show the message was actually handled."""
        self.assertGreater(self.r["unchanged_messages"]["cacheReads"], 0)

    def test_a_burst_settles_into_one_pass(self):
        """One message lands per file and a run touches many. Twenty must not schedule
        twenty timers, and must not leave one scheduling the next."""
        r = self.r["burst"]
        self.assertEqual(r["timersScheduled"], 1)
        self.assertEqual(r["netAfter"], 4)
        self.assertEqual(r["rendersTotal"], 1)

    # -- what a message may and may not change -------------------------------------------------

    def test_changed_cached_bytes_update_the_state_and_redraw_once(self):
        r = self.r["changed_message"]
        self.assertEqual(r["before"], "2026-09-07T06:00:00+00:00")
        self.assertEqual(r["after"], "2026-09-07T08:30:00+00:00")
        self.assertEqual(r["rendersAdded"], 1)

    def test_an_unchanged_message_redraws_nothing(self):
        """A render that changes nothing is what folding the burst is trying to avoid."""
        self.assertEqual(self.r["unchanged_no_redraw"]["rendersAdded"], 0)

    def test_a_message_for_a_file_the_cache_does_not_hold_changes_nothing(self):
        """And in particular does not fall back to the network, which would be the loop
        again by another route."""
        r = self.r["cache_miss"]
        self.assertEqual(r["netAdded"], 0)
        self.assertEqual(r["rendersAdded"], 0)
        self.assertTrue(r["orionStillHeld"])

    # -- asking the network on purpose -----------------------------------------------------------

    def test_a_resumed_tab_is_throttled(self):
        """Opened, backgrounded and reopened repeatedly is otherwise 38 requests each time."""
        r = self.r["resume_throttle"]
        self.assertFalse(r["secondRan"])
        self.assertEqual(r["afterSecond"], r["afterFirst"])

    def test_a_later_retry_is_still_allowed(self):
        """The throttle delays a resume; it must not disable one."""
        r = self.r["resume_throttle"]
        self.assertTrue(r["thirdRan"])
        self.assertGreater(r["afterThird"], r["afterFirst"])

    def test_a_forced_load_bypasses_the_throttle(self):
        """Boot, and anything else deliberate."""
        r = self.r["force_bypasses_throttle"]
        self.assertTrue(r["ran"])
        self.assertTrue(r["netGrew"])

    def test_a_slower_earlier_load_does_not_overwrite_a_newer_one(self):
        r = self.r["stale_load_dropped"]
        self.assertFalse(r["slowWrote"])
        self.assertTrue(r["fastWrote"])

    def test_a_failed_provider_list_clears_the_rows_and_records_the_check(self):
        """statusModel reads no rows as "could not check". Keeping the old rows would show
        a list nothing had just verified."""
        r = self.r["provider_list_failed"]
        self.assertEqual(r["heldBefore"], 3)
        self.assertEqual(r["providersAfter"], 0)
        self.assertTrue(r["checkedAtMoved"])


if __name__ == "__main__":
    unittest.main()
