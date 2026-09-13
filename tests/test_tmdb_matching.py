"""How the TMDB pass uses an original title and a published year, and when it re-judges.

Kino Regina publishes repertory films under Finnish distributor titles TMDB has never
heard of ("Rakasta tai tuhoudu" is "All Night Long", 1962), and TMDB holds several films
under one title. Before this the search saw the Finnish title alone and the first exact
hit in popularity order won. Now a nonblank `original` is a search candidate, a published
year filters the search and decides among exact hits, and an exact match judged before
that evidence existed is judged once more.

The pass needs a token and a third party, so TMDB is a dispatch on the URL: the search
table is keyed on the query and the year filter the code actually sent.
"""
import contextlib
import datetime
import io
import json
import os
import pathlib
import tempfile
import types
import unittest
import urllib.parse

import _ctx                                                # noqa: F401
import enrich_tmdb


def hit(mid, title, year, original=None):
    return {"id": mid, "title": title, "original_title": original or title,
            "release_date": f"{year}-05-01" if year else "", "poster_path": f"/{mid}.jpg"}


ALL_NIGHT_1981 = hit(22, "All Night Long", 1981)
ALL_NIGHT_1962 = hit(37038, "All Night Long", 1962)


class QueriesTest(unittest.TestCase):

    def test_the_original_title_is_searched_after_the_published_one(self):
        q = enrich_tmdb.queries("Rakasta tai tuhoudu", original="All Night Long")
        self.assertEqual(q[:2], ["Rakasta tai tuhoudu", "All Night Long"])

    def test_no_original_leaves_the_candidates_as_they_were(self):
        for blank in (None, "", "  "):
            with self.subTest(original=blank):
                self.assertEqual(enrich_tmdb.queries("Dyyni: Osa kolme", original=blank),
                                 enrich_tmdb.queries("Dyyni: Osa kolme"))

    def test_an_original_equal_to_the_title_is_not_searched_twice(self):
        """Regina publishes "The Music Lovers" under that title and names it as the
        original too. Dedup is case-insensitive, like the rest of the list."""
        q = enrich_tmdb.queries("The Music Lovers", original="THE MUSIC LOVERS")
        self.assertEqual(q.count("The Music Lovers"), 1)
        self.assertNotIn("THE MUSIC LOVERS", q)
        self.assertEqual(len(q), len(set(x.lower() for x in q)))

    def test_the_alias_string_still_goes_first(self):
        q = enrich_tmdb.queries("Autot (re-release)", alias="Cars", original="Cars")
        self.assertEqual(q[0], "Cars")
        self.assertEqual(q.count("Cars"), 1)


class PublishedYearTest(unittest.TestCase):

    def test_the_year_field_is_read(self):
        self.assertEqual(enrich_tmdb.published_year({"title": "X", "year": "1962"}), "1962")

    def test_a_trailing_year_in_the_title_is_kept_before_cleanup_strips_it(self):
        """clean() drops "(1996)" from the search string; the year is read first."""
        show = {"title": "Trainspotting (1996)"}
        self.assertEqual(enrich_tmdb.published_year(show), "1996")
        self.assertEqual(enrich_tmdb.clean(show["title"]), "Trainspotting")

    def test_the_screening_date_is_never_the_year(self):
        show = {"title": "Rakasta tai tuhoudu", "start": "2026-09-13T18:30:00+03:00"}
        self.assertEqual(enrich_tmdb.published_year(show), "")

    def test_only_a_four_digit_year_counts(self):
        for bad in ("", "abc", "199", "19621", 1962.5, None):
            with self.subTest(year=bad):
                self.assertEqual(enrich_tmdb.published_year({"title": "X", "year": bad}), "")

    def test_a_year_in_the_middle_of_a_title_is_not_a_year(self):
        self.assertEqual(enrich_tmdb.published_year({"title": "2001: Avaruusseikkailu"}), "")


