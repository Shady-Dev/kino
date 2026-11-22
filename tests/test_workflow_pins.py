"""Every pip install in a workflow is pinned by hash, and the fetch job checks its cache
restore before any script runs.

A Checks run on main shares the cache scope the write-token fetch job restores from, so
an unpinned package there could plant a cache entry whose tarball adds files under
`scripts/` (review L3, 2026-11-22). The scan covers every workflow file, so a new install
step is held to the same rule.
"""
import re
import unittest

import _ctx

WORKFLOWS = sorted((_ctx.ROOT / ".github" / "workflows").glob("*.yml"))


def commands(text):
    """Shell lines with their backslash continuations joined."""
    return re.sub(r"\\\n\s*", " ", text).splitlines()


class PipPinTest(unittest.TestCase):

    def test_every_pip_install_requires_hashes_and_wheels(self):
        found = 0
        for wf in WORKFLOWS:
            for line in commands(wf.read_text(encoding="utf-8")):
                if not line.lstrip().startswith("#") and re.search(r"\bpip install\b", line):
                    found += 1
                    with self.subTest(workflow=wf.name, line=line.strip()):
                        self.assertIn("--require-hashes", line)
                        self.assertIn("--only-binary :all:", line)
        self.assertGreaterEqual(found, 3)


class CacheRestoreCheckTest(unittest.TestCase):

    def test_the_fetch_job_checks_the_restore_before_any_script(self):
        text = (_ctx.ROOT / ".github/workflows/biorex.yml").read_text(encoding="utf-8")
        steps = re.split(r"\n      - ", text)
        names = [s.split("\n", 1)[0] for s in steps]
        restore = next(i for i, s in enumerate(steps) if "path: .http-cache" in s)
        check = next(i for i, n in enumerate(names) if "Check the cache restored nothing" in n)
        first_script = next(i for i, s in enumerate(steps) if "python3 " in s)
        self.assertEqual(check, restore + 1)
        self.assertLess(check, first_script)
        self.assertIn("git status --porcelain --ignored --untracked-files=all", steps[check])
        self.assertIn("exit 1", steps[check])


class CommitStepHooksTest(unittest.TestCase):
    """The step holding the push token runs git with hooks off. An earlier step parsed
    provider content and could have planted a .git/hooks script (review I2, 2026-11-22)."""

    def step(self):
        text = (_ctx.ROOT / ".github/workflows/biorex.yml").read_text(encoding="utf-8")
        return next(s for s in re.split(r"\n      - ", text)
                    if s.startswith("name: Commit data and logs"))

    def test_every_git_in_the_step_runs_with_hooks_off(self):
        step = self.step()
        env, run = step.split("\n        run: |", 1)
        self.assertIn("PUSH_TOKEN:", env)
        self.assertIn('GIT_CONFIG_COUNT: "1"', env)
        self.assertIn("GIT_CONFIG_KEY_0: core.hooksPath", env)
        self.assertIn("GIT_CONFIG_VALUE_0: /dev/null", env)
        self.assertRegex(run, r"\bgit (?:add|commit)\b", "the step no longer runs git")
        for word in ("hooksPath", "GIT_CONFIG"):
            self.assertNotIn(word, run, "the run block overrides the hooks setting")


if __name__ == "__main__":
    unittest.main()
