"""eTiketti renders its screenings in two templates, and etiketti.py reads both.

Kotka's template (sixteen hosts since 2026-08-30) prints "KE 2.9. klo 20.00", a place
line "TRIO 123 | SALI 2", "Lippu 15,00€" and "Vapaat paikat 27/35". Cinema Niagara's
(2026-09-02) prints the time in a `time` div, the price in `show-price`, "Paikkoja
vapaana: 126/127", per-screening tags in `movie-specs`, no place line, a newline between
`<div` and `class`, and detail labels without a colon. The fixtures below are minimal
hand-written reconstructions of those shapes, not copies of anyone's page.

Niagara's programme page renders every screening twice, in a desktop and a mobile wrapper.
The adapter never reads that page, but a film page must not be able to double a show
either, so shows are keyed on the public screening id the ticket href carries. The href
itself is published as the outbound link and is never fetched.

Provider modules are imported inside the tests: they bind `common.EmptyProgramme` at
import time and `test_common_fetch` reloads `common`.
"""
import datetime
import importlib
import json
import pathlib
import re
import tempfile
import unittest

import _ctx                                                # noqa: F401
import common


def load():
    return importlib.import_module("etiketti")


def site(pid):
    return next(s for s in load().SITES if s["provider"] == pid)


HIDDEN = ('<div class="no-results" id="no-results" style="display: none;">'
          "<p>Ei näytöksiä valitsemallasi päivämäärällä.</p></div>")

# --- template 1: Kotka ------------------------------------------------------------------

KOTKA_FILM = """<main>
<h1>Insidious: Out of the Further</h1>
<img class="poster-img" src="https://cdn.example/kotka/poster/insidious_1.webp?w=250" alt="">
<img src="https://cdn.example/kotka/img/ikarajat/fi-16.svg" alt="Sallittu yli 16-vuotiaille">
<div class="description-container"><span>Elokuva on sallittu yli 16-vuotiaille. Sisältää kauhua. Tarina jatkuu siitä, mihin edellinen jäi.</span></div>
<span class="label">Kesto:</span> 1 h 46 min<br />
<span class="label">Kieli:</span> englanti<br />
<span class="label">Tekstitys:</span> Suomi ja ruotsi<br />
<span class="movie-genre">Kauhu</span><span class="movie-genre">Trilleri</span>
<h2>Näytökset</h2>
<div class="screenings">
""" + HIDDEN + """
<div class="item kotka date-2.9.2026"> <div> <p> <strong><span>KE 2.9. klo 20.00</span></strong> </p> <p> TRIO 123 | SALI 2<br /> Lippu 15,00&euro;<br /> Vapaat paikat 27/35 </p> </div> <div> <a class="button-screening" href="/salikartta?id=56106"> Osta tai varaa </a> </div> </div>
<div class="item kotka date-4.9.2026"> <div> <p> <strong><span>PE 4.9. klo 19.30</span></strong> </p> <p> KINOPALATSI<br /> Lippu 12,50&euro;<br /> Vapaat paikat 0/120 </p> </div> <div> <a class="button-screening" href="/salikartta?id=56107"> Osta tai varaa </a> </div> </div>
</div>
</div>
</div>
</main>"""

# --- template 2: Cinema Niagara ---------------------------------------------------------

def niagara_item(date, hhmm, sid, price="13,00", seats="126/127", tags=(), opener=None):
    opener = opener if opener is not None else f'<div\n        class="item tampere date-{date}">'
    tag_html = "".join(f'<span class="tag" style="background-color:#a6d6c4;">{t}</span>'
                       for t in tags)
    price_html = f'<div class="show-price">\n  {price}€\n</div>' if price else ""
    seats_html = (f'<div class="seats-info"><div class="seat-color seats-high">\n</div>\n'
                  f'Paikkoja vapaana: {seats}\n</div>' if seats else "")
    return (f"{opener}\n<div class=\"time\">\n  <span>{hhmm}</span>\n</div>\n"
            f'<div class="movie-specs">\n  {tag_html}\n</div>\n{price_html}\n'
            f'<div class="action">\n<a class="button-screening" href="/salikartta?id={sid}">\n'
            f"  Osta liput\n</a>\n{seats_html}</div>\n</div>\n")


