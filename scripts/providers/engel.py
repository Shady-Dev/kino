"""Kino Engel (Sofiankatu 4, Helsinki) — front-page scrape. Stdlib only.

kinoengel.fi answers **HTTP 202 with an `SG-Captcha: challenge` header** to a datacenter
address, so this runs from the Mac alongside Finnkino and Kino Akseli. The challenge is
on IP reputation, not on the request shape, so there is nothing to spoof and nothing that
would make it work from Actions.

The site has an open WordPress REST API and it looked for a moment like the whole
adapter: `wp/v2/elokuva` exists and exposes `acf`. It is empty on every film, and the
endpoint returns 899 posts across 9 pages, so it is the archive rather than the
programme. The schedule only exists in the rendered page. REST is still worth a second
pass later for the cinema's own Finnish synopsis and a full-size poster; see the note at
the bottom.

Two things about this site that shape the parser:

- **Rows carry their own date**, "La 29.08." next to "klo 17:30", so the `<h2>` day
  headings and the date `<select>` above them are both redundant. Parsing the rows alone
  means the heading markup can change without breaking this.
- **A strand is a separate `elokuva` post.** `autofiktio` (3303) and `kesakino-autofiktio`
  (3295) are two records for one film, and 23 of the first 100 posts are `kesakino-`. So
  the slug cannot be the `eventId`: it would split one film into two cards in one venue,
  each with its own poster lookup and its own TMDB miss. The id is the slug with the
  strand prefix removed, which is exactly the plain post's slug, so both halves land on
  one card.

**KesäKino is a room, not a strand.** It is the outdoor screen, so it goes in `aud` where
the client renders it on the showtime stub, next to "Sali 1" and "LUXE 4". Routing it
through `strands.py` would put it in `method` as a pill beside Anniskelu and SenioriKino,
which frames a place as a programme category. `kesäkino` stays in `EVENT_PREFIXES`
regardless, because `enrich_tmdb.clean()` needs it off the TMDB search string; this
adapter simply strips it first, so `run.py`'s central pass finds nothing left to split.
`BARNSÖNDAGAR:` and `BARNFESTIVAL:` are real strands and are left for that pass.
"""
import datetime
import html as html_mod
import re
import sys
from zoneinfo import ZoneInfo

from common import fetch

BASE = "https://kinoengel.fi"
URL = BASE + "/"
FI = ZoneInfo("Europe/Helsinki")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

VENUE = {"id": "engel-helsinki", "provider": "engel", "providerId": "1",
         "name": "Kino Engel", "short": "Kino Engel", "city": "Helsinki"}

SITES = [{"provider": "engel", "label": "Kino Engel", "venues": [VENUE]}]

# The outdoor screen. Slug prefix is the reliable signal; the visible title carries
# "KESÄKINO:" too, but the slug is ascii-folded and cannot be affected by a typo.
OUTDOOR_SLUG = "kesakino-"
OUTDOOR_AUD = "KesäKino"

ANCHOR_RE = re.compile(r'<a\b[^>]*href="(?:https?://kinoengel\.fi)?(/elokuva/([^"/]+)/?)"[^>]*>'
                       r'(.*?)</a>', re.S | re.I)
DATE_RE = re.compile(r'(?:Ma|Ti|Ke|To|Pe|La|Su)\s*(\d{1,2})\.(\d{1,2})\.')
TIME_RE = re.compile(r'klo\s*(\d{1,2})[:.](\d{2})')
IMG_RE = re.compile(r'<img\b[^>]*>', re.I)
SRCSET_RE = re.compile(r'srcset="([^"]+)"')
SRC_RE = re.compile(r'\b(?:data-src|src)="([^"]+)"')
TAGS_RE = re.compile(r"<[^>]+>")
NOISE_RE = re.compile(r"Osta liput|Varaa|Liput|klo\s*\d{1,2}[:.]\d{2}"
                      r"|(?:Ma|Ti|Ke|To|Pe|La|Su)\s*\d{1,2}\.\d{1,2}\.", re.I)
# Prefixes this adapter takes off the title itself. Kesäkino because it becomes `aud`;
# the rest stay for strands.apply in run.py.
SELF_PREFIX = ("kesäkino", "kesakino")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s))).strip()


def _biggest(srcset):
    best, bw = "", -1
    for part in srcset.split(","):
        bits = part.strip().split()
        if len(bits) == 2 and bits[1].endswith("w"):
            try:
                w = int(bits[1][:-1])
            except ValueError:
                continue
            if w > bw:
                best, bw = bits[0], w
    return best


