"""The analytics privacy contract, checked against index.html rather than against intent.

`analyticsScrub` is posthog-js `before_send`. An event not keyed in PH_ALLOW is dropped;
a property not listed for it is removed, including the 43 the library attaches.

Measured on the wire 2026-09-20, posthog-js 1.434.2, with a title and query planted in the
capture call. `token` and `distinct_id` are mandatory: strip either and posthog-js builds
no request at all. `distinct_id` in cookieless mode is the constant `$posthog_cookieless`.
Full payload in docs/archive/2026-09-app.md.
"""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

import _ctx


HARNESS = pathlib.Path(__file__).resolve().parent / "analytics_harness.js"
INDEX = _ctx.ROOT / "index.html"

# The documented allowlist. A change here without a change to the privacy notice is the
# failure this pairing exists to catch.
ALLOWLIST = {
    "$pageview": ["category"],
    "area_opened": ["kind", "area"],
    "cinema_opened": ["venue"],
    "date_changed": ["offset_days"],
    "language_changed": ["lang"],
    "search_used": [],
    "ticket_opened": ["provider"],
}

# Attached by posthog-js before before_send runs, and observed stripped on the wire.
# $current_url is absent here: $pageview carries a synthetic one, asserted separately.
STRIPPED = ["$pathname", "$host", "$referrer", "$referring_domain",
            "$raw_user_agent", "$browser", "$browser_version", "$browser_language",
            "$os", "$os_version", "$device_type", "$device_id", "$screen_height",
            "$screen_width", "$viewport_height", "$viewport_width", "$timezone",
            "$timezone_offset", "$initial_person_info", "$lib", "$lib_version"]

MANDATORY = ["token", "distinct_id"]

CASES = [
    # name, event, properties in, expected properties out (None = event dropped)
    ("allowed_minimal", "cinema_opened", {"venue": "tahtikino-muhos"},
     {"venue": "tahtikino-muhos"}),
    ("strips_a_title", "cinema_opened", {"venue": "v", "title": "Carrie"}, {"venue": "v"}),
    ("strips_a_query", "search_used", {"q": "carrie", "$current_url": "http://a/?q=carrie"},
     {}),
    ("search_carries_nothing", "search_used", {"whatever": 1}, {}),
    ("area_keeps_two", "area_opened", {"kind": "city", "area": "Espoo", "name": "x"},
     {"kind": "city", "area": "Espoo"}),
    # The scrubber builds $current_url from the validated category: all four views, a
    # hostile URL replaced rather than forwarded, and unknown categories dropped.
    ("pv_home", "$pageview", {"category": "home"},
     {"category": "home", "$current_url": "https://leffavuoro.fi/app/home"}),
    ("pv_venue", "$pageview", {"category": "venue"},
     {"category": "venue", "$current_url": "https://leffavuoro.fi/app/venue"}),
    ("pv_city", "$pageview", {"category": "city"},
     {"category": "city", "$current_url": "https://leffavuoro.fi/app/city"}),
    ("pv_region", "$pageview", {"category": "region"},
     {"category": "region", "$current_url": "https://leffavuoro.fi/app/region"}),
    ("pv_hostile_url_replaced", "$pageview",
     {"category": "city", "$current_url": "https://evil.example/?q=carrie&title=Carrie",
      "$pathname": "/?area=city:Espoo&q=carrie", "$host": "evil.example",
      "$referrer": "https://evil.example/ref"},
     {"category": "city", "$current_url": "https://leffavuoro.fi/app/city"}),
    ("pv_real_location_stripped", "$pageview",
     {"category": "home", "$current_url": "https://leffavuoro.fi/?area=city:Espoo&q=x",
      "$raw_user_agent": "Mozilla/5.0", "$screen_width": 1440, "$device_type": "Desktop",
      "$timezone": "Europe/Helsinki"},
     {"category": "home", "$current_url": "https://leffavuoro.fi/app/home"}),
    ("pv_unknown_category", "$pageview", {"category": "admin"}, None),
    ("pv_missing_category", "$pageview", {}, None),
    ("pv_category_not_a_string", "$pageview", {"category": 1}, None),
    ("date_offset_only", "date_changed", {"offset_days": 3, "date": "2026-09-23"},
     {"offset_days": 3}),
    ("lang_only", "language_changed", {"lang": "sv", "$current_url": "http://a/?q=z"},
     {"lang": "sv"}),
    ("ticket_provider_only", "ticket_opened", {"provider": "finnkino", "url": "http://x/?ref=1"},
     {"provider": "finnkino"}),
    ("empty_value_dropped", "cinema_opened", {"venue": ""}, {}),
    # events that must never be sent
    ("drops_autocapture", "$autocapture", {"$el_text": "Buy"}, None),
    ("drops_exception", "$exception", {}, None),
    ("drops_identify", "$identify", {}, None),
    ("drops_unknown", "something_else", {"a": 1}, None),
]


