"""Shared HTTP fetch with retry for provider adapters.

Named common, not http: run.py and fetch_data.py put this directory first on sys.path,
and a local http.py would shadow the stdlib package urllib.request imports.

tries=3 with backoff*n sleeps: one transient 502 or connection reset no longer counts as
a site failure, and the worst case is 3*backoff seconds of extra wait per request.
"""
import datetime
import email.utils
import hashlib
import json
import os
import pathlib
import threading
import time
import typing
import urllib.error
import urllib.parse
import urllib.request

# Identifies the reader. Every adapter used to send a Chrome string, which is an
# automated pipeline claiming to be a person at a keyboard -- the one thing in here a
# cinema had no way to check for itself. Probed against all eleven providers on
# 2026-08-30 before changing it: every one answers this byte-for-byte identically to the
# Chrome string, so honesty costs nothing. If a provider ever refuses it, record the
# reading in docs/research/ticketing-platforms.md and keep the browser string for that one
# host deliberately, rather than quietly re-disguising the whole pipeline.
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

# run.py fetches independent hosts in parallel, so every counter in this module is now
# read-modify-written from several threads, and these counters are what the committed
# run-*.log offers as evidence for how the pipeline fetched. A wrong number there is
# worse than a slow run, so the arithmetic is made correct by construction rather than
# left to the interpreter.
#
# Measured rather than assumed: on CPython 3.14 with the GIL the lock changes nothing
# observable. `_stats["miss"] += 1` compiles to a subscript, an
# add and a store, and the eval loop does not offer to switch threads inside that stretch
# -- eight threads and 1.6 million increments lose exactly zero. The same is true of the
# Retry-After decision, whose read of `waited` and charge against it are separated by no
# call and no jump. So this is not a fix for an observed miscount.
#
# It is here because that behaviour is an implementation accident, not a language
# guarantee, and it is not true of a free-threaded build -- which 3.14 ships and which
# nothing in this repo pins against. The lock also lets the Retry-After ceiling be a
# decision rather than three separate reads: see fetch(). `_diag_seen` shares it so that
# its check-then-add cannot print one host's refusal twice.
_lock = threading.Lock()


def _bump(counter, key, by=1):
    with _lock:
        counter[key] += by


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

# Every response body is read in bounded chunks, never with a bare read(): these are
# third parties, and a broken or compromised origin answering with gigabytes would
# otherwise sit in memory in full before any parser or Pillow ever saw it. Not a
# measured figure the way PAGE_BUDGET is -- the sizes that would need measuring are the
# upstreams' to change -- but the largest body this pipeline legitimately reads is a
# poster source image at a few MB, so 20 MB is generous headroom, not a boundary any
# real response has approached. A Content-Length past the cap is refused before the
# body is read; the chunked loop below enforces the cap whether or not the header was
# sent, since the header is only the origin's claim.
MAX_BODY = int(os.environ.get("KINO_MAX_BODY") or 20_000_000)


class Show(typing.TypedDict):
    """One screening as every adapter publishes it and as run.py, synmerge and the client
    read it. Plain dicts stay the runtime shape; this is the written contract, and
    `SHOW_KEYS` is what tests/test_show_contract.py holds each adapter to.

    Every key is required and a value the adapter cannot fill is "" (or False). Measured
    2026-09-14 across the twelve adapters: eleven emitted all seventeen and BioRex emitted
    no `price`, which the client tolerated only because priceLabel reads `r.price || ''`.
    Every frontend bug on the day multi-provider landed came from a field only Finnkino
    populated, so a key present with an empty value is the rule and a missing key is not.
    An adapter may add keys of its own (`_syn`, `age`, `movieUrl`); a TypedDict does not
    validate at runtime, so the test is the check, not this class.
    """
    eventId: str        # the provider's film id, scoped to its site; the film key in films.json
    title: str          # verbatim, the key for normTitle(), films-extra.json, tmdb-aliases.json
    original: str
    len: str
    rating: str
    genres: str
    method: str         # strand, format or language tag shown on the stub
    theatre: str
    aud: str            # room, verbatim: it is what the ticket prints
    start: str          # ISO 8601 with offset, Europe/Helsinki
    url: str            # absolute http(s); the client runs it through safeUrl()
    img: str
    lang: str
    soldOut: bool
    price: str          # "8€", "alkaen 10€", "Vapaa pääsy", or ""
    provider: str       # registry id
    venue: str          # a venue id the site's registry entry lists


