"""BioRex provider: WordPress admin-ajax, no auth. Stdlib only.

Venue selection is cookie-based: POST location={id} to /teatterin-valinta/ first.
Without that cookie the ajax endpoint silently returns BioRex Verkatehdas, so a
missing session yields wrong data rather than an error.
"""
import html as html_mod
import http.cookiejar, json, re, time, urllib.parse, urllib.request

BASE = "https://biorex.fi"
AJAX = BASE + "/wp-admin/admin-ajax.php?lang=fi"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

VENUES = [
    {"id": "br-tripla",      "providerId": "13", "name": "BioRex Tripla",      "short": "Tripla",      "city": "Helsinki"},
    {"id": "br-redi",        "providerId": "14", "name": "BioRex Redi",        "short": "Redi",        "city": "Helsinki"},
    {"id": "br-verkatehdas", "providerId": "1",  "name": "BioRex Verkatehdas", "short": "Verkatehdas", "city": "Hämeenlinna"},
    {"id": "br-sveitsi",     "providerId": "9",  "name": "BioRex Sveitsi",     "short": "Sveitsi",     "city": "Hyvinkää"},
    {"id": "br-kajaani",     "providerId": "7",  "name": "BioRex Kajaani",     "short": "Kajaani",     "city": "Kajaani"},
    {"id": "br-pietarsaari", "providerId": "4",  "name": "BioRex Pietarsaari", "short": "Pietarsaari", "city": "Pietarsaari"},
    {"id": "br-porvoo",      "providerId": "10", "name": "BioRex Porvoo",      "short": "Porvoo",      "city": "Porvoo"},
    {"id": "br-riihimaki",   "providerId": "8",  "name": "BioRex Riihimäki",   "short": "Riihimäki",   "city": "Riihimäki"},
    {"id": "br-rovaniemi",   "providerId": "2",  "name": "BioRex Rovaniemi",   "short": "Rovaniemi",   "city": "Rovaniemi"},
    {"id": "br-seinajoki",   "providerId": "12", "name": "BioRex Seinäjoki",   "short": "Seinäjoki",   "city": "Seinäjoki"},
    {"id": "br-tornio",      "providerId": "3",  "name": "BioRex Tornio",      "short": "Tornio",      "city": "Tornio"},
    {"id": "br-vaasa",       "providerId": "5",  "name": "BioRex Vaasa",       "short": "Vaasa",       "city": "Vaasa"},
]

# Note: the wrapper class carries a trailing space -> 'showtime-item '
ITEM_RE = re.compile(r'<div class="showtime-item\s*">(.*?)(?=<div class="showtime-item\s*">|\Z)', re.S)
# Double-quoted with &quot;-escaped JSON inside.
DL_RE = re.compile(r'data-click-data-layer="([^"]+)"')
# Attributes are newline-separated and href comes before class, so match the URL directly.
HREF_RE = re.compile(r'href="(https://biorex\.fi/secure-redirect/[^"]+)"')
PLACE_RE = re.compile(r'class="showtime-item__place__value">\s*(.*?)\s*</div>', re.S)
RATING_RE = re.compile(r'class="showtime-item__movie-rating">\s*\(?([^)<]*?)\)?\s*</span>', re.S)
FORMAT_RE = re.compile(r'class="showtime-item__format">(.*?)</span>', re.S)
SRCSET_RE = re.compile(r'data-srcset="([^"]+)"')
MOVIEURL_RE = re.compile(r'class="showtime-item__movie-name"[^>]*href="([^"]+)"')
TAGS_RE = re.compile(r"<[^>]+>")
# Format spans mix event/venue tags (Plus, Anniskelu, Senioribio…) with language codes
# (EN, FI&SV, ES). Language codes are the trailing all-caps tokens.
LANG_TOKEN_RE = re.compile(r"^[A-Z]{2}(?:&[A-Z]{2})*$")
WS_RE = re.compile(r"\s+")


def _text(s):
    return WS_RE.sub(" ", TAGS_RE.sub(" ", s)).strip()


