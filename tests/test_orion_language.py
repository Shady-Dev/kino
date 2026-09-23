"""Cinema Orion's language, read off the film page each row links to (2026-09-23).

The front-page table names no language; each film page has `Kieli:` and `Tekstitys:`
rows in lower-case Finnish names. The value is the film's, so it goes on every screening
of that film only when nothing suggests two versions: the rows agree on the title and no
note names a version. Reads go through prices.enrich's cache and cap, one per film.
Probe: docs/research/screening-language-sources.md.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import _ctx                                                # noqa: F401
import orion
import prices
from test_orion import TODAY, link, page, row

NOW = datetime.datetime(2026, 9, 4, 12, 0, tzinfo=datetime.timezone.utc)


def film(slug, title, blurb=""):
    """A title cell in the site's linked shape."""
    return (f"<a href='/elokuvat/{slug}/' title =\"{title}\"> {title} "
            f"<span class=\"descrption\">{blurb}<span> </a>")


def film_page(kieli=None, tekstitys=None):
    out = "<table>"
    for label, v in (("Kieli:", kieli), ("Tekstitys:", tekstitys)):
        if v is not None:
            out += f"<tr> <td id='field_x' class='dt'>{label}</td> <td class='dd'>{v}</td> </tr>"
    return out + "</table>"


class PageLanguageTest(unittest.TestCase):
    def test_the_shapes_read_on_the_day(self):
        cases = {("espanja", "suomi, ruotsi"): "ES-A, FI-S, SV-S",
                 ("englanti, portugali, ranska, japani", "suomi"): "EN-A, PT-A, FR-A, JA-A, FI-S",
                 ("suomi", "ruotsi"): "FI-A, SV-S"}
        for (k, t), want in cases.items():
            with self.subTest(kieli=k):
                self.assertEqual(orion.page_language(film_page(k, t)), want)

    def test_a_language_no_table_knows_leaves_that_row_empty(self):
        """The Secret Reading Club of Kabul: "dari, paštu, englanti"."""
        self.assertEqual(orion.page_language(film_page("dari, paštu, englanti", "suomi, ruotsi")),
                         "FI-S, SV-S")

    def test_a_page_without_the_rows_says_nothing(self):
        self.assertEqual(orion.page_language("<html></html>"), "")
        self.assertEqual(orion.page_language(film_page("suomi")), "FI-A")


class FilmLanguageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = pathlib.Path(self.tmp.name) / "film-lang-orion.json"

    def run_it(self, rows, pages, fail=(), limit=None):
        shows = orion.parse(page(("04.09.", rows)), today=TODAY)
        gets = []

        def fake(url, headers):
            gets.append(url)
            slug = url.rstrip("/").rsplit("/", 1)[1]
            if slug in fail:
                raise OSError("boom")
            return pages[slug]

        with contextlib.redirect_stdout(io.StringIO()) as out, \
             mock.patch.object(prices.time, "sleep"):
            st = orion.film_language(shows, path=self.path, now=NOW, sleep=0, limit=limit,
                                     fetch_fn=fake)
        return shows, gets, st, out.getvalue()

    def test_every_screening_of_a_film_gets_its_page_s_language_from_one_read(self):
        shows, gets, st, _ = self.run_it(
            [row(film("autofiktio", "Autofiktio"), "17:00", "04.09.", link("/checkout/a")),
             row(film("autofiktio", "Autofiktio"), "19:00", "04.09.", link("/checkout/b")),
             row(film("memoria", "Memoria"), "21:00", "04.09.", link("/checkout/c"))],
            {"autofiktio": film_page("espanja", "suomi, ruotsi"),
             "memoria": film_page("englanti, espanja", "suomi")})
        self.assertEqual([s["lang"] for s in shows],
                         ["ES-A, FI-S, SV-S", "ES-A, FI-S, SV-S", "EN-A, ES-A, FI-S"])
        self.assertEqual(gets, [orion.URL + "elokuvat/autofiktio/", orion.URL + "elokuvat/memoria/"])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["autofiktio"]["fields"],
                         {"lang": "ES-A, FI-S, SV-S"})

    def test_a_film_that_may_have_two_versions_is_not_asked(self):
        shows, gets, st, out = self.run_it(
            [row(film("kojootti", "Kojootti vs ACME"), "17:00", "04.09.", link("/checkout/a")),
             row(film("kojootti", "Kojootti vs ACME (Puhumme suomea!)"), "19:00", "04.09.",
                 link("/checkout/b")),
             row(film("troija", "Troija", "Dubattu versio."), "21:00", "04.09.",
                 link("/checkout/c"))],
            {"kojootti": film_page("englanti", "suomi"), "troija": film_page("englanti", "suomi")})
        self.assertEqual((gets, [s["lang"] for s in shows], st["unclear"]), ([], ["", "", ""], 2))
        self.assertIn("2 left out as possibly more than one version", out)

    def test_two_titles_on_one_film_page_settle_nothing_without_a_version_word(self):
        shows, gets, st, _ = self.run_it(
            [row(film("troija", "Troija"), "17:00", "04.09.", link("/checkout/a")),
             row(film("troija", "Troija (35 mm)"), "19:00", "04.09.", link("/checkout/b"))],
            {"troija": film_page("englanti", "suomi")})
        self.assertEqual((gets, [s["lang"] for s in shows], st["unclear"]), ([], ["", ""], 1))

    def test_a_row_s_own_language_is_kept(self):
        shows = orion.parse(page(("04.09.", [row(film("memoria", "Memoria"), "21:00", "04.09.",
                                                  link("/checkout/c"))])), today=TODAY)
        shows[0]["lang"] = "SV-A"
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(prices.time, "sleep"):
            orion.film_language(shows, path=self.path, now=NOW, sleep=0,
                                fetch_fn=lambda u, h: film_page("englanti"))
        self.assertEqual(shows[0]["lang"], "SV-A")

    def test_a_failed_page_leaves_its_screenings_as_they_were(self):
        shows, _, st, _ = self.run_it(
            [row(film("memoria", "Memoria"), "21:00", "04.09.", link("/checkout/c"))],
            {}, fail=("memoria",))
        self.assertEqual((len(shows), shows[0]["lang"], shows[0]["price"], st["failed"]),
                         (1, "", "8€", 1))

    def test_the_reads_are_capped_per_run(self):
        rows = [row(film(f"f{i}", f"Film {i}"), f"1{i}:00", "04.09.", link(f"/checkout/{i}"))
                for i in range(4)]
        with mock.patch.object(orion, "FILM_MAX", 2):
            shows, gets, st, out = self.run_it(rows,
                                               {f"f{i}": film_page("suomi") for i in range(4)})
        self.assertEqual((len(gets), st["deferred"]), (2, 2))
        self.assertIn("[orion] film pages: 4 due, reading 2, 2 wait for the next run", out)

    def test_a_row_with_no_film_page_is_left_alone(self):
        shows, gets, _, _ = self.run_it(
            [row("Espoo Ciné: Four Minus Three", "21:00", "04.09.", link("/checkout/x"))], {})
        self.assertEqual((gets, shows[0]["movieUrl"], shows[0]["lang"]), ([], "", ""))

    def test_fetch_site_runs_the_pass_on_the_table_it_read(self):
        shows = [{"title": "A", "movieUrl": ""}]
        with mock.patch.object(orion, "fetch_page", return_value=shows), \
             mock.patch.object(orion, "film_language") as pass_:
            out = orion.fetch_site()
        pass_.assert_called_once_with(shows)
        self.assertEqual(out, {orion.VENUE["id"]: shows})

    def test_the_film_page_url_is_the_row_s_own_link(self):
        shows = orion.parse(page(("04.09.", [row(film("memoria", "Memoria"), "21:00", "04.09.",
                                                  link("/checkout/c"))])), today=TODAY)
        self.assertEqual(shows[0]["movieUrl"], orion.URL + "elokuvat/memoria/")


if __name__ == "__main__":
    unittest.main()
