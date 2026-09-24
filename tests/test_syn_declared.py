"""Adapters whose synopses are not all Finnish declare the language of each one.

A bare `_syn` string is filed as Finnish in films-extra.json, in a slot keyed by normalised
title that every chain showing the film reads. Read 2026-09-24: Kino Engel's
`BARNSÖNDAGAR` film pages carry a Swedish synopsis beside Finnish ones for everything
else, and the page declares neither (`<html lang="en-US">` on both kinds). Gilda's booking
feed carries English `description`s for 6 of 36 films and no language field, and Savon
Kinot's film pages carry English for one of 24. So each text is placed by
`common.syn_language`, and one it cannot place is withheld. Other eTiketti sites keep the
bare string: Niagara's bilingual `fi *** sv` blurbs would be outvoted into Swedish.
"""
import io
import unittest
from contextlib import redirect_stdout

import _ctx                                                # noqa: F401
import engel
import etiketti
import gilda
from test_etiketti_templates import HIDDEN, Stubbed, listing

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


def gilda_rows(*descriptions):
    films = []
    for n, desc in enumerate(descriptions):
        title = f"Elokuva {n}"
        films.append({"movie_id": n + 1, "movie_name": title, "description": desc,
                      "show_times": [{"movie_name": title, "cinema_screen_id": 66,
                                      "show_time": f"2026-09-26T1{n}:00:00Z",
                                      "screen_name": "Gilda 1", "rating_name": "12"}]})
    with redirect_stdout(io.StringIO()):
        per_venue = gilda.parse({"fi": {"data": films}}, gilda.SITES[0], {})
    return {r["title"]: r for rows in per_venue.values() for r in rows}


class GildaTest(unittest.TestCase):
    def test_each_description_is_filed_in_its_own_language(self):
        rows = gilda_rows(f"<p>{EN}</p>", f"<p>{FI}</p>", f"<p>{SV}</p>")
        self.assertEqual(rows["Elokuva 0"]["_syn"], {"en": EN})
        self.assertEqual(rows["Elokuva 1"]["_syn"], {"fi": FI})
        self.assertEqual(rows["Elokuva 2"]["_syn"], {"sv": SV})

    def test_a_description_no_language_settles_is_withheld(self):
        # "Not Supplied" is the feed's own placeholder, read 2026-09-24.
        rows = gilda_rows("<p>Not Supplied</p>", f"<p>{UNPLACED}</p>", f"<p>{FI}</p>")
        self.assertNotIn("_syn", rows["Elokuva 0"])
        self.assertNotIn("_syn", rows["Elokuva 1"])
        self.assertEqual(rows["Elokuva 2"]["_syn"], {"fi": FI}, "the next film is unaffected")


class EtikettiTest(Stubbed):
    def site(self, provider):
        return next(s for s in etiketti.SITES if s["provider"] == provider)

    def test_savon_kinot_declares_each_synopsis(self):
        site = self.site("savonkinot")
        self.assertEqual(etiketti.syn_value(site, EN), {"en": EN})
        self.assertEqual(etiketti.syn_value(site, FI), {"fi": FI})
        self.assertEqual(etiketti.syn_value(site, UNPLACED), "")

    def test_a_site_without_the_flag_keeps_the_bare_string(self):
        self.assertEqual(etiketti.syn_value(self.site("niagara"), EN), EN)
        self.assertEqual(etiketti.syn_value(self.site("niagara"), UNPLACED), UNPLACED)

    def test_fetch_site_publishes_the_declared_value(self):
        item = ('<div class="item joensuu date-26.9.2026"> <div> <p> <strong><span>LA 26.9. '
                'klo 18.00</span></strong> </p> <p> JOENSUU | TAPIO | TAPIO 3<br /> </p> </div> '
                '<div> <a class="button-screening" href="/salikartta?id=901"> Osta </a> </div> '
                "</div>")
        page = (f'<main><h1>Konsertti</h1><div class="description-container"><span>{EN}'
                f'</span></div><div class="screenings">{HIDDEN}{item}</div></main>')
        e = self.stub({"/elokuvat/ohjelmistossa": listing("/elokuvat/7/konsertti"),
                       "/elokuvat/7/konsertti": page})
        with redirect_stdout(io.StringIO()):
            out = e.fetch_site(self.site("savonkinot"), sleep=0)
        self.assertEqual([r["_syn"] for r in out["sk-tapio"]], [{"en": EN}])

    def test_only_savon_kinot_declares(self):
        # A site joins after a read of its own pages, as Savon Kinot's on 2026-09-24.
        self.assertEqual([s["provider"] for s in etiketti.SITES if s.get("declare_syn")],
                         ["savonkinot"])


if __name__ == "__main__":
    unittest.main()
