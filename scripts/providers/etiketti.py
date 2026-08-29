"""eTiketti platform adapter (etiketti.app powers several Finnish cinema sites).

The etiketti.app API host sits behind Cloudflare, but the cinema's own site is
server-rendered and fetchable, so this parses the public pages:

  /elokuvat/ohjelmistossa   -> movie links  /elokuvat/{id}/{slug}
  /elokuvat/{id}/{slug}     -> every screening for that film, with room, price,
                               free seats and a booking link

Adding another eTiketti cinema = an entry in SITES.
"""
import datetime, html as html_mod, json, re, time
from zoneinfo import ZoneInfo

from common import budget_or_raise, fetch

FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

SITES = [
    {"provider": "kotkanleffat", "base": "https://kotkanleffat.fi", "label": "Kotkan Leffat",
     "venues": [
         {"id": "kl-kinopalatsi", "match": "kinopalatsi", "name": "Kinopalatsi Kotka",
          "short": "Kinopalatsi", "city": "Kotka"},
         {"id": "kl-trio123", "match": "trio 123", "name": "Trio 123",
          "short": "Trio 123", "city": "Kotka"},
     ]},
    # One cinema, three rooms (DIGI 1, DIGI 2, SALI 3), all reported under the single
    # place name "BIO 1&2 REX". A room is not a venue, so this is one entry and the
    # room lands in `aud` verbatim, the way it is printed on the ticket.
    {"provider": "biorexkokkola", "base": "https://www.biorex.org", "label": "Bio Rex Kokkola",
     "venues": [
         {"id": "bx-kokkola", "match": "rex", "name": "Bio Rex Kokkola",
          "short": "Bio Rex Kokkola", "city": "Kokkola"},
     ]},
]

MOVIE_LINK_RE = re.compile(r'href="(/elokuvat/(\d+)/[a-z0-9-]+)"')
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
ITEM_RE = re.compile(r'<div class="item [^"]*date-(\d{1,2})\.(\d{1,2})\.(\d{4})"(.*?)(?=<div class="item |</div>\s*</div>\s*</div>|\Z)', re.S)
TIME_RE = re.compile(r"klo\s*(\d{1,2})[.:](\d{2})")
# Trio 123 screenings read "TRIO 123 | SALI 1"; Kinopalatsi has no room at all.
PLACE_RE = re.compile(r"<p>\s*([^<|]+?)\s*(?:\|\s*([^<]+?)\s*)?<br", re.S)
PRICE_RE = re.compile(r"Lippu\s*([\d,\.]+)")
SEATS_RE = re.compile(r"Vapaat paikat\s*(\d+)\s*/\s*(\d+)")
BOOK_RE = re.compile(r'href="(/salikartta\?id=\d+)"')
AGE_RE = re.compile(r"ikarajat/fi-(\d+|s)\.svg", re.I)
DUR_RE = re.compile(r"Kesto:</span>\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*min)?", re.I)
LANGV_RE = re.compile(r"Kieli:</span>\s*([^<]+)", re.I)
SUBS_RE = re.compile(r"Tekstitys:</span>\s*([^<]+)", re.I)
POSTER_RE = re.compile(r'<img class="poster-img" src="([^"]+)"')
GENRES_RE = re.compile(r'<span class="movie-genre">([^<]+)</span>')
DESC_RE = re.compile(r'class="description-container[^"]*"[^>]*>\s*<span>(.*?)</span>', re.S)
# The description opens with an age-limit boilerplate line; drop it.
AGE_BOILER_RE = re.compile(r"^Elokuva on [^.]*\.[^.]*\.\s*", re.S)
TAGS_RE = re.compile(r"<[^>]+>")


def _txt(x):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", x or ""))).strip()


def get(url, tries=3):
    """Server-rendered HTML. common.fetch supplies the retry: same tries=3 and the
    same 5 s * n backoff and 30 s timeout this loop had, so behaviour is unchanged."""
    return fetch(url, headers={
        "user-agent": UA, "accept-language": "fi-FI,fi;q=0.9",
        "accept": "text/html,application/xhtml+xml"}, tries=tries,
        cache=True).decode("utf-8", "replace")


