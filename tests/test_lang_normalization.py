"""Four codes in the committed data were not in the client's name table, and each was a
defect somewhere else (measured 2026-09-02): `TU` and `MA` are Finnkino's own vocabulary
for Turkish and Malayalam, `XX` is Nexxo's "no subtitles", `LT` is Lithuanian and simply
missing. The app showed all four raw; the landing pages aliased them. These tests pin the
fixes at their sources and the aliases that stay until the committed data has turned over.

Provider modules are imported inside the tests rather than at module level: they bind
`common.EmptyProgramme` at import time and `test_common_fetch` reloads `common`, so a
module-level import here would make the suite's result depend on file order.
"""
import re
import unittest
from itertools import product
from string import ascii_uppercase

import _ctx


HTML = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")


def client_tables():
    """`LN.fi`, `LN.sv` and `LN.en` read out of index.html, in source order."""
    block = re.search(r"const LN = \{(.*?)\n  \};", HTML, re.S).group(1)
    out = {}
    for lang in ("fi", "sv", "en"):
        body = re.search(rf"\b{lang}:\{{(.*?)\}}", block, re.S).group(1)
        out[lang] = dict(re.findall(r"([A-Z]{2}):'([^']*)'", body))
    return out


class FinnkinoLangTagTest(unittest.TestCase):
    """`fetch_data.lang_tag`: the OCAPI attribute becomes this app's tag, with Finnkino's
    non-ISO codes mapped on the way. `SE` -> `SV` has worked this way since 2026-08-29."""

    def tag(self, lbl):
        import fetch_data
        return fetch_data.lang_tag(lbl)

    def test_tu_is_turkish_in_both_roles(self):
        self.assertEqual(self.tag(".TU-A"), "TR-A")
        self.assertEqual(self.tag(".TU-S"), "TR-S")

    def test_ma_is_malayalam_in_both_roles(self):
        self.assertEqual(self.tag(".MA-A"), "ML-A")
        self.assertEqual(self.tag(".MA-S"), "ML-S")

    def test_swedish_still_maps_and_a_compound_keeps_its_shape(self):
        self.assertEqual(self.tag(".FI-SE-A"), "FI-SV-A")
        self.assertEqual(self.tag(".TU-SE-S"), "TR-SV-S")
        self.assertEqual(self.tag(".FI-S"), "FI-S")
        self.assertEqual(self.tag("EN-A"), "EN-A")

    def test_no_other_code_changes(self):
        """Every other two-letter code passes through untouched, in both roles."""
        import fetch_data
        for a, b in product(ascii_uppercase, repeat=2):
            code = a + b
            if code in fetch_data.FINNKINO_LANG:
                continue
            with self.subTest(code=code):
                self.assertEqual(self.tag(f".{code}-A"), f"{code}-A")
                self.assertEqual(self.tag(f".{code}-S"), f"{code}-S")

    def test_the_map_is_exactly_these_three(self):
        """Adding a fourth is a decision about Finnkino's vocabulary and gets written
        here first."""
        import fetch_data
        self.assertEqual(fetch_data.FINNKINO_LANG, {"SE": "SV", "TU": "TR", "MA": "ML"})


class NexxoLangTest(unittest.TestCase):
    """`nexxo._lang`: code_language / code_subtitles -> `FI-A, SV-S`. `XX` in the subtitle
    column means no subtitles and produces nothing."""

    TAG_LIST = re.compile(r"^[A-Z]{2}-[AS](?:, [A-Z]{2}-[AS])*$")

    def lang(self, language, subtitles):
        import nexxo
        return nexxo._lang({"code_language": language, "code_subtitles": subtitles})

    def test_xx_subtitles_vanish_and_leave_no_separator(self):
        self.assertEqual(self.lang("FI", "XX"), "FI-A")
        self.assertEqual(self.lang("EN", "XX"), "EN-A")
        self.assertEqual(self.lang("SV", "XX"), "SV-A")

    def test_xx_alone_publishes_the_value_a_row_without_languages_already_has(self):
        self.assertEqual(self.lang("", "XX"), "")
        self.assertEqual(self.lang(None, "XX"), "")
        self.assertEqual(self.lang("OV", "XX"), "")

    def test_xx_beside_a_real_subtitle_code_drops_only_itself(self):
        self.assertEqual(self.lang("FI", "XX/SE"), "FI-A, SV-S")
        self.assertEqual(self.lang("FI", "SE/XX"), "FI-A, SV-S")
        self.assertEqual(self.lang("FI-SE", "XX"), "FI-A, SV-A")

    def test_existing_semantics_are_untouched(self):
        """Compounds split, SE becomes SV, OV is unspecified and dropped, LT passes as
        the real code it is, and duplicates are kept here: the renderers collapse them."""
        self.assertEqual(self.lang("FI", "SE"), "FI-A, SV-S")
        self.assertEqual(self.lang("FI-SE", "FI"), "FI-A, SV-A, FI-S")
        self.assertEqual(self.lang("OV", "FI"), "FI-S")
        self.assertEqual(self.lang("LT", "FI"), "LT-A, FI-S")
        self.assertEqual(self.lang("FI/FI", "FI"), "FI-A, FI-A, FI-S")
        self.assertEqual(self.lang("", ""), "")
        self.assertEqual(self.lang(None, None), "")

    def test_every_output_is_a_well_formed_tag_list_or_empty(self):
        cases = [("FI", "XX"), ("", "XX"), ("OV", "XX"), ("FI", "XX/SE"), ("FI-SE", "XX"),
                 ("EN", "FI/XX"), ("SV", "XX"), ("FI", "SE"), ("", "")]
        for language, subtitles in cases:
            with self.subTest(language=language, subtitles=subtitles):
                out = self.lang(language, subtitles)
                self.assertTrue(out == "" or self.TAG_LIST.match(out), repr(out))


