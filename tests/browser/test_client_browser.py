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
import time
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
    """index.html, sw.js and fonts from the checkout; data/ from the fixture.

    `delay` holds seconds by path suffix: a venue file answered late is how the readiness
    condition below is shown to wait rather than to race the boot."""
    delay = {}

    def do_GET(self):
        self.nostore = False
        for suffix, secs in self.delay.items():
            if self.path.endswith(suffix):
                # A delayed file is also uncacheable, or the browser answers the second
                # request from its own HTTP cache and the delay describes nothing. That is
                # what makes a cold load reproducible here at all.
                self.nostore = True
                time.sleep(secs)
        self.server.served.append((self.path, time.monotonic()))
        super().do_GET()

    def end_headers(self):
        if getattr(self, "nostore", False):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

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
        cls.srv.served = []
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
        self.page.goto(self.origin + "/index.html")

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
        """Click until the picker opens. `openVenueSheet` returns before the venue lists
        have arrived and the page changes nothing observable when they do (the day chips
        are built before `loadAreas`; the trigger's label and attributes stay as in the
        markup), so the condition is the picker itself: a click that opened it. Each
        attempt waits on the class through `expect`, no fixed sleep, and the loop is
        bounded by the same 10 s the other waits get."""
        deadline = time.monotonic() + 10
        vwrap = self.page.locator("#vwrap")
        while True:
            self.page.locator("#areaSelect").click()
            try:
                expect(vwrap).to_have_class("vwrap open", timeout=250)
                return self.page.locator("#vq")
            except AssertionError:
                if time.monotonic() > deadline:
                    raise

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

class DelayedVenues(Browser):
    """The venue file arrives two seconds late: the picker opens on the venue anyway, and
    only after that file was served, so the readiness condition waited for the data and not
    for the page load."""

    def setUp(self):
        Handler.delay = {"/data/venues-orion.json": 2.0}
        self.addCleanup(lambda: setattr(Handler, "delay", {}))
        self.srv.served.clear()
        super().setUp()

    def test_the_picker_opens_only_after_the_late_venue_file(self):
        self.pick_orion()
        opened = time.monotonic()
        served = {path.split("?")[0]: t for path, t in self.srv.served}
        self.assertIn("/data/venues-orion.json", served)
        self.assertGreater(served["/data/venues-orion.json"] - served["/index.html"], 2.0)
        self.assertGreater(opened, served["/data/venues-orion.json"])


class ShareLink(Browser):
    """A `#m=&d=` link marks a ticket. The reader has to be able to see it.

    Short viewport on purpose: the sheet has to overflow before "scrolled to" can mean
    anything. The film picked is the fixture's only one with a day far enough down the
    body to fall outside it -- Hetki ennen valoa, 17.9. and 23.9.
    """

    viewport = {"width": 375, "height": 320}
    touch = True

    def sheet_box(self):
        return self.page.evaluate("""() => {
            const body = document.querySelector('.sheet-body');
            const pick = document.querySelector('.sheet-body .stub.pick');
            if(!body || !pick) return null;
            const b = body.getBoundingClientRect(), p = pick.getBoundingClientRect();
            return {top: b.top, bottom: b.bottom, pickTop: p.top, pickBottom: p.bottom,
                    scrollTop: body.scrollTop, scrollable: body.scrollHeight > body.clientHeight};
        }""")

    def test_a_link_to_a_later_day_leaves_its_ticket_in_view(self):
        self.pick_orion()
        self.page.evaluate("location.hash = 'm=hetki-ennen-valoa&d=2026-09-23'")
        expect(self.page.locator(".sheet-body .stub.pick")).to_have_count(1)
        box = self.sheet_box()
        self.assertTrue(box and box["scrollable"],
                        "the sheet has to overflow or this proves nothing")
        self.assertGreater(box["pickTop"], box["top"] - 1,
                           "the marked ticket sits above the top of the body")
        self.assertLess(box["pickBottom"], box["bottom"],
                        f"the marked ticket is below the body's bottom edge by "
                        f"{box['pickBottom'] - box['bottom']:.0f}px: marked and left off "
                        f"screen, which is what a share link did before this was fixed")

    def test_a_link_to_the_first_day_also_leaves_its_ticket_in_view(self):
        """The counterweight. At this height the synopsis pushes even the first day past
        the fold, so both days need the scroll and neither may end up off screen."""
        self.pick_orion()
        self.page.evaluate("location.hash = 'm=hetki-ennen-valoa&d=2026-09-17'")
        expect(self.page.locator(".sheet-body .stub.pick")).to_have_count(1)
        box = self.sheet_box()
        self.assertGreater(box["pickTop"], box["top"] - 1)
        self.assertLess(box["pickBottom"], box["bottom"] + 1)


