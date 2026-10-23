"""Cinema Levi Summit, Kittilä. Stdlib only.

The Levi Summit event centre, run by Kassiopeia, shows films in the ski season. One
request, to its cinema page; levisummit.fi/cinema/ redirects there (issue #13, read
2026-10-24):

- **The calendar is in the page.** A week is a `levi-summit-cinema-show-day-container`
  section, a day its `h3`, "Torstai 12.11.2026", with the year, and a screening a
  `levi-summit-cinema-show-day__single`: the film's link and `h4` title, "To klo 14:00",
  and the prices. One link went to the English path, `/levi-summit/en/cinema/{slug}/`, on
  2026-10-24, so the film is joined on its slug and links to its card's Finnish page. A screening whose weekday is not its date's is left out and counted.
- **The ordinary ticket is the price.** Each screening prints `movie-tickets` "15 €" and,
  apart from it, `movie-tickets__children` "10 € (alle 12-v)", the under-12 concession,
  which is not published. The page states the same tariff, "15 € aikuiset | 10 € alle
  12-vuotiaat".
- **The film cards on the same page carry the film's facts**, joined by the film's link:
  "1h 49min", the age-rating image's alt text "Ikäraja 16: ...", and the flags under
  "Kieli" (spoken language) and "Tekstitys" (subtitles), named in English in their alt
  text. An unnamed rating or a language name not listed here publishes nothing.
- **No poster of the site's own is published**, so a poster comes only from a trusted TMDB
  match. Tickets are sold at the café from half an hour before a screening, so `book` is
  door.

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
    {"provider": "levisummit", "label": "Cinema Levi Summit", "base": "https://www.kassiopeia.fi",
     "listing": "/levi-summit/cinema/",
     "venues": [{"id": "levisummit-kittila", "name": "Cinema Levi Summit",
                 "short": "Cinema Levi Summit", "city": "Kittilä"}]},
]

LANGS = {"finnish": "FI", "swedish": "SV", "english": "EN", "german": "DE", "french": "FR",
         "spanish": "ES", "italian": "IT", "japanese": "JA", "norwegian": "NO",
         "danish": "DA", "sami": "SE", "russian": "RU", "estonian": "ET"}
CARD_SPLIT_RE = re.compile(r'<div class="movies-container__single">')
CARD_LINK_RE = re.compile(r'href="(https://www\.kassiopeia\.fi/levi-summit/cinema/([^"/]+)/)"')
DURATION_RE = re.compile(r'class="duration">\s*(\d{1,2})\s*h\s*(?:(\d{1,2})\s*min)?', re.I)
AGE_RE = re.compile(r'class="movie-age-rating__img"[^>]*\balt="Ik\u00e4raja\s+(\d{1,2}|S)\b', re.I)
AUDIO_RE = re.compile(r'class="movie-language__flag"[^>]*\balt="([^"]*)"', re.I)
SUBS_RE = re.compile(r'class="movie-subtitles__flag"[^>]*\balt="([^"]*)"', re.I)
DAY_SPLIT_RE = re.compile(r'<section class="levi-summit-cinema-show-day-container"')
DAY_RE = re.compile(r"<h3>\s*([A-Za-z\u00c4\u00d6\u00e4\u00f6]+)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})\s*</h3>")
SHOW_SPLIT_RE = re.compile(r"<div class='levi-summit-cinema-show-day__single'>")
SHOW_LINK_RE = re.compile(r"<a href='(https://www\.kassiopeia\.fi/levi-summit/(?:en/)?cinema/"
                          r"([^'/]+)/)'>\s*<h4>(.*?)</h4>", re.S)
TIME_RE = re.compile(r"\b(ma|ti|ke|to|pe|la|su)\s+klo\s+(\d{1,2})[:.](\d{2})", re.I)
TICKET_RE = re.compile(r"<span class='movie-tickets'>\s*(\d{1,3})(?:,(\d{2}))?\s*\u20ac\s*</span>")
TAGS_RE = re.compile(r"<[^>]+>")


def text(fragment):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", fragment or ""))).strip()


def codes(names):
    return [LANGS[n.strip().lower()] for n in names if n.strip().lower() in LANGS]


def cards(page):
    """-> {film slug: (link, minutes, rating, lang)} from the film cards."""
    out = {}
    for card in CARD_SPLIT_RE.split(page)[1:]:
        link = CARD_LINK_RE.search(card)
        if not link:
            continue
        d = DURATION_RE.search(card)
        minutes = str(int(d.group(1)) * 60 + int(d.group(2) or 0)) if d else ""
        a = AGE_RE.search(card)
        rating = ("S" if a.group(1).upper() == "S" else f"K-{int(a.group(1))}") if a else ""
        lang = [f"{c}-A" for c in codes(AUDIO_RE.findall(card))]
        lang += [f"{c}-S" for c in codes(SUBS_RE.findall(card))]
        out.setdefault(link.group(2), (link.group(1), minutes, rating, ", ".join(lang)))
    return out


def rows(site, page):
    """-> (shows, report). One row per screening in the calendar."""
    venue = site["venues"][0]
    facts = cards(page)
    out = []
    report = {"films": set(), "disagree": 0, "no_card": 0}
    for section in DAY_SPLIT_RE.split(page)[1:]:
        d = DAY_RE.search(section)
        if not d:
            continue
        date = datetime.date(int(d.group(4)), int(d.group(3)), int(d.group(2)))
        for show in SHOW_SPLIT_RE.split(section)[1:]:
            link = SHOW_LINK_RE.search(show)
            if not link:
                continue
            slug, title = link.group(2), text(link.group(3))
            if slug not in facts:
                report["no_card"] += 1
            url, minutes, rating, lang = facts.get(slug, (link.group(1), "", "", ""))
            t = TICKET_RE.search(show)
            price = ""
            if t:
                cents = t.group(2) or "00"
                price = f"{int(t.group(1))}€" if cents == "00" else f"{int(t.group(1))},{cents}€"
            for wd, hh, mm in TIME_RE.findall(show):
                if weekday_index(wd) != date.weekday():
                    report["disagree"] += 1
                    continue
                report["films"].add(slug)
                out.append({
                    "eventId": slug, "title": title,
                    "original": "", "len": minutes, "rating": rating, "genres": "",
                    "method": "", "theatre": venue["name"], "aud": "",
                    "start": datetime.datetime(date.year, date.month, date.day, int(hh),
                                               int(mm), tzinfo=FI).isoformat(),
                    "url": url, "img": "", "lang": lang, "soldOut": False, "price": price,
                    "provider": site["provider"], "venue": venue["id"],
                })
    report["films"] = len(report["films"])
    out.sort(key=lambda x: (x["start"], x["title"]))
    return out, report


def fetch_site(site):
    """Runner contract: one request for the cinema page."""
    pid = site["provider"]
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    page = get_text(url)
    shows, report = rows(site, page)
    if not shows:
        bot_check(page, url)
        raise RuntimeError(
            f"{url}: no screening in the calendar ({served(page)}). This site publishes no "
            f"sentence saying there are none, so there is no evidence of an empty programme "
            f"to read this as and the previous files stand")
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {report['films']} film(s)")
    for key, what in (("disagree", "screening(s) whose weekday is not its date's, left out"),
                      ("no_card", "screening(s) whose film has no card, published without facts")):
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
        print(f"   {s['start'][:16]}  {s['title'][:36]:38} {s['rating']:5} {s['len']:4} "
              f"{s['price']:5} {s['lang']}")
    sys.exit(0)