class GatherTest(unittest.TestCase):

    def test_agreeing_shows_supply_the_evidence(self):
        shows = [{"title": "Rakasta tai tuhoudu", "original": "All Night Long", "year": "1962"},
                 {"title": "Rakasta tai tuhoudu", "original": "All Night Long", "year": "1962"}]
        f = enrich_tmdb.gather(shows)["rakasta tai tuhoudu"]
        self.assertEqual((f["t"], f["o"], f["y"]),
                         ("Rakasta tai tuhoudu", "All Night Long", "1962"))

    def test_disagreeing_shows_supply_none(self):
        """Two chains, two originals or two years under one title: no evidence, and the
        search runs on the title alone as before."""
        shows = [{"title": "Nosferatu", "original": "Nosferatu", "year": "1922"},
                 {"title": "Nosferatu", "original": "Nosferatu: A Symphony", "year": "2024"}]
        f = enrich_tmdb.gather(shows)["nosferatu"]
        self.assertEqual((f["o"], f["y"]), ("", ""))

    def test_a_show_with_neither_field_is_older_data_and_still_a_title(self):
        shows = [{"title": "Old Film", "start": "2026-09-02T18:00:00+03:00"}]
        f = enrich_tmdb.gather(shows)["old film"]
        self.assertEqual((f["t"], f["o"], f["y"]), ("Old Film", "", ""))

    def test_blank_fields_do_not_veto_a_chain_that_publishes_them(self):
        shows = [{"title": "X", "original": "", "year": ""},
                 {"title": "X", "original": "Y", "year": "1990"}]
        f = enrich_tmdb.gather(shows)["x"]
        self.assertEqual((f["o"], f["y"]), ("Y", "1990"))


class PickTest(unittest.TestCase):

    def test_the_year_decides_among_exact_hits(self):
        """TMDB's order puts the 1981 film first. The cinema said 1962."""
        h, exact = enrich_tmdb.pick([ALL_NIGHT_1981, ALL_NIGHT_1962], "All Night Long", "1962")
        self.assertEqual((h["id"], exact), (37038, True))

    def test_without_a_year_the_first_exact_hit_wins_as_before(self):
        h, exact = enrich_tmdb.pick([ALL_NIGHT_1981, ALL_NIGHT_1962], "All Night Long")
        self.assertEqual((h["id"], exact), (22, True))

    def test_an_exact_title_from_another_decade_is_not_exact(self):
        """Not settled by popularity: the hit comes back as weak, so no tmdbId and no
        merge, and the log says why."""
        h, exact = enrich_tmdb.pick([ALL_NIGHT_1981], "All Night Long", "1962")
        self.assertEqual((h["id"], exact), (22, False))

    def test_a_year_off_by_one_is_the_same_film(self):
        h, exact = enrich_tmdb.pick([hit(5, "Käpy selän alla", 1967)], "Käpy selän alla", "1966")
        self.assertEqual((h["id"], exact), (5, True))
        _, exact = enrich_tmdb.pick([hit(5, "Käpy selän alla", 1968)], "Käpy selän alla", "1966")
        self.assertFalse(exact)

    def test_a_hit_without_a_release_date_cannot_contradict_the_year(self):
        h, exact = enrich_tmdb.pick([hit(9, "Obscure", None)], "Obscure", "1950")
        self.assertEqual((h["id"], exact), (9, True))

    def test_the_year_itself_beats_a_neighbouring_year_in_either_order(self):
        hits = [hit(1963001, "All Night Long", 1963), ALL_NIGHT_1962]
        for order in (hits, list(reversed(hits))):
            h, exact = enrich_tmdb.pick(order, "All Night Long", "1962")
            self.assertEqual((h["id"], exact), (37038, True))

    def test_two_films_of_the_same_title_and_year_are_a_tie_and_not_exact(self):
        """Whatever order TMDB lists them in: an unresolved tie stays weak, so no tmdbId,
        no merge, and the entry is dropped and searched again next run."""
        hits = [hit(101, "Remake", 1990), hit(202, "Remake", 1990)]
        for order in (hits, list(reversed(hits))):
            h, exact = enrich_tmdb.pick(order, "Remake", "1990")
            self.assertFalse(exact)
            self.assertIn(h["id"], (101, 202))

    def test_the_published_original_title_breaks_a_same_year_tie(self):
        hits = [hit(555, "Rakasta tai tuhoudu", 1962, original="Toute la nuit"),
                hit(37038, "Rakasta tai tuhoudu", 1962, original="All Night Long")]
        for order in (hits, list(reversed(hits))):
            h, exact = enrich_tmdb.pick(order, "Rakasta tai tuhoudu", "1962",
                                        original="All Night Long")
            self.assertEqual((h["id"], exact), (37038, True))

    def test_no_exact_title_is_the_popularity_fallback_as_before(self):
        h, exact = enrich_tmdb.pick([hit(1, "Mother Mary", 2025)], "Mother", "2009")
        self.assertEqual((h["id"], exact), (1, False))


