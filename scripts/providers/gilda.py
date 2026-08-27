"""Gilda (Helsinki: Gilda salit 1-3, Bio Rex Lasipalatsi) — MyCloudCinema behind a
WordPress REST facade.

The listing is a React app whose config the page prints for anonymous visitors, so the
API needs no auth:

    GET {base}/wp-json/gilda-react-booking/v1/movies
    -> {"fi": {"data": [ {film..., show_times:[...]} ], "resultCode": 0}}

One request covers every film and showtime (35 films / 101 shows / 22 dates when probed).
Everything write-side on that namespace (payment, lockSeat, setPurchase, transaction) is
closed to anonymous callers and is deliberately untouched here.

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
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

FI = ZoneInfo("Europe/Helsinki")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SITES = [{
    "provider": "gilda",
    "label": "Gilda",
    "base": "https://www.gilda.fi",
    "api": "/wp-json/gilda-react-booking/v1",
    "listing": "/elokuvat/",
    # MyCloudCinema poster path is {host}/media/posters/{movie_id}/{width}/{uuid}.
    # Only width 1080 exists; 720 and 500 are 404. The same shape serves BioRex
    # (web.biorex.mycloudcinema.com), which is how it was found after a bare
    # /media/posters/{uuid} guess from the React bundle returned 404 for every film.
    "posters": "https://web.atlanticfilm.mycloudcinema.com/media/posters",
    "poster_width": 1080,
    "venues": [
        {"id": "gd-gilda", "screens": [66, 67, 68],
         "name": "Gilda Helsinki", "short": "Gilda", "city": "Helsinki"},
        {"id": "gd-lasipalatsi", "screens": [69],
         "name": "Bio Rex Lasipalatsi", "short": "Bio Rex Lasipalatsi",
         "city": "Helsinki"},
    ],
}]

LANG = {"fi": "FI", "suomi": "FI", "en": "EN", "englanti": "EN", "sv": "SE",
        "se": "SE", "ruotsi": "SE", "ja": "JA", "japani": "JA", "fr": "FR",
        "ranska": "FR", "de": "DE", "saksa": "DE", "es": "ES", "espanja": "ES",
        "it": "IT", "italia": "IT", "ru": "RU", "venäjä": "RU", "da": "DA",
        "no": "NO", "et": "ET", "viro": "ET", "pl": "PL", "puola": "PL"}
# version_* flags worth showing as a format pill; the rest are noise
FORMATS = {"version_70mm": "70mm", "version_35mm": "35mm", "version_16mm": "16mm",
           "version_imax": "IMAX", "version_3d": "3D", "version_4k": "4K",
           "version_atmos": "Atmos", "version_luxe": "LUXE", "version_dbox": "D-BOX",
           "version_hfr": "HFR"}
TAGS_RE = re.compile(r"<[^>]+>")


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
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "user-agent": UA, "accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e
            if n + 1 < tries:
                time.sleep(5 * (n + 1))
    raise last


def parse(payload, site):
    """-> {venue_id: [show, ...]}"""
    by_screen = {}
    for v in site["venues"]:
        for sid in v["screens"]:
            by_screen[int(sid)] = v
    base = site["base"].rstrip("/")
    listing = base + site.get("listing", "/")
    posters = site.get("posters", "").rstrip("/")
    width = site.get("poster_width", 1080)

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
                "url": listing,      # no public per-show booking URL found yet
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
    return parse(get(url), site)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        res = parse(json.load(open(sys.argv[1], encoding="utf-8")), SITES[0])
    else:
        res = fetch_site(SITES[0])
    for vid, shows in sorted(res.items()):
        days = sorted({s["start"][:10] for s in shows})
        print(f"{vid}: {len(shows)} showtimes, {len(days)} dates -> {days[-1]}")
        for s in sorted(shows, key=lambda x: x["start"])[:3]:
            print(f"   {s['start'][:16]}  {s['title'][:28]:30} {s['rating']:5} "
                  f"{s['aud'][:20]:22} {s['lang']}")
