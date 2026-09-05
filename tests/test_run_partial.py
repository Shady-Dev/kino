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


class RunSiteHarness(unittest.TestCase):
    """Temporary OUT plus the helpers; the test classes below inherit it."""
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


class RunSitePartialTest(RunSiteHarness):

    # -- the partial case ---------------------------------------------------------

    def test_a_stale_venue_is_reported_and_does_not_stamp_the_provider_fresh(self):
        self.seed_previous("fc-b")
        mod = FakeModule({
            "fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
            "fc-b": [],
            "fc-c": [show("C Film", "2026-08-30T20:00:00+03:00")],
        })
        live, total, stale, unverified, pending = self.run_site(mod)

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
        _, _, stale, unverified, _ = self.run_site(mod)
        self.assertNotIn("fc-a", stale)
        self.assertNotIn("fc-c", stale)

    def test_two_stale_venues_are_both_listed(self):
        self.seed_previous("fc-a", "2026-08-10T00:00:00+00:00")
        self.seed_previous("fc-b", OLD)
        mod = FakeModule({"fc-a": [], "fc-b": [],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        live, _, stale, unverified, _ = self.run_site(mod)
        self.assertEqual(live, 1)
        self.assertEqual(sorted(stale), ["fc-a", "fc-b"])
        self.assertEqual(self.venues_file()["oldest"], OLD, "oldest is not the minimum")

    # -- the healthy case ---------------------------------------------------------

    def test_a_fully_fresh_provider_reports_ok(self):
        mod = FakeModule({v["id"]: [show("F", "2026-08-30T18:00:00+03:00")]
                          for v in SITE["venues"]})
        live, total, stale, unverified, pending = self.run_site(mod)
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
        _, _, stale, unverified, _ = self.run_site(mod)
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
        _, _, stale, unverified, _ = self.run_site(mod, now=later)
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
        live, _, stale, unverified, _ = self.run_site(full, now=later)
        self.assertEqual((live, stale, unverified), (3, [], []))
        doc = self.venues_file()
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["unverified"], [])
        self.assertEqual(doc["oldest"], later)

    # -- pending: only on the adapter's word ----------------------------------------

    def test_a_confirmed_empty_venue_is_pending_not_unverified(self):
        """An adapter that sets EMPTY_VENUES_CONFIRMED vouches that a venue it reported
        with an empty list is known empty -- nexxo's schema check makes that positive
        evidence. Such a venue is a programme that has not started, and the provider
        file must not read partial over it."""
        mod = FakeModule({
            "fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
            "fc-b": [],
            "fc-c": [show("C Film", "2026-08-30T20:00:00+03:00")],
        })
        mod.EMPTY_VENUES_CONFIRMED = True
        _, _, stale, unverified, _ = self.run_site(mod)
        self.assertEqual(unverified, [])
        self.assertEqual(stale, [])
        doc = self.venues_file()
        self.assertEqual(doc["pending"], ["fc-b"])
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(json.loads(
            (self.out / "area-fc-b.json").read_text(encoding="utf-8"))["shows"], [])

    def test_without_the_module_flag_the_same_venue_stays_unverified(self):
        """run.py cannot tell "programme not started" from "parse never worked", so the
        quiet state exists only where the adapter can."""
        mod = FakeModule({
            "fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
            "fc-b": [],
            "fc-c": [show("C Film", "2026-08-30T20:00:00+03:00")],
        })
        _, _, _, unverified, _ = self.run_site(mod)
        self.assertEqual(unverified, ["fc-b"])
        doc = self.venues_file()
        self.assertEqual(doc["pending"], [])
        self.assertEqual(doc["status"], "partial")

    def test_the_flag_does_not_cover_a_venue_the_adapter_never_reported(self):
        """Key absent means the adapter has nothing to vouch for -- the locationid
        failed, or the venue fell out of the answer -- and that is the ambiguous case."""
        mod = FakeModule({
            "fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
            "fc-c": [show("C Film", "2026-08-30T20:00:00+03:00")],
        })
        mod.EMPTY_VENUES_CONFIRMED = True
        _, _, _, unverified, _ = self.run_site(mod)
        self.assertEqual(unverified, ["fc-b"])
        self.assertEqual(self.venues_file()["pending"], [])

    def test_a_confirmed_empty_venue_with_previous_data_is_pending_not_stale(self):
        """Reversed on 2026-09-05. Until then real older data outranked the adapter's word
        that today's answer is empty, so a touring cinema's town kept its last, past show
        and read "did not refresh" for weeks after its programme had ended. The adapter's
        confirmation is the same evidence `pending` already trusts; the old file does not
        change what the upstream said today. See ConfirmedEmptyTest for the full shape."""
        self.seed_previous("fc-b")
        mod = FakeModule({
            "fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
            "fc-b": [],
            "fc-c": [show("C Film", "2026-08-30T20:00:00+03:00")],
        })
        mod.EMPTY_VENUES_CONFIRMED = True
        _, _, stale, _, pending = self.run_site(mod)
        self.assertEqual((stale, pending), ([], ["fc-b"]))
        self.assertEqual(self.venues_file()["pending"], ["fc-b"])
        self.assertEqual(self.area("fc-b")["shows"], [])

    def test_a_totally_dead_site_writes_no_provider_file(self):
        """Nothing may stamp a fresh timestamp when every venue came back empty."""
        for v in SITE["venues"]:
            self.seed_previous(v["id"])
        mod = FakeModule({v["id"]: [] for v in SITE["venues"]})
        live, _, stale, unverified, _ = self.run_site(mod)
        self.assertEqual(live, 0)
        self.assertEqual(len(stale), 3)
        self.assertFalse((self.out / "venues-fakechain.json").exists())


class SummaryLineTest(unittest.TestCase):
    """The run's one-line verdict must count pending venues: run-nexxo.log read
    "0 stale, 0 unverified, 0 with no programme" while Tikkakoski sat pending, which
    made the summary read as if the venue did not exist."""

    def test_pending_venues_are_counted(self):
        line = run.summary_line(["nexxo"], 12, 152,
                                partial=[], pendings=[("kinometso", ["km-tikkakoski"])],
                                empty=[], failures=0)
        self.assertIn("1 pending", line)
        self.assertIn("0 stale, 0 unverified, 1 pending, 0 with no programme", line)

    def test_pending_is_not_a_failure_or_a_partial(self):
        line = run.summary_line(["nexxo"], 12, 152,
                                partial=[], pendings=[("kinometso", ["a", "b"])],
                                empty=[], failures=0)
        self.assertIn("2 pending", line)
        self.assertIn("0 failures", line)
        self.assertIn("0 stale", line)


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


class ConfirmedModule(FakeModule):
    """An adapter that vouches for emptiness: a venue it reports with [] was answered in
    schema and listed nothing (nexxo). Its word outranks a previous file."""
    __name__ = "fakeconfirmed"
    EMPTY_VENUES_CONFIRMED = True


class FailingModule(FakeModule):
    __name__ = "fakefailing"
    EMPTY_VENUES_CONFIRMED = True

    def fetch_site(self, site):
        raise RuntimeError("upstream unreachable")


FOUR = {
    "provider": "fakechain",
    "label": "Fake Touring Cinema",
    "venues": [
        {"id": "fc-a", "name": "Alpha", "short": "Alpha", "city": "Espoo"},
        {"id": "fc-b", "name": "Beta", "short": "Beta", "city": "Espoo"},
        {"id": "fc-c", "name": "Gamma", "short": "Gamma", "city": "Espoo"},
        {"id": "fc-d", "name": "Delta", "short": "Delta", "city": "Espoo"},
    ],
}


class ConfirmedEmptyTest(RunSiteHarness):
    """Confirmed empty beats kept data (2026-09-05). Kino Metso's Muurame had one show,
    its last for now; the next run found the town empty, kept the past show, marked the
    venue stale and pinned the provider's `oldest` to it. The adapter had confirmed the
    emptiness and was not asked. The invariant: confirmed empty publishes a fresh empty
    file in the quiet state whether or not old data exists; zero rows without
    confirmation keeps the previous file as stale; a failure never replaces anything."""

    def test_confirmed_empty_with_an_old_file_is_pending_not_stale(self):
        self.seed_previous("fc-b")
        mod = ConfirmedModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                               "fc-b": [],
                               "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        live, total, stale, unverified, pending = self.run_site(mod)
        self.assertEqual((live, total), (2, 2))
        self.assertEqual(stale, [], "the programme had ended; that is not stale data")
        self.assertEqual(pending, ["fc-b"])
        self.assertEqual(unverified, [])
        empty = self.area("fc-b")
        self.assertEqual(empty["shows"], [], "the past show was kept")
        self.assertEqual(empty["generated"], NOW, "the empty file was not stamped fresh")
        doc = self.venues_file()
        self.assertEqual(doc["status"], "ok")
        self.assertEqual((doc["stale"], doc["pending"]), ([], ["fc-b"]))
        self.assertEqual(doc["oldest"], NOW, "an ended programme dragged `oldest` down")

    def test_confirmed_empty_with_no_file_is_pending_as_before(self):
        mod = ConfirmedModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                               "fc-b": [],
                               "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        _, _, stale, unverified, pending = self.run_site(mod)
        self.assertEqual((stale, unverified, pending), ([], [], ["fc-b"]))
        self.assertEqual(self.area("fc-b")["shows"], [])
        self.assertEqual(self.venues_file()["status"], "ok")

    def test_zero_rows_without_confirmation_still_keeps_the_previous_file(self):
        """The same answer from a module that cannot vouch for it: stale, kept."""
        self.seed_previous("fc-b")
        mod = FakeModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        _, _, stale, unverified, pending = self.run_site(mod)
        self.assertEqual((stale, pending), (["fc-b"], []))
        self.assertEqual(self.area("fc-b")["generated"], OLD)
        self.assertEqual(self.venues_file()["status"], "partial")

    def test_a_confirming_module_that_did_not_report_the_venue_does_not_get_pending(self):
        """The flag alone is not evidence; the venue has to be in the adapter's answer."""
        self.seed_previous("fc-b")
        mod = ConfirmedModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                               "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        _, _, stale, unverified, pending = self.run_site(mod)
        self.assertEqual((stale, pending), (["fc-b"], []))
        self.assertEqual(self.area("fc-b")["generated"], OLD)

    def test_a_failed_fetch_never_replaces_previous_data(self):
        self.seed_previous("fc-a"); self.seed_previous("fc-b"); self.seed_previous("fc-c")
        with self.assertRaises(RuntimeError):
            self.run_site(FailingModule({}))
        for vid in ("fc-a", "fc-b", "fc-c"):
            self.assertEqual(self.area(vid)["generated"], OLD, vid)
            self.assertEqual(self.area(vid)["shows"][0]["title"], "Yesterday's Film")
        self.assertFalse((self.out / "venues-fakechain.json").exists(),
                         "a failed site must not publish a provider file")

    def test_a_single_venue_site_confirmed_empty_publishes_fresh_empty_files(self):
        """Heureka's shape: one venue, a paused programme. The old screenings go, the empty
        file is stamped now, the provider file is written with the venue pending."""
        one = {**SITE, "venues": SITE["venues"][:1]}
        self.seed_previous("fc-a")
        mod = ConfirmedModule({"fc-a": []})
        live, total, stale, unverified, pending = self.run_site(mod, site=one)
        self.assertEqual((live, total, stale, unverified, pending), (0, 0, [], [], ["fc-a"]))
        self.assertEqual(self.area("fc-a")["shows"], [])
        self.assertEqual(self.area("fc-a")["generated"], NOW)
        doc = self.venues_file()
        self.assertEqual((doc["status"], doc["pending"], doc["oldest"]), ("ok", ["fc-a"], NOW))
        self.assertEqual([v["id"] for v in doc["venues"]], ["fc-a"])

    def test_every_venue_confirmed_empty_writes_the_provider_file(self):
        self.seed_previous("fc-b")
        mod = ConfirmedModule({"fc-a": [], "fc-b": [], "fc-c": []})
        live, _, stale, unverified, pending = self.run_site(mod)
        self.assertEqual((live, stale, unverified, sorted(pending)), (0, [], [], ["fc-a", "fc-b", "fc-c"]))
        self.assertEqual(self.venues_file()["status"], "ok")
        self.assertEqual(self.area("fc-b")["shows"], [])

    def test_pending_beside_an_unexplained_venue_with_no_live_one_writes_no_provider_file(self):
        """Two venues confirmed empty and one the adapter did not report: part of the site
        is unexplained, so nothing is stamped fresh at provider level."""
        self.seed_previous("fc-b")
        mod = ConfirmedModule({"fc-a": [], "fc-c": []})
        live, _, stale, unverified, pending = self.run_site(mod)
        self.assertEqual((live, stale, sorted(pending)), (0, ["fc-b"], ["fc-a", "fc-c"]))
        self.assertFalse((self.out / "venues-fakechain.json").exists())
        self.assertEqual(self.area("fc-b")["generated"], OLD)

    def test_an_unconfirmed_empty_single_venue_site_writes_no_provider_file(self):
        one = {**SITE, "venues": SITE["venues"][:1]}
        self.seed_previous("fc-a")
        live, _, stale, unverified, pending = self.run_site(FakeModule({"fc-a": []}), site=one)
        self.assertEqual((live, stale, unverified, pending), (0, ["fc-a"], [], []))
        self.assertFalse((self.out / "venues-fakechain.json").exists())
        self.assertEqual(self.area("fc-a")["shows"][0]["title"], "Yesterday's Film")

    def test_a_touring_cinema_with_two_empty_towns_reads_ok_and_ages_on_its_live_venues(self):
        """Kino Metso's shape: one town whose programme ended (old file), one that has
        never had one, two with showtimes. The provider is ok, both towns pending, and
        `oldest` comes from the live venues, all stamped now."""
        self.seed_previous("fc-b")
        mod = ConfirmedModule({"fc-a": [show("A", "2026-08-30T18:00:00+03:00")],
                               "fc-b": [], "fc-c": [],
                               "fc-d": [show("D", "2026-09-19T14:00:00+03:00")]})
        live, total, stale, unverified, pending = self.run_site(mod, site=FOUR)
        self.assertEqual((live, total), (2, 2))
        self.assertEqual((stale, unverified, sorted(pending)), ([], [], ["fc-b", "fc-c"]))
        doc = self.venues_file()
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["oldest"], NOW)
        self.assertEqual(sorted(doc["pending"]), ["fc-b", "fc-c"])
        self.assertEqual([v["id"] for v in doc["venues"]], ["fc-a", "fc-b", "fc-c", "fc-d"])


