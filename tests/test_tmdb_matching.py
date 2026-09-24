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
from unittest import mock
import urllib.parse

import _ctx                                                # noqa: F401
import enrich_tmdb


def hit(mid, title, year, original=None):
    return {"id": mid, "title": title, "original_title": original or title,
            "release_date": f"{year}-05-01" if year else "", "poster_path": f"/{mid}.jpg"}


ALL_NIGHT_1981 = hit(22, "All Night Long", 1981)
ALL_NIGHT_1962 = hit(37038, "All Night Long", 1962)

# Cinema Sheryl, 2026-09-24: 96 minutes, no year. Under fi-FI TMDB titles Wong Kar-Wai's
# film "Happy Together - viimeinen tango Buenos Airesissa", so only en-US offers it.
HAPPY_1989 = hit(55059, "Happy Together", 1989)
HAPPY_1997 = hit(18329, "Happy Together", 1997, original="\u6625\u5149\u4e4d\u6d29")
HAPPY_1997_FI = hit(18329, "Happy Together \u2013 viimeinen tango Buenos Airesissa", 1997,
                    original="\u6625\u5149\u4e4d\u6d29")
HAPPY_RUNTIMES = {55059: 102, 18329: 96}


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

    def test_every_published_runtime_is_collected(self):
        shows = [{"title": "Digger", "len": "128"}, {"title": "Digger", "len": "129"},
                 {"title": "Digger", "len": ""}, {"title": "Digger"}]
        self.assertEqual(enrich_tmdb.gather(shows)["digger"]["m"], [128, 129])

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

    def test_without_a_year_the_published_runtime_decides_among_exact_hits(self):
        hits = [HAPPY_1989, HAPPY_1997]
        for order in (hits, list(reversed(hits))):
            h, exact = enrich_tmdb.pick(order, "Happy Together", minutes=[96],
                                        runtimes=HAPPY_RUNTIMES)
            self.assertEqual((h["id"], exact), (18329, True))

    def test_the_runtime_nearest_any_published_one_wins(self):
        """Two chains publish 139 and 144; TMDB's 2006 Casino Royale is 144."""
        hits = [hit(12208, "Casino Royale", 1967), hit(36557, "Casino Royale", 2006)]
        h, exact = enrich_tmdb.pick(hits, "Casino Royale", minutes=[139, 144],
                                    runtimes={12208: 131, 36557: 144})
        self.assertEqual((h["id"], exact), (36557, True))

    def test_an_equal_distance_keeps_tmdbs_order(self):
        """Niagara's Night of the Demon is 90 minutes; both films on TMDB are 96."""
        hits = [hit(25103, "Night of the Demon", 1957), hit(40146, "Night of the Demon", 1980)]
        h, exact = enrich_tmdb.pick(hits, "Night of the Demon", minutes=[90],
                                    runtimes={25103: 96, 40146: 96})
        self.assertEqual((h["id"], exact), (25103, True))

    def test_no_film_within_the_tolerance_keeps_tmdbs_order(self):
        """A tie-break, never a refusal: a cinema publishes The Shining at the European
        cut's 119 minutes and TMDB holds 144. Just inside the tolerance still moves it."""
        hits = [hit(694, "The Shining", 1980), hit(1174044, "The Shining", 2023)]
        tol = enrich_tmdb.TIE_RUNTIME_TOL_MIN
        for minutes, want in (([119], 694), ([79 + tol], 1174044), ([79 + tol + 1], 694)):
            with self.subTest(minutes=minutes):
                h, exact = enrich_tmdb.pick(hits, "The Shining", minutes=minutes,
                                            runtimes={694: 144, 1174044: 79})
                self.assertEqual((h["id"], exact), (want, True))

    def test_an_unknown_runtime_cannot_win(self):
        """TMDB answers 0 for a runtime it does not hold: a 3-minute short is not near it."""
        h, exact = enrich_tmdb.pick([hit(1, "Short", 2020), hit(2, "Short", 2021)], "Short",
                                    minutes=[3], runtimes={1: 0, 2: 6})
        self.assertEqual((h["id"], exact), (2, True))

    def test_a_year_still_decides_before_any_runtime(self):
        h, exact = enrich_tmdb.pick([HAPPY_1997, HAPPY_1989], "Happy Together", "1989",
                                    minutes=[96], runtimes=HAPPY_RUNTIMES)
        self.assertEqual((h["id"], exact), (55059, True))

    def test_no_exact_title_is_the_popularity_fallback_as_before(self):
        h, exact = enrich_tmdb.pick([hit(1, "Mother Mary", 2025)], "Mother", "2009")
        self.assertEqual((h["id"], exact), (1, False))


