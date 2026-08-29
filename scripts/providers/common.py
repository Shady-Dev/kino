"""Shared HTTP fetch with retry for provider adapters.

Named common, not http: run.py and fetch_data.py put this directory first on
sys.path, and a local http.py would shadow the stdlib package urllib.request
itself imports (http.client), breaking every fetch in the pipeline.

One transient 502 or connection reset used to count as total site failure for
the adapters without their own retry loop, and the next cron is four hours
away. tries=3 with backoff*n sleeps means a worst case of 3*backoff seconds of
extra wait per request, so a dead upstream cannot stall the workflow.
"""
import hashlib
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

# Identifies the reader. Every adapter used to send a Chrome string, which is an
# automated pipeline claiming to be a person at a keyboard -- the one thing in here a
# cinema had no way to check for itself. Probed against all eleven providers on
# 2026-08-30 before changing it: every one answers this byte-for-byte identically to the
# Chrome string, so honesty costs nothing. If a provider ever refuses it, say so in
# IDEAS and keep the browser string for that one host deliberately, rather than quietly
# re-disguising the whole pipeline.
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

# Validator cache for conditional GETs. Deliberately outside the repo tree and
# gitignored: it holds verbatim copies of third parties' pages, and committing those
# is the rule that probe/ already exists to enforce -- one such dump put someone
# else's API key in this repo. On Actions the directory is restored by actions/cache
# between runs; locally it simply survives, since the wrapper's `git reset --hard`
# does not touch untracked files.
CACHE_DIR = pathlib.Path(os.environ.get("KINO_HTTP_CACHE")
                         or pathlib.Path(__file__).resolve().parents[2] / ".http-cache")
_stats = {"hit": 0, "miss": 0, "stored": 0, "nostore": 0}


def cache_stats():
    """-> (304s, full bodies, entries written). Reset per run by the caller."""
    return dict(_stats)


def _slot(url):
    return CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest()[:32] + ".bin")


def _read_slot(path):
    try:
        raw = path.read_bytes()
        head, body = raw.split(b"\n\n", 1)
        return json.loads(head.decode()), body
    except Exception:
        return None, None


def _write_slot(path, meta, body):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(json.dumps(meta).encode() + b"\n\n" + body)
        os.replace(tmp, path)
        _stats["stored"] += 1
    except Exception:
        pass          # a cache that cannot be written must never fail a run


def fetch(url, headers=None, data=None, tries=3, backoff=5, timeout=30, opener=None,
          cache=False):
    """GET (or POST when `data` is given) with retry. -> bytes.

    `opener` lets a cookie-session adapter (BioRex) retry a single request
    without redoing the whole session dance. Retries every exception the same
    way the per-adapter get() loops already do; an HTTP 4xx is rare enough
    here that distinguishing it is not worth the branch.

    `cache=True` makes it a conditional GET: a stored ETag or Last-Modified goes back
    as If-None-Match / If-Modified-Since, and a 304 returns the stored body without
    the server sending it again. A response marked no-store or no-cache is never
    written to disk, and one with no validator is not either -- there would be
    nothing to revalidate it with.

    Measured 2026-08-30, across every endpoint this pipeline reads: only Cinema
    Orion sends a validator at all, so today this saves about one request per run
    rather than the bulk of them. It is here because it is the correct way to ask,
    it costs nothing when the origin offers nothing, and a provider that starts
    sending ETags is picked up without another change.

    Never enable it on a POST -- the response is not addressed by the URL alone,
    so a slot would collide across different request bodies.
    """
    if data is not None:
        cache = False
    slot = _slot(url) if cache else None
    meta, cached_body = _read_slot(slot) if cache else (None, None)

    hdrs = dict(headers or {"user-agent": UA})
    if meta and cached_body is not None:
        if meta.get("etag"):
            hdrs["if-none-match"] = meta["etag"]
        if meta.get("last_modified"):
            hdrs["if-modified-since"] = meta["last_modified"]

    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs)
            op = opener.open if opener is not None else urllib.request.urlopen
            with op(req, timeout=timeout) as r:
                body = r.read()
                if cache:
                    _stats["miss"] += 1
                    cc = (r.headers.get("Cache-Control") or "").lower()
                    et = r.headers.get("ETag")
                    lm = r.headers.get("Last-Modified")
                    # Storing a body the origin marked no-store is the thing this whole
                    # change exists to avoid. eTiketti and Nexxo both send it; measured
                    # 2026-08-30. Without a validator there is nothing to revalidate
                    # with either, so the slot would only ever grow.
                    if ("no-store" in cc or "no-cache" in cc):
                        _stats["nostore"] += 1
                    elif et or lm:
                        _write_slot(slot, {"etag": et, "last_modified": lm}, body)
                return body
        except urllib.error.HTTPError as e:
            if e.code == 304 and cached_body is not None:
                _stats["hit"] += 1
                return cached_body
            last = e
            if n + 1 < tries:
                time.sleep(backoff * (n + 1))
        except Exception as e:
            last = e
            if n + 1 < tries:
                time.sleep(backoff * (n + 1))
    raise last


