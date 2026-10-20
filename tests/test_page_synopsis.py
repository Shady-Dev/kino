"""A generated page falls back to Finnkino's own synopsis when films-extra has none.

The pages read films-extra.json by title only, while the app's sheet reads films.json by
Finnkino's film id first, so Mysteerinäytös, Operaatio Ave Maria and others had a
description in the app and none on 49 page cards (audit, 2026-09-27). Iso-Hannu's
"KÄTYRIT & MONSTERIT (suomeksi puhuttu)" has the TMDB id Finnkino's own pass trusted for
its "Kätyrit & Monsterit", and gets that text. Another cinema's text is never borrowed.
"""
import json
import pathlib
import re
import tempfile
import unittest
from datetime import date
from unittest import mock

import _ctx                                                # noqa: F401
import build_pages as bp

FILMS = {"HO1": {"s": {"fi": "Suomenkielinen kuvaus elokuvasta, jossa tapahtuu paljon.",
                       "en": "Mystery"}},
         "HO2": {"s": {"fi": "The hardest part of ending is starting again, they said."}},
         "HO3": {"s": {"fi": "Toinen suomenkielinen kuvaus, joka kertoo elokuvan juonesta."}}}
NATIVE = (FILMS, {77: ["HO3"]})


def finnkino(fid="HO1", title="Mysteerinäytös"):
    return {"eventId": fid, "title": title, "start": "2026-09-27T18:00:00+03:00",
            "url": "https://www.finnkino.fi/", "rating": "", "len": ""}


def other(title="KÄTYRIT (suomeksi puhuttu)", tmdb=77, eid="HO1"):
    return {**finnkino(eid, title), "provider": "isohannu", "tmdbId": tmdb}


def syn(shows, extra=None, lang="fi", native=NATIVE, seen=None):
    html = bp.film_block(shows[0]["title"], shows, extra or {}, {lang: {}}, lang, bp.L[lang],
                         False, set() if seen is None else seen, current_year=2026,
                         native=native)
    m = re.search(r'<p class="syn">(.*?)</p>', html, re.S)
    return m.group(1) if m else ""


class NativeSynopsisTest(unittest.TestCase):

    def test_a_finnkino_card_takes_its_own_film_s_text(self):
        self.assertIn("Suomenkielinen kuvaus", syn([finnkino()]))

    def test_films_extra_still_comes_first(self):
        extra = {"mysteerinäytös": {"s": {"fi": "Teksti films-extrasta."}}}
        self.assertEqual(syn([finnkino()], extra), "Teksti films-extrasta.")

    def test_another_cinema_reaches_it_through_a_trusted_tmdb_id(self):
        self.assertIn("Toinen suomenkielinen", syn([other()]))

    def test_another_cinema_s_event_id_is_not_a_finnkino_film_id(self):
        self.assertEqual(syn([other(tmdb=None)]), "")

    def test_a_slot_in_another_language_or_only_a_title_is_skipped(self):
        self.assertEqual(syn([finnkino("HO2", "LINKIN PARK")]), "")
        self.assertEqual(syn([finnkino()], lang="en"), "")

    def test_only_the_first_appearance_carries_it(self):
        seen = set()
        self.assertTrue(syn([finnkino()], seen=seen))
        self.assertEqual(syn([finnkino()], seen=seen), "")

    def test_without_the_files_nothing_changes(self):
        self.assertEqual(syn([finnkino()], native=None), "")


