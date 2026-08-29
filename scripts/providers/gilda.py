"""Gilda (Helsinki: Gilda salit 1-3, Bio Rex Lasipalatsi) — MyCloudCinema behind a
WordPress REST facade.

The listing is a React app whose config the page prints for anonymous visitors, so the
API needs no auth:

    GET {base}/wp-json/gilda-react-booking/v1/movies
    -> {"fi": {"data": [ {film..., show_times:[...]} ], "resultCode": 0}}

One request covers every film and showtime (35 films / 101 shows / 22 dates when probed).
The namespace also holds write and administrative routes. They are closed to anonymous
callers, are never called, and are not listed here.

Venues split by **cinema_screen_id**, not by cinema: there is one cinema_id (15) whose
screens 66/67/68 are Gilda 1-3 and screen 69 is the separate Bio Rex Lasipalatsi house.
Add another MyCloudCinema site as a SITES entry once its apiUrl and screen ids are known.

Notes from the fixture (2026-08-27):
- `rating_name` is bare: "12", "16", "S", plus "T" and "EI MÄÄR." for unrated. Map to the
  Finnkino-style tags the client filters on, and leave unrated blank.
- `screen_name` for Lasipalatsi carries "(K-18)", a venue door policy rather than a film
  rating. Strip it or every show there looks adults-only.
- `subtitle_lang` mixes Finnish words ("suomi, ruotsi"), ISO-ish codes ("FI", "SE") and
  "-" for none. `audio_lang` is always a code.
- `show_time` is UTC with a +00:00 offset; convert to Europe/Helsinki.
- Posters are a bare uuid; the React bundle names the host.
"""
import html as html_mod
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from common import fetch

FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

SITES = [{
    "provider": "gilda",
    "label": "Gilda",
    "base": "https://www.gilda.fi",
    "api": "/wp-json/gilda-react-booking/v1",
    "listing": "/elokuvat/",
    # Per-film pages live at /elokuva/{slug}/ as WordPress posts of type `movies`.
    # The booking API carries no slug and no permalink, so the mapping comes from the
    # WP REST list and is matched on the title.
    "posts": "/wp-json/wp/v2/movies",
    # MyCloudCinema poster path is {host}/media/posters/{movie_id}/{width}/{uuid}.
    # Only width 1080 exists; 720 and 500 are 404. The same shape serves BioRex
    # (web.biorex.mycloudcinema.com), which is how it was found after a bare
    # /media/posters/{uuid} guess from the React bundle returned 404 for every film.
    "posters": "https://web.atlanticfilm.mycloudcinema.com/media/posters",
    "poster_width": 1080,
    "venues": [
        # Kamppi (Narinkka 2) is how people locate it, and "Gilda Gilda" would be the
        # label otherwise: the client prefixes the chain onto `short` unless it already
        # starts with it.
        {"id": "gd-gilda", "screens": [66, 67, 68],
         "name": "Gilda Kamppi", "short": "Kamppi", "city": "Helsinki"},
        {"id": "gd-lasipalatsi", "screens": [69],
         "name": "Bio Rex Lasipalatsi", "short": "Bio Rex Lasipalatsi",
         "city": "Helsinki"},
    ],
}]

LANG = {"fi": "FI", "suomi": "FI", "en": "EN", "englanti": "EN", "sv": "SV",
        "se": "SV", "ruotsi": "SV", "ja": "JA", "japani": "JA", "fr": "FR",
        "ranska": "FR", "de": "DE", "saksa": "DE", "es": "ES", "espanja": "ES",
        "it": "IT", "italia": "IT", "ru": "RU", "venäjä": "RU", "da": "DA",
        "no": "NO", "et": "ET", "viro": "ET", "pl": "PL", "puola": "PL"}
# version_* flags worth showing as a format pill; the rest are noise
FORMATS = {"version_70mm": "70mm", "version_35mm": "35mm", "version_16mm": "16mm",
           "version_imax": "IMAX", "version_3d": "3D", "version_4k": "4K",
           "version_atmos": "Atmos", "version_luxe": "LUXE", "version_dbox": "D-BOX",
           "version_hfr": "HFR"}
