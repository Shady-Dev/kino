"""The Pajakkakino reader: the WordPress posts, one per film.

The fixtures are the post shapes read on 2026-10-21 (issue #10), cut to what each rule
needs, with two posts and two rows wherever there is a loop.

What they exist to prove:

- **Only a film post is read**: an `ESITYKSET:` list and a runtime before it. The event
  post whose prose holds a burger slot beside a documentary is not.
- **Film and non-film stay apart inside a post**: a row whose note is a reading circle is
  left out and the row saying the film starts is kept.
- **Every row shape seen is read**: no second dot, clocks on the next line, two clocks on
  one line. A struck-through row, a row with no clock yet and a date outside the window
  are left out and counted.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import pajakka as P
import registry
import run

SITE = P.SITES[0]
VENUE = SITE["venues"][0]["id"]
LISTING = SITE["base"] + SITE["listing"]
TODAY = datetime.date(2026, 10, 21)


def post(pid, slug, title, rows, facts="Draama, sota, kotimainen <strong>I </strong>2h 35min "
         "<strong>I</strong> 23.10.2026 <strong>I</strong> AUDIO suomi", age="16"):
    img = (f'<img src="https://www.pajakkakino.fi/wp-content/uploads/ikaraja_{age}.png">'
           if age else "")
    body = (f'<div class="elementor"><p><span style="color: #000000;">{facts}</span></p><hr />'
            f'{img}<h2 class="elementor-heading-title"><b>ESITYKSET:</b> </h2>'
            f'<div class="elementor-widget-container">{rows}</div></div>')
    return {"id": pid, "link": f"https://www.pajakkakino.fi/{slug}/",
            "title": {"rendered": title}, "content": {"rendered": body}}


LAPIN = post(13923, "lapin-sota", "R&Ouml;MPP&Auml;VIIKOT: LAPIN SOTA",
             "<p><strong>LA 24.10. KLO 15:00</strong></p><p><strong>SU 25.10 KLO 17:00</strong>"
             "</p><p><strong>TI 27.10.</strong></p><p><strong>KLO 14:00 &amp; 18:00</strong></p>"
             "<p><strong>SU 1.11 KLO ? ilmoitetaan my&ouml;hemmin</strong></p>")
VIRTAHEPO = post(13786, "rakkautta", "RÖMPPÄVIIKOT: RAKKAUTTA JA VIRTAHEPOJA",
                 "<p><strong>MA 26.10. KLO 16:30</strong> alkaen lukupiiri, tervetuloa!</p>"
                 "<p><strong>MA 26.10. KLO 18:00</strong> elokuva alkaa</p>",
                 facts="Draama, kotimainen <strong>I</strong> 1h 41min <strong>I</strong> "
                       "AUDIO englanti <strong>TEKSTIT</strong> suomi", age="12")
STRUCK = post(13803, "unohdettu-saari", "UNOHDETTU SAARI",
              "<p><del><strong>PE 23.10. KLO 15:30</strong></del> PERUTTU!</p>"
              "<p><strong>LA 24.10. KLO 15:30</strong></p><p>VIIMEINEN NÄYTÖS</p>"
              "<p><strong>KE 20.9. KLO 18:00</strong></p>", age="s")
EVENT = {"id": 14000, "link": "https://www.pajakkakino.fi/tekemattomien/",
         "title": {"rendered": "RÖMPPÄVIIKOT: TEKEMÄTTÖMIEN LASTEN MAA"},
         "content": {"rendered": "<h3><strong>Perjantai 23.10.2026</strong></h3><h3><strong>"
                                 "Klo 15:30 – 17:30 Cafe Torilla burgerit.</strong></h3><h3>"
                                 "<strong>Klo 18:00 Tekemättömien lasten maa</strong></h3>"}}


class PostTest(unittest.TestCase):

    def rows(self, *posts):
        return P.rows(SITE, list(posts), TODAY)

    def test_every_row_shape_is_read(self):
        shows, report = self.rows(LAPIN)
        self.assertEqual([s["start"] for s in shows],
                         ["2026-10-24T15:00:00+03:00", "2026-10-25T17:00:00+02:00",
                          "2026-10-27T14:00:00+02:00", "2026-10-27T18:00:00+02:00"])
        self.assertEqual(report["untimed"], 1)

    def test_the_fields_a_row_carries(self):
        shows, _ = self.rows(LAPIN, VIRTAHEPO)
        lapin = shows[0]
        self.assertEqual((lapin["title"], lapin["len"], lapin["rating"], lapin["lang"],
                          lapin["genres"], lapin["url"], lapin["eventId"], lapin["img"]),
                         ("RÖMPPÄVIIKOT: LAPIN SOTA", "155", "K-16", "FI-A",
                          "Draama, Sota, Kotimainen", "https://www.pajakkakino.fi/lapin-sota/",
                          "lapin-sota", ""))
        hepo = [s for s in shows if s["eventId"] == "rakkautta"][0]
        self.assertEqual((hepo["lang"], hepo["rating"]), ("EN-A, FI-S", "K-12"))

    def test_a_row_whose_note_is_not_the_film_is_left_out(self):
        shows, report = self.rows(VIRTAHEPO)
        self.assertEqual([s["start"][:16] for s in shows], ["2026-10-26T18:00"])
        self.assertEqual(report["noted"], 1)

    def test_struck_stale_and_note_lines_are_not_screenings(self):
        shows, report = self.rows(STRUCK)
        self.assertEqual([s["start"][:16] for s in shows], ["2026-10-24T15:30"])
        self.assertEqual((report["cancelled"], report["undated"]), (1, 1))
        self.assertEqual(shows[0]["rating"], "S")

    def test_a_post_with_no_list_is_not_a_film(self):
        shows, report = self.rows(EVENT, LAPIN)
        self.assertEqual({s["eventId"] for s in shows}, {"lapin-sota"})
        self.assertEqual((report["films"], report["not_film"]), (1, 1))

    def test_a_list_with_no_runtime_before_it_is_not_a_film(self):
        """A concert or a talk can carry an ESITYKSET list too; a film post states a runtime."""
        gig = post(3, "konsertti", "KONSERTTI", "<p>LA 24.10. KLO 19:00</p>",
                   facts="Konsertti <strong>I</strong> liput ovelta", age="")
        shows, report = self.rows(gig, LAPIN)
        self.assertEqual({s["eventId"] for s in shows}, {"lapin-sota"})
        self.assertEqual(report["not_film"], 1)

    def test_the_rating_sentence_stands_in_for_a_missing_image(self):
        text = post(1, "x", "X",
                    "<p>LA 24.10. KLO 15:00</p><p>Elokuva on kielletty alle 7 v</p>", age="")
        shows, _ = self.rows(text)
        self.assertEqual(shows[0]["rating"], "K-7")


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get = P.get_text
        self.addCleanup(lambda: setattr(P, "get_text", self._get))
        self.calls = []

    def serve(self, body):
        def get_text(url, **kw):
            self.calls.append(url)
            if isinstance(body, Exception):
                raise body
            return body
        P.get_text = get_text

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["pajakka", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def line(self, days, clock):
        """run.main reads the real clock, so a fixture dated in October would go stale."""
        d = datetime.datetime.now(P.FI).date() + datetime.timedelta(days=days)
        wd = ("MA", "TI", "KE", "TO", "PE", "LA", "SU")[d.weekday()]
        return f"<p><strong>{wd} {d.day}.{d.month}. KLO {clock}</strong></p>"

    def kept(self):
        doc = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
               "horizon": "2026-10-20",
               "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(doc), encoding="utf-8")

    def after(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))

    def test_the_site_publishes_from_one_request(self):
        self.serve(json.dumps([
            post(1, "a", "LAPIN SOTA", self.line(1, "18:00") + self.line(2, "18:00")),
            post(2, "b", "PIKKULI", self.line(2, "13:00"), age="s"), EVENT]))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls, [LISTING])
        self.assertEqual(sorted({s["title"] for s in self.after()["shows"]}),
                         ["LAPIN SOTA", "PIKKULI"])
        self.assertIn("1 post(s) with no screening list", log)

    def test_posts_with_no_screening_fail_and_keep_the_previous_file(self):
        self.kept()
        self.serve(json.dumps([EVENT]))
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no screening read", log)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")

    def test_an_answer_that_is_not_json_keeps_the_previous_file(self):
        self.kept()
        self.serve("<html><body>Just a moment...</body></html>")
        code, _ = self.main()
        self.assertNotEqual(code, 0)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("pajakkakino")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Pajakkakino", "pajakkakino.fi", "door", "pajakka", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == p["accent"]), 1)


if __name__ == "__main__":
    unittest.main()