NIAGARA_HEAD = """<main>
<h1>The Invite</h1>
<img class="poster-img" src="https://cdn.example/niagara/poster/the-invite_1.webp?w=250" alt="The Invite">
<img src="https://cdn.example/niagara/img/ikarajat/fi-12.svg" alt="Sallittu yli 12-vuotiaille">
<div class="description-container"><span>Elokuva on sallittu yli 12-vuotiaille. Sisältää seksiä. Joen ja Angelan avioliitto on veitsenterällä.</span></div>
<div class="movie-details-grid">
<div><span class="label">Kieli                </span> englanti, espanja </div>
<div><span class="label">Tekstitys            </span> Suomi ja ruotsi </div>
<div><span class="label">Kesto                </span> 1 h 48 min </div>
<div><span class="label">Näyttelijät</span> Seth Rogen, Olivia Wilde </div>
<div><span class="label">Ohjaaja</span> Olivia Wilde </div>
<div><span class="label">genre</span> Draama, Komedia </div>
</div>
"""

NIAGARA_ITEMS = (
    '<div class="show-date-header">Torstai 3.9.</div>\n'
    + niagara_item("3.9.2026", "16.15", 53882, "13,00", "126/127")
    + niagara_item("3.9.2026", "18.45", 53955, "11,00", "0/127", ("Seniorikino", "Q&amp;A"))
    + '<div class="show-date-header">Torstai 5.11.</div>\n'
    + niagara_item("5.11.2026", "12.00", 60001, "8,00", "40/127", ("Seniorikino",))
)


def niagara_page(items=NIAGARA_ITEMS, twice=True):
    block = f'<div class="screenings shows niagara">\n{HIDDEN}\n{items}</div>\n'
    body = f'<div class="desktop">\n{block}</div>\n'
    if twice:
        body += f'<div class="mobile">\n{block}</div>\n'
    return NIAGARA_HEAD + body + "</main>"


NIAGARA_FILM = niagara_page()

# A film page in neither template: the listing links to it, it renders no screening item.
FOREIGN_FILM = "<main><h1>Elokuva</h1><section><p>Liput ovelta.</p></section></main>"


def listing(*paths):
    cards = "".join(f'<div class="item tampere date-3.9.2026 name-x"><a href="{p}">x</a></div>'
                    for p in paths)
    return f'<main><div class="screenings movie-list">{cards}</div>{HIDDEN}</main>'


LISTING = listing("/elokuvat/70/the-invite", "/elokuvat/63/the-dog-stars")
GENUINELY_EMPTY = ('<main><div class="screenings movie-list"><p>Ei ohjelmistoa saatavilla.</p>'
                   f"</div>{HIDDEN}</main>")


def stub_get(mapping):
    """Route `etiketti.get` by URL suffix. Anything unmapped is a test error, and a
    request for /salikartta is the one thing this adapter must never make."""
    def get(url, tries=3):
        if "/salikartta" in url:
            raise AssertionError(f"booking page requested: {url}")
        for suffix, page in mapping.items():
            if url.endswith(suffix):
                return page
        raise AssertionError(f"unexpected fetch: {url}")
    return get


class Stubbed(unittest.TestCase):
    def stub(self, mapping):
        e = load()
        real = e.get
        e.get = stub_get(mapping)
        self.addCleanup(lambda: setattr(e, "get", real))
        return e


# --- template 1 still parses exactly as before -------------------------------------------

class KotkaTemplateTest(Stubbed):

    def rows(self):
        e = load()
        return e.parse_movie(KOTKA_FILM, site("kotkanleffat"), "/elokuvat/3268/insidious")

    def test_two_dates_two_rows_with_place_room_price_seats_and_link(self):
        rows, meta = self.rows()
        self.assertEqual(len(rows), 2)
        a, b = rows
        self.assertEqual((a["theatre_raw"], a["aud"]), ("TRIO 123", "SALI 2"))
        self.assertEqual(a["start"], "2026-09-02T20:00:00+03:00")
        self.assertEqual((a["price"], a["free"]), ("15€", 27))
        self.assertEqual(a["url"], "https://kotkanleffat.fi/salikartta?id=56106")
        self.assertEqual((b["theatre_raw"], b["aud"]), ("KINOPALATSI", ""))
        self.assertEqual((b["price"], b["free"]), ("12.5€", 0))

    def test_metadata_with_colon_labels_and_genre_spans(self):
        _, meta = self.rows()
        self.assertEqual(meta["title"], "Insidious: Out of the Further")
        self.assertEqual(meta["rating"], "K-16")
        self.assertEqual(meta["len"], "106")
        self.assertEqual(meta["img"], "https://cdn.example/kotka/poster/insidious_1.webp")
        self.assertEqual(meta["lang"], "EN-A, FI-S, SV-S")
        self.assertEqual(meta["genres"], "Kauhu, Trilleri")
        self.assertEqual(meta["syn"], "Tarina jatkuu siitä, mihin edellinen jäi.")

    def test_kotka_rows_carry_no_tags_and_match_by_the_place_line(self):
        e = self.stub({"/elokuvat/ohjelmistossa": listing("/elokuvat/3268/insidious"),
                       "/elokuvat/3268/insidious": KOTKA_FILM})
        out = e.fetch_site(site("kotkanleffat"), sleep=0)
        self.assertEqual(sorted(out), ["kl-kinopalatsi", "kl-trio123"])
        show = out["kl-trio123"][0]
        self.assertEqual(show["method"], "")
        self.assertEqual(show["aud"], "SALI 2")
        self.assertFalse(show["soldOut"])
        self.assertTrue(out["kl-kinopalatsi"][0]["soldOut"])


