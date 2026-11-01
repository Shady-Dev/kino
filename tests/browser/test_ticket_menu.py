"""Where the ticket's menu opens, in a real engine (2026-11-01).

The menu opened under the ticket from its left edge, so a mouse that clicked the dots at
the ticket's right end had to travel left to reach it. It now opens under the dots with
the two right edges in line, above them when the sheet body has no room below, and shifted
to stay 16 px inside the body (`menuPlace`). The arithmetic is also unit-tested through
tests/screening_link_harness.js; this file checks what the engines draw from it.

Served data: one Finnkino film with six screenings, each with a hall and three languages,
so the ticket is as wide as the screenshot that reported this (Clayface at Sello).
"""
import http.server
import json
import os
import unittest

from playwright.sync_api import expect

import _harness
import test_client_browser as base

FILM = {"eventId": "menu-film", "title": "Valikkoelokuva", "original": "", "len": "108",
        "rating": "K-16", "age": "", "genres": "Kauhu", "method": "2D", "theatre": "Promenadi Pori",
        "aud": "Sali 1", "img": "", "lang": "EN-A, FI-S, SV-S", "soldOut": False, "price": "",
        "provider": "finnkino", "venue": "1004"}
DAYS = ["2026-09-14", "2026-09-15", "2026-09-16"]
SHOWS = [{**FILM, "start": f"{d}T{t}:00+03:00", "url": f"https://www.finnkino.fi/event/{d}/{t}"}
         for d in DAYS for t in ("18:00", "20:50")]
AREA = json.dumps({"generated": "2026-09-14T08:00:00+00:00", "dates": DAYS,
                   "horizon": DAYS[-1], "shows": SHOWS}).encode()


class Handler(base.Handler):
    def do_GET(self):
        if self.path.split("?", 1)[0].endswith("/data/area-1004.json"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(AREA)))
            self.end_headers()
            self.wfile.write(AREA)
            return
        super().do_GET()


MEASURE = """(i) => {
  const b = document.querySelectorAll('.sheet-body .tk .more')[i].getBoundingClientRect();
  const m = document.querySelector('.tkmenu').getBoundingClientRect();
  const body = document.querySelector('.sheet-body'), r = body.getBoundingClientRect();
  return { btnLeft: b.left, btnRight: b.right, btnTop: b.top, btnBottom: b.bottom,
           left: m.left, right: m.right, top: m.top, bottom: m.bottom,
           boxLeft: Math.max(0, r.left), boxRight: Math.min(document.documentElement.clientWidth, r.right),
           pageOver: document.documentElement.scrollWidth - document.documentElement.clientWidth,
           bodyOver: body.scrollWidth - body.clientWidth };
}"""


class TicketMenuPlace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.srv.served, cls.srv.requested = [], []
        _harness.start(cls.srv)
        cls.origin = f"http://127.0.0.1:{cls.srv.server_port}"
        cls.pw = _harness.playwright()
        engine = os.environ.get("KINO_BROWSER_ENGINE", "chromium")
        channel = os.environ.get("KINO_BROWSER_CHANNEL") if engine == "chromium" else None
        cls.browser = getattr(cls.pw, engine).launch(channel=channel or None, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); _harness.stop(cls.srv)

    def sheet(self, width, height, theme):
        ctx = self.browser.new_context(viewport={"width": width, "height": height},
                                       timezone_id="Europe/Helsinki", locale="fi-FI",
                                       service_workers="block")
        self.addCleanup(ctx.close)
        ctx.add_init_script(f"localStorage.setItem('kino-theme', '{theme}')")
        page = ctx.new_page()
        page.clock.install(time=base.FIXED)
        page.goto(f"{self.origin}/index.html?area=1004#m=menu-film")
        expect(page.locator(".sheet-body .tk .more")).to_have_count(len(SHOWS))
        return page

    def open(self, page, i):
        page.locator(".sheet-body .tk .more").nth(i).click()
        expect(page.locator(".tkmenu")).to_be_visible()
        return page.evaluate(MEASURE, i)

    def test_the_menu_opens_under_the_dots_with_the_right_edges_in_line(self):
        for theme in ("light", "dark"):
            for width in (320, 375, 402, 1200):
                with self.subTest(theme=theme, width=width):
                    page = self.sheet(width, 900, theme)
                    m = self.open(page, 0)
                    self.assertAlmostEqual(m["right"], m["btnRight"], delta=0.5, msg=m)
                    self.assertGreaterEqual(m["top"], m["btnBottom"], m)
                    self.assertLess(m["top"] - m["btnBottom"], 8, m)
                    self.assertGreaterEqual(m["left"], m["boxLeft"] + 16 - 0.5, m)
                    self.assertLessEqual(m["right"], m["boxRight"] - 16 + 0.5, m)
                    self.assertLessEqual(m["pageOver"], 0, m)
                    self.assertLessEqual(m["bodyOver"], 0, m)

    def test_the_menu_goes_above_the_dots_at_the_bottom_of_the_sheet(self):
        for width in (375, 1200):
            with self.subTest(width=width):
                page = self.sheet(width, 560, "light")
                page.evaluate("document.querySelector('.sheet-body').scrollTop = 1e6")
                m = self.open(page, len(SHOWS) - 1)
                self.assertAlmostEqual(m["right"], m["btnRight"], delta=0.5, msg=m)
                self.assertLessEqual(m["bottom"], m["btnTop"], m)
                self.assertLess(m["btnTop"] - m["bottom"], 8, m)

    def test_escape_still_closes_it_and_returns_focus_to_the_dots(self):
        page = self.sheet(375, 900, "light")
        self.open(page, 1)
        expect(page.locator(".tkmenu .mi").first).to_be_focused()
        page.keyboard.press("ArrowDown")
        expect(page.locator(".tkmenu .mi").nth(1)).to_be_focused()
        page.keyboard.press("Escape")
        expect(page.locator(".tkmenu")).to_have_count(0)
        expect(page.locator(".sheet-body .tk .more").nth(1)).to_be_focused()


if __name__ == "__main__":
    unittest.main()
