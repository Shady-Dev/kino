"""A site with nothing on must not fail the run; a broken parse still must.

"A whole site parsing zero showtimes fails the run" is what catches a parse that broke
silently, and it has to keep doing that. But eight sites here are a single small venue --
K-Kino publishes 3 showtimes, Kino Saimaa 2 -- so a cinema with a quiet week turning the
whole run red stopped being hypothetical when the eTiketti sweep landed. Joutsan Kino had
just shown what one red site does to a module: exit=1 with everything else green.

The line is drawn where the adapter has information run.py does not: what the listing
said. An empty listing is a cinema with no programme. A listing full of films that
yields no showtimes is a broken parser wearing the same clothes, and every test below
that keeps it failing is the point of the exercise.
"""
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import common
import run


SITE = {
    "provider": "fakechain", "label": "Fake Chain",
    "venues": [{"id": "fc-a", "name": "Alpha", "short": "Alpha", "city": "Espoo"}],
}


class Mod:
    __name__ = "fakemod"
    SITES = [SITE]

    def __init__(self, behaviour):
        self.behaviour = behaviour

    def fetch_site(self, site):
        if isinstance(self.behaviour, Exception):
            raise self.behaviour
        return self.behaviour


class EmptyProgrammeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._saved))

    def run_mod(self, mod):
        import importlib
        real = importlib.import_module
        importlib.import_module = lambda name: mod if name == "fakemod" else real(name)
        self.addCleanup(lambda: setattr(importlib, "import_module", real))
        return run.main(["fakemod", "--half", "all"])

    def test_an_empty_listing_does_not_fail_the_run(self):
        code = self.run_mod(Mod(common.EmptyProgramme("listing lists no films")))
        self.assertEqual(code, 0)

    def test_a_listing_with_films_and_no_showtimes_still_fails(self):
        """The case the rule exists for. An adapter that parsed a full listing into
        nothing is broken, and must not be able to hide behind the same silence."""
        code = self.run_mod(Mod({"fc-a": []}))
        self.assertEqual(code, 1)

    def test_a_fetch_error_still_fails(self):
        code = self.run_mod(Mod(RuntimeError("connection reset")))
        self.assertEqual(code, 1)

    def test_an_empty_site_writes_no_venue_file(self):
        """Nothing is stamped fresh for a site that produced nothing, so the health line
        ages honestly instead of going green on an empty answer."""
        self.run_mod(Mod(common.EmptyProgramme("nothing on")))
        self.assertFalse((run.OUT / "venues-fakechain.json").exists())

    def test_a_module_with_no_sites_for_this_half_is_not_a_failure(self):
        """Site-level routing made this reachable: `run.py biorex --half local` has
        nothing to do and must say so with 0, not fail. Before routing, a run that
        produced no venues could only mean everything broke."""
        class CloudOnly(Mod):
            SITES = [SITE]
        mod = CloudOnly({"fc-a": []})
        import registry
        real = registry.by_id
        registry.by_id = lambda pid: ({"where": "cloud"} if pid == "fakechain"
                                      else real(pid))
        self.addCleanup(lambda: setattr(registry, "by_id", real))
        import importlib
        realimp = importlib.import_module
        importlib.import_module = lambda n: mod if n == "fakemod" else realimp(n)
        self.addCleanup(lambda: setattr(importlib, "import_module", realimp))
        self.assertEqual(run.main(["fakemod", "--half", "local"]), 0)

    def test_an_empty_site_does_not_wipe_data_it_published_before(self):
        """The discriminator can be wrong -- a site that changed its markup so film
        links stop matching looks identical to one with nothing on. Keeping the previous
        file is what makes being wrong survivable."""
        (run.OUT).mkdir(exist_ok=True)
        prev = {"generated": "2026-08-01T00:00:00+00:00", "dates": ["2026-08-02"],
                "horizon": "2026-08-02",
                "shows": [{"title": "Dyyni", "start": "2026-08-02T18:00:00+03:00"}]}
        (run.OUT / "area-fc-a.json").write_text(json.dumps(prev), encoding="utf-8")
        self.run_mod(Mod(common.EmptyProgramme("nothing on")))
        after = json.loads((run.OUT / "area-fc-a.json").read_text(encoding="utf-8"))
        self.assertEqual(after, prev)


class NexxoEmptyTest(unittest.TestCase):
    """Nexxo is where this case is not hypothetical: four hosts answer public_api.php
    with valid JSON and no shows at any locationid, permanently. The distinction the
    adapter has to make is between that and a request that never landed."""

    SITE = {"provider": "p", "base": "https://example.test", "programme": "/ohjelmisto/",
            "venues": [
                {"id": "a", "locationid": "1", "name": "A", "short": "A", "city": "X"},
                {"id": "b", "locationid": "2", "name": "B", "short": "B", "city": "Y"},
            ]}

    def patch(self, fn):
        import nexxo
        real = nexxo.fetch_venue
        nexxo.fetch_venue = fn
        self.addCleanup(lambda: setattr(nexxo, "fetch_venue", real))
        return nexxo

    def test_every_locationid_answering_with_no_shows_is_an_empty_programme(self):
        nexxo = self.patch(lambda site, v, **kw: [])
        with self.assertRaises(common.EmptyProgramme):
            nexxo.fetch_site(self.SITE, sleep=0)

    def test_a_failed_request_is_a_failure_not_an_empty_programme(self):
        """If a locationid never answered we do not know what the site holds, so this
        must stay a plain empty result and fail the run the way it always did."""
        def boom(site, v, **kw):
            raise RuntimeError("403")
        nexxo = self.patch(boom)
        self.assertEqual(nexxo.fetch_site(self.SITE, sleep=0), {})

    def test_one_answering_and_one_failing_is_not_an_empty_programme(self):
        def half(site, v, **kw):
            if v["locationid"] == "1":
                return []
            raise RuntimeError("403")
        nexxo = self.patch(half)
        self.assertEqual(nexxo.fetch_site(self.SITE, sleep=0), {"a": []})

    def test_any_showtime_anywhere_means_a_normal_result(self):
        nexxo = self.patch(lambda site, v, **kw: [{"start": "x"}] if v["locationid"] == "1" else [])
        out = nexxo.fetch_site(self.SITE, sleep=0)
        self.assertEqual(len(out["a"]), 1)


if __name__ == "__main__":
    unittest.main()
