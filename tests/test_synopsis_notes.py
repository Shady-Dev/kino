"""A screening note is not a synopsis (2026-09-03).

`films-extra.json` holds one Finnish synopsis per normalised title, filled by the first
provider to publish one and read by every cinema showing the film. Gilda's senior-screening
entries open with a paragraph of the cinema's own -- "Gildan seniorikinonäytökset joka kuun
ensimmäisenä tiistaina. Elokuvaliput ... 9€/kpl. Lipun hintaan sisältyy leffakahvit!" --
before the distributor's blurb, and a screening sometimes carries the plain film title, so
that paragraph landed in the shared slot for "Keltaiset kirjeet" and Cinema Niagara showed
Gilda's price. Fill-if-empty then kept it there. Bio Vuoksi's "Liput 8€ maksetaan
Pennittömien edustajalle" is the same class from another adapter.

Two rules, at two layers. Structural, at the adapter: Gilda's description is HTML with
paragraphs, and a paragraph that quotes a price or names the cinema is dropped whole.
Generic, at the merge: text that quotes a price never enters the shared slot at all, and
is counted in the log, so an adapter that strips paragraph boundaries before merging cannot
leak a price either. The slot stays empty for TMDB.

The Gilda test goes through `parse()` with a two-paragraph description, so the adapter's
call site is exercised rather than only the helper. Provider modules are imported inside
the tests: they bind `common.EmptyProgramme` at import time and test_common_fetch reloads
`common`.
"""
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

import _ctx


PROMO = ("<p>Gildan seniorikinon&auml;yt&ouml;kset joka kuun ensimm&auml;isen&auml; tiistaina. "
         "Elokuvaliput seniorikinon n&auml;yt&ouml;ksiin saat hintaan 9&euro;/kpl. "
         "Lipun hintaan sisältyy leffakahvit!</p>")
BLURB1 = "<p>Derya on Ankaran suurimman teatterin t&auml;hti.&nbsp;</p>"
BLURB2 = "<p>KELTAISET KIRJEET on kuvaus el&auml;m&auml;st&auml; autorit&auml;&auml;risen yhteiskunnan puristuksissa.</p>"


class DropNotesHtmlTest(unittest.TestCase):

    def test_the_price_paragraph_goes_and_the_blurb_stays_in_order(self):
        import synmerge
        out = synmerge.drop_notes_html(PROMO + " " + BLURB1 + " " + BLURB2, names=("Gilda",))
        self.assertEqual(out, "Derya on Ankaran suurimman teatterin tähti. "
                              "KELTAISET KIRJEET on kuvaus elämästä autoritäärisen yhteiskunnan puristuksissa.")

    def test_a_paragraph_naming_the_cinema_goes_without_a_price(self):
        import synmerge
        desc = "<p>Koe eepos 70mm-filmilt&auml;. Vain Gildan Bio Rex Lasipalatsissa.</p><p>Nolanin eepos.</p>"
        self.assertEqual(synmerge.drop_notes_html(desc, names=("Gilda",)), "Nolanin eepos.")
        # The stem is a word prefix, so "Gildan" matches "Gilda" and "gildattu" would not
        # match a name that is not a prefix of it.
        self.assertEqual(synmerge.drop_notes_html("<p>Elokuva on gildattu.</p>", names=("Gilda",)), "")
        self.assertEqual(synmerge.drop_notes_html("<p>Elokuva on kullattu.</p>", names=("Gilda",)),
                         "Elokuva on kullattu.")

    def test_text_without_paragraphs_is_one_paragraph(self):
        import synmerge
        self.assertEqual(synmerge.drop_notes_html("Pelkk&auml;&nbsp;teksti.", names=("Gilda",)), "Pelkkä teksti.")
        self.assertEqual(synmerge.drop_notes_html("Liput 8€ ovelta.", names=()), "")
        self.assertEqual(synmerge.drop_notes_html("", names=("Gilda",)), "")

    def test_is_note_reads_a_price_in_either_order_and_nothing_else(self):
        import synmerge
        for s in ("Liput 8€ ovelta", "hintaan 9 €/kpl", "vain 12 euroa", "€ 10 ovelta", "5 EUR"):
            self.assertTrue(synmerge.is_note(s), s)
        for s in ("Vuonna 1930 Ankarassa", "72 tuntia ennen h-hetkeä", "Ainoa näytös, klubialennus.", ""):
            self.assertFalse(synmerge.is_note(s), s)


class MergeRefusesNotesTest(unittest.TestCase):

    def run_merge(self, shows):
        import synmerge
        synmerge.reset()
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            buf = io.StringIO()
            with redirect_stdout(buf):
                synmerge.merge(out, {"v1": shows}, "test")
            doc = json.loads((out / "films-extra.json").read_text())
        return doc["films"], buf.getvalue()

    def test_a_priced_text_never_enters_the_shared_slot(self):
        films, log = self.run_merge([
            {"title": "Nouvelle Vague", "_syn": "Juhlanäytös! Liput 8€ maksetaan ovella."},
            {"title": "Autofiktio", "_syn": "Almodóvarin melodraama."},
        ])
        self.assertNotIn("nouvelle vague", films)
        self.assertEqual(films["autofiktio"]["s"]["fi"], "Almodóvarin melodraama.")
        self.assertIn("[test] synopses merged: 1", log)
        self.assertIn("[test] synopses skipped as screening notes (price): 1", log)

    def test_the_skipped_line_is_silent_when_nothing_was_skipped(self):
        _, log = self.run_merge([{"title": "Autofiktio", "_syn": "Almodóvarin melodraama."}])
        self.assertIn("synopses merged: 1", log)
        self.assertNotIn("skipped", log)


class GildaParseTest(unittest.TestCase):

    def test_parse_drops_gildas_own_paragraph_from_the_synopsis(self):
        import gilda
        site = {"provider": "gilda", "base": "https://www.gilda.fi", "listing": "/",
                "venues": [{"id": "gd-gilda", "name": "Gilda Kamppi", "short": "Gilda", "screens": [1]}]}
        show = {"movie_name": "Keltaiset Kirjeet", "cinema_screen_id": 1, "show_is_visible": 1,
                "show_time": "2026-09-05T18:00:00+03:00", "running_time": 120,
                "screen_name": "Gilda 3", "rating_name": "12"}
        payload = {"fi": {"data": [
            {"movie_id": 1574, "movie_name": "Seniorikino: Keltaiset kirjeet",
             "description": PROMO + BLURB1 + BLURB2, "show_times": [show]},
            {"movie_id": 1575, "movie_name": "Toinen", "description": BLURB1, "show_times": [dict(show, movie_name="Toinen")]},
        ]}}
        per_venue = gilda.parse(payload, site)
        rows = per_venue.get("gd-gilda") or []
        self.assertEqual(len(rows), 2, per_venue)
        by_title = {r["title"]: r for r in rows}
        self.assertEqual(by_title["Keltaiset Kirjeet"]["_syn"],
                         "Derya on Ankaran suurimman teatterin tähti. "
                         "KELTAISET KIRJEET on kuvaus elämästä autoritäärisen yhteiskunnan puristuksissa.")
        self.assertEqual(by_title["Toinen"]["_syn"], "Derya on Ankaran suurimman teatterin tähti.")
        for r in rows:
            self.assertNotIn("€", r["_syn"]); self.assertNotIn("Gilda", r["_syn"])


if __name__ == "__main__":
    unittest.main()
