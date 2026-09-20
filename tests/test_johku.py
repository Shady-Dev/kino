"""The Johku storefront reader: four cinemas, one listing each.

The fixtures are the markup as read on 2026-09-18, cut to the smallest shape that still
exercises a rule. Two rows minimum everywhere there is a loop.

What they exist to prove:

- **The UTC instant and the printed clock are both read.** They agreed on all 71 rows that
  day, so only a fixture can show what happens when they stop agreeing, which is the fault
  that would publish every screening at the wrong hour.
- **A day group holds one thing that is not a screening**, a hall hire, and the storefront
  files it under `/fi_FI/products/` while every film and event sits under a programme
  category. Nothing else is left out: a film page with no director, no genre or no answer
  at all costs the row its metadata and never its place.
- **A grid item with no `data-showtime` is a coming-soon entry**, and Bio Marilyn had
  fourteen of them.
- **The synopsis carries its own language.** Tammisaari publishes Swedish.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import johku as J
import registry
import run


MARILYN = next(s for s in J.SITES if s["provider"] == "biomarilyn")
FORUM = next(s for s in J.SITES if s["provider"] == "bioforum")

SYN_FI = ("Klaus Härön draama kertoo kahden naisen kohtaamisesta keskellä hoitoalan "
          "kriisiä, kun sairaanhoitajat uhkaavat lakolla ja hän joutuu venymään.")
SYN_SV = ("Filmen handlar om en ung kvinna som inte vet att hennes far är tillbaka, och "
          "det som händer efter att hon möter honom i staden.")
# Long enough to be read as a synopsis and carrying no function word of any of the three
# languages. "The Odyssey" at Vihdin Kino was this case on 2026-09-18.
SYN_NO_LANGUAGE = ("Odysseus. Troija, Ithaka, Kirke, Kalypso, Skylla, Kharybdis, Poseidon, "
                   "Penelope, Telemakhos, Polyfemos, Aiolos, Laistrygonit.")


def row(slug, title, when, clock, loc="Bio Marilyn", rating="12", dur="1 h 27 min",
        product="1038", category="nyt-ohjelmistossa", timed=True, path=None):
    """One grid item. `when` is the UTC instant, `clock` what the page prints beside it."""
    time_span = (f'<span class="showtime" data-showtime="{when}">klo {clock}</span>'
                 if timed else "")
    path = path if path is not None else f"/fi_FI/{category}/{slug}"
    return (f'<a href="{path}" class="js-grid-item js-grid-show" '
            f'data-product="{product}"><span class="grid-content-image"></span>'
            f'<span class="showrating rating-icon rating-{rating}">K-{rating}</span>'
            f'<h3 class="grid-content-title" data-name="{title}">{title}</h3>'
            f'<span class="grid-content-text">'
            f'<span class="location showlocation venue showresource" '
            f'data-location="{loc}">{loc}</span>'
            f'<span class="showtimecontainer">{time_span}'
            f'<span class="showduration">{dur}</span></span></span></a>')


def listing(*groups_):
    return "<html><body><div class='container'>" + "".join(groups_) + "</div></body></html>"


def group(day, *rows_):
    return (f'<div class="showgroup"><h3 class="daytitle">{day}</h3>'
            f'<div class="js-grid">' + "".join(rows_) + "</div></div>")


def film(kesto="87 min", genres="Draama", original="Hetki ennen valoa", syn=SYN_FI,
         labels=True):
    rows_ = ""
    if labels:
        rows_ = (f'<div class="product-content-inforow">'
                 f'<div class="product-content-infolabel">Kesto</div>'
                 f'<div class="product-content-infovalue text-content">{kesto}</div></div>'
                 f'<div class="product-content-inforow">'
                 f'<div class="product-content-infolabel">Luokittelu</div>'
                 f'<div class="product-content-infovalue text-content">{genres}</div></div>'
                 f'<div class="product-content-inforow">'
                 f'<div class="product-content-infolabel">Alkuperäinen nimi</div>'
                 f'<div class="product-content-infovalue text-content">{original}</div>'
                 f'</div><div class="product-content-inforow">'
                 f'<div class="product-content-infolabel">Ohjaaja</div>'
                 f'<div class="product-content-infovalue text-content">Klaus Härö</div>'
                 f'</div>')
    else:
        rows_ = ('<div class="product-content-inforow">'
                 '<div class="product-content-infolabel">Kesto</div>'
                 '<div class="product-content-infovalue text-content">120 min</div></div>')
    body = (f'<div class="product-description__html"><p>{syn}</p>'
            f'<p>Elokuvateattereissa 4.9.</p></div>' if syn else "")
    return ("<html><body>" + body + '<div class="product-content-infotable">'
            + rows_ + "</div></body></html>")


class ListingTest(unittest.TestCase):
    def two(self):
        return listing(group("Perjantai 19.9.2026",
                             row("hetki", "Hetki ennen valoa", "2026-09-19T14:30:00.000Z",
                                 "17.30"),
                             row("presidentin", "Presidentin kyyditys",
                                 "2026-09-19T16:15:00.000Z", "19.15", product="1039")))

    def test_the_utc_instant_becomes_a_helsinki_offset(self):
        rows_, skipped = J.rows(MARILYN, self.two())
        self.assertEqual([r["start"] for r in rows_],
                         ["2026-09-19T17:30:00+03:00", "2026-09-19T19:15:00+03:00"])
        self.assertEqual(skipped, [])

    def test_winter_time_converts_at_two_hours(self):
        page = listing(group("Perjantai 12.12.2026",
                             row("a", "A", "2026-12-12T17:30:00.000Z", "19.30"),
                             row("b", "B", "2026-12-12T18:00:00.000Z", "20.00")))
        self.assertEqual([r["start"] for r in J.rows(MARILYN, page)[0]],
                         ["2026-12-12T19:30:00+02:00", "2026-12-12T20:00:00+02:00"])

    def test_a_clock_that_contradicts_the_instant_fails_the_site(self):
        page = listing(group("Perjantai 19.9.2026",
                             row("a", "A", "2026-09-19T14:30:00.000Z", "17.30"),
                             row("b", "B", "2026-09-19T16:15:00.000Z", "16.15")))
        with self.assertRaises(J.ListingRowError) as e:
            J.rows(MARILYN, page)
        self.assertIn("16.15", str(e.exception))

    def test_an_instant_with_no_offset_fails_the_site(self):
        page = listing(group("Perjantai 19.9.2026",
                             row("a", "A", "2026-09-19T14:30:00.000", "17.30"),
                             row("b", "B", "2026-09-19T16:15:00.000Z", "19.15")))
        with self.assertRaises(J.ListingRowError) as e:
            J.rows(MARILYN, page)
        self.assertIn("no offset", str(e.exception))

    def test_a_hall_the_site_does_not_list_fails_the_site(self):
        page = listing(group("Perjantai 19.9.2026",
                             row("a", "A", "2026-09-19T14:30:00.000Z", "17.30"),
                             row("b", "B", "2026-09-19T16:15:00.000Z", "19.15",
                                 loc="Kulmasali")))
        with self.assertRaises(J.ListingRowError) as e:
            J.rows(MARILYN, page)
        self.assertIn("Kulmasali", str(e.exception))

    def test_a_row_with_no_time_is_a_coming_soon_entry(self):
        page = listing(group("Perjantai 25.9.2026",
                             row("heart", "Heart of Beast", "", "", timed=False,
                                 category="tulossa"),
                             row("digger", "Digger", "", "", timed=False,
                                 category="tulossa"),
                             row("avengers", "Avengers Endgame Encore",
                                 "2026-09-25T16:20:00.000Z", "19.20")))
        rows_, skipped = J.rows(MARILYN, page)
        self.assertEqual([r["title"] for r in rows_], ["Avengers Endgame Encore"])
        self.assertEqual(sorted(skipped), ["Digger", "Heart of Beast"])

    def test_a_grid_outside_a_day_group_is_not_a_screening(self):
        """The coming-soon shelf renders the same item markup."""
        page = (listing(group("Perjantai 19.9.2026",
                              row("a", "A", "2026-09-19T14:30:00.000Z", "17.30")))
                + '<div class="js-grid">'
                + row("b", "B", "2026-09-19T16:15:00.000Z", "19.15") + "</div>")
        rows_, _ = J.rows(MARILYN, page)
        self.assertEqual([r["title"] for r in rows_], ["A"])

    def test_the_row_carries_rating_runtime_and_the_film_page(self):
        [a, b] = J.rows(MARILYN, self.two())[0]
        self.assertEqual((a["rating"], a["len"]), ("K-12", "87"))
        self.assertEqual(a["url"], "https://www.biomarilyn.com/fi_FI/nyt-ohjelmistossa/hetki")
        self.assertEqual(b["venue"], "biomarilyn-lapua")

    def test_an_unknown_rating_class_is_left_empty(self):
        page = listing(group("Perjantai 19.9.2026",
                             row("a", "A", "2026-09-19T14:30:00.000Z", "17.30",
                                 rating="unknown"),
                             row("b", "B", "2026-09-19T16:15:00.000Z", "19.15",
                                 rating="s")))
        self.assertEqual([r["rating"] for r in J.rows(MARILYN, page)[0]], ["", "S"])


class FilmFactsTest(unittest.TestCase):
    def test_the_info_table_and_the_first_long_paragraph(self):
        f = J.film_facts(film())
        self.assertEqual((f["len"], f["genres"], f["original"]),
                         ("87", "Draama", "Hetki ennen valoa"))
        self.assertEqual(f["syn"], SYN_FI)

    def test_hours_and_minutes(self):
        self.assertEqual(J.film_facts(film(kesto="2 h 30 min"))["len"], "150")

    def test_a_page_with_no_director_or_genre_still_yields_what_it_has(self):
        f = J.film_facts(film(labels=False))
        self.assertEqual((f["genres"], f["original"]), ("", ""))
        self.assertEqual(f["len"], "120")

    def test_a_short_paragraph_is_not_a_synopsis(self):
        self.assertEqual(J.film_facts(film(syn="Tervetuloa!"))["syn"], "")


class ParseTest(unittest.TestCase):
    def pages(self, **over):
        pages = {"1038": film(), "1039": film(syn=SYN_SV)}
        pages.update(over)
        return pages

    def listing_(self):
        return listing(group("Perjantai 19.9.2026",
                             row("hetki", "Hetki ennen valoa", "2026-09-19T14:30:00.000Z",
                                 "17.30"),
                             row("filmen", "Filmen", "2026-09-19T16:15:00.000Z", "19.15",
                                 product="1039")))

    def test_the_synopsis_is_keyed_by_the_language_it_is_written_in(self):
        shows, report = J.parse(MARILYN, self.listing_(), self.pages())
        [a, b] = shows["biomarilyn-lapua"]
        self.assertEqual(a["_syn"], {"fi": SYN_FI})
        self.assertEqual(b["_syn"], {"sv": SYN_SV})
        self.assertEqual(report["unplaced"], set())

    def test_a_text_in_no_settled_language_is_withheld_and_counted(self):
        shows, report = J.parse(MARILYN, self.listing_(),
                                self.pages(**{"1039": film(syn=SYN_NO_LANGUAGE)}))
        self.assertNotIn("_syn", shows["biomarilyn-lapua"][1])
        self.assertEqual(report["unplaced"], {"Filmen"})

    def test_a_row_whose_page_carries_no_director_or_genre_still_publishes(self):
        """A small film that publishes little about itself keeps its place."""
        shows, _ = J.parse(MARILYN, self.listing_(),
                           self.pages(**{"1039": film(labels=False)}))
        [a, b] = shows["biomarilyn-lapua"]
        self.assertEqual(b["title"], "Filmen")
        self.assertEqual((b["genres"], b["original"]), ("", ""))
        self.assertEqual(b["len"], "87", "the row's own runtime stands")

    def test_a_row_whose_page_was_not_read_publishes_without_its_metadata(self):
        shows, _ = J.parse(MARILYN, self.listing_(), {"1038": film()})
        titles = [s["title"] for s in shows["biomarilyn-lapua"]]
        self.assertEqual(titles, ["Hetki ennen valoa", "Filmen"])
        self.assertEqual(shows["biomarilyn-lapua"][1]["genres"], "")
        self.assertNotIn("_syn", shows["biomarilyn-lapua"][1])

    def test_hall_hire_is_left_out_by_its_path(self):
        page = listing(group("Perjantai 19.9.2026",
                             row("hetki", "Hetki ennen valoa", "2026-09-19T14:30:00.000Z",
                                 "17.30"),
                             row("sali", "Salivaraus", "2026-09-19T16:15:00.000Z",
                                 "19.15", product="94",
                                 path="/fi_FI/products/94-kinokulma-salivaraus")))
        shows, report = J.parse(MARILYN, page, self.pages())
        self.assertEqual([s["title"] for s in shows["biomarilyn-lapua"]],
                         ["Hetki ennen valoa"])
        self.assertEqual((report["hire"], report["hire_shows"]), ({"Salivaraus"}, 1))

    def test_the_show_shape(self):
        shows, _ = J.parse(MARILYN, self.listing_(), self.pages())
        s = shows["biomarilyn-lapua"][0]
        self.assertEqual((s["price"], s["img"], s["soldOut"], s["aud"], s["lang"]),
                         ("", "", False, "", ""))
        self.assertEqual((s["eventId"], s["provider"], s["theatre"]),
                         ("1038", "biomarilyn", "Bio Marilyn"))
        self.assertEqual(s["original"], "Hetki ennen valoa")


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._fetch, self._sleep = J.fetch, J.time.sleep
        self.addCleanup(lambda: setattr(J, "fetch", self._fetch))
        self.addCleanup(lambda: setattr(J.time, "sleep", self._sleep))
        J.time.sleep = lambda s: None
        self.calls = []

    def serve(self, pages):
        def fetch(url, **kw):
            self.calls.append(url)
            body = pages.get(url)
            if isinstance(body, Exception):
                raise body
            if body is None:
                raise RuntimeError(f"unexpected fetch {url}")
            return body.encode("utf-8")
        J.fetch = fetch

    def main(self, half="all"):
        """`--half all` explicitly: Haapamäen Elokuvat is local and the other four are
        cloud, so without it this would run five sites on a laptop and four on Actions,
        where `half_of` reads GITHUB_ACTIONS. The fixture serves every site either way."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["johku", "--half", half])
        return code, out.getvalue() + err.getvalue()

    def all_sites(self, **over):
        pages = {}
        for site in J.SITES:
            loc = site["venues"][0]["loc"]
            base = site["base"]
            pages[base + "/"] = listing(group(
                "Perjantai 19.9.2026",
                row("a", "A", "2026-09-19T14:30:00.000Z", "17.30", loc=loc,
                    product="1", category="ohjelmisto"),
                row("b", "B", "2026-09-19T16:15:00.000Z", "19.15", loc=loc,
                    product="2", category="ohjelmisto")))
            pages[base + "/fi_FI/ohjelmisto/a"] = film()
            pages[base + "/fi_FI/ohjelmisto/b"] = film(syn=SYN_SV)
        pages.update(over)
        return pages

    def test_all_sites_publish(self):
        self.serve(self.all_sites())
        code, log = self.main()
        self.assertEqual(code, 0, log)
        for site in J.SITES:
            vid = site["venues"][0]["id"]
            shows = json.loads((run.OUT / f"area-{vid}.json").read_text())["shows"]
            self.assertEqual(len(shows), 2, vid)
            self.assertEqual({s["price"] for s in shows}, {""})
        self.assertIn("0 failures", log)

    def test_a_listing_with_no_day_group_fails_that_site_and_keeps_its_file(self):
        """No tenant has been seen empty, so this may not read as an empty programme."""
        prev = {"generated": "2026-09-01T00:00:00+00:00", "dates": ["2026-09-01"],
                "horizon": "2026-09-01",
                "shows": [{"title": "Old", "start": "2026-09-01T12:00:00+03:00"}]}
        (run.OUT / "area-kinokulma-oulainen.json").write_text(json.dumps(prev))
        self.serve(self.all_sites(**{"https://kinokulma.fi/": "<html><body></body></html>"}))
        code, log = self.main()
        self.assertEqual(code, 1, log)
        self.assertIn("no evidence of one", log)
        self.assertNotIn("no programme published", log)
        self.assertEqual(json.loads(
            (run.OUT / "area-kinokulma-oulainen.json").read_text()), prev)
        self.assertTrue((run.OUT / "area-bioforum-tammisaari.json").exists())

    def test_a_listing_of_nothing_but_hall_hire_fails_that_site(self):
        self.serve(self.all_sites(**{
            "https://bioforum.fi/": listing(group(
                "Perjantai 19.9.2026",
                row("a", "Salivaraus", "2026-09-19T14:30:00.000Z", "17.30",
                    loc="Bio Forum", product="94", path="/fi_FI/products/94-sali"),
                row("b", "Salivaraus 2", "2026-09-19T16:15:00.000Z", "19.15",
                    loc="Bio Forum", product="95", path="/fi_FI/products/95-sali")))}))
        code, log = self.main()
        self.assertEqual(code, 1, log)
        self.assertIn("template failure", log)
        self.assertFalse((run.OUT / "area-bioforum-tammisaari.json").exists())
        self.assertTrue((run.OUT / "area-vihdinkino-vihti.json").exists())

    def test_a_film_page_that_fails_still_publishes_its_screenings(self):
        """The page carries metadata, not the decision to publish."""
        self.serve(self.all_sites(**{
            "https://vihdinkino.fi/fi_FI/ohjelmisto/a": RuntimeError("HTTP Error 503")}))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        shows = json.loads(
            (run.OUT / "area-vihdinkino-vihti.json").read_text())["shows"]
        self.assertEqual([s["title"] for s in shows], ["A", "B"])
        self.assertEqual(shows[0]["genres"], "")

    def test_the_hall_hire_page_is_never_fetched(self):
        """It is dropped before the film pages are chosen, so the request is not made."""
        self.serve(self.all_sites(**{
            "https://kinokulma.fi/": listing(group(
                "Perjantai 19.9.2026",
                row("a", "A", "2026-09-19T14:30:00.000Z", "17.30", loc="Kulmasali",
                    product="1", category="ohjelmisto"),
                row("sali", "Salivaraus", "2026-09-19T20:00:00.000Z", "23.00",
                    loc="Kulmasali", product="94",
                    path="/fi_FI/products/94-kinokulma-salivaraus")))}))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual([c for c in self.calls if "/products/" in c], [])
        self.assertIn("hall-hire", log)

    def test_one_film_page_per_distinct_product(self):
        self.serve(self.all_sites())
        self.assertEqual(self.main()[0], 0)
        films = [c for c in self.calls if "/fi_FI/" in c]
        self.assertEqual(sorted(films), sorted(set(films)))
        self.assertEqual(len(films), 12)      # six storefronts, two films each


