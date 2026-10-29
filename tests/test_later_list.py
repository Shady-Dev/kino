"""Tests for the later-screenings pilot on ten Finnish theatre pages (2026-10-29).

Only those pages change, and every listed screening shows the facts from its own row."""
import contextlib
import io
import pathlib
import re
import shutil
import tempfile
import unittest
from datetime import date

import _ctx                                                # noqa: F401
import build_pages as bp

D = date(2026, 10, 29)          # A Thursday. The window is 29.10.-1.11. and the list 2.11.-1.12.
T = bp.L["fi"]
APP = "/?area=v&lang=fi"


def show(start, title="Elokuva", **kw):
    return {"title": title, "start": start, "url": "https://example.fi/naytos", "aud": "",
            "method": "", "lang": "", "price": "", **kw}


class RangeTest(unittest.TestCase):
    def test_the_first_and_last_listed_days_are_d_plus_4_and_d_plus_33(self):
        shows = [show("2026-11-01T20:00:00+02:00", "Ikkunassa"),
                 show("2026-11-02T18:00:00+02:00", "Ensimmainen"),
                 show("2026-12-01T18:00:00+02:00", "Viimeinen"),
                 show("2026-12-02T18:00:00+02:00", "Ohi")]
        groups, beyond = bp.later_shows(shows, D)
        self.assertEqual([k[0] for k, _ in groups], ["Ensimmainen", "Viimeinen"])
        self.assertEqual(beyond, 1)

    def test_nothing_after_the_window_gives_no_section(self):
        groups, beyond = bp.later_shows([show("2026-10-30T18:00:00+02:00")], D)
        self.assertEqual((groups, beyond), ([], 0))
        self.assertEqual(bp.later_block(groups, beyond, D, T, "fi", APP), "")


class GroupingTest(unittest.TestCase):
    def test_titles_and_events_stay_apart_as_on_the_day_list(self):
        shows = [show("2026-11-03T16:00:00+02:00", "Unohdettu saari (suomeksi)", tmdbId=1),
                 show("2026-11-03T18:00:00+02:00", "Unohdettu saari", tmdbId=1),
                 show("2026-11-04T18:00:00+02:00", "Konsertti", nonFilm=True),
                 show("2026-11-05T18:00:00+02:00", "Konsertti")]
        keys = [k for k, _ in bp.later_shows(shows, D)[0]]
        self.assertEqual(keys, [("Unohdettu saari (suomeksi)", False),
                                ("Unohdettu saari", False),
                                ("Konsertti", True), ("Konsertti", False)])

    def test_order_is_first_start_then_title_and_screenings_by_start_then_room(self):
        shows = [show("2026-11-05T18:00:00+02:00", "B"),
                 show("2026-11-02T20:00:00+02:00", "B", aud="Sali 2"),
                 show("2026-11-02T20:00:00+02:00", "B", aud="Sali 1"),
                 show("2026-11-02T20:00:00+02:00", "A")]
        groups, _ = bp.later_shows(shows, D)
        self.assertEqual([k[0] for k, _ in groups], ["A", "B"])
        self.assertEqual([(s["start"][:10], s["aud"]) for s in groups[1][1]],
                         [("2026-11-02", "Sali 1"), ("2026-11-02", "Sali 2"),
                          ("2026-11-05", "")])


class LineTest(unittest.TestCase):
    def line(self, **kw):
        return bp.later_item(show("2026-11-03T19:00:00+02:00", **kw), T, "fi")

    def test_each_screening_keeps_its_own_facts(self):
        html = self.line(aud="Sali 1", method="Erikoisn\u00e4yt\u00f6s", lang="EN-A, FI-S",
                         price="13\u20ac")
        self.assertIn(">Ti 3.11. 19:00</a>", html)
        self.assertIn('<span class="lf">Sali 1, Erikoisn\u00e4yt\u00f6s, englanti, tekstitys: '
                      'suomi</span> <span class="price">13\xa0\u20ac</span>', html)

    def test_what_a_row_does_not_state_stays_unstated(self):
        html = self.line()
        self.assertNotIn('class="lf"', html)
        self.assertNotIn("\u20ac", html)

    def test_a_booking_state_and_a_two_d_tag_are_left_out(self):
        html = self.line(method="2D \u00b7 Loppuunmyyty \u00b7 Lapsille")
        self.assertIn("Lapsille", html)
        self.assertNotIn("2D", html)
        self.assertNotIn("Loppuunmyyty", html)

    def test_the_time_links_to_the_screenings_own_url_and_only_an_absolute_one(self):
        self.assertIn('href="https://example.fi/naytos" rel="nofollow noopener"', self.line())
        self.assertNotIn("<a ", self.line(url="/suhteellinen"))


