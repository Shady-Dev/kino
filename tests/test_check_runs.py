"""check_runs.py: the local half's only failure signal.

A failed cloud provider turns its Actions run red. The local half runs outside this repo,
writes `exit=1` into a log, pushes it and carries on. Both halves commit their logs, so
reading them is the signal. The deciding cases: a log with no exit line, and a stale log
nobody overwrites any more.
"""
import contextlib
import io
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import check_runs
import common


class CheckRunsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = pathlib.Path(self.tmp.name)

    def log(self, name, body):
        (self.dir / name).write_text(body, encoding="utf-8")

    def run_check(self):
        return check_runs.main(["--dir", str(self.dir)])

    def test_the_default_dir_finds_the_repos_own_logs(self):
        """Every other test passes --dir, so none of them would notice the logs moving.

        This is the one that goes red on a half-done migration: it asserts the default
        resolves to a directory that actually holds the committed logs, and it does not
        care what the working directory is.
        """
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            check_runs.main([])
        self.assertNotIn("nothing has been committed yet", err.getvalue())
        self.assertRegex(out.getvalue(), r"\[check\] \d+ run log\(s\)")

    def test_a_log_left_at_the_repo_root_fails(self):
        """A writer that was not migrated keeps publishing where nothing reads.

        Without this the check would read the moved copies, find them fine and report
        green while the live half wrote somewhere else entirely.
        """
        self.assertEqual(check_runs.strays(self.dir), [])
        (self.dir / "run-stray.log").write_text("exit=0\n", encoding="utf-8")
        self.assertEqual([p.name for p in check_runs.strays(self.dir)], ["run-stray.log"])

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