class KinoHannikainenTest(unittest.TestCase):
    """The sixth storefront, Nurmes, added 2026-09-20.

    Read that day: eight rows over five day groups, every one carrying
    `data-location="Hannikaisen sali"`, which is the hall the registry declares and the
    one the 250-seat auditorium in Nurmes-talo is named. The listing is served from the
    cinema's own domain rather than from `johku.com`, so the site keeps a pacing group of
    its own.
    """

    SITE = next(s for s in J.SITES if s["provider"] == "kinohannikainen")

    def listing_(self):
        return listing(group(
            "Perjantai 2.10.2026",
            row("rakkautta-ja-virtahepoja", "Rakkautta ja virtahepoja",
                "2026-10-02T14:00:00.000Z", "17.00", loc="Hannikaisen sali",
                product="1", category="ohjelmisto", dur="1 h 41 min"),
            row("myrskyn-nbsp-ikkuna", "MYRSKYN IKKUNA",
                "2026-10-02T16:30:00.000Z", "19.30", loc="Hannikaisen sali",
                product="2", category="ohjelmisto", dur="1 h 40 min")))

    def test_the_hall_the_rows_carry_is_the_declared_venue(self):
        shows, _ = J.parse(self.SITE, self.listing_(), {})
        self.assertEqual(list(shows), ["kinohannikainen-nurmes"])
        rows_ = shows["kinohannikainen-nurmes"]
        self.assertEqual([s["title"] for s in rows_],
                         ["Rakkautta ja virtahepoja", "MYRSKYN IKKUNA"])
        self.assertEqual([s["start"] for s in rows_],
                         ["2026-10-02T17:00:00+03:00", "2026-10-02T19:30:00+03:00"])
        self.assertEqual({s["theatre"] for s in rows_}, {"Kino Hannikainen"})

    def test_the_listing_is_read_from_the_cinemas_own_domain(self):
        """`johku.com` is the platform, not the host any site is read from. A base there
        would share one pacing group with every other site on it."""
        self.assertEqual(self.SITE["base"], "https://www.kinohannikainen.net")
        self.assertNotIn("johku.com", self.SITE["base"])
        self.assertNotIn("reads", self.SITE)


