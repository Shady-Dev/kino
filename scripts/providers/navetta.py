"""Navettakino, a cinema in a cowshed in Pyhälahti, Konnevesi. Stdlib only.

On 2026-11-01, between 09:28 and 12:19 UTC, the site moved from a WordPress page with the
programme in prose to a hand-written PHP page. This reads the new page. The front page
carries a "Seuraavat näytökset" box and below it one card per film:

    <div class='w3-auto w3-card w3-container' ...>
      <a href='leffa?id=100004470'><img src=kuvat/jul_100004470.jpg alt='Juliste' ...></a>
      <h2>Lapin sota</h2><p>K16, kesto 158 min, liput 11 €</p>
      <div class='w3-container w3-margin'><h4>Näytökset</h4>
        <p>su 01.11 klo 17:00 - <a href='varaa.php?id=80'>Varaa</a></p></div></div>

What shapes the parser:

- **The cards are the schedule.** Each card's `Näytökset` lines carry the date and the
  time. The box above them prints "Tänään" with a clock and no date, and it is not read.
  A line under `Näytökset` that this parser cannot read fails the site, because skipping
  it would publish the weekend one screening short with nothing in the log.
- **The date prints no year**, `su 01.11 klo 17:00`, so the weekday selects the year
  through `common.resolve_year`.
- **The metadata line is read by pattern.** `K16, kesto 158 min, liput 11 €` on the one
  card read. A `liput` figure that is not one amount settles nothing.
- **The ticket link is the card's own `Varaa` href, copied and never requested.** A
  screening without one opens the film's page, `leffa?id=N`, which answered 200 on the
  day read. Before the move the page linked no ticket host and the registry said `door`.
  It says `reserve` since the move.
- **The synopsis is on the film page**, in the first paragraph after the title that
  carries no bold label. The cast, the rating and the runtime each open with one
  (`<b>Pääosissa:</b>`). The paragraph separates its own paragraphs with blank lines,
  which a browser shows as spaces. A part shorter than `SYN_MIN` is a release note
  ("Elokuvateattereissa 23.10.") and is dropped, the rule johku.py and kinola.py use.
  One request per film, paced and capped. A film page that fails costs that film its
  synopsis and nothing else.
- **The poster is the card's image.** The tag carries no dimensions to check its shape.
- No language and no genre is published, so both stay empty.

**An empty programme has not been seen on the new page.** The old page said in its own
words that times appear only when there are screenings, and the new one has no such
sentence. So an empty programme is confirmed only when the page renders the "Seuraavat
näytökset" heading, no card prints a screening, and no date or clock appears anywhere in
the body. A page without the heading raises and the previous files stand. The maintainer
kept this on 2026-11-02 after a review showed two dateless film cards clear a saved
screening: a run that finds no screening is not to fail and raise an alert. Each film card
on such a page is recorded as unread instead, which the run-log check reports without
failing.
"""
import datetime
import html as html_mod
import re
import sys
import time
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from common import (bot_check, capped, check_shows, fetch, get_text, resolve_year,
                    served, unread, weekday_index)
from synmerge import norm

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "navettakino", "label": "Navettakino",
     "base": "https://www.navettakino.fi",
     "listing": "/",
     "venues": [{"id": "navettakino-konnevesi", "name": "Navettakino",
                 "short": "Navettakino", "city": "Konnevesi"}]},
]

# `resolve_year`'s (behind, ahead). The page publishes the coming weekend and nothing
# further, so 120 is headroom rather than a fit.
WINDOW = (30, 120)

BODY_RE = re.compile(r"<body\b[^>]*>(.*?)(?=<footer\b|</body>|\Z)", re.S | re.I)
HEADING_RE = re.compile(r"<h2[^>]*>\s*seuraavat\s+näytökset\s*</h2>", re.I)
CARD_RE = re.compile(r"<div[^>]*\bw3-card\b[^>]*>(.*?)(?=<div[^>]*\bw3-card\b|\Z)",
                     re.S | re.I)
TITLE_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
META_RE = re.compile(r"</h2>\s*<p[^>]*>(.*?)</p>", re.S | re.I)
SHOWS_RE = re.compile(r"<h4[^>]*>\s*näytökset\s*</h4>(.*)", re.S | re.I)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)
FILM_RE = re.compile(r"""<a[^>]*\bhref=['"]?(leffa\?id=\d+)""", re.I)
IMG_RE = re.compile(r"""<img[^>]*\bsrc=(?:'([^']+)'|"([^"]+)"|([^\s>]+))""", re.I)
HREF_RE = re.compile(r"""<a[^>]*\bhref=(?:'([^']+)'|"([^"]+)"|([^\s>]+))""", re.I)
# A weekday and a date, or a clock, anywhere in the body. Checked only when the cards
# yielded nothing, and a hit there fails the site.
TIMES_RE = re.compile(r"\b(?:ma|ti|ke|to|pe|la|su)\s+\d{1,2}\.\d{1,2}\b"
                      r"|\bklo\s*\d{1,2}[:.]\d{2}", re.I)