class NativeIndexTest(unittest.TestCase):
    """Only an id Finnkino's pass trusted maps a TMDB id to a Finnkino film."""

    def test_a_weak_id_or_a_film_not_in_films_json_maps_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "films.json").write_text(json.dumps({"films": {"HO1": {}, "HO2": {}}}))
            (d / "tmdb.json").write_text(json.dumps({"HO1": {"i": 5, "x": True},
                                                     "HO2": {"i": 6, "x": False},
                                                     "HO9": {"i": 7, "x": True}}))
            with mock.patch.object(bp, "DATA", d):
                self.assertEqual(bp.native_synopses()[1], {5: ["HO1"]})

    def test_missing_files_read_as_none(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(bp, "DATA", pathlib.Path(d)):
            self.assertEqual(bp.native_synopses(), ({}, {}))


def src(shows, extra=None, lang="fi", native=NATIVE, seen=None):
    out = set()
    bp.film_block(shows[0]["title"], shows, extra or {}, {lang: {}}, lang, bp.L[lang], False,
                  set() if seen is None else seen, current_year=2026, native=native,
                  syn_src=out)
    return out


class SynopsisCreditTest(unittest.TestCase):
    """The footer credited every synopsis to TMDB, also where the text was a cinema's own
    (review, 2026-10-20). films-extra lists in `ts` the slots TMDB filled; any other
    text came from a cinema, and Finnkino's films.json text is Finnkino's."""

    TMDB = {"mysteerinäytös": {"s": {"fi": "TMDB:n kuvaus elokuvasta."}, "ts": ["fi"]}}
    CINEMA = {"mysteerinäytös": {"s": {"fi": "Teatterin oma kuvaus.", "en": "TMDB's."},
                                 "ts": ["en"]}}

    def test_a_slot_tmdb_filled_is_credited_to_tmdb(self):
        self.assertEqual(src([finnkino()], self.TMDB), {"tmdb"})

    def test_a_slot_tmdb_did_not_fill_is_the_cinemas(self):
        self.assertEqual(src([finnkino()], self.CINEMA), {"cinema"})
        self.assertEqual(src([finnkino()], self.CINEMA, lang="en"), {"tmdb"})

    def test_finnkinos_own_text_is_a_cinemas(self):
        self.assertEqual(src([finnkino()]), {"cinema"})

    def test_a_card_that_prints_no_synopsis_credits_nothing(self):
        seen = set()
        self.assertEqual(src([finnkino()], self.TMDB, seen=seen), {"tmdb"})
        self.assertEqual(src([finnkino()], self.TMDB, seen=seen), set())
        self.assertEqual(src([finnkino()], native=None), set())

    def test_the_line_names_what_the_page_printed(self):
        t = bp.L["fi"]
        self.assertEqual(bp.sources_line(t, set()),
                         "Näytöstiedot: kyseisen teatterin oma ohjelmisto. Arvosanat ja "
                         "kuvaukset: TMDB. Henkilökohtainen harrastusprojekti, ei "
                         "sidoksissa teattereihin.")
        self.assertEqual(bp.sources_line(t, {"tmdb"}), bp.sources_line(t, set()))
        self.assertIn(t["credit_cinema"], bp.sources_line(t, {"cinema"}))
        self.assertIn(t["credit_both"], bp.sources_line(t, {"tmdb", "cinema"}))
        for lang, t in bp.L.items():
            lines = {bp.sources_line(t, s) for s in ({"tmdb"}, {"cinema"}, {"tmdb", "cinema"})}
            self.assertEqual(len(lines), 3, lang)
            self.assertFalse(any("{" in x for x in lines), lang)

    def test_the_page_footer_carries_the_line(self):
        today = date(2026, 9, 27)

        def row(title, eid):
            return {**finnkino(eid, title), "theatre": "Kino Testi"}

        days = {today.isoformat(): {("Mysteerinäytös", False): [row("Mysteerinäytös", "X1")],
                                    ("Toinen", False): [row("Toinen", "X2")]}}
        extra = {**self.TMDB, "toinen": {"s": {"fi": "Teatterin teksti."}}}

        def footer(extra):
            html = bp.page(
                lang="fi", paths={"fi": "/teatteri/x/", "sv": "/sv/teatteri/x/",
                                  "en": "/en/theatre/x/"},
                title="X", desc="d", h1="h", sub="s", intro="i", days=days, today=today,
                t=bp.L["fi"], extra=extra, gmap={}, city="Helsinki", with_venue=False,
                legend="", also="", og_image="/icon-512.png", app_href="/", area="x",
                chain_css="", kind="theatre")
            return re.search(r"<footer><div data-nosnippet>(.*?)</div>", html).group(1)

        self.assertIn(bp.L["fi"]["credit_both"], footer(extra))
        self.assertIn(bp.L["fi"]["credit_tmdb"], footer(self.TMDB))


if __name__ == "__main__":
    unittest.main()
