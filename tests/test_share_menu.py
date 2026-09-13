"""Each upcoming ticket in the film sheet has a menu with "Share screening" (2026-09-13, v145).

The dots button sits beside the ticket, outside the anchor, and opens a `role="menu"`
popover; share goes through `navigator.share` or the clipboard with a toast. The two pure
pieces, `shareText` and `menuSide`, run verbatim through tests/screening_link_harness.js;
the markup, the strings and the CSS are pinned on the source. Keyboard, focus return and
the flip near the right edge stay verified live.
"""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

import _ctx

HARNESS = pathlib.Path(__file__).resolve().parent / "screening_link_harness.js"
HTML = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")


def rule(selector):
    m = re.search(r"^\s*" + re.escape(selector) + r"\{(.*?)\}", HTML, re.S | re.M)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def strings(lang):
    block = re.search(r"\n    " + lang + r":\{(.*?)\n    \w+:\{|\n    " + lang + r":\{(.*?)\n  \};", HTML, re.S)
    text = (block.group(1) or block.group(2)) if block else ""
    return dict(re.findall(r"(\w+):'([^']*)'", text))


def sheet_stub():
    body = re.search(r"async function showSheet\(fid, want\)\{.*?\n  \}\n", HTML, re.S).group(0)
    return re.search(r"const stub = s => \{.*?\n    \};", body, re.S).group(0)


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class SharePureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        o = json.loads(out.stdout)
        cls.share, cls.side = o["share"], o["side"]

    def test_the_share_text_is_title_place_and_time_one_per_line(self):
        self.assertEqual(self.share["with_hall"], "Ryhmä Hau: Dinoelokuva\nFinnkino Promenadi, Sali 3\nTi 15.9. klo 16:30")
        self.assertEqual(self.share["no_hall"], "Kino Regina\nKino Regina\nLa 13.9. kl. 20:45")

    def test_the_share_payload_is_plain_text_not_html_escaped(self):
        self.assertEqual(self.share["verbatim"].split("\n")[0], "<b>A & B</b>")

    def test_the_menu_flips_leftwards_within_200px_of_the_right_edge_when_it_fits_there(self):
        self.assertEqual((self.side["far_from_edge"], self.side["wide"]), ("right", "right"))
        self.assertEqual((self.side["at_199_room_left"], self.side["at_edge"]), ("left", "left"))
        self.assertEqual(self.side["at_200"], "right", "200 px is not within")
        self.assertEqual(self.side["at_199_no_room_left"], "right", "a 157 px ticket at 375: flipped, the menu left the screen")


