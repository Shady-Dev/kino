"""The film sheet leads with the times, and long content is collapsed.

On a phone the sheet opened with a 600-character synopsis, then every screening of the
day including the ones that had already started: Autofiktio's first bookable showtime was
below the fold behind text and dead times. The day list now comes first, past times sit
behind the control the cards already use, and a long synopsis is clamped under them.

Source-level guards, in the shape tests/test_ticket_anatomy.py uses. The behaviour --
focus, the drag, the scroll position -- stays a live check against the served page.
"""
import pathlib
import re
import unittest

import _ctx

HTML = (pathlib.Path(_ctx.ROOT) / "index.html").read_text(encoding="utf-8")


def rule(selector):
    """-> the body of the last rule for exactly this selector."""
    hits = re.findall(re.escape(selector) + r"\{([^}]*)\}", HTML)
    return hits[-1] if hits else ""


class SheetOrderTest(unittest.TestCase):

    def test_the_day_list_is_rendered_before_the_synopsis(self):
        """Order in the template is the order on screen: the body is one assignment."""
        body = HTML[HTML.index('<div class="sheet-body">'):]
        body = body[:body.index("</div>`")]
        self.assertLess(body.index("sheet-days"), body.index("synHtml"), body[:200])

    def test_a_long_synopsis_is_clamped_and_a_short_one_is_not(self):
        self.assertRegex(HTML, r"synLong = syn\.length > \d+")
        self.assertIn("-webkit-line-clamp:4", rule(".syn.clamp"))
        self.assertRegex(HTML, r"class=\"syn\$\{synLong \? ' clamp' : ''\}\"")

    def test_the_synopsis_toggle_exists_in_three_languages(self):
        self.assertEqual(len(re.findall(r"synMore:'", HTML)), 3)
        self.assertEqual(len(re.findall(r"synLess:'", HTML)), 3)

    def test_the_sheet_past_times_reuse_the_tested_label(self):
        """pastLabel is the pure function the cards' toggle already uses, so the sheet
        cannot drift into its own wording or its own singular rule."""
        self.assertIn("pastLabel(false, gone.length, L[lang])", HTML)
        self.assertIn('data-pastday=', HTML)

    def test_the_collapsed_past_times_outrank_the_grid_display(self):
        """`hidden` is display:none in the UA sheet and `.stubs.grid{display:grid}` beats
        it. At equal specificity the grid rule also sits later in the file, so the hidden
        rule has to name both classes: without it the collapsed block rendered in full."""
        self.assertIn("display:none", rule(".stubs[hidden], .stubs.grid[hidden]"))
        grid_at = HTML.index(".stubs.grid{")
        hidden_at = HTML.index(".stubs[hidden], .stubs.grid[hidden]{")
        self.assertLess(hidden_at, grid_at, "order alone must not be what makes it win")


if __name__ == "__main__":
    unittest.main()
