"""One contact address, and no other address anywhere in the tree.

Rotation: the address is a disposable alias typed in the client (static fallback and JS
constant), the page generator and both documents. Missing one on rotation leaves the site
contradicting itself, most likely in the generated pages. Leaks: this repo is public, and
a real name once reached 18 commits. The address is discovered from the client, so the
test carries none of its own and keeps working across a rotation.
"""
import pathlib
import re
import shutil
import subprocess
import unittest

import _ctx


EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Addresses that are legitimately not the contact route. Kept deliberately short: every
# entry is a place a real address could hide behind a plausible-looking name.
ALLOWED = {
    "noreply@anthropic.com",          # commit trailer, if it ever lands in a file
    # The sanctioned author identity. It is in the metadata of every commit already, and
    # CLAUDE.md names it so a future session can recognise an author line that is *not*
    # it. Added after this test caught that very sentence being written -- which is the
    # guard working, not a false positive: a GitHub noreply address is not a personal one.
    "19388620+Shady-Dev@users.noreply.github.com",
}

# Files that hand-write the address. Generated pages are excluded on purpose: they are
# rewritten from build_pages.py on the next run, so between a rotation and that run they
# are legitimately behind, and failing on it would just be noise.
SOURCES = ["index.html", "scripts/build_pages.py", "README.md", "IDEAS.md"]


def tracked_text_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=str(_ctx.ROOT),
                         capture_output=True, text=True, timeout=60)
    out.check_returncode()
    for name in out.stdout.split("\0"):
        if not name:
            continue
        p = _ctx.ROOT / name
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".woff2", ".ico"}:
            continue
        yield p


class ContactAddressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        html = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")
        m = re.search(r"const CONTACT = '([^']+)'", html)
        assert m, "index.html no longer declares a CONTACT constant"
        cls.contact = m.group(1)

    def test_the_client_constant_is_an_address_at_all(self):
        self.assertRegex(self.contact, EMAIL)

    def test_every_hand_written_copy_agrees(self):
        """The whole point: a half-finished rotation fails here instead of shipping."""
        for name in SOURCES:
            with self.subTest(file=name):
                text = (_ctx.ROOT / name).read_text(encoding="utf-8")
                found = set(EMAIL.findall(text)) - ALLOWED
                self.assertIn(self.contact, found,
                              f"{name} does not carry the contact address")
                self.assertEqual(found, {self.contact},
                                 f"{name} carries an address that is not the contact one")

    def test_the_client_static_fallback_matches_its_constant(self):
        """The markup holds a literal so the address survives a broken script. That is a
        second copy inside one file, and the likeliest one to be missed."""
        html = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")
        markup = re.search(r'<div id="contact">.*?</div>', html, re.S)
        self.assertIsNotNone(markup, "the static contact line is gone")
        self.assertIn(self.contact, markup.group(0))

    def test_the_page_generator_matches(self):
        py = (_ctx.ROOT / "scripts" / "build_pages.py").read_text(encoding="utf-8")
        m = re.search(r'^CONTACT = "([^"]+)"', py, re.M)
        self.assertIsNotNone(m, "build_pages.py no longer declares CONTACT")
        self.assertEqual(m.group(1), self.contact,
                         "the generator would stamp a different address onto every page")

    @unittest.skipIf(shutil.which("git") is None, "git not installed")
    def test_no_other_address_is_tracked_anywhere(self):
        """Including the generated pages. This is the leak guard: a personal address that
        reaches a tracked file in a public repo costs a history rewrite to remove."""
        offenders = {}
        for p in tracked_text_files():
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            extra = set(EMAIL.findall(text)) - ALLOWED - {self.contact}
            if extra:
                offenders[str(p.relative_to(_ctx.ROOT))] = sorted(extra)
        self.assertEqual(offenders, {},
                         "tracked files contain an address that is not the contact one")


if __name__ == "__main__":
    unittest.main()
