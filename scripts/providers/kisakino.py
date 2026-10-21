"""KisaKino, Saarijärvi. Stdlib only.

The sports club Pullistus runs it in the town hall's hall. The front page shows each
film's next three screenings and links the film page, whose sidebar lists all of them
(issue #9, read 2026-10-21). `/wp-json/` exposes no film type, so the pages are read: the
front page for the film links, then one request per film page, paced.

- **A film is an `h2.etusivu-otsikko` link to `/elokuvat/{slug}/`.** The slug is the
  `eventId`, the film page is where a showtime links, and the front page's title is
  published verbatim.
- **The sidebar's "Elokuvan näytökset" block holds one line per screening**,
  `<strong>La</strong> 24.10.2026 16:00`, with the year. A line whose weekday is not its
  date's is left out and counted.
- **"Lipun hinta: 12€" is the film's price**, printed beside its screenings, so it is each
  screening's; anything but one bare amount publishes none. "Kesto 02 h 38 min" is the
  runtime and `/images/k16.png` the rating.
- **No poster of the site's own is published** (maintainer, 2026-10-21), so a poster comes
  only from a trusted TMDB match. Tickets are sold at the box office, so `book` is door.

A front page with no film link, or a film page that cannot be read, fails the site: the
site publishes no sentence saying there is nothing on, and a film page is part of the
programme.
"""
import datetime
import html as html_mod
import re
import sys
import time
from zoneinfo import ZoneInfo

from common import bot_check, check_shows, get_text, served, weekday_index

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "kisakino", "label": "KisaKino", "base": "https://kisakino.fi",
     "listing": "/",
     "venues": [{"id": "kisakino-saarijarvi", "name": "KisaKino", "short": "KisaKino",
                 "city": "Saarijärvi"}]},
]

FILM_RE = re.compile(r'<h2 class="etusivu-otsikko">\s*<a href="([^"]*/elokuvat/([^"/]+)/?)"'
                     r'[^>]*>(.*?)</a>', re.S | re.I)
SIDEBAR_RE = re.compile(r'id="sidebar"(.*?)(?:<div id="footer|</body>)', re.S | re.I)
LIST_RE = re.compile(r"Elokuvan näytökset\s*</strong>(.*?)(?:<p>|</div>|$)", re.S | re.I)
ROW_RE = re.compile(r"<strong>\s*([A-Za-zÅÄÖåäö]{2})\s*</strong>\s*(\d{1,2})\.(\d{1,2})\."
                    r"(\d{4})\s+(\d{1,2})[:.](\d{2})", re.I)
LEN_RE = re.compile(r"Kesto\s*</strong>\s*(\d{1,2})\s*h\s*(\d{1,2})\s*min", re.I)
PRICE_RE = re.compile(r"Lipun hinta:?\s*</strong>\s*([^<]*)<", re.I)
AMOUNT_RE = re.compile(r"^(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:€|eur)?$", re.I)
RATING_RE = re.compile(r"/images/(?:k(\d{1,2})|(s))\.png", re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def text(fragment):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", fragment or ""))).strip()


def films(page):
    """The front page -> [(url, slug, title)], each film once, in page order."""
    out, seen = [], set()
    for url, slug, title in FILM_RE.findall(page):
        if slug not in seen and text(title):
            seen.add(slug)
            out.append((html_mod.unescape(url), slug, text(title)))
    return out


def film_rows(page, report):
    """A film page -> ([(start, ...)], minutes, price, rating)."""
    side = SIDEBAR_RE.search(page)
    side = side.group(1) if side else ""
    n = LEN_RE.search(side)
    minutes = str(int(n.group(1)) * 60 + int(n.group(2))) if n else ""
    p = PRICE_RE.search(side)
    a = AMOUNT_RE.match(text(p.group(1))) if p else None
    price = f"{a.group(1).replace('.', ',')}€" if a else ""
    r = RATING_RE.search(side)
    rating = ("S" if r.group(2) else f"K-{int(r.group(1))}") if r else ""
    block = LIST_RE.search(side)
    starts = []
    for wd, d, m, y, hh, mm in ROW_RE.findall(block.group(1) if block else ""):
        when = datetime.date(int(y), int(m), int(d))
        if weekday_index(wd) != when.weekday():
            report["disagree"] += 1
            continue
        starts.append(datetime.datetime(when.year, when.month, when.day, int(hh), int(mm),
                                        tzinfo=FI))
    return starts, minutes, price, rating


def fetch_site(site, sleep=1.5):
    """Runner contract: the front page, then each film page."""
    pid = site["provider"]
    venue = site["venues"][0]
    base = site["base"].rstrip("/")
    front_url = base + site["listing"]
    front = get_text(front_url)
    listed = films(front)
    if not listed:
        bot_check(front, front_url)
        raise RuntimeError(
            f"{front_url}: no film link ({served(front)}). This site publishes no sentence "
            f"saying there are none, so there is no evidence of an empty programme to read "
            f"this as and the previous files stand")
    shows, report = [], {"disagree": 0, "no_price": 0, "no_rows": 0}
    for i, (url, slug, title) in enumerate(listed):
        if i:
            time.sleep(sleep)
        starts, minutes, price, rating = film_rows(get_text(url), report)
        if not starts:
            report["no_rows"] += 1
        if starts and not price:
            report["no_price"] += 1
        shows += [{
            "eventId": slug, "title": title, "original": "", "len": minutes,
            "rating": rating, "genres": "", "method": "", "theatre": venue["name"],
            "aud": "", "start": s.isoformat(), "url": url, "img": "", "lang": "",
            "soldOut": False, "price": price, "provider": pid, "venue": venue["id"],
        } for s in starts]
    if not shows:
        raise RuntimeError(f"{front_url}: {len(listed)} film page(s) and no screening line "
                           f"on any; the previous files stand")
    shows.sort(key=lambda s: (s["start"], s["title"]))
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {len(listed)} film page(s)")
    for key, what in (("disagree", "line(s) whose weekday is not its date's, left out"),
                      ("no_rows", "film page(s) listing no screening"),
                      ("no_price", "film(s) with no single price, published without")):
        if report[key]:
            print(f"[{pid}] {report[key]} {what}")
    return per_venue


if __name__ == "__main__":
    for s in fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]:
        print(f"   {s['start'][:16]}  {s['title'][:34]:36} {s['rating']:5} "
              f"{s['price']:7} {s['len']:4}")
    sys.exit(0)
