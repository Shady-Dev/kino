"""Gilda: the booking feed lists a film twice, and each copy drew its own stubs.

Read live on 2026-09-07 the feed held 39 film records for 33 distinct `movie_id`s: six
films arrived as two copies differing only in `premiere`, each carrying the same
`show_times`. Both parsed, so 44 of 183 rows were repeats and "Presidentin kyyditys"
showed twice at 14:40 in Gilda 3 on 12 September. The key is the screening rather than
the record: venue, start, film and auditorium.

The fixtures cover the shape the feed really has (one film_id, two records) and the
shape it could take instead (one record, a repeated show_time), plus the three cases that
must survive: a second start, a second auditorium and a second venue.
"""
import io
import unittest
from contextlib import redirect_stdout

import _ctx                                                # noqa: F401
import gilda

SITE = gilda.SITES[0]


def show(movie_id, name, when, screen=66, screen_name="Gilda 3", **extra):
    row = {"movie_id": movie_id, "movie_name": name, "original_title": name,
           "show_time": when, "cinema_screen_id": screen, "screen_name": screen_name,
           "running_time": 90, "rating_name": "12", "audio_lang": "fi",
           "subtitle_lang": "sv"}
    row.update(extra)
    return row


def payload(*films):
    return {"fi": {"data": list(films)}}


def film(movie_id, name, shows):
    return {"movie_id": movie_id, "movie_name": name, "genre": "Draama",
            "description": "", "movie_poster": "", "show_times": shows}


class GildaDuplicateTest(unittest.TestCase):
    def parse(self, doc):
        buf = io.StringIO()
        with redirect_stdout(buf):
            out = gilda.parse(doc, SITE)
        return out, buf.getvalue()

    def test_an_exact_repeat_is_one_screening(self):
        doc = payload(
            film(1513, "Presidentin kyyditys", [
                show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z"),
                show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z"),
            ]),
            film(1591, "Oasis", [
                show(1591, "Oasis", "2026-09-12T17:00:00Z", screen=67,
                     screen_name="Gilda 1"),
                show(1591, "Oasis", "2026-09-12T17:00:00Z", screen=67,
                     screen_name="Gilda 1"),
            ]),
        )
        out, log = self.parse(doc)
        starts = [(s["title"], s["start"], s["aud"]) for s in out["gd-gilda"]]
        self.assertEqual(len(starts), 2, starts)
        self.assertIn("dropped 2 duplicate showtime(s)", log)

    def test_a_repeat_that_differs_only_in_an_unread_field_is_still_one(self):
        """The key is the screening rather than the record: a feed that rebuilds its
        rows can change a field the stub never shows, and two 14:40s would still be
        drawn."""
        doc = payload(film(1513, "Presidentin kyyditys", [
            show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z"),
            show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z",
                 show_id=99, seats_available=12),
        ]))
        out, _ = self.parse(doc)
        self.assertEqual(len(out["gd-gilda"]), 1)

    def test_two_real_screenings_of_one_film_both_survive(self):
        """The guard must not swallow a matinee and an evening show, or the same film in
        two auditoriums at the same time."""
        doc = payload(film(1513, "Presidentin kyyditys", [
            show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z"),
            show(1513, "Presidentin kyyditys", "2026-09-12T17:40:00Z"),
            show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z", screen=67,
                 screen_name="Gilda 1"),
        ]))
        out, log = self.parse(doc)
        self.assertEqual(len(out["gd-gilda"]), 3)
        self.assertNotIn("duplicate", log)

    def test_the_same_start_in_another_venue_survives(self):
        """Screen 69 is Bio Rex Lasipalatsi, screen 66 is Gilda Kamppi, and two houses can
        run one film at one time. Both screen names repeat their venue here, which is what
        `_aud` blanks, so the venue is the only thing left telling the two rows apart: drop
        it from the key and one of these screenings disappears."""
        doc = payload(film(1513, "Presidentin kyyditys", [
            show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z", screen=66,
                 screen_name="Kamppi"),
            show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z", screen=69,
                 screen_name="Bio Rex Lasipalatsi (K-18)"),
        ]))
        out, log = self.parse(doc)
        self.assertEqual([s["aud"] for s in out["gd-gilda"]], [""])
        self.assertEqual([s["aud"] for s in out["gd-lasipalatsi"]], [""])
        self.assertNotIn("duplicate", log)

    def test_a_film_listed_twice_yields_one_set_of_rows(self):
        """The measured shape: the same movie_id as two records, differing in a field
        nothing here reads, each carrying the same showtimes."""
        shows = [show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z"),
                 show(1513, "Presidentin kyyditys", "2026-09-12T17:40:00Z")]
        a = film(1513, "Presidentin kyyditys", shows)
        b = dict(a, premiere="2026-09-12")
        out, log = self.parse(payload(a, b))
        self.assertEqual(len(out["gd-gilda"]), 2)
        self.assertIn("dropped 2 duplicate showtime(s)", log)

    def test_two_films_at_one_start_in_one_venue_both_survive(self):
        """Two screens of one house, both screen names blanked by `_aud` because they
        repeat the venue name. Venue, start and auditorium are then identical for two
        different films, so the film id is the only thing keeping both screenings: without
        it the second film is dropped as a repeat of the first."""
        doc = payload(
            film(1513, "Presidentin kyyditys", [
                show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z", screen=66,
                     screen_name="Kamppi")]),
            film(1591, "Oasis", [
                show(1591, "Oasis", "2026-09-12T11:40:00Z", screen=67,
                     screen_name="Kamppi")]),
        )
        out, log = self.parse(doc)
        self.assertEqual(sorted(s["title"] for s in out["gd-gilda"]),
                         ["Oasis", "Presidentin kyyditys"])
        self.assertNotIn("duplicate", log)

    def test_a_clean_feed_logs_nothing(self):
        doc = payload(film(1513, "Presidentin kyyditys", [
            show(1513, "Presidentin kyyditys", "2026-09-12T11:40:00Z"),
        ]))
        _, log = self.parse(doc)
        self.assertEqual(log, "")


