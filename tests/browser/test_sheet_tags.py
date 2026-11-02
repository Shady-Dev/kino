"""The sheet draws a film's tags as the card does (2026-11-02).

One day of a served Orion file, so the card and the sheet hold the same screenings.
"""
import http.server
import json
import os
import unittest

from playwright.sync_api import expect

import _harness
import test_client_browser as base

DAY = "2026-09-14"


def show(film, title, clock, aud, method):
    return {"eventId": film, "title": title, "original": "", "len": "118", "rating": "K-12",
            "age": "", "genres": "Draama", "img": "", "price": "", "tmdb": 7.1, "votes": 41,
            "theatre": "Cinema Orion", "aud": aud, "lang": "EN-A, FI-S, SV-S",
            "method": method, "start": f"{DAY}T{clock}:00+03:00", "soldOut": False,
            "provider": "orion", "venue": "or-helsinki",
            "url": f"https://example.invalid/or-helsinki/{film}/{clock}"}


MIXED, SHARED = "Sama elokuva", "Toinen elokuva"
SHOWS = [show("sama", MIXED, "13:20", "IMAX", "2D · Anniskelu · IMAX"),
         show("sama", MIXED, "15:00", "LUXE 8", "2D · Anniskelu · LUXE"),
         show("sama", MIXED, "18:00", "Sali 2", "Afternoon Tea"),
         show("sama", MIXED, "20:40", "Sali 3", ""),
         show("toinen", SHARED, "14:00", "Sali 1", "35 mm · Senioribio · Kuvaileva tekstitys"),
         show("toinen", SHARED, "19:00", "Sali 2", "35 mm")]


class Handler(base.Handler):
    def do_GET(self):
        if self.path.split("?", 1)[0].endswith("/data/area-or-helsinki.json"):
            body = json.dumps({"generated": "2026-09-14T08:00:00+00:00", "dates": [DAY],
                               "horizon": DAY, "shows": SHOWS}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


# textContent: the pills are upper-cased by CSS.
DRAWN = """(scope) => ({
  pills: [...document.querySelectorAll(scope + ' .meta1 .fmt')].map(e => e.textContent.trim()),
  tickets: [...document.querySelectorAll(scope + ' a.stub')].map(a => ({
    time: a.querySelector('.time').textContent.trim(),
    loc: (a.querySelector('.loc') || {}).textContent || '',
    glyphs: a.querySelectorAll('.glyphs > .gl').length }))
})"""


class SheetTags(unittest.TestCase):
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

    def drawn(self, width, title):
        """The film's card and its sheet, as DRAWN reads them."""
        ctx = self.browser.new_context(viewport={"width": width, "height": 900},
                                       timezone_id="Europe/Helsinki", locale="fi-FI",
                                       service_workers="block")
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        page.clock.install(time=base.FIXED)
        page.add_init_script("localStorage.setItem('kino-prefs', JSON.stringify({view:'movies'}));"
                             "localStorage.setItem('kino-theme', 'light')")
        page.goto(self.origin + "/index.html?area=or-helsinki")
        card = page.locator("#main article.movie", has_text=title)
        expect(card.locator("a.stub").first).to_be_visible()
        card_id = card.get_attribute("data-id")
        on_card = page.evaluate(DRAWN, f'#main article.movie[data-id="{card_id}"]')
        card.locator("h2.title a.tlink").click()
        expect(page.locator("#sheet a.stub").first).to_be_visible()
        return on_card, page.evaluate(DRAWN, "#sheet")

    def test_tags_that_differ_go_on_their_own_tickets(self):
        for width in (393, 1200):
            with self.subTest(width=width):
                card, sheet = self.drawn(width, MIXED)
                self.assertEqual(sheet["pills"], ["118 min"], sheet)
                by_time = {t["time"]: t for t in sheet["tickets"]}
                self.assertIn("Afternoon Tea", by_time["18:00"]["loc"])
                self.assertEqual(by_time["13:20"]["loc"].count("IMAX"), 1, by_time["13:20"])
                self.assertNotIn("IMAX", by_time["15:00"]["loc"])
                self.assertEqual([t["glyphs"] for t in sheet["tickets"]], [1, 1, 0, 0])
                self.assertFalse(any("2D" in t["loc"] for t in sheet["tickets"]), sheet)

    def test_a_tag_every_screening_carries_is_drawn_once_in_the_head(self):
        for width in (393, 1200):
            with self.subTest(width=width):
                card, sheet = self.drawn(width, SHARED)
                self.assertEqual(card["pills"], ["35 mm"], card)
                self.assertEqual(sheet["pills"], ["118 min", "35 mm"], sheet)
                first = sheet["tickets"][0]["loc"]
                self.assertIn("Senioribio", first)
                self.assertIn("Kuvaileva tekstitys", first)
                self.assertFalse(any("35 mm" in t["loc"] for t in sheet["tickets"]), sheet)

    def test_a_screening_carries_the_same_labels_on_the_card_and_in_the_sheet(self):
        for title in (MIXED, SHARED):
            with self.subTest(title=title):
                card, sheet = self.drawn(393, title)
                self.assertEqual(card["tickets"], sheet["tickets"])


if __name__ == "__main__":
    unittest.main()