class ReconsiderTest(unittest.TestCase):
    """Which exact matches a pass judges again, and how many."""

    def entry(self, mid, **over):
        e = {"r": 7.0, "n": 100, "v": "k", "x": True, "g": [18], "i": mid,
             "c": "2026-09-01", "fi": "", "en": "", "p": "/p.jpg"}
        e.update(over)
        return e

    def facts(self, **years):
        return {k: {"t": k, "o": "", "y": y} for k, y in years.items()}

    def test_new_year_evidence_re_judges_an_exact_match_made_without_it(self):
        cache = {"a": self.entry(22)}                       # no `y`: judged before the year
        due, held = enrich_tmdb.reconsider(self.facts(a="1962"), cache, {})
        self.assertEqual((due, held), (["a"], 0))

    def test_a_match_judged_on_the_same_evidence_is_left_alone(self):
        cache = {"a": self.entry(37038, o="", y="1962")}
        self.assertEqual(enrich_tmdb.reconsider(self.facts(a="1962"), cache, {}), ([], 0))

    def test_no_evidence_now_means_nothing_to_re_judge(self):
        cache = {"a": self.entry(22)}
        self.assertEqual(enrich_tmdb.reconsider(self.facts(a=""), cache, {}), ([], 0))

    def test_a_manual_alias_is_never_re_judged(self):
        cache = {"a": self.entry(240)}
        self.assertEqual(enrich_tmdb.reconsider(self.facts(a="1974"), cache, {"a": "240"}),
                         ([], 0))
        self.assertEqual(enrich_tmdb.reconsider(self.facts(a="1974"), cache, {"a": "Cars"}),
                         ([], 0))

    def test_a_weak_entry_is_not_this_list(self):
        """Weak ids are dropped on every load, so they already see the new candidates."""
        cache = {"w": self.entry(22, x=False)}
        self.assertEqual(enrich_tmdb.reconsider(self.facts(w="1962"), cache, {}), ([], 0))

    def test_an_unmatched_entry_is_re_judged_when_evidence_arrives(self):
        """A title with no id is searched once a day; one whose original title and year
        arrive after today's search would otherwise wait until tomorrow. Legacy entries
        without `o`/`y` count as judged on nothing."""
        cache = {"n": self.entry("", x=False)}
        self.assertEqual(enrich_tmdb.reconsider(self.facts(n="1962"), cache, {}), (["n"], 0))
        legacy = {"n": {"r": 0, "n": 0, "v": "", "x": False, "g": [], "i": "", "c": "2026-09-13",
                        "fi": "", "en": "", "p": ""}}
        facts = {"n": {"t": "n", "o": "All Night Long", "y": ""}}
        self.assertEqual(enrich_tmdb.reconsider(facts, legacy, {}), (["n"], 0))

    def test_an_unmatched_entry_judged_on_the_same_evidence_is_left_to_its_daily_retry(self):
        cache = {"n": self.entry("", x=False, o="all night long", y="1962")}
        facts = {"n": {"t": "n", "o": "All Night Long", "y": "1962"}}
        self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), ([], 0))
        self.assertEqual(enrich_tmdb.reconsider(self.facts(n=""), {"n": self.entry("", x=False)}, {}),
                         ([], 0), "no evidence now: nothing to re-judge")

    def test_exact_and_unmatched_entries_share_one_budget_in_key_order(self):
        cache = {"a": self.entry(1), "b": self.entry("", x=False), "c": self.entry(""), "d": self.entry(3)}
        del cache["c"]["x"]; cache["c"]["x"] = False
        due, held = enrich_tmdb.reconsider(self.facts(a="1", b="2", c="3", d="4"), cache, {}, budget=2)
        self.assertEqual((due, held), (["a", "b"], 2))
        # The deferred ones are untouched, so the next pass picks them up.
        due2, held2 = enrich_tmdb.reconsider(self.facts(c="3", d="4"), cache, {}, budget=2)
        self.assertEqual((due2, held2), (["c", "d"], 0))

    def test_the_budget_bounds_a_pass_and_reports_the_rest_in_key_order(self):
        cache = {k: self.entry(1) for k in ("c", "a", "b")}
        due, held = enrich_tmdb.reconsider(self.facts(a="1", b="2", c="3"), cache, {}, budget=2)
        self.assertEqual((due, held), (["a", "b"], 1))

    def test_original_title_evidence_counts_too(self):
        cache = {"a": self.entry(22, o="", y="")}
        facts = {"a": {"t": "a", "o": "All Night Long", "y": ""}}
        self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), (["a"], 0))