SHOW_KEYS = tuple(Show.__annotations__)


def check_shows(per_venue, label, venue_ids=()):
    """Refuse an adapter's result that does not meet `Show`. -> None, or raises RuntimeError.

    run.py calls this on what fetch_site returned, before anything is written, so a show
    missing a key or carrying the wrong type fails its site the way a parse error does:
    the previous files stay, the health line ages, and the log names the venue and the
    key. A TypedDict checks nothing at runtime; this is the check. Keys beyond the
    contract are allowed: adapters carry `_syn` for synmerge and `age`, `movieUrl` and
    `year` as documented extras, and the enrichment pass adds its own later.

    `venue_ids` is the site's venue list when the caller has one: a show filed under a
    venue the site does not list would be written to a file the picker never links.
    """
    for vid, shows in per_venue.items():
        if venue_ids and vid not in venue_ids:
            raise RuntimeError(f"{label}: shows for venue {vid!r}, which the site does not list")
        for s in shows:
            for k, t in Show.__annotations__.items():
                if k not in s:
                    raise RuntimeError(f"{label}: venue {vid}: a show has no {k!r} "
                                       f"(title {s.get('title')!r})")
                if not isinstance(s[k], t):
                    raise RuntimeError(f"{label}: venue {vid}: {k!r} is "
                                       f"{type(s[k]).__name__}, not {t.__name__} "
                                       f"(title {s.get('title')!r})")
            if not s["start"] or not s["venue"] or s["venue"] != vid:
                raise RuntimeError(f"{label}: venue {vid}: a show with start {s['start']!r} "
                                   f"filed under venue {s['venue']!r} (title {s['title']!r})")


class EmptyProgramme(Exception):
    """An adapter reached a site, read its listing, and there were no films on it.

    A whole site parsing zero showtimes fails the run, and that has to stay true: it is
    the only thing that catches a parse which broke silently and would otherwise leave
    old data ageing with no signal. But some cinemas genuinely publish nothing for a
    week. Eight sites here are a single small venue -- K-Kino runs 3 showtimes, Kino
    Saimaa 2 -- so "empty" stopped being hypothetical the day the eTiketti sweep landed.

    The distinction an adapter can make, and run.py cannot, is *what the listing said*.
    Raise this only on **positive evidence that the upstream said it has nothing on** --
    an empty-state element the template renders in place of its films, a payload that
    answered in the expected schema with an empty collection. A listing that still lists
    films while the parse yields no showtimes is the broken case and must keep failing,
    and an unreachable listing raises its own error long before this.

    **"My parser found nothing" is not that evidence**, and reading it as such is the
    trap this class creates. Zero matches proves only that one regex or one key lookup
    came back empty, which is exactly what a markup or schema change upstream produces --
    while the page is still full of films. Inferring emptiness from it converts a parser
    regression into a soft ageing signal: exit 0, stale data preserved, nothing red, and
    the first symptom hours later on the health line. Every adapter raising this must
    therefore check something it did *not* use to find the films.

    Nothing is muted by configuration on purpose: a per-site "allow empty" flag would
    switch the check off permanently for the one site most likely to need it, which is
    the hole this is meant to avoid rather than open.
    """


def cache_stats():
    """-> (304s, full bodies, entries written). Reset per run by the caller."""
    with _lock:
        return dict(_stats)


def throttle_stats():
    """-> how often an upstream asked us to slow down, and what that cost.

    `asked` counts Retry-After responses, `waited` the seconds sat out,
    `refused` the ones whose ask was past a ceiling and so were not retried at all.
    All zero on a normal run, which is why run.py prints the line only when it is not.
    """
    with _lock:
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
    with _lock:
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


class BodyTooLarge(Exception):
    """A response body passed the max_bytes cap. Deterministic, so never retried:
    asking again downloads the same oversize answer at both ends' expense."""


