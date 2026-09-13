"""The design-contract push check keeps its range when `before` cannot be seen.

On 2026-09-13 a rebased branch was force-pushed; `github.event.before` named the old tip,
which no ref carried any more, and the step's `git diff before sha` died with exit 128
(run 34773073208). These tests build small repositories with real git so the object
lookups, the merge base and the diff are git's own, not a mock's idea of them.
"""
import pathlib
import subprocess
import tempfile
import unittest

import _ctx
import check_design_push as cdp

MISSING = "d" * 40


def git(repo, *args):
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(f"git {' '.join(args)}: {r.stderr}")
    return r.stdout.strip()


def commit(repo, message, **files):
    for name, text in files.items():
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        git(repo, "add", name)
    git(repo, "-c", "user.name=t", "-c", "user.email=t@localhost", "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


class CheckDesignPushTest(unittest.TestCase):
    """main: A. branch: B (touches DESIGN.md), C (touches nothing of the contract)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = pathlib.Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        self.a = commit(self.repo, "A", **{"DESIGN.md": "v1\n", "IDEAS.md": "notes\n", "index.html": "x\n"})
        git(self.repo, "checkout", "-q", "-b", "feature")
        self.b = commit(self.repo, "B", **{"DESIGN.md": "v2\n"})
        self.c = commit(self.repo, "C", **{"index.html": "y\n"})
        self.log = []

    def run_check(self, before, after):
        return cdp.main([before, after, "--base", "main", "--repo", str(self.repo)])

    # -- the range is the push's own -----------------------------------------------------

    def test_a_reachable_before_gives_exactly_the_pushed_range(self):
        self.assertEqual(cdp.push_base(self.b, self.c, "main", self.repo, self.log.append), self.b)
        self.assertEqual(self.run_check(self.b, self.c), 0, "B..C touches no contract file")
        self.assertEqual(self.run_check(self.a, self.c), 1, "A..C carries the DESIGN change without IDEAS")

    def test_a_design_change_in_an_earlier_commit_of_the_push_is_not_lost(self):
        """The tip's parent alone would pass: C touches nothing. The push is A..C."""
        self.assertEqual(self.run_check(self.a, self.c), 1)

    # -- the regression: before is not a commit the checkout can see ----------------------

    def test_an_unreachable_before_falls_back_to_the_merge_base_with_main(self):
        base = cdp.push_base(MISSING, self.c, "main", self.repo, self.log.append)
        self.assertEqual(base, self.a)
        self.assertTrue(any("not reachable" in m for m in self.log), self.log)
        self.assertTrue(any("merge base" in m for m in self.log), self.log)

    def test_an_unreachable_before_still_catches_the_design_change(self):
        self.assertEqual(self.run_check(MISSING, self.c), 1)

    def test_an_entry_in_another_commit_of_the_branch_does_not_answer_for_the_change(self):
        """The recovered range is a superset of the push, so "IDEAS.md changed somewhere in
        here" lets an unrelated commit explain B's contract change. It has to be B's own."""
        commit(self.repo, "D", **{"IDEAS.md": "notes\nwhy\n"})
        self.assertEqual(self.run_check(MISSING, "HEAD"), 1)
        self.assertEqual(cdp.entryless_commits(self.a, "HEAD", self.repo), [self.b])

    def test_the_entry_in_the_contract_commit_itself_passes(self):
        git(self.repo, "checkout", "-q", "-B", "entry", self.a)
        d = commit(self.repo, "D", **{"DESIGN.md": "v9\n", "IDEAS.md": "notes\nwhy\n"})
        self.assertEqual(cdp.entryless_commits(self.a, d, self.repo), [])
        self.assertEqual(self.run_check(MISSING, d), 0)

    def test_an_all_zero_before_is_a_created_ref_and_uses_the_merge_base(self):
        self.assertEqual(cdp.push_base("0" * 40, self.c, "main", self.repo, self.log.append), self.a)
        self.assertEqual(self.run_check("0" * 40, self.c), 1)

    def test_no_recoverable_range_fails_loudly_instead_of_guessing(self):
        """A push to main itself with an unreachable before: the merge base is the tip,
        so there is nothing to compare and the check says so with exit 2."""
        git(self.repo, "checkout", "-q", "main")
        self.assertIsNone(cdp.push_base(MISSING, self.a, "main", self.repo, self.log.append))
        self.assertEqual(self.run_check(MISSING, self.a), 2)

    def test_a_missing_before_never_reaches_git_diff(self):
        """The failure mode itself: `git diff` on the unreachable sha is exit 128."""
        with self.assertRaises(RuntimeError):
            cdp.changed_files(MISSING, self.c, self.repo)

    # -- the rule --------------------------------------------------------------------------

    def test_the_verdict_names_the_touched_file_and_the_commit_without_the_entry(self):
        ok, msg = cdp.verdict(["tests/test_design_contract.py", "index.html"], ["0123456789abcdef"])
        self.assertFalse(ok)
        self.assertIn("tests/test_design_contract.py changed without an IDEAS.md entry in "
                      "the same commit", msg)
        self.assertIn("0123456789", msg)
        self.assertEqual(cdp.verdict(["DESIGN.md", "IDEAS.md"]),
                         (True, "design contract change carries an IDEAS entry"))
        self.assertEqual(cdp.verdict(["index.html"], ["0123456789abcdef"]),
                         (True, "design contract untouched"),
                         "a push that takes its own contract change back has nothing to explain")


class ForcePushedBranchTest(unittest.TestCase):
    """`before` names the tip a force-push replaced. It is often still readable -- GitHub
    serves a rewritten SHA for a while -- and `before..after` is then the difference
    between two branches, not the push."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = pathlib.Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        self.a = commit(self.repo, "A", **{"DESIGN.md": "v1\n", "IDEAS.md": "notes\n",
                                           "index.html": "x\n"})
        self.log = []

    def rewrite(self, dropped, kept):
        """Commit `dropped` on a branch off main, rewind, commit `kept` in its place.
        -> (the tip the push reported as `before`, the tip it actually pushed)."""
        git(self.repo, "checkout", "-q", "-B", "feature", self.a)
        before = commit(self.repo, "dropped", **dropped)
        git(self.repo, "checkout", "-q", "-B", "feature", self.a)
        return before, commit(self.repo, "kept", **kept)

    def run_check(self, before, after):
        return cdp.main([before, after, "--base", "main", "--repo", str(self.repo)])

    def test_a_design_change_the_push_dropped_is_not_charged_to_the_new_tip(self):
        before, after = self.rewrite({"DESIGN.md": "v2\n"}, {"index.html": "y\n"})
        self.assertTrue(cdp.has_commit(self.repo, before), "the replaced tip is still readable")
        self.assertEqual(cdp.push_base(before, after, "main", self.repo, self.log.append), self.a)
        self.assertTrue(any("not an ancestor" in m for m in self.log), self.log)
        self.assertEqual(self.run_check(before, after), 0,
                         "the push leaves DESIGN.md at v1; the change is the one it dropped")

    def test_a_contract_change_the_raw_range_cannot_see_is_still_caught(self):
        """The mirror case. The dropped tip carried the same contract change with its
        entry, so `before..after` shows only IDEAS.md going away and reads "contract
        untouched" for a push that changes DESIGN.md with no entry at all."""
        before, after = self.rewrite({"DESIGN.md": "v2\n", "IDEAS.md": "notes\nwhy\n"},
                                     {"DESIGN.md": "v2\n"})
        self.assertEqual(cdp.verdict(cdp.changed_files(before, after, self.repo)),
                         (True, "design contract untouched"))
        self.assertEqual(self.run_check(before, after), 1)


class WorkflowWiringTest(unittest.TestCase):
    CI = (_ctx.ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    def test_ci_runs_the_script_with_the_event_range(self):
        self.assertIn('python3 scripts/check_design_push.py "${{ github.event.before }}" "${{ github.sha }}"', self.CI)
        self.assertNotIn('git diff --name-only "${{ github.event.before }}"', self.CI,
                         "the inline diff is what died on an unreachable before")

    def test_ci_no_longer_skips_a_created_ref(self):
        """The script handles the all-zero before itself, through the merge base."""
        self.assertNotIn("github.event.before != '0000000000000000000000000000000000000000'", self.CI)
        self.assertNotIn("both skip, since there is no range to read", self.CI,
                         "the comment outlived the skip it described")


if __name__ == "__main__":
    unittest.main()
