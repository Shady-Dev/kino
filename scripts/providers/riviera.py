"""Riviera Cinemas (Helsinki: Kallio, Punavuori). WordPress admin-ajax, no auth.

  POST /wp/wp-admin/admin-ajax.php
       action=filter_movies&date=&movie=&area=1040&singlemovie=&initial=1
  -> {"success":true,"data":{"movies":"<ul class=movielist>…</ul>"}}

One request returns every showtime for both venues across the whole published window,
so the adapter splits by the `location` field ("Kallio, Sali 1") rather than by request.

Parameterised by base URL: every field the endpoint needs lives on the site dict, so
another cinema on the same WordPress theme (Gilda) is a SITES entry with no new parser.
Confirm the ajax action matches before adding one.

Prices (2026-09-13): the listing carries none. Each screening's public ticket page,
`{tickets}{id}`, prints a `table.showPrices-table` with one row per ticket category, and
the ordinary seat is "Sohvapaikka tai Nojatuolipaikka". That row's amount is the price
shown; a page without exactly one such row publishes no price. See enrich_prices().
"""
import datetime, html as html_mod, json, os, pathlib, re, time, urllib.parse
from zoneinfo import ZoneInfo

from common import fetch, write_json

FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

SITE = {"provider": "riviera", "label": "Riviera",
        "base": "https://www.rivieracinemas.fi",
        "ajax": "/wp/wp-admin/admin-ajax.php",
        "listing": "/elokuvat/",
        # Where the site's own "Valitse näytös" button sends a visitor. The
        # listing carries no link at all: the button holds the screening id in
        # data-movieid and the theme's app.js sets the ticket iframe to
        # {tickets}{id}. Publishing that URL is what a click does, one request per run
        # and none per screening.
        "tickets": "https://tickets.rivieracinemas.fi/websales/show/",
        # `area` is ignored by their backend (1040 all / 1024 Kallio / 1039 Punavuori),
        # which is why venues carry a `match` against the location field instead.
        "area": "1040",
        "venues": [
    {"id": "rv-kallio",    "match": "kallio",    "name": "Riviera Kallio",
     "short": "Kallio",    "city": "Helsinki"},
    {"id": "rv-punavuori", "match": "punavuori", "name": "Riviera Punavuori",
     "short": "Punavuori", "city": "Helsinki"},
]}
SITES = [SITE]

ITEM_RE = re.compile(r'<li class="movielist__item single-show[^"]*">(.*?)</li>', re.S)
DATE_RE = re.compile(r'class="date">\s*([^<]+?)\s*<')
TIME_RE = re.compile(r'class="time">\s*(\d{1,2})[:.](\d{2})')
LOC_RE = re.compile(r'class="location">\s*([^<]+?)\s*<')
TITLE_RE = re.compile(r'class="movielist__item__title title">\s*([^<]+?)\s*<')
SEATS_RE = re.compile(r"Varatut paikat:\s*(\d+)\s*/\s*(\d+)")
LEN_RE = re.compile(r"Kesto:\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*min)?")
# The actions cell, and the two shapes a screening link takes inside it. An anchor wins
# when the theme ships one, because it is the site's own URL for that screening including
# any query and fragment; the button is what it ships today. Scoped to the cell so a link
# elsewhere in the row (a title, a trailer) cannot answer for the screening.
ACTIONS_RE = re.compile(r'<div class="movielist__item__actions.*?</div>', re.S)
ACTION_HREF_RE = re.compile(r'<a\b[^>]*\bhref="([^"]*)"', re.S)
SHOW_BTN_RE = re.compile(r'<button\b[^>]*\bshow_tickets\b[^>]*>', re.S)
MOVIEID_RE = re.compile(r'\bdata-movieid="(\d+)"')
DISABLED_RE = re.compile(r"<button[^>]*\bdisabled\b")
TAGS_RE = re.compile(r"<[^>]+>")
# "To 27.8.2026" -> day, month, year
DMY_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


def _txt(x):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", x or ""))).strip()


def show_url(block, listing="", base="", tickets=""):
    """The URL for one screening: the action cell's own link, else its ticket page.

    An anchor is resolved against `base` with urljoin, so a relative href keeps its
    query and fragment instead of being dropped for not starting with http. That was the
    old rule, and every Riviera showtime published `/elokuvat/` because of it. With no
    anchor, the button's data-movieid is the screening id the theme opens as
    `{tickets}{id}`. With neither, the listing, which at least names the cinema.
    """
    cell = ACTIONS_RE.search(block)
    cell = cell.group(0) if cell else ""
    a = ACTION_HREF_RE.search(cell)
    if a and a.group(1).strip():
        return urllib.parse.urljoin(base or listing, html_mod.unescape(a.group(1).strip()))
    btn = SHOW_BTN_RE.search(cell)
    sid = MOVIEID_RE.search(btn.group(0)) if btn else None
    if sid and tickets:
        return tickets + sid.group(1)
    return listing


