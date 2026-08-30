"""run_site: a provider that is partly stale must not publish itself as fresh.

The failure this guards is the one the pipeline was built against and still had: a
provider with three venues where one parses to nothing keeps that venue's previous file,
and the provider-level file used to stamp `generated: now` over all three. The health
line reads that stamp, so the app said the chain was current while one of its cinemas
sat on days-old showtimes.

Three venues, not two: two would let a version that reports "the last venue's state" or
"any venue's state" pass, because with one good and one bad those are the same answer.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import run


OLD = "2026-08-01T00:00:00+00:00"
NOW = "2026-08-30T12:00:00+00:00"


class FakeModule:
    """Stands in for an adapter: SITES plus fetch_site, which is the whole contract."""
    __name__ = "fakeprovider"

    def __init__(self, per_venue):
        self.per_venue = per_venue

    def fetch_site(self, site):
        return self.per_venue


def show(title, start):
    return {"title": title, "start": start, "url": "https://example.test/x"}


SITE = {
    "provider": "fakechain",
    "label": "Fake Chain",
    "venues": [
        {"id": "fc-a", "name": "Alpha", "short": "Alpha", "city": "Espoo"},
        {"id": "fc-b", "name": "Beta", "short": "Beta", "city": "Espoo"},
        {"id": "fc-c", "name": "Gamma", "short": "Gamma", "city": "Espoo"},
    ],
}


class RunSitePartialTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = pathlib.Path(self.tmp.name)
        self._saved_out = run.OUT
        run.OUT = self.out
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: setattr(run, "OUT", self._saved_out))

    def venues_file(self):
        return json.loads((self.out / "venues-fakechain.json")
                          .read_text(encoding="utf-8"))

    def area(self, vid):
        return json.loads((self.out / f"area-{vid}.json").read_text(encoding="utf-8"))

    def run_site(self, mod, site=SITE, now=NOW):
        """run_site logs to stdout and stderr by design -- the committed run-*.log is
        the thing you read after a run. Swallow it here so a passing suite is quiet."""
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return run.run_site(mod, site, now)

    def seed_previous(self, vid, generated=OLD):
        (self.out / f"area-{vid}.json").write_text(json.dumps({
            "generated": generated, "dates": ["2026-08-01"], "horizon": "2026-08-01",
            "shows": [show("Yesterday's Film", "2026-08-01T18:00:00+03:00")],
        }), encoding="utf-8")

    # -- the partial case ---------------------------------------------------------

    def test_a_stale_venue_is_reported_and_does_not_stamp_the_provider_fresh(self):
        self.seed_previous("fc-b")
        mod = FakeModule({
            "fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
            "fc-b": [],
            "fc-c": [show("C Film", "2026-08-30T20:00:00+03:00")],
        })
        live, total, stale, unverified = self.run_site(mod)

        self.assertEqual(live, 2)
        self.assertEqual(total, 2)
        self.assertEqual(stale, ["fc-b"], "the empty venue was not recorded")

        doc = self.venues_file()
        self.assertEqual(doc["status"], "partial")
        self.assertEqual(doc["stale"], ["fc-b"])
        self.assertEqual(doc["oldest"], OLD,
                         "provider claimed to be as fresh as its newest venue")
        self.assertEqual(doc["generated"], NOW,
                         "`generated` still means when this file was written")

    def test_the_stale_venue_keeps_its_own_data_and_its_own_timestamp(self):
        self.seed_previous("fc-b")
        mod = FakeModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        self.run_site(mod)
        kept = self.area("fc-b")
        self.assertEqual(kept["generated"], OLD)
        self.assertEqual(kept["shows"][0]["title"], "Yesterday's Film")

    def test_every_venue_stays_in_the_picker_including_the_stale_one(self):
        self.seed_previous("fc-b")
        mod = FakeModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        self.run_site(mod)
        self.assertEqual([v["id"] for v in self.venues_file()["venues"]],
                         ["fc-a", "fc-b", "fc-c"])

    def test_the_middle_venue_is_the_stale_one_so_position_cannot_pass_by_luck(self):
        """Guards an implementation that reports only the first or last venue."""
        self.seed_previous("fc-b")
        mod = FakeModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        _, _, stale, unverified = self.run_site(mod)
        self.assertNotIn("fc-a", stale)
        self.assertNotIn("fc-c", stale)

    def test_two_stale_venues_are_both_listed(self):
        self.seed_previous("fc-a", "2026-08-10T00:00:00+00:00")
        self.seed_previous("fc-b", OLD)
        mod = FakeModule({"fc-a": [], "fc-b": [],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        live, _, stale, unverified = self.run_site(mod)
        self.assertEqual(live, 1)
        self.assertEqual(sorted(stale), ["fc-a", "fc-b"])
        self.assertEqual(self.venues_file()["oldest"], OLD, "oldest is not the minimum")

    # -- the healthy case ---------------------------------------------------------

    def test_a_fully_fresh_provider_reports_ok(self):
        mod = FakeModule({v["id"]: [show("F", "2026-08-30T18:00:00+03:00")]
                          for v in SITE["venues"]})
        live, total, stale, unverified = self.run_site(mod)
        self.assertEqual((live, total, stale, unverified), (3, 3, [], []))
        doc = self.venues_file()
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["stale"], [])
        self.assertEqual(doc["oldest"], NOW)

    def test_a_new_venue_with_no_previous_file_is_unverified_not_stale(self):
        """It gets an empty file so the picker does not link to a 404, and its data is
        from now rather than the past, so `stale` would misreport what is wrong. It must
        still not read as healthy: nothing tracked it at all, so a provider with a venue
        that had never produced a showtime published itself as fully ok."""
        mod = FakeModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        _, _, stale, unverified = self.run_site(mod)
        self.assertEqual(stale, [])
        self.assertEqual(unverified, ["fc-b"])
        self.assertEqual(self.area("fc-b")["shows"], [])
        doc = self.venues_file()
        self.assertEqual(doc["status"], "partial",
                         "a venue that has never produced a showtime read as healthy")
        self.assertEqual(doc["unverified"], ["fc-b"])
        self.assertEqual(doc["stale"], [])

    def test_an_empty_venue_stays_unverified_on_the_next_run(self):
        """The bug the `path.exists()` discriminator hid. Run one writes an empty file;
        run two then sees a file and called it stale, claiming previous data that was
        never there -- and its ageing `generated` dragged the provider's `oldest` down
        for a venue that has never had anything to be stale about."""
        mod = FakeModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        self.run_site(mod)                       # run one creates the empty file
        later = "2026-08-31T12:00:00+00:00"
        _, _, stale, unverified = self.run_site(mod, now=later)
        self.assertEqual(stale, [], "an always-empty venue was reported as stale")
        self.assertEqual(unverified, ["fc-b"])
        doc = self.venues_file()
        self.assertEqual(doc["oldest"], later,
                         "a venue that never had data dragged `oldest` backwards")

    def test_unverified_clears_when_the_venue_starts_producing(self):
        empty = FakeModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                            "fc-b": [],
                            "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        self.run_site(empty)
        self.assertEqual(self.venues_file()["status"], "partial")
        full = FakeModule({v["id"]: [show("F", "2026-08-31T18:00:00+03:00")]
                           for v in SITE["venues"]})
        later = "2026-08-31T12:00:00+00:00"
        live, _, stale, unverified = self.run_site(full, now=later)
        self.assertEqual((live, stale, unverified), (3, [], []))
        doc = self.venues_file()
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["unverified"], [])
        self.assertEqual(doc["oldest"], later)

    def test_a_totally_dead_site_writes_no_provider_file(self):
        """Nothing may stamp a fresh timestamp when every venue came back empty."""
        for v in SITE["venues"]:
            self.seed_previous(v["id"])
        mod = FakeModule({v["id"]: [] for v in SITE["venues"]})
        live, _, stale, unverified = self.run_site(mod)
        self.assertEqual(live, 0)
        self.assertEqual(len(stale), 3)
        self.assertFalse((self.out / "venues-fakechain.json").exists())


class GeneratedOfTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)

    def test_reads_the_committed_timestamp(self):
        p = self.dir / "a.json"
        p.write_text(json.dumps({"generated": OLD}), encoding="utf-8")
        self.assertEqual(run.generated_of(p), OLD)

    def test_a_torn_file_is_unknown_rather_than_an_error(self):
        """A run killed mid-write must not stop the next one publishing showtimes."""
        p = self.dir / "torn.json"
        p.write_text('{"generated": "2026-08', encoding="utf-8")
        self.assertEqual(run.generated_of(p), "")
        self.assertEqual(run.generated_of(self.dir / "missing.json"), "")


if __name__ == "__main__":
    unittest.main()
