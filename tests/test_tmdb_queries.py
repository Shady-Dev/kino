"""What `queries()` sends to TMDB, and what it must never send.

Two rules: the strand list is exact, never a `^\\w+:` pattern, because most colons are
franchise titles ("Spider-Man:" 443 times in one day against 4 for "Seniorikino:"); and
only the search string is cleaned, since `norm()` keys the cache and films-extra.json on
the published title and `normTitle()` in index.html must agree. The raw title stays in the
candidate list, so a wrong cleanup costs one extra request instead of a missing film.
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


class AudioMarkerTest(unittest.TestCase):
    """A marker names the audio, never the film, so it comes off the search string.

    `suomeksi` was on the list and its counterparts were not, so a cinema selling the
    dubbed and the subtitled run as two films had one searchable and the other not.
    Measured across the committed data on 2026-09-14: one film, Coyote vs. Acme, was
    published under eight spellings by nine chains, and the four below were the ones the
    search could not reach.
    """

    def test_every_spelling_of_the_english_marker_comes_off(self):
        """Three positions, all in the data on 2026-09-14: parenthesised at Kino 123,
        Leffabuumi and Studio 123 Järvenpää, trailing in caps at the two Cinemahouse
        sites, comma-separated at Kotkan Leffat."""
        for published in ("Kojootti vs. ACME (englanniksi)",
                          "Kojootti vs. ACME ENGLANNIKSI",
                          "Kojootti vs. ACME, englanniksi"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.clean(published), "Kojootti vs. ACME")

    def test_the_swedish_and_the_spelled_out_finnish_markers_come_off(self):
        self.assertEqual(enrich_tmdb.clean("Gråben vs. ACME (på svenska)"),
                         "Gråben vs. ACME")
        self.assertEqual(enrich_tmdb.clean("Kojootti vs. ACME (pa svenska)"),
                         "Kojootti vs. ACME")
        self.assertEqual(enrich_tmdb.clean("Kojootti vs. ACME (suomeksi puhuttu)"),
                         "Kojootti vs. ACME")

    def test_the_finnish_markers_still_come_off(self):
        """The half that already worked, pinned so the rewrite cannot drop it."""
        for published in ("Kojootti vs. ACME (suomeksi)", "Kojootti vs. ACME SUOMEKSI",
                          "Kojootti vs. ACME, suomeksi", "Kojootti vs. ACME (Dub)"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.clean(published), "Kojootti vs. ACME")

    def test_the_two_runs_of_one_film_still_key_apart(self):
        """The dub and the subtitled run are two cards at the cinema and must stay two
        cache entries, even though they now search for the same string."""
        fi, en = "Kojootti vs. ACME SUOMEKSI", "Kojootti vs. ACME ENGLANNIKSI"
        self.assertEqual(enrich_tmdb.clean(fi), enrich_tmdb.clean(en))
        self.assertNotEqual(enrich_tmdb.norm(fi), enrich_tmdb.norm(en))
        self.assertEqual(enrich_tmdb.norm(en), "kojootti vs acme englanniksi")


class TerminalVersionMarkerTest(unittest.TestCase):
    """Two more ways a cinema names which run of a film a screening is, measured
    2026-09-20 in the committed data and both reaching TMDB with the marker attached.

    TMB publishes "Kojootti vs ACME Orginaali äänillä" with no brackets and with the i
    missing, on all four of its cinemas at once: 8 showtimes across Toijala, Sampo, Mania
    and Elo, every one drawn as an initials tile, while every other spelling of that film
    matched 1204680. "(eng)" and "(sub)" are the same claim in three letters and had sat
    unmatched in the cache since 2026-09-14.

    Both rules are anchored to the end of the title. "eng" and "sub" are ordinary
    syllables, so a rule that fired anywhere would cut real words out of real names.
    """

    def test_the_unbracketed_original_audio_marker_comes_off(self):
        """Both spellings, because the one in the data is the operator's."""
        for published in ("Kojootti vs ACME Orginaali äänillä",
                          "Kojootti vs ACME Originaali äänillä",
                          "Kojootti vs ACME, orginaali äänillä",
                          "Kojootti vs ACME ORGINAALI ääNILLä"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.clean(published), "Kojootti vs ACME")

    def test_the_three_letter_version_markers_come_off(self):
        for published in ("Kojootti vs. ACME (eng)", "Kojootti vs. ACME (sub)",
                          "Kojootti vs. ACME (ENG)", "Kojootti vs. ACME ( sub )"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.clean(published), "Kojootti vs. ACME")

    def test_a_marker_only_comes_off_at_the_end(self):
        """The restriction that keeps the rule safe: a title carrying the same letters
        anywhere else is left exactly as the cinema published it."""
        for published in ("Subway", "Submarine", "English Patient", "Engel",
                          "Kojootti vs. ACME (sub) osa 2",
                          "Orginaali äänillä ja muita tarinoita"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.clean(published), published)

    def test_the_accepted_acme_spellings_still_clean_the_same_way(self):
        """The variants that already matched 1204680, pinned so this rule cannot move
        them. Every one has to reach the same search string as the bare title."""
        for published in ("Kojootti vs. ACME (suomeksi)", "Kojootti vs. ACME (orig)",
                          "Kojootti vs. ACME (englanniksi)", "Kojootti vs. ACME (Dub)",
                          "Kojootti vs. ACME ENGLANNIKSI", "Kojootti vs. ACME, suomeksi",
                          "Kojootti vs. ACME (suomeksi puhuttu)"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.clean(published), "Kojootti vs. ACME")
        self.assertEqual(enrich_tmdb.clean("Gråben vs. ACME (på svenska)"),
                         "Gråben vs. ACME")

    def test_the_published_title_still_keys_the_entry(self):
        """clean() touches the search string only. The three runs stay three cache
        entries, or the cache and normTitle() in index.html part company."""
        marked = "Kojootti vs ACME Orginaali äänillä"
        self.assertEqual(enrich_tmdb.norm(marked),
                         "kojootti vs acme orginaali äänillä")
        self.assertNotEqual(enrich_tmdb.norm(marked), enrich_tmdb.norm("Kojootti vs ACME"))
        self.assertNotEqual(enrich_tmdb.norm("Kojootti vs. ACME (eng)"),
                            enrich_tmdb.norm("Kojootti vs. ACME (sub)"))