SHOW_RE = re.compile(r"^(ma|ti|ke|to|pe|la|su)\s+(\d{1,2})\.(\d{1,2})\.?\s*klo\s*"
                     r"(\d{1,2})[:.](\d{2})(?:\s*-.*)?$", re.I)
RATING_RE = re.compile(r"\bK[-\s]?(\d{1,2})\b")
S_RATING_RE = re.compile(r"(?:^|[\s,(])S(?=[\s,)]|$)")
MIN_RE = re.compile(r"(?:(\d{1,2})\s*h\s*)?(\d{1,3})\s*min", re.I)
PRICE_RE = re.compile(r"liput\s+([^,;]+?)\s*(?:$|,|;)", re.I)
AMOUNT_RE = re.compile(r"^(\d{1,3}(?:[.,]\d{1,2})?)\s*€$")
FILM_PAGE_RE = re.compile(r"</h2>(.*?)(?=<h3\b|\Z)", re.S | re.I)
LABEL_RE = re.compile(r"^\s*<b>[^<]*:\s*</b>", re.I)
SYN_MIN = 120
TAGS_RE = re.compile(r"<[^>]+>")

# Set on the evidence in the docstring and the maintainer's decision of 2026-11-02, which
# accepts an unseen empty state over a failing run. A page without the heading never reaches it.
EMPTY_VENUES_CONFIRMED = True


class ListingError(RuntimeError):
    """The cards are there and this parser could not read them."""


def _txt(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "")
    s = TAGS_RE.sub("", s)
    s = html_mod.unescape(s).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in s.split("\n")).strip()


def body(page):
    """The page between `<body>` and the footer, or "" when there is none."""
    m = BODY_RE.search(page or "")
    return m.group(1) if m else ""


def _attr(m):
    return html_mod.unescape(next(g for g in m.groups() if g is not None)).strip()


def _minutes(text):
    m = MIN_RE.search(text or "")
    if not m:
        return ""
    return str(int(m.group(1) or 0) * 60 + int(m.group(2)))


def _rating(text):
    m = RATING_RE.search(text or "")
    if m:
        return f"K-{int(m.group(1))}"
    return "S" if S_RATING_RE.search(text or "") else ""


def _price(text):
    """`liput 11 €` -> "11€". A figure that is not one amount settles nothing."""
    m = PRICE_RE.search(text or "")
    if not m:
        return ""
    a = AMOUNT_RE.match(m.group(1).strip())
    return f"{a.group(1)}€" if a else ""


def cards(page, base):
    """[card] for every film card on the page, in page order. -> list.

    A card is {title, film, img, len, rating, price, lines}, where `lines` holds
    (text, ticket href or "") for each paragraph under `Näytökset`.
    """
    out = []
    for raw in CARD_RE.findall(body(page)):
        t = TITLE_RE.search(raw)
        if not t or not _txt(t.group(1)):
            continue
        meta = META_RE.search(raw)
        meta = _txt(meta.group(1)) if meta else ""
        film = FILM_RE.search(raw)
        img = IMG_RE.search(raw)
        shows = SHOWS_RE.search(raw)
        lines = []
        for inner in P_RE.findall(shows.group(1) if shows else ""):
            text = _txt(inner)
            if not text:
                continue
            href = HREF_RE.search(inner)
            lines.append((text, urljoin(base, _attr(href)) if href else ""))
        out.append({"title": _txt(t.group(1)),
                    "film": urljoin(base, html_mod.unescape(film.group(1))) if film else "",
                    "img": urljoin(base, _attr(img)) if img else "",
                    "len": _minutes(meta), "rating": _rating(meta), "price": _price(meta),
                    "lines": lines})
    return out


