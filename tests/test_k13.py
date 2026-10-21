"""The Kino K13 reader: one section of prose, and the organiser page a Kinokka evening links.

The fixtures are the section as read on 2026-09-21, cut to the smallest shape that still
exercises a rule. The Kinokka fixtures follow the markup of both pages as read on
2026-10-20. Two blocks and two rows everywhere there is a loop.

What they exist to prove:

- **A line with a weekday, a date and a clock is a screening.**
- **A Kinokka evening is published only at the start time the page it links states**, for
  a date that page lists. Without such a page it publishes nothing and is counted.
- **A festival heading is a date range, not a row.**
- **Free admission belongs to the block it is stated under**, not to the page.
- **A timed row prints no year**, and the weekday places it.
- **The rating is the trailing sentence**, and a row without one leaves it empty.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import _no_sleep as no_sleep
import k13 as K
import registry
import run


SITE = K.SITES[0]
BASE = SITE["base"]
VENUE = SITE["venues"][0]["id"]
LISTING = BASE + SITE["listing"]
URL = BASE + SITE["listing"] + SITE["anchor"]
TODAY = datetime.date(2026, 9, 21)

FESTIVAL = "5.–9.10.2026 Puolan elokuvaviikot – Polish Film Weeks"
FREE = "Näytöksiin on vapaa pääsy. Saliin mahtuu 150 katsojaa."
ROW1 = ("ma 5.10. klo 18: LUVATTU MAA (Ziemia obiecana) 1974, 179 min. "
        "Sallittu yli 16-vuotiaille.")
ROW2 = ("ti 6.10. klo 18: KUORIPOJAT (Ministranci) 2025, 105 min. "
        "Sallittu yli 12-vuotiaille.")
SHORTS = "ke 7.10. klo 18: STUDIO MUNKA, 3 lyhytelokuvaa."
KINOKKA = "27.9.2026 Kinokka: Ei karhuja"
KINOKKA_BODY = "Ohjaaja: Jafar Panahi, 2022, Iran. Sallittu yli 7-vuotiaille."
ORGANISER = "https://kaupunginosat.fi/skatta/ohjelmisto/"
Y2026, Y2027 = "<p><strong>2026</strong></p>", "<p><strong>2027</strong></p>"
JOYLAND = "25.10 Joyland, ohjaaja: Saim Sadiq, 2022 Pakistan"
KOTIINPALUU = "22.11 Kotiinpaluu, ohjaaja: Davy Chou, 2022 Belgia, Saksa, Ranska"
STARTS = "Esitykset alkavat 16:00."
DIRECTED = "Ohjaaja: Saim Sadiq, 2022, Pakistan. Sallittu yli 12-vuotiaille."


def page(*lines):
    """The section. A line starting with `<` is markup and goes in as it is."""
    body = "".join(x if x.startswith("<") else f"<p>{x}</p>"
                   for x in (lines or (FESTIVAL, FREE, ROW1)))
    return ('<html><body><section id=ohjelmisto class="l-visual-editor">'
            '<h2>Avoimet yleisönäytökset</h2>'
            f'<div class="l-visual-editor__item wysiwyg">{body}</div>'
            "</section></body></html>")


def kinokka(date, title, body=DIRECTED, link=ORGANISER):
    """A Kinokka evening: the title in its own `<i>`, then the body and the organiser link
    split by a `<br />`."""
    return (f'<p class="p3"><strong>{date} Kinokka: <i>{title}</i></strong></p>'
            f'<p class="p3">{body}<br />\n<a href="{link}">{link}</a></p>')


def organiser(*listed, starts=STARTS, after=""):
    """The organiser page: its upcoming block, then the past list's `<h3>` and `after`."""
    lines = "".join(x if x.startswith("<") else f"<p>{x}</p>" for x in listed)
    return ('<html><body><div class="td-post-content">'
            '<h3 style="text-align: left">Tuleva ohjelmisto</h3>'
            f"<div>{lines}</div>"
            f"<ul><li>Elokuvalipun hinta on 8 €.</li><li>{starts}</li></ul>"
            f"<h3>Esitetyt elokuvat</h3>{after}</div></body></html>")


