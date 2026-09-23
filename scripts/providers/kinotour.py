"""Kinotour, a touring operator in Varsinais-Suomi. Stdlib only.

One request. `kinotour.fi/varaa-liput-elokuvatapahtumiin/` renders the whole programme as
one Events Manager table, one row per screening:

    <tr>
      <td> la 19.09.2026<br />14:00 </td>
      <td><a href="https://www.kinotour.fi/events/hetki-ennen-valoa-k7-6/">
            Hetki ennen valoa, K7</a><br />
          <i>Kyrö kurkisali, Kyrö </i></td>
    </tr>

What shapes the parser:

- **A town this repository does not declare is counted and named, never dropped in
  silence and never a failure.** A touring operator visits a new town as a matter of
  course: its own `/locations/` list ran to Karkkila, Ikaalinen and Piispanristi as well as
  the three towns on the programme when this was written. Failing the site on one, the way
  `johku.py` fails on an undeclared hall, would turn the routine case into breakage. So the
  run log carries a line per run until someone adds the town to `SITES`, which is the same
  shape CLAUDE.md gives `reads`: "a `refused to ...` line in a log is a `reads` entry
  waiting to be written".
- **The venue is keyed on the town, not the hall.** `Kyrö kurkisali, Kyrö` is hall then
  town, and the hall is what changes while the tour keeps coming back to the town.
- **The date carries its year**, so nothing is inferred and `common.resolve_year` is not
  used. The row also prints a weekday, which is redundant; a weekday that contradicts its
  own date is counted and the date is what the screening is published on.
- **Only a rating-shaped tail comes off the title.** `Ryhmä Hau, Dinoelokuva, K7` is a
  title with a comma in it, so cutting at the last comma would publish
  `Ryhmä Hau` and lose the rest. The tail has to look like `K7`, `K12` or `S`.
- **The price is on the event page, one request per screening.** The table carries none.
  Each row already links to its own `/events/{slug}/`, and that page renders Events
  Manager's single-ticket block server-side:

      <div class="em-tickets em-tickets-single">
        <label>Hinta</label><strong>&euro;11,00</strong>

  It is the amount for *that* screening, which is what the rule asks for, so it is
  published. This adapter said the opposite until 2026-09-19 -- "the event page carries a
  booking form with no amount rendered anywhere on it" -- and that was simply wrong;
  whoever wrote it read the listing table or stopped at the word "booking". One request
  per distinct event page is the same cost `marita.py` and `tmb.py` already pay for a
  runtime.

  A page that renders no amount, or more than one, publishes none: a screening with two
  figures and nothing on the row to choose between them settles nothing. A page that
  cannot be fetched at all costs that row its price and nothing else, because the
  programme is already in hand and failing the whole site over a price would throw away
  the schedule.
- **No poster, runtime, genre or language.** The table is the whole of what this site
  publishes in one request, and the shared enrichment fills what it can.

**Zero rows fails the site**, and so does a table whose rows all land in undeclared
towns: a town key that stopped reading produces the same table, so it is no evidence the
declared towns are empty. No empty programme has been seen here, so there is no evidence
of what one looks like: `common.EmptyProgramme` is for the case where that evidence is in
hand.
"""
import datetime
import html as html_mod
import re
import sys
from zoneinfo import ZoneInfo

from common import check_shows, fetch, get_text
from synmerge import norm

FI = ZoneInfo("Europe/Helsinki")

# The towns read off the programme on 2026-09-18. The operator's own locations list is
# longer and reaches outside this region, so the set grows by observation: a town that
# turns up is named in the run log until it is added here, and nothing is guessed.
SITES = [
    {"provider": "kinotour", "label": "Kinotour",
     "base": "https://www.kinotour.fi",
     "listing": "/varaa-liput-elokuvatapahtumiin/",
     "venues": [
         {"id": "kinotour-kyro", "name": "Kurkisali", "short": "Kurkisali",
          "city": "Kyrö", "town": "Kyrö"},
         {"id": "kinotour-naantali", "name": "Kristoffersali", "short": "Kristoffersali",
          "city": "Naantali", "town": "Naantali"},
         {"id": "kinotour-lieto", "name": "Valtuustosali", "short": "Valtuustosali",
          "city": "Lieto", "town": "Lieto"},
     ]},
]

