"""Kino Tervakoski, Janakkala. Stdlib only.

The municipality runs it in Tervakosken Seuratalo. Its programme is one WordPress page,
read through the page's REST twin in one request (issue #14, read 2026-10-24):

    /kino/wp-json/wp/v2/pages/196?_fields=id,link,content

- **The programme is the paragraphs before the first film section.** A day is a bold
  paragraph, "Keskiviikko 21.10.", and a slot is a paragraph opening with the clock, "Klo
  17.00 – Pirjo i Sverige (S), kotimainen, komedia, kesto 1 t 28 min, lippu 10,00 €". The
  clock is "klo" in lower case on some slots. No date carries a year, so
  `common.resolve_year` places it on the weekday.
- **A slot is a film only when it links to a film section on the page**, `#h-pirjo-i-sverige`.
  On 2026-10-24 that left out one of eighteen slots, "Klo 17.00 – Yksityistilaisuus", a
  private event with no link. The anchor is the `eventId` and the showtime links to it.
- **The slot carries the facts:** the rating in brackets in the link text, the
  genres, "kesto 1 t 28 min" (once "kesto, 1t 57 min"), and "lippu 10,00 €", that slot's
  price. "SUOMEKSI PUHUTTU" marks a Finnish-dubbed print.
- **No poster of the site's own is published**, so a poster comes only from a trusted TMDB
  match. Tickets are sold at the box office from 30 minutes before a screening, so `book`
  is door.

Zero rows fails the site: the page publishes no sentence saying there is nothing on.
"""
import datetime
import html as html_mod
import json
import re
import sys
from zoneinfo import ZoneInfo

from common import bot_check, check_shows, get_text, resolve_year, served, weekday_index

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "kinotervakoski", "label": "Kino Tervakoski", "base": "https://www.janakkala.fi",
     "listing": "/kino/wp-json/wp/v2/pages/196?_fields=id,link,content",
     "site": "https://www.janakkala.fi/kino/ohjelmisto-2-2-2/",
     "venues": [{"id": "kinotervakoski-janakkala", "name": "Kino Tervakoski",
                 "short": "Kino Tervakoski", "city": "Janakkala"}]},
]

WINDOW = (30, 120)
SECTION_RE = re.compile(r'<h[2-4][^>]*\bid="(h-[^"]+)"', re.I)
PARA_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
DAY_RE = re.compile(r"^(maanantai|tiistai|keskiviikko|torstai|perjantai|lauantai|sunnuntai)"
                    r"\s+(\d{1,2})\.(\d{1,2})\.?$", re.I)