class RegistryTest(unittest.TestCase):
    def test_the_cloud_registry_entries(self):
        for pid, label, host, city in (
                ("biomarilyn", "Bio Marilyn", "biomarilyn.com", "Lapua"),
                ("vihdinkino", "Vihdin Kino", "vihdinkino.fi", "Vihti"),
                ("bioforum", "Bio Forum", "bioforum.fi", "Tammisaari"),
                ("kinokulma", "Kinokulma", "kinokulma.fi", "Oulainen"),
                ("kinohannikainen", "Kino Hannikainen", "kinohannikainen.net", "Nurmes")):
            with self.subTest(provider=pid):
                p = registry.by_id(pid)
                self.assertEqual((p["label"], p["host"], p["book"], p["module"],
                                  p["where"]), (label, host, "buy", "johku", "cloud"))
                self.assertEqual(sum(1 for q in registry.PROVIDERS
                                     if q["accent"] == p["accent"]), 1)
                site = next(s for s in J.SITES if s["provider"] == pid)
                self.assertEqual(site["venues"][0]["city"], city)

    def test_the_venue_name_matches_the_chain_label(self):
        """`build_pages.label_of` concatenates the two when the venue name does not start
        with the chain word, which put the town in the page slug twice."""
        for site in J.SITES:
            with self.subTest(provider=site["provider"]):
                label = registry.by_id(site["provider"])["label"]
                self.assertTrue(site["venues"][0]["name"].startswith(label))

    def test_bio_marilyn_and_kino_marilyn_are_two_cinemas(self):
        """Loviisa's is on its own site and its own module."""
        self.assertNotEqual(registry.by_id("biomarilyn")["host"],
                            registry.by_id("kinomarilyn")["host"])
        self.assertNotEqual(registry.by_id("biomarilyn")["module"],
                            registry.by_id("kinomarilyn")["module"])

    def test_each_site_names_the_host_it_reads_and_they_are_paced_apart(self):
        self.assertEqual([s["base"] for s in J.SITES],
                         ["https://www.biomarilyn.com", "https://vihdinkino.fi",
                          "https://bioforum.fi", "https://kinokulma.fi",
                          "https://haapamaenelokuvat.fi",
                          "https://www.kinohannikainen.net"])
        self.assertEqual(len(run.host_groups(J.SITES)), 6)

    def test_kino_engel_and_kino_tapiola_stay_on_their_own_modules(self):
        """The widget is not the storefront; those two keep their own parsers."""
        self.assertEqual(registry.by_id("engel")["module"], "engel")
        self.assertEqual(registry.by_id("tapiola")["module"], "tapiola")


if __name__ == "__main__":
    unittest.main()
