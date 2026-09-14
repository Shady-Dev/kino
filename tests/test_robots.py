"""robots.txt lets a renderer fetch what the client needs and nothing else under /data/.

Search Console's live test of `/` on 2026-09-13 rendered an empty picker and the
load-failure line, and its resource report listed 14 of 15 requests as blocked by
robots.txt: `Disallow: /data/` covered every JSON the app reads. Googlebot renders the
page before indexing it, so the data files are rendering dependencies, not crawl waste.

The rules are checked with Google's own matching (the robots.txt RFC 9309 semantics
Google documents): a rule is a path prefix, `*` matches any run of characters, `$`
anchors the end, the query string is part of the matched path, the longest matching rule
wins and a tie goes to Allow. Python's urllib.robotparser applies rules in file order,
which is not that, so the matcher lives here. Every URL below is a real file in data/ or
a literal path in index.html or status/index.html, so a renamed file fails the test.
"""
import pathlib
import re
import unittest

import _ctx                                                # noqa: F401

ROOT = _ctx.ROOT
ROBOTS = (ROOT / "robots.txt").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
STATUS = (ROOT / "status" / "index.html").read_text(encoding="utf-8")


def rules(text=ROBOTS, agent="*"):
    """(allow, disallow, sitemaps) for one user-agent group."""
    allow, disallow, sitemaps, mine = [], [], [], False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "sitemap":
            sitemaps.append(value)
        elif key == "user-agent":
            mine = value == agent
        elif mine and key == "allow" and value:
            allow.append(value)
        elif mine and key == "disallow" and value:
            disallow.append(value)
    return allow, disallow, sitemaps


def matches(pattern, path):
    rx = "^" + re.escape(pattern).replace(r"\*", ".*")
    if rx.endswith(r"\$"):
        rx = rx[:-2] + "$"
    return re.match(rx, path) is not None


def allowed(path, text=ROBOTS):
    """Google's verdict for a path (with its query string, if any)."""
    allow, disallow, _ = rules(text)
    best_a = max((len(p) for p in allow if matches(p, path)), default=-1)
    best_d = max((len(p) for p in disallow if matches(p, path)), default=-1)
    if best_d < 0:
        return True
    return best_a >= best_d          # longest wins; a tie goes to Allow


# What the client reads. Families are the filename prefixes the pipeline writes; the
# literal files are every static `data/...json` path in the two pages.
CONSUMED = ("providers.json", "regions.json", "areas.json", "films.json",
            "films-extra.json", "tmdb-genres.json")
FAMILIES = ("venues-", "area-", "posters/")
# Pipeline state nothing public reads.
INTERNAL = ("tmdb.json", "tmdb-titles.json", "prices-")


def literal_paths(html):
    return sorted(set(re.findall(r"/?(data/[A-Za-z0-9_.-]+\.json)", html)))


def data_files():
    return sorted(p.name for p in (ROOT / "data").glob("*.json"))


class MatcherTest(unittest.TestCase):
    """The semantics the rest of the file depends on, on a fixed text."""

    TEXT = "User-agent: *\nDisallow: /data/\nAllow: /data/area-\nAllow: /data/x.json\n"

    def test_the_longest_matching_rule_wins(self):
        self.assertTrue(allowed("/data/area-br-tripla.json", self.TEXT))
        self.assertFalse(allowed("/data/other.json", self.TEXT))

    def test_the_query_string_is_part_of_the_path(self):
        self.assertTrue(allowed("/data/x.json?v=3", self.TEXT))
        self.assertFalse(allowed("/data/y.json?v=3", self.TEXT))

    def test_a_tie_goes_to_allow(self):
        self.assertTrue(allowed("/data/", "User-agent: *\nDisallow: /data/\nAllow: /data/\n"))

    def test_wildcard_and_end_anchor(self):
        text = "User-agent: *\nDisallow: /*.log$\n"
        self.assertFalse(allowed("/run-enrich.log", text))
        self.assertTrue(allowed("/run-enrich.log.txt", text))

    def test_another_agents_group_is_not_ours(self):
        text = "User-agent: other\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
        self.assertTrue(allowed("/data/anything", text))


