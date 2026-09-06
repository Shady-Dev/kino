"""Cinema Orion: the ticket link a row carries is stored as an absolute URL.

The site published absolute `orion.kinola.ee` links until 2026-09-06 and now publishes
site-relative ones (`/checkout/{uuid}`). Nothing downstream resolves a bare path: the
client's `safeUrl` passes a scheme-less URL through, so the browser resolves it against
leffavuoro.fi and the reader gets a 404 instead of a box office. The fixture follows
cinemaorion.fi's own markup, two `table.kinola-day` blocks so the day loop runs more than
once, and mixes the link shapes one page really carries: a site-relative path, a
festival's own absolute box office, a protocol-relative host and a free-admission row
with no link at all.
"""
import unittest
from urllib.parse import urlsplit

import _ctx                                                # noqa: F401
import orion

TODAY = __import__("datetime").date(2026, 9, 4)
SITE = "https://cinemaorion.fi/"


def row(title, time_, date, link_html, price="8€"):
    return f"""
      <tr>
        <td class='date'>{date}</td>
        <td class='time'>{time_}</td>
        <td class='title'>{title}</td>
        <td class='price'>{price}</td>
        <td class='link'>{link_html}</td>
      </tr>"""


def link(href):
    return f"<a href='{href}'>Osta lippu</a>"


def page(*days):
    out = []
    for heading, rows in days:
        out.append(f"<h3><span>Torstai</span> {heading}</h3>")
        out.append(f"<table class='kinola-day'>{''.join(rows)}</table>")
    return "".join(out)


PAGE = page(
    ("04.09.", [
        row("Troija", "19:00", "04.09.", link("/checkout/f7def1e7")),
        row("Four Minus Three", "21:00", "04.09.",
            link("https://boxoffice.espoocine.fi/tickets/99")),
    ]),
    ("05.09.", [
        row("Dance Around the Fire", "17:30", "05.09.",
            link("//orion.kinola.ee/web/screening/9c2f")),
        row("Kerhon ilta", "20:00", "05.09.", "Vapaa pääsy", price="Vapaa pääsy"),
    ]),
)


class OrionTicketUrlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shows = orion.parse(PAGE, today=TODAY)
        cls.by_title = {s["title"]: s for s in cls.shows}

    def test_the_fixture_parses_both_days(self):
        """Guards the fixture itself: a page that stopped parsing would make every URL
        assertion below vacuous."""
        self.assertEqual(len(self.shows), 4)
        self.assertEqual(sorted({s["start"][:10] for s in self.shows}),
                         ["2026-09-04", "2026-09-05"])

    def test_a_site_relative_link_is_resolved_against_the_site(self):
        """The defect: `/checkout/{uuid}` stored bare reaches the client bare, and the
        browser resolves it against leffavuoro.fi, which answers 404."""
        self.assertEqual(self.by_title["Troija"]["url"],
                         "https://cinemaorion.fi/checkout/f7def1e7")

    def test_a_festival_box_office_link_is_left_alone(self):
        """Espoo Ciné and the other festivals sell on their own hosts. Resolving must not
        drag those onto cinemaorion.fi."""
        self.assertEqual(self.by_title["Four Minus Three"]["url"],
                         "https://boxoffice.espoocine.fi/tickets/99")

    def test_a_protocol_relative_link_gets_a_scheme(self):
        self.assertEqual(self.by_title["Dance Around the Fire"]["url"],
                         "https://orion.kinola.ee/web/screening/9c2f")

    def test_a_row_with_no_link_falls_back_to_the_programme_page(self):
        self.assertEqual(self.by_title["Kerhon ilta"]["url"], SITE)

    def test_every_stored_url_is_absolute_http(self):
        """The invariant that would have caught this on the day the site changed. A URL
        without a scheme and a host is a link to this origin, whatever it was meant to be."""
        for s in self.shows:
            with self.subTest(title=s["title"]):
                parts = urlsplit(s["url"])
                self.assertIn(parts.scheme, ("http", "https"))
                self.assertTrue(parts.netloc, f"no host in {s['url']!r}")


if __name__ == "__main__":
    unittest.main()
