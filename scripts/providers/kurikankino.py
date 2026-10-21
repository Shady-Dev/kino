"""Kurikan Kino, Kurikka. Stdlib only.

One request, to the front page, which is server-rendered WordPress (issue #8, read
2026-10-21):

- **A film is one `li.elokuva-thumb`** whose `a.elokuva-linkki` goes to
  `/elokuvat/{slug}/`. The slug is the row's `eventId` and the film page is where a
  showtime links, because the site sells no tickets: its contact page lists the payment
  methods taken at the cinema and links no shop. A card linking anywhere else (the gift
  card tile) is not a film, and a card with no time is a coming-soon card ("vk 45").
- **Each time is printed twice**, in the card and again in `.elokuva-ajat.mobiili`, so
  rows are deduplicated on the time's stamp.
- **`esitysaika` is a Unix stamp of the local clock written as if it were UTC**:
  1791644400 is 2026-10-10T15:00Z and the page prints "la 10.10. 15:00". The stamp's UTC
  fields give the year the printed "10.10." lacks, and a row is published only where the
  stamp's day, month, weekday and clock agree with the printed ones. A row where they
  disagree is left out and counted.
- **One price per film**, `.hinta` "14 €", printed beside the film's times, so it is each
  of its screenings' price. Anything but one bare amount settles nothing and publishes none.
- **The rating is the `ikaraja-{n|s}` class**, the runtime `.kesto` "1 h 52 min".
- **No poster of the site's own is published** (maintainer, 2026-10-21), so a poster comes
  only from a trusted TMDB match. The cards carry a landscape background image anyway.

Zero rows fails the site: the page publishes no sentence saying there is nothing on.
"""
import datetime
import html as html_mod
import re
import sys
from zoneinfo import ZoneInfo

from common import bot_check, check_shows, get_text, served, weekday_index

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "kurikankino", "label": "Kurikan Kino", "base": "https://www.kurikankino.com",
     "listing": "/",
     "venues": [{"id": "kurikankino-kurikka", "name": "Kurikan Kino",
                 "short": "Kurikan Kino", "city": "Kurikka"}]},
]

CARD_RE = re.compile(r'<li class="elokuva-thumb">(.*?)</li>', re.S | re.I)
LINK_RE = re.compile(r'<a class="elokuva-linkki" href="([^"]*/elokuvat/([^"/]+)/?)"', re.I)
# A coming-soon card links its film page without the class and prints no time.
FILM_HREF_RE = re.compile(r'href="[^"]*/elokuvat/[^"/]+/?"', re.I)
NAME_RE = re.compile(r'<div class="elokuva-nimi[^"]*">(.*?)</div>', re.S | re.I)
TIME_RE = re.compile(r'<span esitysaika="(\d{9,11})" class="elokuva-aika">(.*?)</span>',
                     re.S | re.I)