class ScreeningMarkerTest(unittest.TestCase):
    """Two more spellings of "this is a film screening", both found on the live site on
    2026-09-19 as cards with an initials tile and no score.

    Neither changes the published title: `clean` touches the search string only, and
    `norm` keys the cache, `films-extra.json` and `normTitle()` on what the cinema wrote.
    """

    def test_tmb_spells_the_finnish_marker_as_a_sentence(self):
        """16 showtimes across Toijala, Sampo, Mania and Elo, every one unmatched, while
        the chains writing `(suomeksi)` matched 1204680 from the first run."""
        self.assertEqual(enrich_tmdb.clean("Kojootti vs ACME (Puhumme suomea!)"),
                         "Kojootti vs ACME")
        self.assertEqual(enrich_tmdb.clean("Kojootti vs ACME (Puhumme suomea)"),
                         "Kojootti vs ACME")

    def test_a_calendar_names_the_event_and_the_noun_comes_off(self):
        """Tähti Kino's three rows on 2026-09-19, in both spellings the same page used."""
        for published, want in (
                ("Hetki ennen valoa -elokuvanäytös", "Hetki ennen valoa"),
                ("Presidentin kyyditys -elokuvan näytös", "Presidentin kyyditys"),
                ("Ryhmä Hau: Dinoelokuva -elokuvanäytös", "Ryhmä Hau: Dinoelokuva")):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.clean(published), want)

    def test_the_published_title_is_not_touched(self):
        """The key has to stay what the cinema wrote, or the cache and the client part."""
        for published in ("Kojootti vs ACME (Puhumme suomea!)",
                          "Hetki ennen valoa -elokuvanäytös"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.norm(published),
                                 enrich_tmdb.norm(published.lower()))
                self.assertIn("elokuvan" if "elokuvan" in published.lower() else "puhumme",
                              enrich_tmdb.norm(published))

    def test_a_film_whose_own_name_is_the_noun_keeps_it(self):
        """Anchored to the end and requiring the dash: nothing else is a marker."""
        self.assertEqual(enrich_tmdb.clean("Elokuvanäytös"), "Elokuvanäytös")
        self.assertEqual(enrich_tmdb.clean("Kesän viimeinen elokuvanäytös"),
                         "Kesän viimeinen elokuvanäytös")

    def test_an_opera_relay_keeps_its_parenthesis(self):
        """TMB's two opera rows are correctly unmatched and must stay as published: the
        parenthesis names the festival and the composer, not the audio."""
        t = "Ooppera: Don Giovanni (Vicenza festivaali / Mozart)"
        self.assertEqual(enrich_tmdb.clean(t), t)


