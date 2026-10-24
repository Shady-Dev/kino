"""Virtain Pirtti, Virrat. Stdlib only.

Virtain Urheilijat ry owns the cinema. One request, to the Weebly page
`/ohjelmistossa-nyt.html` (issue #15, read 2026-10-24):

- **A film is one `div.paragraph`**: a bold title with its rating, "Lapin sota K-16", "Pirjo
  i Sverige -S-", "Unohdettu saari K-7 dub.", then one line per screening, "pe 23.10. klo
  18.00", and "Kesto 2 h 38 min". No date carries a year, so `common.resolve_year` places
  it on the weekday. "dub." after the rating marks a Finnish-dubbed print. "Ensi-ilta" above
  the rows marks the first of them as the premiere.
- **A footnote applies only to the dates it names.** "*28.10. on 9€ päivänäytös ja
  tekstitys suomeksi" gives the 28.10. screening a 9 € price and Finnish subtitles, and
  "(27.10. on 9 € päivänäytös)" the 27.10. one a 9 € price. A note naming no date, "9 €
  päivänäytös", settles no screening and is counted. The page states no ordinary price, so
  every other screening publishes none.
- **No poster of the site's own is published**, so a poster comes only from a trusted TMDB
  match. Tickets are sold at the café from an hour before a screening, so `book` is door.

Zero rows fails the site: the page publishes no sentence saying there is nothing on.
"""
import datetime
import html as html_mod
import re
import sys
from zoneinfo import ZoneInfo

from common import bot_check, check_shows, get_text, resolve_year, served, weekday_index

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "virtainpirtti", "label": "Virtain Pirtti", "base": "https://www.virtainpirtti.fi",
     "listing": "/ohjelmistossa-nyt.html",
     "venues": [{"id": "virtainpirtti-virrat", "name": "Virtain Pirtti", "short": "Virtain Pirtti",
                 "city": "Virrat"}]},
]

WINDOW = (30, 120)
PARA_RE = re.compile(r'<div class="paragraph"[^>]*>(.*?)</div>', re.S | re.I)
BR_RE = re.compile(r"<br\s*/?>", re.I)
TAGS_RE = re.compile(r"<[^>]+>")
HEAD_RE = re.compile(r"^(.+?)\s+(K-?\d{1,2}|-S-|S)(?=\W|$)\.?\s*(.*)$", re.I)
ROW_RE = re.compile(r"^(ma|ti|ke|to|pe|la|su)\s+(\d{1,2})\.(\d{1,2})\.?\s+klo\s+(\d{1,2})[.:](\d{2})"
                    r"\s*(\*?)$", re.I)
LEN_RE = re.compile(r"^kesto\s+(\d{1,2})\s*h(?:\s*(\d{1,2})\s*min)?", re.I)
NOTE_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.")
NOTE_PRICE_RE = re.compile(r"(\d{1,3})(?:,(\d{2}))?\s*\u20ac")
NOTE_SUBS_RE = re.compile(r"tekstitys\s+suomeksi", re.I)


def lines(fragment):
    out = []
    for part in BR_RE.split(fragment or ""):
        t = re.sub(r"[\s\u200b\u00a0]+", " ", html_mod.unescape(TAGS_RE.sub("", part))).strip()
        if t:
            out.append(t)
    return out


def slug(title):
    s = title.lower().translate(str.maketrans("\u00e4\u00f6\u00e5\u00e9", "aoae"))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def price_of(m):
    cents = m.group(2) or "00"
    return f"{int(m.group(1))}\u20ac" if cents == "00" else f"{int(m.group(1))},{cents}\u20ac"