def parse(page_html, listing="", base="", tickets=""):
    """-> list of raw showings; venue assignment happens in fetch_site.

    `listing` is the fallback URL for a showing whose cell names no screening.
    """
    out = []
    for block in ITEM_RE.findall(page_html):
        d = DATE_RE.search(block)
        t = TIME_RE.search(block)
        ti = TITLE_RE.search(block)
        if not (d and t and ti):
            continue
        dmy = DMY_RE.search(d.group(1))
        if not dmy:
            continue
        day, mon, year = (int(x) for x in dmy.groups())
        loc = _txt(LOC_RE.search(block).group(1)) if LOC_RE.search(block) else ""
        venue_name, _, room = loc.partition(",")
        seats = SEATS_RE.search(block)
        taken, total = (int(seats.group(1)), int(seats.group(2))) if seats else (None, None)
        ln = LEN_RE.search(block)
        minutes = ""
        if ln and (ln.group(1) or ln.group(2)):
            minutes = str(int(ln.group(1) or 0) * 60 + int(ln.group(2) or 0))
        out.append({
            "loc": venue_name.strip().lower(),
            "aud": room.strip(),
            "title": _txt(ti.group(1)),
            "start": datetime.datetime(year, mon, day, int(t.group(1)), int(t.group(2)),
                                      tzinfo=FI).isoformat(),
            "len": minutes,
            # A disabled button plus every seat taken is the sold-out signal.
            "soldOut": bool(seats and total and taken >= total) or bool(DISABLED_RE.search(block)),
            "url": show_url(block, listing, base, tickets),
        })
    return out


# ---------------------------------------------------------------- prices

# Where a screening's price comes from and how often it is asked for. One GET per
# screening id, on the ticket host, sequential and `price_sleep` apart. An id is read
# again after PRICE_TTL_H, so a price change reaches the site within that time and a
# screening is otherwise read once for its whole life on the listing. At most
# PRICE_FETCH_MAX pages per run: never-fetched ids first, then the oldest. Three
# consecutive failures end the pass for this run. Nothing here can fail the schedule:
# a price that cannot be read stays "" and the showtime is published without it.
PRICES_PATH = pathlib.Path("data") / "prices-riviera.json"
PRICE_TTL_H = float(os.environ.get("KINO_RIVIERA_PRICE_TTL_H") or 48)
PRICE_FETCH_MAX = int(os.environ.get("KINO_RIVIERA_PRICE_MAX") or 40)
PRICE_FAIL_STOP = 3
ORDINARY = "sohvapaikka tai nojatuolipaikka"

SHOW_ID_RE = re.compile(r"/websales/show/(\d+)$")
PRICE_TABLE_RE = re.compile(r"<table[^>]*\bshowPrices-table\b[^>]*>(.*?)</table>", re.S)
PRICE_ROW_RE = re.compile(r"<tr\b.*?</tr>", re.S)
CATEGORY_RE = re.compile(r"<td[^>]*\bshowPrices-table-ticketCategory\b[^>]*>(.*?)</td>", re.S)
PRICE_CELL_RE = re.compile(r"<td[^>]*\bshowPrices-table-price\b[^>]*>(.*?)</td>", re.S)
AMOUNT_RE = re.compile(r"(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:\u20ac|EUR)", re.I)


def ordinary_price(page_html):
    """The ordinary seat's price on a ticket page -> "20\u20ac", "12.5\u20ac", or "".

    Only the row whose category is ORDINARY counts: a wheelchair, concession or other
    restricted ticket listed above it must not become the advertised price, and neither
    may the cheapest or the first amount on the page. No such row, or two of them
    naming different amounts, is "" -- unknown, never zero. The string is eTiketti's
    shape, which priceLabel() and price_label() already render.
    """
    table = PRICE_TABLE_RE.search(page_html or "")
    if not table:
        return ""
    amounts = set()
    for row in PRICE_ROW_RE.findall(table.group(1)):
        cat, cell = CATEGORY_RE.search(row), PRICE_CELL_RE.search(row)
        if not (cat and cell) or _txt(cat.group(1)).lower() != ORDINARY:
            continue
        m = AMOUNT_RE.search(_txt(cell.group(1)))
        if m:
            amounts.add(m.group(1).replace(",", "."))
    if len(amounts) != 1:
        return ""
    amount = amounts.pop()
    if float(amount) <= 0:
        return ""
    return amount.rstrip("0").rstrip(".") + "\u20ac"


def _age_h(entry, now):
    try:
        at = datetime.datetime.fromisoformat(entry["at"])
    except (KeyError, TypeError, ValueError):
        return float("inf")
    return (now - at).total_seconds() / 3600


