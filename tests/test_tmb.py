"""TMB Cinema: one list view per venue, four cinemas that publish the same films.

The fixtures follow the `?lista=1` markup as read on 2026-09-15: a `<small>` carrying the
weekday, the full date with its year, the time and, on the two-screen sites only, a
`, sali N` tail; then the title in an `<h2><a href="?ohjelmisto=N">`; then the age limit
as an image filename in the next cell.

Two venues are built here, single-screen and two-screen, because the chain's own sites
differ that way and a fixture with only one would never exercise the auditorium branch.
The cases this file exists to pin are the ones that would silently corrupt the data: the
age image mapping, which is measured rather than assumed and must not grow a guess; the
weekday guard, which is the only thing that notices the template moving a field; and the
refusal to link to the booking action.
"""
import contextlib
import datetime
import io
import unittest

import _ctx                                                # noqa: F401
import common
import tmb

TOIJALA = next(s for s in tmb.SITES if s["provider"] == "kinotoijala")
MANIA = next(s for s in tmb.SITES if s["provider"] == "kinomania")


def row(wd, date, time_, fid, title, ika="3", sali=None):
    tail = f", sali&nbsp;{sali}" if sali else ""
    return (f'<tr><td style="padding: 0 20px;"><b><small>{wd}&nbsp;{date} klo&nbsp;{time_}'
            f'{tail}</small></b><h2 style="padding-left: 40px;">'
            f'<a  href="?ohjelmisto={fid}">{title}</a></h2></td>'
            f'<td style="padding: 10px;"><img title="Tutustu ikärajoihin hinnasto-sivulla."\n'
            f'\t\t\t\tsrc="/files/images/ikaraja_{ika}.png" alt="Ikäraja"></td>')


def page(*rows, hinnat=None):
    """The list view. `hinnat` adds the nav link to the site's price page, which the four
    sites number differently and which the adapter reads rather than writes down."""
    nav = f'<nav><a href="?hinnat={hinnat}">Hinnasto</a></nav>' if hinnat else ""
    return ('<html><head><title>Kino-Toijala :: elokuvat, 3D-elokuvat</title></head><body>'
            + nav + '<h2>Valkokankaalla...</h2><div class="container"><div class="row">'
            '<div class="12u"><section class="box feature"><table width="100%">'
            + "".join(rows) +
            '</table></section></div></div></div></body></html>')


def price_page(adult="14.45", senior="12.45", child="11.45", surcharge="+0.50 \u20ac",
               three_d=True):
    """The `?hinnat=N` page, as read on 2026-09-16. The 3D block sits immediately under the
    2D one at 2.50 more, which is what an unbounded search would publish."""
    tail = ('<h3>3D</h3><ul><li>Aikuinen <span>16.95 \u20ac</span></li>'
            '<li>El\u00e4kel\u00e4inen <span>15.95 \u20ac</span></li>'
            '<li>Lapsi <span>13.95 \u20ac</span></li></ul>' if three_d else "")
    rows = "".join(f'<li>{k} <span>{v} \u20ac</span></li>' for k, v in
                   (("Aikuinen", adult), ("El\u00e4kel\u00e4inen", senior),
                    ("Lapsi", child)) if v is not None)
    return ('<html><head><title>Kino-Toijala :: elokuvat, 3D-elokuvat</title></head><body>'
            '<h1>Hinnasto</h1><h2>Liput</h2><h3>2D</h3><ul>' + rows + "</ul>"
            + (f"<p>LA, SU ja arkipyh\u00e4t {surcharge}</p>" if surcharge else "")
            + tail + "<p>Hinnat sis. alv 13.5%</p></body></html>")


SINGLE = page(
    row("TI", "15.09.2026", "14:00", "842", "Hetki ennen valoa", ika="2"),
    row("TI", "15.09.2026", "18:00", "833", "Presidentin kyyditys", ika="3"),
    row("KE", "16.09.2026", "17:30", "842", "Hetki ennen valoa", ika="2"),
    # An opera event: ikaraja_1 is not a mapped rating, see the module docstring.
    row("LA", "03.10.2026", "16:00", "834", "Ooppera: Don Giovanni (Vicenza)", ika="1"),
)

TWO_SCREEN = page(
    row("TI", "15.09.2026", "14:00", "833", "Presidentin kyyditys", ika="3", sali="1"),
    row("TI", "15.09.2026", "14:30", "842", "Hetki ennen valoa", ika="2", sali="2"),
    row("TI", "15.09.2026", "18:00", "853", "Insidious: Out of the Further", ika="4", sali="2"),
    row("KE", "16.09.2026", "18:00", "833", "Presidentin kyyditys", ika="3", sali="1"),
)