def rows(site, page, today=None):
    """-> ([show], report). One row per line a card prints under `Näytökset`."""
    today = today or datetime.datetime.now(FI).date()
    venue = site["venues"][0]
    base = site["base"].rstrip("/") + "/"
    url = site["base"].rstrip("/") + site["listing"]
    if not HEADING_RE.search(body(page)):
        bot_check(page, url)
        raise ListingError(f"{site['provider']}: the page renders no "
                           f"'Seuraavat näytökset' heading ({served(page)})")
    out, report = [], {"no_price": set(), "no_ticket": set()}
    for card in cards(page, base):
        title = card["title"]
        if card["lines"] and not card["price"]:
            report["no_price"].add(title)
        for text, ticket in card["lines"]:
            m = SHOW_RE.match(text)
            if not m:
                raise ListingError(f"{site['provider']}: {title!r} prints the line "
                                   f"{text!r}, which is no date and time this parser reads")
            wd, day, month, hh, mm = m.groups()
            year = resolve_year(int(day), int(month), today, weekday_index(wd), WINDOW)
            if year is None:
                raise ListingError(
                    f"{site['provider']}: {title!r} prints {wd} {day}.{month}. and no "
                    f"candidate year carries that weekday inside the window, so the "
                    f"screening cannot be placed")
            try:
                start = datetime.datetime(year, int(month), int(day), int(hh), int(mm),
                                          tzinfo=FI)
            except ValueError as e:
                raise ListingError(f"{site['provider']}: {title!r} prints the impossible "
                                   f"date {day}.{month}.{year}") from e
            if not ticket:
                report["no_ticket"].add(title)
            out.append({
                "eventId": norm(title),
                "title": title,
                "original": "",
                "len": card["len"],
                "rating": card["rating"],
                "genres": "",
                "method": "",
                "theatre": venue["name"],
                "aud": "",
                "start": start.isoformat(),
                "url": ticket or card["film"] or url,
                "img": card["img"],
                "lang": "",
                "soldOut": False,
                "price": card["price"],
                "provider": site["provider"],
                "venue": venue["id"],
                "_film": card["film"],
            })
    out.sort(key=lambda s: s["start"])
    return out, report


def synopsis(page):
    """The film page's first unlabelled paragraph, without its release note. -> str."""
    m = FILM_PAGE_RE.search(body(page))
    for inner in P_RE.findall(m.group(1) if m else ""):
        if LABEL_RE.match(inner):
            continue
        parts = [" ".join(part.split()) for part in re.split(r"\n\s*\n", _txt(inner))]
        return " ".join(part for part in parts if len(part) >= SYN_MIN)
    return ""


def get(url, tries=3, timeout=30):
    """`common.get_text` with this module's own `fetch`, which its tests stub."""
    return get_text(url, fetcher=fetch, tries=tries, timeout=timeout)


def synopses(urls, pid, sleep=1.5):
    """{film page url: synopsis} for every film page that answered. -> dict."""
    out = {}
    for n, u in enumerate(capped(urls, pid)):
        if n:
            time.sleep(sleep)
        try:
            out[u] = synopsis(get(u))
        except Exception as e:
            print(f"[{pid}] film page {u}: {type(e).__name__}: {e}", file=sys.stderr)
    return out


def fetch_site(site, today=None, sleep=1.5):
    pid = site["provider"]
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    page = get(url)
    shows, report = rows(site, page, today)
    if not shows:
        if TIMES_RE.search(TAGS_RE.sub(" ", body(page))):
            raise RuntimeError(
                f"{url}: no card prints a screening and the page prints a date or time "
                f"elsewhere ({served(page)}). Treating it as screenings the parser missed, "
                f"and the previous files stand")
        print(f"[{pid}] {venue['name']}: the page renders its screenings heading, no card "
              f"prints a screening and no date or time appears on the page. The venue is "
              f"confirmed empty")
        for card in cards(page, site["base"]):
            unread("row", f"{card['title']}: a film card with no screening on a page "
                          f"confirmed empty")
        return {venue["id"]: []}
    syn = synopses(sorted({s["_film"] for s in shows if s["_film"]}), pid, sleep)
    for s in shows:
        if syn.get(s["_film"]):
            s["_syn"] = syn[s["_film"]]
        del s["_film"]
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {len({s['eventId'] for s in shows})} film(s), "
          f"{sum(1 for s in shows if s.get('_syn'))} with a synopsis")
    if report["no_ticket"]:
        print(f"[{pid}] {len(report['no_ticket'])} film(s) with a screening that links no "
              f"reservation and opens the film page: "
              f"{', '.join(sorted(report['no_ticket'])[:6])}")
    if report["no_price"]:
        print(f"[{pid}] {len(report['no_price'])} film(s) whose card settles no price: "
              f"{', '.join(sorted(report['no_price'])[:6])}")
    return per_venue


if __name__ == "__main__":
    for vid, shows in fetch_site(SITES[0]).items():
        print(f"{vid}: {len(shows)} showtimes")
        for s in shows:
            print(f"   {s['start'][:16]}  {s['title'][:30]:32} {s['rating']:5} "
                  f"{s['len']:4} {s['price']:6} img={'y' if s['img'] else '-'} "
                  f"syn={len(s.get('_syn', ''))} {s['url']}")
    sys.exit(0)