class ReconsiderTest(unittest.TestCase):
    """Which exact matches a pass judges again, and how many."""

    def entry(self, mid, title="a", **over):
        """`q` defaults to the search string this title cleans to, because that is what
        "judged on the same evidence" means from 2026-09-23: an entry without one is an
        entry judged by a cleaner nobody can name, and it is re-judged. The cases that
        are about a missing `q` pass `q=None` and say so."""
        e = {"r": 7.0, "n": 100, "v": "k", "x": True, "g": [18], "i": mid,
             "c": "2026-09-01", "fi": "", "en": "", "p": "/p.jpg",
             "q": enrich_tmdb.norm(enrich_tmdb.clean(title))}
        e.update(over)
        if e.get("q") is None:
            e.pop("q")
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

    def test_a_changed_search_string_re_judges_the_same_day(self):
        """The gap a strand addition falls into. `o` and `y` are the cinema's evidence and
        do not move when strands.py does, so without `q` the entry keeps its daily retry
        and the new strand does not apply until tomorrow."""
        title = "Vilimit-festivaali: Aavesoturi (1987)"      # no strand strips this one
        facts = {"v": {"t": title, "o": "", "y": "1987"}}
        cache = {"v": self.entry("", x=False, y="1987",
                                 q=enrich_tmdb.norm(enrich_tmdb.clean(title)))}
        self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), ([], 0))
        # what adding "vilimit-festivaali" to strands.py would do to clean()
        with mock.patch.object(enrich_tmdb, "clean", lambda s: "Aavesoturi"):
            self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), (["v"], 0))

    def test_the_search_string_is_checked_above_the_no_evidence_guard(self):
        """`Kino Iglu: Tokyo Story` carries neither an original title nor a year, so the
        ("", "") guard returns early. Checked after it, the whole field would miss the
        case it was added for; it is checked before."""
        title = "Kino Iglu: Tokyo Story"
        facts = {"k": {"t": title, "o": "", "y": ""}}          # no original, no year
        self.assertEqual((enrich_tmdb.norm(facts["k"]["o"]), facts["k"]["y"]), ("", ""))
        cache = {"k": self.entry(18148, q=enrich_tmdb.norm(enrich_tmdb.clean(title)))}
        self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), ([], 0))
        with mock.patch.object(enrich_tmdb, "clean", lambda s: "something else"):
            self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), (["k"], 0))

    def test_the_search_string_carries_no_year_so_the_year_signal_stays_in_y(self):
        """clean() strips a trailing year, so q is the title alone and y is the year. Put
        the year back into q and a cinema correcting it would trip both comparisons and
        re-judge the entry twice for one change."""
        for title in ("Trainspotting (1996)", "Vilimit-festivaali: Aavesoturi (1987)"):
            with self.subTest(title=title):
                q = enrich_tmdb.norm(enrich_tmdb.clean(title))
                self.assertNotIn(enrich_tmdb.published_year({"title": title}), q)

    def test_an_entry_written_before_q_existed_is_re_judged(self):
        """Reversed 2026-09-23. It used to re-judge nothing, so the pass that introduced
        `q` would not re-search all 532 entries at once; the budget above already prevents
        that, and the cost of the old reading was an entry frozen on whatever a long-gone
        cleaner decided. `Spider-Man: Brand New Day 2D` sat on 557, Spider-Man (2002), over
        seven showtimes at Kino 123 and Trio 123, and no change to clean() could reach it.
        262 of 609 entries were in that state."""
        legacy = {"n": {"r": 0, "n": 0, "v": "", "x": False, "g": [], "i": "",
                        "c": "2026-09-13", "fi": "", "en": "", "p": "", "o": "", "y": ""}}
        facts = {"n": {"t": "Anything At All", "o": "", "y": ""}}
        self.assertEqual(enrich_tmdb.reconsider(facts, legacy, {}), (["n"], 0))

    def test_the_legacy_backlog_drains_at_the_budget_and_no_faster(self):
        """The objection the old reading answered, answered by the ceiling instead: a pass
        takes at most the budget and reports the rest, so the entries arrive over several
        runs rather than as one re-fetch."""
        legacy = {f"t{i:03d}": {"r": 0, "n": 0, "v": "", "x": True, "g": [], "i": 7,
                                "c": "2026-09-13", "fi": "", "en": "", "p": ""}
                  for i in range(120)}
        facts = {k: {"t": k, "o": "", "y": ""} for k in legacy}
        due, held = enrich_tmdb.reconsider(facts, legacy, {}, budget=25)
        self.assertEqual((len(due), held), (25, 95))
        self.assertEqual(due, sorted(legacy)[:25], "key order, so the next pass continues")

    def test_an_entry_that_has_been_re_judged_once_behaves_like_any_other(self):
        """The drain is one-way: the re-judge writes `q`, and the entry is then only due
        when something actually moves."""
        title = "Anything At All"
        cache = {"n": self.entry(7, title=title)}
        facts = {"n": {"t": title, "o": "", "y": ""}}
        self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), ([], 0))

    def test_an_alias_still_wins_over_a_changed_search_string(self):
        cache = {"a": self.entry(240, q="old")}
        facts = {"a": {"t": "new", "o": "", "y": ""}}
        self.assertEqual(enrich_tmdb.reconsider(facts, cache, {"a": "240"}), ([], 0))

    def test_an_unmatched_entry_judged_on_the_same_evidence_is_left_to_its_daily_retry(self):
        cache = {"n": self.entry("", title="n", x=False, o="all night long", y="1962")}
        facts = {"n": {"t": "n", "o": "All Night Long", "y": "1962"}}
        self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), ([], 0))
        self.assertEqual(enrich_tmdb.reconsider(self.facts(n=""),
                                                {"n": self.entry("", title="n", x=False)}, {}),
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

    def run_main(self, table, en=None, runtimes=None):
        """`table` answers the fi-FI searches, `en` the en-US second pass.

        The language is part of the dispatch because that is the only thing the second
        pass changes: TMDB searches the same titles either way and answers `title` in the
        language asked for. An en-US search is recorded as a three-tuple so a test can
        tell the two passes apart, and so the ones written before this pass existed keep
        asserting what they did.
        """
        def fake_get(url, headers, timeout=25):
            if "/genre/movie/list" in url:
                return {"genres": [{"id": 18, "name": "Draama"}]}
            if "/search/movie" in url:
                q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
                key = (q["query"][0], (q.get("primary_release_year") or [""])[0])
                lang = (q.get("language") or ["fi-FI"])[0]
                if lang == "en-US":
                    self.searches.append(key + ("en-US",))
                    return {"results": (en or {}).get(key, [])}
                self.searches.append(key)
                return {"results": table.get(key, [])}
            if url.endswith("/videos"):
                return {"results": []}
            mid = int(urllib.parse.urlsplit(url).path.rsplit("/", 1)[1])
            return {"overview": "Teksti", "vote_count": 900, "vote_average": 7.5,
                    "genres": [{"id": 18}], "runtime": (runtimes or {}).get(mid, 0)}
        real = enrich_tmdb.get
        enrich_tmdb.get = fake_get
        self.addCleanup(lambda: setattr(enrich_tmdb, "get", real))
        # Both streams: this pass writes its warnings to stderr, and a test that only
        # read stdout could assert a warning was absent while it was being printed.
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = enrich_tmdb.main()
        self.assertEqual(code, 0)
        return out.getvalue() + err.getvalue()


class MainPathTest(MainHarness):

    # 1. an original title enables the match
    def test_an_original_title_finds_a_film_the_finnish_title_cannot(self):
        self.shows({"title": "Rakasta tai tuhoudu", "original": "All Night Long"})
        self.run_main({("All Night Long", ""): [ALL_NIGHT_1962]})
        e = self.cache()["rakasta tai tuhoudu"]
        self.assertEqual((e["i"], e["x"]), (37038, True))
        self.assertEqual(self.searches[:2], [("Rakasta tai tuhoudu", ""), ("All Night Long", "")])
        self.assertEqual((e["o"], e["y"]), ("all night long", ""), "the evidence used is recorded")

    def test_the_entry_records_the_search_string_it_was_judged_on(self):
        """`q` is what makes reconsider() notice a strand added on our side. A run that
        does not write it leaves the field dead and the comparison can never fire."""
        self.shows({"title": "Vauvakino: All Night Long", "year": "1962"})
        self.run_main({("All Night Long", "1962"): [ALL_NIGHT_1962]})
        e = self.cache()["vauvakino all night long"]
        self.assertEqual(e["q"], "all night long", "the cleaned string, normalised")
        self.assertEqual(enrich_tmdb.norm(enrich_tmdb.clean("Vauvakino: All Night Long")),
                         e["q"])

    def test_one_key_reached_by_two_spellings_does_not_re_judge_every_pass(self):
        """34 keys in the committed data are reached by more than one spelling, and
        gather() keeps whichever show it met first. Comparing the bare cleaned string
        re-judged 26 settled matches on every pass; normalised, the spelling cannot
        move the comparison."""
        self.shows({"title": "ALL NIGHT LONG", "year": "1962"})
        self.run_main({("ALL NIGHT LONG", "1962"): [ALL_NIGHT_1962]})
        cache = self.cache()
        for spelling in ("All Night Long", "all night long", "ALL NIGHT LONG"):
            with self.subTest(spelling=spelling):
                facts = enrich_tmdb.gather([{"title": spelling, "year": "1962"}])
                self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), ([], 0))

    def test_a_strand_added_after_the_match_re_judges_it_on_the_next_pass(self):
        """The round trip the field exists for: judged under one strand list, re-judged
        under the next without waiting a day, and left alone when nothing moved."""
        self.shows({"title": "Vauvakino: All Night Long", "year": "1962"})
        self.run_main({("All Night Long", "1962"): [ALL_NIGHT_1962]})
        cache = self.cache()
        facts = enrich_tmdb.gather([{"title": "Vauvakino: All Night Long", "year": "1962"}])
        self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}), ([], 0))
        with mock.patch.object(enrich_tmdb, "clean", lambda s: "Something Else"):
            self.assertEqual(enrich_tmdb.reconsider(facts, cache, {}),
                             (["vauvakino all night long"], 0))

    # 1b. no year, several films of the title: the published runtime decides
    def test_a_rival_only_english_offers_is_found_and_the_runtime_picks_it(self):
        self.shows({"title": "Happy Together", "len": "96"})
        out = self.run_main({("Happy Together", ""): [HAPPY_1989, HAPPY_1997_FI]},
                            en={("Happy Together", ""): [HAPPY_1989, HAPPY_1997]},
                            runtimes=HAPPY_RUNTIMES)
        e = self.cache()["happy together"]
        self.assertEqual((e["i"], e["x"]), (18329, True))
        self.assertIn(("Happy Together", "", "en-US"), self.searches)
        self.assertIn("runtime decides (1): Happy Together (96 min) -> Happy Together "
                      "(1997, 96 min)", out)
        self.assertEqual(json.loads((self.dir / "area-zz.json").read_text())
                         ["shows"][0]["tmdbId"], 18329)

    def test_the_english_pass_is_held_to_the_same_runtime_rule(self):
        """The fi-FI pass matches nothing exactly, so the en-US pass decides, and it must
        not fall back to TMDB's order when the runtime says otherwise."""
        self.shows({"title": "Happy Together", "len": "96"})
        self.run_main({}, en={("Happy Together", ""): [HAPPY_1989, HAPPY_1997]},
                      runtimes=HAPPY_RUNTIMES)
        self.assertEqual(self.cache()["happy together"]["i"], 18329)

    def test_one_film_of_the_title_needs_no_runtime(self):
        """The English search runs, finds no rival, and no detail request is spent."""
        self.shows({"title": "Happy Together", "len": "96"})
        self.run_main({("Happy Together", ""): [HAPPY_1997]},
                      en={("Happy Together", ""): [HAPPY_1997]}, runtimes={18329: 50})
        e = self.cache()["happy together"]
        self.assertEqual((e["i"], e["x"]), (18329, True))

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

    def test_an_alias_id_replaces_an_exact_match_it_disagrees_with(self):
        """The error this prevents: 256 showtimes keeping the 1998 Practical Magic because
        the 2026 sequel's Finnish title is what TMDB registers for the original, so the
        wrong id was written with x:True and a complete entry is skipped before the alias
        is read."""
        self.shows({"title": "Practical Magic: Lumotut sisaret", "year": "2026"})
        (self.dir / "tmdb-aliases.json").write_text(
            json.dumps({"practical magic lumotut sisaret": "1302904"}))
        self.cache_write({"practical magic lumotut sisaret": {
            "r": 6.8, "n": 1853, "v": "k", "x": True, "g": [14], "i": 6435,
            "c": self.today, "fi": "", "en": "", "p": "/old.jpg"}})
        out = self.run_main({})
        self.assertEqual(self.cache()["practical magic lumotut sisaret"]["i"], 1302904)
        self.assertIn("an alias replaces", out)

    def test_an_alias_id_that_agrees_leaves_the_entry_and_the_budget_alone(self):
        """The counterweight: an alias naming the id already held is not a reason to throw
        the entry away and spend a request re-fetching it every run."""
        self.shows({"title": "Kummisetä osa II", "year": "1974"})
        (self.dir / "tmdb-aliases.json").write_text(json.dumps({"kummisetä osa ii": "240"}))
        self.cache_write({"kummisetä osa ii": {
            "r": 8.5, "n": 12000, "v": "k", "x": True, "g": [18], "i": 240,
            "c": self.today, "fi": "", "en": "", "p": ""}})
        out = self.run_main({})
        self.assertEqual(self.cache()["kummisetä osa ii"]["i"], 240)
        self.assertNotIn("an alias replaces", out)

    def test_a_search_string_alias_does_not_unseat_an_exact_entry(self):
        """A replacement query is a better way to ask, not a verdict on which film it is,
        and there is no id in it to disagree with the one the matcher settled on."""
        self.shows({"title": "Autot (uudelleenjulkaisu)", "year": "2026"})
        (self.dir / "tmdb-aliases.json").write_text(
            json.dumps({"autot uudelleenjulkaisu": "Cars"}))
        self.cache_write({"autot uudelleenjulkaisu": {
            "r": 7.0, "n": 19000, "v": "k", "x": True, "g": [16], "i": 920,
            "c": self.today, "fi": "", "en": "", "p": ""}})
        out = self.run_main({})
        self.assertEqual(self.cache()["autot uudelleenjulkaisu"]["i"], 920)
        self.assertNotIn("an alias replaces", out)

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


