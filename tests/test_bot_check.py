"""Adapters whose hosts have served the runner a bot-check page name that page in their logs.

From 2026-09-18 to 2026-10-19 eight cloud runs were served a page titled "One moment,
please..." by these hosts, and three of the adapters said only that a marker was missing.
The fixture holds the title and the one sentence measured on that page and nothing else of
it. Evidence: docs/research/runner-challenges.md.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import cinemahouse
import common
import kinotour
import kirkkonummi
import lieksa
import matintupa
import navetta
import run
import tmb
import vpk

BOT_CHECK = ("<!DOCTYPE html><html><head><title>One moment, please...</title></head><body>"
             "<p>Please wait while your request is being verified...</p></body></html>")
ORDINARY = "<html><head><title>Tervetuloa</title></head><body><p>Tervetuloa</p></body></html>"
TODAY = datetime.date(2026, 10, 19)

# (module, the function that hands it the page, the URL its log names, how to run it)
ADAPTERS = [
    (kirkkonummi, "get_listing", "https://kinokirkkonummi.fi/",
     lambda: kirkkonummi.fetch_site()),
    (lieksa, "get", "https://www.lieksanelokuvat.net/",
     lambda: lieksa.fetch_site(lieksa.SITES[0], TODAY)),
    (tmb, "get", "https://toijalan-kino.info/?lista=1",
     lambda: tmb.fetch_site(tmb.SITES[0], sleep=0)),
    (vpk, "get", "https://www.pyhasalmenvpk.fi/wp-json/my-calendar/v1/events",
     lambda: vpk.fetch_site(vpk.SITES[0], TODAY)),
    (matintupa, "get_text", "https://www.matin-tupa.fi/ohjelmistossa/",
     lambda: matintupa.fetch_site(matintupa.SITES[0], TODAY)),
    (navetta, "get", "https://www.navettakino.fi/",
     lambda: navetta.fetch_site(navetta.SITES[0], TODAY)),
    (kinotour, "get", "https://www.kinotour.fi/varaa-liput-elokuvatapahtumiin/",
     lambda: kinotour.fetch_site(kinotour.SITES[0])),
    (cinemahouse, "get", "https://www.kinopiispanristi.fi/",
     lambda: cinemahouse.fetch_site(cinemahouse.SITES[0])),
]


class AdapterTest(unittest.TestCase):
    def setUp(self):
        common._seen.headers = {}
        self.addCleanup(lambda: setattr(common._seen, "headers", {}))

    def failure(self, mod, attr, page, call):
        saved = getattr(mod, attr)
        setattr(mod, attr, lambda *a, **kw: page)
        self.addCleanup(setattr, mod, attr, saved)
        with self.assertRaises(Exception) as cm, contextlib.redirect_stdout(io.StringIO()):
            call()
        return cm.exception

    def test_a_bot_check_page_fails_the_site_and_says_so(self):
        for mod, attr, url, call in ADAPTERS:
            with self.subTest(mod.__name__):
                e = self.failure(mod, attr, BOT_CHECK, call)
                self.assertIsInstance(e, common.BotCheck)
                self.assertNotIsInstance(e, common.EmptyProgramme)
                self.assertIn(url, str(e))
                self.assertIn("bot-check page", str(e))
                self.assertIn(f'{len(BOT_CHECK)} B served, titled "One moment, please..."',
                              str(e))

    def test_any_other_page_fails_with_what_was_served(self):
        for mod, attr, url, call in ADAPTERS:
            with self.subTest(mod.__name__):
                e = self.failure(mod, attr, ORDINARY, call)
                self.assertNotIsInstance(e, common.BotCheck)
                self.assertNotIsInstance(e, common.EmptyProgramme)
                self.assertIn(f'{len(ORDINARY)} B served, titled "Tervetuloa"', str(e))


class RunnerTest(unittest.TestCase):
    """The run still fails and the previous files stand."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved_out, saved_get = run.OUT, matintupa.get_text
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(setattr, run, "OUT", saved_out)
        self.addCleanup(setattr, matintupa, "get_text", saved_get)

    def test_the_run_fails_and_keeps_the_previous_file(self):
        venue = matintupa.SITES[0]["venues"][0]["id"]
        kept = {"generated": "2026-10-19T11:15:00+00:00", "dates": ["2026-10-19"],
                "horizon": "2026-10-19",
                "shows": [{"title": "Eilen", "start": "2026-10-19T18:00:00+03:00"}]}
        (run.OUT / f"area-{venue}.json").write_text(json.dumps(kept), encoding="utf-8")
        matintupa.get_text = lambda *a, **kw: BOT_CHECK
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = run.main(["matintupa", "--half", "all"])
        self.assertNotEqual(code, 0)
        self.assertIn("FAILED: https://www.matin-tupa.fi/ohjelmistossa/: the host served a "
                      "bot-check page", out.getvalue())
        after = json.loads((run.OUT / f"area-{venue}.json").read_text(encoding="utf-8"))
        self.assertEqual(after, kept)


if __name__ == "__main__":
    unittest.main()