class SectionTest(unittest.TestCase):
    def rows(self, *lines, today=TODAY):
        return K.rows(SITE, page(*lines), today)

    def test_every_timed_line_of_the_block_becomes_a_row(self):
        shows, report = self.rows(FESTIVAL, FREE, ROW1, ROW2)
        self.assertEqual([(s["title"], s["start"]) for s in shows], [
            ("LUVATTU MAA", "2026-10-05T18:00:00+03:00"),
            ("KUORIPOJAT", "2026-10-06T18:00:00+03:00"),
        ])
        self.assertEqual(report["headings"], 1)

    def test_a_dated_entry_with_no_clock_publishes_nothing_and_is_counted(self):
        """A Kinokka evening with no linked page to time it."""
        shows, report = self.rows(KINOKKA, KINOKKA_BODY, FESTIVAL, FREE, ROW1)
        self.assertEqual([s["title"] for s in shows], ["LUVATTU MAA"])
        self.assertEqual(report["no_time"], 1)

    def test_a_festival_heading_is_not_a_screening(self):
        shows, report = self.rows(FESTIVAL, FREE)
        self.assertEqual((shows, report["headings"]), ([], 1))

    def test_free_admission_reaches_the_rows_under_its_heading(self):
        shows, _ = self.rows(FESTIVAL, FREE, ROW1, ROW2)
        self.assertEqual([s["price"] for s in shows], ["Vapaa pääsy"] * 2)

    def test_free_admission_does_not_cross_into_the_next_block(self):
        """A later block states its own terms or states none."""
        shows, _ = self.rows(FESTIVAL, FREE, ROW1,
                             "6.–8.11.2026 Serbian elokuvapäivät",
                             "pe 6.11. klo 18: ODOTUS, 95 min.")
        self.assertEqual([(s["title"], s["price"]) for s in shows],
                         [("LUVATTU MAA", "Vapaa pääsy"), ("ODOTUS", "")])

    def test_a_row_with_no_free_admission_line_publishes_no_price(self):
        shows, _ = self.rows(FESTIVAL, ROW1)
        self.assertEqual(shows[0]["price"], "")

    def test_the_year_comes_from_the_weekday_because_the_row_prints_none(self):
        """5.10. is a Monday in 2026 and a Sunday in 2025, and the row says ma."""
        shows, _ = self.rows(FESTIVAL, ROW1)
        self.assertEqual(shows[0]["start"], "2026-10-05T18:00:00+03:00")

    def test_a_weekday_no_candidate_year_holds_is_counted_and_left_out(self):
        shows, report = self.rows(FESTIVAL, "su 5.10. klo 18: LUVATTU MAA, 179 min.")
        self.assertEqual((shows, report["undated"]), ([], 1))

    def test_a_clock_without_minutes_is_read_as_the_hour(self):
        shows, _ = self.rows(FESTIVAL, "to 8.10 klo 18: HYVÄ TALO (Dom dobry) 2025, 107 min.")
        self.assertEqual(shows[0]["start"], "2026-10-08T18:00:00+03:00")

    def test_a_clock_with_minutes_keeps_them(self):
        shows, _ = self.rows(FESTIVAL, "ma 5.10. klo 18.30: LUVATTU MAA, 179 min.")
        self.assertEqual(shows[0]["start"], "2026-10-05T18:30:00+03:00")

    def test_the_original_title_and_the_runtime_are_read_when_the_row_states_them(self):
        s = self.rows(FESTIVAL, ROW1)[0][0]
        self.assertEqual((s["title"], s["original"], s["len"]),
                         ("LUVATTU MAA", "Ziemia obiecana", "179"))

    def test_a_row_stating_neither_leaves_both_empty(self):
        s = self.rows(FESTIVAL, SHORTS)[0][0]
        self.assertEqual((s["title"], s["original"], s["len"], s["rating"]),
                         ("STUDIO MUNKA", "", "", ""))

    def test_the_rating_is_the_trailing_sentence(self):
        self.assertEqual(K.rating_of("Sallittu yli 16-vuotiaille."), "K-16")
        self.assertEqual(K.rating_of("Sallittu yli 7-vuotiaille."), "K-7")
        self.assertEqual(K.rating_of("Sallittu kaikenikäisille."), "S")
        self.assertEqual(K.rating_of("3 lyhytelokuvaa."), "")

    def test_the_emitted_row_carries_the_rating_from_its_own_line(self):
        shows, _ = self.rows(FESTIVAL, ROW1, ROW2, SHORTS)
        self.assertEqual([(s["title"], s["rating"]) for s in shows],
                         [("LUVATTU MAA", "K-16"), ("KUORIPOJAT", "K-12"),
                          ("STUDIO MUNKA", "")])

    def test_a_line_whose_hour_is_only_implied_publishes_nothing(self):
        """`27.9.2026 Kinokka: Ei karhuja` has a date, a colon and a title, and the hour
        would have to be invented. A parser that defaulted it to midnight would publish
        every Kinokka evening at 00:00."""
        shows, report = self.rows(FESTIVAL, "27.9.2026 Kinokka: Ei karhuja", ROW1)
        self.assertEqual([s["title"] for s in shows], ["LUVATTU MAA"])
        self.assertNotIn("00:00", [s["start"][11:16] for s in shows])
        self.assertEqual(report["no_time"], 1)

    def test_the_show_shape(self):
        s = self.rows(FESTIVAL, FREE, ROW1)[0][0]
        self.assertEqual((s["provider"], s["venue"], s["aud"], s["lang"], s["method"],
                          s["genres"], s["img"], s["soldOut"]),
                         ("k13", VENUE, "", "", "", "", "", False))
        self.assertEqual((s["theatre"], s["eventId"], s["url"]),
                         ("Kino K13", "luvattu-maa", URL))


