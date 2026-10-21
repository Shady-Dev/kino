"""Bio Marlon, Kauhajoki. Stdlib only.

One request, to the front page, an Elementor page (issue #11, read 2026-10-21). The
programme is published on Mondays, a week and a half ahead.

- **A film is a text-editor widget with one `h1` and its `h4` rows.** The `h1` links to a
  third party (nytleffaan.fi), never the cinema, so a showtime links to the cinema's own
  front page. A widget with several `h1`s under "Tulossa" holds coming films with no time.
- **A row is a weekday, a date and one or more clocks**, "la 24.10. 14:00 ja 18:30". No
  date carries a year, so `common.resolve_year` places it on the weekday. "Ensi-ilta pe
  23.10. 16:00 ja 19:15" is a premiere, and "Ensi-ilta" goes in `method`, the site's own
  word. A row in brackets is a private screening, "(ma 26.10. 13:00 yksityisnäytös)", and
  is left out, as is a row with no clock yet.
- **The facts line after the rows** is "K-16 2 t 35 min 15 €", "-S- 1 t 13 €" for a whole
  hour, or "0 €" for a free screening, published as "Vapaa pääsy". "Suomea puhutaan!"
  under it marks a Finnish-dubbed print.
- **No poster of the site's own is published** (maintainer, 2026-10-21), so a poster comes
  only from a trusted TMDB match. Tickets are sold at the door, so `book` is door.

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
    {"provider": "biomarlon", "label": "Bio Marlon", "base": "https://biomarlon.fi",
     "listing": "/",
     "venues": [{"id": "biomarlon-kauhajoki", "name": "Bio Marlon", "short": "Bio Marlon",
                 "city": "Kauhajoki"}]},
]

WINDOW = (30, 120)
WIDGET_RE = re.compile(r'<div class="elementor-element[^"]*elementor-widget-text-editor[^"]*"'
                       r'[^>]*>(.*?)</div>\s*</div>', re.S | re.I)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
H4_RE = re.compile(r"<h4[^>]*>(.*?)</h4>", re.S | re.I)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)
ROW_RE = re.compile(r"^(?:(ensi-ilta)\s+)?(ma|ti|ke|to|pe|la|su)\s+(\d{1,2})\.(\d{1,2})\.?"
                    r"(?:\s+(.*))?$", re.I)
CLOCK_RE = re.compile(r"^(\d{1,2})[:.](\d{2})\s*(?:(?:ja|&|,)\s*)?", re.I)
RATING_RE = re.compile(r"(?:^|\s)(?:-S-|K-(\d{1,2})(?:/\d{1,2})?)(?=\s|$)", re.I)
LEN_RE = re.compile(r"(\d{1,2})\s*t(?:\s+(\d{1,2})\s*min)?\b", re.I)
PRICE_RE = re.compile(r"(\d{1,3}(?:,\d{1,2})?)\s*€")
TAGS_RE = re.compile(r"<[^>]+>")


def text(fragment):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", fragment or ""))).strip()


def slug(title):
    s = title.lower().translate(str.maketrans("äöåé", "aoae"))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def facts(paras):
    """The widget's paragraphs -> (rating, minutes, price, lang)."""
    rating = minutes = price = lang = ""
    for p in paras:
        line = text(p)
        if not rating:
            r = RATING_RE.search(line)
            if r:
                rating = f"K-{int(r.group(1))}" if r.group(1) else "S"
        if not minutes:
            n = LEN_RE.search(line)
            if n:
                minutes = str(int(n.group(1)) * 60 + int(n.group(2) or 0))
        if not price:
            a = PRICE_RE.search(line)
            if a:
                price = "Vapaa pääsy" if a.group(1) in ("0", "0,00") else f"{a.group(1)}€"
        if re.search(r"suomea puhutaan", line, re.I):
            lang = "FI-A"
    return rating, minutes, price, lang


def rows(site, page, today=None):
    """-> (shows, report). One row per clock of every film widget."""
    today = today or datetime.datetime.now(FI).date()
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    out = []
    report = {"films": 0, "coming": 0, "private": 0, "untimed": 0, "undated": 0}
    for w in WIDGET_RE.findall(page):
        titles = [text(t) for t in H1_RE.findall(w) if text(t)]
        lines = [text(h) for h in H4_RE.findall(w)]
        if len(titles) != 1:
            # "Tulossa" heads the coming films; other several-h1 widgets are the address.
            if any(re.match(r"tulossa\b", x, re.I) for x in lines):
                report["coming"] += len(titles)
            continue
        title = titles[0]
        rating, minutes, price, lang = facts(P_RE.findall(w))
        film = False
        for line in lines:
            if line.startswith("(") or re.search(r"yksityis", line, re.I):
                report["private"] += 1
                continue
            m = ROW_RE.match(line)
            if not m:
                continue
            day, month = int(m.group(3)), int(m.group(4))
            year = resolve_year(day, month, today, weekday_index(m.group(2)), WINDOW)
            if year is None:
                report["undated"] += 1
                continue
            rest, clocks = m.group(5) or "", []
            while True:
                c = CLOCK_RE.match(rest)
                if not c:
                    break
                clocks.append((int(c.group(1)), int(c.group(2))))
                rest = rest[c.end():]
            if not clocks:
                report["untimed"] += 1
                continue
            film = True
            for h, mi in clocks:
                out.append({
                    "eventId": slug(title), "title": title, "original": "", "len": minutes,
                    "rating": rating, "genres": "",
                    "method": "Ensi-ilta" if m.group(1) else "", "theatre": venue["name"],
                    "aud": "",
                    "start": datetime.datetime(year, month, day, h, mi, tzinfo=FI).isoformat(),
                    "url": url, "img": "", "lang": lang, "soldOut": False, "price": price,
                    "provider": site["provider"], "venue": venue["id"],
                })
        report["films"] += film
    out.sort(key=lambda s: (s["start"], s["title"]))
    return out, report


def fetch_site(site, today=None):
    """Runner contract: one request for the front page."""
    pid = site["provider"]
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    page = get_text(url)
    shows, report = rows(site, page, today)
    if not shows:
        bot_check(page, url)
        raise RuntimeError(
            f"{url}: no film with a timed screening ({served(page)}). This site publishes no "
            f"sentence saying there are none, so there is no evidence of an empty programme "
            f"to read this as and the previous files stand")
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {report['films']} film(s), {report['coming']} coming")
    for key, what in (("private", "private screening row(s), left out"),
                      ("untimed", "row(s) with no clock yet, left out"),
                      ("undated", "row(s) whose date no candidate year holds, left out")):
        if report[key]:
            print(f"[{pid}] {report[key]} {what}")
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
        print(f"   {s['start'][:16]}  {s['title'][:40]:42} {s['rating']:5} {s['len']:4} "
              f"{s['price']:11} {s['method']}")
    sys.exit(0)
