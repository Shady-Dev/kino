"""Kuvakukko and Kino Manttu: two venues on one page, no year, a stale weekend.

The fixtures follow `kuvakukko.fi/ohjelmisto/kuvakukon-ja-kino-mantun-ohjelmisto/` as read
on 2026-09-15: an `<h2>` per cinema, then one `<p class="wp-block-paragraph">` per day
opening with a weekday and a date, holding `<br>`-separated `Klo 13:` rows.

Both cinemas are in every fixture, because the boundary between them is the only thing
stopping Nilsiä's weekend being filed under Kuopio, and nothing downstream would catch
that. Manttu's section is deliberately dated before the others: it publishes every other
weekend and its schedule is routinely already past, which is correct output and not
staleness to repair.
"""
import datetime
import unittest

import _ctx                                                # noqa: F401
import common
import kuvakukko

BASE = "https://www.kuvakukko.fi"
LIST = kuvakukko.LISTING
TODAY = datetime.date(2026, 9, 15)


def row(time_, title, href=None):
    if href is None:
        return f"Klo {time_}: {title}"
    return f'Klo {time_}: <a href="{href}" data-type="page" data-id="2698">{title}</a>'


def day(heading, *rows):
    return f'<p class="wp-block-paragraph">{heading}<br>' + "<br>".join(rows) + "</p>"


def info(text):
    """The same element type carries addresses and prices; it must not become a day."""
    return f'<p class="wp-block-paragraph">{text}</p>'


def page(kuopio_days=(), nilsia_days=(), extra=""):
    return ("<html><body><div class='entry__content'>"
            '<h2 class="wp-block-heading">Kino Kuvakukon esitysaikataulu</h2>'
            + "".join(kuopio_days) + info("Kino Kuvakukko Vuorikatu 27, 70100 KUOPIO") +
            '<h2 class="wp-block-heading">Nilsiän Kino Mantun esitysaikataulu</h2>'
            + "".join(nilsia_days)
            + info("<strong>Kino Mantun liput:</strong> 11 € / 9 €. Ei ennakkovarauksia.")
            # An info line that mentions a date mid-sentence. Anchoring the day pattern to
            # the start of the paragraph is what keeps this out; searching anywhere in it
            # would turn a closure notice into a day of screenings.
            + info("Teatteri on suljettu lauantai 20.6. Klo 18: alkaneet n&auml;yt&ouml;kset "
                   "siirtyv&auml;t syksyyn.")
            + extra + "</div></body></html>")


LISTING_PAGE = page(
    kuopio_days=[
        day("Tiistai 15.9.",
            row("13", "Hopeatähti-sarja: Laula minulle Arja",
                "https://isak.fi/hopeatahti-elokuvasarja/"),
            row("17.30", "Hetki ennen valoa", f"{BASE}/ohjelmisto/tulossa-hetki/"),
            row("19.30", "Presidentin kyyditys", f"{BASE}/ohjelmisto/tulossa-pk/")),
        day("Keskiviikko 16.9.",
            row("13", "Keltaiset kirjeet", f"{BASE}/ohjelmisto/blue-heron/")),
    ],
    # Manttu's weekend, already past on the 15th.
    nilsia_days=[
        day("Perjantai 11.9.",
            row("17.15", "Presidentin kyyditys", f"{BASE}/ohjelmisto/manttu-pk/"),
            row("19", "Hetki ennen valoa", f"{BASE}/ohjelmisto/manttu-hev/")),
        day("Lauantai 12.9.",
            row("13", "Marsupilami (dub)", f"{BASE}/ohjelmisto/manttu-mars/")),
    ],
)


class TwoVenuesTest(unittest.TestCase):
    def setUp(self):
        self.per = kuvakukko.parse(LISTING_PAGE, today=TODAY)

    def test_each_heading_owns_the_days_under_it(self):
        """The error this prevents: Nilsiä's weekend filed under Kuopio."""
        self.assertEqual(len(self.per["kk-kuopio"]), 4)
        self.assertEqual(len(self.per["kk-nilsia"]), 3)
        self.assertEqual({s["start"][:10] for s in self.per["kk-kuopio"]},
                         {"2026-09-15", "2026-09-16"})
        self.assertEqual({s["start"][:10] for s in self.per["kk-nilsia"]},
                         {"2026-09-11", "2026-09-12"})

    def test_each_show_names_its_own_venue_and_theatre(self):
        for s in self.per["kk-kuopio"]:
            self.assertEqual((s["venue"], s["theatre"]), ("kk-kuopio", "Kino Kuvakukko"))
        for s in self.per["kk-nilsia"]:
            self.assertEqual((s["venue"], s["theatre"]), ("kk-nilsia", "Kino Manttu"))

    def test_an_info_paragraph_is_not_a_day(self):
        """Addresses and price lists use the same element. They open with no weekday, so
        they never become screenings and no exclusion list is needed."""
        titles = [s["title"] for v in self.per.values() for s in v]
        self.assertNotIn("Kino Kuvakukko Vuorikatu 27, 70100 KUOPIO", titles)
        self.assertFalse([t for t in titles if "liput" in t.lower()])

    def test_a_closure_notice_naming_a_date_and_a_time_is_not_a_day(self):
        """"Teatteri on suljettu lauantai 20.6. Klo 18: ..." carries a weekday, a date and
        something shaped exactly like a screening row. The day pattern is anchored to the
        start of the paragraph for this reason: matching it anywhere in the text would
        publish a screening on a day the cinema said it was closed."""
        starts = {s["start"][:10] for v in self.per.values() for s in v}
        self.assertNotIn("2026-06-20", starts)
        self.assertEqual(starts, {"2026-09-11", "2026-09-12", "2026-09-15", "2026-09-16"})

    def test_the_time_is_read_both_ways_it_is_written(self):
        times = sorted(s["start"][11:16] for s in self.per["kk-kuopio"])
        self.assertIn("13:00", times)      # "Klo 13:"
        self.assertIn("17:30", times)      # "Klo 17.30:"

    def test_a_manttu_weekend_that_has_already_passed_stays_in_the_past(self):
        """It publishes every other weekend, so a past schedule is the normal state. The
        weekday places it; nothing shifts a year to make it look current."""
        self.assertEqual(sorted({s["start"][:10] for s in self.per["kk-nilsia"]}),
                         ["2026-09-11", "2026-09-12"])

    def test_the_title_is_published_verbatim_including_a_strand_prefix(self):
        """`run.py` splits the prefixes strands.EVENT_PREFIXES names, centrally. This
        adapter does not invent a split of its own."""
        self.assertIn("Hopeatähti-sarja: Laula minulle Arja",
                      [s["title"] for s in self.per["kk-kuopio"]])

    def test_an_external_link_sends_the_reader_to_the_programme_page(self):
        """The Hopeatähti row links to isak.fi, a third party. A showtime opens this
        cinema's own page instead."""
        by = {s["title"]: s for s in self.per["kk-kuopio"]}
        self.assertEqual(by["Hopeatähti-sarja: Laula minulle Arja"]["url"], LIST)
        self.assertTrue(by["Hetki ennen valoa"]["url"].startswith(BASE))

    def test_every_show_meets_the_contract(self):
        common.check_shows(self.per, "kuvakukko", {v["id"] for v in kuvakukko.VENUES})