class SectionTest(unittest.TestCase):
    def block(self, shows):
        groups, beyond = bp.later_shows(shows, D)
        return bp.later_block(groups, beyond, D, T, "fi", APP)

    def test_the_span_names_the_published_end_when_nothing_is_cut(self):
        html = self.block([show("2026-11-02T18:00:00+02:00"), show("2026-11-04T18:00:00+02:00")])
        self.assertIn("N\u00e4yt\u00f6kset 2.11.\u20134.11. Teatteri on julkaissut "
                      "n\u00e4yt\u00f6ksi\u00e4 4.11. asti.", html)
        self.assertNotIn("j\u00e4lkeen", html)

    def test_screenings_past_the_range_are_counted_and_linked_to_the_app(self):
        html = self.block([show("2026-11-02T18:00:00+02:00"),
                           show("2026-12-05T18:00:00+02:00"), show("2026-12-06T18:00:00+02:00")])
        self.assertIn("Lis\u00e4ksi 2 n\u00e4yt\u00f6st\u00e4 1.12. j\u00e4lkeen.", html)
        self.assertIn(f'<a href="{bp.esc(APP)}">{T["cta"]}</a>', html)
        self.assertNotIn("asti", html)

    def test_one_screening_past_the_range_reads_in_the_singular(self):
        html = self.block([show("2026-12-05T18:00:00+02:00")])
        self.assertIn("Lis\u00e4ksi yksi n\u00e4yt\u00f6s 1.12. j\u00e4lkeen.", html)
        self.assertNotIn("<h3>", html)

    def test_every_listed_screening_appears_once(self):
        shows = [show(f"2026-11-{d:02d}T18:00:00+02:00", t) for d in (2, 3, 9) for t in "AB"]
        self.assertEqual(self.block(shows).count("<li>"), 6)


class StackingTest(unittest.TestCase):
    def test_the_section_covers_the_last_sticky_day_heading(self):
        day = int(re.search(r"h2\.day\{[^}]*z-index:(\d+)", bp.CSS).group(1))
        rule = re.search(r"\.later\{([^}]*)\}", bp.PILOT_CSS).group(1)
        self.assertIn("position:relative", rule)
        self.assertIn("background:var(--bg)", rule)
        self.assertGreater(int(re.search(r"z-index:(\d+)", rule).group(1)), day)


class BuildTest(unittest.TestCase):
    """Builds the site twice from the same data and day, once without the pilot and once with it."""

    @classmethod
    def setUpClass(cls):
        real = _ctx.ROOT / "data"
        cls.today = bp.recorded_date()
        cls.saved = (bp.ROOT, bp.DATA, bp.PILOT_VENUES)
        cls.builds = {}
        cls.tmps = []
        for name, pilot in (("off", frozenset()), ("on", cls.saved[2])):
            tmp = tempfile.TemporaryDirectory()
            cls.tmps.append(tmp)
            root = pathlib.Path(tmp.name)
            (root / "data").mkdir()
            for p in real.glob("*.json"):
                shutil.copy2(p, root / "data" / p.name)
            bp.ROOT, bp.DATA, bp.PILOT_VENUES = root, root / "data", pilot
            with contextlib.redirect_stdout(io.StringIO()):
                bp.main(today=cls.today)
            cls.builds[name] = {str(p.relative_to(root)): p.read_text(encoding="utf-8")
                                for prefix in bp.PAGE_ROOTS
                                for p in (root / prefix).glob("*/index.html")}
            cls.builds[name]["sitemap.xml"] = (root / "sitemap.xml").read_text()
        bp.ROOT, bp.DATA, bp.PILOT_VENUES = cls.saved

    @classmethod
    def tearDownClass(cls):
        for tmp in cls.tmps:
            tmp.cleanup()

    def changed(self):
        off, on = self.builds["off"], self.builds["on"]
        self.assertEqual(off.keys(), on.keys())
        return {k for k in off if off[k] != on[k]}

    def test_only_finnish_theatre_pages_of_pilot_venues_change(self):
        changed = self.changed()
        self.assertTrue(changed, "no pilot page has a later screening in the committed data")
        for path in changed:
            self.assertTrue(path.startswith("teatteri/"), path)
            area = re.search(r'\?area=([^&"]+)&amp;lang=fi', self.builds["on"][path]).group(1)
            self.assertIn(area, bp.PILOT_VENUES, path)

    def test_a_pilot_page_differs_only_by_the_list_and_its_css(self):
        for path in self.changed():
            on = self.builds["on"][path]
            self.assertEqual(on.count(bp.PILOT_CSS), 1, path)
            self.assertEqual(on.count('<section class="later">'), 1, path)
            stripped = re.sub(r'<section class="later">.*?</section>', "",
                              on.replace(bp.PILOT_CSS, "", 1), count=1, flags=re.S)
            self.assertEqual(stripped, self.builds["off"][path], path)


if __name__ == "__main__":
    unittest.main()
