"""A city page's film heading opens that film's sheet in the app, in the page's city and
language (2026-11-03).

The pages are built from this file's two Helsinki venues and served beside the app, which
reads the same files. Copies of one film under a format, a dubbing and an author-visit
title each open one sheet, and so does a film whose group the app names by a copy dated
after the page's two days.
"""
import contextlib
import http.server
import io
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date

from playwright.sync_api import expect

import _harness
import test_client_browser as base

sys.path.insert(0, str(base.ROOT / "scripts"))
import build_pages as bp                                            # noqa: E402

DAY, DAY2, DAY3 = "2026-09-14", "2026-09-15", "2026-09-16"
OR, KP = "or-helsinki", "1100"


def show(vid, eid, title, day, clock, tmdb=0):
    return {"eventId": eid, "title": title, "original": "", "len": "100", "rating": "K-7",
            "age": "", "genres": "Draama", "img": "", "price": "", "tmdb": 7.0, "votes": 30,
            "theatre": "Cinema Orion" if vid == OR else "Kinopalatsi", "aud": "Sali 1",
            "lang": "FI-A", "method": "", "start": f"{day}T{clock}:00+03:00", "soldOut": False,
            "provider": "orion" if vid == OR else "finnkino", "venue": vid, "tmdbId": tmdb,
            "url": f"https://example.invalid/{vid}/{eid}/{day}/{clock}"}


SHOWS = {
    OR: [show(OR, "tav", "Tavallinen elokuva", DAY, "18:00"),
         show(OR, "sama", "Sama elokuva", DAY2, "19:00"),
         show(OR, "acme-en", "Kojootti vs. ACME (englanniksi)", DAY, "21:00", 1204680),
         show(OR, "purra-v", "Minä ja Riikka Purra (+tekijävierailu)", DAY2, "18:30", 900),
         show(OR, "shaun-sv", "Fåret Shaun och monstret på bondgården", DAY3, "14:00", 55)],
    KP: [show(KP, "sama2d", "Sama elokuva 2D", DAY, "17:00"),
         show(KP, "sama3d", "Sama elokuva 3D", DAY, "20:00"),
         show(KP, "acme-fi", "Kojootti vs. ACME, suomeksi", DAY, "16:00", 1204680),
         show(KP, "purra", "Minä ja Riikka Purra", DAY, "13:30", 900),
         show(KP, "lammas", "Late Lammas -elokuva: Hämäräpuuhissa", DAY2, "15:00", 55)],
}
# Heading -> every screening its sheet holds, as (day, time).
SHEETS = {
    "Tavallinen elokuva": {("14.9.", "18:00")},
    "Sama elokuva": {("14.9.", "17:00"), ("14.9.", "20:00"), ("15.9.", "19:00")},
    "Kojootti vs. ACME": {("14.9.", "16:00"), ("14.9.", "21:00")},
    "Minä ja Riikka Purra": {("14.9.", "13:30"), ("15.9.", "18:30")},
    "Late Lammas -elokuva: Hämäräpuuhissa": {("15.9.", "15:00"), ("16.9.", "14:00")},
}
LAMMAS = "Late Lammas -elokuva: Hämäräpuuhissa"

TICKETS = """() => {
  const out = []; let day = '';
  for (const el of document.querySelectorAll('#sheet .sheet-days > *')) {
    if (el.tagName === 'H3') { day = (el.textContent.match(/\\d+\\.\\d+\\./) || [''])[0]; continue; }
    for (const s of el.querySelectorAll('.stub'))
      out.push([day, s.querySelector('.time').textContent.trim(), s.classList.contains('pick')]);
  }
  return out;
}"""


class Handler(base.Handler):
    """The app from the checkout; data and the generated pages from the build."""

    def translate_path(self, path):
        rel = path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        built = rel.startswith(("data/", "kaupunki/", "sv/", "en/"))
        return str((self.server.built if built else base.ROOT) / rel)


class CityTitleLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.tmp.name)
        shutil.copytree(base.FIXTURE / "data", root / "data")
        for vid, shows in SHOWS.items():
            (root / "data" / f"area-{vid}.json").write_text(json.dumps(
                {"generated": "2026-09-14T08:00:00+00:00", "dates": [DAY, DAY2, DAY3],
                 "horizon": DAY3, "shows": shows}), encoding="utf-8")
        (root / "data" / "tmdb-genres.json").write_text('{"fi": {}, "sv": {}, "en": {}}')
        (root / "data" / "films-extra.json").write_text('{"films": {}}')
        saved = (bp.ROOT, bp.DATA)
        bp.ROOT, bp.DATA = root, root / "data"
        bp._SHOWS.clear(); bp._unmirrored_hosts.clear()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                bp.main(today=date.fromisoformat(DAY))
        finally:
            bp.ROOT, bp.DATA = saved
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.srv.served, cls.srv.requested, cls.srv.built = [], [], root
        _harness.start(cls.srv)
        cls.origin = f"http://127.0.0.1:{cls.srv.server_port}"
        cls.pw = _harness.playwright()
        engine = os.environ.get("KINO_BROWSER_ENGINE", "chromium")
        channel = os.environ.get("KINO_BROWSER_CHANNEL") if engine == "chromium" else None
        cls.browser = getattr(cls.pw, engine).launch(channel=channel or None, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); _harness.stop(cls.srv); cls.tmp.cleanup()

    def setUp(self):
        self.ctx = None

    def tearDown(self):
        if self.ctx:
            self.ctx.close()

    def jump(self, path, nth, width=1200):
        """Open `path`, click its `nth` heading. -> (page, heading, the link's day)"""
        # One context open at a time: WebKit hung with a test's worth of failed ones open.
        if self.ctx:
            self.ctx.close()
        self.ctx = ctx = self.browser.new_context(
            viewport={"width": width, "height": 900}, timezone_id="Europe/Helsinki",
            service_workers="block")
        ctx.set_default_timeout(10000)
        page = ctx.new_page()
        page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(self.origin)
                   else r.abort())
        page.clock.install(time=base.FIXED)
        page.goto(self.origin + path)
        link = page.locator("article.film h3 a").nth(nth)
        head = link.text_content()
        day = re.search(r"&d=\d{4}-(\d\d)-(\d\d)$", link.get_attribute("href"))
        link.click()
        expect(page.locator("#sheet a.stub").first).to_be_visible()
        return page, head, f"{int(day.group(2))}.{int(day.group(1))}."

    def test_each_heading_opens_its_own_film_on_its_day(self):
        for width in (393, 1200):
            for nth in range(7):
                with self.subTest(width=width, nth=nth):
                    page, head, day = self.jump("/kaupunki/helsinki/", nth, width)
                    tickets = page.evaluate(TICKETS)
                    self.assertEqual({(d, t) for d, t, _ in tickets}, SHEETS[head], head)
                    self.assertEqual([d for d, _, pick in tickets if pick], [day], head)

    def test_the_city_and_the_language_survive_the_jump_and_the_close(self):
        for path, lang, city in (("/kaupunki/helsinki/", "fi", "Helsinki"),
                                 ("/sv/kaupunki/helsinki/", "sv", "Helsingfors"),
                                 ("/en/city/helsinki/", "en", "Helsinki")):
            with self.subTest(lang=lang):
                page, head, _ = self.jump(path, 4)
                self.assertEqual(head, LAMMAS)
                self.assertEqual(len(page.evaluate(TICKETS)), 2)
                want = f"?area=city%3AHelsinki&lang={lang}"
                self.assertEqual(page.evaluate("location.search"), want)
                self.assertEqual(page.evaluate("document.documentElement.lang"), lang)
                page.keyboard.press("Escape")
                expect(page.locator("#sheet")).to_have_attribute("inert", "")
                self.assertEqual(page.evaluate("location.search + '|' + location.hash"),
                                 want + "|")
                expect(page.locator("#areaSelect")).to_contain_text(city)


if __name__ == "__main__":
    unittest.main()
