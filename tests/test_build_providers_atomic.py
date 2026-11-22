"""`data/providers.json` is replaced whole or not at all.

It was written in place, so a run killed mid-write left truncated JSON for the next
`git add data` to commit (review I3, 2026-11-22). The client falls back to `PROV_FALLBACK`
only when the file cannot be read, and a truncated one does exactly that.
"""
import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest

import _ctx
import build_providers


class AtomicWriteTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cwd = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, cwd)
        # Read only: main() compares the fallback block without --sync-index.
        self.addCleanup(setattr, build_providers, "INDEX", build_providers.INDEX)
        build_providers.INDEX = _ctx.ROOT / "index.html"
        self.path = pathlib.Path("data/providers.json")
        self.path.parent.mkdir()
        self.old = json.dumps({"providers": [{"id": "old"}, {"id": "older"}]})
        self.path.write_text(self.old, encoding="utf-8")

    def test_a_write_that_dies_halfway_leaves_the_previous_file(self):
        real = pathlib.Path.write_text

        def torn(path, text, *a, **kw):
            real(path, text[: len(text) // 2], *a, **kw)
            raise OSError("disk full")
        pathlib.Path.write_text = torn
        self.addCleanup(setattr, pathlib.Path, "write_text", real)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(OSError):
            build_providers.main([])
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.old)

    def test_a_whole_write_replaces_it(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build_providers.main([])
        self.assertGreater(len(json.loads(self.path.read_text(encoding="utf-8"))["providers"]), 2)
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["providers.json"])


if __name__ == "__main__":
    unittest.main()
