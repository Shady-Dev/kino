"""Navettakino: one card per film on the front page, and a page of its own per film.

The fixtures follow the markup read on 2026-11-01, the day the site moved to its PHP page.
The cards are the schedule. The ticket link is the card's own `Varaa` href, copied as it
stands. The synopsis comes from the film page. An empty programme is confirmed only when
the heading renders and no date or clock appears anywhere, and a missing heading fails.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import types
import unittest

import _ctx                                                # noqa: F401
import navetta as N
import registry
import run


SITE = N.SITES[0]
BASE = "https://www.navettakino.fi/"
TODAY = datetime.date(2026, 10, 31)          # a Saturday
SYN = ("Elokuvan tapahtumat sijoittuvat Lappiin syksyllä 1944, Suomen ja Saksan väliseen "
       "konfliktiin toisen maailmansodan loppuvaiheessa.")
SYN2 = ("Nuori sotamies Heikki taistelee Karjalan kannaksella ystävänsä Paulin kanssa, ja "
        "komppaniaan liittyy vankilasta vapautunut Arvo.")


def card(title, *lines, meta="K16, kesto 158 min, liput 11 €", film="100004470",
         img=True):
    """`lines` are (text, href). An href of None prints the line without a link."""
    shows = "".join(f"<p>{text} - <a href='{href}'>Varaa</a></p>" if href else
                    f"<p>{text}</p>" for text, href in lines)
    pic = f"<img src=kuvat/jul_{film}.jpg alt='Juliste' style='width:100%'>" if img else ""
    link = f"<a href='leffa?id={film}'>{pic}</a>" if film else pic
    return ("<div class='w3-auto w3-padding-16 w3-col s12 m6 l4'>"
            "<div class='w3-auto w3-card w3-container' style='width:300px;max-width:100%'>"
            f"{link}<h2>{title}</h2><p>{meta}</p>"
            "<div class='w3-container w3-margin'><h4>Näytökset</h4>"
            f"{shows}</div></div></div>\n")


def page(*cards, heading=True, box="<h2>Tänään</h2><p>Lapin sota klo 17:00</p>"):
    head = (f"<div class='w3-container w3-auto'><h2>Seuraavat näytökset</h2>"
            f"<div class='w3-container w3-auto'><div class='w3-border w3-light-gray'>{box}"
            f"</div></div></div>" if heading else "")
    return ('<!DOCTYPE html><html lang="fi"><meta charset="UTF-8"><title>Navettakino</title>'
            '<body><a href="index.php"><img src="logo.png" alt="Navettakino"></a>'
            '<div class="w3-auto w3-bar w3-navetta">'
            '<a href="tulevaa.php" class="w3-bar-item w3-button">Tuleva ohjelmisto</a></div>'
            + head + "\n<!-- Leffakontit -->\n<div class='w3-row-padding w3-auto'>\n"
            + "".join(cards) + "<!-- End of LEFFAKONTIT -->\n</div>\n"
            '<footer class="w3-container w3-navetta w3-auto">'
            "<p>Navettakino, Pyhälahdentie 972, Konnevesi</p><p>(c) 2026 Navettakino</p>"
            "</footer></body></html>")


def film_page(title, syn=SYN + "\n\n" + SYN2 + "\n\nElokuvateattereissa 23.10.",
              trailer=True, cast="Peter Franzén, Sannah Nedergård"):
    video = ("<iframe width='560' height='315' src='https://www.youtube.com/embed/x'"
             "title='Youtube' allowfullscreen></iframe>" if trailer else "")
    text = f"<p>{syn}</p>" if syn else ""
    return ('<html><body><div class="w3-auto w3-container">'
            f"<h2>{title}</h2>{video}{text}"
            f"<p><b>Pääosissa:</b> {cast}</p>"
            "<p><b>Ikäraja:</b> 16</p><p><b>Kesto:</b> 158 min</p>"
            "<h3>Näytösajat:</h3><p>Sunnuntai 01.11 klo 17:00 - "
            "<a href='varaa.php?id=80'>Varaa</a></p></div>"
            "<footer><p>(c) 2026 Navettakino</p></footer></body></html>")


TWO = page(card("Lapin sota", ("la 31.10 klo 17:00", "varaa.php?id=79"),
                ("su 01.11 klo 17:00", "varaa.php?id=80")),
           card("Angry Birds -elokuva 3", ("la 31.10 klo 13:00", "varaa.php?id=81"),
                ("su 01.11 klo 13:00", None),
                meta="K7, kesto 1 h 37 min, liput 8 €", film="100004471"))


class RowsTest(unittest.TestCase):
    def rows(self, html, today=TODAY):
        return N.rows(SITE, html, today)[0]

    def test_two_films_publish_with_their_facts(self):
        out = self.rows(TWO)
        self.assertEqual([(s["title"], s["start"]) for s in out], [
            ("Angry Birds -elokuva 3", "2026-10-31T13:00:00+02:00"),
            ("Lapin sota", "2026-10-31T17:00:00+02:00"),
            ("Angry Birds -elokuva 3", "2026-11-01T13:00:00+02:00"),
            ("Lapin sota", "2026-11-01T17:00:00+02:00")])
        lapin = [s for s in out if s["title"] == "Lapin sota"][0]
        birds = [s for s in out if s["title"] != "Lapin sota"][0]
        self.assertEqual((lapin["price"], lapin["len"], lapin["rating"]), ("11€", "158", "K-16"))
        self.assertEqual((birds["price"], birds["len"], birds["rating"]), ("8€", "97", "K-7"))
        self.assertEqual(lapin["img"], BASE + "kuvat/jul_100004470.jpg")
        self.assertEqual(birds["img"], BASE + "kuvat/jul_100004471.jpg")

    def test_the_ticket_link_is_the_cards_own_href(self):
        urls = {s["start"][:16] + s["title"][:5]: s["url"] for s in self.rows(TWO)}
        self.assertEqual(urls["2026-10-31T17:00Lapin"], BASE + "varaa.php?id=79")
        self.assertEqual(urls["2026-11-01T17:00Lapin"], BASE + "varaa.php?id=80")
        self.assertEqual(urls["2026-10-31T13:00Angry"], BASE + "varaa.php?id=81")

    def test_a_line_without_a_link_opens_the_film_page(self):
        birds = [s for s in self.rows(TWO) if s["start"].startswith("2026-11-01T13")][0]
        self.assertEqual(birds["url"], BASE + "leffa?id=100004471")
        self.assertEqual(N.rows(SITE, TWO, TODAY)[1]["no_ticket"], {"Angry Birds -elokuva 3"})

    def test_a_card_without_a_film_link_opens_the_front_page(self):
        html = page(card("A", ("la 31.10 klo 17:00", None), film=""),
                    card("B", ("su 01.11 klo 17:00", None), film=""))
        self.assertEqual([s["url"] for s in self.rows(html)], [BASE, BASE])

    def test_a_ticket_figure_that_is_not_one_amount_settles_nothing(self):
        html = page(card("A", ("la 31.10 klo 17:00", None), meta="K7, liput 8 € / 6 €"),
                    card("B", ("su 01.11 klo 17:00", None), meta="K7, 90 min"))
        self.assertEqual([s["price"] for s in self.rows(html)], ["", ""])
        self.assertEqual(N.rows(SITE, html, TODAY)[1]["no_price"], {"A", "B"})

    def test_a_line_that_is_no_date_fails_the_site(self):
        html = page(card("A", ("la 31.10 klo 17:00", None), ("sunnuntaina klo 17", None)))
        with self.assertRaisesRegex(N.ListingError, "sunnuntaina klo 17"):
            self.rows(html)

    def test_an_impossible_date_fails_the_site(self):
        html = page(card("A", ("la 31.10 klo 17:00", None), ("ma 31.11 klo 17:00", None)))
        with self.assertRaisesRegex(N.ListingError, "impossible date|no candidate year"):
            self.rows(html)

    def test_a_weekday_no_candidate_year_carries_fails_the_site(self):
        html = page(card("A", ("la 31.10 klo 17:00", None), ("ma 01.11 klo 17:00", None)))
        with self.assertRaisesRegex(N.ListingError, "no candidate year"):
            self.rows(html)

    def test_a_page_with_no_heading_fails_the_site(self):
        html = page(card("A", ("la 31.10 klo 17:00", None)), heading=False)
        with self.assertRaisesRegex(N.ListingError, "Seuraavat näytökset"):
            self.rows(html)

    def test_cards_without_screenings_parse_to_nothing(self):
        self.assertEqual(self.rows(page(card("A"), card("B", film="2"))), [])

    def test_the_show_shape(self):
        s = self.rows(TWO)[0]
        self.assertEqual(set(s), {"eventId", "title", "original", "len", "rating", "genres",
                                  "method", "theatre", "aud", "start", "url", "img", "lang",
                                  "soldOut", "price", "provider", "venue", "_film"})
        self.assertEqual((s["provider"], s["venue"], s["theatre"]),
                         ("navettakino", "navettakino-konnevesi", "Navettakino"))


class SynopsisTest(unittest.TestCase):
    def test_the_paragraphs_join_and_the_release_note_is_dropped(self):
        self.assertEqual(N.synopsis(film_page("Lapin sota")), SYN + " " + SYN2)

    def test_a_page_without_a_trailer_reads_the_same(self):
        self.assertEqual(N.synopsis(film_page("Lapin sota", trailer=False)), SYN + " " + SYN2)

    def test_a_labelled_paragraph_is_never_the_synopsis(self):
        cast = ", ".join(["Peter Franzén", "Sannah Nedergård", "Volker Bruch"] * 5)
        self.assertEqual(N.synopsis(film_page("Lapin sota", syn="", cast=cast)), "")

    def test_paragraphs_split_by_line_breaks_join_too(self):
        html = film_page("A", syn=SYN + "<br><br>" + SYN2)
        self.assertEqual(N.synopsis(html), SYN + " " + SYN2)


class FetchSiteTest(unittest.TestCase):
    def setUp(self):
        self._fetch, self._time = N.fetch, N.time
        self.addCleanup(lambda: (setattr(N, "fetch", self._fetch),
                                 setattr(N, "time", self._time)))
        self.sleeps, self.asked = [], []
        N.time = types.SimpleNamespace(sleep=self.sleeps.append)

    def serve(self, pages):
        def fetch(url, **kw):
            self.asked.append(url)
            body = pages[url]
            if isinstance(body, Exception):
                raise body
            return body.encode("utf-8")
        N.fetch = fetch

    def site(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            shows = N.fetch_site(SITE, TODAY)["navettakino-konnevesi"]
        return shows, err.getvalue()

    def test_each_film_page_is_read_once_paced_and_the_ticket_page_never(self):
        self.serve({BASE: TWO, BASE + "leffa?id=100004470": film_page("Lapin sota"),
                    BASE + "leffa?id=100004471": film_page("Angry Birds", syn=SYN2)})
        shows, _ = self.site()
        self.assertEqual(sorted(self.asked), [BASE, BASE + "leffa?id=100004470",
                                              BASE + "leffa?id=100004471"])
        self.assertEqual(self.sleeps, [1.5])
        syn = {s["title"]: s.get("_syn") for s in shows}
        self.assertEqual(syn, {"Lapin sota": SYN + " " + SYN2, "Angry Birds -elokuva 3": SYN2})
        self.assertFalse(any("_film" in s for s in shows))

    def test_a_failing_film_page_keeps_the_screenings(self):
        self.serve({BASE: TWO, BASE + "leffa?id=100004470": RuntimeError("HTTP Error 500"),
                    BASE + "leffa?id=100004471": film_page("Angry Birds", syn=SYN2)})
        shows, err = self.site()
        self.assertEqual(len(shows), 4)
        self.assertEqual({s["title"]: s.get("_syn") for s in shows},
                         {"Lapin sota": None, "Angry Birds -elokuva 3": SYN2})
        self.assertIn("leffa?id=100004470: RuntimeError: HTTP Error 500", err)


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
        self._fetch, self._time = N.fetch, N.time
        self.addCleanup(lambda: (setattr(N, "fetch", self._fetch),
                                 setattr(N, "time", self._time)))
        N.time = types.SimpleNamespace(sleep=lambda s: None)
        self.file = run.OUT / "area-navettakino-konnevesi.json"

    def serve(self, front, films=None):
        def fetch(url, **kw):
            body = front if url == BASE else (films or {}).get(url, "")
            if isinstance(body, Exception):
                raise body
            return body.encode("utf-8")
        N.fetch = fetch

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["navetta"])
        return code, out.getvalue() + err.getvalue()

    def line(self, days, clock):
        d = datetime.datetime.now(N.FI).date() + datetime.timedelta(days=days)
        wd = ("ma", "ti", "ke", "to", "pe", "la", "su")[d.weekday()]
        return f"{wd} {d.day:02d}.{d.month:02d} klo {clock}"

    def test_the_site_publishes(self):
        self.serve(page(card("A", (self.line(1, "15:00"), "varaa.php?id=1"),
                             (self.line(2, "15:00"), "varaa.php?id=2"), film="1"),
                        card("B", (self.line(1, "17:00"), None),
                             (self.line(2, "17:00"), None), film="2",
                             meta="K12, kesto 90 min, liput 8 €")),
                   {BASE + "leffa?id=1": film_page("A"), BASE + "leffa?id=2": film_page("B")})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        shows = json.loads(self.file.read_text())["shows"]
        self.assertEqual(sorted(s["price"] for s in shows), ["11€", "11€", "8€", "8€"])
        self.assertIn("0 failures", log)

    def test_cards_without_screenings_keep_the_previous_file_without_failing(self):
        """The page's empty state has not been seen, so two dateless film cards keep the
        saved screening (review of 2026-11-02), and the run does not fail."""
        self.file.write_text(json.dumps(self.PREV))
        self.serve(page(card("A"), card("B", film="2"), box=""))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertIn("[navettakino] no screenings:", log)
        self.assertIn("Film cards: A, B.", log)
        self.assertNotIn("no programme at the moment", log)
        self.assertEqual(json.loads(self.file.read_text()), self.PREV)

    def test_times_the_cards_do_not_carry_fail_and_keep_the_previous_file(self):
        """The box above the cards prints a clock while no card prints a screening. That is
        a screening the parser missed, and the weekend is not confirmed empty."""
        for name, box in (("a clock in the box", "<h2>Tänään</h2><p>A klo 17:00</p>"),
                          ("a date in the box", "<h2>Huomenna</h2><p>A su 01.11</p>")):
            with self.subTest(name):
                self.file.write_text(json.dumps(self.PREV))
                self.serve(page(card("A"), card("B", film="2"), box=box))
                code, log = self.main()
                self.assertEqual(code, 1, log)
                self.assertIn("prints a date or time elsewhere", log)
                self.assertNotIn("no programme at the moment", log)
                self.assertEqual(json.loads(self.file.read_text()), self.PREV)

    def test_a_page_with_no_heading_fails_and_keeps_the_previous_file(self):
        self.file.write_text(json.dumps(self.PREV))
        self.serve(page(card("A"), heading=False))
        code, log = self.main()
        self.assertEqual(code, 1, log)
        self.assertEqual(json.loads(self.file.read_text()), self.PREV)

    def test_a_refused_page_keeps_the_previous_file(self):
        self.file.write_text(json.dumps(self.PREV))
        self.serve(RuntimeError("HTTP Error 503"))
        code, log = self.main()
        self.assertEqual(code, 1, log)
        self.assertEqual(json.loads(self.file.read_text()), self.PREV)


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        prov = registry.by_id("navettakino")
        self.assertEqual((prov["label"], prov["host"], prov["book"], prov["module"],
                          prov["where"]),
                         ("Navettakino", "navettakino.fi", "reserve", "navetta", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == prov["accent"]), 1)

    def test_the_site_names_the_host_it_reads(self):
        self.assertEqual([s["base"] for s in N.SITES], ["https://www.navettakino.fi"])
        self.assertEqual(len(run.host_groups(N.SITES)), 1)

    def test_the_label_is_the_venue_name(self):
        self.assertEqual(SITE["venues"][0]["name"], registry.by_id("navettakino")["label"])
        self.assertEqual(SITE["venues"][0]["city"], "Konnevesi")


if __name__ == "__main__":
    unittest.main()
