#!/usr/bin/env python3
"""Mirror hot-linked posters into data/posters/ and rewrite the references.

Why this exists: every poster served from a cinema's own CDN or from
image.tmdb.org is a third-party request made by the reader's browser, so those
hosts see a visitor's IP on every page view. `referrerpolicy="no-referrer"`
keeps the page URL out of it, which is the part that was already right. This
closes the rest for posters; the Google Fonts request is still open.

Runs after enrichment and before build_pages, so a poster mirrored on this run
is same-origin in the pages the same run generates.

Two things worth knowing before changing this:

- **Everything is downscaled to POSTER_W.** The sources are not comparable
  sizes: TMDB serves w342 (~25 kB) while MyCloudCinema only publishes 1080 and
  Nexxo publishes the distributor's 1984x2835 key art. Mirroring those verbatim
  would put tens of megabytes of images into a repo that is currently 4 MB, to
  render a tile about 130 px wide on a phone. Pillow is installed in the
  workflow for this and nothing else.
- **A poster that fails to download is logged and left hot-linked, never
  fatal.** kinoakseli.fi challenges datacenter IPs, so its posters cannot be
  fetched from a runner at all and will fail every run by design. `tries=2`
  keeps that cheap. Anything that has to succeed here would make a third
  party's uptime able to fail our build.
- **Not being able to run at all is different, and exits CANNOT_RUN.** That is
  not a poster that failed; it is every poster silently left remote by a step
  that then reported success. See the exit codes below.

Filenames are sha1(url)[:16].jpg: the sources have no id namespace in common,
and the URL is the only thing that identifies a poster across all seven hosts.
"""

import glob
import hashlib
import io
import json
import pathlib
import sys
import time
from urllib.parse import quote, urlsplit, urlunsplit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

# Three states, because the caller has to tell them apart and the data cannot.
#
#   OK           ran; some posters may have failed to download, and those are logged
#   CANNOT_RUN   cannot downscale at all, so nothing was attempted and nothing changed
#   1            an uncaught traceback, which is what the interpreter already exits with
#
# The gap this closes: with a missing Pillow reported as OK, "mirrored everything" and
# "could not mirror anything" were the same answer to a caller. The second is invisible
# downstream -- every reference stays remote, the client declines to render a remote
# poster, and those films show a placeholder tile -- so the one step positioned to notice
# was the one saying it was fine. 3 rather than 1 because 1 already means the script
# crashed, and 2 is the conventional usage error.
OK = 0
CANNOT_RUN = 3

POSTER_DIR = pathlib.Path("data/posters")
POSTER_W = 342          # what TMDB already serves and what the client renders from
JPEG_Q = 82
MIN_BYTES = 500         # anything smaller is an error page, not an image
PAUSE = 0.3             # these are other people's CDNs
HEADERS = {"user-agent": common.UA, "accept": "image/*,*/*"}