class FailingSiteHistoryTest(unittest.TestCase):
    """Every failing site is named and marked new or carried, from git history alone.

    Nineteen of twenty cloud runs up to 2026-09-25 were red from Kinotour's HTTP 500, so a
    second site failing read exactly like the first (audit, cloud verdict). The run stays
    red; the report says which failure is which. No state file: the committed logs are the
    record, read with `git log` and `git show`.
    """

    OK = "[x] X: 3 showtimes\nexit=0\n"

    @staticmethod
    def failed(*sites):
        return "".join(f"[{s}] FAILED: HTTP Error 500\n" for s in sites) + "exit=1\n"

    def setUp(self):
        import subprocess
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = pathlib.Path(self.tmp.name)
        self.logs = self.repo / "logs"
        self.logs.mkdir()
        self.git = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], check=True,
                                             capture_output=True, text=True)
        self.git("init", "-q")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t" + "@" + "example.invalid")
        self.day = 0

    def commit(self, body, name="run-mod.log"):
        import os
        self.day += 1
        (self.logs / name).write_text(body, encoding="utf-8")
        self.git("add", "-A")
        when = f"2026-09-{10 + self.day:02d}T12:00:00+00:00"
        import subprocess
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "run"], check=True,
                       env=dict(os.environ, GIT_COMMITTER_DATE=when, GIT_AUTHOR_DATE=when))

    def report(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_runs.main(["--dir", str(self.logs)])
        return code, err.getvalue()

    def test_a_site_failing_for_the_first_time_is_new(self):
        self.commit(self.OK)
        self.commit(self.failed("alpha"))
        code, err = self.report()
        self.assertEqual(code, 1, "the run stays red")
        self.assertIn("    alpha: new", err)

    def test_a_site_failing_run_after_run_is_carried_since_its_first_failure(self):
        self.commit(self.OK)
        self.commit(self.failed("alpha"))            # 2026-09-12
        self.commit(self.failed("alpha") + "\n")     # 2026-09-13, a later run
        self.commit(self.failed("alpha"))            # 2026-09-14
        code, err = self.report()
        self.assertEqual(code, 1)
        self.assertIn("    alpha: carried since 2026-09-12 (3 runs)", err)

    def test_a_new_site_beside_a_carried_one_is_told_apart(self):
        self.commit(self.OK)
        self.commit(self.failed("alpha"))
        self.commit(self.failed("alpha", "beta"))
        _, err = self.report()
        self.assertIn("    alpha: carried since 2026-09-12 (2 runs)", err)
        self.assertIn("    beta: new", err)

    def test_the_file_on_disk_ahead_of_its_commit_is_the_run_being_judged(self):
        """The fetch workflow writes the log and checks before it commits."""
        self.commit(self.OK)
        self.commit(self.failed("alpha"))
        (self.logs / "run-mod.log").write_text(self.failed("alpha") + "\n", encoding="utf-8")
        _, err = self.report()
        self.assertIn("    alpha: carried since 2026-09-12 (2 runs)", err)

    def test_the_coordinator_log_names_the_module(self):
        self.commit("[cloud] a: exit=0\n[cloud] kinotour: exit=1\nexit=1\n", "run-cloud.log")
        _, err = self.report()
        self.assertIn("    kinotour: new", err)

    def test_a_streak_reaching_the_history_limit_is_at_least_that_old(self):
        for _ in range(3):
            self.commit(self.failed("alpha") + "x" * self.day)
        saved = check_runs.HISTORY_LIMIT
        check_runs.HISTORY_LIMIT = 2
        self.addCleanup(lambda: setattr(check_runs, "HISTORY_LIMIT", saved))
        _, err = self.report()
        self.assertIn("    alpha: carried since at least 2026-09-12 (2 runs read)", err)


class UnreadHistoryTest(unittest.TestCase):
    """Unread items are listed as new or carried and never change the verdict. The lines
    come from `common.unread_lines`, the same writer the runs use."""

    setUp = FailingSiteHistoryTest.setUp
    commit = FailingSiteHistoryTest.commit
    PALLAS = ("line", "Järki ja tunteet, To/Tors 5.11 Klo 17.00: Halvjus på")
    # Two items alike past the width the log shows.
    HEAD = "Film 26.10.2026: " + "x" * common.UNREAD_WIDTH
    LONG_A, LONG_B = ("row", HEAD + " ending one"), ("row", HEAD + " ending two")

    @staticmethod
    def written(label, *items, counts=None):
        """The log lines a site's scope prints for these items. -> str."""
        box = {item: (counts or {}).get(item, 1) for item in items}
        return "".join(line + "\n" for line in common.unread_lines(label, box))

    @staticmethod
    def shown(label, item):
        """How the report quotes one item: its log line without a repeat count."""
        return common.unread_lines(label, {item: 1})[0]

    def report(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_runs.main(["--dir", str(self.logs)])
        return code, out.getvalue()

    def test_an_item_first_seen_in_this_run_is_new_and_the_log_stays_green(self):
        self.commit("[biopallas] 19 showtimes\nexit=0\n")
        self.commit(self.written("biopallas", self.PALLAS) + "[biopallas] 19 showtimes\nexit=0\n")
        code, out = self.report()
        self.assertEqual(code, 0)
        self.assertIn("[check] unread: 1 item(s) in 1 log(s), 1 new", out)
        self.assertIn(f"    run-mod.log: {self.shown('biopallas', self.PALLAS)}: new", out)

    def test_two_items_alike_in_what_the_log_shows_stay_two(self):
        """Both lines read `Film 26.10.2026: xxx...`. The digest tells them apart."""
        body = self.written("niagara", self.LONG_A, self.LONG_B)
        texts = [line.split(": ", 1)[1] for line in body.splitlines()]
        self.assertEqual(texts[0], texts[1], "the fixture must print the same text twice")
        self.commit(body + "exit=0\n")
        self.assertEqual(len(check_runs.unread_items(body)), 2)
        _, out = self.report()
        self.assertIn("[check] unread: 2 item(s) in 1 log(s), 2 new", out)

    def test_the_second_of_two_alike_items_is_new_beside_the_carried_first(self):
        self.commit(self.written("niagara", self.LONG_A) + "exit=0\n")
        self.commit(self.written("niagara", self.LONG_A, self.LONG_B) + "exit=0\n")
        _, out = self.report()
        self.assertIn("2 item(s) in 1 log(s), 1 new", out)
        self.assertIn(f"{self.shown('niagara', self.LONG_A)}: carried since 2026-09-11 (2 runs)",
                      out)
        self.assertIn(f"{self.shown('niagara', self.LONG_B)}: new", out)

    def test_an_item_in_earlier_runs_is_carried_whatever_its_repeat_count(self):
        """Niagara's mobile copy doubles an item on some runs and not others."""
        self.commit("exit=0\n")
        self.commit(self.written("biopallas", self.PALLAS) + "exit=0\n")         # 09-12
        self.commit(self.written("biopallas", self.PALLAS, counts={self.PALLAS: 2})
                    + "exit=0\n")                                                # 09-13
        self.commit(self.written("biopallas", self.PALLAS) + "[x] later\nexit=0\n")  # 09-14
        _, out = self.report()
        self.assertIn(f"{self.shown('biopallas', self.PALLAS)}: carried since 2026-09-12 "
                      f"(3 runs)", out)
        self.assertIn("0 new", out)

    def test_a_repeat_count_is_left_out_of_the_quoted_item(self):
        self.commit(self.written("biopallas", self.PALLAS) + "exit=0\n")
        self.commit(self.written("biopallas", self.PALLAS, counts={self.PALLAS: 3})
                    + "exit=0\n")
        _, out = self.report()
        self.assertIn(f"{self.shown('biopallas', self.PALLAS)}: carried since 2026-09-11 "
                      f"(2 runs)", out)
        self.assertNotIn("(x3)", out)

    def test_a_new_item_of_another_site_beside_a_carried_one_is_told_apart(self):
        other = ("date", "KERRO KAIKILLE 3.11. TI klo 15.00 ja klo 18.00")
        self.commit(self.written("biopallas", self.PALLAS) + "exit=0\n")
        self.commit(self.written("biopallas", self.PALLAS) + self.written("kinohuovi", other)
                    + "exit=0\n")
        _, out = self.report()
        self.assertIn(f"{self.shown('biopallas', self.PALLAS)}: carried since 2026-09-11 "
                      f"(2 runs)", out)
        self.assertIn(f"{self.shown('kinohuovi', other)}: new", out)
        self.assertIn("2 item(s) in 1 log(s), 1 new", out)

    def test_output_stays_bounded_and_the_rest_is_counted(self):
        items = [("line", f"line {i}") for i in range(common.UNREAD_SHOWN + 7)]
        body = self.written("biopallas", *items)
        self.assertEqual(len(body.splitlines()), common.UNREAD_SHOWN + 1)
        self.commit(body + "exit=0\n")
        _, out = self.report()
        self.assertIn(f"{common.UNREAD_SHOWN} item(s) in 1 log(s), {common.UNREAD_SHOWN} new, "
                      f"7 more not shown in the logs", out)

    def test_a_failing_log_with_items_is_still_red(self):
        self.commit(self.written("biopallas", self.PALLAS)
                    + "[biopallas] FAILED: no screening line\nexit=1\n")
        code, out = self.report()
        self.assertEqual(code, 1)
        self.assertIn(f"{self.shown('biopallas', self.PALLAS)}: new", out)

    def test_no_items_print_no_unread_line(self):
        self.commit("[biopallas] 19 showtimes\nexit=0\n")
        _, out = self.report()
        self.assertNotIn("unread", out)
