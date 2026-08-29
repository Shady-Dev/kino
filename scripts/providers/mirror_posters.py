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
- **A failure is logged and left hot-linked, never fatal.** kinoakseli.fi
  challenges datacenter IPs, so its posters cannot be fetched from a runner at
  all and will fail every run by design. `tries=2` keeps that cheap. Anything
  that has to succeed here would make a third party's uptime able to fail our
  build.

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


def main() -> int:
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

    # Rewrite references. A URL that failed keeps its remote address, so the
    # poster still renders in the app; only the page generator drops it.
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
