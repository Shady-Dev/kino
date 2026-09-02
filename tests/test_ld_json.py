"""Provider text inside the JSON-LD block must not be able to close the element.

`ld_json()` output is embedded inside <script type="application/ld+json">, and the HTML
parser ends a script element at the first literal "</script>" regardless of the type
attribute. Titles, theatre names and booking URLs are provider text published verbatim
(the raw title is the enrichment key, so adapters cannot escape it at the source), which
made this the one sink where upstream data reached a script context unescaped -- every
other interpolation in the generator and the client already goes through esc() or
safeUrl(). The serializer therefore \\uXXXX-escapes the HTML-significant characters,
which is equivalent JSON: a consumer parses the identical value.
"""
import datetime
import json
import unittest

import _ctx                                                # noqa: F401
import build_pages as bp

HOSTILE = "Film </script><script>throw 1</script>"
TODAY = datetime.date(2026, 8, 31)


def days_with(title, theatre="Kino Testi"):
    return {TODAY.isoformat(): {title: [
        {"theatre": theatre, "start": f"{TODAY.isoformat()}T18:00:00",
         "url": "https://example.fi/tickets?a=1&b=2"},
    ]}}


class LdJsonEscapingTest(unittest.TestCase):
    def test_no_html_significant_bytes_survive(self):
        """"</script>" is only reachable through a literal "<", so none may remain --
        in a title, a theatre name, or a URL's query separator."""
        out = bp.ld_json(days_with(HOSTILE, theatre="Kino & <b>"), TODAY,
                         "Helsinki", {})
        for ch in "<>&":
            self.assertNotIn(ch, out)
        self.assertNotIn("</script", out.lower())

    def test_escaping_is_lossless(self):
        """The escapes are alternative JSON spellings, not sanitisation: a crawler
        parsing the block must see the exact provider strings."""
        out = bp.ld_json(days_with(HOSTILE, theatre="Kino & <b>"), TODAY,
                         "Helsinki", {})
        names = {n.get("name") for n in json.loads(out)["@graph"]}
        self.assertIn(HOSTILE, names)
        self.assertIn("Kino & <b>", names)

    def test_js_line_separators_are_escaped(self):
        """U+2028/U+2029 are legal in JSON but not in JavaScript source, and
        ensure_ascii=False would otherwise emit them raw."""
        title = "A\u2028B\u2029C"
        out = bp.ld_json(days_with(title), TODAY, "Helsinki", {})
        self.assertNotIn("\u2028", out)
        self.assertNotIn("\u2029", out)
        names = {n.get("name") for n in json.loads(out)["@graph"]}
        self.assertIn(title, names)

    def test_page_has_exactly_one_script_closer(self):
        """The whole-document property the escaping exists for: the only "</script>"
        closers are the ones page() writes itself -- one per script element it emits,
        the JSON-LD block and the two theme scripts -- and the hostile title adds none."""
        html = bp.page(
            lang="fi", path_fi="/teatteri/x/", path_en="/en/theatre/x/",
            title="X", desc="d", h1="h", sub="s", intro="i",
            days=days_with(HOSTILE), today=TODAY, t=bp.L["fi"], extra={},
            gmap={}, city="Helsinki", with_venue=False, legend="", also="",
            og_image="/icon-512.png", app_href="/", area="x", chain_css="")
        self.assertEqual(html.lower().count("</script>"), html.lower().count("<script"))
        self.assertEqual(html.lower().count("</script>"), 3)


if __name__ == "__main__":
    unittest.main()
