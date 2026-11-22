"""`common.web_url` is the one scheme test for a link or picture address, and every place
the pages and the show contract publish one goes through it.

The page generator tested `url.startswith("http")`, which `httpx:alert(1)` and
`http:alert(1)` pass, and deleting either guard left every test green (review L10,
2026-11-22). The contract already refused both, so this was defence in depth.
"""
import datetime
import json
import unittest

import _ctx                                                # noqa: F401
import build_pages as bp
import common

HOSTILE = ("javascript:alert(1)", "httpx:alert(1)", "http:alert(1)", "JavaScript:alert(1)",
           " javascript:alert(1)", "//example.org/x", "data:text/html,x")
TODAY = datetime.date(2026, 8, 31)


def show(url):
    return dict(title="Film", start="2026-08-31T18:00:00+03:00", price="", aud="",
                venueLabel="Kino Testi", venueProvider="testi", url=url, lang="")


class WebUrlTest(unittest.TestCase):

    def test_absolute_http_and_https_with_a_host_pass(self):
        for url in ("https://example.org/x", "http://example.org", "HTTPS://example.org/a?b=1"):
            with self.subTest(url=url):
                self.assertTrue(common.web_url(url))

    def test_anything_else_is_refused(self):
        for url in HOSTILE + ("", None, 5, "https:/example.org", "/relative"):
            with self.subTest(url=url):
                self.assertFalse(common.web_url(url))


class PagesUseItTest(unittest.TestCase):
    """One case per place a page writes a provider URL."""

    def test_a_ticket_stub_links_only_a_web_url(self):
        for url in HOSTILE:
            with self.subTest(url=url):
                html = bp.film_block("Film", [show(url)], {}, {}, "fi", bp.L["fi"], False,
                                     set(), current_year=2026)
                self.assertNotIn("href=", html.split('class="stub')[1].split("</li>")[0])
        html = bp.film_block("Film", [show("https://example.org/t")], {}, {}, "fi",
                             bp.L["fi"], False, set(), current_year=2026)
        self.assertIn('href="https://example.org/t"', html)

    def test_a_later_screening_links_only_a_web_url(self):
        for url in HOSTILE:
            with self.subTest(url=url):
                self.assertNotIn("href=", bp.later_item(show(url), bp.L["fi"], "fi"))
        self.assertIn('href="https://example.org/t"',
                      bp.later_item(show("https://example.org/t"), bp.L["fi"], "fi"))

    def test_json_ld_carries_only_a_web_url(self):
        def events(url):
            days = {TODAY.isoformat(): {("Film", False): [
                {"theatre": "Kino Testi", "start": f"{TODAY.isoformat()}T18:00:00", "url": url}]}}
            graph = json.loads(bp.ld_json(days, TODAY, "Helsinki", {}))["@graph"]
            return [n for n in graph if n.get("@type") == "ScreeningEvent"]
        for url in HOSTILE:
            with self.subTest(url=url):
                self.assertTrue(events(url))
                self.assertFalse([e for e in events(url) if "url" in e])
        self.assertEqual(events("https://example.org/t")[0]["url"], "https://example.org/t")

    def test_a_poster_address_in_markup_is_only_a_web_url(self):
        for url in HOSTILE:
            with self.subTest(url=url):
                self.assertIsNone(bp.poster_url({"title": "Film", "img": url}, {}))
        self.assertEqual(bp.poster_url({"title": "Film", "img": "https://img.test/p.jpg"}, {}),
                         "https://img.test/p.jpg")


class NoPrefixTestTest(unittest.TestCase):

    def test_build_pages_has_no_http_prefix_test_but_the_unmirrored_count(self):
        """`_unmirrored` only counts a remote reference and never writes it out."""
        import ast
        tree = ast.parse((_ctx.ROOT / "scripts/build_pages.py").read_text(encoding="utf-8"))
        found = []
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef) or fn.name == "_unmirrored":
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "startswith" \
                        and node.args and isinstance(node.args[0], ast.Constant) \
                        and str(node.args[0].value).startswith("http"):
                    found.append((fn.name, node.lineno))
        self.assertEqual(found, [], "test a published address with common.web_url")


if __name__ == "__main__":
    unittest.main()
