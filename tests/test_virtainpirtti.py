"""The Virtain Pirtti reader: one Weebly paragraph per film.

The fixtures are the page's shapes read on 2026-10-24 (issue #15), cut to what each rule
needs, with two films and two rows wherever there is a loop.

What they exist to prove:

- **A footnote applies only to the dates it names**: the 28.10. footnote sets a price and
  Finnish subtitles on that screening and on no other, and a note naming no date sets
  nothing.
- **Every heading shape seen is read**: "K-16", "-S-" and "K-7 dub.".
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import registry
import run
import virtainpirtti as V

SITE = V.SITES[0]
VENUE = SITE["venues"][0]["id"]
LISTING = SITE["base"] + SITE["listing"]
TODAY = datetime.date(2026, 10, 24)


def film(head, *lines):
    title, _, rating = head.partition("|")
    body = "<br />".join(f'<font size="5">{x}</font>' for x in lines)
    return (f'<div class="paragraph" style="display:block;"><strong><font size="5">{title}'
            f'</font></strong><font size="5"> {rating}</font><br />{body}</div>')


def page(*films):
    # A paragraph above the content area, as Weebly's header can hold, is not the programme.
    return ('<html><body><div class="paragraph"><strong>Lapin sota</strong> K-16<br />'
            'pe 23.10. klo 18.00</div><div id="wsite-content" class="wsite-elements">'
            + "".join(films)
            + '<div class="paragraph">Site powered by Weebly.</div></div></body></html>')


LIVE = page(
    film("Kerro kaikille|K-12", "la 24.10. klo 18.00", "ke 28.10. klo 15.45*",
         "*28.10. on 9€ päivänäytös ja tekstitys suomeksi", "Kesto 1 h 52 min"),
    film("Pikkuli ja Tähtipeura|-S-", "Ensi-ilta", "pe 23.10. klo 16.15",
         "ti 27.10. klo 15.45", "(27.10. on 9 € päivänäytös)", "Kesto 1 h 20 min"),
    film("Unohdettu saari|K-7 dub.", "pe 23.10. klo 14.00", "9 € päivänäytös",
         "Kesto 1 h 49 min"),
)


class PageTest(unittest.TestCase):

    def rows(self, body):
        return V.rows(SITE, body, TODAY)

    def test_every_screening_line_is_a_row(self):
        shows, report = self.rows(LIVE)
        self.assertEqual([(s["start"], s["title"]) for s in shows],
                         [("2026-10-23T14:00:00+03:00", "Unohdettu saari"),
                          ("2026-10-23T16:15:00+03:00", "Pikkuli ja Tähtipeura"),
                          ("2026-10-24T18:00:00+03:00", "Kerro kaikille"),
                          ("2026-10-27T15:45:00+02:00", "Pikkuli ja Tähtipeura"),
                          ("2026-10-28T15:45:00+02:00", "Kerro kaikille")])
        self.assertEqual(report["films"], 3)

    def test_a_footnote_applies_only_to_its_dates(self):
        shows, report = self.rows(LIVE)
        by = {(s["title"], s["start"][:10]): s for s in shows}
        self.assertEqual((by[("Kerro kaikille", "2026-10-28")]["price"],
                          by[("Kerro kaikille", "2026-10-28")]["lang"]), ("9€", "FI-S"))
        self.assertEqual((by[("Kerro kaikille", "2026-10-24")]["price"],
                          by[("Kerro kaikille", "2026-10-24")]["lang"]), ("", ""))
        self.assertEqual(by[("Pikkuli ja Tähtipeura", "2026-10-27")]["price"], "9€")
        self.assertEqual(by[("Pikkuli ja Tähtipeura", "2026-10-23")]["price"], "")

    def test_a_note_naming_no_date_sets_nothing(self):
        shows, report = self.rows(LIVE)
        saari = [s for s in shows if s["title"] == "Unohdettu saari"][0]
        self.assertEqual(saari["price"], "")
        self.assertEqual(report["undated_note"], 1)

    def test_the_heading_shapes(self):
        shows, _ = self.rows(LIVE)
        by = {s["title"]: s for s in shows}
        self.assertEqual((by["Kerro kaikille"]["rating"], by["Kerro kaikille"]["len"]), ("K-12", "112"))
        self.assertEqual(by["Pikkuli ja Tähtipeura"]["rating"], "S")
        self.assertEqual((by["Unohdettu saari"]["rating"], by["Unohdettu saari"]["lang"]), ("K-7", "FI-A"))
        self.assertEqual((by["Unohdettu saari"]["url"], by["Unohdettu saari"]["img"],
                          by["Unohdettu saari"]["eventId"]), (LISTING, "", "unohdettu-saari"))

    def test_the_premiere_is_the_first_screening_only(self):
        shows, _ = self.rows(LIVE)
        pikkuli = [s for s in shows if s["title"] == "Pikkuli ja Tähtipeura"]
        self.assertEqual([s["method"] for s in pikkuli], ["Ensi-ilta", ""])

    def test_a_paragraph_above_the_content_is_not_a_film(self):
        shows, _ = self.rows(LIVE)
        self.assertNotIn("2026-10-23T18:00:00+03:00", [s["start"] for s in shows])


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get = V.get_text
        self.addCleanup(lambda: setattr(V, "get_text", self._get))
        self.calls = []

    def serve(self, body):
        def get_text(url, **kw):
            self.calls.append(url)
            return body
        V.get_text = get_text

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["virtainpirtti", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def row(self, days, clock):
        """run.main reads the real clock, so a fixture dated in October would go stale."""
        d = datetime.datetime.now(V.FI).date() + datetime.timedelta(days=days)
        wd = ("ma", "ti", "ke", "to", "pe", "la", "su")[d.weekday()]
        return f"{wd} {d.day}.{d.month}. klo {clock}"

    def kept(self):
        doc = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
               "horizon": "2026-10-20",
               "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(doc), encoding="utf-8")

    def after(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))

    def test_the_site_publishes_from_one_request(self):
        self.serve(page(film("Lapin sota|K-16", self.row(1, "18.00"), self.row(2, "18.00")),
                        film("Pirjo i Sverige|-S-", self.row(2, "13.00"))))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls, [LISTING])
        self.assertEqual(sorted({s["title"] for s in self.after()["shows"]}),
                         ["Lapin sota", "Pirjo i Sverige"])

    def test_a_page_with_no_screening_line_fails_and_keeps_the_previous_file(self):
        self.kept()
        self.serve(page(film("Tulossa|K-12", "Kesto 1 h 52 min")))
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no film with a screening line", log)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        r = registry.by_id("virtainpirtti")
        self.assertEqual((r["label"], r["host"], r["book"], r["module"], r["where"]),
                         ("Virtain Pirtti", "virtainpirtti.fi", "door", "virtainpirtti", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS if q["accent"] == r["accent"]), 1)


if __name__ == "__main__":
    unittest.main()
