"""Kino Kirkkonummi: page-builder markup, published twice, with no year.

The fixtures follow `kinokirkkonummi.fi` as read on 2026-09-15: a film title in
`<p class="elementor-heading-title">` and its screenings in following
`<span class="elementor-icon-list-text">` items, with no semantic class marking either.

Everything the real page does that could corrupt the output is in the fixture: the whole
programme is emitted twice for desktop and mobile, a `tulossa` label sits above several
film titles, one film has only a release line and no screening, and the same list element
carries cast names, a director, a note, a street address and a phone number.
"""
import datetime
import unittest

import _ctx                                                # noqa: F401
import common
import kirkkonummi

BASE = "https://kinokirkkonummi.fi"
TODAY = datetime.date(2026, 9, 15)


def head(text):
    return (f'<div class="elementor-widget-container">'
            f'<p class="elementor-heading-title elementor-size-default">{text}</p></div>')


def item(text):
    return (f'<ul class="elementor-icon-list-items"><li class="elementor-icon-list-item">'
            f'<span class="elementor-icon-list-text">{text}</span></li></ul>')


def block():
    """One copy of the programme. The page emits this twice."""
    return "".join([
        head("tulossa"), head("Rakkautta ja virtahepoja"),
        item("Tulossa 25.9. alkaen"),
        item("Pihla Viitala, Aku Sipola, Jenni Vartiainen"),
        head("tulossa"), head("Myrskyn Ikkuna"),
        item("Andrew Scott, Brendan Fraser, Kerry Condon"),
        item("20.9. Sunnuntai klo18.00"),
        item("22.9. Tiistai klo19.00"),
        head("Päivien Lumo"),
        item("Ohjaus Karin Pennanen"),
        item("21.9. Maanantai klo19.00"),
        item("vain tämä näytös"),
        head("HETKI ENNEN VALOA"),
        item("Ohjaus Klaus Härö"),
        item("14.9. Maanantai klo19.00"),
        item("16.9. Keskiviikko klo19.00"),
    ])


def page(body=None, twice=True):
    inner = block() if body is None else body
    return ("<html><body>" + head("Elokuvateatteri") + inner + (inner if twice else "") +
            head("112 paikkaa") + item("Munkinmäentie 17") + item("041 7428871") +
            "</body></html>")


LISTING = page()


class ProgrammeTest(unittest.TestCase):
    def setUp(self):
        self.shows = kirkkonummi.parse(LISTING, today=TODAY)

    def test_the_duplicated_desktop_and_mobile_copies_publish_one_set(self):
        """The page emits the whole programme twice. Five screenings, not ten."""
        self.assertEqual(len(self.shows), 5)
        self.assertEqual(len({(s["eventId"], s["start"]) for s in self.shows}), 5)

    def test_each_screening_belongs_to_the_heading_above_it(self):
        by = {}
        for s in self.shows:
            by.setdefault(s["title"], []).append(s["start"][:10])
        self.assertEqual(sorted(by["Myrskyn Ikkuna"]), ["2026-09-20", "2026-09-22"])
        self.assertEqual(sorted(by["HETKI ENNEN VALOA"]), ["2026-09-14", "2026-09-16"])
        self.assertEqual(by["Päivien Lumo"], ["2026-09-21"])

    def test_a_release_line_with_no_time_is_not_a_screening(self):
        """"Tulossa 25.9. alkaen" names a day and a month and no time. The film has no
        other row, so it publishes nothing at all."""
        self.assertNotIn("Rakkautta ja virtahepoja", {s["title"] for s in self.shows})
        self.assertNotIn("2026-09-25", {s["start"][:10] for s in self.shows})

    def test_the_tulossa_label_never_becomes_a_film(self):
        """It sits above a title, in the same element the titles use."""
        self.assertNotIn("tulossa", {s["title"].lower() for s in self.shows})

    def test_cast_directors_notes_and_the_address_are_not_screenings(self):
        titles = {s["title"] for s in self.shows}
        for junk in ("Ohjaus Klaus Härö", "vain tämä näytös", "Munkinmäentie 17",
                     "041 7428871", "112 paikkaa", "Elokuvateatteri"):
            self.assertNotIn(junk, titles)

    def test_the_time_is_read_without_a_space_after_klo(self):
        self.assertEqual(sorted(s["start"][11:16] for s in self.shows)[0], "18:00")

    def test_no_auditorium_is_invented(self):
        """The page names two seat counts and never says which screening uses which."""
        self.assertEqual({s["aud"] for s in self.shows}, {""})

    def test_every_showtime_opens_the_programme_page(self):
        for s in self.shows:
            self.assertEqual(s["url"], BASE + "/")

    def test_every_show_meets_the_contract(self):
        common.check_shows({kirkkonummi.VENUE["id"]: self.shows}, "kirkkonummi",
                           {kirkkonummi.VENUE["id"]})