# Per-site ceiling on secondary page fetches -- the film pages an adapter reads after
# the listing tells it what is showing. Those loops iterate whatever the listing
# contains, so the request count is bounded in practice by how many films a cinema is
# showing (15-31 today) and unbounded in principle: a listing that ever returned
# thousands would be fetched in full, politely paced and still thousands of requests at
# someone else's expense.
#
# 120 is roughly four times the largest real figure. Truncating costs metadata, never
# showtimes -- those come from the listing, which is one request -- so a film past the
# cap simply shows without runtime, genres or synopsis until the next run. That is the
# right way round, and it is logged loudly because a cap that trims silently would read
# as complete data.
PAGE_BUDGET = int(os.environ.get("KINO_PAGE_BUDGET") or 120)


def capped(items, label, limit=None):
    """Trim an *enrichment* loop to the budget. -> list, logged once if it trims.

    Only for pages that add metadata to showtimes already parsed from a listing --
    BioRex's and Engel's film pages. A film past the cap shows without runtime,
    genres or synopsis until the next run, which is a fair trade for a bounded
    request count.

    Not for a loop that produces the showtimes themselves; use budget_or_raise.
    """
    items = list(items)
    limit = PAGE_BUDGET if limit is None else limit
    if len(items) > limit:
        print(f"[{label}] page budget: {len(items)} film pages wanted, fetching {limit}, "
              f"{len(items) - limit} skipped this run -- those films lose metadata only")
        return items[:limit]
    return items


def budget_or_raise(items, label, limit=None):
    """Same ceiling, for a loop whose pages carry the schedule itself. -> list.

    eTiketti puts the screenings on the film pages, so trimming that loop does not
    cost metadata, it drops showtimes -- and a venue that publishes half its day is
    worse than one that publishes nothing, because run.py keeps the previous file
    when a site fails and the health line then ages honestly. Caught by testing the
    cap rather than by reading it: with the budget forced to 2, Kinopalatsi Kotka
    went to zero showtimes and Trio 123 to 6 of 34, and both would have shipped.
    """
    items = list(items)
    limit = PAGE_BUDGET if limit is None else limit
    if len(items) > limit:
        raise RuntimeError(
            f"{label}: {len(items)} film pages to fetch, over the {limit} budget. "
            "These pages carry the showtimes, so a partial fetch would publish a "
            "partial schedule; failing instead keeps the last good data.")
    return items


def write_text_atomic(path, text):
    """Write via a sibling .tmp then os.replace, atomic on the same filesystem.

    On Actions a torn write is harmless (ephemeral runner), but the local
    wrapper writes into a checked-out repo, so a run killed mid-write -- closed
    laptop, cancel-in-progress -- would leave truncated JSON that the next
    run's `git add data` commits. .tmp is gitignored for the same reason.
    """
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path, obj, **dumps_kw):
    write_text_atomic(path, json.dumps(obj, ensure_ascii=False, **dumps_kw))
