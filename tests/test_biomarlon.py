"""The Bio Marlon reader: one Elementor front page, one text-editor widget per film.

The fixtures are the widget shapes read on 2026-10-21 (issue #11), two films and two rows
wherever there is a loop.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import biomarlon as B
import registry
import run

SITE = B.SITES[0]
VENUE = SITE["venues"][0]["id"]
FRONT = SITE["base"] + SITE["listing"]
TODAY = datetime.date(2026, 10, 21)


def widget(title, rows, facts="K-16 2 t 35 min 15 €", extra=""):
    h4 = "".join(f'<h4><span style="font-size: x-large;">{r}</span></h4>' for r in rows)
    return (f'<div class="elementor-element elementor-element-x elementor-widget '
            f'elementor-widget-text-editor" data-id="x"> <div class="elementor-widget-container">'
            f' <h1><a href="https://nytleffaan.fi/elokuva/x/">{title}</a></h1>{h4}'
            f'<p>{facts}</p>{extra} </div> </div>')


COMING = ('<div class="elementor-element elementor-widget elementor-widget-text-editor"> '
          '<div class="elementor-widget-container"> <h4><span>Tulossa</span></h4>'
          '<h1><a href="https://nytleffaan.fi/a/">JÄRKI JA TUNTEET</a></h1><h1><a '
          'href="https://nytleffaan.fi/b/">AVENGERS: DOOMSDAY</a></h1> </div> </div>')
ADDRESS = ('<div class="elementor-element elementor-widget elementor-widget-text-editor"> '
           '<div class="elementor-widget-container"> <h1>Topeeka 37</h1><h1>61800 Kauhajoki'
           '</h1> </div> </div>')


def page(*widgets):
    return "<html><body>" + "".join(widgets) + "</body></html>"


LIVE = page(
    widget("LAPIN SOTA", ["Ensi-ilta pe 23.10. 16:00 ja </span><span>19:15",
                          "la 24.10. 14:00 ja 18:30"]),
    widget("PIRJO I SVERIGE", ["to 22.10. 17:15", "(ma 26.10. 13:00 yksityisnäytös)"],
           facts="-S- 1 t 25 min 14 €", extra="<p>Suomea puhutaan!</p>"),
    widget("NÄÄ MAAT, NÄÄ MANNUT &#8211; MEIDÄN KAUHAJOKI", ["ke 21.10. 18:00"], facts="0 €"),
    COMING, ADDRESS)


class PageTest(unittest.TestCase):

    def rows(self, html):
        return B.rows(SITE, html, TODAY)

    def test_every_clock_of_every_film_is_a_row(self):
        shows, report = self.rows(LIVE)
        self.assertEqual([(s["start"][:16], s["title"][:15], s["method"]) for s in shows],
                         [("2026-10-21T18:00", "NÄÄ MAAT, NÄÄ M", ""),
                          ("2026-10-22T17:15", "PIRJO I SVERIGE", ""),
                          ("2026-10-23T16:00", "LAPIN SOTA", "Ensi-ilta"),
                          ("2026-10-23T19:15", "LAPIN SOTA", "Ensi-ilta"),
                          ("2026-10-24T14:00", "LAPIN SOTA", ""),
                          ("2026-10-24T18:30", "LAPIN SOTA", "")])
        self.assertEqual((report["films"], report["coming"], report["private"]), (3, 2, 1))

    def test_the_facts_line(self):
        shows, _ = self.rows(LIVE)
        by = {s["title"][:5]: s for s in shows}
        self.assertEqual((by["LAPIN"]["rating"], by["LAPIN"]["len"], by["LAPIN"]["price"]),
                         ("K-16", "155", "15€"))
        self.assertEqual((by["PIRJO"]["rating"], by["PIRJO"]["len"], by["PIRJO"]["lang"]),
                         ("S", "85", "FI-A"))
        self.assertEqual(by["NÄÄ M"]["price"], "Vapaa pääsy")
        self.assertEqual({s["url"] for s in shows}, {FRONT})
        self.assertEqual({s["img"] for s in shows}, {""})

    def test_a_whole_hour_and_a_flexible_age(self):
        shows, _ = self.rows(page(widget("X", ["la 24.10. 17:00"], facts="K-7/4 1 t 13 €")))
        self.assertEqual((shows[0]["rating"], shows[0]["len"], shows[0]["price"]),
                         ("K-7", "60", "13€"))

    def test_a_premiere_with_no_clock_is_not_a_screening(self):
        shows, report = self.rows(page(widget("X", ["Ensi-ilta pe 23.10.", "la 24.10. 17:00"])))
        self.assertEqual([s["start"][:16] for s in shows], ["2026-10-24T17:00"])
        self.assertEqual(report["untimed"], 1)


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get = B.get_text
        self.addCleanup(lambda: setattr(B, "get_text", self._get))

    def serve(self, body):
        def get_text(url, **kw):
            if isinstance(body, Exception):
                raise body
            return body
        B.get_text = get_text

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["biomarlon", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def row(self, days, clock):
        """run.main reads the real clock, so a fixture dated in October would go stale."""
        d = datetime.datetime.now(B.FI).date() + datetime.timedelta(days=days)
        return f"{('ma', 'ti', 'ke', 'to', 'pe', 'la', 'su')[d.weekday()]} {d.day}.{d.month}. {clock}"

    def kept(self):
        doc = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
               "horizon": "2026-10-20",
               "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(doc), encoding="utf-8")

    def after(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))

    def test_the_site_publishes(self):
        self.serve(page(widget("LAPIN SOTA", [self.row(1, "18:00"), self.row(2, "18:00")]),
                        widget("PIKKU", [self.row(2, "13:00")], facts="-S- 1 t 13 €"), COMING))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(sorted({s["title"] for s in self.after()["shows"]}),
                         ["LAPIN SOTA", "PIKKU"])

    def test_a_page_with_only_coming_films_fails_and_keeps_the_previous_file(self):
        self.kept()
        self.serve(page(COMING, ADDRESS))
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no film with a timed screening", log)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("biomarlon")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Bio Marlon", "biomarlon.fi", "door", "biomarlon", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == p["accent"]), 1)


if __name__ == "__main__":
    unittest.main()
