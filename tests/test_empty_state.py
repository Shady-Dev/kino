"""An empty result can clear the filter that caused it.

12 September with Anniskelu on rendered "Yksikään elokuva ei vastaa suodattimia." and
nothing else: the reader had to work out which of five chips, a chain filter or the search
box had emptied the list and undo it themselves. The message now carries a button that
clears all of them.

Source-level guards. The click itself is verified live against the served page.
"""
import pathlib
import re
import unittest

import _ctx

HTML = (pathlib.Path(_ctx.ROOT) / "index.html").read_text(encoding="utf-8")


class EmptyStateActionTest(unittest.TestCase):

    def test_the_clear_action_only_appears_when_a_filter_is_on(self):
        """An empty day with no filter set is not a filter problem, and the button would
        claim otherwise."""
        self.assertRegex(HTML, r"function clearFiltersLink\(\)\{\s*\n\s*return anyFilter\(\)")

    def test_a_chain_filter_counts_as_a_filter(self):
        """The chain legend empties the list the same way the chips do, and emptyMsg
        blames the filters for it too."""
        self.assertRegex(HTML, r"function anyFilter\(\)\{[^}]*state\.chains")

    def test_clearing_resets_every_filter_and_the_search_box(self):
        body = HTML[HTML.index("function clearFilters()"):]
        body = body[:body.index("\n  }")]
        for bit in ("state.filter = ''", "searchEl.value = ''", "state.fLang = false",
                    "state.fKids = false", "state.fAnnis = false", "state.chains = null"):
            self.assertIn(bit, body)

    def test_the_label_exists_in_three_languages(self):
        self.assertEqual(len(re.findall(r"clearFilters:'", HTML)), 3)


if __name__ == "__main__":
    unittest.main()
