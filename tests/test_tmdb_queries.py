"""What `queries()` sends to TMDB, and what it must never send.

`clean()` and `queries()` already do this work -- the entry in IDEAS records the fix and
the 8-of-9 misses it closed -- but nothing pinned the behaviour, so the two rules that
make it correct were held only by the comments explaining them:

  * the strand list is exact, never a `^\\w+:` pattern, because most colons in this data
    are franchise titles. "Spider-Man:" appears 443 times in one day's showtimes against
    4 for "Seniorikino:", and a pattern would decapitate every one of them;
  * only the *search string* is cleaned. `norm()` keys the cache and films-extra.json on
    the title as the cinema published it, and `normTitle()` in index.html has to agree
    with that key, so a title that TMDB is searched for under a shorter name still has
    to key under its full one.

The raw title staying in the candidate list is the third rule: a wrong cleanup then
costs one extra request instead of a missing film.
"""
import unittest

import _ctx                                                # noqa: F401
import enrich_tmdb


class QueriesTest(unittest.TestCase):

    # -- what gets searched first --------------------------------------------------

    def test_a_year_suffix_is_dropped_before_searching(self):
        """A repertory screening publishes the year: "Trainspotting (1996)". TMDB has no
        such title, so the search has to go out without it."""
        q = enrich_tmdb.queries("Trainspotting (1996)")
        self.assertEqual(q[0], "Trainspotting")

    def test_the_raw_title_stays_as_the_last_candidate(self):
        """The fallback that makes cleaning safe: if the cleanup is ever wrong, the
        published title is still tried, so the cost is a request rather than a film with
        no rating, poster or genres."""
        q = enrich_tmdb.queries("Trainspotting (1996)")
        self.assertEqual(q[-1], "Trainspotting (1996)")
        self.assertIn("Trainspotting (1996)", q)

    def test_a_strand_prefix_is_dropped_before_searching(self):
        """"Vauvakino" is how the cinema sells the screening, not part of the film."""
        self.assertEqual(enrich_tmdb.queries("Vauvakino: La La Land")[0], "La La Land")

    def test_the_strand_match_ignores_case(self):
        """Published in caps by the cinema; the list is lowercase."""
        self.assertEqual(enrich_tmdb.queries("KESÄKINO: Autofiktio")[0], "Autofiktio")

    def test_a_swedish_strand_is_dropped_too(self):
        """Finland-Swedish strands sit in the same position. The ampersand and the rest
        of the title come through untouched."""
        q = enrich_tmdb.queries("BARNSÖNDAGAR: Minioner & monster")
        self.assertEqual(q[0], "Minioner & monster")

    # -- what must not get decapitated ---------------------------------------------

    def test_a_franchise_colon_is_searched_whole(self):
        """The reason the strand list is exact rather than a pattern. "Dyyni: Osa kolme"
        is one film's title; searching "Dyyni" first would match the wrong film, and it
        is what a `^\\w+:` rule would do to every franchise in the data."""
        q = enrich_tmdb.queries("Dyyni: Osa kolme")
        self.assertEqual(q[0], "Dyyni: Osa kolme")
        self.assertNotEqual(q[0], "Dyyni")

    def test_the_franchise_head_is_only_a_fallback(self):
        """It is still tried, after the whole title, which is what rescues a title the
        distributor punctuated differently from TMDB."""
        q = enrich_tmdb.queries("Dyyni: Osa kolme")
        self.assertIn("Dyyni", q)
        self.assertGreater(q.index("Dyyni"), q.index("Dyyni: Osa kolme"))

    # -- the cache key is the published title --------------------------------------

    def test_cleaning_does_not_reach_the_cache_key(self):
        """norm() keys on what the cinema published. If clean() ever leaked into the key,
        "Trainspotting (1996)" would key as "trainspotting" and collide with the plain
        film -- one cache entry for two titles, and a key that no longer agrees with
        normTitle() in index.html, which never sees the cleaned string at all."""
        for published in ("Trainspotting (1996)", "Vauvakino: La La Land",
                          "KESÄKINO: Autofiktio", "BARNSÖNDAGAR: Minioner & monster"):
            with self.subTest(published=published):
                searched = enrich_tmdb.clean(published)
                self.assertNotEqual(enrich_tmdb.norm(published),
                                    enrich_tmdb.norm(searched))

    def test_the_key_keeps_the_year_and_the_strand(self):
        """Stated as the values themselves, so the test fails if the key silently starts
        dropping either one."""
        self.assertEqual(enrich_tmdb.norm("Trainspotting (1996)"), "trainspotting 1996")
        self.assertEqual(enrich_tmdb.norm("Vauvakino: La La Land"), "vauvakino la la land")

    def test_a_franchise_title_keys_apart_from_its_head(self):
        """The collision norm()'s own docstring names: "Dyyni: Osa kolme" must not key as
        "Dyyni"."""
        self.assertNotEqual(enrich_tmdb.norm("Dyyni: Osa kolme"), enrich_tmdb.norm("Dyyni"))


if __name__ == "__main__":
    unittest.main()
