"""Grid tickets take the width of the list's widest one, and no more (2026-09-23).

The combined view's tracks were `minmax(min(240px, 100%), 1fr)`: a row packed as many
240 px columns as fitted and stretched them. Measured over the committed Helsinki data,
identically in Chromium and WebKit: three columns squeezed to 245 px at 900 and wrapped
44 of 83 tickets to three lines, while at 1300 the same rule under a wider minimum ran to
470 px of empty ticket. Now each rendered list measures its grid cells at max-content and
every track is the widest plus `TKW_PAD`; a column is added only when a whole ticket fits.
Measured after at 500 to 1400: every ticket 310 px, none past two lines, before and after
a resize. `ticketWidth` is sliced verbatim out of index.html and run in node; the DOM half
is pinned on the source.
"""
import json
import re
import shutil
import subprocess
import unittest

import _ctx

HTML = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")


def ticket_width(cases):
    block = re.search(r"// --- ticketWidth: [^\n]*\n(.*?)\n\s*// --- end ticketWidth ---",
                      HTML, re.S).group(1)
    js = f"{block}\nprocess.stdout.write(JSON.stringify({json.dumps(cases)}.map(ticketWidth)));"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


def tickets_beside(cases):
    block = re.search(r"// --- ticketWidth: [^\n]*\n(.*?)\n\s*// --- end ticketWidth ---",
                      HTML, re.S).group(1)
    js = (f"{block}\nprocess.stdout.write(JSON.stringify({json.dumps(cases)}"
          ".map(c => ticketsBeside(...c, 20))));")
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class TicketsBesideTest(unittest.TestCase):
    """On a phone a card's tickets go beside the poster only when all of them fit one line
    in the column there (2026-09-28). The column is 245 px at 375."""

    def test_row_tickets_fit_by_their_own_widths(self):
        # Kino Kirkkonummi's lone 144 px ticket; two of them need 296. The gap counts.
        self.assertEqual(tickets_beside([[[144], 245, 8, 0], [[144, 144], 245, 8, 0],
                                         [[118, 118], 245, 8, 0], [[120, 120], 245, 8, 0],
                                         [[245.5], 245, 8, 0]]),
                         [True, False, True, False, False])

    def test_combined_tickets_take_the_track_capped_at_the_column(self):
        # Every combined ticket is one track wide; a 283 px track shrinks to the column,
        # which a 241 px ticket fits with the pad and a 242 px one does not.
        self.assertEqual(tickets_beside([[[241], 245, 8, 283], [[242], 245, 8, 283],
                                         [[100, 100], 245, 8, 283], [[100, 100], 245, 8, 110]]),
                         [True, False, False, True])

    def test_nothing_to_place(self):
        self.assertEqual(tickets_beside([[[], 245, 8, 0]]), [False])

    def test_the_list_has_to_start_beside_the_poster(self):
        """Details that run past the poster put the list under it either way; moving it
        into the column would only narrow it."""
        self.assertEqual(tickets_beside([[[144], 245, 8, 0, 0.5], [[144], 245, 8, 0, 0],
                                         [[144], 245, 8, 0, -30]]), [True, False, False])


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class TicketWidthTest(unittest.TestCase):
    def test_the_widest_ticket_plus_the_pad(self):
        self.assertEqual(ticket_width([[250, 306], [300.2], [306, 306]]), [310, 305, 310])

    def test_nothing_measurable_keeps_the_fallback(self):
        """A list with no ticket, or one not laid out yet, reads widths of 0."""
        self.assertEqual(ticket_width([[], [0, 0]]), [0, 0])


class TicketWidthWiringTest(unittest.TestCase):
    def test_the_measured_tracks_are_that_wide_and_no_wider(self):
        self.assertIn(".tkw .stubs.grid{grid-template-columns:repeat(auto-fill, "
                      "min(var(--tkw), 100%))}", HTML)
        # The unmeasured fallback stays for the first paint.
        self.assertIn("grid-template-columns:repeat(auto-fill, minmax(min(240px, 100%), 1fr));",
                      HTML)

    def test_the_measure_reads_the_cell_uncapped(self):
        """The cell, because the film view's is the ticket plus its menu button; and
        uncapped, because `.tk{max-width:100%}` held the reading to the fallback track and
        made it follow the window: 284 to 352 px for one film, with 29 of 33 tickets
        wrapping, in both engines."""
        self.assertIn(".tkw-measure .stubs.grid > *{width:max-content; max-width:none; "
                      "justify-self:start}", HTML)
        self.assertIn("root.querySelectorAll('.stubs.grid > *')", HTML)
        self.assertIn(".tkw-measure .stubs.grid[hidden]{display:grid}", HTML)

    def test_both_lists_are_measured_after_they_are_drawn(self):
        self.assertRegex(HTML, r"main\.innerHTML = listLegend[^;]*;\n\s*sizeTickets\(main\);")
        self.assertRegex(HTML, r"</div>`;\n\s*sizeTickets\(sheetEl\);")
        self.assertIn("document.fonts.ready.then(() => sizeTickets(root))", HTML)


if __name__ == "__main__":
    unittest.main()