def allowlist_entries(html):
    """The PH_ALLOW block with comment lines removed, so a comment mentioning a property
    cannot be mistaken for the property being allowed."""
    block = html[html.index("const PH_ALLOW = {"):]
    block = block[:block.index("};")]
    return "\n".join(l for l in block.splitlines() if not l.strip().startswith("//"))


def js_cases():
    return [{"name": n, "event": e, "properties": p} for n, e, p, _ in CASES]


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class ScrubTest(unittest.TestCase):
    """index.html's analyticsScrub(), extracted verbatim."""

    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], input=json.dumps(js_cases()),
                             capture_output=True, text=True, cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stdout}{out.stderr}")
        cls.r = json.loads(out.stdout)
        if "error" in cls.r:
            raise AssertionError(f"harness error: {cls.r['error']}")

    def test_every_case(self):
        for name, event, props, want in CASES:
            with self.subTest(case=name):
                got = self.r[name]
                if want is None:
                    self.assertIsNone(got, "this event must never be sent")
                else:
                    self.assertIsNotNone(got, "this event must be sent")
                    # The mandatory pair rides along and is asserted separately.
                    self.assertEqual({k: v for k, v in got.items()
                                      if k not in MANDATORY}, want)

    def test_the_library_properties_are_all_stripped(self):
        """The 43 posthog-js attaches, represented by the ones that carry a URL, a user
        agent or a screen size. $current_url is the load-bearing one: the search query
        lives in it."""
        probe = {k: "LEAK-" + k for k in STRIPPED}
        probe["venue"] = "v"
        out = self.r["_stripprobe"]
        self.assertEqual(out and {k: v for k, v in out.items() if k not in MANDATORY},
                         {"venue": "v"})
        for k in STRIPPED:
            with self.subTest(prop=k):
                self.assertNotIn(k, out or {})

    def test_the_two_mandatory_properties_survive(self):
        """Measured: with either stripped, posthog-js builds no request and the event is
        lost silently. They are the reason the scrub is an allowlist plus a fixed pair
        rather than an allowlist alone."""
        out = self.r["_mandatory"]
        self.assertIsNotNone(out)
        for k in MANDATORY:
            with self.subTest(prop=k):
                self.assertIn(k, out)

    def test_person_properties_are_removed(self):
        """$set and $set_once build a person profile. person_profiles:'never' already
        makes them no-ops; emptying them means a later config change cannot start
        building one out of whatever a call site passed."""
        self.assertEqual(self.r["_setprobe"], {"set": None, "set_once": None})