def film(block, today, report):
    """One paragraph -> [(start, title, rating, minutes, lang, price, method)], or []."""
    ls = lines(block)
    head = HEAD_RE.match(ls[0]) if ls else None
    if not head:
        return []
    title, raw, rest = head.group(1).strip(), head.group(2).upper(), head.group(3)
    rating = "S" if raw.strip("-") == "S" else f"K-{int(raw.replace('K', '').strip('-'))}"
    dub = bool(re.search(r"\bdub\b", rest, re.I))
    minutes, premiere, starts, notes = "", False, [], []
    for line in ls[1:]:
        r = ROW_RE.match(line)
        if r:
            day, month = int(r.group(2)), int(r.group(3))
            year = resolve_year(day, month, today, weekday_index(r.group(1)), WINDOW)
            if year is None:
                report["undated"] += 1
                continue
            starts.append(datetime.datetime(year, month, day, int(r.group(4)), int(r.group(5)),
                                            tzinfo=FI))
            continue
        n = LEN_RE.match(line)
        if n:
            minutes = str(int(n.group(1)) * 60 + int(n.group(2) or 0))
        elif line.lower().startswith("ensi-ilta"):
            premiere = True
        elif NOTE_PRICE_RE.search(line) or NOTE_SUBS_RE.search(line):
            notes.append(line)
    by_date = {}
    for note in notes:
        dates = {(int(d), int(m)) for d, m in NOTE_DATE_RE.findall(note)}
        if not dates:
            report["undated_note"] += 1
            continue
        p = NOTE_PRICE_RE.search(note)
        for key in dates:
            got = by_date.setdefault(key, {"price": "", "subs": False})
            if p:
                got["price"] = price_of(p)
            got["subs"] = got["subs"] or bool(NOTE_SUBS_RE.search(note))
    first = min(starts) if starts else None
    out = []
    for s in starts:
        note = by_date.get((s.day, s.month), {"price": "", "subs": False})
        lang = ", ".join(x for x in ("FI-A" if dub else "", "FI-S" if note["subs"] else "") if x)
        out.append((s, title, rating, minutes, lang, note["price"],
                    "Ensi-ilta" if premiere and s == first else ""))
    return out


def rows(site, page, today=None):
    """-> (shows, report). One row per screening line of every film paragraph."""
    today = today or datetime.datetime.now(FI).date()
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    body = page[page.find("wsite-content"):] if "wsite-content" in page else page
    out = []
    report = {"films": 0, "undated": 0, "undated_note": 0}
    for block in PARA_RE.findall(body):
        got = film(block, today, report)
        report["films"] += bool(got)
        out += [{
            "eventId": slug(title), "title": title, "original": "", "len": minutes,
            "rating": rating, "genres": "", "method": method, "theatre": venue["name"],
            "aud": "", "start": s.isoformat(), "url": url, "img": "", "lang": lang,
            "soldOut": False, "price": price, "provider": site["provider"], "venue": venue["id"],
        } for s, title, rating, minutes, lang, price, method in got]
    out.sort(key=lambda x: (x["start"], x["title"]))
    return out, report


def fetch_site(site, today=None):
    """Runner contract: one request for the programme page."""
    pid = site["provider"]
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    page = get_text(url)
    shows, report = rows(site, page, today)
    if not shows:
        bot_check(page, url)
        raise RuntimeError(
            f"{url}: no film with a screening line ({served(page)}). This site publishes no "
            f"sentence saying there are none, so there is no evidence of an empty programme "
            f"to read this as and the previous files stand")
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {report['films']} film(s)")
    for key, what in (("undated_note", "price note(s) naming no date, applied to no screening"),
                      ("undated", "row(s) whose date no candidate year holds, left out")):
        if report[key]:
            print(f"[{pid}] {report[key]} {what}")
    return per_venue


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        with open(src, encoding="utf-8") as fh:
            shows, report = rows(SITES[0], fh.read())
        print(report)
    else:
        shows = fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]
    for s in shows:
        print(f"   {s['start'][:16]}  {s['title'][:30]:32} {s['rating']:5} {s['len']:4} "
              f"{s['price']:5} {s['lang']:10} {s['method']}")
    sys.exit(0)