class SheetRefresh(Browser):
    """A background refresh redraws an open sheet. It must not move the reader."""

    def open_sheet(self):
        self.pick_orion()
        self.page.evaluate("location.hash = 'm=hetki-ennen-valoa&d=2026-09-17'")
        expect(self.page.locator(".sheet-body .stub.pick")).to_have_count(1)

    def focused(self):
        return self.page.evaluate(
            "() => { const a = document.activeElement;"
            " return a ? (a.className || '') + '|' + (a.dataset.i || '') : ''; }")

    def test_following_a_link_to_another_film_still_focuses_the_close_button(self):
        """The path `keepFocus` must not reach: the reader asked for this sheet, so the
        keyboard goes into it. Only `refreshOpenSheet` passes the flag, and that path is
        driven by a service-worker message this context blocks -- it is covered in
        tests/test_screening_link.py instead, which is stated there rather than implied."""
        self.open_sheet()
        self.page.evaluate("location.hash = 'm=autofiktio'")
        expect(self.page.locator(".sheet-body")).to_be_visible()
        self.assertIn("sheet-close", self.focused())

    def test_opening_the_sheet_still_focuses_the_close_button(self):
        """The counterweight: a sheet the reader opens takes focus, as it always has, or
        the keyboard is left behind the page."""
        self.pick_orion()
        self.page.locator("article.movie").first.click()
        expect(self.page.locator(".sheet-body")).to_be_visible()
        self.assertIn("sheet-close", self.focused())


class HistoryAcrossVenues(Browser):
    """Back and Forward across venues and home, with the movie sheet open.

    The sheet is modal: it marks everything behind it inert. A traversal that changes
    `?area=` and `#m=` in one step fires `popstate` and no `hashchange`, and `hashchange`
    was the only thing that closed the sheet from the URL, so what stayed on screen was
    another cinema's film, with that cinema's ticket links, over a page nothing could
    reach. The fixture carries a second venue for exactly this: Promenadi Pori shows a
    film no other venue in it does.
    """

    def pick_promenadi(self):
        vq = self.open_picker(); vq.fill("promenadi")
        rows = self.page.locator("#vlist .vrow")
        expect(rows).to_have_count(1)
        vq.press("Enter")
        expect(self.page.locator("#areaSelect")).to_contain_text("Promenadi")
        expect(self.page.locator("a.stub").first).to_be_visible()

    def open_first_film(self):
        self.page.locator("article.movie").first.click()
        expect(self.page.locator(".sheet-body")).to_be_visible()

    def state(self):
        return self.page.evaluate("""() => ({
            hidden: document.getElementById('sheet').inert === true,
            behindInert: !!document.querySelector('main').inert
                      || !!document.querySelector('header').inert,
            title: (document.querySelector('#sheetTitle') || {}).textContent || '',
            url: location.search + location.hash,
            venue: document.querySelector('#areaSelect .vlbl').textContent,
            focus: (document.activeElement && document.activeElement.className) || '',
        })""")

    def test_back_across_a_venue_change_closes_the_other_cinema_s_sheet(self):
        self.pick_orion()
        self.pick_promenadi()
        self.open_first_film()
        before = self.state()
        self.assertFalse(before["hidden"], "the sheet should be open at this point")
        self.assertIn("Porin", before["title"])
        self.page.go_back()          # ?area=1004 without the fragment
        self.page.go_back()          # ?area=or-helsinki
        expect(self.page.locator("#areaSelect")).to_contain_text("Cinema Orion")
        after = self.state()
        self.assertTrue(after["hidden"],
                        f"the sheet is still open showing {after['title']!r} while the "
                        f"page shows {after['venue']!r}")
        self.assertFalse(after["behindInert"],
                         "the page behind the sheet is still inert and cannot be used")

    def test_one_traversal_over_both_the_area_and_the_fragment(self):
        """`history.go(-2)` crosses the fragment and the area in a single step, which is
        the case that fires no hashchange at all."""
        self.pick_orion()
        self.pick_promenadi()
        self.open_first_film()
        self.page.evaluate("history.go(-2)")
        expect(self.page.locator("#areaSelect")).to_contain_text("Cinema Orion")
        after = self.state()
        self.assertTrue(after["hidden"], f"sheet still showing {after['title']!r}")
        self.assertFalse(after["behindInert"])
        self.assertEqual(after["url"], "?area=or-helsinki")

    def test_back_to_the_chooser_closes_the_sheet_too(self):
        """Home clears the selection, and `syncSheet` returns early without one, so even
        a later hashchange could not close it."""
        self.pick_orion()
        self.open_first_film()
        self.page.evaluate("history.go(-2)")
        expect(self.page.locator("#homeMore")).to_be_visible()
        after = self.state()
        self.assertTrue(after["hidden"], f"sheet still showing {after['title']!r} on the chooser")
        self.assertFalse(after["behindInert"])

    def test_the_wrong_film_is_gone_before_the_new_schedule_arrives(self):
        """Closing after the load would leave a window where the previous cinema's film
        and its ticket links sit over the incoming venue's page, inert behind them.

        The reload is what makes that window real: a traversal alone refetches nothing,
        because the venue being returned to is already in `jsonCache`. After a reload the
        history is intact and the cache is empty, so Back does fetch -- and the fixture
        answers that one file a second late.
        """
        Handler.delay["area-or-helsinki.json"] = 1.0
        self.addCleanup(Handler.delay.clear)
        self.pick_orion()           # answered late, and uncacheable, from here on
        self.pick_promenadi()
        self.open_first_film()
        self.page.reload()
        expect(self.page.locator("#sheetTitle")).to_have_text("Porin oma elokuva")
        self.page.evaluate("history.go(-2)")
        # Read while Orion's schedule is still in flight: the label changes before the
        # load, so it is no evidence either way, and the file takes a second to answer.
        mid = self.state()
        self.assertIn("Cinema Orion", mid["venue"])
        self.assertTrue(mid["hidden"],
                        f"mid-load the sheet still showed {mid['title']!r}")
        self.assertFalse(mid["behindInert"], "mid-load the page behind was still inert")
        expect(self.page.locator("#areaSelect")).to_contain_text("Cinema Orion")

    def test_forward_into_a_sheet_entry_shows_that_venue_s_film(self):
        """Forward is the same reconciliation the other way: the entry names an area and a
        film, and the film shown has to be that area's."""
        self.pick_orion()
        self.pick_promenadi()
        self.open_first_film()
        self.page.evaluate("history.go(-2)")
        expect(self.page.locator("#areaSelect")).to_contain_text("Cinema Orion")
        self.page.evaluate("history.go(2)")
        expect(self.page.locator("#areaSelect")).to_contain_text("Promenadi")
        after = self.state()
        self.assertFalse(after["hidden"], "the entry names a film; the sheet belongs open")
        self.assertIn("Porin", after["title"])

    def test_closing_the_sheet_puts_focus_back_on_the_card(self):
        """The counterweight to all of the above: an ordinary close still returns the
        keyboard to what opened the sheet, so the traversal fix cannot be a blanket
        hideSheet that drops focus to the document."""
        self.pick_orion()
        self.open_first_film()
        opened = self.state()
        self.assertFalse(opened["hidden"])
        self.page.keyboard.press("Escape")
        closed = self.state()
        self.assertTrue(closed["hidden"], "Escape no longer closes the sheet")
        self.assertFalse(closed["behindInert"])
        self.assertNotEqual(closed["focus"], "",
                            "focus fell to the document instead of the card")