class ShareMarkupTest(unittest.TestCase):

    def test_the_button_is_beside_the_anchor_in_a_wrapper_and_absent_on_past_tickets(self):
        stub = sheet_stub()
        self.assertIn('return `<div class="tk"><a class="stub${cls}${tint}"', stub)
        self.assertIn("</a>${more}</div>`;", stub)
        self.assertIn("const more = past ? '' : `<button class=\"more\" type=\"button\" data-i=\"${s._i}\"", stub)
        self.assertIn('aria-haspopup="menu" aria-expanded="false">${DOTS}</button>', stub)
        self.assertIn('aria-label="${esc(L[lang].aActions)}"', stub)
        # cards and the Ajat list are untouched: one wrapper, in the sheet
        self.assertEqual(HTML.count('<div class="tk">'), 1)
        self.assertEqual(len(re.findall(r'<a class="stub\$\{cls\}', HTML)), 3)

    def test_the_dots_are_inline_svg_in_current_color(self):
        dots = re.search(r"const DOTS = '(<svg.*?</svg>)';", HTML).group(1)
        self.assertEqual(dots.count('fill="currentColor"'), 3)
        self.assertIn('aria-hidden="true"', dots)
        for gone in ("⋮", "font-family", "http"):
            self.assertNotIn(gone, dots)

    def test_the_menu_is_a_menu_with_44px_rows_on_the_surface(self):
        self.assertIn("menu.setAttribute('role', 'menu');", HTML)
        self.assertIn('<button type="button" role="menuitem" class="mi" data-act="share"><span>${esc(T.shareScreening)}</span><small>${esc(sub)}</small></button>', HTML)
        self.assertIn("min-height:44px", rule(".tkmenu .mi"))
        menu = rule(".tkmenu")
        for want in ("background:var(--surface)", "border:1px solid var(--line)", "border-radius:8px", "position:absolute"):
            self.assertIn(want, menu)
        self.assertEqual(rule(".tkmenu.left"), "left:auto; right:0")
        self.assertIn("menuSide(tk.getBoundingClientRect().right, window.innerWidth)", HTML)

    def test_the_button_is_40px_muted_at_rest_and_accent_while_open(self):
        more = rule(".tk .more")
        for want in ("width:40px", "height:40px", "color:var(--muted)", "border:0"):
            self.assertIn(want, more)
        self.assertEqual(rule(".tk.open .more"), "color:var(--accent)")
        self.assertIn("grid-template-columns:minmax(0,1fr) auto", rule(".stubs.grid .tk"))

    def test_escape_closes_before_the_sheet_and_focus_returns_to_the_dots(self):
        key = re.search(r"sheetEl\.addEventListener\('keydown', e => \{.*?\n  \}, true\);", HTML, re.S).group(0)
        self.assertIn("if(e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); closeStubMenu(true); return; }", key)
        self.assertIn("if(e.key === 'ArrowDown' || e.key === 'ArrowUp'){", key)
        close = re.search(r"function closeStubMenu\(refocus\)\{.*?\n  \}\n", HTML, re.S).group(0)
        self.assertIn("if(refocus) b.focus();", close)
        self.assertIn("b.setAttribute('aria-expanded', 'false');", close)
        self.assertIn("if(openTk && !openTk.contains(e.target)) closeStubMenu(false);", HTML)   # outside tap
        self.assertIn("function hideSheet(){\n    closeStubMenu(false);", HTML)

    def test_share_uses_the_native_sheet_else_the_clipboard_and_the_toast(self):
        fn = re.search(r"async function shareScreening\(s\)\{.*?\n  \}\n", HTML, re.S).group(0)
        self.assertIn("screeningUrl(location.href, state.area, sheetCtx.fid, iso, s.startIso)", fn)
        self.assertIn("shareText(sheetCtx.title, venueName(s), s.aud || '',", fn)
        self.assertIn("await navigator.share({ title: sheetCtx.title, text, url });", fn)
        self.assertIn("await navigator.clipboard.writeText(url); toast(T.linkCopied);", fn)
        self.assertNotIn("esc(", fn, "the payload is plain text")
        self.assertIn("toastEl.setAttribute('role', 'status');", HTML)
        self.assertIn("setListStatus(msg);", re.search(r"function toast\(msg\)\{.*?\n  \}\n", HTML, re.S).group(0))

    def test_the_strings_in_all_three_languages(self):
        want = {"fi": ("Jaa näytös", "Näytöksen toiminnot", "Linkki kopioitu"),
                "sv": ("Dela visningen", "Åtgärder för visningen", "Länk kopierad"),
                "en": ("Share screening", "Screening actions", "Link copied")}
        for lang, (share, actions, copied) in want.items():
            s = strings(lang)
            self.assertEqual((s.get("shareScreening"), s.get("aActions"), s.get("linkCopied")),
                             (share, actions, copied), lang)

    def test_the_sheet_is_redrawn_on_a_language_toggle_so_every_string_follows(self):
        apply = re.search(r"function applyLang\(\)\{.*?\n  \}\n", HTML, re.S).group(0)
        self.assertIn("if(document.body.classList.contains('sheet-open')) syncSheet();", apply)

    def test_the_service_worker_moved_with_the_page(self):
        sw = (_ctx.ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"leffavuoro-v(\d+)", sw).group(1)), 145)


if __name__ == "__main__":
    unittest.main()
