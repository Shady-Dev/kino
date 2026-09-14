"""Browser tests for the client: the venue picker and the ticket links, in a real engine.

Separate from the adapter tests on purpose, and outside `discover -s tests` (this
directory is not a package): it needs Playwright and a Chrome, which CI does not
install, and the suite fails on a skipped test. Run it by hand from a venv:

    python3 -m venv .venv && .venv/bin/pip install playwright==1.62.0
    .venv/bin/python -m unittest discover -s tests/browser

`channel="chrome"` drives the Chrome already on the machine, so `playwright install`
and its browser download are not needed. The page is index.html from this checkout;
`data/` is answered from tests/browser/fixture, five files copied from the committed
data on 2026-09-14, and the clock is pinned to 12:00 Helsinki that day, so the
schedule it renders never moves. Every wait is an `expect` condition, none a sleep. A
failing test writes a full-page PNG and a Playwright trace zip into tests/browser/out
(gitignored); open the zip with `playwright show-trace`.

What lives here and not in the node harnesses: focus, inert, Escape, arrow keys and
the on-screen-keyboard rule are DOM and event plumbing, which the extracted pure
functions cannot reach and CLAUDE.md lists as "verified live".
"""
import datetime
import http.server
import json
import os
import pathlib
import threading
import unittest

from playwright.sync_api import expect, sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURE = HERE / "fixture"
OUT = HERE / "out"
FIXED = datetime.datetime(2026, 9, 14, 9, 0, tzinfo=datetime.timezone.utc)   # 12:00 Helsinki
SHOWS = json.loads((FIXTURE / "data/area-or-helsinki.json").read_text(encoding="utf-8"))["shows"]
TODAY_URLS = {s["url"] for s in SHOWS if s["start"].startswith("2026-09-14")}


# 10 s rather than Playwright's 5 s default: the first launch of a freshly installed
# Chromium on a cold runner took the first test past 5 s once in six local runs, and
# every wait here is a condition, so a longer ceiling costs nothing on a green run.
expect.set_options(timeout=10_000)


class Handler(http.server.SimpleHTTPRequestHandler):
    """index.html, sw.js and fonts from the checkout; data/ from the fixture."""

    def translate_path(self, path):
        rel = path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        base = FIXTURE if rel.startswith("data/") else ROOT
        return str(base / rel)

    def log_message(self, *a):
        pass


