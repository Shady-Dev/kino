"""Bio Savoy, Mariehamn: the weekly schedule page and one page per film.

The fixtures follow `www.biosavoy.ax` as read on 2026-10-29: `/spelschema` with one
`schedule__day-heading` per day ("Torsdag <span>29/10</span>") and `show-row` links under
it, and `/film/{slug}` with a facts list, a lead and body, and its own schedule of panels
keyed by ISO date. Two halls and two days are in every fixture, and one film plays twice.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import biosavoy
import common
import enrich_tmdb
import synmerge

BASE = "https://www.biosavoy.ax"
TODAY = datetime.date(2026, 10, 29)


def row(slug, title, clock, hall="Sal 1"):
    chip = f'<span class="chip">{hall}</span>' if hall is not None else ""
    return (f'<li><a class="show-row show-row--link grid items-center gap-4" '
            f'href="/film/{slug}"><span class="show-row__time show-row__time--large">'
            f'{clock}</span><span class="show-row__title">{title}</span>'
            f'<span class="flex items-center gap-4">{chip}'
            f'<span class="show-row__arrow" aria-hidden="true">\u2192</span></span></a></li>')


def day(name, dm, *rows):
    return (f'<div><h2 class="schedule__day-heading flex items-baseline gap-3.5">{name} '
            f'<span>{dm}</span></h2><ul class="show-list">' + "".join(rows) + '</ul></div>')


def schedule(*days):
    return ('<html><body><main><section class="schedule " data-section="schedule">'
            '<h1 class="heading-lg">Spelschema</h1><div class="schedule__days flex flex-col">'
            + "".join(days) + '</div></section></main>'
            '<nav><ul><li><a class="flex items-center justify-between" href="/om-oss">'
            'Om oss</a></li></ul></nav></body></html>')


LISTING = schedule(
    day("Torsdag", "29/10",
        row("whalefall", "WHALEFALL", "18.00", "Sal 1"),
        row("street-fighter", "STREET FIGHTER", "18.15", "Sal 2")),
    day("Fredag", "30/10",
        row("lapin-sota", "LAPIN SOTA (Lapplandskriget)", "17.00", "Sal 1"),
        row("faret-shaun", "F\u00c5RET SHAUN", "18.00", "Sal 2"),
        row("whalefall", "WHALEFALL", "20.00", "Sal 1")),
)


def film_page(panels=(), speltid="1 h 48 min", age="Fr\u00e5n 16 \u00e5r", pris="15 \u20ac",
              lead="DCU sl\u00e4pper sin f\u00f6rsta skr\u00e4ckfilm.",
              body=("<p>Clayface handlar om Matt Hagen.</p>",), hero=("16", "1 h 48 min")):
    """A `/film/{slug}` page. `panels` is [(iso date, [(clock, hall, meta)])]. The hero
    line repeats some facts unlabelled, as the real page does, and is never the source."""
    facts = [("Genre", "Skr\u00e4ck"), ("Speltid", speltid), ("\u00c5ldersgr\u00e4ns", age),
             ("Salong", "Sal 2"), ("Pris", pris)]
    dl = "".join(f'<div class="film-facts__item"><dt class="label">{k}</dt>'
                 f'<dd class="film-facts__value">{v}</dd></div>'
                 for k, v in facts if v is not None)
    hero_html = "".join(f"<span>{x}</span>" for x in hero)
    about = ((f'<p class="film-about__lead">{lead}</p>' if lead is not None else "")
             + (f'<div class="film-about__body mt-8">{"".join(body)}</div>' if body else ""))
    tabs = "".join(
        f'<div class="schedule__panel" id="film-day-{d}" data-tab-panel>'
        f'<h3 class="schedule__day-heading schedule__day-heading--small">x</h3>'
        f'<ul class="show-list">'
        + "".join(f'<li class="show-row grid items-center gap-4">'
                  f'<span class="show-row__time">{c}</span><span class="min-w-0">'
                  f'<span class="show-row__title block">{h}</span>'
                  + (f'<span class="show-row__meta mt-1 block">{m}</span>' if m is not None
                     else "")
                  + '</span></li>' for c, h, m in rs)
        + '</ul></div>' for d, rs in panels)
    return ('<html><body><main><article class="film">'
            f'<div class="film-hero__meta">{hero_html}</div>'
            f'<section class="film-facts" aria-label="Fakta om filmen"><dl>{dl}</dl></section>'
            f'<section class="film-about container-narrow">{about}</section>'
            f'<section class="film-schedule" id="schema">{tabs}</section>'
            '</article></main></body></html>')


def pages(**over):
    out = {
        f"{BASE}/spelschema": LISTING,
        f"{BASE}/film/whalefall": film_page(
            [("2026-10-29", [("18.00", "Sal 1", "15 \u20ac")]),
             ("2026-10-30", [("20.00", "Sal 1", "15 \u20ac")])]),
        f"{BASE}/film/street-fighter": film_page(
            [("2026-10-29", [("18.15", "Sal 2", "15 \u20ac")])], speltid="2 h 5 min",
            age="Fr\u00e5n 12 \u00e5r"),
        f"{BASE}/film/lapin-sota": film_page(
            [("2026-10-30", [("17.00", "Sal 1", "15 \u20ac")])], speltid="2 h 35 min"),
        f"{BASE}/film/faret-shaun": film_page(
            [("2026-10-30", [("18.00", "Sal 2", "13 \u20ac")])], speltid="1 h 20 min",
            age="Till\u00e5ten f\u00f6r alla", pris="13 \u20ac",
            lead="Shaun \u00e4r tillbaka.", body=("<p>Om f\u00e5ren.</p>",
                                                     "<p>SVENSKT TAL!</p>")),
    }
    out.update({f"{BASE}{k}": v for k, v in over.items()})
    return out


class Served:
    """Stubs `biosavoy.get` and `time.sleep` for one test."""

    def __init__(self, test, served):
        self.calls, self.slept = [], []

        def get(url):
            self.calls.append(url)
            body = served.get(url)
            if isinstance(body, Exception):
                raise body
            if body is None:
                raise RuntimeError(f"unexpected fetch {url}")
            return body
        real_get, real_sleep = biosavoy.get, biosavoy.time.sleep
        biosavoy.get, biosavoy.time.sleep = get, self.slept.append
        test.addCleanup(lambda: setattr(biosavoy, "get", real_get))
        test.addCleanup(lambda: setattr(biosavoy.time, "sleep", real_sleep))


def run_site(test, **over):
    served = Served(test, pages(**over))
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        data = biosavoy.fetch_site(today=TODAY)
    return data["savoy-mariehamn"], out.getvalue(), served


class ScheduleTest(unittest.TestCase):
    def setUp(self):
        self.shows = biosavoy.parse(LISTING, TODAY)

    def test_every_row_under_every_day_is_read(self):
        self.assertEqual(len(self.shows), 5)
        self.assertEqual(sorted({s["eventId"] for s in self.shows}),
                         ["faret-shaun", "lapin-sota", "street-fighter", "whalefall"])

    def test_the_date_takes_its_year_from_the_weekday(self):
        """The heading prints "29/10" with no year. Torsdag selects 2026."""
        by = {(s["eventId"], s["start"][11:16]): s["start"] for s in self.shows}
        self.assertEqual(by[("whalefall", "18:00")], "2026-10-29T18:00:00+02:00")
        self.assertEqual(by[("lapin-sota", "17:00")], "2026-10-30T17:00:00+02:00")

    def test_a_week_across_new_year_lands_in_the_next_year(self):
        page = schedule(day("Torsdag", "31/12", row("a", "A", "18.00")),
                        day("Fredag", "1/1", row("b", "B", "18.00")))
        out = biosavoy.parse(page, datetime.date(2026, 12, 30))
        self.assertEqual([s["start"][:10] for s in out], ["2026-12-31", "2027-01-01"])

    def test_the_offset_follows_finnish_and_aland_summer_time(self):
        page = schedule(day("Fredag", "23/10", row("a", "A", "18.00")),
                        day("Fredag", "30/10", row("b", "B", "18.00")))
        out = biosavoy.parse(page, datetime.date(2026, 10, 22))
        self.assertEqual([s["start"][-6:] for s in out], ["+03:00", "+02:00"])

    def test_the_hall_comes_from_the_chip(self):
        by = {(s["eventId"], s["start"][11:16]): s["aud"] for s in self.shows}
        self.assertEqual(by[("whalefall", "18:00")], "Sal 1")
        self.assertEqual(by[("street-fighter", "18:15")], "Sal 2")

    def test_a_row_without_a_chip_has_no_hall(self):
        out = biosavoy.parse(schedule(day("Torsdag", "29/10",
                                          row("a", "A", "18.00", hall=None),
                                          row("b", "B", "19.00"))), TODAY)
        self.assertEqual([s["aud"] for s in out], ["", "Sal 1"])

    def test_the_title_is_the_row_title_with_its_own_case(self):
        self.assertIn("LAPIN SOTA (Lapplandskriget)", {s["title"] for s in self.shows})
        self.assertIn("F\u00c5RET SHAUN", {s["title"] for s in self.shows})

    def test_the_destination_is_the_films_https_page(self):
        for s in self.shows:
            self.assertEqual(s["url"], f"{BASE}/film/{s['eventId']}")

    def test_the_navigation_links_are_not_rows(self):
        self.assertNotIn("Om oss", {s["title"] for s in self.shows})

    def test_a_repeated_row_is_published_once(self):
        r = row("a", "A", "18.00")
        self.assertEqual(len(biosavoy.parse(schedule(day("Torsdag", "29/10", r, r)),
                                            TODAY)), 1)

    def test_the_same_minute_in_two_halls_is_two_screenings(self):
        out = biosavoy.parse(schedule(day("Torsdag", "29/10",
                                          row("a", "A", "18.00", "Sal 1"),
                                          row("a", "A", "18.00", "Sal 2"))), TODAY)
        self.assertEqual(sorted(s["aud"] for s in out), ["Sal 1", "Sal 2"])

    def test_a_colon_clock_is_read_as_well_as_a_dot(self):
        out = biosavoy.parse(schedule(day("Torsdag", "29/10", row("a", "A", "18:45"))),
                             TODAY)
        self.assertEqual(out[0]["start"][11:16], "18:45")

    def test_every_show_meets_the_contract(self):
        common.check_shows({biosavoy.VENUE["id"]: self.shows}, "biosavoy",
                           {biosavoy.VENUE["id"]})


class BrokenScheduleTest(unittest.TestCase):
    def test_a_page_without_the_schedule_section_fails(self):
        with self.assertRaises(RuntimeError) as cm:
            biosavoy.parse("<html><body><p>V\u00e4lkommen</p></body></html>", TODAY)
        self.assertNotIsInstance(cm.exception, common.EmptyProgramme)

    def test_days_with_no_row_fail_rather_than_empty_the_venue(self):
        with self.assertRaises(RuntimeError) as cm:
            biosavoy.parse(schedule(day("Torsdag", "29/10"), day("Fredag", "30/10")), TODAY)
        self.assertNotIsInstance(cm.exception, common.EmptyProgramme)

    def test_a_weekday_that_fits_no_year_fails_the_site(self):
        """29/10 is a Thursday in 2026. A Monday 29/10 inside the window does not exist."""
        with self.assertRaises(biosavoy.ShowRowError):
            biosavoy.parse(schedule(day("M\u00e5ndag", "29/10", row("a", "A", "18.00"))),
                           TODAY)

    def test_a_heading_that_is_no_swedish_weekday_fails_the_site(self):
        for name in ("Torstai", "Idag", ""):
            with self.subTest(name=name), self.assertRaises(biosavoy.ShowRowError):
                biosavoy.parse(schedule(day(name, "29/10", row("a", "A", "18.00"))), TODAY)

    def test_a_row_without_a_time_or_a_title_fails_the_site(self):
        for bad in (row("a", "A", "kv\u00e4ll"), row("a", "", "18.00")):
            with self.subTest(row=bad[-80:]), self.assertRaises(biosavoy.ShowRowError):
                biosavoy.parse(schedule(day("Torsdag", "29/10", bad,
                                            row("b", "B", "19.00"))), TODAY)


class SiteTest(unittest.TestCase):
    def test_one_venue_on_aland_keyed_under_its_official_name(self):
        """Åland's only official language is Swedish. A Finnish exonym would show
        untranslated in the Swedish interface."""
        self.assertEqual([v["city"] for v in biosavoy.SITES[0]["venues"]], ["Mariehamn"])

    def test_the_host_is_read_over_https(self):
        """The new site went live on 2026-10-28 with a certificate and redirects http."""
        self.assertEqual(biosavoy.BASE, "https://www.biosavoy.ax")
        self.assertEqual(biosavoy.SITES[0]["base"], biosavoy.BASE)


class AgeTest(unittest.TestCase):
    """Every wording read on 2026-10-29 across 19 film pages, and the ones refused."""

    def rating(self, age):
        return biosavoy.film_facts(film_page(age=age))["rating"]

    def test_from_n_years_is_k_n(self):
        for text, want in (("Fr\u00e5n 7 \u00e5r", "K-7"), ("Fr\u00e5n 12 \u00e5r", "K-12"),
                           ("Fr\u00e5n 16 \u00e5r", "K-16"), ("Fr\u00e5n 18 \u00e5r", "K-18"),
                           ("Till\u00e5ten fr\u00e5n 12 \u00e5r", "K-12"),
                           ("fr\u00e5n 16 \u00e5r", "K-16")):
            with self.subTest(text=text):
                self.assertEqual(self.rating(text), want)

    def test_allowed_for_all_is_s(self):
        self.assertEqual(self.rating("Till\u00e5ten f\u00f6r alla"), "S")

    def test_any_other_wording_publishes_nothing(self):
        for text in ("Rekommenderas fr\u00e5n 7 \u00e5r", "16", "\u00c5ldersgr\u00e4ns 12",
                     "Fr\u00e5n 12 \u00e5r i vuxens s\u00e4llskap", "Barntill\u00e5ten", "",
                     None):
            with self.subTest(text=text):
                self.assertEqual(self.rating(text), "")

    def test_the_unlabelled_hero_number_is_never_the_rating(self):
        page = film_page(age=None, hero=("16", "1 h 48 min"))
        self.assertEqual(biosavoy.film_facts(page)["rating"], "")


class RuntimeTest(unittest.TestCase):
    def length(self, speltid):
        return biosavoy.film_facts(film_page(speltid=speltid))["len"]

    def test_hours_and_minutes_become_minutes(self):
        for text, want in (("1 h 48 min", "108"), ("2 h 5 min", "125"), ("1 h 2 min", "62"),
                           ("2h 35min", "155")):
            with self.subTest(text=text):
                self.assertEqual(self.length(text), want)

    def test_a_placeholder_or_partial_value_publishes_nothing(self):
        for text in ("XX h 00 min", "ca 2 h", "108 min", "1 h 48 min / 2 h 10 min",
                     "ca 1 h 48 min", "", None):
            with self.subTest(text=text):
                self.assertEqual(self.length(text), "")


class ScreeningPriceTest(unittest.TestCase):
    """The price is the screening's own, from the film page's schedule row."""

    def prices(self, *rows, date="2026-10-29"):
        return biosavoy.screening_prices(film_page([(date, list(rows))]))

    def test_each_row_states_its_screenings_price(self):
        got = biosavoy.screening_prices(film_page(
            [("2026-10-31", [("14.00", "Sal 1", "13 \u20ac")]),
             ("2026-11-01", [("13.30", "Sal 1", "13 \u20ac"), ("20.15", "Sal 2", "15 \u20ac")])]))
        self.assertEqual(got, {("2026-10-31", "14:00", "Sal 1"): "13\u20ac",
                               ("2026-11-01", "13:30", "Sal 1"): "13\u20ac",
                               ("2026-11-01", "20:15", "Sal 2"): "15\u20ac"})

    def test_cents_are_kept_unless_they_are_zero(self):
        self.assertEqual(self.prices(("18.00", "Sal 1", "15,00 \u20ac")),
                         {("2026-10-29", "18:00", "Sal 1"): "15\u20ac"})
        self.assertEqual(self.prices(("18.00", "Sal 1", "13,50 \u20ac")),
                         {("2026-10-29", "18:00", "Sal 1"): "13.5\u20ac"})

    def test_anything_but_one_amount_publishes_nothing(self):
        """`hexed` printed a bare "13" in its facts on 2026-10-29. Without the euro sign the
        value is not stated as a price, and an unlabelled screening row says even less."""
        for meta in ("13", "15 \u20ac / 13 \u20ac", "Sluts\u00e5ld", "fr\u00e5n 13 \u20ac",
                     "", None):
            with self.subTest(meta=meta):
                self.assertEqual(self.prices(("18.00", "Sal 1", meta)),
                                 {("2026-10-29", "18:00", "Sal 1"): ""})

    def test_two_rows_for_one_screening_that_disagree_publish_neither(self):
        self.assertEqual(self.prices(("18.00", "Sal 1", "15 \u20ac"), ("18.00", "Sal 1", "13 \u20ac")),
                         {("2026-10-29", "18:00", "Sal 1"): ""})
        self.assertEqual(self.prices(("18.00", "Sal 1", "15 \u20ac"), ("18.00", "Sal 1", "15 \u20ac")),
                         {("2026-10-29", "18:00", "Sal 1"): "15\u20ac"})

    def test_the_film_level_price_is_not_read(self):
        """The facts list's "Pris" says nothing about a particular screening."""
        self.assertEqual(biosavoy.screening_prices(film_page([], pris="15 \u20ac")), {})