class NameTableTest(unittest.TestCase):
    """The client's `LN` gained LT and ML in all three UI languages; the generator's
    mirror is held equal to fi and en by `tests/test_landing_pages.py`."""

    def test_lt_and_ml_have_names_in_every_client_table(self):
        t = client_tables()
        self.assertEqual((t["fi"]["LT"], t["fi"]["ML"]), ("liettua", "malajalam"))
        self.assertEqual((t["sv"]["LT"], t["sv"]["ML"]), ("litauiska", "malayalam"))
        self.assertEqual((t["en"]["LT"], t["en"]["ML"]), ("Lithuanian", "Malayalam"))

    def test_the_three_tables_share_one_key_order_and_the_new_codes_come_last(self):
        """Ordering preserved: the existing keys keep their sequence in every table and the
        additions are appended, so a diff of the tables reads as two entries."""
        t = client_tables()
        self.assertEqual(list(t["fi"]), list(t["sv"]))
        self.assertEqual(list(t["fi"]), list(t["en"]))
        self.assertEqual(list(t["fi"])[-2:], ["LT", "ML"])
        self.assertEqual(len(t["fi"]), 26)

    def test_the_names_follow_the_tables_style(self):
        """Lower-case nominatives in fi and sv, capitalised in en, like every neighbour."""
        t = client_tables()
        for code in ("LT", "ML"):
            with self.subTest(code=code):
                self.assertTrue(t["fi"][code].islower() and t["sv"][code].islower())
                self.assertTrue(t["en"][code][0].isupper())

    def test_the_new_names_render_through_the_generator(self):
        import build_pages as bp
        self.assertEqual(bp.lang_parts("LT-A, FI-S", "fi"), ["liettua", "tekstitys suomi"])
        self.assertEqual(bp.lang_parts("LT-A, FI-S", "en"), ["Lithuanian", "Finnish subtitles"])
        self.assertEqual(bp.lang_parts("ML-A, EN-S", "fi"), ["malajalam", "tekstitys englanti"])
        self.assertEqual(bp.lang_parts("ML-A, EN-S", "en"), ["Malayalam", "English subtitles"])


class GeneratorAliasTest(unittest.TestCase):
    """The landing-page aliases stay, unchanged, until the committed data holds none of
    TU, MA or XX. Their removal is a re-measure and a decision, written in IDEAS."""

    def test_the_alias_set_is_exactly_what_it_was(self):
        import build_pages as bp
        self.assertEqual(bp.CODE_ALIAS, {"TU": "TR", "MA": "ML"})
        self.assertEqual(bp.NO_SUBTITLES, {"XX"})
        self.assertEqual(bp.LN_EXTRA, {"fi": {"LT": "liettua", "ML": "malajalam"},
                                       "en": {"LT": "Lithuanian", "ML": "Malayalam"}})

    def test_the_aliases_agree_with_the_client(self):
        """An alias target has to be a code the client names, and an extra name has to
        be the client's own, or the two surfaces would call one language two things."""
        import build_pages as bp
        t = client_tables()
        for lang in ("fi", "en"):
            for code, name in bp.LN_EXTRA[lang].items():
                with self.subTest(lang=lang, code=code):
                    self.assertEqual(name, t[lang][code])
        for src, dst in bp.CODE_ALIAS.items():
            with self.subTest(src=src):
                self.assertIn(dst, t["fi"])
                self.assertIn(dst, t["en"])

    def test_legacy_codes_still_in_the_data_render_as_words(self):
        """The four shapes the committed data carries on 2026-09-02."""
        import build_pages as bp
        self.assertEqual(bp.lang_parts("FI-S, SV-S, TU-A", "fi"), ["turkki", "tekstitys suomi/ruotsi"])
        self.assertEqual(bp.lang_parts("EN-S, MA-A", "en"), ["Malayalam", "English subtitles"])
        self.assertEqual(bp.lang_parts("FI-A, XX-S", "fi"), ["suomi"])
        self.assertEqual(bp.lang_parts("XX-S", "en"), [])


if __name__ == "__main__":
    unittest.main()