def _split_formats(fmts):
    """-> (tags, audio, subs). Trailing caps tokens are languages; the rest are tags."""
    langs = []
    while fmts and LANG_TOKEN_RE.match(fmts[-1]):
        langs.insert(0, fmts.pop())
    audio = langs[0] if langs else ""
    subs = langs[1] if len(langs) > 1 else ""
    return fmts, audio, subs


def _lang_str(audio, subs):
    """Finnkino-compatible tags so the existing 'Suom. puhe' filter keeps working."""
    parts = [f"{a}-A" for a in audio.split("&") if a]
    parts += [f"{x}-S" for x in subs.split("&") if x]
    return ", ".join(parts)


def _poster(chunk):
    m = SRCSET_RE.search(chunk)
    if not m:
        return ""
    best, best_w = "", -1
    for part in m.group(1).split(","):
        bits = part.strip().split()
        if len(bits) == 2 and bits[1].endswith("w"):
            try:
                w = int(bits[1][:-1])
            except ValueError:
                continue
            if w > best_w:
                best, best_w = bits[0], w
    return best


def parse(posts_html, venue):
    """HTML fragment -> normalized showtime dicts."""
    shows = []
    for chunk in ITEM_RE.findall(posts_html):
        m = DL_RE.search(chunk)
        if not m:
            continue
        try:
            dl = json.loads(html_mod.unescape(m.group(1)))
        except Exception:
            continue
        start = dl.get("showDateTime") or ""
        if not start:
            continue
        place = _text(PLACE_RE.search(chunk).group(1)) if PLACE_RE.search(chunk) else ""
        aud = place.split(",")[-1].strip() if "," in place else place
        rating_raw = _text(RATING_RE.search(chunk).group(1)) if RATING_RE.search(chunk) else ""
        fmts = [f for f in (_text(x) for x in FORMAT_RE.findall(chunk)) if f]
        tags, audio, subs = _split_formats(fmts)
        href = HREF_RE.search(chunk)
        movie = MOVIEURL_RE.search(chunk)
        shows.append({
            "eventId": str(dl.get("movieId") or ""),
            "title": dl.get("movieName") or "?",
            "original": "",
            "len": "",
            "rating": rating_raw,
            "genres": "",
            "method": " · ".join(tags),
            "theatre": dl.get("showCinemaName") or venue["name"],
            "aud": aud,
            "start": start,
            "url": href.group(1) if href else (movie.group(1) if movie else BASE),
            "img": _poster(chunk),
            "lang": _lang_str(audio, subs),
            "soldOut": False,   # BioRex exposes no seat availability in this response
            "provider": "biorex",
            "venue": venue["id"],
        })
    return shows


def _opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _post(op, url, data):
    req = urllib.request.Request(
        url, data=urllib.parse.urlencode(data).encode(),
        headers={"user-agent": UA, "accept": "*/*",
                 "content-type": "application/x-www-form-urlencoded",
                 "referer": BASE + "/elokuvat/"})
    with op.open(req, timeout=30) as r:
        return r.read()


def fetch_venue(venue):
    op = _opener()
    op.open(urllib.request.Request(BASE + "/elokuvat/", headers={"user-agent": UA}),
            timeout=30).read()
    _post(op, BASE + "/teatterin-valinta/", {"location": venue["providerId"]})
    raw = _post(op, AJAX, {"action": "br_movies_handler", "genre": "-1", "date": "-1",
                           "format": "-1", "language": "-1", "activeType": "showtimes"})
    payload = json.loads(raw.decode("utf-8", "replace"))
    shows = parse(payload.get("posts") or "", venue)
    # Cookie failure shows up as another venue's data, so verify before trusting it.
    names = {s["theatre"] for s in shows}
    if names and venue["name"] not in names:
        raise RuntimeError(f"venue mismatch: asked {venue['name']}, got {sorted(names)}")
    return shows


def fetch_all(sleep=0.6):
    out = {}
    for v in VENUES:
        try:
            out[v["id"]] = fetch_venue(v)
            print(f"[biorex] {v['name']}: {len(out[v['id']])} showtimes")
        except Exception as e:
            print(f"[biorex] {v['name']} FAILED: {e}")
        time.sleep(sleep)
    return out