class SynopsisTest(unittest.TestCase):
    def facts(self, **kw):
        return biosavoy.film_facts(film_page(**kw))

    def test_the_lead_and_the_body_make_the_synopsis(self):
        self.assertEqual(self.facts()["syn"],
                         "DCU sl\u00e4pper sin f\u00f6rsta skr\u00e4ckfilm. "
                         "Clayface handlar om Matt Hagen.")

    def test_a_page_with_only_a_lead_has_that_as_its_synopsis(self):
        self.assertEqual(self.facts(body=())["syn"], "DCU sl\u00e4pper sin f\u00f6rsta skr\u00e4ckfilm.")

    def test_a_page_with_neither_has_none(self):
        self.assertEqual(self.facts(lead=None, body=())["syn"], "")

    def test_svenskt_tal_is_the_language_and_leaves_the_synopsis(self):
        f = self.facts(body=("<p>Om Pikkuli.</p>", "<p>SVENSKT TAL!</p>"))
        self.assertEqual((f["syn"], f["lang"]),
                         ("DCU sl\u00e4pper sin f\u00f6rsta skr\u00e4ckfilm. Om Pikkuli.", "SV-A"))

    def test_a_local_premiere_paragraph_leaves_the_synopsis(self):
        f = self.facts(lead=None, body=("<p>Om Digger.</p>", "<p>PREMI\u00c4R:<br>2.10 2026</p>"))
        self.assertEqual(f["syn"], "Om Digger.")

    def test_the_words_inside_a_sentence_stay(self):
        for kept in ("Svenskt tal och finsk text p\u00e5 alla visningar.",
                     "Filmen hade premi\u00e4r 2.10 2026 i Cannes.",
                     "Mellan 1986-1988 - Faith-eran - inleder filmen."):
            with self.subTest(kept=kept):
                f = self.facts(lead=None, body=(f"<p>{kept}</p>",))
                self.assertEqual((f["syn"], f["lang"]), (kept, ""))

    def test_markup_and_entities_are_flattened(self):
        f = self.facts(lead=None, body=("<p>En <em>ny</em> film&nbsp;om <a href=\"/x\">Laban</a>"
                                        "<br>och&amp;sp\u00f6ken.</p>",))
        self.assertEqual(f["syn"], "En ny film om Laban och&sp\u00f6ken.")