def _poster(block):
    m = IMG_RE.search(block)
    if not m:
        return ""
    tag = m.group(0)
    ss = SRCSET_RE.search(tag)
    if ss:
        big = _biggest(ss.group(1))
        if big:
            return big
    src = SRC_RE.search(tag)
    url = src.group(1) if src else ""
    # Elementor ships a transparent placeholder in `src` when it lazy-loads.
    return "" if url.startswith("data:") else url


def _iso(day, month, hh, mm, today=None):
    """The rows carry no year, same as Kino Akseli. Pick the one nearest today."""
    today = today or datetime.datetime.now(FI).date()
    for year in (today.year, today.year + 1, today.year - 1):
        try:
            d = datetime.date(year, month, day)
        except ValueError:
            continue
        if -45 <= (d - today).days <= 320:
            return datetime.datetime(year, month, day, hh, mm, tzinfo=FI).isoformat()
    return ""


def _title(block):
    """Everything in the row that is not the date, the time or the button."""
    return re.sub(r"\s+", " ", NOISE_RE.sub(" ", _txt(block))).strip(" -–·|")


def _strip_outdoor(title):
    low = title.lower()
    for pre in SELF_PREFIX:
        if low.startswith(pre + ":"):
            rest = title[len(pre) + 1:].strip(" -–:")
            if rest:
                return rest
    return title


def parse(page, today=None):
    shows = []
    for m in ANCHOR_RE.finditer(page):
        href, slug, block = m.group(1), m.group(2), m.group(3)
        d = DATE_RE.search(block)
        t = TIME_RE.search(block)
        if not (d and t):
            # Posters and "read more" links point at the same film pages without
            # carrying a screening. Only a row with both a date and a time is a show.
            continue
        start = _iso(int(d.group(1)), int(d.group(2)),
                     int(t.group(1)), int(t.group(2)), today)
        if not start:
            continue
        outdoor = slug.lower().startswith(OUTDOOR_SLUG)
        title = _title(block)
        if outdoor:
            title = _strip_outdoor(title)
        if not title:
            continue
        shows.append({
            # Never the raw slug: kesakino-autofiktio and autofiktio are one film.
            "eventId": slug[len(OUTDOOR_SLUG):] if outdoor else slug,
            "title": title,
            "original": "",
            "len": "",
            "rating": "",
            "genres": "",
            "method": "",
            "theatre": VENUE["name"],
            "aud": OUTDOOR_AUD if outdoor else "",
            "start": start,
            "url": BASE + href if href.startswith("/") else href,
            "img": _poster(block),
            "lang": "",
            "soldOut": False,
            "price": "",
            "provider": "engel",
            "venue": VENUE["id"],
        })
    # One anchor can appear twice on a page (a carousel and the day list), so drop
    # exact repeats of the same film at the same minute rather than double-counting.
    seen, out = set(), []
    for s in shows:
        k = (s["eventId"], s["start"], s["aud"])
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    out.sort(key=lambda s: s["start"])
    return out


def fetch_page():
    page = fetch(URL, headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"},
                 timeout=30).decode("utf-8", "replace")
    if len(page) < 20000 or "sgcaptcha" in page:
        raise RuntimeError("challenged (needs a residential IP)")
    return parse(page)


def fetch_site(site=SITES[0]):
    """Runner contract: one page, one venue."""
    return {VENUE["id"]: fetch_page()}


# Next pass, deliberately not in this one: wp/v2/elokuva?slug[]=... with
# _embed=wp:featuredmedia gives the cinema's own Finnish synopsis (`content.rendered`,
# which synmerge prefers over TMDB) and a full-size poster, for the ~40 films actually
# showing rather than all 899. One request, keyed by the slugs this parse already has.

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = parse(open(src, encoding="utf-8", errors="replace").read()) if src else fetch_page()
    films = {s["eventId"] for s in data}
    outdoor = [s for s in data if s["aud"] == OUTDOOR_AUD]
    dates = sorted({s["start"][:10] for s in data})
    print(f"{len(data)} showtimes, {len(films)} films, {len(dates)} dates "
          f"({dates[0] if dates else '-'} .. {dates[-1] if dates else '-'}), "
          f"{len(outdoor)} KesäKino, {sum(1 for s in data if s['img'])} with a poster")
    for s in data:
        print(f"  {s['start'][:16]}  {s['title'][:38]:40} {s['aud']:9} {s['eventId'][:28]}")
