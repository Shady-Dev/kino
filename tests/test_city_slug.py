"""Two cities whose names fold to one slug fail the page build before a page is staged.

Venue slugs were de-duplicated and city slugs were not: "Jyväskylä" and "Jyvaskyla" would
both stage `/kaupunki/jyvaskyla/`, the later page silently replacing the earlier one, and
the sitemap would list the URL twice (review L13, 2026-11-22). None of the 116 committed
cities collides; this holds the case for the next spelling a provider ships.
"""
import json
import unittest

import _ctx                                                # noqa: F401
import build_pages as bp
import test_home_sync_exit as H


class CitySlugTest(unittest.TestCase):

    setUp = H.HomeSyncExitTest.setUp
    write_block = H.HomeSyncExitTest.write_block
    build = H.HomeSyncExitTest.build

    def rename(self, names):
        path = bp.DATA / "areas.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        for a, n in zip(doc["areas"], names):
            a["name"] = n
        path.write_text(json.dumps(doc), encoding="utf-8")

    def test_two_spellings_of_one_page_city_fail_and_write_nothing(self):
        self.rename(["Kino Testi Jyväskylä", "Studio Testi Jyväskylä",
                     "Kino Testi Jyvaskyla", "Studio Testi Jyvaskyla"])
        with self.assertRaisesRegex(RuntimeError, "share the page slug 'jyvaskyla'"):
            self.build()
        self.assertFalse((self.root / "kaupunki").exists())
        self.assertFalse((self.root / "sitemap.xml").exists())

    def test_distinct_slugs_still_build(self):
        self.write_block(bp.home_links_html(bp.home_cities()))
        code, _ = self.build()
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "kaupunki/espoo/index.html").is_file())
        self.assertTrue((self.root / "kaupunki/oulu/index.html").is_file())


if __name__ == "__main__":
    unittest.main()