def enrich_prices(shows, site, *, now=None, sleep=1.0, path=None, limit=None):
    """Put each screening's ordinary seat price on its showtimes. -> counts dict.

    `shows` are the rows fetch_site built, every one carrying its ticket URL; a row
    without one (sold out, listing fallback) is left alone. The cache at `path` maps a
    screening id to {"price", "at"} and is pruned to the ids on the listing, so it cannot
    grow past the programme. Only a changed cache is written.
    """
    tickets = site.get("tickets") or ""
    path = pathlib.Path(path or PRICES_PATH)
    limit = PRICE_FETCH_MAX if limit is None else limit
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    try:
        old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(old, dict):
            old = {}
    except (OSError, ValueError):
        old = {}

    by_id = {}
    for s in shows:
        url = s.get("url") or ""
        m = SHOW_ID_RE.search(url) if tickets and url.startswith(tickets) else None
        if m:
            by_id.setdefault(m.group(1), []).append(s)
    cache = {k: v for k, v in old.items() if k in by_id and isinstance(v, dict)}

    due = [i for i in by_id if i not in cache or _age_h(cache[i], now) >= PRICE_TTL_H]
    due.sort(key=lambda i: (i in cache, cache.get(i, {}).get("at", ""), int(i)))
    todo, deferred = due[:limit], len(due) - min(len(due), limit)
    if deferred:
        print(f"[{site['provider']}] prices: {len(due)} ticket pages due, reading {limit}, "
              f"{deferred} wait for the next run")

    fetched = failed = 0
    streak = 0
    for n, sid in enumerate(todo):
        if streak >= PRICE_FAIL_STOP:
            deferred += 1
            continue
        if n:
            time.sleep(sleep)
        try:
            page = fetch(tickets + sid, headers={"user-agent": UA, "accept": "text/html",
                                                 "referer": site["base"].rstrip("/") + "/"},
                         tries=2, timeout=20).decode("utf-8", "replace")
        except Exception as e:                     # noqa: BLE001 -- the price is optional
            failed += 1
            streak += 1
            print(f"[{site['provider']}] price page {sid}: {type(e).__name__}: "
                  f"{str(e)[:80]}")
            continue
        streak = 0
        fetched += 1
        cache[sid] = {"price": ordinary_price(page), "at": now.isoformat()}

    for sid, group in by_id.items():
        price = (cache.get(sid) or {}).get("price") or ""
        for s in group:
            s["price"] = price

    if cache != old:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, dict(sorted(cache.items())), indent=1)
    return {"screenings": len(by_id), "priced": sum(1 for i in by_id if (cache.get(i) or {}).get("price")),
            "fetched": fetched, "reused": len(by_id) - len(due),
            "unknown": sum(1 for i in by_id if i in cache and not cache[i].get("price")),
            "failed": failed, "deferred": deferred}


def fetch_site(site=SITE, tries=3, price_sleep=1.0, prices_path=None, now=None):
    base = site["base"].rstrip("/")
    ajax = base + site.get("ajax", "/wp/wp-admin/admin-ajax.php")
    listing = base + site.get("listing", "/elokuvat/")
    body = urllib.parse.urlencode({"action": "filter_movies", "date": "", "movie": "",
                                   "area": site.get("area", "1040"),
                                   "singlemovie": "", "initial": "1"}).encode()
    # POST, so `data` is passed to common.fetch; same tries=3, 5 s * n backoff and 30 s
    # timeout as the loop this replaces. The parse sits outside the retry now.
    payload = json.loads(fetch(ajax, data=body, headers={
        "user-agent": UA, "accept": "application/json, text/javascript, */*",
        "content-type": "application/x-www-form-urlencoded",
        "x-requested-with": "XMLHttpRequest",
        "referer": listing}, tries=tries).decode("utf-8", "replace"))

    rows = parse((payload.get("data") or {}).get("movies") or "", listing, base,
                 site.get("tickets", ""))
    per_venue = {v["id"]: [] for v in site["venues"]}
    unmatched = 0
    for r in rows:
        venue = next((v for v in site["venues"] if v["match"] in r["loc"]), None)
        if not venue:
            unmatched += 1
            continue
        per_venue[venue["id"]].append({
            "eventId": "", "title": r["title"], "original": "", "len": r["len"],
            "rating": "", "genres": "", "method": "",
            "theatre": venue["name"], "aud": r["aud"], "start": r["start"],
            "url": r["url"], "img": "", "lang": "", "soldOut": r["soldOut"],
            "price": "", "provider": site["provider"], "venue": venue["id"],
        })
    if unmatched:
        print(f"[{site['provider']}] {unmatched} showtimes with an unrecognised location")
    for k in per_venue:
        per_venue[k].sort(key=lambda s: s["start"])
        for s in per_venue[k]:
            s["eventId"] = re.sub(r"[^\w]+", "-", s["title"].lower()).strip("-")
    # After the schedule is complete, and never able to take it down: a failure here
    # publishes the showtimes without prices, which is what the site did before.
    try:
        st = enrich_prices([s for v in per_venue.values() for s in v], site,
                           sleep=price_sleep, path=prices_path, now=now)
        print(f"[{site['provider']}] prices: {st['screenings']} screenings, "
              f"{st['priced']} priced, {st['fetched']} pages read, {st['reused']} reused, "
              f"{st['unknown']} without an ordinary seat, {st['failed']} failed, "
              f"{st['deferred']} deferred")
    except Exception as e:                         # noqa: BLE001 -- the price is optional
        print(f"[{site['provider']}] prices skipped: {type(e).__name__}: {str(e)[:80]}")
    return {k: v for k, v in per_venue.items() if v}
