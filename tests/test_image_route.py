"""Every picture the pipeline did not draw is decoded by `mirror_posters.open_image`.

That helper limits Pillow to JPEG, PNG, WebP and GIF (review H2 and L2, 2026-11-22). A
bare `Image.open` elsewhere reaches every decoder Pillow ships, so this scans the whole of
`scripts/` rather than the modules that exist today. `make_cards.py` draws title cards
from nothing and opens no file, so it needs no exception.
"""
import ast
import pathlib
import tempfile
import unittest

import _ctx

SCRIPTS = _ctx.ROOT / "scripts"
HELPER = ("scripts/providers/mirror_posters.py", "open_image")


def image_opens(path):
    """-> [(line, enclosing function)] for every `Image.open` call in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    found = []

    def walk(node, fn):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, child.name)
                continue
            if isinstance(child, ast.ImportFrom) and child.module == "PIL.Image" and \
                    any(a.name == "open" for a in child.names):
                found.append((child.lineno, fn))
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and \
                    child.func.attr == "open" and \
                    getattr(child.func.value, "id", getattr(child.func.value, "attr", "")) == "Image":
                found.append((child.lineno, fn))
            walk(child, fn)
    walk(tree, None)
    return found


def offenders(root=SCRIPTS):
    out = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(_ctx.ROOT).as_posix()
        uses = [(n, fn) for n, fn in image_opens(path) if (rel, fn) != HELPER]
        if uses:
            out[rel] = uses
    return out


class ImageRouteTest(unittest.TestCase):

    def test_no_picture_is_decoded_outside_the_helper(self):
        self.assertEqual(offenders(), {}, "decode through mirror_posters.open_image")

    def test_the_helper_is_still_where_the_scan_expects_it(self):
        uses = image_opens(_ctx.ROOT / HELPER[0])
        self.assertIn(HELPER[1], [fn for _, fn in uses])

    def test_the_scan_sees_each_form_it_names(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "adapter.py"
            for code in ("from PIL import Image\nImage.open('x')\n",
                         "import PIL.Image\ndef f():\n    PIL.Image.open('x')\n",
                         "from PIL.Image import open\n"):
                with self.subTest(code=code):
                    src.write_text(code, encoding="utf-8")
                    self.assertTrue(image_opens(src))


if __name__ == "__main__":
    unittest.main()
