#!/usr/bin/env python3
"""Keep every served page's Content-Security-Policy in step with its inline scripts.
-> 0 clean, 1 a page disagrees.

    python3 scripts/check_csp.py                # every HTML file the site serves
    python3 scripts/check_csp.py --sync         # rewrite each page's tag to match
    python3 scripts/check_csp.py FILE [FILE]    # just these

GitHub Pages sets no response headers, so a `<meta http-equiv>` tag is the only policy a
page can carry. It allows scripts from this origin, the PostHog bundle host, and each
inline script by its SHA-256, so an inline script added or edited without `--sync` stops
running in the browser. This check fails first. `build_pages.py` writes the tag through
`with_policy` below, so generated pages are correct as built; `--sync` is for the
hand-written ones. JSON-LD blocks are data, which a policy does not govern, so they carry
no hash. `frame-ancestors` is ignored in a meta tag and is left out.

The tag has to come before the first script, style or link, because a meta policy applies
only to what the parser reaches after it. It goes straight after `<meta charset>`.
"""
import argparse
import base64
import hashlib
import html
import pathlib
import re
import subprocess
import sys

import check_inline_js

ROOT = pathlib.Path(__file__).resolve().parent.parent

POLICY = ("default-src 'self'; script-src 'self'{hashes} https://eu-assets.i.posthog.com; "
          "connect-src 'self' https://eu.i.posthog.com; img-src 'self'; "
          "style-src 'self' 'unsafe-inline'; font-src 'self'; object-src 'none'; "
          "base-uri 'self'; form-action 'self'; worker-src 'self'; manifest-src 'self'")

TAG_RE = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">\n?', re.I)
CHARSET_RE = re.compile(r"<meta charset=[^>]*>\n?", re.I)
FIRST_RESOURCE_RE = re.compile(r"<(?:script|style|link)\b", re.I)


def script_hashes(page):
    """-> ["'sha256-...'"] for each inline script that runs, in page order, deduplicated."""
    out = []
    for kind, _, body in check_inline_js.blocks(TAG_RE.sub("", page)):
        if kind == "js":
            digest = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode()
            h = f"'sha256-{digest}'"
            if h not in out:
                out.append(h)
    return out


def policy(page):
    """The policy `page` should carry. -> str."""
    return POLICY.format(hashes="".join(" " + h for h in script_hashes(page)))


def with_policy(page):
    """`page` with its tag replaced or, when it has none, inserted after `<meta charset>`."""
    tag = f'<meta http-equiv="Content-Security-Policy" content="{policy(page)}">\n'
    if TAG_RE.search(page):
        return TAG_RE.sub(lambda _: tag, page, count=1)
    m = CHARSET_RE.search(page)
    if not m:
        raise ValueError("no <meta charset> to place the policy after")
    return page[:m.end()] + tag + page[m.end():]


def problems(page):
    """-> [complaint] for one page's text, empty when its tag is right and in place."""
    tags = TAG_RE.findall(page)
    if not tags:
        return ["no Content-Security-Policy meta tag"]
    if len(tags) > 1:
        return [f"{len(tags)} Content-Security-Policy meta tags"]
    out = []
    want = policy(page)
    if html.unescape(tags[0]) != want:
        out.append("the policy does not match the page's inline scripts; run "
                   "python3 scripts/check_csp.py --sync")
    first = FIRST_RESOURCE_RE.search(page)
    if first and first.start() < TAG_RE.search(page).start():
        out.append("the policy comes after a script, style or link, which it does not cover")
    return out


def served(root=ROOT):
    """Every HTML file the site serves: tracked or new, and not ignored. -> [Path]."""
    r = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "--", "*.html"],
                       cwd=root, capture_output=True, text=True, check=True)
    return [root / p for p in sorted(set(r.stdout.split()))]


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", help="pages to check (default: every served page)")
    ap.add_argument("--sync", action="store_true", help="rewrite each page's tag to match")
    args = ap.parse_args(argv)

    paths = [pathlib.Path(f) for f in args.files] or served()
    bad = synced = 0
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if args.sync:
            new = with_policy(text)
            if new != text:
                path.write_text(new, encoding="utf-8")
                synced += 1
            continue
        for complaint in problems(text):
            print(f"[csp] {path}: {complaint}", file=sys.stderr)
            bad += 1
    if args.sync:
        print(f"[csp] {len(paths)} page(s), {synced} rewritten")
        return 0
    print(f"[csp] {len(paths)} page(s) checked, {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