TAGS_RE = re.compile(r"<[^>]+>")
ENTITIES = {"&#8211;": "-", "&#8217;": "'", "&#039;": "'", "&#8216;": "'",
            "&amp;": "&", "&nbsp;": " "}


def _key(title):
    """Loose title key for matching a film to its WordPress post."""
    t = TAGS_RE.sub(" ", title or "")
    for k, v in ENTITIES.items():
        t = t.replace(k, v)
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()


def _code(token):
    t = (token or "").strip().lower()
    return LANG.get(t, t.upper() if re.fullmatch(r"[a-zäöå]{2}", t) else "")


def _lang(show):
    """-> "EN-A, FI-S, SE-S" using Finnkino's tags, so one filter serves every provider."""
    out = []
    a = _code(show.get("audio_lang"))
    if a:
        out.append(a + "-A")
    raw = (show.get("subtitle_lang") or "").strip()
    if raw and raw != "-":
        for part in re.split(r"[,/]", raw):
            s = _code(part)
            if s and s + "-S" not in out:
                out.append(s + "-S")
    return ", ".join(out)


def _rating(show):
    """"12" -> "K-12", "S"/"T" -> "S", "EI MÄÄR." -> "" (unrated, say nothing)."""
    v = (show.get("rating_name") or "").strip()
    if not v or v.upper().startswith(("EI M", "EI_M")):
        return ""
    if v.upper() in ("S", "T"):
        return "S"
    m = re.search(r"(\d+)", v)
    return f"K-{m.group(1)}" if m else ""


def _start(show):
    raw = (show.get("show_time") or "").strip()
    if not raw:
        return ""
    t = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return t.astimezone(FI).isoformat()


def _aud(show, venue):
    """"Bio Rex Lasipalatsi (K-18)" -> "": the (K-18) is a door policy for that venue,
    not this film's rating, and a single-screen house whose screen name repeats the venue
    name must render blank or the stub reads "Bio Rex Lasipalatsi · Bio Rex Lasipalatsi".
    "Gilda 3" is kept, since it distinguishes one of three screens."""
    name = re.sub(r"\s*\(K-?\d+\)\s*$", "", (show.get("screen_name") or "").strip())
    low = name.lower()
    if low in (venue["short"].lower(), venue["name"].lower()):
        return ""
    return name


def _method(show):
    out = [label for flag, label in FORMATS.items() if show.get(flag)]
    style = (show.get("movie_audio_style_name") or "").strip()
    if style and style.lower() not in ("tekstitetty", "ei tekstitystä"):
        out.append(style)          # e.g. a dub tag; the plain cases are already in lang
    return ", ".join(out)


def get(url, tries=3, timeout=45):
    """MyCloudCinema REST, JSON. 45 s is passed through rather than left to common's
    30 s default: /movies returns the whole programme in one response.

    A malformed body still raises out of json.loads without a retry, same as before:
    common.fetch retries the request, not the parse, and a site answering 200 with
    non-JSON is a shape change to look at rather than a transient to sit out."""
    return json.loads(fetch(url, cache=True,
                            headers={"user-agent": UA, "accept": "application/json"},
                            tries=tries, timeout=timeout).decode("utf-8", "replace"))


def film_pages(site, tries=3):
    """-> {title key: permalink} for every /elokuva/{slug}/ page.

    Paginated at 100. A failure here is not fatal: showtimes fall back to the
    programme listing, which is what every show used before this existed.
    """
    base = site["base"].rstrip("/") + site.get("posts", "")
    out = {}
    for page in range(1, 6):
        url = f"{base}?per_page=100&page={page}&_fields=link,title"
        try:
            chunk = get(url, tries=tries)
        except Exception as e:
            if page == 1:
                print(f"[{site['provider']}] film pages unavailable: {e}")
            break
        if not isinstance(chunk, list) or not chunk:
            break
        for post in chunk:
            k = _key((post.get("title") or {}).get("rendered"))
            if k and k not in out:
                out[k] = post.get("link") or ""
        if len(chunk) < 100:
            break
    return out


