"""Bio Savoy, Mariehamn: two halls, ISO instants, and an http-only host.

The fixtures follow `biosavoy.ax` as read on 2026-09-15: one
`block-filmer-schema-block` per hall, each headed `Filmvisningar - Sal N`, holding rows
whose `<span class="date-display-single">` carries the full instant in its `content`
attribute.

Both halls are in the fixture because the hall comes from the block title and nothing on
the row, so a single-block fixture would never show it being lost. The `content` attribute
and the visible clock deliberately disagree in one row: the attribute is the one to read.
"""
import unittest

import _ctx                                                # noqa: F401
import biosavoy
import common

BASE = "http://www.biosavoy.ax"


def row(slug, title, content, shown=None):
    shown = shown if shown is not None else content[11:16]
    return ('<div class="views-row"><div class="views-field views-field-title">'
            f'<span class="field-content"><a href="/film/{slug}">'
            f'<span class="date-display-single" property="dc:date" '
            f'datatype="xsd:dateTime" content="{content}">{shown}</span>'
            f' - {title}</a></span></div></div>')


def block(hall, *rows, day="tis 15/09"):
    return (f'<section class="block block-views block-filmer-schema-block">'
            f'<div class="block-inner clearfix">'
            f'<h2 class="block-title">Filmvisningar - {hall}</h2>'
            f'<div class="block-content content"><div class="view view-filmer-schema">'
            f'<div class="view-content"><h3>{day}</h3>' + "".join(rows) +
            '</div></div></div></div></section>')


def page(*blocks, share_row=False):
    """The real page carries a "Dela" block with the same class as the two schedules. It
    holds no screening, so `share_row` puts one in it: only a block whose title actually
    reads "Filmvisningar - ..." may contribute screenings, and that has to be provable."""
    extra = row("shared", "SHARE WIDGET", "2026-09-15T12:00:00+03:00") if share_row else ""
    return ('<html><body><section class="block block-views block-filmer-schema-block">'
            f'<h2 class="block-title">Dela </h2><div>share buttons{extra}</div></section>'
            + "".join(blocks) + "</body></html>")


LISTING = page(
    block("Sal 1",
          row("dog-stars", "THE DOG STARS", "2026-09-15T18:00:00+03:00"),
          row("uprising", "THE UPRISING", "2026-09-15T20:15:00+03:00")),
    block("Sal 2",
          # The visible clock says something else; the attribute is authoritative.
          row("marsupilami", "MARSUPILAMI", "2026-09-15T18:15:00+03:00", shown="18.15"),
          row("spa-weekend", "SPA WEEKEND", "2026-09-16T20:20:00+03:00")),
)


