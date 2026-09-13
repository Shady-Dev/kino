"""An eTiketti venue with no screening row is confirmed empty only on evidence (2026-09-13).

Cine Nikkilä's programme ended and the provider read "not updated" on its past shows,
because eTiketti never vouched for an empty venue and run.py kept the previous file on
every run. Now the adapter reports a rowless venue as an empty list when the listing's
theatre navigation names it and the read left nothing unexplained. Fixtures are Cine's
shape in the Kotka template: the town is the place line and the cinema is the room.
"""
import datetime
import importlib
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import common                                              # noqa: F401


def load():
    return importlib.import_module("etiketti")


def site():
    return next(s for s in load().SITES if s["provider"] == "cine")


NAV = ('<div class="footer-nav"><ul><li><a href="/teatterit">Teatterit</a><ul>'
       '<li><a href="/teatterit/mantsala">Cine Mäntsälä</a></li>'
       '<li><a href="/teatterit/keuda-talo">Cine Keuda-Talo</a></li>'
       '<li><a href="/teatterit/nikkila">Cine Nikkilä</a></li>'
       '<li><a href="/teatterit/kiertue">Kiertuenäytökset</a></li></ul></li></ul></div>')
NAV_WITHOUT_NIKKILA = NAV.replace('<li><a href="/teatterit/nikkila">Cine Nikkilä</a></li>', "")
PROSE = '<ul><li><a href="/esitysjaksot">Esitysjaksot Keravalla ja Nikkilässä</a></li></ul>'
HIDDEN = ('<div class="no-results" id="no-results" style="display: none;">'
          "<p>Ei näytöksiä valitsemallasi päivämäärällä.</p></div>")


def listing(paths, nav=NAV):
    cards = "".join(f'<div class="item kerava date-17.9.2026 name-x"><a href="{p}">x</a></div>'
                    for p in paths)
    return f'<main><div class="screenings movie-list">{cards}</div>{HIDDEN}</main>{PROSE}{nav}'


def item(day, hhmm, place, room, sid):
    return (f'<div class="item kerava date-{day}.9.2026"> <div> <p> <strong><span>KE {day}.9. klo {hhmm}'
            f"</span></strong> </p> <p> {place} | {room}<br /> Lippu 12,00&euro;<br /> "
            f'Vapaat paikat 40/120 </p> </div> <div> <a class="button-screening" href="/salikartta?id={sid}">'
            " Osta tai varaa </a> </div> </div>")


def film(*items):
    return ("<main><h1>Hetki ennen valoa</h1><h2>Näytökset</h2>"
            f'<div class="screenings">{HIDDEN}{"".join(items)}</div></main>')


KEUDA_FILM = film(item(17, "18.00", "KERAVA", "CINE KEUDA-TALO", 901),
                  item(18, "18.00", "KERAVA", "CINE KEUDA-TALO", 902))
MANTSALA_FILM = film(item(17, "19.00", "MÄNTSÄLÄ", "CINE MÄNTSÄLÄ", 903))


def stub_get(mapping):
    def get(url, tries=3):
        for suffix, page in mapping.items():
            if url.endswith(suffix):
                if isinstance(page, Exception):
                    raise page
                return page
        raise AssertionError(f"unexpected fetch: {url}")
    return get


class Stubbed(unittest.TestCase):
    def fetch(self, mapping):
        e = load()
        real = e.get
        e.get = stub_get(mapping)
        self.addCleanup(lambda: setattr(e, "get", real))
        return e.fetch_site(site(), sleep=0)


