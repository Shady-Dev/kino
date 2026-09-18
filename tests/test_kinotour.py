"""Kinotour: one table, one row per screening, and a venue set that moves.

The fixtures are the markup as read on 2026-09-18. What they exist to prove:

- **An undeclared town is ordinary, not a failure.** Every fixture that touches the town
  rule carries at least two towns, one this repo lists and one it does not, so the loop is
  exercised rather than the body alone. The count reaches the run log and the declared
  town still publishes.
- **Only a rating-shaped tail comes off the title.** "Ryhmä Hau, Dinoelokuva, K7" is a
  title with a comma in it.
- **The time is the one with a colon.** The cell flattens to "su 27.09.2026 14:00", and a
  dot-tolerant pattern read the 27.09 of the date as 27:09 and raised on the hour.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import kinotour as K
import registry
import run


SITE = K.SITES[0]
LISTING = "https://www.kinotour.fi/varaa-liput-elokuvatapahtumiin/"


def row(date, time, title, place, slug="hetki-ennen-valoa-k7-6"):
    return (f"<tr><td> {date}<br />{time} </td>"
            f'<td><a href="https://www.kinotour.fi/events/{slug}/">{title}</a><br />'
            f"<i>{place} </i></td></tr>")


def table(*rows_):
    return ('<html><body><div class="em em-view-container"><table class="events-table">'
            "<thead><tr><th>Esityspäivä</th><th>Elokuvat ja lippuvaraukset</th></tr>"
            "</thead><tbody>" + "".join(rows_) + "</tbody></table></div></body></html>")


DECLARED = row("la 19.09.2026", "14:00", "Hetki ennen valoa, K7", "Kyrö kurkisali, Kyrö")
UNDECLARED = row("la 19.09.2026", "16:00", "Presidentin kyyditys, K12",
                 "Karkkilasali, Karkkila", slug="presidentin-kyyditys-k12-6")


class RowsTest(unittest.TestCase):
    def test_a_declared_town_publishes_and_an_undeclared_one_is_counted(self):
        per_venue, report = K.rows(SITE, table(DECLARED, UNDECLARED))
        self.assertEqual([s["title"] for s in per_venue["kinotour-kyro"]],
                         ["Hetki ennen valoa"])
        self.assertEqual(report["undeclared"], {"Karkkila": 1})
        self.assertEqual(sum(len(v) for v in per_venue.values()), 1)

    def test_several_screenings_in_one_undeclared_town_are_counted_together(self):
        per_venue, report = K.rows(SITE, table(
            DECLARED, UNDECLARED,
            row("su 20.09.2026", "15:00", "Hetki ennen valoa, K7",
                "Karkkilasali, Karkkila"),
            row("su 20.09.2026", "17:00", "Pirjo, K12", "Ikaalisten tori, Ikaalinen")))
        self.assertEqual(report["undeclared"], {"Karkkila": 2, "Ikaalinen": 1})
        self.assertEqual(len(per_venue["kinotour-kyro"]), 1)

    def test_each_declared_town_files_under_its_own_venue(self):
        per_venue, _ = K.rows(SITE, table(
            DECLARED,
            row("su 20.09.2026", "13:00", "Ryhmä Hau: Dinoelokuva, K7",
                "Lieto valtuustosali, Lieto"),
            row("su 20.09.2026", "15:00", "Hetki ennen valoa, K7",
                "Naantali Kristoffersali, Naantali")))
        self.assertEqual({k: len(v) for k, v in per_venue.items()},
                         {"kinotour-kyro": 1, "kinotour-lieto": 1, "kinotour-naantali": 1})

    def test_a_title_keeps_its_own_comma(self):
        per_venue, _ = K.rows(SITE, table(
            row("la 19.09.2026", "14:00", "Ryhmä Hau, Dinoelokuva, K7",
                "Kyrö kurkisali, Kyrö"),
            row("la 19.09.2026", "16:00", "Sarjis, S", "Kyrö kurkisali, Kyrö")))
        shows = per_venue["kinotour-kyro"]
        self.assertEqual([(s["title"], s["rating"]) for s in shows],
                         [("Ryhmä Hau, Dinoelokuva", "K-7"), ("Sarjis", "S")])

    def test_a_title_with_no_rating_tail_keeps_all_of_itself(self):
        """Including one whose own comma would be read as the tail."""
        per_venue, _ = K.rows(SITE, table(
            row("la 19.09.2026", "14:00", "Elokuva ilman ikärajaa", "Kyrö kurkisali, Kyrö"),
            row("la 19.09.2026", "16:00", "Ryhmä Hau, Dinoelokuva", "Kyrö kurkisali, Kyrö")))
        shows = per_venue["kinotour-kyro"]
        self.assertEqual([(s["title"], s["rating"]) for s in shows],
                         [("Elokuva ilman ikärajaa", ""), ("Ryhmä Hau, Dinoelokuva", "")])

    def test_the_time_is_the_colon_one_and_not_the_date(self):
        """The cell flattens to one line, so the date's dots are in the same string."""
        per_venue, _ = K.rows(SITE, table(
            row("su 27.09.2026", "14:00", "Hetki ennen valoa, K7", "Kyrö kurkisali, Kyrö"),
            row("su 27.09.2026", "16:30", "Pirjo, K12", "Kyrö kurkisali, Kyrö")))
        self.assertEqual([s["start"] for s in per_venue["kinotour-kyro"]],
                         ["2026-09-27T14:00:00+03:00", "2026-09-27T16:30:00+03:00"])

    def test_a_weekday_that_contradicts_the_date_is_counted_and_the_date_wins(self):
        per_venue, report = K.rows(SITE, table(
            row("ma 19.09.2026", "14:00", "Hetki ennen valoa, K7", "Kyrö kurkisali, Kyrö"),
            row("la 19.09.2026", "16:00", "Pirjo, K12", "Kyrö kurkisali, Kyrö")))
        self.assertEqual(report["weekday"], 1)
        self.assertEqual([s["start"][:10] for s in per_venue["kinotour-kyro"]],
                         ["2026-09-19", "2026-09-19"])

    def test_a_row_with_no_readable_date_fails_the_site(self):
        with self.assertRaises(K.RowError):
            K.rows(SITE, table(DECLARED,
                               row("pian", "", "Pirjo, K12", "Kyrö kurkisali, Kyrö")))

    def test_a_row_that_names_no_place_fails_the_site(self):
        bad = ('<tr><td> la 19.09.2026<br />14:00 </td>'
               '<td><a href="https://www.kinotour.fi/events/x/">Pirjo, K12</a></td></tr>')
        with self.assertRaises(K.RowError):
            K.rows(SITE, table(DECLARED, bad))

    def test_an_impossible_date_fails_the_site(self):
        with self.assertRaises(K.RowError):
            K.rows(SITE, table(DECLARED,
                               row("ti 31.02.2026", "14:00", "Pirjo, K12",
                                   "Kyrö kurkisali, Kyrö")))

    def test_the_show_shape(self):
        per_venue, _ = K.rows(SITE, table(DECLARED))
        s = per_venue["kinotour-kyro"][0]
        self.assertEqual((s["price"], s["img"], s["len"], s["lang"], s["genres"]),
                         ("", "", "", "", ""))
        self.assertEqual((s["provider"], s["venue"], s["theatre"]),
                         ("kinotour", "kinotour-kyro", "Kurkisali"))
        self.assertEqual(s["url"],
                         "https://www.kinotour.fi/events/hetki-ennen-valoa-k7-6/")
        self.assertEqual(s["eventId"], "hetki ennen valoa")