# --- template 2 ---------------------------------------------------------------------------

class NiagaraTemplateTest(Stubbed):

    def rows(self, page=NIAGARA_FILM):
        e = load()
        return e.parse_movie(page, site("niagara"), "/elokuvat/70/the-invite")

    def fetch(self, film=NIAGARA_FILM):
        e = self.stub({"/elokuvat/ohjelmistossa": listing("/elokuvat/70/the-invite"),
                       "/elokuvat/70/the-invite": film})
        return e.fetch_site(site("niagara"), sleep=0)

    def test_the_items_parse_with_the_newline_before_class(self):
        rows, _ = self.rows()
        self.assertEqual(len(rows), 6)           # three screenings, rendered twice
        self.assertEqual([r["start"] for r in rows[:3]],
                         ["2026-09-03T16:15:00+03:00", "2026-09-03T18:45:00+03:00",
                          "2026-11-05T12:00:00+02:00"])

    def test_finnish_time_zone_follows_the_date(self):
        """September is +03:00, November +02:00: the offset is computed, not pasted."""
        rows, _ = self.rows()
        self.assertTrue(rows[0]["start"].endswith("+03:00"))
        self.assertTrue(rows[2]["start"].endswith("+02:00"))

    def test_responsive_duplicates_collapse_to_one_show_each(self):
        out = self.fetch()
        shows = out["cn-tampere"]
        self.assertEqual(len(shows), 3)
        self.assertEqual(len({s["url"] for s in shows}), 3)

    def test_the_same_id_repeated_is_one_show_even_in_one_wrapper(self):
        page = niagara_page(niagara_item("3.9.2026", "16.15", 1) * 3, twice=False)
        self.assertEqual(len(self.fetch(page)["cn-tampere"]), 1)

    def test_prices_stay_with_their_screening(self):
        shows = self.fetch()["cn-tampere"]
        self.assertEqual([s["price"] for s in shows], ["13€", "11€", "8€"])

    def test_seats_derive_sold_out_and_nothing_else(self):
        shows = self.fetch()["cn-tampere"]
        self.assertEqual([s["soldOut"] for s in shows], [False, True, False])
        for s in shows:
            with self.subTest(url=s["url"]):
                self.assertNotIn("free", s)
                self.assertNotIn("seats", s)
                self.assertNotIn("127", json.dumps(s))

    def test_tags_become_method_decoded_and_deduplicated(self):
        shows = self.fetch()["cn-tampere"]
        self.assertEqual([s["method"] for s in shows], ["", "Seniorikino · Q&A", "Seniorikino"])

    def test_the_venue_is_matched_by_the_items_place_class(self):
        rows, _ = self.rows()
        self.assertEqual(rows[0]["theatre_raw"], "tampere")
        self.assertEqual(rows[0]["aud"], "")
        out = self.fetch()
        self.assertEqual(list(out), ["cn-tampere"])
        self.assertEqual(out["cn-tampere"][0]["theatre"], "Cinema Niagara")

    def test_the_ticket_href_is_the_outbound_link_and_is_never_fetched(self):
        """stub_get raises on any /salikartta request, so reaching the assertion at all
        proves the adapter published the href without following it."""
        shows = self.fetch()["cn-tampere"]
        self.assertEqual(shows[0]["url"], "https://cinemaniagara.fi/salikartta?id=53882")

    def test_metadata_without_colons_and_the_genre_label(self):
        _, meta = self.rows()
        self.assertEqual(meta["title"], "The Invite")
        self.assertEqual(meta["rating"], "K-12")
        self.assertEqual(meta["len"], "108")
        self.assertEqual(meta["img"], "https://cdn.example/niagara/poster/the-invite_1.webp")
        self.assertEqual(meta["lang"], "EN-A, ES-A, FI-S, SV-S")
        self.assertEqual(meta["genres"], "Draama, Komedia")
        self.assertEqual(meta["syn"], "Joen ja Angelan avioliitto on veitsenterällä.")

    def test_credits_are_not_published(self):
        show = self.fetch()["cn-tampere"][0]
        self.assertNotIn("Olivia Wilde", json.dumps(show, ensure_ascii=False))

    def test_whitespace_and_trailing_class_variants_parse(self):
        openers = ['<div class="item tampere date-6.9.2026">',
                   '<div class="item tampere date-6.9.2026 name-The-Invite">',
                   '<div\n\t\tclass="item tampere date-6.9.2026">',
                   '<div\n   class="item tampere date-6.9.2026 name-x">']
        for i, op in enumerate(openers):
            with self.subTest(opener=op):
                rows, _ = self.rows(niagara_page(niagara_item("6.9.2026", "10.00", 100 + i, opener=op), twice=False))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["start"], "2026-09-06T10:00:00+03:00")
                self.assertEqual(rows[0]["theatre_raw"], "tampere")

    def test_missing_or_malformed_optional_fields(self):
        item = niagara_item("6.9.2026", "10.00", 7, price="", seats="")
        item = item.replace("</a>\n</div>", '</a>\n<div class="seats-info">Paikkoja vapaana: n/a</div></div>')
        page = niagara_page(item, twice=False).replace(
            '<img class="poster-img" src="https://cdn.example/niagara/poster/the-invite_1.webp?w=250" alt="The Invite">', "")
        rows, meta = self.rows(page)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["price"], rows[0]["free"], rows[0]["method"]), ("", None, ""))
        self.assertEqual(meta["img"], "")
        show = self.fetch(page)["cn-tampere"][0]
        self.assertFalse(show["soldOut"])
        self.assertEqual(show["img"], "")

    def test_an_item_without_a_time_is_skipped_not_invented(self):
        item = niagara_item("6.9.2026", "10.00", 7).replace("<span>10.00</span>", "")
        rows, _ = self.rows(niagara_page(item, twice=False))
        self.assertEqual(rows, [])