class MainHarness(unittest.TestCase):
    """The whole pass, TMDB stubbed on the URL. `table` maps (query, year filter) to hits;
    an unknown pair answers nothing, which is what TMDB does for a Finnish title."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)
        for attr, value in (("DATA", self.dir), ("CACHE", self.dir / "tmdb-titles.json"),
                            ("GENRES", self.dir / "tmdb-genres.json"),
                            ("EXTRA", self.dir / "films-extra.json"),
                            ("ALIAS_FILE", self.dir / "tmdb-aliases.json")):
            saved = getattr(enrich_tmdb, attr)
            setattr(enrich_tmdb, attr, value)
            self.addCleanup(lambda a=attr, v=saved: setattr(enrich_tmdb, a, v))
        real_time = enrich_tmdb.time
        enrich_tmdb.time = types.SimpleNamespace(sleep=lambda *_: None)
        self.addCleanup(lambda: setattr(enrich_tmdb, "time", real_time))
        saved_token = os.environ.get("TMDB_TOKEN")
        os.environ["TMDB_TOKEN"] = "test-token"
        self.addCleanup(lambda: (os.environ.__setitem__("TMDB_TOKEN", saved_token)
                                 if saved_token is not None
                                 else os.environ.pop("TMDB_TOKEN", None)))
        self.today = datetime.date.today().isoformat()
        self.searches = []

    def shows(self, *rows):
        base = {"start": "2026-09-13T18:30:00+03:00", "provider": "zz", "venue": "zz"}
        (self.dir / "area-zz.json").write_text(json.dumps({
            "generated": self.today, "dates": [], "horizon": "",
            "shows": [{**base, **r} for r in rows]}), encoding="utf-8")

    def cache_write(self, cache):
        (self.dir / "tmdb-titles.json").write_text(json.dumps(cache), encoding="utf-8")

    def cache(self):
        return json.loads((self.dir / "tmdb-titles.json").read_text(encoding="utf-8"))

    def run_main(self, table):
        def fake_get(url, headers, timeout=25):
            if "/genre/movie/list" in url:
                return {"genres": [{"id": 18, "name": "Draama"}]}
            if "/search/movie" in url:
                q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
                key = (q["query"][0], (q.get("primary_release_year") or [""])[0])
                self.searches.append(key)
                return {"results": table.get(key, [])}
            if url.endswith("/videos"):
                return {"results": []}
            return {"overview": "Teksti", "vote_count": 900, "vote_average": 7.5,
                    "genres": [{"id": 18}]}
        real = enrich_tmdb.get
        enrich_tmdb.get = fake_get
        self.addCleanup(lambda: setattr(enrich_tmdb, "get", real))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = enrich_tmdb.main()
        self.assertEqual(code, 0)
        return buf.getvalue()


class MainPathTest(MainHarness):

    # 1. an original title enables the match
    def test_an_original_title_finds_a_film_the_finnish_title_cannot(self):
        self.shows({"title": "Rakasta tai tuhoudu", "original": "All Night Long"})
        self.run_main({("All Night Long", ""): [ALL_NIGHT_1962]})
        e = self.cache()["rakasta tai tuhoudu"]
        self.assertEqual((e["i"], e["x"]), (37038, True))
        self.assertEqual(self.searches[:2], [("Rakasta tai tuhoudu", ""), ("All Night Long", "")])
        self.assertEqual((e["o"], e["y"]), ("all night long", ""), "the evidence used is recorded")

    # 2. duplicate candidates are searched once
    def test_an_original_equal_to_the_title_costs_no_second_search(self):
        self.shows({"title": "The Music Lovers", "original": "The Music Lovers", "year": "1970"})
        self.run_main({("The Music Lovers", "1970"): [hit(3, "The Music Lovers", 1971)]})
        self.assertEqual(self.searches.count(("The Music Lovers", "1970")), 1)
        self.assertEqual(self.cache()["the music lovers"]["i"], 3)

    # 3. films sharing a title, different years
    def test_the_published_year_filters_the_search_and_picks_the_right_film(self):
        self.shows({"title": "All Night Long", "year": "1962"})
        self.run_main({("All Night Long", "1962"): [ALL_NIGHT_1962],
                       ("All Night Long", ""): [ALL_NIGHT_1981, ALL_NIGHT_1962]})
        e = self.cache()["all night long"]
        self.assertEqual((e["i"], e["x"], e["y"]), (37038, True, "1962"))
        self.assertEqual(self.searches, [("All Night Long", "1962")], "one filtered search settled it")

    # 4. no original, no year: as before
    def test_without_evidence_the_search_is_unfiltered_and_the_first_exact_hit_wins(self):
        self.shows({"title": "All Night Long"})
        self.run_main({("All Night Long", ""): [ALL_NIGHT_1981, ALL_NIGHT_1962]})
        e = self.cache()["all night long"]
        self.assertEqual((e["i"], e["x"]), (22, True))
        self.assertTrue(all(y == "" for _, y in self.searches), self.searches)

    # 5. the filtered search returns nothing: unfiltered retry, still held to the year
    def test_a_year_filtered_miss_retries_unfiltered_and_accepts_a_year_off_by_one(self):
        self.shows({"title": "Käpy selän alla", "year": "1966"})
        self.run_main({("Käpy selän alla", ""): [hit(5, "Käpy selän alla", 1967)]})
        e = self.cache()["käpy selän alla"]
        self.assertEqual((e["i"], e["x"]), (5, True))
        self.assertEqual(self.searches[:2], [("Käpy selän alla", "1966"), ("Käpy selän alla", "")])

    # 6. ambiguous: exact titles, none of the published year
    def test_an_exact_title_from_the_wrong_decade_is_weak_and_logged(self):
        self.shows({"title": "All Night Long", "year": "1962"})
        out = self.run_main({("All Night Long", ""): [ALL_NIGHT_1981, hit(8, "All Night Long", 2010)]})
        e = self.cache()["all night long"]
        self.assertEqual((e["i"], e["x"]), (22, False), "kept as a weak fallback, not a match")
        self.assertIn("year mismatch, exact title refused (1): All Night Long (1962) -> "
                      "All Night Long (1981)", out)
        self.assertNotIn("weak match, no exact title", out)

    def test_a_same_year_tie_is_cached_weak_and_logged_as_a_tie(self):
        self.shows({"title": "Remake", "year": "1990"})
        out = self.run_main({("Remake", "1990"): [hit(101, "Remake", 1990), hit(202, "Remake", 1990)]})
        e = self.cache()["remake"]
        self.assertFalse(e["x"])
        self.assertIn("several films match the title and year, none trusted (1): "
                      "Remake (1990) -> Remake (1990)", out)
        self.assertNotIn("weak match, no exact title", out)

    # 7. new evidence re-judges a cached exact match
    def test_a_cached_exact_match_is_re_judged_when_the_year_arrives(self):
        self.shows({"title": "All Night Long", "year": "1962"})
        self.cache_write({"all night long": {
            "r": 6.0, "n": 300, "v": "k", "x": True, "g": [18], "i": 22,
            "c": self.today, "a": self.today, "fi": "Vanha", "en": "Old", "p": "/22.jpg"}})
        out = self.run_main({("All Night Long", "1962"): [ALL_NIGHT_1962]})
        e = self.cache()["all night long"]
        self.assertEqual((e["i"], e["x"], e["y"]), (37038, True, "1962"))
        self.assertIn("re-judging 1 title(s) on new title or year evidence (1 exact match(es), 0 unmatched)", out)

    def test_a_re_judged_match_is_not_re_judged_again_next_run(self):
        self.shows({"title": "All Night Long", "year": "1962"})
        self.cache_write({"all night long": {
            "r": 6.0, "n": 300, "v": "k", "x": True, "g": [18], "i": 22,
            "c": self.today, "fi": "", "en": "", "p": ""}})
        self.run_main({("All Night Long", "1962"): [ALL_NIGHT_1962]})
        n = len(self.searches)
        out = self.run_main({("All Night Long", "1962"): [ALL_NIGHT_1962]})
        self.assertEqual(len(self.searches), n, "the second pass searched again")
        self.assertNotIn("re-judging", out)

    # 8. manual overrides
    def test_an_alias_id_is_neither_re_judged_nor_searched(self):
        self.shows({"title": "Kummisetä osa II", "year": "1974"})
        (self.dir / "tmdb-aliases.json").write_text(json.dumps({"kummisetä osa ii": "240"}))
        self.cache_write({"kummisetä osa ii": {
            "r": 8.5, "n": 12000, "v": "k", "x": True, "g": [18], "i": 240,
            "c": self.today, "fi": "", "en": "", "p": ""}})
        out = self.run_main({})
        self.assertEqual(self.cache()["kummisetä osa ii"]["i"], 240)
        self.assertEqual(self.searches, [])
        self.assertNotIn("re-judging", out)

    def test_an_alias_search_string_is_never_filtered_by_the_year(self):
        self.shows({"title": "Autot (uudelleenjulkaisu)", "year": "2026"})
        (self.dir / "tmdb-aliases.json").write_text(json.dumps({"autot uudelleenjulkaisu": "Cars"}))
        self.run_main({("Cars", ""): [hit(920, "Autot", 2006, original="Cars")]})
        self.assertEqual(self.searches[0], ("Cars", ""))
        self.assertEqual(self.cache()["autot uudelleenjulkaisu"]["i"], 920)

    # 10. older data
    def test_shows_without_the_optional_fields_still_enrich(self):
        self.shows({"title": "Old Film"}, {"title": "Other Film"})
        self.run_main({("Old Film", ""): [hit(1, "Old Film", 2001)],
                       ("Other Film", ""): [hit(2, "Other Film", 2002)]})
        c = self.cache()
        self.assertEqual((c["old film"]["i"], c["other film"]["i"]), (1, 2))
        self.assertEqual((c["old film"]["o"], c["old film"]["y"]), ("", ""))


class FixedDate(datetime.date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 13)


class SameDayReconsiderTest(MainHarness):
    """The gap the three Regina films fell into on 2026-09-13, on a fixed date: a title
    searched without result this morning, whose original title and year the local run
    published at noon, is searched again in the afternoon run."""

    TODAY = "2026-09-13"

    def setUp(self):
        super().setUp()
        real = enrich_tmdb.datetime
        enrich_tmdb.datetime = types.SimpleNamespace(date=FixedDate)
        self.addCleanup(lambda: setattr(enrich_tmdb, "datetime", real))

    def unmatched(self, day, **over):
        e = {"r": 0, "n": 0, "v": "", "x": False, "g": [], "i": "", "c": day, "a": "",
             "fi": "", "en": "", "p": ""}
        e.update(over)
        return e

    def test_an_unmatched_title_checked_today_is_searched_again_when_evidence_arrives(self):
        self.shows({"title": "Rakasta tai tuhoudu", "original": "All Night Long", "year": "1962"})
        self.cache_write({"rakasta tai tuhoudu": self.unmatched(self.TODAY)})
        out = self.run_main({("All Night Long", "1962"): [ALL_NIGHT_1962]})
        self.assertIn("re-judging 1 title(s) on new title or year evidence "
                      "(0 exact match(es), 1 unmatched)", out)
        e = self.cache()["rakasta tai tuhoudu"]
        self.assertEqual((e["i"], e["x"], e["o"], e["y"]), (37038, True, "all night long", "1962"))
        self.assertIn(("Rakasta tai tuhoudu", "1962"), self.searches)

    def test_a_failed_retry_records_the_evidence_and_is_not_retried_again_that_day(self):
        self.shows({"title": "Prinssi ja revyytyttö", "original": "The Prince and the Showgirl",
                    "year": "1957"})
        self.cache_write({"prinssi ja revyytyttö": self.unmatched(self.TODAY)})
        self.run_main({})                                   # TMDB answers nothing
        e = self.cache()["prinssi ja revyytyttö"]
        self.assertEqual((e["i"], e["o"], e["y"]),
                         ("", "the prince and the showgirl", "1957"))
        self.assertEqual(e["c"], self.TODAY)
        n = len(self.searches)
        out = self.run_main({})                             # same day, same evidence
        self.assertEqual(len(self.searches), n, "searched again with nothing new")
        self.assertNotIn("re-judging", out)

    def test_an_unchanged_unmatched_title_keeps_its_daily_retry(self):
        self.shows({"title": "Bussipysäkki"})
        self.cache_write({"bussipysäkki": self.unmatched("2026-09-12"),
                          "other": self.unmatched(self.TODAY)})
        self.shows({"title": "Bussipysäkki"}, {"title": "Other"})
        out = self.run_main({})
        self.assertIn(("Bussipysäkki", ""), self.searches, "yesterday's miss is retried")
        self.assertNotIn(("Other", ""), self.searches, "today's miss waits for tomorrow")
        self.assertNotIn("re-judging", out)

    def test_a_deferred_title_keeps_its_old_evidence_and_is_taken_next_pass(self):
        real = enrich_tmdb.RECONSIDER_BUDGET
        enrich_tmdb.RECONSIDER_BUDGET = 1
        self.addCleanup(lambda: setattr(enrich_tmdb, "RECONSIDER_BUDGET", real))
        self.shows({"title": "Aaa", "year": "1962"}, {"title": "Bbb", "year": "1957"})
        self.cache_write({"aaa": self.unmatched(self.TODAY), "bbb": self.unmatched(self.TODAY)})
        out = self.run_main({("Aaa", "1962"): [hit(1, "Aaa", 1962)], ("Bbb", "1957"): [hit(2, "Bbb", 1957)]})
        self.assertIn("1 wait for the next run", out)
        c = self.cache()
        self.assertEqual(c["aaa"]["i"], 1)
        self.assertEqual((c["bbb"]["i"], c["bbb"].get("y")), ("", None), "deferred: untouched")
        out = self.run_main({("Aaa", "1962"): [hit(1, "Aaa", 1962)], ("Bbb", "1957"): [hit(2, "Bbb", 1957)]})
        self.assertIn("re-judging 1 title(s)", out)
        self.assertEqual(self.cache()["bbb"]["i"], 2)

    def test_an_alias_and_a_settled_exact_match_are_left_alone(self):
        self.shows({"title": "Kummisetä osa II", "year": "1974"}, {"title": "Settled", "year": "1990"})
        (self.dir / "tmdb-aliases.json").write_text(json.dumps({"kummisetä osa ii": "240"}))
        self.cache_write({
            "kummisetä osa ii": {"r": 8.5, "n": 12000, "v": "k", "x": True, "g": [18], "i": 240,
                                 "c": self.TODAY, "fi": "", "en": "", "p": ""},
            "settled": {"r": 7.0, "n": 100, "v": "k", "x": True, "g": [18], "i": 5,
                        "c": self.TODAY, "fi": "", "en": "", "p": "", "o": "", "y": "1990"}})
        out = self.run_main({})
        self.assertEqual(self.searches, [])
        self.assertNotIn("re-judging", out)


if __name__ == "__main__":
    unittest.main()