class ListViewTest(unittest.TestCase):
    def setUp(self):
        self.single = tmb.parse(SINGLE, TOIJALA, TOIJALA["venues"][0])
        self.two = tmb.parse(TWO_SCREEN, MANIA, MANIA["venues"][0])

    def test_every_row_is_a_screening_with_its_own_year(self):
        self.assertEqual(len(self.single), 4)
        self.assertEqual(self.single[0]["start"], "2026-09-15T14:00:00+03:00")
        self.assertEqual(self.single[-1]["start"], "2026-10-03T16:00:00+03:00")

    def test_the_film_id_is_the_event_id_and_recurs_across_days(self):
        runs = [s for s in self.single if s["eventId"] == "842"]
        self.assertEqual(len(runs), 2)
        self.assertEqual({s["start"][:10] for s in runs}, {"2026-09-15", "2026-09-16"})

    def test_a_single_screen_site_publishes_no_auditorium(self):
        self.assertEqual({s["aud"] for s in self.single}, {""})

    def test_a_two_screen_site_keeps_each_row_in_its_own_hall(self):
        by = {(s["start"][11:16], s["aud"]) for s in self.two}
        self.assertIn(("14:00", "Sali 1"), by)
        self.assertIn(("14:30", "Sali 2"), by)
        self.assertEqual(sorted({s["aud"] for s in self.two}), ["Sali 1", "Sali 2"])

    def test_the_age_image_maps_only_where_it_was_measured(self):
        """2, 3 and 4 were checked against this repo's own ratings for films other
        providers carry. 1 appears only on opera events and is deliberately unmapped: a
        guessed classification is worse than none."""
        by_title = {s["title"]: s["rating"] for s in self.single}
        self.assertEqual(by_title["Hetki ennen valoa"], "K-7")
        self.assertEqual(by_title["Presidentin kyyditys"], "K-12")
        self.assertEqual(by_title["Ooppera: Don Giovanni (Vicenza)"], "")
        self.assertEqual({s["title"]: s["rating"] for s in self.two}
                         ["Insidious: Out of the Further"], "K-16")

    def test_an_unknown_age_image_yields_no_rating_rather_than_a_guess(self):
        out = tmb.parse(page(row("TI", "15.09.2026", "18:00", "1", "X", ika="9")),
                        TOIJALA, TOIJALA["venues"][0])
        self.assertEqual(out[0]["rating"], "")

    def test_the_showtime_links_to_the_public_film_page_never_the_booking_action(self):
        for s in self.single + self.two:
            self.assertRegex(s["url"], r"^https://[^/]+/\?ohjelmisto=\d+$")
            self.assertNotIn("varaa", s["url"])

    def test_each_site_files_its_shows_under_its_own_provider_and_venue(self):
        self.assertEqual({s["provider"] for s in self.single}, {"kinotoijala"})
        self.assertEqual({s["venue"] for s in self.single}, {"tmb-toijala"})
        self.assertEqual({s["provider"] for s in self.two}, {"kinomania"})
        self.assertEqual({s["venue"] for s in self.two}, {"tmb-mania"})

    def test_every_show_meets_the_contract(self):
        for shows, site in ((self.single, TOIJALA), (self.two, MANIA)):
            common.check_shows({site["venues"][0]["id"]: shows}, site["provider"],
                               {v["id"] for v in site["venues"]})

    def test_a_repeated_row_is_published_once(self):
        r = row("TI", "15.09.2026", "18:00", "833", "Presidentin kyyditys")
        self.assertEqual(len(tmb.parse(page(r, r), TOIJALA, TOIJALA["venues"][0])), 1)

    def test_the_same_minute_in_two_halls_is_two_screenings(self):
        """Two screens can start together; keying on time alone would drop one."""
        out = tmb.parse(page(row("TI", "15.09.2026", "18:00", "1", "A", sali="1"),
                             row("TI", "15.09.2026", "18:00", "2", "B", sali="2")),
                        MANIA, MANIA["venues"][0])
        self.assertEqual(len(out), 2)


