"""Adapter regexes finish in linear time on hostile markup.

Spaces on both sides of a lazy group backtracked cubically: a few kilobytes of crafted
markup held one match for seconds to minutes, and `re` holds the GIL, so one such page
froze every site in the cloud pool (review of 2026-11-22, M1). Each input here took the
pre-fix pattern between 0.9 s and over 30 s on the machine it was measured on, and takes
the current one a few milliseconds. The limit is one second so that a slow runner does
not turn it red, and a cubic pattern still does.
"""
import datetime
import time
import unittest

import _ctx                                                # noqa: F401
import alatalo
import biorex
import engel
import enrich_tmdb
import etiketti
import heureka
import huvimylly
import kirkkonummi
import lieksa
import localhub
import marita
import pallas
import regina
import riviera

W = " "
LIMIT_S = 1.0

CASES = [
    ("localhub subtitles", lambda: localhub.language(
        {"descriptionLong": "<li><strong>Tekstitys:</strong>" + W * 700, "name": "x"},
        datetime.datetime(2026, 1, 1))),
    ("etiketti place", lambda: etiketti.PLACE_RE.search("<p>" + W * 1400)),
    ("riviera listing", lambda: riviera.parse(
        '<li class="movielist__item single-show"><span class="date">' + W * 2500 + "</li>")),
    ("biorex synopsis", lambda: biorex.SYN_RE.search(
        '<div class="movie-description__synopsis">' + W * 2500)),
    ("biorex rating", lambda: biorex.RATING_RE.search(
        'class="showtime-item__movie-rating">' + W * 2500)),
    ("lieksa price", lambda: lieksa.PRICE_RE.search("<h4>Liput:</h4>" + W * 2500)),
    ("heureka languages", lambda: heureka.LANGS_RE.search("Kielivaihtoehdot:" + W * 2000)),
    ("engel details", lambda: engel.DETAIL_RE.search("<label>" + W * 2500)),
    ("regina offer", lambda: regina.OFFER_RE.search('itemprop="price">' + W * 2500)),
    ("marita facts", lambda: marita.FACT_RE.findall('movies-info-title">' + W * 2500)),
    ("tmdb trailing visit", lambda: enrich_tmdb.TRAIL_EVENT.sub(" ", "Elokuva" + W * 2500 + "!")),
    ("tmdb bracket strand", lambda: enrich_tmdb.paren_strand("Elokuva (" + W * 600 + "!")),
    ("huvimylly rating", lambda: huvimylly._split_rating("Elokuva -k12" + W * 1500 + "!")),
    ("alatalo rating", lambda: alatalo._split_rating("Elokuva" + W * 2500 + "!")),
    ("pallas meta line", lambda: pallas.META_RE.search("1" + W * 2500)),
    ("kirkkonummi range", lambda: kirkkonummi.RANGE_RE.match("1 - 1.1." + W * 5000 + "!")),
]


class HostileMarkupTest(unittest.TestCase):
    def test_each_crafted_input_finishes_quickly(self):
        for name, run in CASES:
            with self.subTest(name):
                t = time.perf_counter()
                run()
                self.assertLess(time.perf_counter() - t, LIMIT_S)


class SameReadingTest(unittest.TestCase):
    """The shapes moved into Python read what the patterns used to read."""

    def test_biorex_rating_brackets(self):
        cases = {" (K-12) ": "K-12", "K-12": "K-12", "( K-7 )": "K-7", "(": "", ")": "",
                 "K))": "", "((K)": "(K", "": ""}
        for raw, want in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(biorex._rating_text(raw), want)

    def test_tmdb_bracket_strand(self):
        self.assertEqual(enrich_tmdb.paren_strand("Matka Piemonteen (ennakkonäytös!)"),
                         ("ennakkonäytös", 17))
        self.assertEqual(enrich_tmdb.paren_strand("X ( esiensi-ilta ) "), ("esiensi-ilta", 2))
        self.assertEqual(enrich_tmdb.paren_strand("X (a!!)"), ("a!", 2))
        self.assertEqual(enrich_tmdb.paren_strand("X ( ! )"), ("!", 2))
        self.assertIsNone(enrich_tmdb.paren_strand("X (   )"))
        self.assertIsNone(enrich_tmdb.paren_strand("X (" + "a" * 41 + ")"))
        self.assertEqual(enrich_tmdb.paren_strand("X (" + "a" * 40 + ")"), ("a" * 40, 2))

    def test_localhub_colon_outside_the_bold(self):
        start = datetime.datetime(2026, 1, 1)
        for desc in ("<li><strong>Tekstitys</strong>: suomenkielinen </li>",
                     "<li><strong>Tekstitys:</strong> suomenkielinen</li>",
                     "<li> <strong> Tekstitys : </strong>:suomenkielinen</li>"):
            with self.subTest(desc):
                self.assertEqual(localhub.language({"descriptionLong": desc, "name": ""}, start),
                                 "FI-S")


if __name__ == "__main__":
    unittest.main()