class YearTest(unittest.TestCase):
    def _weekday_case(self, wd, want):
        """Parse a one-row page for `wd 15.9.`; `want` is the date, or None for a row the
        bound refuses, which leaves the page with no screening at all."""
        body = page(kuopio_days=[day(f"{wd} 15.9.", row("19", "A"))])
        if want is None:
            with self.assertRaises(common.EmptyProgramme, msg=wd):
                kuvakukko.parse(body, today=TODAY)
            return
        per = kuvakukko.parse(body, today=TODAY)
        self.assertEqual(per["kk-kuopio"][0]["start"][:10], want, wd)

    def test_a_weekday_that_would_place_a_row_a_year_out_is_refused(self):
        """15.9. is a Monday in 2025, a Tuesday in 2026 and a Wednesday in 2027. Read on
        2026-09-15 only the Tuesday is inside the plausibility bound; the other two are a
        year away, which is what a mistyped weekday produces."""
        self._weekday_case("Tiistai", "2026-09-15")
        for wd in ("Maanantai", "Keskiviikko"):
            self._weekday_case(wd, None)


    def test_a_weekday_no_candidate_year_can_satisfy_drops_the_day(self):
        per = kuvakukko.parse(page(kuopio_days=[day("Torstai 15.9.", row("19", "A")),
                                                day("Tiistai 15.9.", row("20", "B"))]),
                              today=TODAY)
        self.assertEqual([s["title"] for s in per["kk-kuopio"]], ["B"])

    def test_a_december_day_read_in_january_stays_in_the_past(self):
        per = kuvakukko.parse(page(kuopio_days=[day("Sunnuntai 28.12.", row("19", "A"))]),
                              today=datetime.date(2026, 1, 2))
        self.assertEqual(per["kk-kuopio"][0]["start"][:10], "2025-12-28")

    def test_a_january_day_read_in_december_rolls_forward(self):
        per = kuvakukko.parse(page(kuopio_days=[day("Tiistai 5.1.", row("19", "A"))]),
                              today=datetime.date(2026, 12, 28))
        self.assertEqual(per["kk-kuopio"][0]["start"][:10], "2027-01-05")


class EmptyAndBrokenTest(unittest.TestCase):
    def test_one_cinema_between_programmes_is_an_empty_list_not_a_failure(self):
        """Both schedules are on one page, so the read cannot have half-failed: Manttu
        with no days while Kuopio has them is positive evidence it is between
        programmes."""
        per = kuvakukko.parse(page(kuopio_days=[day("Tiistai 15.9.", row("19", "A"))]),
                              today=TODAY)
        self.assertEqual(len(per["kk-kuopio"]), 1)
        self.assertEqual(per["kk-nilsia"], [])

    def test_both_empty_is_an_empty_programme(self):
        with self.assertRaises(common.EmptyProgramme):
            kuvakukko.parse(page(), today=TODAY)

    def test_a_page_without_a_schedule_heading_is_a_failure(self):
        with self.assertRaises(RuntimeError) as cm:
            kuvakukko.parse("<html><body><p>Tervetuloa</p></body></html>", today=TODAY)
        self.assertNotIsInstance(cm.exception, common.EmptyProgramme)

    def test_a_repeated_row_is_published_once(self):
        r = row("19", "A", f"{BASE}/x/")
        per = kuvakukko.parse(page(kuopio_days=[day("Tiistai 15.9.", r, r)]), today=TODAY)
        self.assertEqual(len(per["kk-kuopio"]), 1)


class SiteTest(unittest.TestCase):
    def test_one_provider_two_venues_two_towns(self):
        site = kuvakukko.SITES[0]
        self.assertEqual(len(site["venues"]), 2)
        self.assertEqual(sorted(v["city"] for v in site["venues"]), ["Kuopio", "Nilsiä"])
        self.assertTrue(kuvakukko.EMPTY_VENUES_CONFIRMED)


if __name__ == "__main__":
    unittest.main()