class Browser(unittest.TestCase):
    viewport = {"width": 1200, "height": 900}; touch = False

    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.origin = f"http://127.0.0.1:{cls.srv.server_port}"
        cls.pw = sync_playwright().start()
        # Playwright's own pinned Chromium by default, the one `playwright install chromium`
        # fetched for this Playwright version, so the engine under test is the same on
        # every machine and on the runner. KINO_BROWSER_CHANNEL=chrome drives the Chrome
        # already installed instead, which skips the download for a quick local run.
        channel = os.environ.get("KINO_BROWSER_CHANNEL") or None
        cls.browser = cls.pw.chromium.launch(channel=channel, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop(); cls.srv.shutdown()

    def setUp(self):
        self.ctx = self.browser.new_context(viewport=self.viewport, has_touch=self.touch,
                                            timezone_id="Europe/Helsinki", locale="fi-FI",
                                            service_workers="block")
        self.ctx.tracing.start(screenshots=True, snapshots=True)
        OUT.mkdir(exist_ok=True)
        self.page = self.ctx.new_page()
        self.page.clock.install(time=FIXED)
        # Until the network has been quiet for 500 ms: the picker opens only once the
        # venue lists are in (`openVenueSheet` returns before that), and the page
        # exposes no DOM marker for that moment. A click that landed first failed one
        # run in seven on a cold machine.
        self.page.goto(self.origin + "/index.html", wait_until="networkidle")

    def tearDown(self):
        res = getattr(self._outcome, "result", None)
        failed = any(t is self for t, _ in (res.failures + res.errors)) if res else False
        name = OUT / self.id().split(".")[-1]
        if failed:
            self.page.screenshot(path=f"{name}.png", full_page=True)
            self.ctx.tracing.stop(path=f"{name}.zip")
        else:
            self.ctx.tracing.stop()
        self.ctx.close()

    def open_picker(self):
        self.page.locator("#areaSelect").click()
        expect(self.page.locator("#vwrap")).to_have_class("vwrap open")
        return self.page.locator("#vq")

    def pick_orion(self):
        vq = self.open_picker(); vq.fill("orion")
        rows = self.page.locator("#vlist .vrow")
        expect(rows).to_have_count(1)
        expect(rows.first).to_have_attribute("data-id", "or-helsinki")
        vq.press("Enter")
        expect(self.page.locator("#vwrap")).not_to_have_class("vwrap open")
        expect(self.page.locator("#areaSelect")).to_contain_text("Cinema Orion")
        expect(self.page.locator("a.stub").first).to_be_visible()


class Desktop(Browser):
    def test_search_and_select_a_cinema(self):
        self.pick_orion()
        self.assertGreater(self.page.locator("a.stub").count(), 0)

    def test_reopening_marks_the_current_venue(self):
        self.pick_orion()
        self.open_picker()
        cur = self.page.locator('#vlist .vrow[aria-current="true"]')
        expect(cur).to_have_count(1)
        expect(cur).to_have_attribute("data-id", "or-helsinki")
        expect(self.page.locator('#vviews .vv[data-view="cities"]')).to_have_attribute("aria-pressed", "true")
        expect(self.page.locator("#vq")).to_be_focused()          # fine pointer: field takes focus

    def test_keyboard_navigation(self):
        vq = self.open_picker()
        vq.press("ArrowDown")
        expect(self.page.locator("#vlist .vrow").first).to_be_focused()
        self.page.keyboard.press("ArrowUp")
        expect(self.page.locator("#vlist .vrow").first).to_be_focused()   # clamps at the top
        vq.fill("zzz"); expect(self.page.locator("#vnone")).to_have_class("vnone show")
        vq.press("Escape"); expect(vq).to_have_value("")                    # first Escape clears
        expect(self.page.locator("#vwrap")).to_have_class("vwrap open")
        vq.press("Escape")                                                  # second closes
        expect(self.page.locator("#vwrap")).not_to_have_class("vwrap open")
        expect(self.page.locator("#areaSelect")).to_be_focused()

    def test_booking_urls_match_the_fixture(self):
        self.pick_orion()
        hrefs = self.page.locator("a.stub").evaluate_all("as => as.map(a => a.href)")
        self.assertTrue(hrefs)
        self.assertEqual(set(hrefs) - TODAY_URLS, set(), "a rendered link is not a fixture URL for today")
        for h in hrefs:
            self.assertTrue(h.startswith("https://cinemaorion.fi/"), h)
            self.assertNotIn(self.origin, h)


class Mobile(Browser):
    viewport = {"width": 375, "height": 812}; touch = True

    def test_picker_fits_the_viewport_and_focus_avoids_the_keyboard(self):
        self.open_picker()
        sheet = self.page.locator("#vwrap .vsheet").bounding_box()
        self.assertLessEqual(sheet["x"] + sheet["width"], 375.5)
        self.assertLessEqual(sheet["y"] + sheet["height"], 812.5)
        expect(self.page.locator("#vq")).to_be_in_viewport()
        expect(self.page.locator("#vclose")).to_be_in_viewport()
        expect(self.page.locator("#vclose")).to_be_focused()     # coarse pointer: no keyboard pop
        self.assertEqual(self.page.evaluate("document.documentElement.scrollWidth"), 375)

    def test_select_on_mobile_renders_tickets(self):
        self.pick_orion()
        expect(self.page.locator("a.stub").first).to_be_in_viewport()

if __name__ == "__main__":
    unittest.main()
