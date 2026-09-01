"""Which cached titles the TMDB pass re-reads, and how many of them at once.

The rule used to be `c.get("v") or c.get("c") == today`: a film with a trailer was never
looked at again, so its rating and vote count froze at whatever they were the day the
trailer turned up. Measured against the committed cache on 2026-09-01: 154 entries, 94
with a trailer, 71 of those last read on 2026-08-27 and never due to be read again.

The pass needs a token and talks to a third party, so what is tested here is the
decision, against a fabricated cache. The two properties that matter pull against each
other: a rating has to stop being permanent, and one pass must not turn into a re-fetch
of every title. `due()` is where they meet, so `due()` is what these exercise.
"""
import unittest

import _ctx                                                # noqa: F401
import enrich_tmdb


TODAY = "2026-09-01"


def entry(day, trailer=True, **over):
    """A complete cache entry as the current shape writes one."""
    e = {"r": 7.1, "n": 400, "v": "abc123" if trailer else "", "x": True,
         "g": [18], "i": 42, "c": day, "fi": "Suomeksi", "en": "In English", "p": "/a.jpg"}
    e.update(over)
    return e


def due(cache, **kw):
    """-> (sorted keys this pass would fetch, refreshed, deferred)."""
    keys, refreshed, deferred = enrich_tmdb.due(list(cache), cache, TODAY, **kw)
    return sorted(keys), refreshed, deferred


class WhatIsDueTest(unittest.TestCase):

    # -- the defect --------------------------------------------------------------------

    def test_a_trailer_no_longer_freezes_the_rating(self):
        """The whole item. Eight days after it was last read, this entry is re-read."""
        keys, refreshed, deferred = due({"old": entry("2026-08-24")}, max_age=7)
        self.assertEqual(keys, ["old"])
        self.assertEqual((refreshed, deferred), (1, 0))

    def test_a_recently_read_entry_with_a_trailer_is_left_alone(self):
        """Otherwise this becomes a re-fetch of everything on every run."""
        keys, refreshed, _ = due({"fresh": entry("2026-08-30")}, max_age=7)
        self.assertEqual(keys, [])
        self.assertEqual(refreshed, 0)

    def test_the_boundary_is_the_age_itself(self):
        cache = {"at": entry("2026-08-25"), "under": entry("2026-08-26")}
        self.assertEqual(due(cache, max_age=7)[0], ["at"])

    # -- what must not change ----------------------------------------------------------

    def test_a_title_with_no_trailer_is_still_re_checked_daily(self):
        """Unchanged behaviour, and the reason it exists: a trailer may not have been
        published when the film opened, so the entry is asked again the next day."""
        cache = {"yesterday": entry("2026-08-31", trailer=False),
                 "already-today": entry(TODAY, trailer=False)}
        self.assertEqual(due(cache)[0], ["yesterday"])

    def test_a_daily_re_check_is_not_charged_to_the_refresh_budget(self):
        """They are different work: one is looking for a trailer that may not exist yet,
        the other is re-reading a rating. Budgeting the first would stop new films being
        picked up because old ones were being refreshed."""
        cache = {f"n{i}": entry("2026-08-31", trailer=False) for i in range(30)}
        cache.update({f"o{i}": entry("2026-08-20") for i in range(30)})
        keys, refreshed, deferred = due(cache, max_age=7, budget=2)
        self.assertEqual(len(keys), 32)
        self.assertEqual((refreshed, deferred), (2, 28))

    def test_an_entry_missing_a_field_is_incomplete_and_costs_one_pass(self):
        """`n` arrived with the MIN_VOTES gate. An entry without it carries an ungated
        rating, and treating that as incomplete is what made adding the gate cost a
        re-check rather than a cache wipe. A trailer does not exempt it."""
        cache = {"nogate": entry(TODAY, n=None)}
        del cache["nogate"]["n"]
        self.assertEqual(due(cache)[0], ["nogate"])

    def test_a_title_that_is_not_cached_at_all_is_fetched(self):
        self.assertEqual(enrich_tmdb.due(["brand new"], {}, TODAY)[0], {"brand new"})

    def test_the_score_and_its_sample_size_are_one_entry(self):
        """`n` travels with `r`, so the MIN_VOTES threshold can be retuned without
        re-fetching. Both are written by the same path, so a refresh carries both."""
        self.assertTrue(enrich_tmdb.is_complete(entry(TODAY)))
        thin = entry(TODAY)
        del thin["n"]
        self.assertFalse(enrich_tmdb.is_complete(thin))


