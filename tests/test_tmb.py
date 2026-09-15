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


def page(*rows):
    return ('<html><body><h2>Valkokankaalla...</h2><div class="container"><div class="row">'
            '<div class="12u"><section class="box feature"><table width="100%">'
            + "".join(rows) +
            '</table></section></div></div></div></body></html>')


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