class PickersStayModal(Browser):
    """Three modals drive one `inert` flag on the page behind them.

    The month picker, the venue picker and the movie sheet all call
    `BEHIND().forEach(el => setInert(el, ...))`, so whichever closes last decides what the
    page behind is. `hideSheet` clears that flag whether or not the sheet was the thing
    that set it, and `onPopState` calls `hideSheet` on every traversal, so a Back pressed
    with a picker open left a `role="dialog" aria-modal="true"` over a fully tabbable page
    whose keydown handler still swallowed Escape and the arrows.
    """

    def behind(self):
        return self.page.evaluate("""() => ({
            main: !!document.querySelector('main').inert,
            header: !!document.querySelector('header').inert,
            venueOpen: document.querySelector('#vwrap').classList.contains('open'),
            calOpen: !!document.querySelector('.calwrap, #calwrap'),
        })""")

    def test_back_with_the_venue_picker_open_leaves_it_modal(self):
        self.pick_orion()
        self.open_picker()
        opened = self.behind()
        self.assertTrue(opened["venueOpen"] and opened["main"] and opened["header"],
                        "the picker should be open over an inert page")
        self.page.go_back()
        after = self.behind()
        if after["venueOpen"]:
            self.assertTrue(after["main"] and after["header"],
                            "the picker is still open and the page behind it is not inert")
        else:
            self.assertFalse(after["main"] or after["header"],
                             "the picker closed and left the page inert")

    def test_closing_the_venue_picker_after_a_traversal_still_clears_inert(self):
        """The counterweight: whatever the fix does, the ordinary close must still hand
        the page back."""
        self.pick_orion()
        self.open_picker()
        self.page.go_back()
        self.page.keyboard.press("Escape")
        expect(self.page.locator("#vwrap")).not_to_have_class("vwrap open")
        after = self.behind()
        self.assertFalse(after["main"] or after["header"])

    def test_a_traversal_with_no_modal_open_leaves_the_page_alone(self):
        self.pick_orion()
        self.page.go_back()
        after = self.behind()
        self.assertFalse(after["main"] or after["header"])


if __name__ == "__main__":
    unittest.main()