# protocol, hostname, allowed. Analytics runs on the production origin only, so a
# preview deploy or a dev server cannot reach the project's data.
ORIGINS = [
    ("prod_https", True), ("prod_http", False),
    ("localhost_http", False), ("localhost_https", False),
    ("loopback_v4", False), ("loopback_v6", False),
    ("file_url", False), ("gh_pages", False), ("gh_preview", False),
    ("www_prefix", False), ("suffix_attack", False), ("prefix_attack", False),
    ("unrelated", False), ("empty_host", False),
]


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class OriginGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], input=json.dumps(js_cases()),
                             capture_output=True, text=True, cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stdout}{out.stderr}")
        cls.r = json.loads(out.stdout)
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_only_the_production_https_origin_is_allowed(self):
        got = self.r["_origins"]
        for name, want in ORIGINS:
            with self.subTest(origin=name):
                self.assertEqual(got[name], want)

    def test_the_bundle_is_not_fetched_off_production(self):
        """The guard runs before the script element is created, so a rejected origin
        makes no request at all, not even for the bundle."""
        init = self.html[self.html.index("function phInit(){"):]
        init = init[:init.index("document.head.appendChild")]
        self.assertIn("if(phDNT() || !phHere()) return;", init)
        self.assertLess(init.index("phHere()"), init.index("createElement"))

    def test_nothing_is_queued_or_captured_off_production(self):
        """Both entry points are gated, so a rejected origin cannot fill the queue that
        a later init would flush."""
        for fn in ("function track(name, props){", "function trackTicket(provider){"):
            with self.subTest(fn=fn):
                body = self.html[self.html.index(fn):]
                body = body[:body.index("\n  }")]
                self.assertIn("phDNT() || !phHere()", body)
                self.assertLess(body.index("phHere()"), body.index("phQueue.push"))

    def test_the_hostname_match_is_exact(self):
        block = self.html[self.html.index("function phAllowedOrigin"):]
        block = block[:block.index("\n  }")]
        self.assertIn("hostname === 'leffavuoro.fi'", block)
        for loose in ("endsWith", "includes", "indexOf", "startsWith", "RegExp", "match("):
            with self.subTest(op=loose):
                self.assertNotIn(loose, block)

    def test_do_not_track_is_still_checked(self):
        self.assertIn("phDNT()", self.html)
        block = self.html[self.html.index("const phDNT"):]
        block = block[:block.index("function phInit")]
        for sig in ("navigator.doNotTrack", "globalPrivacyControl"):
            with self.subTest(signal=sig):
                self.assertIn(sig, block)


class SyntheticUrlTest(unittest.TestCase):
    """$pageview is the one event carrying a URL, and it is built from the category."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_the_scrubber_builds_the_url_and_the_caller_cannot(self):
        """$current_url is not in the allowlist, so it cannot be forwarded; it is
        constructed from the validated category instead."""
        self.assertNotIn("$current_url", allowlist_entries(self.html))
        self.assertIn("out.$current_url = PH_APP_BASE + out.category;", self.html)
        self.assertIn("if(PH_CATEGORIES.indexOf(out.category) === -1) return null;",
                      self.html)

    def test_the_call_site_passes_only_the_category(self):
        self.assertIn("track('$pageview', { category: phCategory() });", self.html)

    def test_the_four_categories_are_the_only_ones(self):
        self.assertIn("const PH_CATEGORIES = ['home', 'venue', 'city', 'region'];",
                      self.html)
        self.assertIn("const PH_APP_BASE = 'https://leffavuoro.fi/app/';", self.html)

    def test_no_real_location_is_read_for_analytics(self):
        block = self.html[self.html.index("/* ---------- analytics ---------- */"):]
        block = block[:block.index("const FI_TZ")]
        for bad in ("location.href", "location.search", "location.pathname",
                    "document.referrer", "document.URL"):
            with self.subTest(source=bad):
                self.assertNotIn(bad, block)

    def test_only_pageview_may_carry_a_url(self):
        self.assertNotIn("$current_url", allowlist_entries(self.html),
                         "no event may forward a URL; $pageview's is constructed")


class VersionPinTest(unittest.TestCase):
    """The bundle is pinned, so a PostHog default change cannot move the measured
    contract underneath it."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_the_version_is_pinned_and_used_in_the_src(self):
        self.assertIn("const PH_VERSION = '1.434.2';", self.html)
        self.assertIn("'/static/' + PH_VERSION + '/array.js'", self.html)

    def test_the_unpinned_path_is_not_used(self):
        self.assertNotIn("'/static/array.js'", self.html)

    def test_the_bundle_is_pinned_by_its_bytes_and_not_only_its_url(self):
        """The version pins the URL. Without integrity, whoever can change what that URL
        returns has script execution here, and analyticsScrub cannot help: before_send
        belongs to the library being replaced. Measured from the 1.434.2 bundle on
        2026-09-22; re-measure in the same commit as any PH_VERSION bump."""
        self.assertIn("sc.integrity = 'sha384-BmbtQMM1P8wo232drqi6RUQiNd0Z"
                      "Fk56bltD3yk2/94kez4jFURztoW+DlYzT2Ah';", self.html)
        # SRI on a cross-origin script is only enforced when the fetch is a CORS one.
        self.assertIn("sc.crossOrigin = 'anonymous';", self.html)
        i, c = self.html.index("sc.integrity ="), self.html.index("sc.crossOrigin =")
        self.assertLess(abs(self.html.count("\n", min(i, c), max(i, c))), 3,
                        "the two sit together on the one script element")


