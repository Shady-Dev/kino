"""Shared HTTP fetch with retry for provider adapters.

Named common, not http: run.py and fetch_data.py put this directory first on
sys.path, and a local http.py would shadow the stdlib package urllib.request
itself imports (http.client), breaking every fetch in the pipeline.

One transient 502 or connection reset used to count as total site failure for
the adapters without their own retry loop, and the next cron is four hours
away. tries=3 with backoff*n sleeps means a worst case of 3*backoff seconds of
extra wait per request, so a dead upstream cannot stall the workflow.
"""
import datetime
import email.utils
import hashlib
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
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

# A 429 or 503 with Retry-After is the only case where an upstream states its own
# terms, and the retry loop below used to ignore them: a provider asking for 60
# seconds got three more requests inside 15, on our schedule rather than its own.
# Kinoset has answered 403 under load before, so this is not hypothetical.
#
# Both ceilings exist because "sleep for as long as you are told" hands a stranger
# the ability to stall the pipeline. RETRY_AFTER_MAX bounds one wait,
# RETRY_AFTER_BUDGET bounds the whole process, so a host that 429s every request
# cannot turn one run into an all-day one. Past either, the request fails instead of
# waiting: the next run is four hours away, run.py keeps the previous file, and the
# health line ages honestly -- which is a better answer than more requests at a host
# that just said no.
RETRY_AFTER_MAX = int(os.environ.get("KINO_RETRY_AFTER_MAX") or 120)
RETRY_AFTER_BUDGET = int(os.environ.get("KINO_RETRY_AFTER_BUDGET") or 300)
_throttle = {"asked": 0, "waited": 0.0, "refused": 0}


class EmptyProgramme(Exception):
    """An adapter reached a site, read its listing, and there were no films on it.

    A whole site parsing zero showtimes fails the run, and that has to stay true: it is
    the only thing that catches a parse which broke silently and would otherwise leave
    old data ageing with no signal. But some cinemas genuinely publish nothing for a
    week. Eight sites here are a single small venue -- K-Kino runs 3 showtimes, Kino
    Saimaa 2 -- so "empty" stopped being hypothetical the day the eTiketti sweep landed.

    The distinction an adapter can make, and run.py cannot, is *what the listing said*.
    Raise this only after the listing was fetched and parsed successfully and contained
    no films at all. A listing that still lists films while the parse yields no
    showtimes is the broken case and must keep failing, and an unreachable listing
    raises its own error long before this.

    Nothing is muted by configuration on purpose: a per-site "allow empty" flag would
    switch the check off permanently for the one site most likely to need it, which is
    the hole this is meant to avoid rather than open.
    """


def cache_stats():
    """-> (304s, full bodies, entries written). Reset per run by the caller."""
    return dict(_stats)


def throttle_stats():
    """-> how often an upstream asked us to slow down, and what that cost.

    `asked` counts Retry-After responses, `waited` the seconds actually sat out,
    `refused` the ones whose ask was past a ceiling and so were not retried at all.
    All zero on a normal run, which is why run.py prints the line only when it is not.
    """
    return dict(_throttle)


def _retry_after(value):
    """Seconds to wait, from a Retry-After header. -> float, or None if unusable.

    RFC 9110 allows delta-seconds or an HTTP-date and both appear in the wild. A date
    already in the past means "now", not a negative sleep. None means the header was
    absent or unparseable, which leaves the caller on its own fixed backoff -- a
    malformed header is not a reason to give a provider three fast retries.
    """
    if not value:
        return None
    v = value.strip()
    if v.isdigit():
        return float(v)
    try:
        when = email.utils.parsedate_to_datetime(v)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return max(0.0, (when - datetime.datetime.now(datetime.timezone.utc)).total_seconds())


# Which layer refused, on the way out of a request that is being given up on. A 403 in
# a committed log read `HTTP Error 403: Forbidden` and nothing else, which is the same
# line whether an edge blocked the address or the origin was throttling -- and those two
# want opposite responses. The block is gone by the time anyone reads the log: Kinoset
# refused all three venues at 08:31 UTC on 2026-08-30 and served them again at 09:14, so
# the run is the only witness there will ever be.
#
# `Server: cloudflare` with a CF-Ray is a decision at the edge. That does not clear by
# waiting, and the answer is to move the endpoint to the local half the way Finnkino
# already is. An origin server with neither is the application rate-limiting, which is
# what Kinoset has done before and which clears on its own -- leave it to the next cron.
#
# **Headers only, never the body.** `run-*.log` is committed to a public repo and a third
# party's error page carries whatever they ship to visitors; that is the raw-dump rule,
# and one such dump already put someone else's API key in here. These three are short,
# fixed, and about the refusal rather than about their stack.
DIAG_HEADERS = ("Server", "CF-Ray", "Retry-After")
_diag_seen = set()


def _server_hint(e):
    """-> 'Server: cloudflare; CF-Ray: ...', or '' if the response said none of them."""
    hh = getattr(e, "headers", None)
    if hh is None:
        return ""
    return "; ".join(f"{k}: {(hh.get(k) or '').strip()[:80]}"
                     for k in DIAG_HEADERS if (hh.get(k) or "").strip())


def _log_refusal(e, url, attempts):
    """Name the refusing layer once, the first time this host refuses this way.

    Deduplicated because `mirror_posters` calls fetch once per poster and has had 185
    failures against one host in a single run; a line each would bury the run's own
    summary, which is the thing that made that run unreadable in the first place. The
    ray id is unique per request by design, so it cannot be part of the key -- presence
    is what identifies the layer, and the line carries the first value seen.
    """
    hint = _server_hint(e)
    if not hint:
        return
    host = urllib.parse.urlsplit(url).netloc
    key = (host, e.code, (e.headers.get("Server") or "").strip(),
           bool((e.headers.get("CF-Ray") or "").strip()))
    if key in _diag_seen:
        return
    _diag_seen.add(key)
    print(f"[http] {e.code} from {host}, gave up after {attempts} attempt(s) -- {hint}")


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
    without redoing the whole session dance. Retries every exception on
    backoff*n the way the per-adapter get() loops already do, with one
    exception: a 429 or 503 carrying Retry-After is retried on the interval the
    upstream named, and is not retried at all when that interval is past
    RETRY_AFTER_MAX or would take the run past RETRY_AFTER_BUDGET.

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

    When a request is given up on, one `[http]` line names the refusing layer from a
    fixed set of response headers -- see DIAG_HEADERS. Never the body.
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
            # 429 and 503 are the two codes RFC 9110 lets carry Retry-After, and both
            # mean "not now" rather than "never". Wait the stated time instead of ours.
            hh = getattr(e, "headers", None)
            wait = (_retry_after(hh.get("Retry-After"))
                    if e.code in (429, 503) and hh is not None else None)
            if wait is not None:
                _throttle["asked"] += 1
                if (wait > RETRY_AFTER_MAX
                        or _throttle["waited"] + wait > RETRY_AFTER_BUDGET):
                    _throttle["refused"] += 1
                    _log_refusal(e, url, n + 1)
                    raise
            if n + 1 < tries:
                if wait is None:
                    time.sleep(backoff * (n + 1))
                else:
                    _throttle["waited"] += wait
                    time.sleep(wait)
        except Exception as e:
            last = e
            if n + 1 < tries:
                time.sleep(backoff * (n + 1))
    if isinstance(last, urllib.error.HTTPError):
        _log_refusal(last, url, tries)
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
