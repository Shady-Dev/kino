"""Ritz Vaasa and Tähti Kino, read through The Events Calendar's REST route.

The fixtures are the API's own shape as read on 2026-09-18. What they exist to prove:

- **A calendar is not a programme.** 6 of 56 events at Ritz and 3 of 35 at Muhos are films.
  The category does the filtering, server-side, and the answer is checked: an event without
  the configured id fails the site rather than publishing a council meeting.
- **Pagination is followed.** Ritz's window needed two pages the day this was written.
- **Both timestamps are read**, and a disagreement between the local one and the UTC one is
  the fault that would move every screening by hours with no other symptom.
- **`cost_details.values` decides the price.** One value publishes, two are a band.
- **A generic calendar image is not a poster.** Muhos illustrates every film with the same
  768x470 PNG.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import registry
import run
import tribe as T


RITZ = next(s for s in T.SITES if s["provider"] == "ritzvaasa")
MUHOS = next(s for s in T.SITES if s["provider"] == "tahtikino")

SYN_FI = ("Klaus Härön draama kertoo kahden naisen kohtaamisesta keskellä hoitoalan "
          "kriisiä, kun sairaanhoitajat uhkaavat lakolla ja hän joutuu venymään.")
POSTER = {"url": "https://ritz.fi/wp-content/uploads/2026/09/juliste.jpg",
          "width": 1500, "height": 2138}
# The one Muhos puts on every film, and Ritz's concert art, both landscape.
CALENDAR_IMG = {"url": "https://muhos.fi/wp-content/uploads/2026/09/Tapahtumakalenteri.png",
                "width": 768, "height": 470}


def event(eid, title, local, utc, cost="10€", values=("10",), image=None, cat=19,
          all_day=False, syn=SYN_FI, url=None, zone="Europe/Helsinki"):
    """One event as the route returns it."""
    return {
        "id": eid,
        "title": title,
        "description": f"<p>{syn}</p>" if syn else "",
        "start_date": local,
        "utc_start_date": utc,
        "timezone": zone,
        "all_day": all_day,
        "cost": cost,
        "cost_details": {"currency_symbol": "€", "values": list(values)},
        "url": url or f"https://ritz.fi/fi/event/{eid}/",
        "image": image,
        "categories": [{"id": cat, "name": "Kino", "slug": "kino"}],
    }


def page(events, total=None, pages=1):
    return {"events": events, "total": total if total is not None else len(events),
            "total_pages": pages}


TWO = [event(1, "Donnie Darko", "2026-09-27 17:00:00", "2026-09-27 14:00:00"),
       event(2, "Blue Baby", "2026-09-29 19:30:00", "2026-09-29 16:30:00",
             cost="10€ – 12€", values=("10", "12"))]


class ParseTest(unittest.TestCase):
    def test_the_local_and_utc_stamps_agree_and_the_offset_is_helsinki(self):
        shows, _ = T.parse(RITZ, TWO)
        self.assertEqual([s["start"] for s in shows["ritz-vaasa"]],
                         ["2026-09-27T17:00:00+03:00", "2026-09-29T19:30:00+03:00"])

    def test_winter_time_converts_at_two_hours(self):
        shows, _ = T.parse(RITZ, [
            event(1, "A", "2026-12-12 19:30:00", "2026-12-12 17:30:00"),
            event(2, "B", "2026-12-13 15:00:00", "2026-12-13 13:00:00")])
        self.assertEqual([s["start"] for s in shows["ritz-vaasa"]],
                         ["2026-12-12T19:30:00+02:00", "2026-12-13T15:00:00+02:00"])

    def test_stamps_that_contradict_each_other_fail_the_site(self):
        with self.assertRaises(T.EventError) as e:
            T.parse(RITZ, [TWO[0],
                           event(9, "Drift", "2026-09-27 17:00:00", "2026-09-27 17:00:00")])
        self.assertIn("UTC", str(e.exception))

    def test_a_stamp_pair_from_another_zone_fails_on_the_comparison(self):
        """Stockholm's 17:00 is 15:00 UTC, which is not 17:00 in Helsinki. No separate
        guard on the `timezone` field: it would refuse only what this already refuses."""
        with self.assertRaises(T.EventError):
            T.parse(RITZ, [event(1, "A", "2026-09-27 17:00:00", "2026-09-27 15:00:00",
                                 zone="Europe/Stockholm")])

    def test_an_event_without_the_configured_category_fails_the_site(self):
        """The server filters; this checks that it did."""
        with self.assertRaises(T.EventError) as e:
            T.parse(RITZ, [TWO[0], event(3, "Kunnanvaltuusto", "2026-09-28 18:00:00",
                                         "2026-09-28 15:00:00", cat=44)])
        self.assertIn("did not filter", str(e.exception))

    def test_one_cost_value_publishes_and_two_are_a_band(self):
        shows, report = T.parse(RITZ, TWO)
        self.assertEqual([s["price"] for s in shows["ritz-vaasa"]], ["10€", ""])
        self.assertEqual(report["band_price"], 1)

    def test_a_free_screening_keeps_the_word_the_cinema_used(self):
        shows, _ = T.parse(RITZ, [event(1, "Nordic Film", "2026-10-07 16:15:00",
                                        "2026-10-07 13:15:00", cost="Free",
                                        values=("0",))])
        self.assertEqual(shows["ritz-vaasa"][0]["price"], "Free")

    def test_a_portrait_image_publishes_and_a_calendar_illustration_does_not(self):
        shows, _ = T.parse(RITZ, [
            event(1, "A", "2026-09-27 17:00:00", "2026-09-27 14:00:00", image=POSTER),
            event(2, "B", "2026-09-28 17:00:00", "2026-09-28 14:00:00",
                  image=CALENDAR_IMG)])
        self.assertEqual([s["img"] for s in shows["ritz-vaasa"]], [POSTER["url"], ""])

    def test_a_portrait_thumbnail_is_too_small_to_be_a_poster(self):
        shows, _ = T.parse(RITZ, [event(1, "A", "2026-09-27 17:00:00",
                                        "2026-09-27 14:00:00",
                                        image={"url": "https://ritz.fi/x.jpg",
                                               "width": 120, "height": 180})])
        self.assertEqual(shows["ritz-vaasa"][0]["img"], "")

    def test_an_all_day_event_is_left_out_and_counted(self):
        shows, report = T.parse(RITZ, [TWO[0],
                                       event(3, "Festivaaliviikko", "2026-10-01 00:00:00",
                                             "2026-09-30 21:00:00", all_day=True)])
        self.assertEqual(len(shows["ritz-vaasa"]), 1)
        self.assertEqual(report["all_day"], ["Festivaaliviikko"])

    def test_the_synopsis_carries_its_language_and_an_unplaceable_one_is_withheld(self):
        shows, report = T.parse(RITZ, [
            TWO[0],
            event(3, "B", "2026-09-30 17:00:00", "2026-09-30 14:00:00",
                  syn="Troija. Ithaka. Kirke. Kalypso. Skylla. Poseidon. Penelope.")])
        self.assertEqual(shows["ritz-vaasa"][0]["_syn"], {"fi": SYN_FI})
        self.assertNotIn("_syn", shows["ritz-vaasa"][1])
        self.assertEqual(report["unplaced_syn"], {"B"})

    def test_the_show_shape(self):
        shows, _ = T.parse(MUHOS, [event(7, "Hetki ennen valoa", "2026-09-19 17:00:00",
                                         "2026-09-19 14:00:00", cost="13 €",
                                         values=("13",), cat=106,
                                         url="https://muhos.fi/tapahtuma/hetki/")])
        s = shows["tahtikino-muhos"][0]
        self.assertEqual((s["eventId"], s["provider"], s["venue"], s["theatre"]),
                         ("7", "tahtikino", "tahtikino-muhos", "Tähti Kino"))
        self.assertEqual((s["url"], s["price"], s["img"]),
                         ("https://muhos.fi/tapahtuma/hetki/", "13 €", ""))
        self.assertEqual((s["len"], s["rating"], s["genres"], s["aud"], s["soldOut"]),
                         ("", "", "", "", False))


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._fetch, self._sleep = T.fetch, T.time.sleep
        self.addCleanup(lambda: setattr(T, "fetch", self._fetch))
        self.addCleanup(lambda: setattr(T.time, "sleep", self._sleep))
        T.time.sleep = lambda s: None
        self.calls = []

    def serve(self, routes):
        def fetch(url, **kw):
            self.calls.append(url)
            for key, body in routes.items():
                if key in url:
                    if isinstance(body, Exception):
                        raise body
                    return json.dumps(body).encode("utf-8")
            raise RuntimeError(f"unexpected fetch {url}")
        T.fetch = fetch

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["tribe"])
        return code, out.getvalue() + err.getvalue()

    def both(self, **over):
        routes = {
            "ritz.fi/?rest_route=/tribe/events/v1/events&per_page=50&page=1":
                page(TWO, total=2),
            "muhos.fi/?rest_route=/tribe/events/v1/events&per_page=50&page=1":
                page([event(7, "Hetki ennen valoa", "2026-09-19 17:00:00",
                            "2026-09-19 14:00:00", cost="13 €", values=("13",), cat=106,
                            image=CALENDAR_IMG,
                            url="https://muhos.fi/tapahtuma/hetki/"),
                      event(8, "Ryhmä Hau", "2026-09-19 13:00:00", "2026-09-19 10:00:00",
                            cost="11 €", values=("11",), cat=106,
                            url="https://muhos.fi/tapahtuma/hau/")], total=2),
        }
        routes.update(over)
        return routes

    def test_both_sites_publish(self):
        self.serve(self.both())
        code, log = self.main()
        self.assertEqual(code, 0, log)
        ritz = json.loads((run.OUT / "area-ritz-vaasa.json").read_text())["shows"]
        muhos = json.loads((run.OUT / "area-tahtikino-muhos.json").read_text())["shows"]
        self.assertEqual(len(ritz), 2)
        self.assertEqual([s["title"] for s in muhos], ["Ryhmä Hau", "Hetki ennen valoa"])
        self.assertEqual({s["img"] for s in muhos}, {""})
        self.assertIn("0 failures", log)

    def test_every_page_is_read(self):
        self.serve(self.both(**{
            "ritz.fi/?rest_route=/tribe/events/v1/events&per_page=50&page=1":
                page(TWO, total=4, pages=2),
            "ritz.fi/?rest_route=/tribe/events/v1/events&per_page=50&page=2":
                page([event(5, "Late show", "2026-10-07 18:15:00", "2026-10-07 15:15:00"),
                      event(6, "Matinee", "2026-10-08 12:00:00", "2026-10-08 09:00:00")],
                     total=4, pages=2)}))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        shows = json.loads((run.OUT / "area-ritz-vaasa.json").read_text())["shows"]
        self.assertEqual(len(shows), 4)
        self.assertIn("2 page(s) read", log)
        self.assertEqual(len([c for c in self.calls if "ritz.fi" in c and "page=" in c]), 2)

    def test_an_empty_category_that_still_exists_is_an_empty_programme(self):
        prev = {"generated": "2026-09-01T00:00:00+00:00", "dates": ["2026-09-01"],
                "horizon": "2026-09-01",
                "shows": [{"title": "Old", "start": "2026-09-01T12:00:00+03:00"}]}
        (run.OUT / "area-ritz-vaasa.json").write_text(json.dumps(prev))
        self.serve(self.both(**{
            "ritz.fi/?rest_route=/tribe/events/v1/events&per_page=50&page=1":
                page([], total=0),
            "ritz.fi/?rest_route=/tribe/events/v1/categories/19":
                {"id": 19, "slug": "kino", "name": "Kino"}}))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertIn("no programme published", log)
        self.assertEqual(json.loads((run.OUT / "area-ritz-vaasa.json").read_text()), prev)

    def test_an_empty_answer_from_a_renamed_category_fails_the_site(self):
        """Zero rows and a category that no longer answers is a configuration change."""
        self.serve(self.both(**{
            "ritz.fi/?rest_route=/tribe/events/v1/events&per_page=50&page=1":
                page([], total=0),
            "ritz.fi/?rest_route=/tribe/events/v1/categories/19":
                {"id": 19, "slug": "elokuvat"}}))
        code, log = self.main()
        self.assertEqual(code, 1, log)
        self.assertIn("renamed or deleted category", log)
        self.assertFalse((run.OUT / "area-ritz-vaasa.json").exists())
        self.assertTrue((run.OUT / "area-tahtikino-muhos.json").exists())

    def test_a_route_that_answers_html_fails_that_site_only(self):
        self.serve(self.both(**{
            "ritz.fi/?rest_route=/tribe/events/v1/events&per_page=50&page=1":
                RuntimeError("HTTP Error 503")}))
        code, log = self.main()
        self.assertEqual(code, 1, log)
        self.assertFalse((run.OUT / "area-ritz-vaasa.json").exists())
        self.assertTrue((run.OUT / "area-tahtikino-muhos.json").exists())


class RegistryTest(unittest.TestCase):
    def test_the_two_registry_entries(self):
        for pid, label, host, city in (("ritzvaasa", "Ritz Vaasa", "ritz.fi", "Vaasa"),
                                       ("tahtikino", "Tähti Kino", "muhos.fi", "Muhos")):
            with self.subTest(provider=pid):
                p = registry.by_id(pid)
                self.assertEqual((p["label"], p["host"], p["book"], p["module"],
                                  p["where"]), (label, host, "buy", "tribe", "cloud"))
                self.assertEqual(sum(1 for q in registry.PROVIDERS
                                     if q["accent"] == p["accent"]), 1)
                site = next(s for s in T.SITES if s["provider"] == pid)
                self.assertEqual(site["venues"][0]["city"], city)
                self.assertEqual(site["venues"][0]["name"], label)

    def test_each_site_declares_its_category_by_id_and_slug(self):
        """The name is display text and moves with the site's language; the id does not."""
        for site in T.SITES:
            with self.subTest(provider=site["provider"]):
                self.assertIsInstance(site["category"]["id"], int)
                self.assertRegex(site["category"]["slug"], r"^[a-z0-9-]+$")

    def test_the_mikkeli_kino_ritz_is_a_different_cinema(self):
        self.assertEqual(registry.by_id("ritzvaasa")["host"], "ritz.fi")
        self.assertEqual(registry.by_id("leffabuumi")["host"], "leffabuumi.fi")

    def test_each_site_names_the_host_it_reads_and_they_are_paced_apart(self):
        self.assertEqual([s["base"] for s in T.SITES],
                         ["https://ritz.fi", "https://muhos.fi"])
        self.assertEqual(len(run.host_groups(T.SITES)), 2)


if __name__ == "__main__":
    unittest.main()