class AliasFileTest(unittest.TestCase):
    """The hand-maintained alias file, as the pass reads it."""

    FILE = _ctx.ROOT / "scripts" / "providers" / "tmdb-aliases.json"

    def test_every_key_is_a_norm_key_and_every_value_an_id_or_a_search_string(self):
        """A key that is not its own norm() can never be looked up: the pass keys on the
        normalised published title. An id is digits; anything else is searched."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        entries = {k: v for k, v in doc.items() if not k.startswith("_")}
        self.assertGreater(len(entries), 5)
        for k, v in entries.items():
            with self.subTest(key=k):
                self.assertEqual(k, enrich_tmdb.norm(k))
                self.assertIsInstance(v, str)
                self.assertTrue(v.strip())

    def test_the_lucky_luke_alias_pins_the_verified_id(self):
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        self.assertEqual(doc["lucky luke sotapolulla"], "50166")
        self.assertEqual(enrich_tmdb.norm("Lucky luke sotapolulla"), "lucky luke sotapolulla")

    def test_the_pressure_alias_covers_both_published_spellings(self):
        """TMDB holds no Finnish title for 1318413, so no query spelling reaches it and
        the alias is the only route. Seventeen providers publish the film and Gilda
        capitalises the second word, so the guard that matters is that both spellings
        normalise onto the one key rather than the id itself."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        self.assertEqual(doc["myrskyn ikkuna"], "1318413")
        for published in ("Myrskyn ikkuna", "Myrskyn Ikkuna"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.norm(published), "myrskyn ikkuna")


    def test_both_practical_magic_spellings_point_at_the_sequel(self):
        """Kino Tar appends its strand to the title as a suffix and `run.py` splits only
        prefixes, so that spelling normalises to its own key and needs its own entry. The
        error this prevents: one of the two silently keeping the 1998 film."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        for published in ("Practical Magic: Lumotut sisaret",
                          "PRACTICAL MAGIC: LUMOTUT SISARET",
                          "Practical Magic: Lumotut sisaret (K18-anniskelunäytös)"):
            with self.subTest(published=published):
                self.assertEqual(doc[enrich_tmdb.norm(published)], "1302904")

    def test_every_royal_opera_alias_pins_the_season_the_cinema_relays(self):
        """An opera relay's TMDB record is per season, so the id is the part that can be
        wrong while the title looks right. The error this prevents: the 2025/26 Tosca
        record, 1482356, which the weak search found for a 2027 relay, being written here.
        All four are 2026/27 records, which is what Kino Tapiola relays; the id is
        asserted rather than merely present, because a present-but-wrong id publishes."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        for published, tmdb_id in (("The Royal Opera: Carmen", "1702759"),
                                   ("The Royal Opera: Götterdämmerung", "1702769"),
                                   ("The Royal Opera: Cosi fan Tutte", "1702775"),
                                   ("The Royal Opera: Tosca", "1702784")):
            with self.subTest(published=published):
                self.assertEqual(doc[enrich_tmdb.norm(published)], tmdb_id)
        self.assertNotIn("1482356", doc.values())


    def test_every_royal_ballet_alias_pins_the_season_the_cinema_relays(self):
        """The same per-season trap as the opera relays, found the other way round. These
        two were never weak and never logged: both were written as EXACT matches to
        265042, Czinner's 1960 documentary, so one id and one 1960 synopsis covered two
        different 2026/27 ballets. No worklist would have shown it, which is why the ids
        are asserted here rather than left to the search."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        for published, tmdb_id in (("The Royal Ballet: Pähkinänsärkijä", "1702761"),
                                   ("The Royal Ballet: Joutsenlampi", "1702782")):
            with self.subTest(published=published):
                self.assertEqual(doc[enrich_tmdb.norm(published)], tmdb_id)
        self.assertNotEqual(doc[enrich_tmdb.norm("The Royal Ballet: Pähkinänsärkijä")],
                            doc[enrich_tmdb.norm("The Royal Ballet: Joutsenlampi")],
                            "two different ballets must not share one id again")

    def test_the_suleiman_relay_alias_is_the_feature_not_the_short(self):
        """1387552 is a 7-minute short that shares the English title. The published row is
        92 minutes and names Elia Suleiman, and 27744 is his 92-minute 2002 feature."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        self.assertEqual(doc[enrich_tmdb.norm("Divine intervention")], "27744")

    def test_the_sheryl_happy_together_alias_is_wong_kar_wai(self):
        """Sheryl publishes 96 minutes and names Wong Kar-Wai; 18329 is his 96-minute 1997
        film. The search had published 55059, a 102-minute 1989 comedy of the same title."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        self.assertEqual(doc[enrich_tmdb.norm("Happy Together")], "18329")

    def test_the_largest_2026_09_19_alias_is_pinned(self):
        """39 showtimes over 17 venues, the largest single row in that batch, and the one
        the maintainer reported. Two independent sources say 1299382: TMDB's own record
        registers FI "Lyhyt rakkaustarina" in alternative_titles, and Bio Forum Tammisaari
        publishes the title with the Italian original attached, which matched on its own
        and already carries the id in the committed data."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        self.assertEqual(doc["lyhyt rakkaustarina"], "1299382")
        self.assertEqual(enrich_tmdb.norm("Lyhyt rakkaustarina"), "lyhyt rakkaustarina")

    def test_no_alias_points_at_a_candidate_the_log_named_wrong(self):
        """The failure this file exists to prevent, in the one direction a reviewer cannot
        see by reading: an id that looks settled because the search returned it. Each of
        these was the weak candidate for a row worked on 2026-09-19 and each is a
        different film, checked against /movie/{id}. Writing one would put a wrong poster
        on a row, which is worse than the blank tile it replaces."""
        doc = json.loads(self.FILE.read_text(encoding="utf-8"))
        wrong = {
            "1080916": "Titanic: 25 Years Later, not Tarkovsky's Solaris",
            "446700": "the Bolshoi's A Hero of Our Time, not Neumeier's Nutcracker",
            "67572": "Disney's The Band Concert, not Il Volo",
            "444446": "the Met's Idomeneo, not Don Giovanni or Madama Butterfly",
            "967969": "Council House Movie Star, not Ortotopologian loputtomat alkeet",
            "893723": "PAW Patrol: The Mighty Movie, not The Dino Movie",
            "331647": "Fratter's 2001 Abraxas, not Polselli's 1973 Black Magic Rites",
            "219580": "a Tom and Jerry short, not the 2026 Mouse",
            "1482356": "the 2025/26 Tosca, not the 2026/27 one the cinema relays",
            "1769545": "deleted from TMDB; /movie/1769545 answers status_code 34",
            "265042": "Czinner's 1960 Covent Garden documentary, not a 2026/27 relay",
            "1387552": "Koudmani's 7-minute short, not Suleiman's Divine Intervention",
            "557": "Raimi's 2002 Spider-Man, not Spider-Man: Brand New Day (969681)",
            "55059": "Damski's 1989 Happy Together, not Wong Kar-Wai's (18329)",
        }
        for tmdb_id, why in wrong.items():
            with self.subTest(tmdb_id=tmdb_id):
                self.assertNotIn(tmdb_id, doc.values(), why)