class ScheduleTest(unittest.TestCase):
    def setUp(self):
        self.shows = biosavoy.parse(LISTING)

    def test_every_row_in_both_blocks_is_read(self):
        self.assertEqual(len(self.shows), 4)
        self.assertEqual(sorted({s["eventId"] for s in self.shows}),
                         ["dog-stars", "marsupilami", "spa-weekend", "uprising"])

    def test_the_hall_comes_from_the_block_title(self):
        by = {s["eventId"]: s["aud"] for s in self.shows}
        self.assertEqual(by["dog-stars"], "Sal 1")
        self.assertEqual(by["marsupilami"], "Sal 2")
        self.assertEqual(sorted({s["aud"] for s in self.shows}), ["Sal 1", "Sal 2"])

    def test_the_share_block_is_not_a_hall_even_when_it_holds_a_row(self):
        """It carries the same block class as the two schedules and only its title tells
        them apart, so a row inside it must not become a screening."""
        self.assertNotIn("Dela", {s["aud"] for s in self.shows})
        out = biosavoy.parse(page(block("Sal 1",
                                        row("a", "A", "2026-09-15T18:00:00+03:00")),
                                  share_row=True))
        self.assertEqual([s["eventId"] for s in out], ["a"])
        self.assertNotIn("SHARE WIDGET", {s["title"] for s in out})

    def test_the_hall_is_the_name_after_the_label_not_the_whole_title(self):
        self.assertEqual(sorted({s["aud"] for s in self.shows}), ["Sal 1", "Sal 2"])
        for s in self.shows:
            self.assertNotIn("Filmvisningar", s["aud"])

    def test_the_instant_comes_from_the_attribute_not_the_visible_clock(self):
        """The attribute carries the date, the clock and the offset. Nothing is inferred
        here: no year to resolve and no timezone to assume."""
        by = {s["eventId"]: s["start"] for s in self.shows}
        self.assertEqual(by["dog-stars"], "2026-09-15T18:00:00+03:00")
        self.assertEqual(by["marsupilami"], "2026-09-15T18:15:00+03:00")
        self.assertEqual(by["spa-weekend"], "2026-09-16T20:20:00+03:00")

    def test_a_row_without_an_offset_is_skipped(self):
        """The offset is what makes the instant unambiguous. A naive datetime would have
        to assume a zone, and this parser assumes none."""
        out = biosavoy.parse(page(block("Sal 1",
                                        row("a", "A", "2026-09-15T18:00:00"),
                                        row("b", "B", "2026-09-15T19:00:00+03:00"))))
        self.assertEqual([s["eventId"] for s in out], ["b"])

    def test_an_unparseable_instant_does_not_abort_the_page(self):
        out = biosavoy.parse(page(block("Sal 1",
                                        row("a", "A", "not-a-date"),
                                        row("b", "B", "2026-09-15T19:00:00+03:00"))))
        self.assertEqual([s["eventId"] for s in out], ["b"])

    def test_the_destination_is_http_because_the_host_has_no_https(self):
        """Port 443 is refused on both biosavoy.ax and www.biosavoy.ax. The verified
        destination is published rather than an https one the host cannot serve."""
        for s in self.shows:
            self.assertTrue(s["url"].startswith("http://www.biosavoy.ax/film/"), s["url"])
            self.assertNotIn("https://", s["url"])

    def test_the_title_is_the_text_after_the_dash(self):
        self.assertIn("THE DOG STARS", {s["title"] for s in self.shows})
        for s in self.shows:
            self.assertNotIn(" - ", s["title"])
            self.assertNotIn(":0", s["title"])

    def test_a_repeated_row_is_published_once(self):
        r = row("a", "A", "2026-09-15T18:00:00+03:00")
        self.assertEqual(len(biosavoy.parse(page(block("Sal 1", r, r)))), 1)

    def test_the_same_minute_in_two_halls_is_two_screenings(self):
        out = biosavoy.parse(page(
            block("Sal 1", row("a", "A", "2026-09-15T18:00:00+03:00")),
            block("Sal 2", row("a", "A", "2026-09-15T18:00:00+03:00"))))
        self.assertEqual(len(out), 2)
        self.assertEqual(sorted(s["aud"] for s in out), ["Sal 1", "Sal 2"])

    def test_every_show_meets_the_contract(self):
        common.check_shows({biosavoy.VENUE["id"]: self.shows}, "biosavoy",
                           {biosavoy.VENUE["id"]})


class EmptyAndBrokenTest(unittest.TestCase):
    def test_blocks_with_no_row_is_an_empty_programme(self):
        with self.assertRaises(common.EmptyProgramme):
            biosavoy.parse(page(block("Sal 1"), block("Sal 2")))

    def test_a_page_without_a_schedule_block_is_a_failure(self):
        with self.assertRaises(RuntimeError) as cm:
            biosavoy.parse("<html><body><p>Välkommen</p></body></html>")
        self.assertNotIsInstance(cm.exception, common.EmptyProgramme)


class SiteTest(unittest.TestCase):
    def test_one_venue_on_aland_keyed_under_its_official_name(self):
        """Åland's only official language is Swedish, and `CITY_SV` in index.html cannot
        gain an entry without editing a file this project keeps frozen. Keying the Finnish
        exonym would show it untranslated in the Swedish interface."""
        self.assertEqual([v["city"] for v in biosavoy.SITES[0]["venues"]], ["Mariehamn"])

    def test_the_base_is_http(self):
        self.assertTrue(biosavoy.BASE.startswith("http://"))


if __name__ == "__main__":
    unittest.main()