class GuardTest(unittest.TestCase):
    def test_a_row_whose_weekday_contradicts_its_date_is_skipped_and_counted(self):
        """The only signal that the template moved a field: 15.09.2026 is a Tuesday, so a
        row calling it Saturday is not a screening this parser understands."""
        out = tmb.parse(page(row("LA", "15.09.2026", "18:00", "1", "wrong day"),
                             row("TI", "15.09.2026", "20:00", "2", "right day")),
                        TOIJALA, TOIJALA["venues"][0])
        self.assertEqual([s["title"] for s in out], ["right day"])

    def test_an_impossible_date_does_not_abort_the_page(self):
        out = tmb.parse(page(row("TI", "31.02.2026", "18:00", "1", "X"),
                             row("TI", "15.09.2026", "20:00", "2", "Y")),
                        TOIJALA, TOIJALA["venues"][0])
        self.assertEqual([s["title"] for s in out], ["Y"])

    def test_a_list_with_no_screening_is_an_empty_programme(self):
        with self.assertRaises(common.EmptyProgramme):
            tmb.parse(page(), TOIJALA, TOIJALA["venues"][0])

    def test_a_page_without_the_container_is_a_failure_not_an_empty_programme(self):
        with self.assertRaises(RuntimeError) as cm:
            tmb.parse("<html><body><p>Tervetuloa</p></body></html>",
                      TOIJALA, TOIJALA["venues"][0])
        self.assertNotIsInstance(cm.exception, common.EmptyProgramme)


class PriceTest(unittest.TestCase):
    """The price comes from the operator's own price page, one request per venue.

    The film page carries an exact per-screening price and is not read: that would be one
    request per film per venue. The price page is linked from the list view already in
    hand, so the whole cost is one more request. Read as a visitor 2026-09-16.
    """

    def test_the_two_d_block_is_what_is_read_and_not_the_three_d_one(self):
        """They sit one under the other and differ by 2.50. An unbounded search publishes
        the 3D tiers on every screening."""
        tiers, surcharge = tmb.price_tiers(price_page())
        self.assertEqual(tiers, [14.45, 12.45, 11.45])
        self.assertEqual(surcharge, 0.5)

    def test_the_title_naming_three_d_films_does_not_bound_the_block(self):
        """`<title>Kino-Toijala :: elokuvat, 3D-elokuvat</title>` comes before the table,
        so a search that stopped at the first `3D` on the page would find nothing."""
        self.assertIn("3D-elokuvat", price_page())
        self.assertEqual(tmb.price_tiers(price_page())[0], [14.45, 12.45, 11.45])

    def test_a_table_missing_a_tier_publishes_nothing_rather_than_a_guess(self):
        """Which tier a lone amount belongs to is not knowable from the amount."""
        self.assertEqual(tmb.price_tiers(price_page(child=None)), ([], 0.0))

    def test_a_page_that_is_not_the_price_page_publishes_nothing(self):
        self.assertEqual(tmb.price_tiers("<html><body><p>Tervetuloa</p></body></html>"),
                         ([], 0.0))

    def test_a_table_with_no_surcharge_line_is_still_a_table(self):
        tiers, surcharge = tmb.price_tiers(price_page(surcharge=""))
        self.assertEqual((tiers, surcharge), ([14.45, 12.45, 11.45], 0.0))

    def test_the_weekend_surcharge_is_applied_and_the_weekday_price_is_not(self):
        """The page states it and the film page confirms it: a Sunday row reads
        14.95 / 12.95 / 11.95 where the Wednesday beside it reads 14.45 / 12.45 / 11.45."""
        tiers, surcharge = tmb.price_tiers(price_page())
        for day, want in ((16, "14.45\u20ac / 12.45\u20ac / 11.45\u20ac"),      # Wednesday
                          (19, "14.95\u20ac / 12.95\u20ac / 11.95\u20ac"),      # Saturday
                          (20, "14.95\u20ac / 12.95\u20ac / 11.95\u20ac")):     # Sunday
            with self.subTest(day=day):
                when = datetime.datetime(2026, 9, day, 17, 30, tzinfo=tmb.FI)
                self.assertEqual(tmb.price_of(tiers, surcharge, when), want)

    def test_an_amount_with_no_cents_loses_its_zeros(self):
        """`14€ / 12€`, the shape julia.py already publishes and price_label reads."""
        tiers, surcharge = tmb.price_tiers(price_page(adult="14.00", senior="12.00",
                                                      child="11.00", surcharge=""))
        when = datetime.datetime(2026, 9, 16, 17, 30, tzinfo=tmb.FI)
        self.assertEqual(tmb.price_of(tiers, surcharge, when),
                         "14\u20ac / 12\u20ac / 11\u20ac")

    def test_no_table_means_no_price_rather_than_a_blank_amount(self):
        when = datetime.datetime(2026, 9, 16, 17, 30, tzinfo=tmb.FI)
        self.assertEqual(tmb.price_of([], 0.0, when), "")

    def test_the_price_page_link_is_read_from_the_list_view(self):
        """The four sites number it 2, 3, 4 and 1. A number copied from one onto another is
        how six Nexxo ticket links once shipped dead."""
        self.assertEqual(tmb.price_url(page(hinnat=3), "https://kinosampo.info"),
                         "https://kinosampo.info/?hinnat=3")
        self.assertEqual(tmb.price_url(page(hinnat=1), "https://elokuvat-elo.info"),
                         "https://elokuvat-elo.info/?hinnat=1")

    def test_a_list_view_linking_no_price_page_asks_for_none(self):
        self.assertEqual(tmb.price_url(page(), "https://toijalan-kino.info"), "")