class MethodTagsTest(unittest.TestCase):
    """`method` is split on " · " by the client (index.html, stubTags and the ticket
    glyphs). Joined with ", ", 3D plus a dub label was one tag nothing could read."""

    def test_a_format_and_a_dub_label_are_two_tags(self):
        self.assertEqual(gilda._method({"version_3d": 1, "movie_audio_style_name": "Dubattu"}),
                         "3D · Dubattu")

    def test_the_plain_audio_styles_add_no_tag(self):
        self.assertEqual(gilda._method({"version_imax": 1,
                                        "movie_audio_style_name": "Tekstitetty"}), "IMAX")


class ChangedFeedTest(unittest.TestCase):
    """A moved schema fails the site, and a row no venue claims is counted (review
    2026-11-22, M2). Both used to return a short or empty result with nothing in the log."""

    SHOWS = [show(1, "Oasis", "2026-11-22T17:00:00Z"),
             show(1, "Oasis", "2026-11-22T19:00:00Z", screen=70, screen_name="Gilda 4"),
             show(1, "Oasis", "2026-11-22T21:00:00Z", screen=71, screen_name="Gilda 5")]

    def test_a_feed_without_its_fi_key_fails(self):
        for doc in ({"data": [film(1, "Oasis", self.SHOWS)]}, {"fi": {"rows": []}}, []):
            with self.subTest(doc=str(doc)[:40]):
                with self.assertRaises(RuntimeError) as cm:
                    gilda.parse(doc, SITE)
                self.assertIn("schema moved", str(cm.exception))

    def test_an_empty_list_in_the_known_schema_is_not_an_error(self):
        self.assertEqual(gilda.parse(payload(), SITE), {})

    def test_a_show_on_an_unknown_screen_is_counted(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            out = gilda.parse(payload(film(1, "Oasis", self.SHOWS)), SITE)
        self.assertEqual([r["start"][11:16] for r in out["gd-gilda"]], ["19:00"])
        self.assertIn("2 showtime(s) left out: 1 on screen 70, 1 on screen 71", buf.getvalue())

    def test_nothing_placed_and_rows_left_out_fails(self):
        doc = payload(film(1, "Oasis", self.SHOWS[1:]))
        with self.assertRaises(RuntimeError) as cm:
            gilda.parse(doc, SITE)
        self.assertIn("no showtime placed", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