SHOW_RE = re.compile(r'^([A-Za-zÅÄÖåäö]{2})\s+(\d{1,2})\.(\d{1,2})\.?\s+(\d{1,2})[.:](\d{2})$')
RATING_RE = re.compile(r'class="ikaraja ikaraja-(\d{1,2}|s)"', re.I)
LEN_RE = re.compile(r'<span class="kesto">(.*?)</span>', re.S | re.I)
PRICE_RE = re.compile(r'<span class="hinta">(.*?)</span>', re.S | re.I)
AMOUNT_RE = re.compile(r'^(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:€|eur)?$', re.I)
MINUTES_RE = re.compile(r'(?:(\d{1,2})\s*h\s*)?(\d{1,3})\s*min', re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def text(fragment):
    """Markup -> one line of plain text."""
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", fragment or ""))).strip()


def title_of(card):
    """The card's title without the rating badge or a coming-soon week."""
    m = NAME_RE.search(card)
    return text(re.sub(r"<span.*?</span>", "", m.group(1), flags=re.S)) if m else ""


def rating_of(card):
    m = RATING_RE.search(card)
    if not m:
        return ""
    return "S" if m.group(1).lower() == "s" else f"K-{int(m.group(1))}"


def minutes_of(card):
    """`<strong>1</strong> h <strong>52</strong> min` -> "112", anything else -> ""."""
    m = LEN_RE.search(card)
    n = MINUTES_RE.search(text(m.group(1))) if m else None
    return str(int(n.group(1) or 0) * 60 + int(n.group(2))) if n else ""


def price_of(card):
    """`14 €` -> "14€", `9,50 €` -> "9,50€"; more than one bare amount -> ""."""
    m = PRICE_RE.search(card)
    a = AMOUNT_RE.match(text(m.group(1))) if m else None
    return f"{a.group(1).replace('.', ',')}€" if a else ""


def start_of(stamp, printed):
    """The stamp read as the local clock, or None where it disagrees with the print."""
    m = SHOW_RE.match(printed)
    if not m:
        return None
    t = datetime.datetime.fromtimestamp(int(stamp), datetime.timezone.utc)
    wd = weekday_index(m.group(1))
    if (t.day, t.month, t.hour, t.minute) != tuple(int(m.group(i)) for i in (2, 3, 4, 5)) \
            or wd is None or t.weekday() != wd:
        return None
    return datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, tzinfo=FI)


def rows(site, page):
    """-> (shows, report). One row per distinct stamp of every film card."""
    venue = site["venues"][0]
    base = site["base"]
    out, report = [], {"films": 0, "coming": 0, "disagree": 0, "no_price": 0}
    for card in CARD_RE.findall(page):
        times = {}
        for stamp, printed in TIME_RE.findall(card):
            times.setdefault(stamp, text(printed))
        link = LINK_RE.search(card)
        if not times or not link:
            report["coming"] += bool(FILM_HREF_RE.search(card)) and not times
            continue
        title = title_of(card)
        if not title:
            continue
        report["films"] += 1
        url = html_mod.unescape(link.group(1))
        url = url if url.startswith("http") else base.rstrip("/") + "/" + url.lstrip("/")
        price = price_of(card)
        if not price:
            report["no_price"] += 1
        for stamp, printed in times.items():
            start = start_of(stamp, printed)
            if start is None:
                report["disagree"] += 1
                continue
            out.append({
                "eventId": link.group(2), "title": title, "original": "",
                "len": minutes_of(card), "rating": rating_of(card), "genres": "",
                "method": "", "theatre": venue["name"], "aud": "",
                "start": start.isoformat(), "url": url, "img": "", "lang": "",
                "soldOut": False, "price": price, "provider": site["provider"],
                "venue": venue["id"],
            })
    out.sort(key=lambda s: (s["start"], s["title"]))
    return out, report


def fetch_site(site):
    """Runner contract: one request for the front page."""
    pid = site["provider"]
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    page = get_text(url)
    shows, report = rows(site, page)
    if not shows:
        bot_check(page, url)
        raise RuntimeError(
            f"{url}: no film card with a screening time ({served(page)}). This site "
            f"publishes no sentence saying there are none, so there is no evidence of an "
            f"empty programme to read this as and the previous files stand")
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {report['films']} film(s), {report['coming']} coming soon")
    if report["disagree"]:
        print(f"[{pid}] {report['disagree']} time(s) whose stamp and printed day or clock "
              f"disagree, left out")
    if report["no_price"]:
        print(f"[{pid}] {report['no_price']} film(s) with no single price, published without")
    return per_venue


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        with open(src, encoding="utf-8", errors="replace") as fh:
            shows, report = rows(SITES[0], fh.read())
        print(report)
    else:
        shows = fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]
    for s in shows:
        print(f"   {s['start'][:16]}  {s['title'][:34]:36} {s['rating']:5} "
              f"{s['price']:7} {s['len']:4}")
    sys.exit(0)