class PriceThroughFetchTest(unittest.TestCase):
    """One list view, then one price page, and every screening carries what it says."""

    LIST = page(row("KE", "16.09.2026", "17:30", "842", "Hetki ennen valoa", ika="2"),
                row("LA", "19.09.2026", "14:00", "833", "Presidentin kyyditys", ika="3"),
                hinnat=2)

    def serve(self, pages):
        self.calls = []

        def get(url):
            self.calls.append(url)
            body = pages.get(url)
            if isinstance(body, Exception):
                raise body
            if body is None:
                raise RuntimeError(f"unexpected fetch {url}")
            return body
        real_get, real_sleep = tmb.get, tmb.time.sleep
        tmb.get = get
        tmb.time.sleep = lambda s: None
        self.addCleanup(lambda: setattr(tmb, "get", real_get))
        self.addCleanup(lambda: setattr(tmb.time, "sleep", real_sleep))

    def run_site(self, **over):
        pages = {"https://toijalan-kino.info/?lista=1": self.LIST,
                 "https://toijalan-kino.info/?hinnat=2": price_page()}
        pages.update(over)
        self.serve(pages)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            data = tmb.fetch_site(TOIJALA)
        return data["tmb-toijala"], out.getvalue() + err.getvalue()

    def test_one_extra_request_per_venue_and_every_screening_priced(self):
        shows, log = self.run_site()
        self.assertEqual(self.calls, ["https://toijalan-kino.info/?lista=1",
                                      "https://toijalan-kino.info/?hinnat=2"])
        self.assertEqual([s["price"] for s in shows],
                         ["14.45\u20ac / 12.45\u20ac / 11.45\u20ac",
                          "14.95\u20ac / 12.95\u20ac / 11.95\u20ac"])
        self.assertIn("2 priced", log)
        common.check_shows({"tmb-toijala": shows}, "kinotoijala", {"tmb-toijala"})

    def test_a_price_page_that_refuses_costs_the_prices_and_not_the_schedule(self):
        """A missing price is metadata; the schedule is why the venue exists."""
        shows, log = self.run_site(**{
            "https://toijalan-kino.info/?hinnat=2": RuntimeError("HTTP Error 503")})
        self.assertEqual([s["price"] for s in shows], ["", ""])
        self.assertEqual(len(shows), 2)
        self.assertIn("publishing without prices", log)
        self.assertIn("0 priced", log)
        common.check_shows({"tmb-toijala": shows}, "kinotoijala", {"tmb-toijala"})

    def test_a_list_view_with_no_price_link_asks_for_nothing_more(self):
        shows, log = self.run_site(**{
            "https://toijalan-kino.info/?lista=1": page(
                row("KE", "16.09.2026", "17:30", "842", "Hetki ennen valoa", ika="2"),
                row("TO", "17.09.2026", "18:00", "842", "Hetki ennen valoa", ika="2"))})
        self.assertEqual(self.calls, ["https://toijalan-kino.info/?lista=1"])
        self.assertEqual([s["price"] for s in shows], ["", ""])
        self.assertIn("links none", log)


class SitesTest(unittest.TestCase):
    def test_four_cinemas_in_four_towns_on_four_hosts(self):
        self.assertEqual(len(tmb.SITES), 4)
        self.assertEqual(sorted(v["city"] for s in tmb.SITES for v in s["venues"]),
                         ["Akaa", "Heinola", "Pieksämäki", "Valkeakoski"])
        self.assertEqual(len({s["base"] for s in tmb.SITES}), 4,
                         "four hosts: they are four cinemas, not one mirrored")
        self.assertEqual(len({v["id"] for s in tmb.SITES for v in s["venues"]}), 4)

    def test_each_site_names_exactly_one_venue(self):
        for s in tmb.SITES:
            self.assertEqual(len(s["venues"]), 1, s["provider"])


if __name__ == "__main__":
    unittest.main()
