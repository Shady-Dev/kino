"""Every served page carries a Content-Security-Policy that names its inline scripts.

The policy is a meta tag, the only lever on GitHub Pages. It allows inline scripts by hash
alone, so one edited without `scripts/check_csp.py --sync` stops running in the browser.
CI runs the same check over every served page; this suite holds the checker itself.
"""
import base64
import hashlib
import re
import unittest

import _ctx
import build_pages
import check_csp

PAGE = """<!DOCTYPE html>
<html lang="fi">
<head>
<meta charset="UTF-8">
<title>t</title>
<script>var a=1;</script>
<script type="application/ld+json">{"@type":"WebSite"}</script>
<script src="/pageview.js" async></script>
</head>
<body><p>x</p><script>var b=2;</script><script>var a=1;</script></body>
</html>
"""


def sha(js):
    return "'sha256-" + base64.b64encode(hashlib.sha256(js.encode()).digest()).decode() + "'"


class PolicyTest(unittest.TestCase):
    def test_each_running_inline_script_is_hashed_once_in_page_order(self):
        self.assertEqual(check_csp.script_hashes(PAGE), [sha("var a=1;"), sha("var b=2;")])

    def test_the_policy_is_strict_where_it_can_be(self):
        p = check_csp.policy(PAGE)
        script = re.search(r"script-src ([^;]*)", p).group(1).split()
        self.assertEqual(script, ["'self'", sha("var a=1;"), sha("var b=2;"),
                                  "https://eu-assets.i.posthog.com"])
        for directive in ("default-src 'self'", "object-src 'none'", "base-uri 'self'",
                          "form-action 'self'", "img-src 'self';",
                          "connect-src 'self' https://eu.i.posthog.com;"):
            self.assertIn(directive, p)
        self.assertNotIn("unsafe-eval", p)
        self.assertNotIn("frame-ancestors", p, "ignored in a meta tag")
        self.assertNotIn("data:", p)

    def test_with_policy_places_the_tag_after_charset_and_before_any_script(self):
        page = check_csp.with_policy(PAGE)
        self.assertEqual(check_csp.problems(page), [])
        head = page.split("\n")
        self.assertEqual(head[3], '<meta charset="UTF-8">')
        self.assertTrue(head[4].startswith('<meta http-equiv="Content-Security-Policy"'))
        self.assertEqual(check_csp.with_policy(page), page, "a second pass changes nothing")

    def test_a_page_with_no_tag_fails(self):
        self.assertEqual(check_csp.problems(PAGE), ["no Content-Security-Policy meta tag"])

    def test_an_added_or_edited_inline_script_fails_until_synced(self):
        page = check_csp.with_policy(PAGE)
        for changed in (page.replace("</body>", "<script>alert(1)</script></body>"),
                        page.replace("var b=2;", "var b=3;")):
            self.assertEqual(len(check_csp.problems(changed)), 1)
            self.assertEqual(check_csp.problems(check_csp.with_policy(changed)), [])

    def test_a_tag_after_a_script_fails(self):
        page = check_csp.with_policy(PAGE)
        tag = check_csp.TAG_RE.search(page).group(0)
        moved = page.replace(tag, "").replace("</head>", tag + "</head>")
        self.assertIn("the policy comes after a script, style or link, which it does not cover",
                      check_csp.problems(moved))

    def test_two_tags_fail(self):
        page = check_csp.with_policy(PAGE)
        tag = check_csp.TAG_RE.search(page).group(0)
        self.assertEqual(check_csp.problems(page.replace(tag, tag + tag)),
                         ["2 Content-Security-Policy meta tags"])


class ServedPagesTest(unittest.TestCase):
    def test_every_served_page_carries_its_policy(self):
        pages = check_csp.served()
        names = {p.relative_to(_ctx.ROOT).as_posix() for p in pages}
        self.assertTrue({"index.html", "status/index.html", "tietosuoja/index.html"} <= names)
        self.assertGreater(sum(n.startswith(("teatteri/", "kaupunki/", "en/", "sv/"))
                               for n in names), 3)
        for p in pages:
            with self.subTest(page=p.relative_to(_ctx.ROOT).as_posix()):
                self.assertEqual(check_csp.problems(p.read_text(encoding="utf-8")), [])

    def test_no_served_page_carries_an_inline_event_handler(self):
        """A handler attribute is inline script the policy blocks. index.html builds markup in
        template literals, so its source is read as well as its static tags."""
        handler = re.compile(r"""<[a-z][^<>]*\son[a-z]+\s*=\s*["']""", re.I)
        for p in check_csp.served():
            with self.subTest(page=p.relative_to(_ctx.ROOT).as_posix()):
                self.assertIsNone(handler.search(p.read_text(encoding="utf-8")))

    def test_a_built_redirect_page_carries_its_policy(self):
        """The landing pages are covered by the served-page test after a build; this one
        has no inline script and still carries the tag."""
        page = build_pages.redirect_page("fi", "/teatteri/kino/", "Kino")
        self.assertEqual(check_csp.problems(page), [])
        self.assertEqual(check_csp.script_hashes(page), [])


if __name__ == "__main__":
    unittest.main()
