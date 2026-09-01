"""common.fetch: retry, Retry-After, the two ceilings, and what a refusal says.

These ran as a throwaway script when the Retry-After handling landed, which meant the
one thing that proved a cap actually fires could not be re-run. A cap verified once and
never again is a cap nobody will notice breaking.

Everything here talks to a real HTTP server on localhost rather than a mocked urlopen,
because the behaviour under test is partly urllib's: which exception a 429 raises, what
`e.headers` holds, what survives closing the response. A mock would encode the
assumptions instead of checking them.
"""
import contextlib
import email.utils
import datetime
import gc
import http.server
import importlib
import io
import os
import threading
import time
import unittest
import urllib.error
import warnings

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
            if k != "X-No-Length":
                self.send_header(k, v)
        if "X-No-Length" in hdrs:
            # No Content-Length at all: the client reads until the connection
            # closes, which is the response shape the streaming cap exists for.
            self.send_header("Connection", "close")
        else:
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def version_string(self):
        """The Server header. BaseHTTPRequestHandler sends one on every response, and
        `send_header` would only append a second that `headers.get` never returns, so a
        test that needs `Server: cloudflare` has to come through here."""
        return getattr(self.server, "banner", "TestHTTP")

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
        # shutdown() stops serve_forever; the listening socket is still
        # open until this. test_run_pool.py has always done both.
        cls.srv.server_close()

    def setUp(self):
        self.srv.script.clear()
        self.srv.hits.clear()
        self.srv.banner = "TestHTTP"
        # Every test here that exercises a failure path now makes fetch print one
        # diagnostic line. Swallowed by default so a run stays readable; `refusals`
        # nests its own redirect inside this one for the tests that read them.
        sink = contextlib.redirect_stdout(io.StringIO())
        sink.__enter__()
        self.addCleanup(sink.__exit__, None, None, None)

    def refusals(self, fn):
        """Run fn with stdout captured. -> (its return value, the [http] lines)."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            got = fn()
        self.captured = buf.getvalue()
        return got, [l for l in self.captured.splitlines() if l.startswith("[http]")]

    def reload(self, **env):
        """Fresh module so the throttle counters start at zero, with env overrides."""
        for k in ("KINO_RETRY_AFTER_MAX", "KINO_RETRY_AFTER_BUDGET", "KINO_MAX_BODY"):
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

    # -- the refused response does not sit on its socket -------------------------------

    def test_a_refused_response_comes_back_closed(self):
        """An HTTPError *is* the response. Holding one without closing it keeps the
        socket until the collector happens to run -- 24 ResourceWarnings in a suite run,
        and on a run against a host refusing everything, that many sockets waiting on a
        collection nobody scheduled."""
        c = self.reload()
        self.srv.script["/k1"] = [(429, {"Retry-After": "9999"}, b"go away")]
        with self.assertRaises(urllib.error.HTTPError) as cm:
            c.fetch(self.url + "/k1", backoff=30)
        self.assertTrue(cm.exception.closed)

    def test_the_last_of_several_tries_comes_back_closed_too(self):
        """Three attempts, so three responses. The one that reaches the caller is the
        last, and the two before it are dropped inside the loop -- a fix that only
        closed the raised one would leave those two, which is most of them."""
        c = self.reload()
        self.srv.script["/k2"] = [(500, {}, b"boom")]
        with self.assertRaises(urllib.error.HTTPError) as cm:
            c.fetch(self.url + "/k2", tries=3, backoff=0)
        self.assertEqual(self.srv.hits["/k2"], 3)
        self.assertTrue(cm.exception.closed)

    def test_no_resource_warning_survives_the_retry_loop(self):
        """Stated as the symptom rather than the mechanism, because `closed` is only
        evidence and this is the thing that was actually wrong. gc.collect() forces the
        collection the warning would otherwise appear at some arbitrary later point."""
        c = self.reload()
        self.srv.script["/k3"] = [(403, {}, b"nope")]
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with self.assertRaises(urllib.error.HTTPError):
                c.fetch(self.url + "/k3", tries=3, backoff=0)
            gc.collect()
        leaked = [w for w in caught if issubclass(w.category, ResourceWarning)]
        self.assertEqual(leaked, [], f"{len(leaked)} response(s) left open")

    def test_the_diagnostic_headers_survive_the_close(self):
        """What the close is allowed to cost. `_log_refusal` reads Server and CF-Ray off
        the exception after the fact, so closing the body must not take the headers with
        it -- that line is how a Cloudflare block was told apart from a real 403."""
        c = self.reload()
        self.srv.script["/k4"] = [(403, {"Server": "cloudflare", "CF-Ray": "abc-HEL"},
                                   b"blocked")]
        with self.assertRaises(urllib.error.HTTPError) as cm:
            c.fetch(self.url + "/k4", tries=1, backoff=0)
        e = cm.exception
        self.assertTrue(e.closed)
        self.assertEqual(e.code, 403)
        self.assertEqual(e.headers.get("CF-Ray"), "abc-HEL")
        # The real consumer rather than the header dict: _server_hint is what builds the
        # line, so asserting on it covers the close and the reader together. `Server` is
        # not asserted -- BaseHTTPRequestHandler writes its own banner over the scripted
        # one, which is the harness talking and not the code under test.
        self.assertIn("CF-Ray: abc-HEL", common._server_hint(e))

    def test_a_200_is_untouched(self):
        c = self.reload()
        self.srv.script["/k"] = [(200, {}, b"hello")]
        self.assertEqual(c.fetch(self.url + "/k"), b"hello")
        self.assertEqual(c.throttle_stats()["asked"], 0)

    # -- the body cap ------------------------------------------------------------

    def test_a_declared_oversize_is_refused_from_the_header(self):
        c = self.reload()
        self.srv.script["/big1"] = [(200, {}, b"x" * 2000)]
        with self.assertRaises(c.BodyTooLarge) as cm:
            c.fetch(self.url + "/big1", max_bytes=1000)
        self.assertIn("Content-Length", str(cm.exception))
        self.assertEqual(self.srv.hits["/big1"], 1, "an oversize answer was re-asked")

    def test_an_undeclared_oversize_is_cut_off_while_reading(self):
        """Content-Length is only the origin's claim; a response without one has to be
        stopped by the read loop itself."""
        c = self.reload()
        self.srv.script["/big2"] = [(200, {"X-No-Length": "1"}, b"x" * 200_000)]
        with self.assertRaises(c.BodyTooLarge) as cm:
            c.fetch(self.url + "/big2", max_bytes=1000)
        self.assertNotIn("Content-Length", str(cm.exception))
        self.assertEqual(self.srv.hits["/big2"], 1)

    def test_a_body_at_the_cap_passes(self):
        c = self.reload()
        self.srv.script["/fit"] = [(200, {}, b"x" * 1000)]
        self.assertEqual(len(c.fetch(self.url + "/fit", max_bytes=1000)), 1000)

    def test_the_default_cap_comes_from_the_environment(self):
        c = self.reload(KINO_MAX_BODY=500)
        self.srv.script["/env"] = [(200, {}, b"x" * 501)]
        with self.assertRaises(c.BodyTooLarge):
            c.fetch(self.url + "/env")

    # -- a refusal says which layer refused -------------------------------------

    def test_a_blocked_venue_is_identified_and_a_working_one_stays_silent(self):
        """The Kinoset shape, with the loop in it: one venue refused, one served. The
        committed log said `HTTP Error 403: Forbidden` three times and nothing else,
        which is the same line for an edge block and for an origin throttle."""
        c = self.reload()
        self.srv.banner = "cloudflare"
        self.srv.script["/v1"] = [(403, {"CF-Ray": "8f2a1b3c4d5e6f70-HEL"}, b"blocked")]
        self.srv.script["/v2"] = [(200, {}, b"ok")]

        def loop():
            out = {}
            for venue in ("v1", "v2"):
                try:
                    out[venue] = c.fetch(f"{self.url}/{venue}", tries=2, backoff=0)
                except urllib.error.HTTPError as e:
                    out[venue] = e.code
            return out

        got, lines = self.refusals(loop)
        self.assertEqual(got, {"v1": 403, "v2": b"ok"})
        self.assertEqual(len(lines), 1, f"one line for one refusal, got: {lines}")
        self.assertIn("403", lines[0])
        self.assertIn("Server: cloudflare", lines[0])
        self.assertIn("CF-Ray: 8f2a1b3c4d5e6f70-HEL", lines[0])
        self.assertIn("2 attempt(s)", lines[0])

    def test_an_origin_refusal_does_not_read_as_an_edge_one(self):
        """The distinction the line exists for: no ray means the application said no,
        which clears on its own, rather than an address being blocked, which does not."""
        c = self.reload()
        self.srv.banner = "Apache/2.4.62"
        self.srv.script["/o"] = [(403, {}, b"nope")]

        def call():
            with self.assertRaises(urllib.error.HTTPError):
                c.fetch(self.url + "/o", tries=1, backoff=0)
        _, lines = self.refusals(call)
        self.assertEqual(len(lines), 1)
        self.assertIn("Server: Apache/2.4.62", lines[0])
        self.assertNotIn("CF-Ray", lines[0])

    def test_one_line_per_host_however_many_requests_it_refuses(self):
        """mirror_posters calls fetch once per poster and has had 185 failures against
        one host in a run. A line each would bury the summary the log is read for."""
        c = self.reload()
        self.srv.banner = "cloudflare"
        for n in (1, 2, 3):
            self.srv.script[f"/p{n}"] = [(403, {"CF-Ray": f"ray-{n}"}, b"blocked")]

        def loop():
            for n in (1, 2, 3):
                with self.assertRaises(urllib.error.HTTPError):
                    c.fetch(f"{self.url}/p{n}", tries=1, backoff=0)

        _, lines = self.refusals(loop)
        self.assertEqual(len(lines), 1, f"deduplication is gone: {lines}")
        self.assertIn("ray-1", lines[0])

    def test_the_body_of_a_refusal_is_never_printed(self):
        """run-*.log is committed to a public repo, and a third party's error page carries
        whatever they ship to visitors. That rule cost a history rewrite once already."""
        c = self.reload()
        self.srv.banner = "cloudflare"
        secret = b"<!-- apiKey: AIzaSyTESTONLYNOTREAL -->"
        self.srv.script["/b"] = [(403, {"CF-Ray": "r1"}, secret)]

        def call():
            with self.assertRaises(urllib.error.HTTPError):
                c.fetch(self.url + "/b", tries=1, backoff=0)

        self.refusals(call)
        self.assertNotIn("AIzaSy", self.captured)
        self.assertNotIn("apiKey", self.captured)

    def test_a_response_with_none_of_the_headers_prints_nothing(self):
        """No empty line, and no line saying only the code -- that is what the adapter's
        own FAILED line already says."""
        c = self.reload()
        self.srv.banner = ""
        self.srv.script["/q"] = [(403, {}, b"nope")]

        def call():
            with self.assertRaises(urllib.error.HTTPError):
                c.fetch(self.url + "/q", tries=1, backoff=0)

        _, lines = self.refusals(call)
        self.assertEqual(lines, [])

    def test_a_refused_retry_after_says_what_was_asked_for(self):
        """The ceiling path raises without retrying, and that exit needs the line too:
        `[run] throttled:` counts them but never names the host."""
        c = self.reload()
        self.srv.banner = "cloudflare"
        self.srv.script["/r"] = [(429, {"Retry-After": "9999"}, b"slow")]

        def call():
            with self.assertRaises(urllib.error.HTTPError):
                c.fetch(self.url + "/r", tries=3, backoff=0)

        _, lines = self.refusals(call)
        self.assertEqual(len(lines), 1)
        self.assertIn("Retry-After: 9999", lines[0])
        self.assertIn("1 attempt(s)", lines[0])
        self.assertEqual(self.srv.hits["/r"], 1)


if __name__ == "__main__":
    unittest.main()