def _read_capped(r, url, limit):
    """Read a response body, refusing past `limit` bytes. -> bytes."""
    cl = (r.headers.get("Content-Length") or "").strip()
    if cl.isdigit() and int(cl) > limit:
        raise BodyTooLarge(f"{url}: Content-Length {cl} is past the {limit}-byte cap")
    chunks, total = [], 0
    while True:
        chunk = r.read(65536)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > limit:
            raise BodyTooLarge(f"{url}: body passed the {limit}-byte cap "
                               f"({total}+ bytes read)")
        chunks.append(chunk)


def _write_slot(path, meta, body):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # The temp name carries the writing thread, because the slot name is a hash of
        # the URL and two threads asking the same URL at once would otherwise write the
        # same `<hash>.tmp` -- one truncating the other's bytes and both then renaming
        # the result over the slot. Unlikely across different sites and not worth
        # leaving to luck, since the loser is a corrupt cache entry that is served as a
        # cached body on the next run.
        tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            tmp.write_bytes(json.dumps(meta).encode() + b"\n\n" + body)
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)     # a unique name would otherwise accumulate
            raise
        _bump(_stats, "stored")
    except Exception:
        pass          # a cache that cannot be written must never fail a run


def fetch(url, headers=None, data=None, tries=3, backoff=5, timeout=30, opener=None,
          cache=False, max_bytes=None):
    """GET (or POST when `data` is given) with retry. -> bytes.

    `max_bytes` caps the response body, MAX_BODY by default. Past it the read stops
    and BodyTooLarge is raised without a retry.

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
    limit = MAX_BODY if max_bytes is None else max_bytes
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
                body = _read_capped(r, url, limit)
                if cache:
                    _bump(_stats, "miss")
                    cc = (r.headers.get("Cache-Control") or "").lower()
                    et = r.headers.get("ETag")
                    lm = r.headers.get("Last-Modified")
                    # Storing a body the origin marked no-store is the thing this whole
                    # change exists to avoid. eTiketti and Nexxo both send it; measured
                    # 2026-08-30. Without a validator there is nothing to revalidate
                    # with either, so the slot would only ever grow.
                    if ("no-store" in cc or "no-cache" in cc):
                        _bump(_stats, "nostore")
                    elif et or lm:
                        _write_slot(slot, {"etag": et, "last_modified": lm}, body)
                return body
        except urllib.error.HTTPError as e:
            # An HTTPError *is* the response, and it holds its socket until the garbage
            # collector gets to it -- 24 ResourceWarnings in a suite run, and on a long
            # run against a host that is refusing everything, that many sockets waiting
            # on a collection nobody scheduled. Closed here because nothing ever wants
            # the body: `code`, `reason` and `headers` all survive the close, the retry
            # logic below reads only those, and `raise last` hands the caller an
            # exception rather than a stream. close() is idempotent, so the paths that
            # re-raise this same object cost nothing.
            e.close()
            if e.code == 304 and cached_body is not None:
                _bump(_stats, "hit")
                return cached_body
            last = e
            # 429 and 503 are the two codes RFC 9110 lets carry Retry-After, and both
            # mean "not now" rather than "never". Wait the stated time instead of ours.
            hh = getattr(e, "headers", None)
            wait = (_retry_after(hh.get("Retry-After"))
                    if e.code in (429, 503) and hh is not None else None)
            if wait is not None:
                # Counted, checked against the budget and charged to it in one step. The
                # budget bounds the whole process, so with hosts running in parallel a
                # check that read `waited` and charged it later would let several threads
                # each pass the same remaining budget and then all sleep against it. The
                # seconds are reserved before the sleep rather than after, and only when
                # there is a retry left to sleep for -- which is what the sequential code
                # did too, since the last attempt never slept.
                sleeping = n + 1 < tries
                with _lock:
                    _throttle["asked"] += 1
                    over = (wait > RETRY_AFTER_MAX
                            or _throttle["waited"] + wait > RETRY_AFTER_BUDGET)
                    if over:
                        _throttle["refused"] += 1
                    elif sleeping:
                        _throttle["waited"] += wait
                if over:
                    _log_refusal(e, url, n + 1)
                    raise
            if n + 1 < tries:
                time.sleep(backoff * (n + 1) if wait is None else wait)
        except BodyTooLarge:
            raise
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

# How far from today a resolved date may fall. Wider than any programme these cinemas
# publish, tight enough that a mistyped weekday cannot put a screening a year out. Asymmetric
# on purpose: a stale row in the past is hidden by the client, a phantom row in the future is
# shown.
MAX_AHEAD = 300
MAX_BEHIND = 180

# Finnish weekday names as the cinema sites write them, full and abbreviated, keyed on the
# first two letters because that is unambiguous across all seven.
FI_WEEKDAYS = {"ma": 0, "ti": 1, "ke": 2, "to": 3, "pe": 4, "la": 5, "su": 6}


def weekday_index(name):
    """`Tiistai`, `ti`, `TI` -> 1 (Monday is 0). -> int, or None for anything else."""
    key = (name or "").strip().lower()[:2]
    return FI_WEEKDAYS.get(key)


def resolve_year(day, month, today, weekday=None):
    """A `DD.MM.` with no year -> the year it means. -> int, or None.

    **A weekday selects uniquely within the assumed window. It does not establish the
    intended date.** Inside Y-1, Y, Y+1 exactly one candidate can carry a given weekday:
    consecutive years shift it by one or two days and the whole window by two or three,
    never zero, checked over 2000-2100 across 4,800 windows. That makes the selection
    unambiguous *given the window*. It does not make it true. A page left up for four years,
    or one with a mistyped weekday, is still resolved to one of these three, and neither
    this function nor the caller can tell that from the page.

    So the answer is bounded as well as selected. A candidate further than `MAX_BEHIND`
    days back or `MAX_AHEAD` days forward is refused and returns None, because the failure
    that matters is a wrong weekday quietly producing a screening roughly a year out, where
    nothing downstream filters it: a stale row in the past is harmless and the client hides
    it, while a phantom row in the future is shown to readers. The bounds are deliberately
    wider than anything these cinemas publish (the widest seen on 2026-09-15 was 88 days
    ahead) and far tighter than the 365 a weekday slip would need.

    A weekday matching **no** candidate year returns None for the same reason: the page is
    contradicting itself, which is a slip or a template change, and `tmb.py` already makes
    that choice. Only three of the seven weekdays can be right for any given day and month.

    Without a weekday it falls back to nearest occurrence, described below, and that is
    bounded too.

    Several small cinemas publish a day and a month and no year at all (Kino Vaakuna,
    Kino Kirkkonummi, Kuvakukko). The year is missing rather than abbreviated, so it has
    to be resolved, and every way of doing that is a guess about which occurrence is
    meant. This is the narrowest one that survives the case the naive rules fail on.

    **Nearest occurrence, ties to the future.** The candidates are the same day and month
    in `today.year - 1`, `today.year` and `today.year + 1`, and the one closest to `today`
    wins. That bounds the answer to about six months either side of today, which is the
    point: a rule that only ever looks forward turns a stale row into a date a year out.
    On 2 January a page still showing `28.12.` means five days ago, not in eleven months;
    on 28 December a page showing `05.01.` means in eight days, not eleven months back.
    Both fall out of "nearest" without a special case.

    A date in the past is not discarded here. The caller publishes it and the client
    filters past screenings already, which is the honest division: this function answers
    which year, not whether to show it.

    Returns None when no candidate year holds that day and month at all, which is 29.02.
    in a three-year window with no leap year in it. The caller skips such a row rather
    than moving it to a date the page did not publish.
    """
    best = None
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            when = datetime.date(year, month, day)
        except ValueError:
            continue
        if not -MAX_BEHIND <= (when - today).days <= MAX_AHEAD:
            continue                     # implausible; see the bound above
        if weekday is not None:
            if when.weekday() == weekday:
                return year
            continue
        # Ties go to the future: a date equally far either way is the coming one.
        key = (abs((when - today).days), 0 if when >= today else 1)
        if best is None or key < best[0]:
            best = (key, year)
    return best[1] if best else None