class PublishedCoverageTest(unittest.TestCase):
    """A standing check on what is published, not on the helpers (2026-09-23).

    The defect this catches is the one a reader sees: a card drawn as an initials tile
    because a cinema decorated a title that every other cinema publishes plainly. It was
    found twice by eye and never by the suite -- "Päivien lumo + tekijävierailu" at Kino
    Tapiola, reported from the live site, and "Spider-Man: Brand New Day 2D" at Kino 123
    and Trio 123, which was worse because it carried a *wrong* film rather than none.

    The rule is narrow on purpose, so it accuses only what it can prove: an unmatched
    title whose cleaned search string *opens with* the whole cleaned search string of a
    title that did match. The remainder is then decoration the cleaner does not know, and
    the cleaner is where it is fixed. It does not compare loosely, does not suggest an id,
    and never writes one.

    `ALLOWED` is empty and should stay that way. An entry belongs there only when the two
    are genuinely different films whose titles nest, and it carries the reason.
    """

    ALLOWED = {}

    @classmethod
    def setUpClass(cls):
        cls.matched, cls.unmatched = {}, {}
        for f in sorted((_ctx.ROOT / "data").glob("area-*.json")):
            try:
                shows = json.loads(f.read_text(encoding="utf-8")).get("shows", [])
            except json.JSONDecodeError:
                continue
            for s in shows:
                t = s.get("title") or ""
                if not t:
                    continue
                bag = cls.matched if s.get("tmdbId") else cls.unmatched
                bag.setdefault(t, set()).add(s.get("theatre") or "")

    def test_the_committed_data_has_both_kinds_to_compare(self):
        """Without this the check below passes on an empty loop, which is how a guard
        stops guarding without anyone noticing."""
        self.assertGreater(len(self.matched), 50, "no matched titles in the committed data")
        self.assertGreater(len(self.unmatched), 5, "no unmatched titles to check")

    def test_no_unmatched_title_opens_with_a_title_that_matched(self):
        keys = {}
        for t in self.matched:
            keys.setdefault(enrich_tmdb.norm(enrich_tmdb.clean(t)), t)
        bad = []
        for u, venues in sorted(self.unmatched.items()):
            if u in self.ALLOWED:
                continue
            words = enrich_tmdb.norm(enrich_tmdb.clean(u)).split()
            if not words:
                continue
            for key, matched_title in keys.items():
                head = key.split()
                if head and len(head) < len(words) and words[:len(head)] == head:
                    bad.append(f"{u!r} at {sorted(v for v in venues if v)} draws no poster "
                               f"while {matched_title!r} matched; "
                               f"{' '.join(words[len(head):])!r} is decoration clean() "
                               f"does not strip")
                    break
        self.assertEqual(bad, [])

    def test_the_rule_would_have_caught_both_titles_it_was_written_for(self):
        """On the strings as they were published, with the two rules that fix them off."""
        keys = {enrich_tmdb.norm("Päivien lumo"), enrich_tmdb.norm("Spider-Man: Brand New Day")}
        for published in ("Päivien lumo + tekijävierailu", "Spider-Man: Brand New Day 2D"):
            with self.subTest(published=published):
                words = enrich_tmdb.norm(published).split()   # norm alone: the old cleaning
                self.assertTrue(
                    any(words[:len(k.split())] == k.split() and len(k.split()) < len(words)
                        for k in keys),
                    "the check would not have seen it")


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

    def unmatched(self, day, title=None, **over):
        """`q` is what the entry was judged on, defaulting to its own key's cleaning. An
        entry without one is re-judged from 2026-09-23, which is a different case and the
        callers that mean it pass `q=None`."""
        e = {"r": 0, "n": 0, "v": "", "x": False, "g": [], "i": "", "c": day, "a": "",
             "fi": "", "en": "", "p": ""}
        if title is not None:
            e["q"] = enrich_tmdb.norm(enrich_tmdb.clean(title))
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
        self.cache_write({"bussipysäkki": self.unmatched("2026-09-12", "Bussipysäkki"),
                          "other": self.unmatched(self.TODAY, "Other")})
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
                                 "c": self.TODAY, "fi": "", "en": "", "p": "",
                                 "q": "kummisetä osa ii"},
            "settled": {"r": 7.0, "n": 100, "v": "k", "x": True, "g": [18], "i": 5,
                        "c": self.TODAY, "fi": "", "en": "", "p": "", "o": "", "y": "1990",
                        "q": "settled"}})
        out = self.run_main({})
        self.assertEqual(self.searches, [])
        self.assertNotIn("re-judging", out)


