"""Adapters whose synopses are not all Finnish declare the language of each one.

A bare `_syn` string is filed as Finnish in films-extra.json, in a slot keyed by normalised
title that every chain showing the film reads. Read 2026-09-24: Kino Engel's
`BARNSÖNDAGAR` film pages carry a Swedish synopsis beside Finnish ones for everything
else, and the page declares neither (`<html lang="en-US">` on both kinds). So each text
is placed by `common.syn_language`, and one it cannot place is withheld.
"""
import unittest

import _ctx                                                # noqa: F401
import engel

SV = ("Efter en lång vinter tar familjen sig till skärgården, och där väntar ett äventyr "
      "som ingen av dem har räknat med.")
FI = ("Kun perhe lähtee saaristoon pitkän talven jälkeen, siellä odottaa seikkailu, jota "
      "kukaan ei osannut odottaa, ja kaikki muuttuu.")
EN = ("After a long winter the family travels to the islands, and there an adventure "
      "waits that none of them expected.")
# Long enough for Engel's 40-character floor, and no function word of any of the three.
UNPLACED = "Seikkailu saaristossa: perhe, talvi, meri, lokit, majakka ja myrsky."


def engel_page(text):
    return (f'<div class="cmd-desription"><h5>KOMEDIA,SEIKKAILU</h5>\n<p>{text}</p>\n'
            f"</div>")


class EngelTest(unittest.TestCase):
    def test_a_swedish_synopsis_is_filed_as_swedish(self):
        self.assertEqual(engel.details(engel_page(SV))["_syn"], {"sv": SV})

    def test_a_finnish_synopsis_is_filed_as_finnish(self):
        self.assertEqual(engel.details(engel_page(FI))["_syn"], {"fi": FI})

    def test_an_english_synopsis_is_filed_as_english(self):
        self.assertEqual(engel.details(engel_page(EN))["_syn"], {"en": EN})

    def test_a_synopsis_no_language_settles_is_withheld(self):
        d = engel.details(engel_page(UNPLACED))
        self.assertNotIn("_syn", d)
        self.assertEqual(d["genres"], "Komedia, Seikkailu", "the rest of the page stands")


if __name__ == "__main__":
    unittest.main()
