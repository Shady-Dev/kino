"""Every showtime is the same ticket in every view (2026-09-02).

The combined city view hid the stub's perforation and the generated city pages hid their
notches, so combined stubs read as generic cards. The combined stub is now the row stub
adapted: a fixed time compartment, the details compartment, the price at the trailing
edge, a dashed seam between the first two, and notches placed from the same variable as
the seam. Rendering is measured live; the source that makes the alignment hold is pinned
here, in both renderers.
"""
import re
import unittest

import _ctx


HTML = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")
GEN = (_ctx.ROOT / "scripts" / "build_pages.py").read_text(encoding="utf-8")


def rule(css, selector):
    m = re.search(r"(?m)^\s*" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
    return m.group(1) if m else None


class ClientTicketTest(unittest.TestCase):

    def test_the_combined_view_no_longer_hides_the_notches(self):
        self.assertNotRegex(HTML, r"\.stubs\.grid \.stub::before,\s*\.stubs\.grid \.stub::after\s*\{\s*display:\s*none")

    def test_seam_and_notches_are_placed_from_one_variable(self):
        """The time compartment is `--tw` wide, the details compartment starts there with
        its dashed border, and the 8 px notch is centred on it: left = --tw - 4."""
        grid = rule(HTML, ".stubs.grid .stub")
        self.assertIn("--tw:64px", grid)
        self.assertIn("grid-template-columns:var(--tw) minmax(0,1fr) auto", grid)
        self.assertIn('grid-template-areas:"time aud price"', grid)
        self.assertIn("min-height:40px", grid)
        aud = rule(HTML, ".stubs.grid .stub .aud")
        self.assertIn("border-left:1px dashed var(--line)", aud)
        self.assertIn("flex-wrap:wrap", aud)
        self.assertIn("min-width:0", aud)
        self.assertIn("overflow-wrap:anywhere", rule(HTML, ".stubs.grid .stub .aud .loc"))
        self.assertRegex(HTML, r"\.stubs\.grid \.stub::before,\.stubs\.grid \.stub::after\{left:calc\(var\(--tw\) - 4px\)(; right:auto)?\}")

    def test_the_time_compartment_spans_the_ticket(self):
        self.assertIn("align-items:stretch", rule(HTML, ".stubs.grid .stub"))
        self.assertIn("align-items:center", rule(HTML, ".stubs.grid .stub .time"))

    def test_normal_and_combined_views_share_one_stub_markup(self):
        """The grid is a container class only; every renderer emits the same
        `<a class="stub …">` with time, aud and optional price."""
        self.assertEqual(len(re.findall(r'<a class="stub\$\{cls\}', HTML)), 3)
        self.assertEqual(HTML.count("'stubs grid'"), 2)          # the card and the sheet
        self.assertNotIn('class="ticket', HTML)

    def test_the_price_stays_inside_its_own_stub(self):
        self.assertEqual(sorted(re.findall(r"priceLabel\(([^)]*)\)", HTML)), ["[s]", "[s]", "[t]", "rows"])
        self.assertIn("grid-area:price", rule(HTML, ".stubs.grid .stub .price"))

    def test_a_second_column_needs_a_240px_ticket(self):
        """The film sheet at 375 px is 335 px wide. minmax(168px) gave it two 163 px
        columns, and "Cinema Orion" beside "alkaen 10€" broke letter by letter over nine
        lines; at 520 px three columns left 1 px of details. 240 = 64 of time + 75 of
        floor price + 90 for a cinema name to keep its words, and min(…,100%) keeps the
        one track from overflowing a narrower container. No phone override may lower it."""
        grid = rule(HTML, ".stubs.grid")
        self.assertIn("minmax(min(240px, 100%), 1fr)", grid)
        self.assertNotRegex(HTML, r"\.stubs\.grid\{grid-template-columns:repeat\(auto-fill, minmax\(1[0-9]{2}px")

    def test_the_past_times_control_is_not_a_ticket(self):
        self.assertIn('<button class="pastlink"', HTML)
        self.assertNotRegex(HTML, r"\.pastlink::(before|after)")
        self.assertNotIn('class="stub pastlink', HTML)


class GeneratedTicketTest(unittest.TestCase):

    def test_the_city_page_no_longer_hides_the_notches(self):
        self.assertNotRegex(GEN, r"\.grid \.stub \.aud::before,\.grid \.stub \.aud::after\{display:none\}")

    def test_the_seam_is_the_details_border_and_the_notches_ride_on_it(self):
        """The generator's combined-view notches are pseudo-elements of `.aud` at
        left:-4px, so their centre sits on its left border wherever the time compartment
        ends. (The row ticket's notches moved to its price compartment on 2026-09-02.)"""
        self.assertIn("left:-4px", rule(GEN, ".grid .stub .aud::before,.grid .stub .aud::after"))
        grid_aud = rule(GEN, ".grid .stub .aud")
        self.assertIn("border-left:1px dashed var(--line)", grid_aud)
        self.assertIn("flex-wrap:wrap", grid_aud)
        self.assertIn("min-width:0", grid_aud)
        self.assertIn("overflow-wrap:anywhere", grid_aud)
        self.assertEqual(rule(GEN, ".grid .stub .aud .a"), "white-space:normal")
        grid = rule(GEN, ".grid .stub")
        self.assertIn('grid-template-areas:"time aud price"', grid)
        self.assertIn("grid-template-columns:64px minmax(0,1fr) auto", grid)
        self.assertIn("min-height:40px", grid)

    def test_the_city_page_needs_the_same_240px_ticket(self):
        self.assertIn("minmax(min(240px,100%),1fr)", rule(GEN, ".times.grid"))
        self.assertNotRegex(GEN, r"\.times\.grid\{grid-template-columns:repeat\(auto-fill,minmax\(1[0-9]{2}px")

    def test_a_rendered_city_stub_keeps_venue_and_room_on_the_details_side(self):
        import build_pages as bp
        show = {"title": "Autofiktio", "start": "2026-09-02T17:30:00+03:00", "price": None,
                "aud": "Sali 7", "venueLabel": "Finnkino Plevna", "venueProvider": "finnkino",
                "url": "https://www.finnkino.fi/x", "lang": "ES-A, FI-S, SV-S"}
        html = bp.film_block("Autofiktio", [show], {}, {}, "fi", bp.L["fi"], True, set())
        li = re.search(r"<li>(.*?)</li>", html, re.S).group(1)
        self.assertRegex(li, r'<span class="time">17:30</span><span class="aud">.*Finnkino Plevna.*Sali 7.*</span><span class="price"></span></a>$')


if __name__ == "__main__":
    unittest.main()