class NoScreeningIdFallbackTest(Stubbed):
    """A row without a ticket href has no public screening id. It is keyed on film,
    start, place and auditorium together, and recorded only once a venue took it."""

    @staticmethod
    def kotka_item(date, hhmm, place, sid=None):
        link = (f'<a class="button-screening" href="/salikartta?id={sid}">Osta</a>'
                if sid else "<span>Liput ovelta</span>")
        return (f'<div class="item kotka date-{date}"> <div> <p> <strong><span>KE 2.9. klo '
                f"{hhmm}</span></strong> </p> <p> {place}<br /> Lippu 10,00&euro;<br /> "
                f"Vapaat paikat 5/50 </p> </div> <div> {link} </div> </div>\n")

    def kotka(self, items):
        page = ("<main><h1>Film</h1><div class=\"screenings\">" + HIDDEN + items
                + "</div>\n</div>\n</div></main>")
        e = self.stub({"/elokuvat/ohjelmistossa": listing("/elokuvat/1/film"),
                       "/elokuvat/1/film": page})
        return e.fetch_site(site("kotkanleffat"), sleep=0)

    def test_the_same_no_id_screening_repeated_by_markup_is_one_show(self):
        item = niagara_item("3.9.2026", "16.15", 0).replace(
            '<a class="button-screening" href="/salikartta?id=0">\n  Osta liput\n</a>', "")
        self.assertNotIn("salikartta", item)
        e = self.stub({"/elokuvat/ohjelmistossa": listing("/elokuvat/70/the-invite"),
                       "/elokuvat/70/the-invite": niagara_page(item, twice=True)})
        shows = e.fetch_site(site("niagara"), sleep=0)["cn-tampere"]
        self.assertEqual(len(shows), 1)
        self.assertEqual(shows[0]["url"], "https://cinemaniagara.fi/elokuvat/70/the-invite")

    def test_two_venues_at_the_same_minute_stay_two_shows(self):
        out = self.kotka(self.kotka_item("2.9.2026", "20.00", "KINOPALATSI")
                         + self.kotka_item("2.9.2026", "20.00", "TRIO 123 | SALI 2"))
        self.assertEqual(sorted(out), ["kl-kinopalatsi", "kl-trio123"])
        self.assertEqual(out["kl-kinopalatsi"][0]["start"], out["kl-trio123"][0]["start"])

    def test_two_auditoriums_at_the_same_minute_stay_two_shows(self):
        out = self.kotka(self.kotka_item("2.9.2026", "20.00", "TRIO 123 | SALI 1")
                         + self.kotka_item("2.9.2026", "20.00", "TRIO 123 | SALI 2"))
        self.assertEqual(sorted(s["aud"] for s in out["kl-trio123"]), ["SALI 1", "SALI 2"])

    def test_the_same_hall_repeated_without_an_id_is_still_one_show(self):
        out = self.kotka(self.kotka_item("2.9.2026", "20.00", "TRIO 123 | SALI 2") * 2)
        self.assertEqual(len(out["kl-trio123"]), 1)

    def test_a_malformed_copy_that_matches_no_venue_does_not_suppress_the_valid_one(self):
        """Same public id twice; the first copy names a place no venue owns. Recording
        the key before the venue match would publish nothing for this screening."""
        out = self.kotka(self.kotka_item("2.9.2026", "20.00", "VARASTO", sid=9)
                         + self.kotka_item("2.9.2026", "20.00", "TRIO 123 | SALI 2", sid=9))
        self.assertEqual(len(out["kl-trio123"]), 1)
        self.assertEqual(out["kl-trio123"][0]["url"], "https://kotkanleffat.fi/salikartta?id=9")

    def test_the_public_id_wins_over_the_composite(self):
        """Two rows, one id, same hall, different printed minute -- the platform's id is
        the identity, so one show."""
        out = self.kotka(self.kotka_item("2.9.2026", "20.00", "TRIO 123 | SALI 2", sid=9)
                         + self.kotka_item("2.9.2026", "20.05", "TRIO 123 | SALI 2", sid=9))
        self.assertEqual(len(out["kl-trio123"]), 1)