class RunnerTest(unittest.TestCase):
    PREV = {"generated": "2026-09-01T00:00:00+00:00", "dates": ["2026-09-01"],
            "horizon": "2026-09-01",
            "shows": [{"title": "Old", "start": "2026-09-01T12:00:00+03:00"}]}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._fetch = K.fetch
        self.addCleanup(lambda: setattr(K, "fetch", self._fetch))

    def serve(self, body):
        def fetch(url, **kw):
            if isinstance(body, Exception):
                raise body
            return body.encode("utf-8")
        K.fetch = fetch

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["kinotour"])
        return code, out.getvalue() + err.getvalue()

    def test_the_run_publishes_and_names_the_undeclared_town(self):
        self.serve(table(DECLARED, UNDECLARED))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        shows = json.loads((run.OUT / "area-kinotour-kyro.json").read_text())["shows"]
        self.assertEqual(len(shows), 1)
        self.assertIn("Karkkila (1)", log)
        self.assertIn("does not list", log)
        self.assertIn("0 failures", log)

    def test_a_table_of_nothing_but_undeclared_towns_empties_the_declared_ones(self):
        """The table is the whole programme, so a town it does not mention has nothing on.
        `EMPTY_VENUES_CONFIRMED` is what turns that into a fresh empty file rather than a
        last visit ageing for weeks."""
        (run.OUT / "area-kinotour-kyro.json").write_text(json.dumps(self.PREV))
        self.serve(table(UNDECLARED))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertIn("Karkkila (1)", log)
        self.assertIn("no programme at the moment", log)
        body = json.loads((run.OUT / "area-kinotour-kyro.json").read_text())
        self.assertEqual(body["shows"], [])
        self.assertNotEqual(body["generated"], self.PREV["generated"])

    def test_an_empty_table_fails_and_keeps_the_previous_file(self):
        (run.OUT / "area-kinotour-kyro.json").write_text(json.dumps(self.PREV))
        self.serve(table())
        code, log = self.main()
        self.assertEqual(code, 1, log)
        self.assertIn("no evidence of one", log)
        self.assertEqual(json.loads(
            (run.OUT / "area-kinotour-kyro.json").read_text()), self.PREV)

    def test_a_refused_page_keeps_the_previous_file(self):
        (run.OUT / "area-kinotour-kyro.json").write_text(json.dumps(self.PREV))
        self.serve(RuntimeError("HTTP Error 503"))
        code, log = self.main()
        self.assertEqual(code, 1, log)
        self.assertEqual(json.loads(
            (run.OUT / "area-kinotour-kyro.json").read_text()), self.PREV)


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("kinotour")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Kinotour", "kinotour.fi", "buy", "kinotour", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == p["accent"]), 1)

    def test_every_venue_declares_the_town_it_is_matched_on(self):
        """The town is the key, because the hall changes while the tour returns."""
        for v in SITE["venues"]:
            with self.subTest(venue=v["id"]):
                self.assertTrue(v["town"])
                self.assertEqual(v["city"], v["town"])
                self.assertNotIn(v["town"], v["name"])

    def test_the_site_names_the_host_it_reads(self):
        self.assertEqual([s["base"] for s in K.SITES], ["https://www.kinotour.fi"])
        self.assertEqual(len(run.host_groups(K.SITES)), 1)


if __name__ == "__main__":
    unittest.main()