class BudgetTest(unittest.TestCase):
    """A ceiling on how much of the backlog one pass takes, and a report of the rest."""

    def stale(self, n, oldest=30):
        return {f"t{i:02d}": entry(f"2026-08-{oldest - i:02d}") for i in range(n)}

    def test_one_pass_never_re_reads_more_than_the_budget(self):
        """The property the whole ceiling exists for: with everything past the age, this
        is a bounded number of extra requests and not a full re-fetch."""
        for n in (13, 40, 200):
            with self.subTest(stale=n):
                keys, refreshed, deferred = due(self.stale(n, oldest=25),
                                                max_age=7, budget=12)
                self.assertEqual(len(keys), 12)
                self.assertEqual((refreshed, deferred), (12, n - 12))

    def test_the_oldest_go_first_so_nothing_starves(self):
        cache = {"a": entry("2026-08-01"), "b": entry("2026-08-20"),
                 "c": entry("2026-08-10"), "d": entry("2026-08-25")}
        self.assertEqual(due(cache, max_age=7, budget=2)[0], ["a", "c"])

    def test_an_entry_with_no_date_counts_as_the_oldest_thing_there_is(self):
        """An entry from a shape this code no longer writes has an unknown age, and
        unknown is not fresh -- reading it as 0 days old would park it for ever."""
        cache = {"dated": entry("2026-08-01"), "undated": entry("2026-08-01", c="")}
        self.assertEqual(due(cache, max_age=7, budget=1)[0], ["undated"])

    def test_nothing_is_selected_when_nothing_is_stale(self):
        cache = {f"t{i}": entry("2026-08-30") for i in range(50)}
        self.assertEqual(due(cache, max_age=7, budget=12), ([], 0, 0))

    def test_the_choice_is_the_same_on_every_machine(self):
        """Ties break on the key, so the log names the same entries twice in a row and a
        second run does not re-read a different arbitrary dozen."""
        cache = {f"t{i:02d}": entry("2026-08-01") for i in range(30)}
        first = due(cache, max_age=7, budget=5)
        self.assertEqual(first, due(cache, max_age=7, budget=5))
        self.assertEqual(first[0], ["t00", "t01", "t02", "t03", "t04"])


class AgainstTheCommittedCacheTest(unittest.TestCase):
    """The catch-up, against the real cache rather than a fixture.

    A fixture can be built to fit the budget. This asks the question of the cache that
    actually exists, on a date by which every entry in it is past the age.
    """

    def setUp(self):
        import json
        import pathlib
        path = pathlib.Path(__file__).resolve().parents[1] / "data" / "tmdb-titles.json"
        self.cache = json.loads(path.read_text(encoding="utf-8"))

    def test_a_run_a_fortnight_from_the_oldest_entry_still_fits_the_budget(self):
        """The catch-up is bounded. Every entry in the committed cache is past the age on
        this date, and one pass still re-reads only the budget."""
        keys, refreshed, deferred = enrich_tmdb.due(
            list(self.cache), self.cache, "2026-09-30")
        self.assertEqual(refreshed, enrich_tmdb.REFRESH_BUDGET)
        self.assertGreater(deferred, 0, "nothing was deferred, so nothing was capped")


if __name__ == "__main__":
    unittest.main()
