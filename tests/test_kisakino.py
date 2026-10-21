"""The KisaKino reader: the front page's film links, then each film page's sidebar.

The fixtures are the markup read on 2026-10-21 (issue #9), two films and two screening
lines each, so the loop over films and the loop over lines both run.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import kisakino as K
import registry
import run

SITE = K.SITES[0]
BASE = SITE["base"]
VENUE = SITE["venues"][0]["id"]
WD = ("Ma", "Ti", "Ke", "To", "Pe", "La", "Su")


def front(*films):
    return ("<html><body>" + "".join(
        f'<div class="col span_4_of_12 movie-box"> <h2 class="etusivu-otsikko"><a '
        f'href="{BASE}/elokuvat/{slug}/" rel="bookmark">{title}</a> </h2></div>'
        for slug, title in films) + "</body></html>")


def line(d, clock, wd=None):
    return f"<strong>{wd or WD[d.weekday()]}</strong> {d:%d.%m.%Y} {clock}<br />"


def film(*lines, length="02 h 38 min", price="12€", age="k16"):
    return (f'<div id="sidebar"><p> <img class="attachment-elokuva-juliste" '
            f'src="{BASE}/wp-content/uploads/x-278x397.jpg" /><hr /> <p><strong>Kesto</strong> '
            f'{length}<br /> <strong>Lipun hinta:</strong> {price}<br /></p> <p><strong>'
            f'Elokuvan näytökset</strong><br />{"".join(lines)} <p><strong>Ikäraja</strong>'
            f'<br /> <img src="{BASE}/wp-content/themes/kisakino/images/{age}.png"><br /></p>'
            f'</div><div id="footer-container"></div>')


D24, D25 = datetime.date(2026, 10, 24), datetime.date(2026, 10, 25)


class Stubbed(unittest.TestCase):
    def serve(self, pages):
        self.calls = []

        def get_text(url, **kw):
            self.calls.append(url)
            body = pages.get(url)
            if isinstance(body, Exception):
                raise body
            if body is None:
                raise RuntimeError(f"unexpected fetch {url}")
            return body
        saved = K.get_text
        K.get_text = get_text
        self.addCleanup(lambda: setattr(K, "get_text", saved))


class SiteTest(Stubbed):

    def fetch(self, lapin, hepo):
        self.serve({BASE + "/": front(("lapin-sota", "Lapin sota"),
                                      ("rakkautta", "Rakkautta ja virtahepoja"),
                                      ("lapin-sota", "Lapin sota")),
                    f"{BASE}/elokuvat/lapin-sota/": lapin,
                    f"{BASE}/elokuvat/rakkautta/": hepo})
        with contextlib.redirect_stdout(io.StringIO()):
            return K.fetch_site(SITE, sleep=0)[VENUE]

    def test_each_film_page_is_read_once_and_every_line_is_a_row(self):
        shows = self.fetch(film(line(D24, "16:00"), line(D25, "16:00")),
                           film(line(D24, "18:00"), line(D25, "18:00"), length="01 h 41 min",
                                price="10€", age="k12"))
        self.assertEqual(len(self.calls), 3)
        self.assertEqual([(s["start"], s["title"]) for s in shows],
                         [("2026-10-24T16:00:00+03:00", "Lapin sota"),
                          ("2026-10-24T18:00:00+03:00", "Rakkautta ja virtahepoja"),
                          # Summer time ends in Finland on 25.10.
                          ("2026-10-25T16:00:00+02:00", "Lapin sota"),
                          ("2026-10-25T18:00:00+02:00", "Rakkautta ja virtahepoja")])
        lapin = shows[0]
        self.assertEqual((lapin["len"], lapin["price"], lapin["rating"], lapin["url"],
                          lapin["eventId"], lapin["img"]),
                         ("158", "12€", "K-16", f"{BASE}/elokuvat/lapin-sota/", "lapin-sota", ""))
        self.assertEqual((shows[1]["len"], shows[1]["price"], shows[1]["rating"]),
                         ("101", "10€", "K-12"))

    def test_a_line_whose_weekday_is_not_its_dates_is_left_out(self):
        shows = self.fetch(film(line(D24, "16:00"), line(D25, "16:00", wd="La")),
                           film(line(D24, "18:00"), price="10 € / 8 € lapset", age="s"))
        self.assertEqual([s["start"][:16] for s in shows],
                         ["2026-10-24T16:00", "2026-10-24T18:00"])
        self.assertEqual((shows[1]["price"], shows[1]["rating"]), ("", "S"))

    def test_a_film_page_that_cannot_be_read_fails_the_site(self):
        with self.assertRaises(RuntimeError):
            self.fetch(film(line(D24, "16:00")), RuntimeError("503"))


class RunnerTest(Stubbed):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["kisakino", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def soon(self, days):
        """run.main reads the real clock, so a fixture dated in October would go stale."""
        return datetime.datetime.now(K.FI).date() + datetime.timedelta(days=days)

    def kept(self):
        doc = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
               "horizon": "2026-10-20",
               "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(doc), encoding="utf-8")

    def after(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))

    def test_the_site_publishes(self):
        self.serve({BASE + "/": front(("a", "Lapin sota"), ("b", "Pikkuli")),
                    f"{BASE}/elokuvat/a/": film(line(self.soon(1), "18:00"),
                                                line(self.soon(2), "18:00")),
                    f"{BASE}/elokuvat/b/": film(line(self.soon(2), "13:00"), age="s")})
        K_sleep = K.time.sleep
        K.time.sleep = lambda s: None
        self.addCleanup(lambda: setattr(K.time, "sleep", K_sleep))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(sorted({s["title"] for s in self.after()["shows"]}),
                         ["Lapin sota", "Pikkuli"])

    def test_a_front_page_with_no_film_fails_and_keeps_the_previous_file(self):
        self.kept()
        self.serve({BASE + "/": "<html><body><p>Kesätauko</p></body></html>"})
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no film link", log)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("kisakino")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("KisaKino", "kisakino.fi", "door", "kisakino", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == p["accent"]), 1)


if __name__ == "__main__":
    unittest.main()
