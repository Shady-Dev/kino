"""Kino Akseli (Nummela, single screen) — Elementor page scrape. Stdlib only.

kinoakseli.fi answers datacenter IPs with a [redacted], so this provider
runs from the Mac alongside Finnkino, not in Actions.

The page gives genres, age limit and ticket price, but no booking links (tickets are
sold at the door), no auditorium, and dates carry no year.
"""
import datetime, html as html_mod, json, re, sys, urllib.request
from zoneinfo import ZoneInfo

URL = "https://kinoakseli.fi/"
FI = ZoneInfo("Europe/Helsinki")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

VENUE = {"id": "ka-nummela", "provider": "kinoakseli", "providerId": "1",
         "name": "Kino Akseli", "short": "Kino Akseli", "city": "Nummela"}

# Single screen, so one site with one venue. See run.py for the contract.
SITES = [{"provider": "kinoakseli", "label": "Kino Akseli", "venues": [VENUE]}]

HEAD_RE = re.compile(r'<h2[^>]*class="elementor-heading-title[^"]*"[^>]*>\s*'
                     r'<a href="(https://kinoakseli\.fi/elokuva-[^"]+)"[^>]*>(.*?)</a>', re.S)
SHOWS_RE = re.compile(r'Näytösajat(.*?)</p>', re.S)
SHOW_RE = re.compile(r'([A-Za-zÄÖäö]{2})\s*(\d{1,2})\.(\d{1,2})\.\s*klo\s*(\d{1,2})[:.](\d{2})\s*(\(dub\.?\))?')
RATING_RE = re.compile(r'Ikäraja\s*:\s*([^<]+)')
PRICE_RE = re.compile(r'Liput\s*:\s*([^<]+)')
GENRE_RE = re.compile(r'<p>([^<]{2,80})</p>')
SRCSET_RE = re.compile(r'srcset="([^"]+)"')
TAGS_RE = re.compile(r"<[^>]+>")


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


def _iso(day, month, hh, mm, today=None):
    """No year on the page: pick the one that keeps the date near today."""
    today = today or datetime.datetime.now(FI).date()
    for year in (today.year, today.year + 1, today.year - 1):
        try:
            d = datetime.date(year, month, day)
        except ValueError:
            continue
        if -45 <= (d - today).days <= 320:
            return datetime.datetime(year, month, day, hh, mm, tzinfo=FI).isoformat()
    return ""


def parse(page, today=None):
    shows = []
    heads = list(HEAD_RE.finditer(page))
    for n, m in enumerate(heads):
        url, title = m.group(1), _txt(m.group(2))
        if not title:
            continue
        before = page[heads[n - 1].end():m.start()] if n else page[:m.start()]
        after = page[m.end():heads[n + 1].start()] if n + 1 < len(heads) else page[m.end():]
        block = SHOWS_RE.search(after)
        if not block:
            continue
        rating_raw = RATING_RE.search(before)
        rating = _txt(rating_raw.group(1)) if rating_raw else ""
        if rating and rating[0].isdigit():
            rating = "K-" + rating
        price_raw = PRICE_RE.search(before)
        srcset = SRCSET_RE.search(before)
        img = _biggest(srcset.group(1)) if srcset else ""
        # Block is <p>genres</p><p>Ikäraja : n</p><p>Liput : n€</p> — take the last
        # plain paragraph before the title.
        genres = ""
        for g in GENRE_RE.findall(before):
            g = _txt(g)
            if g and not any(k in g for k in ("Ikäraja", "Liput", "Näytösajat", "Kesto")):
                genres = g
        for sm in SHOW_RE.finditer(block.group(1)):
            _, day, month, hh, mm, dub = sm.groups()
            start = _iso(int(day), int(month), int(hh), int(mm), today)
            if not start:
                continue
            shows.append({
                "eventId": url.rstrip("/").rsplit("/", 1)[-1],
                "title": title,
                "original": "",
                "len": "",
                "rating": rating,
                "genres": genres,
                "method": "",
                "theatre": VENUE["name"],
                "aud": "",
                "start": start,
                "url": url,
                "img": img,
                "lang": "FI-A" if dub else "",
                "soldOut": False,
                "price": _txt(price_raw.group(1)) if price_raw else "",
                "provider": "kinoakseli",
                "venue": VENUE["id"],
            })
    shows.sort(key=lambda s: s["start"])
    return shows


def fetch():
    req = urllib.request.Request(URL, headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    if len(page) < 5000 or "sgcaptcha" in page:
        raise RuntimeError("challenged (needs a residential IP)")
    return parse(page)


def fetch_site(site=SITES[0]):
    """Runner contract: one page, one screen, keyed by the venue id."""
    return {VENUE["id"]: fetch()}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = parse(open(src, encoding="utf-8", errors="replace").read()) if src else fetch()
    print(f"{len(data)} showtimes, {len({s['eventId'] for s in data})} films")
    for s in data:
        print(f"  {s['start'][:16]}  {s['title'][:34]:36} {s['rating']:6} "
              f"{s['price']:7} {s['lang']:5} {s['genres'][:28]}")
