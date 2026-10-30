"""Bio-Salo's Nexxo tenant: two cinemas, a request only it sends, and no banner images.

biosalo.fi serves Bio-Salo (Salo) on locationid 1 and Bio Stara (Paimio) on 2, and plugin
25.051 answers {"shows": []} unless `movieid` is sent (issue #19, read 2026-10-21). The
maintainer scoped `movieid=0` to this tenant: every other Nexxo site's request has to stay
byte for byte what it was. The tenant publishes no banner image, so a poster comes only
from a trusted TMDB match.
"""
import unittest
import urllib.parse

import _ctx                                                # noqa: F401
import nexxo
import registry
from test_nexxo_rooms import row

PATH = "/wp-content/plugins/nexxo-scope/public_api.php?"
SALO = next(s for s in nexxo.SITES if s["provider"] == "biosalo")
STARA = next(s for s in nexxo.SITES if s["provider"] == "biostara")


def before(site, loc, days):
    """The request every Nexxo site sent before this tenant was added."""
    return site["base"] + PATH + urllib.parse.urlencode(
        {"action": "exportdailyshows", "locationid": loc, "days": days, "lang": "fi",
         "upcoming": "0"})


class RequestTest(unittest.TestCase):

    def test_every_other_site_sends_the_request_it_always_sent(self):
        others = [s for s in nexxo.SITES if s["provider"] not in ("biosalo", "biostara")]
        self.assertGreaterEqual(len(others), 7)
        for s in others:
            for v in s["venues"]:
                with self.subTest(site=s["provider"], venue=v["id"]):
                    days = s.get("days", 21)
                    self.assertEqual(nexxo.api_url(s, v["locationid"], days),
                                     before(s, v["locationid"], days))

    def test_the_bio_salo_tenant_adds_movieid_zero(self):
        for s in (SALO, STARA):
            loc = s["venues"][0]["locationid"]
            with self.subTest(site=s["provider"]):
                self.assertEqual(nexxo.api_url(s, loc, 21), before(s, loc, 21) + "&movieid=0")

    def test_fetch_site_asks_each_site_with_its_own_request(self):
        asked = []

        def fetch(url, **kw):
            asked.append(url)
            return b'{"shows": {"2026-10-24": [{"movieId": "9", "movieTitle": "Film", ' \
                   b'"startDate": "2026-10-24", "startTime": "2026-10-24 18:00:00"}]}}'

        saved = nexxo.fetch
        nexxo.fetch = fetch
        try:
            nexxo.fetch_site(STARA, sleep=0)
            nexxo.fetch_site(nexxo.SITES[0], sleep=0)
        finally:
            nexxo.fetch = saved
        self.assertEqual(asked[0], before(STARA, "2", 21) + "&movieid=0")
        self.assertNotIn("movieid", "".join(asked[1:]))
        self.assertEqual(len(asked), 1 + len(nexxo.SITES[0]["venues"]))


class TenantTest(unittest.TestCase):

    def payload(self):
        return {"shows": {"2026-10-24": [
            dict(row(1, "Bio-Salo 1", "Film A", "2026-10-24 18:00:00"),
                 ageLimit="7/4", posterurl="a.jpg"),
            dict(row(7, "Bio-Salo 3", "Film B", "2026-10-24 20:30:00"),
                 ageLimit="16", posterurl="b.jpg"),
        ]}}

    def test_both_cinemas_are_one_tenant_read_from_biosalo_fi(self):
        self.assertEqual({s["base"] for s in (SALO, STARA)}, {"https://biosalo.fi"})
        self.assertEqual([(s["venues"][0]["locationid"], s["venues"][0]["city"])
                          for s in (SALO, STARA)], [("1", "Salo"), ("2", "Paimio")])

    def test_a_showtime_links_to_its_own_cinemas_site(self):
        for s, want in ((SALO, "https://biosalo.fi/?location=1"),
                        (STARA, "https://biostara.fi/?location=2")):
            with self.subTest(site=s["provider"]):
                shows = nexxo.parse(self.payload(), s, s["venues"][0])
                self.assertEqual({x["url"] for x in shows}, {want})

    def test_no_banner_image_is_published(self):
        shows = nexxo.parse(self.payload(), SALO, SALO["venues"][0])
        self.assertEqual([x["img"] for x in shows], ["", ""])
        other = dict(SALO, banners=True)
        self.assertTrue(all(x["img"] for x in nexxo.parse(self.payload(), other,
                                                           other["venues"][0])))

    def test_the_rows_carry_rating_room_and_cinema(self):
        shows = nexxo.parse(self.payload(), SALO, SALO["venues"][0])
        self.assertEqual([(x["title"], x["rating"], x["aud"], x["theatre"]) for x in shows],
                         [("Film A", "K-7", "Bio-Salo 1", "Bio-Salo"),
                          ("Film B", "K-16", "Bio-Salo 3", "Bio-Salo")])


class RegistryTest(unittest.TestCase):

    def test_two_providers_credit_the_host_they_are_read_from(self):
        got = {p["id"]: p for p in registry.PROVIDERS if p["id"] in ("biosalo", "biostara")}
        self.assertEqual(sorted(got), ["biosalo", "biostara"])
        for p in got.values():
            with self.subTest(provider=p["id"]):
                self.assertEqual((p["host"], p["module"], p["book"], p["where"]),
                                 ("biosalo.fi", "nexxo", "reserve", "cloud"))
        self.assertNotEqual(got["biosalo"]["accent"], got["biostara"]["accent"])


if __name__ == "__main__":
    unittest.main()
