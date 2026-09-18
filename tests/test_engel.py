"""Kino Engel: the year a row does not print.

The rows read `La 29.08.` beside `klo 17:30` and carry no year, so the year is selected
from the weekday and then bounded by `common.resolve_year`. Before 2026-09-19 this module
kept a private loop that took the first candidate year inside a window rather than the
nearest one, and a row 46 or more days stale published as next year: `1.8.` read on
2026-09-19 came out as 2027-08-01.

Two rows minimum in every fixture, because the skip is a `continue` inside the loop.
"""
import contextlib
import datetime
import io
import unittest

import _ctx                                                # noqa: F401
import engel as E


TODAY = datetime.date(2026, 9, 19)          # a Saturday


def row(slug, when, clock, title):
    return (f'<a href="/elokuva/{slug}/"><span>{when}</span><span>klo {clock}</span>'
            f"<h3>{title}</h3>Osta liput</a>")


def parse(page, today=None):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        shows = E.parse(page, today or TODAY)
    return shows, out.getvalue()


class YearTest(unittest.TestCase):
    def test_the_weekday_places_a_row_that_prints_no_year(self):
        shows, _ = parse(row("autofiktio", "Su 20.09.", "17:30", "Autofiktio")
                         + row("troija", "Ke 30.09.", "19:00", "Troija"))
        self.assertEqual([s["start"] for s in shows],
                         ["2026-09-20T17:30:00+03:00", "2026-09-30T19:00:00+03:00"])

    def test_a_stale_row_is_skipped_and_the_current_one_keeps_its_date(self):
        """`La 1.8.` is 49 days behind: the private loop this replaced published it as
        2027-08-01, a year and a half out."""
        shows, log = parse(row("vanha", "La 01.08.", "18:00", "Vanha")
                           + row("autofiktio", "Su 20.09.", "17:30", "Autofiktio"))
        self.assertEqual([s["title"] for s in shows], ["Autofiktio"])
        self.assertIn("1 row(s) whose weekday matches no candidate year", log)
        self.assertIn("La 01.08.", log)

    def test_a_weekday_that_contradicts_its_own_date_is_skipped(self):
        """20 September 2026 is a Sunday. A row calling it Monday selects 2027, 366 days
        out, which the window refuses."""
        shows, log = parse(row("vaara", "Ma 20.09.", "18:00", "Väärä")
                           + row("autofiktio", "Su 20.09.", "17:30", "Autofiktio"))
        self.assertEqual([s["title"] for s in shows], ["Autofiktio"])
        self.assertIn("Ma 20.09.", log)

    def test_a_row_inside_the_window_behind_today_still_publishes(self):
        """The client hides a past screening; dropping one would lose a same-day row."""
        shows, _ = parse(row("eilen", "Pe 18.09.", "18:00", "Eilen")
                         + row("autofiktio", "Su 20.09.", "17:30", "Autofiktio"))
        self.assertEqual([s["start"][:10] for s in shows], ["2026-09-18", "2026-09-20"])

    def test_the_window_is_the_callers_and_this_one_is_measured(self):
        """The committed programme reached +9 to +15 days on 2026-09-19, so 120 ahead is
        headroom. The weekday is derived here rather than written down, because a calendar
        fact typed by hand is how three of these assertions were wrong first."""
        self.assertEqual(E.WINDOW, (30, 120))
        for days, published in ((100, True), (150, False)):
            with self.subTest(days=days):
                d = TODAY + datetime.timedelta(days=days)
                got = E._iso(d.day, d.month, 18, 0, TODAY, d.weekday())
                self.assertEqual(got[:10], d.isoformat() if published else "")


if __name__ == "__main__":
    unittest.main()
