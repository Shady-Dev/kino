"""A page build that fails partway writes nothing.

`build_pages.main()` wrote each page as it produced it, and `biorex.yml` stages and pushes
the pages before it checks the exit code, so a failed build published a mix of two
generations: city pages disagreeing with the venue pages they link to, under a sitemap
describing neither. Measured before the fix by raising on the 41st render against the real
data: 40 of 172 pages new, 132 old, all staged.

The pages are now collected and written in one loop at the end. These tests run the real
`main()` against the repo's own `data/` in a temporary tree, because the ordering between
the venue pass and the city pass is what makes a partial build incoherent.
"""
import contextlib
import hashlib
import io
import json
import pathlib
import shutil
import tempfile
import unittest

import _ctx
import build_pages as bp


REAL_DATA = _ctx.ROOT / "data"


class PartialBuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "data").mkdir()
        # Only the JSON. Nothing in the generator opens a poster -- it reads the `img`
        # string and checks its prefix -- so copying 21 MB of images would buy nothing.
        for p in REAL_DATA.glob("*.json"):
            shutil.copy2(p, self.root / "data" / p.name)

        for name in ("ROOT", "DATA"):
            self.addCleanup(setattr, bp, name, getattr(bp, name))
        bp.ROOT, bp.DATA = self.root, self.root / "data"

        real_page = bp.page
        self.addCleanup(setattr, bp, "page", real_page)
        self.real_page = real_page
        # Module-level and accumulating, so one test's remote posters would otherwise
        # be counted again in the next one's warning.
        bp._unmirrored_hosts.clear()

    # -- helpers -----------------------------------------------------------------------

    def build(self, fail_after=None, fail_write_after=None):
        """Run the real main(). -> the exception it raised, or None.

        `fail_after` raises inside the renderer, which is where the reported defect
        lives. `fail_write_after` raises inside the flush instead -- a different and much
        narrower window, and the one the batching does not close."""
        if fail_write_after is not None:
            real_write = bp.write_if_changed
            self.addCleanup(setattr, bp, "write_if_changed", real_write)
            wcalls = {"n": 0}

            def exploding_write(path, text, stats):
                wcalls["n"] += 1
                if wcalls["n"] > fail_write_after:
                    raise OSError(f"injected write failure on file {wcalls['n']}")
                return real_write(path, text, stats)

            bp.write_if_changed = exploding_write
        if fail_after is None:
            bp.page = self.real_page
        else:
            calls = {"n": 0}

            def exploding(**kw):
                calls["n"] += 1
                if calls["n"] > fail_after:
                    raise RuntimeError(f"injected failure rendering page {calls['n']}")
                return self.real_page(**kw)

            bp.page = exploding
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                bp.main()
            except Exception as e:
                return e
        return None

    def snapshot(self):
        """Every generated file, by content."""
        out = {}
        for p in sorted(self.root.rglob("index.html")):
            out[str(p.relative_to(self.root))] = hashlib.sha256(p.read_bytes()).hexdigest()
        sm = self.root / "sitemap.xml"
        if sm.exists():
            out["sitemap.xml"] = hashlib.sha256(sm.read_bytes()).hexdigest()
        return out

    def perturb(self):
        """Change the schedule the way a fresh fetch would, so pages would move."""
        n = 0
        for p in sorted((self.root / "data").glob("area-*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            if not d.get("shows"):
                continue
            for s in d["shows"]:
                s["title"] = s.get("title", "") + " (uusi)"
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            n += 1
        return n

    # -- the baseline the rest depends on ------------------------------------------------

    def test_a_clean_build_writes_the_whole_set(self):
        self.assertIsNone(self.build())
        got = self.snapshot()
        self.assertIn("sitemap.xml", got)
        self.assertGreater(len(got), 100, "the fixture stopped producing a real page set")

    def test_the_perturbation_would_otherwise_move_a_lot_of_pages(self):
        """The guard that stops every test below passing for the wrong reason. If the
        perturbation changed nothing, "no page changed after the failure" would be true
        of a build that was working perfectly and of one that wrote nothing at all."""
        self.build()
        before = self.snapshot()
        self.assertGreater(self.perturb(), 1, "fewer than two area files carry shows")
        self.assertIsNone(self.build())
        after = self.snapshot()
        moved = [k for k in before if before[k] != after.get(k)]
        self.assertGreater(len(moved), 20, "the perturbation barely moved the pages")

    # -- the defect ----------------------------------------------------------------------

    def test_a_failure_partway_through_leaves_every_page_untouched(self):
        """The reported case. Forty pages into a build that would have written a hundred
        and seventy-three, an exception -- and the tree must look exactly as it did."""
        self.build()
        before = self.snapshot()
        self.perturb()
        err = self.build(fail_after=40)
        self.assertIsInstance(err, RuntimeError)
        self.assertEqual(self.snapshot(), before)

    def test_the_sitemap_is_not_left_describing_a_generation_that_was_not_written(self):
        """Stated separately because the sitemap is written last and is the one file a
        partial build would most obviously disagree with."""
        self.build()
        before = self.snapshot()["sitemap.xml"]
        self.perturb()
        self.build(fail_after=40)
        self.assertEqual(self.snapshot()["sitemap.xml"], before)

    def test_where_the_failure_lands_does_not_matter(self):
        """Early, mid, and inside the city-page pass, which is the one that matters.

        The boundary is derived rather than written down: main() renders both languages
        of every venue before it starts on the cities, so the first city render is
        `2 * venues + 1`. A hard-coded number was wrong here once already -- 140 looked
        late and is still in the venue pass, which let a half-fix that flushed the venue
        pages before the city pass go green."""
        self.build()
        before = self.snapshot()
        self.perturb()
        first_city = 2 * len(bp.load_venues()) + 1
        for n in (1, 40, first_city, first_city + 2):
            with self.subTest(fail_after=n):
                err = self.build(fail_after=n)
                self.assertIsInstance(err, RuntimeError)
                self.assertEqual(self.snapshot(), before)

    def test_the_first_ever_build_failing_writes_no_pages_at_all(self):
        """No previous generation to preserve. A failed first build must not leave a
        handful of orphan pages for the workflow to commit as if they were a site."""
        err = self.build(fail_after=40)
        self.assertIsInstance(err, RuntimeError)
        self.assertEqual(self.snapshot(), {})

    # -- and the run still publishes what did work -----------------------------------------

    def test_a_failed_build_does_not_hold_back_the_data_it_was_built_from(self):
        """The half of the rule that is easy to lose. The workflow stages data and pages
        in one commit; pages being held back must not mean the schedule is held back too.
        The generator never writes under data/, and this says so rather than assuming
        it -- a fix that reached for a repo-wide rollback would fail here."""
        self.build()
        self.perturb()
        data_before = {p.name: p.read_bytes()
                       for p in sorted((self.root / "data").glob("*.json"))}
        self.build(fail_after=40)
        data_after = {p.name: p.read_bytes()
                      for p in sorted((self.root / "data").glob("*.json"))}
        self.assertEqual(data_before, data_after)

    def test_a_write_failure_is_not_swallowed(self):
        """The window batching does not close, pinned so nobody closes it by hiding it.

        The flush compares and writes and does no work of its own that can fail, so the
        only way it stops halfway is the disk. That leaves a mixed set exactly as before
        -- and the one response that would make it worse is catching the error and
        letting the run report success, because then the mixture publishes with a green
        tick. It has to propagate."""
        self.build()
        self.perturb()
        err = self.build(fail_write_after=5)
        self.assertIsInstance(err, OSError)

    def test_the_next_clean_build_publishes_the_whole_new_generation(self):
        """A failure defers the pages, it does not lose them. The run after it must write
        the complete new set, not the remainder of the one that died."""
        self.build()
        before = self.snapshot()
        self.perturb()
        self.build(fail_after=40)
        self.assertIsNone(self.build())
        after = self.snapshot()
        self.assertEqual(sorted(after), sorted(before))
        moved = [k for k in before if before[k] != after[k]]
        self.assertGreater(len(moved), 20)


if __name__ == "__main__":
    unittest.main()