def _lang(page):
    """'Alkuperäinen' / 'Suomi ja ruotsi' -> Finnkino-style tags."""
    def codes(v):
        v = (v or "").lower()
        out = []
        if "suomi" in v or "suom" in v:
            out.append("FI")
        if "ruotsi" in v or "ruots" in v:
            # SV: the ISO 639-1 code for Swedish. SE is Sweden the country, which this
            # app used to use because Finnkino does.
            out.append("SV")
        if "englan" in v:
            out.append("EN")
        return out
    a = LANGV_RE.search(page)
    s = SUBS_RE.search(page)
    av = _txt(a.group(1)) if a else ""
    parts = [f"{c}-A" for c in codes(av)]
    if not parts and "alkuper" in av.lower():
        parts = []                       # original version: audio language unstated
    parts += [f"{c}-S" for c in (codes(_txt(s.group(1))) if s else [])]
    return ", ".join(parts)


def parse_movie(page, site, movie_url):
    """-> (list of raw screenings, film meta)."""
    h1 = H1_RE.search(page)
    title = _txt(h1.group(1)) if h1 else ""
    age = AGE_RE.search(page)
    rating = ""
    if age:
        a = age.group(1).lower()
        rating = "S" if a == "s" else f"K-{a}"
    dur = DUR_RE.search(page)
    minutes = ""
    if dur and (dur.group(1) or dur.group(2)):
        minutes = str(int(dur.group(1) or 0) * 60 + int(dur.group(2) or 0))
    poster = POSTER_RE.search(page)
    img = poster.group(1).split("?")[0] if poster else ""
    lang = _lang(page)
    genres = ", ".join(dict.fromkeys(_txt(g) for g in GENRES_RE.findall(page) if _txt(g)))
    d = DESC_RE.search(page)
    syn = AGE_BOILER_RE.sub("", _txt(d.group(1))) if d else ""

    out = []
    for m in ITEM_RE.finditer(page):
        d, mo, y, block = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
        tm = TIME_RE.search(block)
        if not tm:
            continue
        place = PLACE_RE.search(block)
        theatre = _txt(place.group(1)) if place else ""
        room = _txt(place.group(2)) if (place and place.group(2)) else ""
        price = PRICE_RE.search(block)
        seats = SEATS_RE.search(block)
        book = BOOK_RE.search(block)
        out.append({
            "theatre_raw": theatre, "aud": room,
            "start": datetime.datetime(y, mo, d, int(tm.group(1)), int(tm.group(2)),
                                       tzinfo=FI).isoformat(),
            "price": (price.group(1).replace(",", ".").rstrip("0").rstrip(".") + "\u20ac"
                      if price else ""),
            "free": int(seats.group(1)) if seats else None,
            "url": site["base"] + (book.group(1) if book else movie_url),
        })
    return out, {"title": title, "rating": rating, "len": minutes, "img": img,
                 "lang": lang, "genres": genres, "syn": syn}


def fetch_site(site, sleep=1.2):
    listing = get(site["base"] + "/elokuvat/ohjelmistossa")
    seen, movies = set(), []
    for path, mid in MOVIE_LINK_RE.findall(listing):
        if mid not in seen:
            seen.add(mid); movies.append((path, mid))

    per_venue = {v["id"]: [] for v in site["venues"]}
    for path, mid in budget_or_raise(movies, site['provider']):
        try:
            page = get(site["base"] + path)
        except Exception as e:
            print(f"[{site['provider']}] movie {mid}: {e}")
            continue
        rows, meta = parse_movie(page, site, path)
        for r in rows:
            hay = f"{r['theatre_raw']} {r['aud']}".lower()
            venue = next((v for v in site["venues"] if v["match"] in hay), None)
            if not venue:
                continue
            per_venue[venue["id"]].append({
                "eventId": mid,
                "title": meta["title"] or "?",
                "original": "",
                "len": meta["len"],
                "rating": meta["rating"],
                "genres": meta["genres"],
                "method": "",
                "theatre": venue["name"],
                "aud": r["aud"],
                "start": r["start"],
                "url": r["url"],
                "img": meta["img"],
                "lang": meta["lang"],
                "soldOut": r["free"] == 0,
                "price": r["price"],
                "provider": site["provider"],
                "venue": venue["id"],
                "_syn": meta["syn"],
            })
        time.sleep(sleep)

    for k in per_venue:
        per_venue[k].sort(key=lambda s: s["start"])
    return {k: v for k, v in per_venue.items() if v}