def parse(payload, site, pages=None):
    """-> {venue_id: [show, ...]}"""
    by_screen = {}
    for v in site["venues"]:
        for sid in v["screens"]:
            by_screen[int(sid)] = v
    base = site["base"].rstrip("/")
    listing = base + site.get("listing", "/")
    posters = site.get("posters", "").rstrip("/")
    width = site.get("poster_width", 1080)

    pages = pages or {}
    doc = (payload.get("fi") or {}).get("data") or []
    per_venue = {}
    for film in doc:
        poster = (film.get("movie_poster") or "").strip()
        mid = film.get("movie_id")
        img = (f"{posters}/{mid}/{width}/{poster}"
               if (posters and poster and mid) else "")
        # description is HTML with entities: strip tags, then unescape, or the
        # synopsis renders as "Almod&oacute;var" in the movie sheet
        syn = html_mod.unescape(TAGS_RE.sub(" ", film.get("description") or ""))
        syn = re.sub(r"\s{2,}", " ", syn.replace("\xa0", " ")).strip()
        for s in film.get("show_times") or []:
            if s.get("deleted") or not s.get("show_is_visible", 1):
                continue
            venue = by_screen.get(int(s.get("cinema_screen_id") or 0))
            start = _start(s)
            if not venue or not start:
                continue
            # The film page, matched on its own title then the original title. That
            # second rule is what resolves a Finnish release title to an
            # English-slugged post ("Maailman rikkain nainen" ->
            # /elokuva/the-richest-woman-in-the-world-2/). No fuzzy matching: a
            # near-miss sends people to the wrong film, the fallback only costs a click.
            page = (pages.get(_key(s.get("movie_name") or film.get("movie_name")))
                    or pages.get(_key(s.get("original_title"))) or "")
            row = {
                "eventId": str(film.get("movie_id") or s.get("movie_id") or ""),
                "title": (s.get("movie_name") or film.get("movie_name") or "").strip(),
                "original": (s.get("original_title") or "").strip(),
                "len": str(s.get("running_time") or ""),
                "rating": _rating(s),
                "genres": (film.get("genre") or "").strip(),
                "method": _method(s),
                "theatre": venue["name"],
                "aud": _aud(s, venue),
                "start": start,
                "url": page or listing,
                "img": img,
                "lang": _lang(s),
                "soldOut": False,    # seat counts need the closed seatplan endpoint
                "price": "",
                "provider": site["provider"],
                "venue": venue["id"],
            }
            if syn:
                row["_syn"] = syn
            per_venue.setdefault(venue["id"], []).append(row)
    return per_venue


def fetch_site(site):
    url = site["base"].rstrip("/") + site.get("api", "") + "/movies"
    payload = get(url)
    pages = film_pages(site)
    print(f"[{site['provider']}] film pages indexed: {len(pages)}")
    return parse(payload, site, pages)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pages = {}
        if len(sys.argv) > 2:      # offline: a saved wp/v2/movies dump
            for post in json.load(open(sys.argv[2], encoding="utf-8")):
                pages.setdefault(_key((post.get("title") or {}).get("rendered")),
                                 post.get("link") or "")
        res = parse(json.load(open(sys.argv[1], encoding="utf-8")), SITES[0], pages)
    else:
        res = fetch_site(SITES[0])
    for vid, shows in sorted(res.items()):
        days = sorted({s["start"][:10] for s in shows})
        print(f"{vid}: {len(shows)} showtimes, {len(days)} dates -> {days[-1]}")
        for s in sorted(shows, key=lambda x: x["start"])[:3]:
            print(f"   {s['start'][:16]}  {s['title'][:28]:30} {s['rating']:5} "
                  f"{s['aud'][:20]:22} {s['lang']}")