class FetchTest(unittest.TestCase):
    def test_one_request_per_distinct_film_after_the_schedule(self):
        shows, log, served = run_site(self)
        films = [c for c in served.calls if "/film/" in c]
        self.assertEqual(served.calls[0], f"{BASE}/spelschema")
        self.assertEqual(len(shows), 5)
        self.assertEqual(sorted(films), sorted(set(films)))
        self.assertEqual(len(films), 4)

    def test_the_film_pages_are_paced(self):
        _, _, served = run_site(self)
        self.assertEqual(len(served.slept), 3)
        self.assertTrue(all(s > 0 for s in served.slept))

    def test_every_screening_carries_its_own_price(self):
        shows, log, _ = run_site(self)
        got = {(s["eventId"], s["start"][:16]): s["price"] for s in shows}
        self.assertEqual(got[("faret-shaun", "2026-10-30T18:00")], "13\u20ac")
        self.assertEqual(got[("whalefall", "2026-10-30T20:00")], "15\u20ac")
        self.assertIn("5 priced", log)

    def test_a_screening_the_film_page_does_not_list_has_no_price(self):
        shows, _, _ = run_site(self, **{"/film/whalefall": film_page(
            [("2026-10-29", [("18.00", "Sal 1", "15 \u20ac")])])})
        got = {s["start"][:16]: s["price"] for s in shows if s["eventId"] == "whalefall"}
        self.assertEqual(got, {"2026-10-29T18:00": "15\u20ac", "2026-10-30T20:00": ""})

    def test_a_film_page_listing_another_hall_gives_no_price(self):
        shows, _, _ = run_site(self, **{"/film/street-fighter": film_page(
            [("2026-10-29", [("18.15", "Sal 1", "15 \u20ac")])])})
        sf = next(s for s in shows if s["eventId"] == "street-fighter")
        self.assertEqual(sf["price"], "")

    def test_a_film_page_that_fails_costs_that_film_and_not_the_schedule(self):
        shows, log, _ = run_site(self, **{"/film/lapin-sota": RuntimeError("HTTP Error 500")})
        ls = next(s for s in shows if s["eventId"] == "lapin-sota")
        self.assertEqual((ls["price"], ls["len"], ls["rating"]), ("", "", ""))
        self.assertNotIn("_syn", ls)
        self.assertEqual(len(shows), 5)
        self.assertIn("film page lapin-sota", log)

    def test_the_facts_reach_every_screening_of_their_film_only(self):
        shows, _, _ = run_site(self)
        got = {}
        for s in shows:
            got.setdefault(s["eventId"], set()).add((s["len"], s["rating"], s["lang"]))
        self.assertEqual(got, {"whalefall": {("108", "K-16", "")},
                               "street-fighter": {("125", "K-12", "")},
                               "lapin-sota": {("155", "K-16", "")},
                               "faret-shaun": {("80", "S", "SV-A")}})

    def test_the_film_pages_are_bounded_by_the_shared_budget(self):
        saved = common.PAGE_BUDGET
        common.PAGE_BUDGET = 2
        self.addCleanup(lambda: setattr(common, "PAGE_BUDGET", saved))
        shows, log, served = run_site(self)
        self.assertEqual(len([c for c in served.calls if "/film/" in c]), 2)
        self.assertEqual(len(shows), 5)
        self.assertIn("page budget", log)
        self.assertEqual({s["eventId"] for s in shows if not s["price"]},
                         {"street-fighter", "whalefall"})

    def test_the_synopsis_is_declared_swedish(self):
        shows, log, _ = run_site(self)
        shaun = next(s for s in shows if s["eventId"] == "faret-shaun")
        self.assertEqual(shaun["_syn"], {"sv": "Shaun \u00e4r tillbaka. Om f\u00e5ren."})
        self.assertIn("5 with a Swedish synopsis", log)

    def test_synmerge_files_it_in_the_swedish_slot(self):
        shows, _, _ = run_site(self)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = pathlib.Path(tmp.name)
        synmerge.reset()
        self.addCleanup(synmerge.reset)
        with contextlib.redirect_stdout(io.StringIO()):
            synmerge.merge(out, {"savoy-mariehamn": shows}, "biosavoy", 0)
        films = json.loads((out / "films-extra.json").read_text())["films"]
        entry = films[synmerge.norm("F\u00c5RET SHAUN")]["s"]
        self.assertEqual((entry["sv"], entry["fi"]), ("Shaun \u00e4r tillbaka. Om f\u00e5ren.", ""))

    def test_every_show_meets_the_contract_with_the_helper_stripped(self):
        shows, _, _ = run_site(self)
        synmerge.strip_helpers(shows)
        common.check_shows({"savoy-mariehamn": shows}, "biosavoy", {"savoy-mariehamn"})


class RatingPrecedenceTest(unittest.TestCase):
    """The cinema's own age limit outranks the shared classification pass."""

    TABLE = {7: {"rating": "K-16", "runtimes": {108}}}

    def test_a_rating_the_cinema_published_is_never_replaced(self):
        self.assertIsNone(enrich_tmdb.borrowed_rating(
            {"rating": "S", "tmdbId": 7, "len": "108"}, self.TABLE))

    def test_a_blank_rating_may_still_be_filled(self):
        self.assertEqual(enrich_tmdb.borrowed_rating(
            {"rating": "", "tmdbId": 7, "len": "108"}, self.TABLE), "K-16")


if __name__ == "__main__":
    unittest.main()