class StartupTest(unittest.TestCase):

    def test_the_page_and_its_shell_are_allowed(self):
        for path in ("/", "/index.html", "/sw.js", "/manifest.webmanifest",
                     "/fonts/", "/icon-192.png"):
            self.assertTrue(allowed(path), path)

    def test_every_literal_data_path_in_the_app_is_allowed(self):
        paths = literal_paths(INDEX)
        self.assertGreaterEqual(len(paths), 6, paths)
        for p in paths:
            self.assertTrue(allowed("/" + p), p)

    def test_every_literal_data_path_on_the_status_page_is_allowed(self):
        paths = literal_paths(STATUS)
        self.assertTrue(paths)
        for p in paths:
            self.assertTrue(allowed("/" + p), p)

    def test_the_startup_files_are_the_ones_the_app_names(self):
        """The list above is not a guess: each consumed file is fetched by index.html."""
        for name in CONSUMED:
            self.assertIn(f"data/{name}", INDEX, name)
            self.assertTrue(allowed(f"/data/{name}"), name)

    def test_no_fetch_carries_a_cache_buster(self):
        """The rules match request URLs; a `?v=` on a fetch would still be covered by a
        prefix rule, but the app sends none, and this pins that."""
        for html in (INDEX, STATUS):
            self.assertNotRegex(html, r"\.json\?")
        self.assertIn("const r = await fetch(path, { signal: ac.signal });", INDEX)


class DataDirectoryTest(unittest.TestCase):
    """Every committed file under data/ is either consumed and allowed or internal and
    blocked. A new family that is neither fails here and has to be classified."""

    def test_every_venue_list_is_allowed(self):
        venues = [f for f in data_files() if f.startswith("venues-")]
        self.assertGreaterEqual(len(venues), 30, "measured 38 on 2026-09-13")
        for f in venues:
            self.assertTrue(allowed(f"/data/{f}"), f)

    def test_every_area_file_is_allowed_across_providers_and_scopes(self):
        areas = [f for f in data_files() if f.startswith("area-")]
        self.assertGreaterEqual(len(areas), 60, "measured 80 on 2026-09-13")
        for f in areas:
            self.assertTrue(allowed(f"/data/{f}"), f)
        # Finnkino's numeric ids, a chain prefix, a single-site module: three shapes.
        for f in ("area-1151.json", "area-br-tripla.json", "area-regina-helsinki.json"):
            self.assertIn(f, areas)

    def test_areas_json_is_not_the_area_family(self):
        """`/data/area-` is a hyphenated prefix and must not be relied on for areas.json."""
        allow, _, _ = rules()
        self.assertIn("/data/areas.json", allow)
        self.assertFalse(matches("/data/area-", "/data/areas.json"))

    def test_posters_are_allowed(self):
        posters = sorted((ROOT / "data" / "posters").glob("*.jpg"))
        self.assertTrue(posters)
        self.assertTrue(allowed(f"/data/posters/{posters[0].name}"))

    def test_internal_caches_and_logs_stay_blocked(self):
        for f in data_files():
            if f.startswith(INTERNAL):
                self.assertFalse(allowed(f"/data/{f}"), f)
        for name in ("tmdb.json", "tmdb-titles.json", "prices-riviera.json"):
            self.assertIn(name, data_files())
        # The logs moved under /logs/ on 2026-09-15. Asserting the old root URLs here
        # would have passed for ever while the real files became crawlable, since a
        # rule that matches nothing still refuses a path nothing serves.
        for path in ("/logs/", "/logs/run.log", "/logs/run-enrich.log",
                     "/logs/run-nexxo.log", "/logs/run-pages-local.log",
                     "/data/", "/data/unknown.json"):
            self.assertFalse(allowed(path), path)

    def test_every_committed_log_is_blocked_at_the_url_it_is_served_from(self):
        """Reads the tree rather than a list, so a log this test never heard of counts."""
        logs = sorted((_ctx.ROOT / "logs").glob("run*.log"))
        self.assertTrue(logs, "no committed run logs to check")
        for p in logs:
            self.assertFalse(allowed(f"/logs/{p.name}"), p.name)

    def test_every_data_file_is_classified(self):
        for f in data_files():
            consumed = f in CONSUMED or f.startswith(FAMILIES)
            internal = f.startswith(INTERNAL)
            self.assertTrue(consumed != internal, f"{f}: classify it")
            self.assertEqual(allowed(f"/data/{f}"), consumed, f)


class LanguageAndPagesTest(unittest.TestCase):

    def test_language_variants_and_generated_pages_are_allowed(self):
        for path in ("/?area=regina-helsinki&lang=sv", "/?area=city%3AHelsinki",
                     "/en/", "/en/theatre/kino-regina-helsinki/",
                     "/teatteri/kino-regina-helsinki/", "/kaupunki/helsinki/", "/status/"):
            self.assertTrue(allowed(path), path)

    def test_the_sitemap_declaration_is_intact(self):
        _, _, sitemaps = rules()
        self.assertEqual(sitemaps, ["https://leffavuoro.fi/sitemap.xml"])


if __name__ == "__main__":
    unittest.main()