ROW_RE = re.compile(r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>", re.S | re.I)
LINK_RE = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
# Events Manager's single-ticket block on the event page. Anchored on the `Hinta` label
# rather than on any euro sign in the document: the page also carries a newsletter box and
# a map, and a bare amount pattern would read whatever those happen to print.
PRICE_RE = re.compile(r"<label[^>]*>\s*Hinta\s*</label>\s*<strong[^>]*>(.*?)</strong>",
                      re.S | re.I)
AMOUNT_RE = re.compile(r"\u20ac\s*(\d{1,3})(?:[.,](\d{1,2}))?|(\d{1,3})(?:[.,](\d{1,2}))?\s*\u20ac")
PLACE_RE = re.compile(r"<i>(.*?)</i>", re.S | re.I)
DATE_RE = re.compile(r"(ma|ti|ke|to|pe|la|su)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})", re.I)
# A colon, and never a dot. The cell flattens to "su 27.09.2026 14:00", so the date is
# in the same string as the time, and a dot-tolerant pattern read its 27.09 as 27:09
# and raised on the hour. The first match is taken, which is only safe because of
# that: with dots allowed the date would win.
TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
# `, K7`, `, K12` or `, S` at the end of a title, and nothing else.
RATING_TAIL_RE = re.compile(r",\s*(K-?\d{1,2}|S)\s*$", re.I)
TAGS_RE = re.compile(r"<[^>]+>")
FI_WEEKDAYS = ("ma", "ti", "ke", "to", "pe", "la", "su")

# A town with no row is known empty, not unread, once the table filed a row under some
# other declared town: this page is the operator's whole published programme in one
# request, so a town it does not mention has nothing on. `run.py` then publishes a fresh
# empty file for that venue instead of ageing its last visit, which is the case its own
# comment names: "a touring cinema's town is empty between visits". A table with no row
# under any declared town never reaches that loop, because `fetch_site` raises first:
# rows that all land in undeclared towns are also what a town key that stopped reading
# produces.
EMPTY_VENUES_CONFIRMED = True


class RowError(RuntimeError):
    """A table row this parser could not read. Not an undeclared town, which is ordinary.

    Skipping it would publish a schedule one screening short with nothing in the log to
    say so, so it fails the site and the previous files stand.
    """


def _txt(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "")
    s = TAGS_RE.sub(" ", s)
    return re.sub(r"\s+", " ", html_mod.unescape(s).replace("\xa0", " ")).strip()


def split_title(text):
    """`Ryhmä Hau, Dinoelokuva, K7` -> ("Ryhmä Hau, Dinoelokuva", "K-7")."""
    m = RATING_TAIL_RE.search(text or "")
    if not m:
        return (text or "").strip(), ""
    tail = m.group(1).upper().replace("-", "")
    rating = "S" if tail == "S" else f"K-{int(tail[1:])}"
    return text[:m.start()].strip(), rating


def price_of(page):
    """The amount Events Manager renders for one screening. -> "11\u20ac", or "".

    One amount settles the row and anything else settles nothing, which is the shared
    rule. Trailing zeros come off so 11,00 publishes as 11\u20ac, the shape `biosavoy.py`
    already writes.
    """
    found = PRICE_RE.findall(page or "")
    amounts = set()
    for blob in found:
        for m in AMOUNT_RE.finditer(_txt(blob)):
            whole, cents = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            amounts.add(f"{int(whole)}.{(cents or '0').ljust(2, '0')}")
    if len(amounts) != 1:
        return ""
    return f"{float(amounts.pop()):.2f}".rstrip("0").rstrip(".") + "\u20ac"


def rows(site, page):
    """-> ({venue_id: [show]}, report).

    `report["undeclared"]` counts the towns this repository does not list, by town, and
    `report["weekday"]` the rows whose printed weekday contradicts their own date.
    """
    by_town = {v["town"]: v for v in site["venues"]}
    per_venue = {v["id"]: [] for v in site["venues"]}
    report = {"undeclared": {}, "weekday": 0}
    for n, (left, right) in enumerate(ROW_RE.findall(page)):
        when, link = _txt(left), LINK_RE.search(right)
        times = TIME_RE.findall(when)
        d, t = DATE_RE.search(when), (times[0] if times else None)
        if not link:
            raise RowError(f"{site['provider']}: row {n + 1} carries no film link")
        title, rating = split_title(_txt(link.group(2)))
        if not d or not t:
            raise RowError(f"{site['provider']}: row {n + 1} for {title!r} has no readable "
                           f"date or time (read {when!r})")
        place = PLACE_RE.search(right)
        town = _txt(place.group(1)).rsplit(",", 1)[-1].strip() if place else ""
        if not town:
            raise RowError(f"{site['provider']}: row {n + 1} for {title!r} names no place")
        day, month, year = int(d.group(2)), int(d.group(3)), int(d.group(4))
        try:
            start = datetime.datetime(year, month, day, int(t[0]), int(t[1]), tzinfo=FI)
        except ValueError as e:
            raise RowError(f"{site['provider']}: row {n + 1} for {title!r} prints the "
                           f"impossible date {day}.{month}.{year}") from e
        if FI_WEEKDAYS[start.weekday()] != d.group(1).lower():
            report["weekday"] += 1
        venue = by_town.get(town)
        if venue is None:
            report["undeclared"][town] = report["undeclared"].get(town, 0) + 1
            continue
        per_venue[venue["id"]].append({
            "eventId": norm(title),
            "title": title,
            "original": "",
            "len": "",
            "rating": rating,
            "genres": "",
            "method": "",
            "theatre": venue["name"],
            "aud": "",
            "start": start.isoformat(),
            "url": html_mod.unescape(link.group(1)),
            "img": "",
            "lang": "",
            "soldOut": False,
            "price": "",
            "provider": site["provider"],
            "venue": venue["id"],
        })
    for shows in per_venue.values():
        shows.sort(key=lambda s: s["start"])
    return per_venue, report


def get(url, tries=3, timeout=30):
    """`common.get_text` with this module's own `fetch`, which its tests stub."""
    return get_text(url, fetcher=fetch, tries=tries, timeout=timeout)


def add_prices(per_venue, get=None):
    """Read each distinct event page once and write its amount onto that row.

    -> (pages read, rows priced, pages that failed). Never raises: the programme is
    already parsed by this point, and failing the site over a price would throw away a
    schedule that is in hand.
    """
    get = get or (lambda u: get_text(u, fetcher=fetch, tries=2, backoff=3, timeout=20))
    seen, failed, priced = {}, 0, 0
    for shows in per_venue.values():
        for s in shows:
            u = s["url"]
            if u not in seen:
                try:
                    seen[u] = price_of(get(u))
                except Exception:
                    seen[u] = ""
                    failed += 1
            s["price"] = seen[u]
            priced += bool(seen[u])
    return len(seen), priced, failed


def fetch_site(site):
    pid = site["provider"]
    url = site["base"].rstrip("/") + site["listing"]
    per_venue, report = rows(site, get(url))
    published = sum(len(v) for v in per_venue.values())
    if not published and report["undeclared"]:
        named = ", ".join(f"{t} ({n})" for t, n in sorted(report["undeclared"].items()))
        raise RuntimeError(
            f"{url}: no row under a declared town, every one in a town this repo does not "
            f"list: {named}. A town key that stopped reading looks the same, so no declared "
            f"town is published empty and the previous files stand")
    if not published:
        raise RuntimeError(
            f"{url}: no screening row in the table. No empty programme has been seen here, "
            f"so there is no evidence of one to read this as, and the previous files stand")
    pages, priced, failed = add_prices(per_venue)
    check_shows(per_venue, pid, {v["id"] for v in site["venues"]})
    print(f"[{pid}] {published} screening(s) in {len(site['venues'])} declared town(s)")
    print(f"[{pid}] prices: {pages} event page(s) read, {priced} of {published} row(s) "
          f"priced, {failed} page(s) that did not answer")
    if report["undeclared"]:
        named = ", ".join(f"{t} ({n})" for t, n in sorted(report["undeclared"].items()))
        print(f"[{pid}] {sum(report['undeclared'].values())} screening(s) in "
              f"{len(report['undeclared'])} town(s) this repo does not list, left out: "
              f"{named}. Add the town to SITES to publish them")
    if report["weekday"]:
        print(f"[{pid}] {report['weekday']} row(s) whose weekday contradicts their own "
              f"date, published on the date")
    for v in site["venues"]:
        shows = per_venue[v["id"]]
        days = sorted({s["start"][:10] for s in shows})
        print(f"[{pid}] {v['name']}, {v['city']}: {len(shows)} showtimes, {len(days)} dates")
    return per_venue


if __name__ == "__main__":
    for vid, shows in fetch_site(SITES[0]).items():
        print(f"{vid}: {len(shows)} showtimes")
        for s in shows[:4]:
            print(f"   {s['start'][:16]}  {s['title'][:34]:36} {s['rating']:5} "
                  f"{s['url'][-34:]}")
    sys.exit(0)
