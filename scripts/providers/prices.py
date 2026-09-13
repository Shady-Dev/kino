"""Per-screening prices from the public ticket page a showtime already links to.

A listing rarely carries a price; the page a visitor lands on when tapping the showtime
usually does, as a table of ticket categories. This module is the shared side step:
after an adapter has built its rows, `enrich()` reads at most FETCH_MAX of those pages a
run, one GET each, sequential and `sleep` apart, and puts the price the adapter's parser
returns on every row that links to that page. Nothing here can fail a schedule: a page
that cannot be read leaves the price "" and the showtime is published without it.

The cache at data/prices-{provider}.json maps a screening key (the URL's last path
segment) to {"price", "at"}. It is pruned to the keys on the listing, so it cannot grow
past the programme, and rewritten only when it changed. A key is read again after TTL_H,
so a price change reaches the site within that time and a screening is otherwise read
once for its life on the listing. Never-read keys go first, then the oldest. Three
consecutive failures end the pass for the run; a failed page is not cached, so it is
retried next run, while a page with no usable price is cached as "" and waits the TTL.

Parsers are the adapters' own (`riviera.ordinary_price`, `regina.ordinary_price`,
`vista.ordinary_price`): each names the ordinary ticket category explicitly, so a
wheelchair, concession or member ticket listed first never becomes the advertised price,
and no row or two rows with different amounts is "" -- unknown, never zero.
"""
import datetime
import json
import os
import pathlib
import time

from common import UA, fetch, write_json

TTL_H = float(os.environ.get("KINO_PRICE_TTL_H") or 48)
FETCH_MAX = int(os.environ.get("KINO_PRICE_MAX") or 40)
FAIL_STOP = 3
OUT = pathlib.Path("data")


def fmt(amount):
    """"20,00" -> "20€", "12,50" -> "12.5€": eTiketti's shape, which the client's
    priceLabel() and the pages' price_label() already render. -> "" for zero or junk."""
    try:
        v = float(str(amount).replace(",", ".").strip())
    except ValueError:
        return ""
    if v <= 0:
        return ""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s + "€"


def one_amount(amounts):
    """The price when the ordinary rows agree -> fmt() of it, else ""."""
    norm = {str(a).replace(",", ".").strip() for a in amounts}
    return fmt(norm.pop()) if len(norm) == 1 else ""


def _age_h(entry, now):
    try:
        at = datetime.datetime.fromisoformat(entry["at"])
    except (KeyError, TypeError, ValueError):
        return float("inf")
    return (now - at).total_seconds() / 3600


def key_of(url, prefix):
    """The screening key of a ticket URL under `prefix` -> str, or "" when not one."""
    if not (prefix and url and url.startswith(prefix)):
        return ""
    tail = url[len(prefix):].split("?")[0].split("#")[0].strip("/")
    return tail.rsplit("/", 1)[-1] if tail else ""


def enrich(shows, *, provider, prefix, parse, referer="", path=None, now=None,
           sleep=1.0, limit=None, headers=None):
    """Put each screening's price on its rows. -> counts dict.

    `prefix` is the ticket-page URL prefix a row's `url` must carry to be asked;
    `parse(page_html)` -> "20€" or "". `headers` replaces the default GET headers.
    """
    path = pathlib.Path(path or (OUT / f"prices-{provider}.json"))
    limit = FETCH_MAX if limit is None else limit
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    try:
        old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(old, dict):
            old = {}
    except (OSError, ValueError):
        old = {}

    by_key = {}
    for s in shows:
        k = key_of(s.get("url") or "", prefix)
        if k:
            by_key.setdefault(k, []).append(s)
    cache = {k: v for k, v in old.items() if k in by_key and isinstance(v, dict)}

    due = [k for k in by_key if k not in cache or _age_h(cache[k], now) >= TTL_H]
    due.sort(key=lambda k: (k in cache, cache.get(k, {}).get("at", ""), k))
    todo, deferred = due[:limit], max(0, len(due) - limit)
    if deferred:
        print(f"[{provider}] prices: {len(due)} ticket pages due, reading {limit}, "
              f"{deferred} wait for the next run")

    hdrs = headers or {"user-agent": UA, "accept": "text/html"}
    if referer and "referer" not in hdrs:
        hdrs = dict(hdrs, referer=referer)
    fetched = failed = streak = 0
    for n, k in enumerate(todo):
        if streak >= FAIL_STOP:
            deferred += 1
            continue
        if n:
            time.sleep(sleep)
        url = by_key[k][0]["url"]
        try:
            page = fetch(url, headers=hdrs, tries=2, timeout=20).decode("utf-8", "replace")
        except Exception as e:                     # noqa: BLE001 -- the price is optional
            failed += 1
            streak += 1
            print(f"[{provider}] price page {k}: {type(e).__name__}: {str(e)[:80]}")
            continue
        streak = 0
        fetched += 1
        cache[k] = {"price": parse(page) or "", "at": now.isoformat()}

    for k, group in by_key.items():
        price = (cache.get(k) or {}).get("price") or ""
        for s in group:
            s["price"] = price

    if cache != old:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, dict(sorted(cache.items())), indent=1)
    return {"screenings": len(by_key),
            "priced": sum(1 for k in by_key if (cache.get(k) or {}).get("price")),
            "fetched": fetched, "reused": len(by_key) - len(due),
            "unknown": sum(1 for k in by_key if k in cache and not cache[k].get("price")),
            "failed": failed, "deferred": deferred}


def report(provider, st):
    """The one log line a run leaves about prices."""
    print(f"[{provider}] prices: {st['screenings']} screenings, {st['priced']} priced, "
          f"{st['fetched']} pages read, {st['reused']} reused, {st['unknown']} without an "
          f"ordinary ticket, {st['failed']} failed, {st['deferred']} deferred")


def run(shows, **kw):
    """enrich() that cannot raise: a failure logs and leaves the prices as they were."""
    provider = kw.get("provider", "?")
    try:
        report(provider, enrich(shows, **kw))
    except Exception as e:                         # noqa: BLE001 -- the price is optional
        print(f"[{provider}] prices skipped: {type(e).__name__}: {str(e)[:80]}")
