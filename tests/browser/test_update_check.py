"""The stale banner against the service worker's background refresh, in a real engine.

test_client_browser.py blocks the worker; these tests need it, because what they check is
the order in which the worker answers from its cache, refreshes behind, and messages the
page. Each test seeds the worker with a 24-hour-old copy of Orion's schedule, changes what
the server answers, reloads, and watches #stale.

`city:Helsinki` is the selection: a combined city's members are known only once the venue
lists arrive, but the boot prefetches them from the ids stored in prefs, so the worker's
refresh can land before the slot exists. Whether it does is a race between the refresh and
the page's boot, so a test that needs it drops Orion's venue list from Cache Storage and
delays it on the server: the fill then waits on the network. In the fixture the city is Orion plus Finnkino
members whose files 404, so the banner turns on Orion's file alone, which the handler
below serves with whatever `generated` the test sets.

Timestamps are relative to the real clock: the worker runs outside the page, where
`page.clock` does not reach.
"""
import datetime
import http.server
import json
import os
import threading
import time
import unittest
import zoneinfo

from playwright.sync_api import expect, sync_playwright

import test_client_browser as base

AREA = json.loads((base.FIXTURE / "data/area-or-helsinki.json").read_text(encoding="utf-8"))
URL = "/index.html?area=city:Helsinki"


def hours_ago(h):
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=h)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(iso):
    """The credit line's time for `iso` as fi-FI draws it: "p\u00e4ivitetty 23.9. klo 14.10"."""
    t = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc).astimezone(zoneinfo.ZoneInfo("Europe/Helsinki"))
    return f"p\u00e4ivitetty {t.day}.{t.month}. klo {t:%H.%M}"


class Handler(base.Handler):
    """base.Handler, with Orion's schedule file answered from `server.cfg`: its
    `generated`, its status and a delay. Nothing may be answered from the browser's HTTP
    cache, so the worker's Cache Storage is the only copy in play."""

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        cfg = self.server.cfg
        if path.endswith("/data/area-or-helsinki.json"):
            self.server.requested.append(path)
            time.sleep(cfg["area_delay"])
            if cfg["area_status"] != 200:
                self.send_error(cfg["area_status"])
                return
            body = json.dumps({**AREA, "generated": cfg["generated"]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path.endswith("/data/venues-orion.json"):
            time.sleep(cfg["venues_delay"])
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        http.server.SimpleHTTPRequestHandler.end_headers(self)


class UpdateCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.srv.served, cls.srv.requested = [], []
        cls.srv.cfg = {}
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.origin = f"http://127.0.0.1:{cls.srv.server_port}"
        cls.pw = sync_playwright().start()
        engine = os.environ.get("KINO_BROWSER_ENGINE", "chromium")
        channel = os.environ.get("KINO_BROWSER_CHANNEL") if engine == "chromium" else None
        cls.browser = getattr(cls.pw, engine).launch(channel=channel or None, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop(); cls.srv.shutdown()

    def setUp(self):
        self.srv.cfg.update(generated=hours_ago(24), area_status=200, area_delay=0,
                            venues_delay=0)
        self.ctx = self.browser.new_context(timezone_id="Europe/Helsinki", locale="fi-FI",
                                            service_workers="allow")
        self.ctx.tracing.start(screenshots=True, snapshots=True)
        base.OUT.mkdir(exist_ok=True)
        self.page = self.ctx.new_page()
        self.stale = self.page.locator("#stale")
        self.credit = self.page.locator("#credit")
        # First load installs the worker and stores the city's member ids in prefs; the
        # second, controlled, puts the 24-hour-old copy in Cache Storage. The banner is
        # then true on both sides: the server has nothing newer yet.
        self.page.goto(self.origin + URL)
        self.page.wait_for_function("navigator.serviceWorker.controller !== null")
        self.page.reload()
        expect(self.stale).to_contain_text("\u26a0")
        expect(self.credit).to_contain_text(stamp(self.srv.cfg["generated"]))

    def uncache(self, fragment):
        """Drop every Cache Storage entry whose URL contains `fragment`."""
        self.page.evaluate("""async f => {
            for (const k of await caches.keys()) {
                const c = await caches.open(k);
                for (const r of await c.keys()) if (r.url.includes(f)) await c.delete(r);
            }
        }""", fragment)

    def tearDown(self):
        res = getattr(self._outcome, "result", None)
        failed = any(t is self for t, _ in (res.failures + res.errors)) if res else False
        name = base.OUT / self.id().split(".")[-1]
        if failed:
            self.page.screenshot(path=f"{name}.png", full_page=True)
            self.ctx.tracing.stop(path=f"{name}.zip")
        else:
            self.ctx.tracing.stop()
        self.ctx.close()

    def test_a_refresh_that_lands_before_the_city_is_drawn_is_applied(self):
        """The server now has an hour-old copy, and the venue lists take 2 s. The worker's
        refresh lands long before the city's slot exists; the slot is filled with the
        24-hour-old copy the prefetch was handed, and the replay must replace it without
        a reload. Until 2026-09-23 the message was dropped and the warning stayed."""
        self.srv.cfg.update(generated=hours_ago(1), venues_delay=2.0)
        self.uncache("/data/venues-orion.json")
        self.page.reload()
        # The credit line is the schedule on screen: until it names the new copy, a hidden
        # banner only means nothing has been drawn yet.
        expect(self.credit).to_contain_text(stamp(self.srv.cfg["generated"]), timeout=8_000)
        expect(self.stale).to_be_hidden()


if __name__ == "__main__":
    unittest.main()