class ConfigTest(unittest.TestCase):
    """The init options, read out of index.html."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")
        i = cls.html.index("posthog.init(PH_KEY")
        cls.cfg = cls.html[i:cls.html.index("});", i)]

    def test_the_privacy_options(self):
        for frag in ("cookieless_mode: 'always'",
                     "person_profiles: 'never'",
                     "persistence: 'memory'",
                     "disable_persistence: true",
                     "respect_dnt: true",
                     "autocapture: false",
                     "capture_pageview: false",
                     "capture_pageleave: false",
                     "capture_dead_clicks: false",
                     "capture_heatmaps: false",
                     "capture_performance: false",
                     "capture_exceptions: false",
                     "disable_session_recording: true",
                     "disable_surveys: true",
                     "enable_recording_console_log: false",
                     "advanced_disable_decide: true",
                     "advanced_disable_feature_flags: true",
                     "before_send: analyticsScrub"):
            with self.subTest(option=frag):
                self.assertIn(frag, self.cfg)

    def test_the_endpoint_is_the_eu_cloud(self):
        self.assertIn("https://eu.i.posthog.com", self.html)
        self.assertNotIn("us.i.posthog.com", self.html)
        # PostHog's own snippet derives the bundle host from the API host this way.
        self.assertIn(".replace('.i.posthog.com', '-assets.i.posthog.com')", self.html)

    def test_do_not_track_stops_the_request_before_it_is_made(self):
        """respect_dnt is the library's answer; this one is ours, and it means a reader
        with DNT set causes no request to posthog at all, not even the bundle."""
        block = self.html[self.html.index("const phDNT"):]
        block = block[:block.index("function phInit")]
        for sig in ("navigator.doNotTrack", "window.doNotTrack",
                    "navigator.msDoNotTrack", "globalPrivacyControl"):
            with self.subTest(signal=sig):
                self.assertIn(sig, block)
        init = self.html[self.html.index("function phInit()"):]
        self.assertIn("if(phDNT() || !phHere()) return;",
                      init[:init.index("document.head.appendChild")])

    def test_identify_and_the_other_person_calls_are_never_used(self):
        for call in ("posthog.identify(", ".identify(", "posthog.alias(",
                     "setPersonProperties", "createPersonProfile", "opt_in_capturing"):
            with self.subTest(call=call):
                self.assertNotIn(call, self.html)

    def test_no_browser_storage_is_used_for_analytics(self):
        """The app's own two keys stay; nothing analytics-related may be added."""
        keys = set(re.findall(r"(?:localStorage|sessionStorage)\.(?:get|set|remove)Item\('([^']+)'",
                              self.html))
        self.assertTrue(keys <= {"kino-prefs", "kino-theme"}, keys)

    def test_the_allowlist_matches_the_documented_one(self):
        block = allowlist_entries(self.html)
        for event, props in ALLOWLIST.items():
            with self.subTest(event=event):
                self.assertRegex(block, rf"{re.escape(event)}:\s*\[")
        found = set(re.findall(r"^\s{4}(\$?\w+):\s*\[", block, re.M))
        self.assertEqual(found, set(ALLOWLIST), "the allowlist changed; the notice must too")


class DedupTest(unittest.TestCase):
    def test_track_dedupes_on_the_property_signature(self):
        html = INDEX.read_text(encoding="utf-8")
        block = html[html.index("function track(name, props)"):]
        block = block[:block.index("\n  }")]
        self.assertIn("phSeen[name] === sig", block)
        self.assertIn("return;", block)

    def test_the_page_view_fires_once_a_load(self):
        html = INDEX.read_text(encoding="utf-8")
        block = html[html.index("function phPageView()"):]
        block = block[:block.index("\n  }")]
        self.assertIn("if(phBooted) return;", block)
        self.assertIn("phBooted = true;", block)


if __name__ == "__main__":
    unittest.main()
