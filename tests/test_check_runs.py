"""check_runs.py: the local half's only failure signal.

A failed cloud provider turns its Actions run red. The local half runs outside this repo,
writes `exit=1` into a log, pushes it and carries on. Both halves commit their logs, so
reading them is the signal. The deciding cases: a log with no exit line, and a stale log
nobody overwrites any more.
"""
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import check_runs


class CheckRunsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)

    def log(self, name, body):
        (self.dir / name).write_text(body, encoding="utf-8")

    def run_check(self):
        return check_runs.main(["--dir", str(self.dir)])

    def test_all_clean_passes(self):
        self.log("run.log", "[run] fine\nexit=0\n")
        self.log("run-biorex.log", "[run] biorex: 12 venues\nexit=0\n")
        self.assertEqual(self.run_check(), 0)

    def test_a_non_zero_exit_fails(self):
        self.log("run.log", "exit=0\n")
        self.log("run-vista.log", "[savonkinot] FAILED: HTTP Error 404: Not Found\nexit=1\n")
        self.assertEqual(self.run_check(), 1)

    def test_a_log_with_no_exit_line_fails(self):
        """Every writer appends one, so its absence means the run died before it could
        or the file was truncated. Treating that as clean is how a half-written log
        passes for a healthy one."""
        self.log("run.log", "[run] started and then nothing\n")
        self.assertEqual(self.run_check(), 1)

    def test_no_logs_at_all_fails(self):
        self.assertEqual(self.run_check(), 1)

    def test_a_stale_log_still_counts(self):
        """run-vista.log sat at exit=1 for hours because its module was retired and
        nothing overwrote it. Age is not a reason to stop reporting."""
        self.log("run.log", "exit=0\n")
        self.log("run-vista.log", "[savonkinot] FAILED: gone\nexit=1\n")
        self.assertEqual(self.run_check(), 1)

    def test_the_cause_line_is_reported_not_just_the_code(self):
        self.log("run-etiketti.log",
                 "[joutsankino] FAILED: HTTP Error 403: Forbidden\n"
                 "[http] 403 from kino.joutsa.fi, gave up after 3 attempt(s)\nexit=1\n")
        ok, code, causes = check_runs.check(self.dir / "run-etiketti.log")
        self.assertFalse(ok)
        self.assertEqual(code, 1)
        self.assertTrue(any("kino.joutsa.fi" in c for c in causes), causes)

    def test_a_clean_log_with_trailing_output_is_still_clean(self):
        """A checker that reads only the final line calls this unreadable and reports a
        healthy run as broken -- which trains people to ignore it, the same failure the
        deleted fetch.yml caused by being permanently red."""
        self.log("run.log", "exit=0\n[run] a note printed after the exit line\n")
        self.assertEqual(self.run_check(), 0)

    def test_the_last_exit_line_wins(self):
        """Each writer appends its own when it finishes, so a later one supersedes an
        earlier one; taking the first would report a run that recovered as failed."""
        self.log("run.log", "exit=1\n[run] second stage\nexit=0\n")
        self.assertEqual(self.run_check(), 0)


if __name__ == "__main__":
    unittest.main()
