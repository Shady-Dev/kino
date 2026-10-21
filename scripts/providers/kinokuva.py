"""Kino-Kuva, Teuva. Stdlib only.

One request, to the front page, served as `text/html;charset=ISO-8859-1` (issue #12, read
2026-10-21). `common.get_text` decodes UTF-8 with replacement, which turned "TÄHTIPEURA"
into "T�HTIPEURA", so the bytes are read here: strict UTF-8 first, ISO-8859-1 when
that fails, so a site that moves to UTF-8 later still reads.

- **The programme is `table.naytokset`, one nested table per film**: `td.elokuva` holds the
  `h1` title and "Kesto: 1 h 34 min -K16-", and `td.elokuva_tiedot` a `<pre>` whose
  `<br>`-separated lines are the screenings, then a dashed rule, the price and notes.
- **A row is a weekday, a date and "KLO" before each clock**: "KE 21.10. KLO 19.00", "TO
  15.10. KLO 14.00 JA KLO 17.00" for two. No date carries a year, so `common.resolve_year`
  places it on the weekday. "ENSI-ILTA" before a row is a premiere, "Ensi-ilta" in
  `method`; "ENSI-ILTA 30.10." with no clock is announced only and left out. A heading
  line ending in a colon, "Puolan elokuvaviikot:", goes in `method` for the rows under it,
  and "ENNAKKONÄYTÖKSET!" marks the rows under it as previews.
- **"Liput 14,-" is the film's price**, "Ilmainen sisäänpääsy!" publishes as free, and
  anything else none. "Puhumme suomea!" marks a Finnish-dubbed print and "englanninkielinen
  teks(t)itys" English subtitles.
- **No poster of the site's own is published** (maintainer, 2026-10-21), so a poster comes
  only from a trusted TMDB match. The site sells no tickets, so `book` is door.

Zero rows fails the site: the page publishes no sentence saying there is nothing on.
"""
import datetime
import html as html_mod
import re
import sys
from zoneinfo import ZoneInfo

from common import bot_check, check_shows, fetch, resolve_year, served, weekday_index

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "kinokuva", "label": "Kino-Kuva", "base": "https://www.kinokuva.fi",
     "listing": "/",
     "venues": [{"id": "kinokuva-teuva", "name": "Kino-Kuva", "short": "Kino-Kuva",
                 "city": "Teuva"}]},
]

WINDOW = (30, 120)
TABLE_RE = re.compile(r'<table class="naytokset">(.*)', re.S | re.I)
FILM_RE = re.compile(r'<td[^>]*class="elokuva"[^>]*>(.*?)</td>.*?'
                     r'<td[^>]*class="elokuva_tiedot"[^>]*>\s*<pre>(.*?)</pre>', re.S | re.I)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
LEN_RE = re.compile(r"Kesto:\s*(\d{1,2})\s*h\s*(\d{1,2})\s*min", re.I)
RATING_RE = re.compile(r"-(?:K\s*(\d{1,2})(?:/\d{1,2})?|(S))-", re.I)
ROW_RE = re.compile(r"^(?:(ensi-ilta)\s+)?(ma|ti|ke|to|pe|la|su)\s+(\d{1,2})\.(\d{1,2})\.?"
                    r"\s*(.*)$", re.I)