class EnglishSecondSearchTest(MainHarness):
    """One en-US search, only for a title the fi-FI pass could not match exactly.

    `language` decides what TMDB answers `title` as; it does not widen which titles are
    searched. So a cinema publishing TMDB's own English title can never match under
    fi-FI where TMDB holds no Finnish one, and the same hits settle under en-US. Decided
    2026-09-19 with the bounds these tests pin: it fills an empty or weak slot, it never
    replaces a cached id, an id that disagrees with the weak candidate is named for the
    alias file rather than published, and it costs one request per title.
    """

    def test_a_title_the_finnish_pass_missed_settles_on_the_english_one(self):
        self.shows({"title": "The Time That Remains"})
        log = self.run_main(
            {("The Time That Remains", ""): [hit(25943, "\u0627\u0644\u0632\u0645\u0646 \u0627\u0644\u0628\u0627\u0642\u064a", 2009)]},
            en={("The Time That Remains", ""): [hit(25943, "The Time That Remains", 2009)]})
        e = self.cache()["the time that remains"]
        self.assertEqual((e["i"], e["x"]), (25943, True))
        self.assertIn("settled on the English title (1)", log)

    def test_it_costs_one_request_and_only_after_the_finnish_pass_failed(self):
        self.shows({"title": "The Time That Remains"})
        self.run_main(
            {("The Time That Remains", ""): [hit(25943, "\u0627\u0644\u0632\u0645\u0646", 2009)]},
            en={("The Time That Remains", ""): [hit(25943, "The Time That Remains", 2009)]})
        en_calls = [c for c in self.searches if len(c) == 3]
        self.assertEqual(en_calls, [("The Time That Remains", "", "en-US")])

    def test_an_exact_finnish_match_never_reaches_the_english_pass(self):
        self.shows({"title": "Kuopus"})
        self.run_main({("Kuopus", ""): [hit(1, "Kuopus", 2026)]})
        self.assertEqual([c for c in self.searches if len(c) == 3], [])

    def test_an_english_id_that_disagrees_is_named_and_not_published(self):
        """The `black magic rites` case the research file records: an exact en-US match on
        a *different* id than the weak candidate. An exact match is trusted and publishes,
        so this one must not be taken automatically."""
        self.shows({"title": "Black Magic Rites"})
        log = self.run_main(
            {("Black Magic Rites", ""): [hit(331647, "Riti, magie nere", 1973)]},
            en={("Black Magic Rites", ""): [hit(59912, "Black Magic Rites", 1973)]})
        e = self.cache()["black magic rites"]
        self.assertEqual((e["i"], e["x"]), (331647, False), "the weak candidate stands")
        self.assertIn("en-US names a different film", log)
        self.assertIn("59912", log)

    def test_an_empty_slot_is_filled_when_the_finnish_pass_found_nothing_at_all(self):
        self.shows({"title": "Tiger on the Beat"})
        log = self.run_main(
            {("Tiger on the Beat", ""): []},
            en={("Tiger on the Beat", ""): [hit(42, "Tiger on the Beat", 1988)]})
        e = self.cache()["tiger on the beat"]
        self.assertEqual((e["i"], e["x"]), (42, True))
        self.assertIn("1 settled", log)

    def test_no_english_match_leaves_the_weak_candidate_exactly_as_it_was(self):
        self.shows({"title": "Ooppera: Don Giovanni"})
        log = self.run_main(
            {("Ooppera: Don Giovanni", ""): [hit(444446, "Ooppera: Idomeneo", 2026)]},
            en={})
        e = self.cache()["ooppera don giovanni"]
        self.assertEqual((e["i"], e["x"]), (444446, False))
        self.assertIn("weak match, no exact title (1)", log)
        self.assertIn("0 settled", log)

    def test_the_pass_is_counted_in_the_log_whatever_it_found(self):
        self.shows({"title": "Ooppera: Don Giovanni"})
        log = self.run_main({("Ooppera: Don Giovanni", ""): [hit(1, "Muu", 2026)]}, en={})
        self.assertIn("en-US second search: 1 title(s) asked", log)


if __name__ == "__main__":
    unittest.main()