class ParenthesisedStrandTest(unittest.TestCase):
    """A strand can sit in a trailing parenthesis instead of in front of a colon.

    Laitilan Kino publishes its whole fortnightly programme as "<film> (Kahvi ja Kino)",
    so this is not one title but every title that cinema will ever publish. The content
    is matched against the one shared list in strands.py, so a parenthesis holding
    anything else is left alone.
    """

    def test_a_listed_strand_in_a_trailing_parenthesis_comes_off(self):
        self.assertEqual(enrich_tmdb.clean("Lapin sota (Kahvi ja Kino)"), "Lapin sota")
        self.assertEqual(enrich_tmdb.clean("Presidentin kyyditys (Kahvi ja Kino)"),
                         "Presidentin kyyditys")

    def test_the_same_strand_still_comes_off_in_front_of_a_colon(self):
        """One list, both positions: the entry added for the parenthesis has to keep
        working where strands.split() reads it."""
        self.assertEqual(enrich_tmdb.clean("Kahvi ja Kino: Lapin sota"), "Lapin sota")

    def test_a_parenthesis_that_is_not_a_listed_strand_is_left_alone(self):
        """Every one of these is in the committed data and every one is part of the
        title or a note about the screening, not a strand."""
        for published in ("Beginnings (Begyndelser)",
                          "Nirvana 'Nevermind' (35th Anniversary)",
                          "Burleskino: Gypsy (+keskusteluvieras)",
                          "Svečias – The Visitor (tekstitys suomi & englanti)"):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.clean(published), published)

    def test_a_title_that_is_only_a_strand_is_not_emptied(self):
        """Stripping it would leave nothing to search, so the published title stands."""
        self.assertEqual(enrich_tmdb.clean("(Kahvi ja Kino)"), "(Kahvi ja Kino)")

    def test_a_strand_that_is_not_at_the_end_is_left_alone(self):
        """The rule cuts everything from the parenthesis onwards, which is only safe
        when the parenthesis is last. Unanchored it would take "osa 2" off this title
        as well, and the published title would lose a word it needs."""
        self.assertEqual(enrich_tmdb.clean("Lapin sota (Kahvi ja Kino) osa 2"),
                         "Lapin sota (Kahvi ja Kino) osa 2")

    def test_the_marker_stays_in_the_cache_key(self):
        """Same rule as the year and the prefix: only the search string is cleaned."""
        for published in ("Lapin sota (Kahvi ja Kino)", "Kojootti vs. ACME ENGLANNIKSI",
                          "Gråben vs. ACME (på svenska)"):
            with self.subTest(published=published):
                self.assertNotEqual(enrich_tmdb.norm(published),
                                    enrich_tmdb.norm(enrich_tmdb.clean(published)))

    def test_the_raw_title_is_still_the_last_candidate(self):
        q = enrich_tmdb.queries("Lapin sota (Kahvi ja Kino)")
        self.assertEqual(q[0], "Lapin sota")
        self.assertEqual(q[-1], "Lapin sota (Kahvi ja Kino)")