if __name__ == "__main__":
    unittest.main()


class EnrichmentCarriedForwardTest(unittest.TestCase):
    """A rewrite must not drop what only the TMDB pass can supply.

    In the cloud this was invisible: enrich_tmdb runs straight after run.py and puts the
    fields back. On the local half nothing does, so Kino Engel and Kino Akseli lost their
    ratings, trailers and genre ids on every run and got them back only when the next
    cloud run landed. Measured on the real data before the fix: 38 of 38 Engel showtimes
    and 12 of 12 Akseli went from a full set to zero.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = pathlib.Path(self.tmp.name)
        saved = run.OUT
        run.OUT = self.out
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: setattr(run, "OUT", saved))

    def run_site(self, mod, site=SITE, now=NOW):
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return run.run_site(mod, site, now)

    def seed_enriched(self, vid, title="A Film"):
        (self.out / f"area-{vid}.json").write_text(json.dumps({
            "generated": OLD, "dates": ["2026-08-01"], "horizon": "2026-08-01",
            "shows": [dict(show(title, "2026-08-01T18:00:00+03:00"),
                           tmdbId=1234, tmdb=7.4, votes=310,
                           tr="https://youtu.be/x", gids=[18, 35])],
        }), encoding="utf-8")

    def area(self, vid):
        return json.loads((self.out / f"area-{vid}.json").read_text(encoding="utf-8"))

    def test_a_rewrite_keeps_the_enrichment_it_cannot_regenerate(self):
        self.seed_enriched("fc-a")
        mod = FakeModule({"fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [show("B", "2026-08-30T19:00:00+03:00")],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        self.run_site(mod)
        s = self.area("fc-a")["shows"][0]
        self.assertEqual(s["tmdbId"], 1234)
        self.assertEqual(s["tmdb"], 7.4)
        self.assertEqual(s["votes"], 310)
        self.assertEqual(s["tr"], "https://youtu.be/x")
        self.assertEqual(s["gids"], [18, 35],
                         "gids drives genre names and the kids filter, not just a badge")
        self.assertEqual(s["start"][:10], "2026-08-30", "the showtime itself is fresh")

    def test_a_film_that_was_not_there_before_gets_nothing(self):
        self.seed_enriched("fc-a", title="Some Other Film")
        mod = FakeModule({"fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [show("B", "2026-08-30T19:00:00+03:00")],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        self.run_site(mod)
        s = self.area("fc-a")["shows"][0]
        for k in run.ENRICHED:
            self.assertNotIn(k, s)

    def test_the_adapter_wins_over_a_carried_value(self):
        """A floor, never an override: a provider that publishes its own value keeps it,
        and the next enrichment pass overwrites the lot regardless."""
        self.seed_enriched("fc-a")
        fresh = dict(show("A Film", "2026-08-30T18:00:00+03:00"), tmdb=9.9)
        mod = FakeModule({"fc-a": [fresh],
                          "fc-b": [show("B", "2026-08-30T19:00:00+03:00")],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        self.run_site(mod)
        s = self.area("fc-a")["shows"][0]
        self.assertEqual(s["tmdb"], 9.9)
        self.assertEqual(s["tmdbId"], 1234, "the other fields still carry")

    def test_an_unreadable_previous_file_is_not_fatal(self):
        (self.out / "area-fc-a.json").write_text('{"shows": [', encoding="utf-8")
        mod = FakeModule({"fc-a": [show("A Film", "2026-08-30T18:00:00+03:00")],
                          "fc-b": [show("B", "2026-08-30T19:00:00+03:00")],
                          "fc-c": [show("C", "2026-08-30T20:00:00+03:00")]})
        live, _, _, _, _ = self.run_site(mod)
        self.assertEqual(live, 3)
