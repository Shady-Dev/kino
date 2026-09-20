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
    "page_view": ["category"],
    "area_opened": ["kind", "area"],
    "cinema_opened": ["venue"],
    "date_changed": ["offset_days"],
    "language_changed": ["lang"],
    "search_used": [],
    "ticket_opened": ["provider"],
}

# Attached by posthog-js before before_send runs, and observed stripped on the wire.
STRIPPED = ["$current_url", "$pathname", "$host", "$referrer", "$referring_domain",
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
    ("page_view_category", "page_view", {"category": "venue", "$pathname": "/x"},
     {"category": "venue"}),
    ("date_offset_only", "date_changed", {"offset_days": 3, "date": "2026-09-23"},
     {"offset_days": 3}),
    ("lang_only", "language_changed", {"lang": "sv", "$current_url": "http://a/?q=z"},
     {"lang": "sv"}),
    ("ticket_provider_only", "ticket_opened", {"provider": "finnkino", "url": "http://x/?ref=1"},
     {"provider": "finnkino"}),
    ("empty_value_dropped", "cinema_opened", {"venue": ""}, {}),
    # events that must never be sent
    ("drops_pageview", "$pageview", {}, None),
    ("drops_autocapture", "$autocapture", {"$el_text": "Buy"}, None),
    ("drops_exception", "$exception", {}, None),
    ("drops_identify", "$identify", {}, None),
    ("drops_unknown", "something_else", {"a": 1}, None),
]


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
        self.assertIn("if(phDNT()) return;", init[:init.index("document.head.appendChild")])

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
        block = self.html[self.html.index("const PH_ALLOW = {"):]
        block = block[:block.index("};")]
        for event, props in ALLOWLIST.items():
            with self.subTest(event=event):
                self.assertRegex(block, rf"{re.escape(event)}:\s*\[")
        found = set(re.findall(r"^\s{4}(\w+):\s*\[", block, re.M))
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