class AliasTest(unittest.TestCase):
    """The two cases the cleaned search still cannot settle, 2026-09-14."""

    def test_the_aliases_are_keyed_by_the_published_title(self):
        """The Avengers id moved from 1769545 to 299534 on 2026-09-19: TMDB deleted
        1769545 and /movie/1769545 answers status_code 34, which is the 404 line
        run-enrich.log carries, while 299534 registers the encore on its own
        alternative_titles. 64 committed showtimes were on the dead id. No alias in this
        file may point at it again."""
        import json
        import pathlib
        aliases = json.loads((pathlib.Path(enrich_tmdb.__file__).parent
                              / "tmdb-aliases.json").read_text(encoding="utf-8"))
        for published, tmdb_id in (("Matka Piemonteen (Kahvi ja Kino)", "1545391"),
                                   ("Avengers: Endgame Re-release (encore)", "299534"),
                                   ("Avengers: Endgame Encore (re-release)", "299534"),
                                   ("AVENGERS: ENDGAME ENCORE (Re-release 2026)", "299534")):
            with self.subTest(published=published):
                self.assertEqual(aliases.get(enrich_tmdb.norm(published)), tmdb_id)
        self.assertNotIn("1769545", aliases.values())

    def test_the_three_strands_added_on_2026_09_19_split_and_the_refused_ones_do_not(self):
        """Three programme names went into the shared list and five words were measured
        and refused on the same pass. The refusals are the half worth pinning: splitting
        "Klassikkoelokuva" leaves "Solaris", which pick() resolves to Soderbergh's 2002
        record as an *exact* match, so the row would publish the wrong film rather than an
        initials tile; and "Ooppera", "Baletti" and "Konsertti" are part of TMDB's own
        registered Finnish relay titles, so stripping one turns a working match into a
        miss. Asserted through queries(), which is where clean() reads the same list."""
        for published, first in (
                ("KUUKAUDEN POHJOISMAINEN: The Last Paradise on Earth",
                 "The Last Paradise on Earth"),
                ("Nordic Film of the Month: Alt Skal Bort (2025)", "Alt Skal Bort"),
                ("Star House Movie: Ortotopologian loputtomat alkeet",
                 "Ortotopologian loputtomat alkeet")):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.queries(published)[0], first)
        for published in ("Klassikkoelokuva: Solaris", "Ooppera: Idomeneo",
                          "Baletti: Aikamme sankari", "Konsertti: Il Volo",
                          "R&A: Mouse"):
            with self.subTest(refused=published):
                self.assertEqual(enrich_tmdb.queries(published)[0], published)

    def test_the_two_standing_series_added_on_2026_09_19_split(self):
        """Riviera's Leffabrunssi and Kino Laika's Kino Iglu are repeating programmes, so
        the prefix comes off here. Kuvakukko's Vilimit-festivaali is one week a year and
        is deliberately not in the list: its rows are aliased, and this pins that choice
        so the festival is not added on a later pass."""
        for published, first in (
                ("Leffabrunssi: Paholainen pukeutuu Pradaan (2006)",
                 "Paholainen pukeutuu Pradaan"),
                ("Leffabrunssi: Sex and the City (2008)", "Sex and the City"),
                ("Kino Iglu: Tokyo Story", "Tokyo Story")):
            with self.subTest(published=published):
                self.assertEqual(enrich_tmdb.queries(published)[0], first)
        self.assertEqual(enrich_tmdb.queries("Vilimit-festivaali: Aavesoturi (1987)")[0],
                         "Vilimit-festivaali: Aavesoturi")

    def test_the_year_survives_the_strand_and_the_cache_key_keeps_it(self):
        """The half that stops two years of one title folding. The trailing year leaves
        the *search string* through PAREN_NOISE but stays in the published year, which is
        what separates The Devil Wears Prada from its 2026 sequel, and stays in norm(),
        which is what keeps two such rows on separate cache keys."""
        published = "Leffabrunssi: Paholainen pukeutuu Pradaan (2006)"
        self.assertEqual(enrich_tmdb.published_year({"title": published}), "2006")
        self.assertEqual(enrich_tmdb.norm(published),
                         "leffabrunssi paholainen pukeutuu pradaan 2006")
        self.assertNotEqual(enrich_tmdb.norm(published),
                            enrich_tmdb.norm("Leffabrunssi: Paholainen pukeutuu Pradaan (2026)"))

    def test_an_alias_is_tried_before_the_cleaned_title(self):
        """A bare id skips the search outright; a replacement string goes first."""
        q = enrich_tmdb.queries("Matka Piemonteen (Kahvi ja Kino)", alias="Resan till Piemonte")
        self.assertEqual(q[0], "Resan till Piemonte")


if __name__ == "__main__":
    unittest.main()
