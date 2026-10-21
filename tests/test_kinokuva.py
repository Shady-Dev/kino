"""The Kino-Kuva reader: one ISO-8859-1 front page, one nested table per film.

The fixtures are the markup read on 2026-10-21 (issue #12), as bytes in the site's own
encoding, with two films and two rows wherever there is a loop.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import kinokuva as K
import registry
import run

SITE = K.SITES[0]
VENUE = SITE["venues"][0]["id"]
FRONT = SITE["base"] + SITE["listing"]
TODAY = datetime.date(2026, 10, 21)


def film(title, lines, length="2 h 38 min", rating="-K16-"):
    pre = "<br/>".join(lines)
    return (f'<tr class="doListRowOdd"><td><table style="width: 100%"><tr><td colspan="2" '
            f'class="elokuva"><h1>{title}</h1>\r\n\t\t\tKesto: {length} {rating} </td></tr>'
            f'<tr><td class="elokuva_kuva"><img src="images/movies/x.jpg"/></td>'
            f'<td class="elokuva_tiedot"> <pre>{pre}</pre> <p>Synopsis.</p></td></tr>'
            f'</table></td></tr>')


RULE = "-" * 35


def page(*films, encoding="iso-8859-1"):
    # A film-shaped block above the programme table is not the programme.
    above = ('<table class="esittely">' + film("ESITTELY", ["LA 24.10. KLO 12.00"]) + "</table>")
    html = ("<html><body>" + above + '<h3>Ohjelmistossa</h3><p><table class="naytokset">'
            + "".join(films) + "</table></body></html>")
    return html.encode(encoding)


LIVE = page(
    film("PIKKULI JA TÄHTIPEURA", ["ENSI-ILTA PE 23.10. KLO 17.30", "SU 25.10. KLO 16.00", RULE,
                                    "Liput  12,-", RULE, "Puhumme suomea!"],
         length="1 h 20 min", rating="-S-"),
    film("LAPIN SOTA", ["Puolan elokuvaviikot:", "TO 22.10. KLO 14.00 JA KLO 17.00",
                         "ENSI-ILTA 30.10.", RULE, "Liput  14,-", RULE,
                         "Elokuvassa englanninkielinen teksitys!"]))


class PageTest(unittest.TestCase):

    def rows(self, body):
        return K.rows(SITE, K.decode(body), TODAY)

    def test_every_clock_of_every_film_in_the_table_is_a_row(self):
        shows, report = self.rows(LIVE)
        self.assertEqual([(s["start"], s["title"], s["method"]) for s in shows],
                         [("2026-10-22T14:00:00+03:00", "LAPIN SOTA", "Puolan elokuvaviikot"),
                          ("2026-10-22T17:00:00+03:00", "LAPIN SOTA", "Puolan elokuvaviikot"),
                          ("2026-10-23T17:30:00+03:00", "PIKKULI JA TÄHTIPEURA", "Ensi-ilta"),
                          # Summer time ends in Finland on 25.10.
                          ("2026-10-25T16:00:00+02:00", "PIKKULI JA TÄHTIPEURA", "")])
        self.assertEqual((report["films"], report["untimed"]), (2, 1))

    def test_the_fields_a_row_carries(self):
        shows, _ = self.rows(LIVE)
        lapin, pikkuli = shows[0], shows[2]
        self.assertEqual((lapin["len"], lapin["rating"], lapin["price"], lapin["lang"],
                          lapin["url"], lapin["img"]),
                         ("158", "K-16", "14€", "EN-S", FRONT, ""))
        self.assertEqual((pikkuli["len"], pikkuli["rating"], pikkuli["price"], pikkuli["lang"],
                          pikkuli["eventId"]),
                         ("80", "S", "12€", "FI-A", "pikkuli-ja-tahtipeura"))

    def test_the_page_reads_in_either_encoding(self):
        utf8 = K.decode(page(film("PIKKULI JA TÄHTIPEURA", ["LA 24.10. KLO 16.00"]),
                             encoding="utf-8"))
        latin = K.decode(page(film("PIKKULI JA TÄHTIPEURA", ["LA 24.10. KLO 16.00"])))
        self.assertIn("TÄHTIPEURA", utf8)
        self.assertIn("TÄHTIPEURA", latin)

    def test_free_admission_and_a_preview_heading(self):
        shows, _ = self.rows(page(film("X", ["ENNAKKONÄYTÖKSET!", "LA 24.10. KLO 16.00", RULE,
                                             "Ilmainen sisäänpääsy!"])))
        self.assertEqual((shows[0]["price"], shows[0]["method"]), ("Vapaa pääsy", "Ennakkonäytös"))


class RunnerTest(unittest.TestCase):
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
            return body
        K.fetch = fetch

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["kinokuva", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def row(self, days, clock):
        """run.main reads the real clock, so a fixture dated in October would go stale."""
        d = datetime.datetime.now(K.FI).date() + datetime.timedelta(days=days)
        wd = ("MA", "TI", "KE", "TO", "PE", "LA", "SU")[d.weekday()]
        return f"{wd} {d.day}.{d.month}. KLO {clock}"

    def kept(self):
        doc = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
               "horizon": "2026-10-20",
               "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(doc), encoding="utf-8")

    def after(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))

    def test_the_site_publishes(self):
        self.serve(page(film("LAPIN SOTA", [self.row(1, "19.00"), self.row(2, "19.00")]),
                        film("RESIDENT EVIL", [self.row(2, "21.00")])))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(sorted({s["title"] for s in self.after()["shows"]}),
                         ["LAPIN SOTA", "RESIDENT EVIL"])

    def test_a_page_with_no_timed_row_fails_and_keeps_the_previous_file(self):
        self.kept()
        self.serve(page(film("X", ["ENSI-ILTA 30.10."])))
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no film with a timed screening", log)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("kinokuva")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Kino-Kuva", "kinokuva.fi", "door", "kinokuva", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == p["accent"]), 1)


if __name__ == "__main__":
    unittest.main()
