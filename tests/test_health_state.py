"""The footer must not call a provider healthy while one of its cinemas did not refresh.

The classifier used to be age alone, so a provider whose venue failed to refresh read as
healthy for as long as the data it kept stayed under STALE_H. The collapsed summary said
every source was up to date while the expanded row beside it said (1/12) -- the two
disagreed, and the one a reader sees first was the wrong one.

`healthState` is sliced verbatim out of index.html by tests/health_state_harness.js and
run on its own. It takes provider metadata and an age and returns a string, so it needs
no DOM; the alternatives were stubbing the whole app or splitting the single file, which
this repo deliberately does not do.
"""
import json
import pathlib
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "health_state_harness.js"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class HealthStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.r = json.loads(out.stdout)

    # -- the reported bug ----------------------------------------------------------

    def test_partial_two_hours_old_is_not_healthy(self):
        """status partial, one stale venue, data two hours old. The exact case: well
        inside STALE_H, so age alone called it fine."""
        self.assertEqual(self.r["partial_recent"], "partial")
        self.assertNotEqual(self.r["partial_recent"], "ok")

    def test_the_status_flag_alone_is_enough(self):
        """A provider can be partial with an empty stale list -- everything it kept back
        was unverified rather than stale -- so the flag has to count on its own."""
        self.assertEqual(self.r["partial_flag_only"], "partial")

    def test_a_stale_count_alone_is_enough(self):
        """Guards a file written before `status` existed."""
        self.assertEqual(self.r["stale_count_only"], "partial")

    def test_an_unverified_venue_alone_is_enough(self):
        self.assertEqual(self.r["unverified_only"], "partial")

    def test_the_unverified_count_alone_is_enough(self):
        """Without a `status` field, so only the unverified term can catch it. The first
        version of this file set status:'partial' here too, which meant the term could be
        deleted with every test still green -- found by deleting it."""
        self.assertEqual(self.r["unverified_count_only"], "partial")

    # -- nothing else moved --------------------------------------------------------

    def test_a_fully_fresh_provider_is_still_ok(self):
        self.assertEqual(self.r["fresh_ok"], "ok")

    def test_a_file_from_before_these_fields_is_still_ok(self):
        """Additive schema: no status, no unverified, nothing stale -> healthy."""
        self.assertEqual(self.r["legacy_no_status"], "ok")

    def test_old_data_is_behind(self):
        self.assertEqual(self.r["too_old"], "behind")

    def test_exactly_at_the_threshold_is_not_yet_behind(self):
        self.assertEqual(self.r["exactly_at_threshold"], "ok")

    def test_an_unreadable_timestamp_is_behind(self):
        self.assertEqual(self.r["invalid_timestamp"], "behind")

    # -- severity order ------------------------------------------------------------

    def test_behind_outranks_partial(self):
        """A provider that is both has the worse problem, and the summary line has room
        for one phrase."""
        self.assertEqual(self.r["too_old_and_partial"], "behind")

    def test_gone_outranks_everything(self):
        self.assertEqual(self.r["gone"], "gone")
        self.assertEqual(self.r["gone_but_fresh_age"], "gone")

    def test_absent_metadata_is_gone_not_healthy(self):
        self.assertEqual(self.r["missing_meta"], "gone")


if __name__ == "__main__":
    unittest.main()
