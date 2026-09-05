"""The Finnish interface copy, pinned after the 2026-09-05 language pass.

Two things a reader flagged and the pass removed from every Finnish string this repo
owns: "Napauta näytöstä" (device-specific, and it treats a screening as the control) and
"Kellonajasta" (a clock time is not what a reader chooses). Booking instructions refer to
the showtime -- "Näytösajasta lipunmyyntiin" -- and freshness messages describe the
showtime data ("näytöstiedot"), never the cinema. The client's `L.fi` block and the
generator's `L["fi"]` are read as they ship. Provider text is not touched by any of this.
"""
import re
import unittest

import _ctx                                                # noqa: F401
import build_pages as bp

HTML = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")

REJECTED = ("Napauta", "Kellonajasta", "aikataulu", "Aikataulu", "tekstit ")


def client_fi():
    """The Finnish block of the client's L table -> {key: string}."""
    start = HTML.index("\n    fi:{")
    end = HTML.index("\n    sv:{", start)
    return dict(re.findall(r"(\w+):'((?:[^'\\]|\\.)*)'", HTML[start:end]))


class ClientCopyTest(unittest.TestCase):
    def setUp(self):
        self.fi = client_fi()
        self.assertGreater(len(self.fi), 60)

    def test_no_rejected_form_survives(self):
        for key, text in self.fi.items():
            for bad in REJECTED:
                with self.subTest(key=key, bad=bad):
                    self.assertNotIn(bad, text)
        self.assertNotIn("Näytösajat suomalaisista", HTML)

    def test_booking_lines_refer_to_the_showtime(self):
        self.assertEqual(self.fi["actBuy"], "Näytösajasta lipunmyyntiin — {host}")
        self.assertEqual(self.fi["actReserve"], "Näytösajasta paikkavaraukseen — {host}")
        self.assertEqual(self.fi["actList"], "Näytösajasta teatterin ohjelmistoon — {host}")
        self.assertEqual(self.fi["actCombined"], "Näytösajasta teatterin omalle sivulle")
        self.assertEqual(self.fi["actAdmission"],
                         "Sisältyy pääsylippuun · Näytösajasta lippukauppaan — {host}")
        self.assertEqual(self.fi["tipAdmission"], "Osta pääsylippu")

    def test_freshness_lines_describe_the_data(self):
        self.assertEqual(self.fi["dataLabel"], "Näytöstiedot")
        self.assertEqual(self.fi["staleOne"], "näytöstiedot eivät ole päivittyneet")
        self.assertEqual(self.fi["behind"], "Vanhentuneet näytöstiedot")
        self.assertEqual(self.fi["partialSources"], "Osa näytöstiedoista ei päivittynyt")
        for key in ("allFresh", "partialOf", "unverifiedOf", "loadFail"):
            self.assertIn("näytöstie", self.fi[key].lower(), key)

    def test_controls_and_empty_states(self):
        self.assertEqual(self.fi["showPast"], "Näytä {n} aiempaa")
        self.assertEqual(self.fi["hidePast"], "Piilota aiemmat")
        self.assertEqual(self.fi["allIn"], "{city} – kaikki teatterit")
        self.assertEqual(self.fi["favOn"], "Oma teatteri valittu – avautuu jatkossa automaattisesti")
        self.assertEqual(self.fi["noshows"], "Valitussa teatterissa ei ole näytöksiä tänä päivänä.")
        self.assertEqual(self.fi["notpublished"], "Tämän päivän ohjelmistoa ei ole vielä julkaistu.")
        self.assertEqual(self.fi["sheetNone"], "Ei näytöksiä valitussa teatterissa.")
        self.assertIn("sheetNone:'", HTML[HTML.index("\n    sv:{"):])          # sv and en have it too
        self.assertEqual(HTML.count("sheetNone:'"), 3)
        self.assertIn("L[lang].sheetNone", HTML)

    def test_the_subtitle_word_is_a_label(self):
        self.assertIn("const LW = { fi:{S:'tekstitys:'}", HTML)
        self.assertIn('<div id="credit">Suomalaisten elokuvateatterien näytösajat</div>', HTML)


class GeneratorCopyTest(unittest.TestCase):
    def test_no_rejected_form_survives(self):
        for key, text in bp.L["fi"].items():
            if not isinstance(text, str):
                continue
            for bad in REJECTED:
                with self.subTest(key=key, bad=bad):
                    self.assertNotIn(bad, text)

    def test_intros_refer_to_the_showtime(self):
        fi = bp.L["fi"]
        for key in ("intro_buy", "intro_reserve", "intro_list", "city_intro"):
            self.assertIn("Näytösajasta pääset", fi[key], key)
        self.assertEqual(bp.venue_intro(fi, "admission", "x.fi"),
                         "Katso lähipäivien näytösajat. Esitykset sisältyvät pääsylippuun, "
                         "jonka voit ostaa sivustolta x.fi.")
        self.assertEqual(fi["age_note"], "Ikäraja {n} vuotta.")
        self.assertEqual(fi["subs"], "tekstitys: {}")
        self.assertIn("näytösajat", fi["venue_desc"])
        self.assertNotIn("kellonajat", fi["venue_desc"])


if __name__ == "__main__":
    unittest.main()
