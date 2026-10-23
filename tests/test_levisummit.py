"""The Cinema Levi Summit reader: the calendar and the film cards on one page.

The fixtures are the page's shapes read on 2026-10-24 (issue #13), cut to what each rule
needs, with two days and two films wherever there is a loop.

What they exist to prove:

- **The ordinary ticket is the price** and the under-12 concession beside it is not.
- **The film's facts come from its card**, joined on the film's slug, including a calendar
  link to the English path.
- **A screening whose weekday is not its date's is left out.**
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import levisummit as L
import registry
import run

SITE = L.SITES[0]
VENUE = SITE["venues"][0]["id"]
LISTING = SITE["base"] + SITE["listing"]
FILM = "https://www.kassiopeia.fi/levi-summit/cinema/"


def card(slug, title, duration="1h 49min",
         age='Ikäraja 7: Kielletty alle 7-vuotiailta.', audio="Finnish", subs=None):
    age_img = (f'<img class="movie-age-rating__img" src="x/rating_large_7.png" alt="{age}" />'
               if age else "")
    subs_div = (f'<div class="movie-subtitles"><span>Tekstitys</span><img class="movie-subtitles__flag" '
                f'src="x.png" alt="{subs}" width="24" height="16" /></div>' if subs else "")
    audio_div = (f'<div class="movie-language"><span>Kieli</span><img class="movie-language__flag" '
                 f'src="x.png" alt="{audio}" width="24" height="16" /></div>' if audio else "")
    return (f'<div class="movies-container__single"><div class="movies-container__single__cover">'
            f'<a href="{FILM}{slug}/"><img class="poster" src="p.jpg" /></a></div>'
            f'<div class="movies-container__single__details"><div class="title-duration">'
            f'<a href="{FILM}{slug}/"><h3><span>{title}</span></h3></a>'
            f'<p class="duration">{duration}</p></div>'
            f'<div class="movies-container__single__details__additional">'
            f'<div class="content-warnings age">{age_img}</div>{audio_div}{subs_div}</div></div></div>')


def show(slug, title, when, path="cinema"):
    url = f"https://www.kassiopeia.fi/levi-summit/{path}/{slug}/"
    return (f"<div class='levi-summit-cinema-show-day__single'><div class='cover'><a href='{url}'>"
            f"<img src='c.webp' alt=''></a></div><div class='levi-summit-cinema-show-day__single__details'>"
            f"<div class='title-showtime'><a href='{url}'>\n<h4>{title}</h4>\n</a>"
            f"<p class='movie-showtime'>{when}<br></p></div></div>"
            f"<div class='levi-summit-cinema-show-day__single__tickets'><span class='movie-tickets'>"
            f"15 €</span><span class='movie-tickets__children'>10 € (alle 12-v)</span></div></div>")


def day(label, *shows):
    return (f'<section class="levi-summit-cinema-show-day-container" data-week-number="46">'
            f'<h3>{label}</h3><div class="levi-summit-cinema-show-day">' + "".join(shows)
            + "</div></section>")


def page(*days, cards=None):
    cards = cards if cards is not None else [
        card("unohdettu-saari", "Unohdettu saari"),
        card("verityn-varjo", "Verityn varjo", duration="1h 57min",
             age="Ikäraja 12: Kielletty alle 12-vuotiailta.", audio="English", subs="Finnish"),
        card("rakkautta-ja-virtahepoja", "Rakkautta ja virtahepoja", duration="1h 41min",
             age="Ikäraja 12: Kielletty alle 12-vuotiailta.", subs="Swedish"),
        card("billie", "Billie", age="Age rating: not defined"),
    ]
    return ('<html><body><div class="show-calendar-filters"></div>' + "".join(days)
            + '<div class="movies-container">' + "".join(cards) + "</div></body></html>")


LIVE = page(
    day("Torstai 12.11.2026",
        show("unohdettu-saari", "Unohdettu saari", "To klo 14:00"),
        show("verityn-varjo", "Verityn varjo", "To klo 17:00")),
    day("Lauantai 14.11.2026",
        show("rakkautta-ja-virtahepoja", "Rakkautta ja virtahepoja", "La klo 17:00", path="en/cinema"),
        show("billie", "Billie", "Pe klo 19:00")),
)


class PageTest(unittest.TestCase):

    def test_every_screening_is_a_row_and_a_wrong_weekday_is_not(self):
        shows, report = L.rows(SITE, LIVE)
        self.assertEqual([(s["start"], s["title"]) for s in shows],
                         [("2026-11-12T14:00:00+02:00", "Unohdettu saari"),
                          ("2026-11-12T17:00:00+02:00", "Verityn varjo"),
                          ("2026-11-14T17:00:00+02:00", "Rakkautta ja virtahepoja")])
        self.assertEqual((report["films"], report["disagree"]), (3, 1))

    def test_the_ordinary_ticket_is_the_price_and_the_concession_is_not(self):
        shows, _ = L.rows(SITE, LIVE)
        self.assertEqual({s["price"] for s in shows}, {"15€"})
        self.assertNotIn("10", " ".join(s["price"] for s in shows))

    def test_the_card_gives_the_facts(self):
        shows, _ = L.rows(SITE, LIVE)
        saari, verity, hippo = shows
        self.assertEqual((saari["len"], saari["rating"], saari["lang"], saari["eventId"],
                          saari["url"], saari["img"]),
                         ("109", "K-7", "FI-A", "unohdettu-saari", FILM + "unohdettu-saari/", ""))
        self.assertEqual((verity["len"], verity["rating"], verity["lang"]),
                         ("117", "K-12", "EN-A, FI-S"))
        self.assertEqual((hippo["rating"], hippo["lang"]), ("K-12", "FI-A, SV-S"))

    def test_an_english_path_link_joins_its_card_and_links_the_finnish_page(self):
        shows, _ = L.rows(SITE, LIVE)
        self.assertEqual(shows[2]["url"], FILM + "rakkautta-ja-virtahepoja/")
        self.assertEqual(shows[2]["len"], "101")

    def test_a_film_with_no_card_publishes_without_facts(self):
        shows, report = L.rows(SITE, page(day("Torstai 12.11.2026",
                                              show("x", "X", "To klo 14:00"),
                                              show("unohdettu-saari", "Unohdettu saari",
                                                   "To klo 17:00"))))
        self.assertEqual([(s["title"], s["len"], s["url"]) for s in shows],
                         [("X", "", FILM + "x/"), ("Unohdettu saari", "109",
                                                  FILM + "unohdettu-saari/")])
        self.assertEqual(report["no_card"], 1)

    def test_an_undefined_rating_and_an_unknown_language_publish_nothing(self):
        cards = [card("a", "A", age="Age rating: not defined", audio="Klingon"),
                 card("b", "B", audio="Finnish")]
        shows, _ = L.rows(SITE, page(day("Torstai 12.11.2026", show("a", "A", "To klo 14:00"),
                                         show("b", "B", "To klo 17:00")), cards=cards))
        self.assertEqual([(s["rating"], s["lang"]) for s in shows], [("", ""), ("K-7", "FI-A")])


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get = L.get_text
        self.addCleanup(lambda: setattr(L, "get_text", self._get))
        self.calls = []

    def serve(self, body):
        def get_text(url, **kw):
            self.calls.append(url)
            return body
        L.get_text = get_text

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["levisummit", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def day(self, days, slug, title):
        """run.main reads the real clock, so a fixture dated in November would go stale."""
        d = datetime.datetime.now(L.FI).date() + datetime.timedelta(days=days)
        names = ("Maanantai", "Tiistai", "Keskiviikko", "Torstai", "Perjantai", "Lauantai",
                 "Sunnuntai")
        wd = ("Ma", "Ti", "Ke", "To", "Pe", "La", "Su")[d.weekday()]
        return day(f"{names[d.weekday()]} {d.day}.{d.month}.{d.year}",
                   show(slug, title, f"{wd} klo 17:00"))

    def kept(self):
        doc = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
               "horizon": "2026-10-20",
               "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(doc), encoding="utf-8")

    def after(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))

    def test_the_site_publishes_from_one_request(self):
        self.serve(page(self.day(1, "unohdettu-saari", "Unohdettu saari"),
                        self.day(2, "verityn-varjo", "Verityn varjo")))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls, [LISTING])
        self.assertEqual(sorted({s["title"] for s in self.after()["shows"]}),
                         ["Unohdettu saari", "Verityn varjo"])

    def test_an_empty_calendar_fails_and_keeps_the_previous_file(self):
        self.kept()
        self.serve(page())
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no screening in the calendar", log)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        r = registry.by_id("levisummit")
        self.assertEqual((r["label"], r["host"], r["book"], r["module"], r["where"]),
                         ("Cinema Levi Summit", "levisummit.fi", "door", "levisummit", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS if q["accent"] == r["accent"]), 1)


if __name__ == "__main__":
    unittest.main()
