"""sw.js never caches a failed response, and its cache writes outlive the response.

Posters are cache-first, so a cached 404 stays broken for the life of the cache version;
the generic branch holds index.html, whose cached copy is the offline fallback. Once the
response promise settles the browser may stop the worker, so every write goes through
e.waitUntil. The harness models that: put() settles on a macrotask and `stored` is read
only after the response and every waitUntil promise have settled.

Driven through tests/sw_fetch_harness.js, which runs the real sw.js with stubbed Cache and
fetch and records which URLs the code chose to cache.
"""
import json
import pathlib
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "sw_fetch_harness.js"


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class ServiceWorkerCacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.results = {r["name"]: r for r in json.loads(out.stdout)}

    def stored(self, name):
        return self.results[name]["stored"]

    # -- failures are never written ------------------------------------------------

    def test_a_404_poster_is_not_cached(self):
        self.assertEqual(self.stored("poster_404"), [],
                         "a cache-first 404 stays broken for the life of the cache")

    def test_a_500_poster_is_not_cached(self):
        self.assertEqual(self.stored("poster_500"), [])

    def test_a_500_page_is_not_cached(self):
        self.assertEqual(self.stored("page_500"),
                         [], "a cached 500 becomes the offline fallback")

    def test_a_404_data_file_is_not_cached(self):
        self.assertEqual(self.stored("data_404"), [])

    # -- success still is ----------------------------------------------------------

    def test_a_200_poster_is_cached(self):
        self.assertEqual(len(self.stored("poster_200")), 1)

    def test_a_200_page_is_cached(self):
        self.assertEqual(len(self.stored("page_200")), 1)

    def test_a_200_data_file_is_cached(self):
        self.assertEqual(len(self.stored("data_200")), 1)

    # -- scope ---------------------------------------------------------------------

    def test_cross_origin_is_left_alone(self):
        """Ticket links and trailers are someone else's origin; the SW must not touch
        them at all, not merely decline to cache them."""
        self.assertFalse(self.results["cross_origin"]["intercepted"])

    def test_a_non_get_is_left_alone(self):
        self.assertFalse(self.results["not_get"]["intercepted"])


if __name__ == "__main__":
    unittest.main()
