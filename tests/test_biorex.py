"""BioRex: the admin-ajax fragment, and the guard against another venue's programme.

Venue selection is a cookie: POST the location, then ask admin-ajax, which answers
BioRex Verkatehdas's programme whenever the cookie did not take. The guard compared the
data layer's `showCinemaName` with the venue and fell back to the venue's own name when
the field was missing, so with the field gone and the cookie failing, Verkatehdas's
programme would publish under all twelve venues (audit A8, 2026-09-25).

The fixture is the item shape `test_show_contract.sample_biorex` uses, the data layer JSON
attribute-escaped as WordPress prints it.
"""
import contextlib
import html
import io
import json
import unittest
import urllib.parse

import _ctx                                                # noqa: F401
import biorex as B

TRIPLA, VERKA = B.VENUES[0], B.VENUES[2]


def item(show_id, when, cinema, place=True, field=True, title="Autofiktio", fmt="EN"):
    dl = {"movieId": 4711, "movieName": title, "showId": show_id, "showDateTime": when}
    if field:
        dl["showCinemaName"] = cinema
    dl = html.escape(json.dumps(dl), quote=True)
    return ('<div class="showtime-item ">'
            f'<div data-click-data-layer="{dl}"><a\nhref="https://biorex.fi/secure-redirect/{show_id}"\n'
            'class="x">Osta</a></div>'
            + (f'<div class="showtime-item__place__value">{cinema}, Sali 6</div>' if place else "")
            + '<span class="showtime-item__movie-rating">(K-16)</span>'
            f'<span class="showtime-item__format">{fmt}</span>'
            '<a class="showtime-item__movie-name" href="https://biorex.fi/elokuva/autofiktio/">'
            f'{title}</a></div>')


class Upstream:
    """biorex.fi as fetch_venue sees it: a location cookie that takes or not, and one
    admin-ajax answer per location, Verkatehdas's when the cookie did not take."""

    def __init__(self, posts, cookie=True):
        self.posts, self.cookie, self.location = posts, cookie, None

    def fetch(self, url, **kw):
        return b"<html></html>"

    def post(self, op, url, data):
        if url.endswith("/teatterin-valinta/"):
            self.location = data["location"] if self.cookie else None
            return b""
        pid = self.location or VERKA["providerId"]
        return json.dumps({"posts": self.posts.get(pid, "")}).encode()


class GuardTest(unittest.TestCase):
    VENUES = [TRIPLA, VERKA]

    def run_site(self, up):
        saved = (B.fetch, B._post, B.VENUES)
        B.fetch, B._post, B.VENUES = up.fetch, up.post, self.VENUES
        self.addCleanup(lambda: (setattr(B, "fetch", saved[0]), setattr(B, "_post", saved[1]),
                                 setattr(B, "VENUES", saved[2])))
        with contextlib.redirect_stdout(io.StringIO()):
            return B.fetch_site(sleep=0, with_meta=False)

    def posts(self, **kw):
        return {TRIPLA["providerId"]: item(1, "2026-09-26T18:00:00+03:00", TRIPLA["name"], **kw),
                VERKA["providerId"]: item(2, "2026-09-26T19:00:00+03:00", VERKA["name"], **kw)}

    def test_each_venue_publishes_its_own_programme(self):
        out = self.run_site(Upstream(self.posts()))
        self.assertEqual({k: [s["url"][-1] for s in v] for k, v in out.items()},
                         {TRIPLA["id"]: ["1"], VERKA["id"]: ["2"]})

    def test_a_failed_cookie_fails_the_site(self):
        with self.assertRaisesRegex(RuntimeError, "cookie"):
            self.run_site(Upstream(self.posts(), cookie=False))

    def test_the_place_line_still_catches_it_when_the_field_is_gone(self):
        """The case the old guard passed: no `showCinemaName`, so every show named the
        venue it was asked for."""
        with self.assertRaisesRegex(RuntimeError, "cookie"):
            self.run_site(Upstream(self.posts(field=False), cookie=False))

    def test_a_programme_naming_no_cinema_at_all_fails_the_site(self):
        with self.assertRaisesRegex(RuntimeError, "names no cinema"):
            self.run_site(Upstream(self.posts(field=False, place=False)))

    def test_without_the_field_the_place_line_verifies_the_right_venue(self):
        out = self.run_site(Upstream(self.posts(field=False)))
        self.assertEqual(sorted(out), sorted([TRIPLA["id"], VERKA["id"]]))
        self.assertEqual(out[TRIPLA["id"]][0]["theatre"], TRIPLA["name"])


if __name__ == "__main__":
    unittest.main()
