"""Every request under scripts/ goes through common's opener, so its redirect policy holds
for adapters written later.

`common.make_opener` refuses a redirect off https and carries no FTP, file or data
handler (review L1, 2026-11-22). A module that calls `urlopen` or builds its own opener
skips all of that without any test noticing, which is why this scans the tree rather
than the modules that exist today. A file that has to open a connection itself is named
in ALLOWED with the reason.
"""
import ast
import pathlib
import unittest

import _ctx

SCRIPTS = _ctx.ROOT / "scripts"
ROUTE = SCRIPTS / "providers" / "common.py"

# Calls that open a connection or build an opener outside common.
CALLS = {"urlopen", "build_opener", "OpenerDirector", "HTTPConnection", "HTTPSConnection",
         "create_connection"}
# Classes whose subclass is a connection or a handler of its own.
BASES = {"HTTPConnection", "HTTPSConnection", "HTTPHandler", "HTTPSHandler", "BaseHandler",
         "OpenerDirector"}

ALLOWED = {
    "scripts/indexnow.py": "posts this site's changed URLs to the fixed api.indexnow.org "
                           "endpoint, never a URL a provider supplied",
    "scripts/ci_verified.py": "reads this repository's own check runs from the GitHub API, "
                              "never a URL a provider supplied",
    "scripts/providers/johku.py": "an HTTPS connection that skips Johku's interim responses; "
                                  "it is mounted through common.make_opener, so the redirect "
                                  "policy still holds",
}


def _name(node):
    return node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", None)


def direct_uses(path):
    """-> [(line, what)] for every direct connection or opener in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _name(node.func) in CALLS:
            found.append((node.lineno, f"calls {_name(node.func)}"))
        elif isinstance(node, ast.ClassDef):
            for b in node.bases:
                if _name(b) in BASES:
                    found.append((node.lineno, f"subclasses {_name(b)}"))
    return found


def offenders(root=SCRIPTS):
    """-> {relative path: [(line, what)]} for every file under `root` but common.py."""
    out = {}
    for path in sorted(root.rglob("*.py")):
        if path == ROUTE:
            continue
        uses = direct_uses(path)
        if uses:
            out[path.relative_to(_ctx.ROOT).as_posix()] = uses
    return out


class NetworkRouteTest(unittest.TestCase):

    def test_no_file_opens_a_connection_outside_common(self):
        found = {p: u for p, u in offenders().items() if p not in ALLOWED}
        self.assertEqual(found, {}, "open requests through common.fetch or "
                                    "common.make_opener, or name the file in ALLOWED")

    def test_every_allowed_file_still_needs_its_entry(self):
        found = offenders()
        for path in ALLOWED:
            with self.subTest(path=path):
                self.assertIn(path, found, "the exception is no longer needed; remove it")

    def test_the_scan_sees_each_form_it_names(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "adapter.py"
            for code in ("import urllib.request\nurllib.request.urlopen('https://x')\n",
                         "from urllib.request import build_opener\nbuild_opener()\n",
                         "import http.client\nhttp.client.HTTPSConnection('x')\n",
                         "import urllib.request\nclass H(urllib.request.HTTPSHandler):\n"
                         "    pass\n"):
                with self.subTest(code=code):
                    src.write_text(code, encoding="utf-8")
                    self.assertTrue(direct_uses(src))


if __name__ == "__main__":
    unittest.main()