class ConfirmedEmptyTest(Stubbed):

    def test_the_module_vouches_for_the_venues_it_returns_empty(self):
        self.assertTrue(load().EMPTY_VENUES_CONFIRMED)

    def test_a_rowless_venue_named_by_the_navigation_comes_back_empty(self):
        out = self.fetch({"/elokuvat/ohjelmistossa": listing(["/elokuvat/13/hetki"]),
                          "/elokuvat/13/hetki": KEUDA_FILM})
        self.assertEqual(sorted(out), ["cine-keuda", "cine-nikkila"])
        self.assertEqual(out["cine-nikkila"], [])
        self.assertEqual([s["start"] for s in out["cine-keuda"]],
                         ["2026-09-17T18:00:00+03:00", "2026-09-18T18:00:00+03:00"])
        self.assertEqual(out["cine-keuda"][0]["theatre"], "Cine Keuda-Talo")

    def test_a_film_page_that_failed_to_fetch_leaves_the_venue_unconfirmed(self):
        out = self.fetch({"/elokuvat/ohjelmistossa": listing(["/elokuvat/13/hetki", "/elokuvat/21/myrsky"]),
                          "/elokuvat/13/hetki": KEUDA_FILM,
                          "/elokuvat/21/myrsky": RuntimeError("HTTP 503")})
        self.assertEqual(sorted(out), ["cine-keuda"], "Keuda keeps its rows, Nikkilä is not vouched for")
        self.assertEqual(len(out["cine-keuda"]), 2)

    def test_a_row_for_a_place_nobody_registered_leaves_the_venue_unconfirmed(self):
        """A renamed venue looks exactly like an unregistered place."""
        out = self.fetch({"/elokuvat/ohjelmistossa": listing(["/elokuvat/13/hetki", "/elokuvat/2/prima"]),
                          "/elokuvat/13/hetki": KEUDA_FILM,
                          "/elokuvat/2/prima": MANTSALA_FILM})
        self.assertEqual(sorted(out), ["cine-keuda"])

    def test_a_venue_the_navigation_does_not_name_is_not_identified(self):
        out = self.fetch({"/elokuvat/ohjelmistossa": listing(["/elokuvat/13/hetki"], nav=NAV_WITHOUT_NIKKILA),
                          "/elokuvat/13/hetki": KEUDA_FILM})
        self.assertEqual(sorted(out), ["cine-keuda"])

    def test_prose_naming_the_town_identifies_nothing(self):
        e = load()
        self.assertEqual(e.identified_venues(PROSE + NAV_WITHOUT_NIKKILA, site()), {"cine-keuda"})
        self.assertEqual(e.identified_venues(PROSE, site()), set())
        self.assertEqual(e.identified_venues(NAV, site()), {"cine-keuda", "cine-nikkila"})


class RunSiteTest(Stubbed):
    """What run.py writes for the two venues, from a previous Nikkilä file with past shows."""

    PREV = {"generated": "2026-09-13T11:10:39+00:00", "dates": ["2026-09-13"], "horizon": "2026-09-13",
            "shows": [{"title": "Hetki ennen valoa", "start": "2026-09-13T15:00:00+03:00"},
                      {"title": "Presidentin kyyditys", "start": "2026-09-13T16:45:00+03:00"}]}
    NOW = "2026-09-13T20:10:00+00:00"

    def setUp(self):
        import run
        self.run = run
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        saved = run.OUT
        run.OUT = pathlib.Path(tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", saved))
        (run.OUT / "area-cine-nikkila.json").write_text(json.dumps(self.PREV), encoding="utf-8")

    def run_site(self, mapping):
        e = load()
        real = e.get
        e.get = stub_get(mapping)
        self.addCleanup(lambda: setattr(e, "get", real))
        return self.run.run_site(e, site(), self.NOW)

    def read(self, name):
        return json.loads((self.run.OUT / name).read_text(encoding="utf-8"))

    def test_a_confirmed_empty_nikkila_gets_a_fresh_empty_file_and_the_provider_is_fresh(self):
        live, total, stale, unverified, pending = self.run_site(
            {"/elokuvat/ohjelmistossa": listing(["/elokuvat/13/hetki"]), "/elokuvat/13/hetki": KEUDA_FILM})
        self.assertEqual((live, total, stale, unverified, pending), (1, 2, [], [], ["cine-nikkila"]))
        nik = self.read("area-cine-nikkila.json")
        self.assertEqual((nik["generated"], nik["shows"], nik["dates"]), (self.NOW, [], []))
        keuda = self.read("area-cine-keuda.json")
        self.assertEqual(len(keuda["shows"]), 2)
        prov = self.read("venues-cine.json")
        self.assertEqual((prov["status"], prov["oldest"], prov["pending"]), ("ok", self.NOW, ["cine-nikkila"]))

    def test_an_uncertain_read_keeps_the_previous_file_and_the_old_stamp(self):
        """The keep-previous branch never advances the stamp, so without confirmation
        the provider stays "not updated" for as long as the venue has no row."""
        live, total, stale, unverified, pending = self.run_site(
            {"/elokuvat/ohjelmistossa": listing(["/elokuvat/13/hetki", "/elokuvat/21/myrsky"]),
             "/elokuvat/13/hetki": KEUDA_FILM, "/elokuvat/21/myrsky": RuntimeError("HTTP 503")})
        self.assertEqual((stale, pending), (["cine-nikkila"], []))
        self.assertEqual(self.read("area-cine-nikkila.json"), self.PREV)
        prov = self.read("venues-cine.json")
        self.assertEqual((prov["status"], prov["oldest"]), ("partial", self.PREV["generated"]))


if __name__ == "__main__":
    unittest.main()
