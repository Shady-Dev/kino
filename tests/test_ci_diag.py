"""ci_diag.py: the failure diagnostics the cloud workflow uploads as a short-lived artifact.

Checks that only non-zero logs are reported, that the probe records status, headers and
body length and never the body, that the expiry date disarms it, and that biorex.yml wires
the step before the commit with a pinned upload action and a two-day retention.
"""
import contextlib
import datetime as dt
import http.server
import io
import os
import pathlib
import tempfile
import threading
import time
import unittest

import _ctx
import ci_diag

ROOT = _ctx.ROOT
WORKFLOW = ROOT / ".github" / "workflows" / "biorex.yml"
BODY = b"<html>SECRET-IN-BODY</html>"


class Handler(http.server.BaseHTTPRequestHandler):
    server_version, sys_version = "openresty/1.31.1.1", ""

    def do_GET(self):
        if self.path.startswith("/slow"):
            time.sleep(1.5)
        self.send_response(403)
        self.send_header("X-Secret-Header", "should-not-appear")
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        self.wfile.write(BODY)

    def log_message(self, *a):
        pass


def write_logs(d, **logs):
    for name, text in logs.items():
        (pathlib.Path(d) / f"run-{name}.log").write_text(text, encoding="utf-8")


class Diag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_only_nonzero_logs_and_only_their_http_and_failed_lines(self):
        with tempfile.TemporaryDirectory() as d:
            write_logs(d, ok="[x] fine\nexit=0\n",
                       bad="[http] 403 from kinoset.fi, gave up after 3 attempt(s) -- Server: x\n"
                           "[kinoset] locationid 1 FAILED: HTTP Error 403: Forbidden\n"
                           "[run] nexxo: 5 venues\nexit=1\n",
                       recovered="FAILED once\nexit=1\nexit=0\n")
            got = ci_diag.failed_logs(sorted(pathlib.Path(d).glob("run-*.log")))
        self.assertEqual(list(got), ["bad"])
        self.assertEqual(len(got["bad"]), 2)
        self.assertNotIn("[run] nexxo: 5 venues", got["bad"])

    def test_hosts_come_from_http_lines_and_module_sites(self):
        hosts = ci_diag.hosts_for("nexxo", ["[http] 403 from example.invalid, gave up"])
        self.assertIn("example.invalid", hosts)
        self.assertIn("kinohirvi.fi", hosts)
        self.assertEqual(ci_diag.hosts_for("no_such_module", []), [])

    def test_probe_keeps_status_headers_and_length_never_the_body(self):
        p = ci_diag.probe(self.url + "/", timeout=5)
        self.assertEqual(p["status"], 403)
        self.assertEqual(p["body_len"], len(BODY))
        self.assertEqual(p["headers"]["Server"], "openresty/1.31.1.1")
        self.assertNotIn("X-Secret-Header", p["headers"])
        self.assertIn("127.0.0.1", p["dns"])
        self.assertNotIn("SECRET", repr(p))

    def test_probe_reports_a_timeout_as_an_error(self):
        p = ci_diag.probe(self.url + "/slow", timeout=0.3)
        self.assertIsNone(p["status"])
        self.assertIn("timed out", p["error"])

    def run_main(self, d, until, **logs):
        write_logs(d, **logs)
        out = pathlib.Path(d) / "out"
        gh = pathlib.Path(d) / "gh_output"
        gh.write_text("")
        old = os.environ.get("GITHUB_OUTPUT")
        os.environ["GITHUB_OUTPUT"] = str(gh)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = ci_diag.main(["--out", str(out), "--until", until, "--offline",
                                     "--logs", str(pathlib.Path(d) / "run-*.log"),
                                     "--probe", self.url + "/{host}"])
        finally:
            if old is None:
                del os.environ["GITHUB_OUTPUT"]
            else:
                os.environ["GITHUB_OUTPUT"] = old
        report = out / "diag.txt"
        return code, report.read_text(encoding="utf-8") if report.exists() else None, gh.read_text()

    def test_main_writes_report_and_flags_the_upload(self):
        with tempfile.TemporaryDirectory() as d:
            code, text, gh = self.run_main(d, "2999-01-01", bad=(
                "[http] 403 from example.invalid, gave up after 3 attempt(s) -- Server: x\n"
                "exit=1\n"))
        self.assertEqual(code, 0)
        self.assertIn("example.invalid", text)
        self.assertIn("403 in", text)
        self.assertIn("Server: openresty", text)
        self.assertNotIn("SECRET", text)
        self.assertNotIn("should-not-appear", text)
        self.assertEqual(gh, "report=true\n")

    def test_main_without_a_failure_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            code, text, gh = self.run_main(d, "2999-01-01", ok="exit=0\n")
        self.assertEqual((code, text, gh), (0, None, ""))

    def test_main_after_the_until_date_does_nothing(self):
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        with tempfile.TemporaryDirectory() as d:
            code, text, gh = self.run_main(d, yesterday, bad="[http] 403 from a.b\nexit=1\n")
        self.assertEqual((code, text, gh), (0, None, ""))


class Workflow(unittest.TestCase):
    def test_step_runs_after_the_fetch_and_before_the_commit(self):
        wf = WORKFLOW.read_text(encoding="utf-8")
        fetch = wf.index("name: Fetch cloud providers\n")
        diag = wf.index("scripts/ci_diag.py")
        commit = wf.index("name: Commit data and logs")
        self.assertLess(fetch, diag)
        self.assertLess(diag, commit)
        self.assertRegex(wf, r'ci_diag\.py --out "\$RUNNER_TEMP/diag" --until \d{4}-\d{2}-\d{2}')

    def test_upload_is_pinned_gated_and_short_lived(self):
        wf = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", wf)
        self.assertIn("if: steps.diag.outputs.report == 'true'", wf)
        self.assertIn("retention-days: 2", wf)
        self.assertNotIn("diag", wf[wf.index("git add data"):].split("\n")[0])


if __name__ == "__main__":
    unittest.main()