def key_for(url: str) -> str:
    """Keyed on the URL exactly as the provider published it, never on the
    percent-encoded form: the published string is what the reference in the JSON
    says, so encoding it first would rename a poster the day the encoder changes."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def request_url(url: str) -> str:
    """Percent-encode the path and query for urllib.

    Nexxo publishes filenames with spaces in them ("SPA WEEKEND_BLACK
    BEAR_POSTER_70x100_FINLAND.jpg"), which urllib rejects outright as a control
    character rather than encoding. A browser encodes on the way out, so the
    address works everywhere except here.
    """
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, quote(p.path, safe="/%:@"),
                       quote(p.query, safe="=&%"), ""))


def collect(docs):
    """Every distinct http(s) poster URL currently referenced."""
    urls = set()
    for _, shows in docs:
        for s in shows:
            u = (s.get("img") or "").strip()
            if u.startswith("http"):
                urls.add(u)
    return urls


def area_docs():
    for p in sorted(glob.glob("data/area-*.json")):
        try:
            doc = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[mirror] skip {p}: {e}")
            continue
        yield p, doc


def download(url: str, dest: pathlib.Path) -> bool:
    from PIL import Image
    raw = common.fetch(request_url(url), headers=HEADERS, tries=2, backoff=3, timeout=20)
    if len(raw) < MIN_BYTES:
        raise RuntimeError(f"{len(raw)} bytes")
    im = Image.open(io.BytesIO(raw))
    im.load()
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if im.width > POSTER_W:
        h = round(im.height * POSTER_W / im.width)
        im = im.resize((POSTER_W, h), Image.LANCZOS)
    tmp = dest.with_name(dest.name + ".tmp")
    im.save(tmp, "JPEG", quality=JPEG_Q, optimize=True)
    tmp.replace(dest)
    return True


def pillow_problem() -> str:
    """Can Pillow do the one job this script needs? -> '' if yes, else why not.

    Importing it is not the question. `from PIL import Image` succeeds on an install
    whose imaging library is incomplete -- a wheel built against a libjpeg that is no
    longer there, a partial reinstall -- and then every poster raises inside its own try
    and is counted as a download failure. Exit 0, "185 failed", and the same silent
    degradation the exit code was split apart to catch, one layer further in.

    So this is a round trip through the exact calls `download` makes: open a paletted
    image, convert, resize with LANCZOS, save as JPEG at the real quality settings. Four
    by six pixels, so it costs nothing.

    The two causes get different sentences because they need different fixes, and
    "install it with pip install pillow" is actively misleading to someone who has.
    """
    try:
        from PIL import Image
    except Exception as e:
        return (f"Pillow is not installed for this interpreter ({type(e).__name__}). "
                "Install it with: python3 -m pip install pillow.")
    try:
        im = Image.new("P", (4, 6)).convert("RGB").resize((2, 3), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=JPEG_Q, optimize=True)
        if not buf.getbuffer().nbytes:
            raise RuntimeError("the JPEG encoder returned no bytes")
    except Exception as e:
        return (f"Pillow is installed but cannot encode a JPEG ({type(e).__name__}: "
                f"{e}). Its imaging library is probably incomplete. Reinstall it with: "
                "python3 -m pip install --force-reinstall pillow.")
    return ""


def main() -> int:
    # Checked once, up front, and checked by using it rather than by importing it.
    # Without this every single download raises inside its own try and is counted as a
    # failure, so a machine that cannot downscale reports "185 failed" and reads like
    # the network is down. This runs on the local half too now, where Pillow is not a
    # given, and the honest answer is one line rather than 185.
    #
    # One line, and a non-zero exit. It used to return 0 so that a local run without
    # Pillow could still publish showtimes -- but neither caller needs that, because
    # neither one stops on this exit code. The cloud workflow commits the data in the step
    # before the gate that reads it, and the local wrapper collects the code into `fail`
    # and carries on through commit, push and dispatch. So the showtimes go out either
    # way, and the only thing returning 0 bought was hiding the fact that no poster was
    # mirrored. That is why there is no --optional flag: the tolerance already lives in
    # the callers, where it belongs, and duplicating it here would just give the silent
    # mode a name.
    #
    # Nothing below this point runs, so nothing is written and no reference is rewritten.
    # The data keeps the cinema's own poster URL, exactly as it did before this script
    # existed; the client declines to render those and build_pages says so loudly.
    problem = pillow_problem()
    if problem:
        print(f"[mirror] {problem} Nothing can be downscaled, so no poster can be "
              "mirrored: posters stay on the cinemas' own hosts, the client will not "
              "render them, and those films show a placeholder tile.")
        return CANNOT_RUN

    POSTER_DIR.mkdir(parents=True, exist_ok=True)

    docs = [(p, doc) for p, doc in area_docs()]
    extra_path = pathlib.Path("data/films-extra.json")
    extra = None
    if extra_path.exists():
        extra = json.loads(extra_path.read_text(encoding="utf-8"))

    urls = collect((p, doc.get("shows") or []) for p, doc in docs)
    if extra:
        for f in (extra.get("films") or {}).values():
            if isinstance(f, dict):
                u = (f.get("img") or "").strip()
                if u.startswith("http"):
                    urls.add(u)

    mapping = {}       # url -> repo-relative path
    had = fetched = 0
    failed = {}        # host -> [reason, ...]
    bytes_added = 0

    for url in sorted(urls):
        dest = POSTER_DIR / f"{key_for(url)}.jpg"
        rel = f"data/posters/{dest.name}"
        if dest.exists():
            mapping[url] = rel
            had += 1
            continue
        host = url.split("/")[2] if "//" in url else url
        try:
            download(url, dest)
        except Exception as e:
            failed.setdefault(host, []).append(f"{type(e).__name__}: {e}")
            continue
        mapping[url] = rel
        fetched += 1
        bytes_added += dest.stat().st_size
        time.sleep(PAUSE)

    # Rewrite references. A URL that failed keeps its remote address on purpose, so a
    # third party's downtime cannot stop publication -- but neither the app nor a
    # generated page's <img> renders a remote poster (safeAssetUrl there, the
    # data/posters/ check in build_pages here), so those films show a placeholder tile
    # until a later run mirrors them. Only JSON-LD still references the remote URL: a
    # crawler reading markup is not a visitor's browser.
    rewritten = files = 0
    for p, doc in docs:
        changed = False
        for s in doc.get("shows") or []:
            u = (s.get("img") or "").strip()
            if u in mapping:
                s["img"] = mapping[u]
                changed = True
                rewritten += 1
        if changed:
            common.write_json(pathlib.Path(p), doc)
            files += 1

    if extra:
        changed = False
        for f in (extra.get("films") or {}).values():
            if isinstance(f, dict):
                u = (f.get("img") or "").strip()
                if u in mapping:
                    f["img"] = mapping[u]
                    changed = True
                    rewritten += 1
        if changed:
            common.write_json(extra_path, extra)
            files += 1

    total = sum(p.stat().st_size for p in POSTER_DIR.glob("*.jpg"))
    print(f"[mirror] {len(urls)} remote poster urls: {had} already mirrored, "
          f"{fetched} downloaded (+{bytes_added // 1024} kB), "
          f"{sum(len(v) for v in failed.values())} failed")
    for host, errs in sorted(failed.items()):
        print(f"[mirror] failed {host} ({len(errs)}): {errs[0]}")
    print(f"[mirror] {rewritten} references rewritten in {files} files; "
          f"data/posters now {len(list(POSTER_DIR.glob('*')))} files, "
          f"{total // 1024} kB")
    return OK


if __name__ == "__main__":
    sys.exit(main())