class YearTest(unittest.TestCase):
    def _weekday_case(self, wd, want):
        """Parse a one-row page for `15.9. wd`; `want` is the date, or None for a row the
        bound refuses, which leaves the page with no screening at all."""
        body = page(head("A") + item(f"15.9. {wd} klo19.00"), twice=False)
        if want is None:
            with self.assertRaises(common.EmptyProgramme, msg=wd):
                kirkkonummi.parse(body, today=TODAY)
            return
        out = kirkkonummi.parse(body, today=TODAY)
        self.assertEqual(out[0]["start"][:10], want, wd)

    def test_a_weekday_that_would_place_a_row_a_year_out_is_refused(self):
        """15.9. is a Monday in 2025, a Tuesday in 2026 and a Wednesday in 2027. Read on
        2026-09-15 only the Tuesday is inside the plausibility bound; the other two are a
        year away, which is what a mistyped weekday produces."""
        self._weekday_case("Tiistai", "2026-09-15")
        for wd in ("Maanantai", "Keskiviikko"):
            self._weekday_case(wd, None)


    def test_a_weekday_no_candidate_year_can_satisfy_is_skipped(self):
        out = kirkkonummi.parse(
            page(head("A") + item("15.9. Torstai klo19.00") +
                 item("15.9. Tiistai klo20.00"), twice=False), today=TODAY)
        self.assertEqual([s["start"][11:16] for s in out], ["20:00"])

    def test_a_december_row_read_in_january_stays_in_the_past(self):
        out = kirkkonummi.parse(page(head("A") + item("28.12. Sunnuntai klo19.00"),
                                     twice=False), today=datetime.date(2026, 1, 2))
        self.assertEqual(out[0]["start"][:10], "2025-12-28")

    def test_a_january_row_read_in_december_rolls_forward(self):
        out = kirkkonummi.parse(page(head("A") + item("5.1. Tiistai klo19.00"),
                                     twice=False), today=datetime.date(2026, 12, 28))
        self.assertEqual(out[0]["start"][:10], "2027-01-05")


class EmptyAndBrokenTest(unittest.TestCase):
    def test_films_with_no_screening_row_is_an_empty_programme(self):
        with self.assertRaises(common.EmptyProgramme):
            kirkkonummi.parse(page(head("Rakkautta ja virtahepoja") +
                                   item("Tulossa 25.9. alkaen"), twice=False), today=TODAY)

    def test_a_page_without_an_icon_list_is_a_failure(self):
        with self.assertRaises(RuntimeError) as cm:
            kirkkonummi.parse("<html><body><p>Tervetuloa</p></body></html>", today=TODAY)
        self.assertNotIsInstance(cm.exception, common.EmptyProgramme)

    def test_a_screening_before_any_heading_is_ignored(self):
        with self.assertRaises(common.EmptyProgramme):
            kirkkonummi.parse(page(item("20.9. Sunnuntai klo18.00"), twice=False),
                              today=TODAY)


class SiteTest(unittest.TestCase):
    def test_one_venue_in_kirkkonummi(self):
        self.assertEqual([v["city"] for v in kirkkonummi.SITES[0]["venues"]],
                         ["Kirkkonummi"])


if __name__ == "__main__":
    unittest.main()