SLOT_RE = re.compile(r"^klo\.?\s*(\d{1,2})[.:](\d{2})\s*[-\u2013\u2014]?\s*(.*)$", re.I | re.S)
LINK_RE = re.compile(r'<a\b[^>]*href="#(h-[^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
RATING_RE = re.compile(r"\((S|K-?\d{1,2})\)", re.I)
LEN_RE = re.compile(r"kesto,?\s*(\d{1,2})\s*t\s*(\d{1,2})\s*min", re.I)
PRICE_RE = re.compile(r"lippu\s+(\d{1,3})(?:,(\d{2}))?\s*\u20ac", re.I)
DUB_RE = re.compile(r"suomeksi\s+puhuttu", re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def text(fragment):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", fragment or ""))).strip()


def facts(rest):
    """The slot's text after the title -> (minutes, price, lang, genres)."""
    n = LEN_RE.search(rest)
    minutes = str(int(n.group(1)) * 60 + int(n.group(2))) if n else ""
    p = PRICE_RE.search(rest)
    price = ""
    if p:
        cents = p.group(2) or "00"
        price = f"{int(p.group(1))}€" if cents == "00" else f"{int(p.group(1))},{cents}€"
    lang = "FI-A" if DUB_RE.search(rest) else ""
    genres = []
    for part in DUB_RE.sub("", PRICE_RE.sub("", LEN_RE.sub("", rest))).split(","):
        part = part.strip()
        if part and not re.match(r"(?i)^kesto\b|^\d", part):
            genres.append(part[0].upper() + part[1:])
    return minutes, price, lang, ", ".join(genres)


def rows(site, content, today=None):
    """-> (shows, report). One row per film slot of the programme."""
    today = today or datetime.datetime.now(FI).date()
    venue = site["venues"][0]
    page = site["site"]
    sections = set(SECTION_RE.findall(content))
    first = SECTION_RE.search(content)
    programme = content[:first.start()] if first else content
    out, day = [], None
    report = {"films": set(), "not_film": 0, "undated": 0, "orphan": 0}
    for para in PARA_RE.findall(programme):
        line = text(para)
        d = DAY_RE.match(line)
        if d:
            dd, mm = int(d.group(2)), int(d.group(3))
            year = resolve_year(dd, mm, today, weekday_index(d.group(1)), WINDOW)
            day = datetime.date(year, mm, dd) if year else None
            if year is None:
                report["undated"] += 1
            continue
        s = SLOT_RE.match(line)
        if not s:
            continue
        link = LINK_RE.search(para)
        if not link:
            report["not_film"] += 1
            continue
        if day is None:
            report["orphan"] += 1
            continue
        anchor, label = link.group(1), text(link.group(2))
        title = RATING_RE.sub("", label).strip().rstrip(",").strip()
        r = RATING_RE.search(line)
        rating = ""
        if r:
            g = r.group(1).upper().replace("K-", "K")
            rating = "S" if g == "S" else f"K-{int(g[1:])}"
        after = text(para[link.end():])
        minutes, price, lang, genres = facts(after)
        report["films"].add(anchor)
        out.append({
            "eventId": anchor[2:], "title": title, "original": "", "len": minutes,
            "rating": rating, "genres": genres, "method": "", "theatre": venue["name"],
            "aud": "",
            "start": datetime.datetime(day.year, day.month, day.day, int(s.group(1)),
                                       int(s.group(2)), tzinfo=FI).isoformat(),
            "url": f"{page}#{anchor}" if anchor in sections else page, "img": "",
            "lang": lang, "soldOut": False, "price": price, "provider": site["provider"],
            "venue": venue["id"],
        })
    report["films"] = len(report["films"])
    out.sort(key=lambda x: (x["start"], x["title"]))
    return out, report


def fetch_site(site, today=None):
    """Runner contract: one request for the programme page's REST twin."""
    pid = site["provider"]
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    body = get_text(url)
    try:
        content = ((json.loads(body) or {}).get("content") or {}).get("rendered") or ""
    except (ValueError, AttributeError):
        bot_check(body, url)
        raise RuntimeError(f"{url}: not the page's JSON ({served(body)})")
    shows, report = rows(site, content, today)
    if not shows:
        raise RuntimeError(
            f"{url}: no film slot ({report['not_film']} slot(s) with no film link). The page "
            f"publishes no sentence saying there are none, so there is no evidence of an "
            f"empty programme to read this as and the previous files stand")
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {report['films']} film(s)")
    for key, what in (("not_film", "slot(s) with no film link, left out"),
                      ("orphan", "slot(s) before any day heading, left out"),
                      ("undated", "day heading(s) whose date no candidate year holds")):
        if report[key]:
            print(f"[{pid}] {report[key]} {what}")
    return per_venue


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        with open(src, encoding="utf-8") as fh:
            shows, report = rows(SITES[0], json.load(fh)["content"]["rendered"])
        print(report)
    else:
        shows = fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]
    for s in shows:
        print(f"   {s['start'][:16]}  {s['title'][:34]:36} {s['rating']:5} {s['len']:4} "
              f"{s['price']:6} {s['lang']:5} {s['url'][-30:]}")
    sys.exit(0)
