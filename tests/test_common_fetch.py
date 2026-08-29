"""common.fetch: retry, Retry-After, and the two ceilings.

These ran as a throwaway script when the Retry-After handling landed, which meant the
one thing that proved a cap actually fires could not be re-run. A cap verified once and
never again is a cap nobody will notice breaking.

Everything here talks to a real HTTP server on localhost rather than a mocked urlopen,
because the behaviour under test is partly urllib's: which exception a 429 raises, what
`e.headers` holds, whether a body is readable after an error. A mock would encode the
assumptions instead of checking them.
"""
import email.utils
import datetime
import http.server
import importlib
import os
import threading
import time
import unittest

import _ctx                                                # noqa: F401
import common


class Handler(http.server.BaseHTTPRequestHandler):
    """Replays a scripted list of responses per path, then repeats the last one."""
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.server.hits[self.path] = self.server.hits.get(self.path, 0) + 1
        steps = self.server.script.get(self.path) or [(200, {}, b"ok")]
        status, hdrs, body = steps.pop(0) if len(steps) > 1 else steps[0]
        self.send_response(status)
        for k, v in hdrs.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class FetchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.srv.script, cls.srv.hits = {}, {}
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.srv.script.clear()
        self.srv.hits.clear()

    def reload(self, **env):
        """Fresh module so the throttle counters start at zero, with env overrides."""
        for k in ("KINO_RETRY_AFTER_MAX", "KINO_RETRY_AFTER_BUDGET"):
            os.environ.pop(k, None)
        os.environ.update({k: str(v) for k, v in env.items()})
        # Never let a test write into the real validator cache.
        os.environ["KINO_HTTP_CACHE"] = os.path.join(
            os.environ.get("TMPDIR", "/tmp"), "kino-test-http-cache")
        return importlib.reload(common)

    # -- Retry-After is honoured -------------------------------------------------

    def test_429_waits_the_stated_interval_not_the_backoff(self):
        c = self.reload()
        self.srv.script["/a"] = [(429, {"Retry-After": "1"}, b"slow"), (200, {}, b"ok")]
        t0 = time.monotonic()
        body = c.fetch(self.url + "/a", backoff=30)
        dt = time.monotonic() - t0
        self.assertEqual(body, b"ok")
        self.assertLess(dt, 2.5, "waited the fixed backoff instead of the stated 1s")
        self.assertGreater(dt, 0.9, "did not wait at all")
        self.assertEqual(self.srv.hits["/a"], 2)
        self.assertEqual(c.throttle_stats()["asked"], 1)
        self.assertEqual(c.throttle_stats()["refused"], 0)

    def test_503_is_honoured_the_same_way(self):
        c = self.reload()
        self.srv.script["/b"] = [(503, {"Retry-After": "1"}, b"maint"), (200, {}, b"ok")]
        self.assertEqual(c.fetch(self.url + "/b", backoff=30), b"ok")
        self.assertEqual(c.throttle_stats()["asked"], 1)

    def test_http_date_form_is_parsed(self):
        c = self.reload()
        when = email.utils.format_datetime(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=3))
        self.srv.script["/c"] = [(429, {"Retry-After": when}, b"slow"), (200, {}, b"ok")]
        t0 = time.monotonic()
        self.assertEqual(c.fetch(self.url + "/c", backoff=30), b"ok")
        # HTTP-date has whole-second granularity, so "+3s" is 2.0-3.0s away once parsed.
        self.assertGreater(time.monotonic() - t0, 1.8)

    def test_a_date_already_past_waits_zero_not_a_negative(self):
        c = self.reload()
        past = email.utils.format_datetime(
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1))
        self.srv.script["/d"] = [(429, {"Retry-After": past}, b"slow"), (200, {}, b"ok")]
        t0 = time.monotonic()
        self.assertEqual(c.fetch(self.url + "/d", backoff=30), b"ok")
        self.assertLess(time.monotonic() - t0, 1.0)

    # -- the ceilings actually fire ----------------------------------------------

    def test_an_ask_past_the_ceiling_costs_one_request_and_no_sleep(self):
        c = self.reload()
        self.srv.script["/e"] = [(429, {"Retry-After": "9999"}, b"go away")]
        t0 = time.monotonic()
        with self.assertRaises(Exception) as cm:
            c.fetch(self.url + "/e", backoff=30)
        self.assertEqual(getattr(cm.exception, "code", None), 429)
        self.assertLess(time.monotonic() - t0, 1.0)
        self.assertEqual(self.srv.hits["/e"], 1, "kept asking a host that said no")
        self.assertEqual(c.throttle_stats()["refused"], 1)
        self.assertEqual(c.throttle_stats()["waited"], 0)

    def test_the_run_wide_budget_stops_the_second_request(self):
        """Two paths, not one: the budget is per process, so a single request could
        never show that it accumulates across them."""
        c = self.reload(KINO_RETRY_AFTER_BUDGET=3)
        for p in ("/f1", "/f2"):
            self.srv.script[p] = [(429, {"Retry-After": "2"}, b"slow"), (200, {}, b"ok")]
        self.assertEqual(c.fetch(self.url + "/f1", backoff=30), b"ok")
        with self.assertRaises(Exception):
            c.fetch(self.url + "/f2", backoff=30)
        self.assertEqual(self.srv.hits["/f2"], 1)
        self.assertEqual(c.throttle_stats()["waited"], 2)
        self.assertEqual(c.throttle_stats()["refused"], 1)

    def test_per_wait_ceiling_is_the_env_override(self):
        c = self.reload(KINO_RETRY_AFTER_MAX=1)
        self.srv.script["/g"] = [(429, {"Retry-After": "2"}, b"slow"), (200, {}, b"ok")]
        with self.assertRaises(Exception):
            c.fetch(self.url + "/g", backoff=30)
        self.assertEqual(self.srv.hits["/g"], 1)

    # -- nothing else changed ----------------------------------------------------

    def test_429_without_the_header_keeps_the_fixed_backoff_and_try_count(self):
        c = self.reload()
        self.srv.script["/h"] = [(429, {}, b"no header")]
        with self.assertRaises(Exception):
            c.fetch(self.url + "/h", tries=3, backoff=0)
        self.assertEqual(self.srv.hits["/h"], 3)
        self.assertEqual(c.throttle_stats()["asked"], 0)

    def test_unparseable_retry_after_falls_back_rather_than_reading_as_zero(self):
        c = self.reload()
        self.srv.script["/i"] = [(429, {"Retry-After": "soonish"}, b"junk")]
        with self.assertRaises(Exception):
            c.fetch(self.url + "/i", tries=2, backoff=0)
        self.assertEqual(self.srv.hits["/i"], 2)
        self.assertEqual(c.throttle_stats()["asked"], 0)

    def test_a_plain_500_still_takes_its_three_tries(self):
        c = self.reload()
        self.srv.script["/j"] = [(500, {}, b"boom")]
        with self.assertRaises(Exception):
            c.fetch(self.url + "/j", tries=3, backoff=0)
        self.assertEqual(self.srv.hits["/j"], 3)
        self.assertEqual(c.throttle_stats()["asked"], 0)

    def test_a_200_is_untouched(self):
        c = self.reload()
        self.srv.script["/k"] = [(200, {}, b"hello")]
        self.assertEqual(c.fetch(self.url + "/k"), b"hello")
        self.assertEqual(c.throttle_stats()["asked"], 0)


if __name__ == "__main__":
    unittest.main()
