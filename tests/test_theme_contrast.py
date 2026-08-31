"""The accent is two colours, because one number cannot do two jobs.

`--accent` is chosen for a 3 px chain border and a focus ring, where WCAG 1.4.11 asks for
3:1. Light theme's #B8860B measures 3.04:1 on `--bg`, which clears that bar and fails the
4.5:1 that 1.4.3 asks of small text -- and eight rules were colouring text with it. Dark
theme never had the problem, so the failure was invisible to anyone developing in dark.

`--accent-text` is the same hue darkened until it clears 4.5:1 against both surfaces in
both themes. `--accent-on-ink` is the third case: the selected day chip paints `--ink`
behind it, so its label needs the opposite polarity from everything else and cannot share
either token.

The ratios are computed here rather than asserted as hex strings, because the thing that
must stay true is the contrast, not the value that produced it. Changing a token is
allowed; changing it to something unreadable is not.
"""
import pathlib
import re
import unittest

import _ctx


ROOT = pathlib.Path(_ctx.ROOT)
HTML = (ROOT / "index.html").read_text(encoding="utf-8")

# Every rule that paints text with the accent. Kept as a literal list: the point of the
# test is that this set and the stylesheet agree, so deriving one from the other would
# assert nothing.
TEXT_RULES = (
    ".vrow mark",
    ".fmt.prem",
    ".trailer",
    ".theatre-tag",
    ".tmdb",
    "#fresh summary.bad",
    "#sources .src.bad",
    "#sources .part",
)

# Accent as a non-text colour is fine at 3:1 and stays on --accent. The wordmark dot is a
# logotype, which 1.4.3 exempts outright.
ACCENT_TEXT_ALLOWED = (".logo span", '.fav[aria-pressed="true"]')

AA_TEXT = 4.5          # 1.4.3, text under 18.66px bold / 24px
AA_NON_TEXT = 3.0      # 1.4.11, borders and focus indicators


def tokens(block_re):
    m = re.search(block_re, HTML, re.S)
    if not m:
        raise AssertionError(f"token block not found: {block_re}")
    return {k: v for k, v in re.findall(r"--([a-z-]+)\s*:\s*(#[0-9A-Fa-f]{6})", m.group(1))}


def luminance(hex_colour):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


LIGHT = tokens(r":root\{(.*?)\}")
DARK = tokens(r'\[data-theme="dark"\]\{(.*?)\}')


class TokenContrastTest(unittest.TestCase):

    def test_the_light_theme_parsed_at_all(self):
        """Guards the two tests below against a regex that silently matched nothing."""
        for name in ("bg", "surface", "ink", "accent", "accent-text", "accent-on-ink"):
            self.assertIn(name, LIGHT, f"--{name} missing from :root")
            self.assertIn(name, DARK, f"--{name} missing from [data-theme=dark]")

    def test_accent_text_is_readable_on_both_surfaces_in_both_themes(self):
        """The defect this token exists for. Text sits on --bg or on --surface; both have
        to clear 4.5:1, in the theme the reader is actually using."""
        for theme, t in (("light", LIGHT), ("dark", DARK)):
            for surface in ("bg", "surface"):
                with self.subTest(theme=theme, surface=surface):
                    ratio = contrast(t["accent-text"], t[surface])
                    # Raw, never rounded: round(4.495, 2) is 4.5, and a token that misses
                    # the bar by three thousandths misses it.
                    self.assertGreaterEqual(
                        ratio, AA_TEXT,
                        f"--accent-text {t['accent-text']} on --{surface} {t[surface]} "
                        f"is {ratio:.3f}:1")

    def test_the_selected_day_label_is_readable_on_the_ink_chip(self):
        """`.day.active` paints --ink, so this label inverts with the theme while
        --accent does not. Dark theme measured 1.57:1 before this token existed."""
        for theme, t in (("light", LIGHT), ("dark", DARK)):
            with self.subTest(theme=theme):
                ratio = contrast(t["accent-on-ink"], t["ink"])
                self.assertGreaterEqual(
                    ratio, AA_TEXT,
                    f"--accent-on-ink {t['accent-on-ink']} on --ink {t['ink']} "
                    f"is {ratio:.3f}:1")

    def test_the_light_chip_label_is_unchanged(self):
        """The fix is dark-theme-only by construction: light already measured 5.46:1 and
        the point was not to redesign it."""
        self.assertEqual(LIGHT["accent-on-ink"], "#B8860B")

    def test_the_plain_accent_still_carries_a_border_and_a_ring(self):
        """--accent keeps its own job. If a later edit darkens it into --accent-text,
        the focus ring quietly drops under 3:1 and nothing else would notice."""
        for theme, t in (("light", LIGHT), ("dark", DARK)):
            for surface in ("bg", "surface"):
                with self.subTest(theme=theme, surface=surface):
                    ratio = contrast(t["accent"], t[surface])
                    self.assertGreaterEqual(ratio, AA_NON_TEXT,
                                            f"--accent on --{surface} is {ratio:.3f}:1")


class TokenRoutingTest(unittest.TestCase):
    """Contrast of a token nothing uses proves nothing. These pin the wiring."""

    def test_every_named_text_rule_uses_the_text_token(self):
        for rule in TEXT_RULES:
            with self.subTest(rule=rule):
                pattern = re.escape(rule) + r"\s*\{[^}]*color:var\(--accent-text\)"
                self.assertRegex(HTML, pattern)

    def test_no_other_rule_uses_the_text_token(self):
        """Keeps the token from spreading into borders and backgrounds, where it is too
        dark and where --accent was already correct."""
        found = re.findall(r"\n\s*([^\n{]+?)\{[^}]*var\(--accent-text\)", HTML)
        self.assertEqual(sorted(s.strip() for s in found), sorted(TEXT_RULES))

    def test_accent_is_no_longer_used_as_text_except_where_it_is_allowed(self):
        """`border-color` and `border-top-color` end in the same eight characters, so the
        lookbehind is what keeps this from passing on a rule it never checked."""
        found = re.findall(r"\n\s*([^\n{]+?)\{[^}]*(?<![-\w])color:var\(--accent\)", HTML)
        self.assertEqual(sorted(s.strip() for s in found), sorted(ACCENT_TEXT_ALLOWED))

    def test_the_selected_day_label_uses_the_ink_token(self):
        self.assertRegex(HTML, r"\.day\.active small\{color:var\(--accent-on-ink\)\}")


if __name__ == "__main__":
    unittest.main()