CLOCK_RE = re.compile(r"klo\.?\s*(\d{1,2})[.:](\d{2})", re.I)
# A premiere announced with its date and no weekday or clock: "ENSI-ILTA 30.10.".
ANNOUNCED_RE = re.compile(r"^ensi-ilta\s+\d{1,2}\.\d{1,2}\.?$", re.I)
PRICE_RE = re.compile(r"^Liput\s+(\d{1,3})(?:,(\d{2}|-))?\s*(?:€)?$", re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def decode(body):
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("iso-8859-1")


def text(fragment):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", fragment or ""))).strip()


def slug(title):
    s = title.lower().translate(str.maketrans("äöåé", "aoae"))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def film_rows(pre, today, report):
    """A `<pre>` block -> ([(start, method)], price, lang)."""
    lines = [text(x) for x in re.split(r"<br\s*/?>|\n", pre, flags=re.I)]
    lines = [x for x in lines if x]
    out, method, price, lang, ruled = [], "", "", "", False
    for line in lines:
        if set(line) <= {"-"}:
            ruled = True
            continue
        if ruled:
            p = PRICE_RE.match(line)
            if p:
                cents = p.group(2) if p.group(2) and p.group(2) != "-" else ""
                price = f"{int(p.group(1))},{cents}€" if cents and cents != "00" \
                    else f"{int(p.group(1))}€"
            elif re.search(r"ilmainen sis", line, re.I):
                price = "Vapaa pääsy"
            if re.search(r"puhumme suomea", line, re.I):
                lang = "FI-A"
            if re.search(r"englanninkielinen teks", line, re.I):
                lang = ", ".join(x for x in (lang, "EN-S") if x)
            continue
        if ANNOUNCED_RE.match(line):
            report["untimed"] += 1
            continue
        m = ROW_RE.match(line)
        if not m:
            if re.search(r"ennakkonäytö", line, re.I):
                method = "Ennakkonäytös"
            elif line.endswith(":"):
                method = line[:-1].strip()
            continue
        day, month = int(m.group(3)), int(m.group(4))
        year = resolve_year(day, month, today, weekday_index(m.group(2)), WINDOW)
        if year is None:
            report["undated"] += 1
            continue
        clocks = CLOCK_RE.findall(m.group(5) or "")
        if not clocks:
            report["untimed"] += 1
            continue
        tag = "Ensi-ilta" if m.group(1) else method
        out += [(datetime.datetime(year, month, day, int(h), int(mi), tzinfo=FI), tag)
                for h, mi in clocks]
    return out, price, lang


def rows(site, page, today=None):
    """-> (shows, report). One row per clock of every film in the programme table."""
    today = today or datetime.datetime.now(FI).date()
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    table = TABLE_RE.search(page)
    out, report = [], {"films": 0, "untimed": 0, "undated": 0}
    for head, pre in FILM_RE.findall(table.group(1) if table else ""):
        t = H1_RE.search(head)
        title = text(t.group(1)) if t else ""
        if not title:
            continue
        n = LEN_RE.search(text(head))
        minutes = str(int(n.group(1)) * 60 + int(n.group(2))) if n else ""
        r = RATING_RE.search(text(head))
        rating = ("S" if r.group(2) else f"K-{int(r.group(1))}") if r else ""
        starts, price, lang = film_rows(pre, today, report)
        report["films"] += bool(starts)
        out += [{
            "eventId": slug(title), "title": title, "original": "", "len": minutes,
            "rating": rating, "genres": "", "method": tag, "theatre": venue["name"],
            "aud": "", "start": s.isoformat(), "url": url, "img": "", "lang": lang,
            "soldOut": False, "price": price, "provider": site["provider"],
            "venue": venue["id"],
        } for s, tag in starts]
    out.sort(key=lambda s: (s["start"], s["title"]))
    return out, report


def fetch_site(site, today=None):
    """Runner contract: one request for the front page."""
    pid = site["provider"]
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    page = decode(fetch(url))
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
          f"{len(days)} dates, {report['films']} film(s)")
    for key, what in (("untimed", "row(s) with no clock, left out"),
                      ("undated", "row(s) whose date no candidate year holds, left out")):
        if report[key]:
            print(f"[{pid}] {report[key]} {what}")
    return per_venue


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        with open(src, "rb") as fh:
            shows, report = rows(SITES[0], decode(fh.read()))
        print(report)
    else:
        shows = fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]
    for s in shows:
        print(f"   {s['start'][:16]}  {s['title'][:36]:38} {s['rating']:5} {s['len']:4} "
              f"{s['price']:5} {s['lang']:6} {s['method']}")
    sys.exit(0)