class KinokkaTest(unittest.TestCase):
    """A Kinokka evening's date and title on this page, its start time on the organiser's."""

    def rows(self, evenings, *listed, starts=STARTS, after=""):
        linked = {ORGANISER: organiser(*listed, starts=starts, after=after)}
        return K.rows(SITE, page(*evenings), TODAY, linked)

    def test_an_evening_is_timed_from_the_page_it_links(self):
        shows, report = self.rows(
            [kinokka("25.10.2026", "Joyland"), kinokka("22.11.2026", "Kotiinpaluu")],
            Y2026, JOYLAND, KOTIINPALUU)
        self.assertEqual([(s["title"], s["start"], s["url"], s["price"]) for s in shows], [
            ("Joyland", "2026-10-25T16:00:00+02:00", URL, ""),
            ("Kotiinpaluu", "2026-11-22T16:00:00+02:00", URL, ""),
        ])
        self.assertEqual(report["linked"], 2)

    def test_the_clock_is_the_one_the_linked_page_states(self):
        shows, _ = self.rows([kinokka("25.10.2026", "Joyland")], Y2026, JOYLAND,
                             starts="Esitykset alkavat 18.30.")
        self.assertEqual(shows[0]["start"], "2026-10-25T18:30:00+02:00")

    def test_a_page_stating_no_single_start_time_times_nothing(self):
        """No clock, or two, settles no hour."""
        for starts in ("Saliin mahtuu 150 henkilöä.",
                       "Esitykset alkavat 16:00. Lauantaisin esitykset alkavat 14:00."):
            with self.subTest(starts=starts):
                shows, report = self.rows(
                    [kinokka("25.10.2026", "Joyland"), kinokka("22.11.2026", "Kotiinpaluu")],
                    Y2026, JOYLAND, KOTIINPALUU, starts=starts)
                self.assertEqual((shows, report["no_time"]), ([], 2))

    def test_an_evening_the_linked_page_does_not_list_publishes_nothing(self):
        shows, report = self.rows(
            [kinokka("25.10.2026", "Joyland"), kinokka("22.11.2026", "Kotiinpaluu")],
            Y2026, KOTIINPALUU)
        self.assertEqual([s["title"] for s in shows], ["Kotiinpaluu"])
        self.assertEqual(report["unlisted"], 1)

    def test_a_date_listed_for_another_film_publishes_nothing(self):
        shows, report = self.rows(
            [kinokka("25.10.2026", "Joyland"), kinokka("22.11.2026", "Kotiinpaluu")],
            Y2026, "25.10 Ei karhuja, ohjaaja: Jafar Panahi", KOTIINPALUU)
        self.assertEqual([s["title"] for s in shows], ["Kotiinpaluu"])
        self.assertEqual(report["unlisted"], 1)

    def test_a_date_listed_with_no_film_yet_is_timed(self):
        """`24.1.` under 2027 names no film, which contradicts nothing."""
        shows, _ = self.rows([kinokka("24.1.2027", "Joyland")], Y2027, "24.1.")
        self.assertEqual(shows[0]["start"], "2027-01-24T16:00:00+02:00")

    def test_the_year_line_above_a_date_places_it(self):
        shows, report = self.rows(
            [kinokka("24.1.2027", "Joyland"), kinokka("24.1.2026", "Kotiinpaluu")],
            Y2026, KOTIINPALUU, Y2027, "24.1.")
        self.assertEqual([(s["title"], s["start"][:10]) for s in shows],
                         [("Joyland", "2027-01-24")])
        self.assertEqual(report["unlisted"], 1)

    def test_the_upcoming_block_ends_at_the_next_heading_of_its_level(self):
        """The live page lists 13.12 in an `<h5>` inside the block, and the past list
        that follows under an `<h3>` is not upcoming."""
        shows, report = self.rows(
            [kinokka("13.12.2026", "Vasenkätinen tyttö"), kinokka("27.9.2026", "Ei karhuja")],
            Y2026, "<h5>13.12 Vasenkätinen tyttö, ohjaaja: Shih-Ching Tsou, 2025 Taiwan. "
                   "<br />Aluksi lyhytelokuva: Ampumarata</h5>",
            after=Y2026 + "<p>27.9 Ei karhuja</p>")
        self.assertEqual([s["title"] for s in shows], ["Vasenkätinen tyttö"])
        self.assertEqual(report["unlisted"], 1)

    def test_the_rating_is_read_from_the_evenings_own_lines(self):
        shows, _ = self.rows(
            [kinokka("25.10.2026", "Joyland"),
             kinokka("22.11.2026", "Kotiinpaluu", body="Ohjaaja: Davy Chou, 2022.")],
            Y2026, JOYLAND, KOTIINPALUU)
        self.assertEqual([(s["title"], s["rating"]) for s in shows],
                         [("Joyland", "K-12"), ("Kotiinpaluu", "")])

    def test_the_films_year_is_the_one_its_director_line_states(self):
        """The TMDB search's hint. An evening with no director line publishes none."""
        shows, _ = self.rows(
            [kinokka("25.10.2026", "Joyland"),
             kinokka("22.11.2026", "Kotiinpaluu", body="Sallittu yli 12-vuotiaille.")],
            Y2026, JOYLAND, KOTIINPALUU)
        self.assertEqual([(s["title"], s.get("year")) for s in shows],
                         [("Joyland", "2022"), ("Kotiinpaluu", None)])

    def test_only_an_evenings_own_link_to_a_declared_host_is_followed(self):
        """A festival's link, a link to an undeclared host and the Lyhyesti button are not
        followed, and two evenings linking one page name it once."""
        p = page(kinokka("25.10.2026", "Joyland"),
                 "6.–8.11.2026 Serbian elokuvapäivät",
                 '<p>Ilmoittautuminen: <a href="https://kaupunginosat.fi/skatta/x/">x</a></p>',
                 kinokka("22.11.2026", "Kotiinpaluu"),
                 kinokka("13.12.2026", "Vasenkätinen tyttö",
                         link="https://example.invalid/k/"),
                 '<h4>Lyhyesti</h4><p><a href="https://www.ses.fi/lyhyesti/">Lyhyesti</a></p>')
        self.assertEqual(K.follow(SITE, p), [ORGANISER])


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get = K.get_text
        self.addCleanup(lambda: setattr(K, "get_text", self._get))
        self.calls = []

    def serve(self, pages):
        def get_text(url, **kw):
            self.calls.append(url)
            body = pages.get(url)
            if isinstance(body, Exception):
                raise body
            if body is None:
                raise RuntimeError(f"unexpected fetch {url}")
            return body
        K.get_text = get_text

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["k13", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def line(self, days, film):
        """A screening line `days` from today. run.main reads the real clock, and ROW1's
        5.10. leaves the 30-day window on 2026-11-05."""
        d = datetime.datetime.now(K.FI).date() + datetime.timedelta(days=days)
        wd = ("ma", "ti", "ke", "to", "pe", "la", "su")[d.weekday()]
        return f"{wd} {d.day}.{d.month}. klo 18: {film}"

    def test_the_site_publishes_from_one_request(self):
        self.serve({LISTING: page(KINOKKA, KINOKKA_BODY, FESTIVAL, FREE,
                                  self.line(1, "LUVATTU MAA (Ziemia obiecana) 1974, 179 min."),
                                  self.line(2, "KUORIPOJAT (Ministranci) 2025, 105 min."))})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls, [LISTING])
        shows = json.loads(
            (run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))["shows"]
        self.assertEqual(sorted({s["title"] for s in shows}), ["KUORIPOJAT", "LUVATTU MAA"])
        self.assertIn("with no clock", log)

    def test_a_section_with_no_timed_row_fails_and_keeps_the_previous_file(self):
        kept = {"generated": "2026-09-20T00:00:00+00:00", "dates": ["2026-09-20"],
                "horizon": "2026-09-20",
                "shows": [{"title": "Yesterday", "start": "2026-09-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(kept), encoding="utf-8")
        self.serve({LISTING: page(KINOKKA, KINOKKA_BODY)})
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no screening line", log)
        after = json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))
        self.assertEqual(after["shows"][0]["title"], "Yesterday")

    def test_a_refused_request_keeps_the_previous_file(self):
        kept = {"generated": "2026-09-20T00:00:00+00:00", "dates": [], "horizon": "",
                "shows": [{"title": "Yesterday", "start": "2026-09-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(kept), encoding="utf-8")
        self.serve({LISTING: RuntimeError("503 refused")})
        code, log = self.main()
        self.assertNotEqual(code, 0)
        after = json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))
        self.assertEqual(after["shows"][0]["title"], "Yesterday")

    def test_a_page_of_kinokka_evenings_publishes_from_the_page_they_link(self):
        """The page as it stood on 2026-10-20, with no timed row. Two evenings linking one
        page cost one request to it."""
        self.serve({LISTING: page(kinokka("25.10.2026", "Joyland"),
                                  "6.–8.11.2026 Serbian elokuvapäivät",
                                  kinokka("22.11.2026", "Kotiinpaluu")),
                    ORGANISER: organiser(Y2026, JOYLAND, KOTIINPALUU)})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls, [LISTING, ORGANISER])
        shows = json.loads(
            (run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))["shows"]
        self.assertEqual([(s["title"], s["start"]) for s in shows],
                         [("Joyland", "2026-10-25T16:00:00+02:00"),
                          ("Kotiinpaluu", "2026-11-22T16:00:00+02:00")])
        self.assertIn(f"{ORGANISER}: start time 16:00", log)

    def test_two_linked_pages_are_read_one_after_the_other(self):
        second = "https://kaupunginosat.fi/skatta/kevat/"
        clock = no_sleep.patch(self, K)
        self.serve({LISTING: page(kinokka("25.10.2026", "Joyland"),
                                  kinokka("24.1.2027", "Kotiinpaluu", link=second)),
                    ORGANISER: organiser(Y2026, JOYLAND),
                    second: organiser(Y2027, "24.1.")})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls, [LISTING, ORGANISER, second])
        self.assertEqual(clock.slept, [1.2])

    def test_a_linked_page_that_cannot_be_read_fails_and_keeps_the_previous_file(self):
        """The timed row alone would publish, and the Kinokka evening with it would be lost."""
        kept = {"generated": "2026-09-20T00:00:00+00:00", "dates": [], "horizon": "",
                "shows": [{"title": "Yesterday", "start": "2026-09-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(kept), encoding="utf-8")
        self.serve({LISTING: page(kinokka("25.10.2026", "Joyland"), FESTIVAL, FREE, ROW1),
                    ORGANISER: RuntimeError("503 refused")})
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn(ORGANISER, log)
        after = json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))
        self.assertEqual(after["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("k13")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Kino K13", "ses.fi", "list", "k13", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == p["accent"]), 1)

    def test_the_site_names_the_hosts_it_is_read_from(self):
        """The organiser page is on a host of its own, which the grouping has to see."""
        self.assertEqual(SITE["base"], "https://www.ses.fi")
        self.assertEqual(run.hosts_of(SITE), ("www.ses.fi", "kaupunginosat.fi"))


if __name__ == "__main__":
    unittest.main()