class LanguageNamesTest(unittest.TestCase):

    def test_names_resolve_in_source_order_without_repeats(self):
        e = load()
        self.assertEqual(e.lang_codes("Suomi ja ruotsi"), ["FI", "SV"])
        self.assertEqual(e.lang_codes("englanti, espanja"), ["EN", "ES"])
        self.assertEqual(e.lang_codes("suom./ruots."), ["FI", "SV"])
        self.assertEqual(e.lang_codes("englanniksi, englanti"), ["EN"])
        self.assertEqual(e.lang_codes("Alkuperäinen"), [])
        self.assertEqual(e.lang_codes(""), [])
        self.assertEqual(e.lang_codes(None), [])

    def test_every_client_language_has_a_finnish_name_here(self):
        """The map is the inverse of the client's LN.fi, so a code it produces is one the
        app can name."""
        e = load()
        client = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")
        block = re.search(r"const LN = \{(.*?)\n  \};", client, re.S).group(1)
        fi = dict(re.findall(r"([A-Z]{2}):'([^']*)'", re.search(r"\bfi:\{(.*?)\}", block, re.S).group(1)))
        self.assertEqual({v: k for k, v in fi.items()}, e.LANG_NAMES)


# --- the zero-show rule, both directions ----------------------------------------------------

class ZeroShowsTest(Stubbed):

    def test_a_listing_with_films_whose_pages_render_no_items_yields_nothing(self):
        """The failure case: fetch_site returns no venue at all, and run.py fails a site
        with no shows. It must not look like an empty programme."""
        e = self.stub({"/elokuvat/ohjelmistossa": LISTING,
                       "/elokuvat/70/the-invite": FOREIGN_FILM,
                       "/elokuvat/63/the-dog-stars": FOREIGN_FILM})
        self.assertEqual(e.fetch_site(site("niagara"), sleep=0), {})

    def test_that_failure_fails_the_run_and_keeps_the_previous_data(self):
        import run
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        saved = run.OUT
        run.OUT = pathlib.Path(tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", saved))
        prev = {"generated": "2026-08-01T00:00:00+00:00", "dates": ["2026-08-02"],
                "horizon": "2026-08-02",
                "shows": [{"title": "Dyyni", "start": "2026-08-02T18:00:00+03:00"}]}
        (run.OUT / "area-cn-tampere.json").write_text(json.dumps(prev), encoding="utf-8")
        e = self.stub({"/elokuvat/ohjelmistossa": LISTING,
                       "/elokuvat/70/the-invite": FOREIGN_FILM,
                       "/elokuvat/63/the-dog-stars": FOREIGN_FILM})
        realimp = importlib.import_module
        mod = type("M", (), {"__name__": "fakemod", "SITES": [site("niagara")],
                             "fetch_site": staticmethod(e.fetch_site)})
        importlib.import_module = lambda n: mod if n == "fakemod" else realimp(n)
        self.addCleanup(lambda: setattr(importlib, "import_module", realimp))
        self.assertEqual(run.main(["fakemod", "--half", "all"]), 1)
        after = json.loads((run.OUT / "area-cn-tampere.json").read_text(encoding="utf-8"))
        self.assertEqual(after, prev)

    def test_a_genuinely_empty_programme_is_the_platforms_empty_state(self):
        e = self.stub({"/elokuvat/ohjelmistossa": GENUINELY_EMPTY})
        with self.assertRaises(common.EmptyProgramme):
            e.fetch_site(site("niagara"), sleep=0)


# --- registry, accent, and what never reaches a page ----------------------------------------

class NiagaraRegistryTest(unittest.TestCase):

    def test_registry_and_sites_agree(self):
        import registry
        p = registry.by_id("niagara")
        self.assertEqual((p["label"], p["host"], p["module"], p["book"], p["accent"]),
                         ("Cinema Niagara", "cinemaniagara.fi", "etiketti", "buy", "#6A4FBF"))
        self.assertIn(p["where"], ("cloud", "local"))
        s = site("niagara")
        self.assertEqual([v["id"] for v in s["venues"]], ["cn-tampere"])
        self.assertEqual(s["venues"][0]["city"], "Tampere")
        self.assertEqual(s["base"], "https://cinemaniagara.fi")

    def test_the_venue_id_is_unique_across_adapters(self):
        import registry
        ids = [v["id"] for m in registry.modules()
               for st in importlib.import_module(m).SITES for v in st["venues"]]
        self.assertEqual(ids.count("cn-tampere"), 1)

    def test_the_accent_clears_finnkino_in_tampere_in_every_vision_model(self):
        """Tampere is the sixth two-chain city. The pair must not become the set's
        binding constraint: every model at or above the current worst same-city pair,
        and comfortably above the 3 px rule's floor."""
        import accent_check as A
        import registry
        niagara = registry.by_id("niagara")["accent"]
        finnkino = registry.by_id("finnkino")["accent"]
        pair = A.dE(niagara, finnkino)
        accents = {p["id"]: p["accent"] for p in registry.PROVIDERS}
        worst = min(min(A.dE(accents[a], accents[b]))
                    for _, a, b in A.shared_city_pairs() if a in accents and b in accents)
        for model, value in zip(("normal", "vienot", "machado"), pair):
            with self.subTest(model=model):
                self.assertGreaterEqual(value, worst)
                self.assertGreaterEqual(value, 40.0)
        self.assertNotIn(niagara, {v for k, v in accents.items() if k != "niagara"})

    def test_no_availability_state_reaches_a_page_or_its_json_ld(self):
        import build_pages as bp
        today = datetime.date(2026, 9, 3)
        show = {"eventId": "70", "title": "The Invite", "original": "", "len": "108",
                "rating": "K-12", "genres": "Draama, Komedia", "method": "Seniorikino · Q&A",
                "theatre": "Cinema Niagara", "aud": "", "start": "2026-09-03T18:45:00+03:00",
                "url": "https://cinemaniagara.fi/salikartta?id=53955", "img": "",
                "lang": "EN-A, ES-A, FI-S, SV-S", "soldOut": True, "price": "11€",
                "provider": "niagara", "venue": "cn-tampere"}
        days = {today.isoformat(): {"The Invite": [show]}}
        for lang in ("fi", "en"):
            with self.subTest(lang=lang):
                html = bp.page(
                    lang=lang, path_fi="/teatteri/x/", path_en="/en/theatre/x/",
                    title="X", desc="d", h1="h", sub="s", intro="i", days=days, today=today,
                    t=bp.L[lang], extra={}, gmap={}, city="Tampere", with_venue=False,
                    legend="", also="", og_image="/icon-512.png", app_href="/", area="x",
                    chain_css="")
                low = html.lower()
                for word in ("soldout", "sold out", "loppuunmyyty", "availability",
                             "paikkoja", "vapaana", "seats"):
                    self.assertNotIn(word, low, word)
                self.assertIn("salikartta?id=53955", html)
                self.assertIn("11", html)


if __name__ == "__main__":
    unittest.main()
