"""A missing or refused TMDB token turns the run red.

`main()` returned 0 with no token and after any number of 401s, so `run-enrich.log` read
`exit=0` and new films published without rating, poster or genres for as long as the
secret stayed rotated (review 2026-11-22, M8). Which exception a 401 raises is urllib's,
so TMDB is a real local server here rather than a stub.
"""
import contextlib
import http.server
import io
import json
import os
import pathlib
import tempfile
import threading
import types
import unittest
from unittest import mock

import _ctx                                                # noqa: F401
import enrich_tmdb

TOKEN = "test-token-not-real"


class Server:
    """Answers each path with the status `answer(path)` returns."""

    def __init__(self, test, answer):
        self.paths = []
        paths = self.paths

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                code = answer(self.path)
                body = (json.dumps({"genres": [{"id": 18, "name": "Draama"}]}) if code == 200
                        else json.dumps({"status_code": 7, "status_message": "Invalid API key"}))
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *a):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        test.addCleanup(self.srv.server_close)
        test.addCleanup(self.srv.shutdown)
        host = f"http://127.0.0.1:{self.srv.server_port}"
        real = enrich_tmdb.get

        def get(url, headers, timeout=25):
            return real(url.replace("https://api.themoviedb.org", host), headers, timeout=5)
        patcher = mock.patch.object(enrich_tmdb, "get", get)
        patcher.start()
        test.addCleanup(patcher.stop)


class TokenTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)
        for attr, value in (("DATA", self.dir), ("CACHE", self.dir / "tmdb-titles.json"),
                            ("GENRES", self.dir / "tmdb-genres.json"),
                            ("EXTRA", self.dir / "films-extra.json")):
            patcher = mock.patch.object(enrich_tmdb, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(enrich_tmdb, "time", types.SimpleNamespace(sleep=lambda *_: None))
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.dir / "area-zz.json").write_text(json.dumps({
            "generated": "2026-11-22", "dates": [], "horizon": "",
            "shows": [{"title": "Yksi", "start": "2026-11-23T18:00:00+02:00"},
                      {"title": "Kaksi", "start": "2026-11-23T20:00:00+02:00"}]}),
            encoding="utf-8")

    def main(self, **env):
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            for k in ("TMDB_TOKEN", "GITHUB_ACTIONS"):
                if k not in env:
                    os.environ.pop(k, None)
            code = enrich_tmdb.main()
        return code, out.getvalue()

    def test_no_token_on_the_runner_fails(self):
        code, out = self.main(GITHUB_ACTIONS="true")
        self.assertEqual(code, 1)
        self.assertIn("secret is missing", out)

    def test_no_token_on_an_ordinary_connection_still_skips(self):
        code, out = self.main()
        self.assertEqual(code, 0)
        self.assertIn("skipping", out)

    def test_a_token_refused_on_every_genre_list_fails_before_any_film_request(self):
        for status in (401, 403):
            with self.subTest(status=status):
                server = Server(self, lambda path: status)
                code, out = self.main(TMDB_TOKEN=TOKEN)
                self.assertEqual(code, 1)
                self.assertEqual(len(server.paths), 3)
                self.assertTrue(all("/genre/movie/list" in p for p in server.paths))
                self.assertNotIn(TOKEN, out)

    def test_one_refused_genre_list_is_not_a_refused_token(self):
        server = Server(self, lambda path: 401 if "language=fi-FI" in path and "genre" in path
                        else 200 if "genre" in path else 404)
        code, out = self.main(TMDB_TOKEN=TOKEN)
        self.assertEqual(code, 0, out)
        self.assertGreater(len(server.paths), 3, "the film requests went ahead")


if __name__ == "__main__":
    unittest.main()
