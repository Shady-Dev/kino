"""A test file's `if __name__ == "__main__"` guard comes after every test in it.

Thirteen files had it mid-file, so running one directly ran only the classes above it:
`python3 tests/test_check_runs.py` ran 10 of 28 (review L11, 2026-11-22). Discovery and
`run_tests.py` were unaffected, which is why nothing noticed. The scan covers every test
file, so a new one is held to it too.
"""
import ast
import unittest

import _ctx

FILES = sorted((_ctx.ROOT / "tests").glob("test_*.py")) + \
    sorted((_ctx.ROOT / "tests" / "browser").glob("test_*.py"))


def is_main_guard(node):
    return (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
            and getattr(node.test.left, "id", None) == "__name__")


def defined_after_guard(path):
    """-> names of top-level classes and functions after the main guard."""
    body = ast.parse(path.read_text(encoding="utf-8"), str(path)).body
    at = next((i for i, n in enumerate(body) if is_main_guard(n)), None)
    if at is None:
        return []
    return [n.name for n in body[at + 1:]
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]


class MainGuardLastTest(unittest.TestCase):

    def test_no_test_file_defines_anything_after_its_main_guard(self):
        late = {p.relative_to(_ctx.ROOT).as_posix(): names
                for p in FILES if (names := defined_after_guard(p))}
        self.assertEqual(late, {})

    def test_the_scan_reads_files_that_have_one(self):
        self.assertGreater(sum(any(is_main_guard(n) for n in ast.parse(
            p.read_text(encoding="utf-8")).body) for p in FILES), 100)


if __name__ == "__main__":
    unittest.main()
