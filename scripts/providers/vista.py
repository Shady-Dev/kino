"""Vista public XML web services — a *platform*, not a site.

Vista is the ticketing system behind Finnkino, and its web front end exposes a set of
unauthenticated XML endpoints. Savon Kinot leaves them open, so any other Vista cinema
that does the same is a `SITES` entry here with a base URL and its venue list, no new
parser. Check `{base}/xml/TheatreAreas/` before adding one.

    GET {base}/xml/TheatreAreas/                     -> ID + Name per area
    GET {base}/xml/Schedule/?area={id}&nrOfDays=31    -> every Show in the window
    GET {base}/xml/ScheduleDates/                    -> the published date list
    GET {base}/xml/Events/                           -> per-film synopsis and credits

Notes from probing savonkinot.fi (2026-08-27):
- `nrOfDays=31` is honoured, so **one request per area** covers the whole published
  window (8 days in practice). Areas map to one or two theatres each, and the response
  carries `TheatreID`, so venues are split from the data rather than by request.
- A one-day fetch is not enough: Kitee had zero shows today and seven in the window.
- No auth, no Cloudflare, and a datacenter IP works, unlike Finnkino's own OCAPI. This
  runs on Actions.
- `Rating` is "K-7 (4)" or "Sallittu kaikenikäisille", not Finnkino's bare "K-7", so it
  needs normalising or the kids filter in the client silently stops matching.
- Times come as both local and UTC. Parse the UTC one and convert, so DST is never our
  problem.
- `SubtitleLanguage2` can carry a Name with an empty ISOTwoLetterCode, so fall back to
  mapping the Finnish language name.
"""
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from common import fetch

FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

SITES = [{
    "provider": "savonkinot",
    "label": "Savon Kinot",
    "base": "https://www.savonkinot.fi",
    "days": 31,
    # area = TheatreArea id in the XML, theatre = TheatreID on each Show
    "venues": [
        {"id": "sk-tapio",     "area": "1006", "theatre": "1038",
         "name": "Tapio Joensuu",       "short": "Tapio",     "city": "Joensuu"},
        {"id": "sk-killa",     "area": "1003", "theatre": "1042",
         "name": "Killa Savonlinna",    "short": "Killa",     "city": "Savonlinna"},
        {"id": "sk-kuvalinna", "area": "1003", "theatre": "1044",
         "name": "Kuvalinna Savonlinna", "short": "Kuvalinna", "city": "Savonlinna"},
        {"id": "sk-kuvalipas", "area": "1002", "theatre": "1040",
         "name": "Kuvalipas Iisalmi",   "short": "Kuvalipas", "city": "Iisalmi"},
        {"id": "sk-maxim",     "area": "1005", "theatre": "1039",
         "name": "Maxim Varkaus",       "short": "Maxim",     "city": "Varkaus"},
        {"id": "sk-kinohovi",  "area": "1004", "theatre": "1043",
         "name": "Kino-Hovi Kitee",     "short": "Kino-Hovi", "city": "Kitee"},
    ],
}]

# Finnkino's tag set, so one language filter works across every provider.
ISO = {"fi": "FI", "en": "EN", "sv": "SV", "se": "SV", "ja": "JA", "fr": "FR",
       "de": "DE", "es": "ES", "it": "IT", "ru": "RU", "da": "DA", "no": "NO",
       "et": "ET", "pl": "PL"}
NAMES = {"suomi": "FI", "englanti": "EN", "ruotsi": "SV", "japani": "JA",
         "ranska": "FR", "saksa": "DE", "espanja": "ES", "italia": "IT",
         "venäjä": "RU", "tanska": "DA", "norja": "NO", "viro": "ET", "puola": "PL"}
TAGS_RE = re.compile(r"<[^>]+>")


def _txt(node, *path):
    for tag in path:
        if node is None:
            return ""
        node = node.find(tag)
    return (node.text or "").strip() if node is not None else ""


def _code(node, tag):
    """Language code from a SpokenLanguage / SubtitleLanguageN node."""
    sub = node.find(tag)
    if sub is None:
        return ""
    iso = (_txt(sub, "ISOTwoLetterCode") or "").lower()
    if iso in ISO:
        return ISO[iso]
    return NAMES.get((_txt(sub, "Name") or "").lower(), "")


def _lang(show):
    """-> "EN-A, FI-S, SE-S". Audio first, then each subtitle track."""
    out = []
    a = _code(show, "SpokenLanguage")
    if a:
        out.append(a + "-A")
    for tag in ("SubtitleLanguage1", "SubtitleLanguage2"):
        s = _code(show, tag)
        if s and s + "-S" not in out:
            out.append(s + "-S")
    return ", ".join(out)


def _rating(v):
    """"K-7 (4)" -> "K-7", "Sallittu kaikenikäisille" -> "S"."""
    v = (v or "").strip()
    if not v:
        return ""
    if v.lower().startswith(("sallittu", "s ")) or v.upper() == "S":
        return "S"
    m = re.search(r"K[-\s]?(\d+)", v)
    return f"K-{m.group(1)}" if m else v


def _start(show):
    """UTC in, Helsinki ISO out, so DST is the library's problem and not ours."""
    raw = _txt(show, "dttmShowStartUTC")
    if raw:
        t = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return t.astimezone(FI).isoformat()
    local = _txt(show, "dttmShowStart")          # fallback: assume it is already local
    if not local:
        return ""
    return datetime.fromisoformat(local).replace(tzinfo=FI).isoformat()


def _aud(show, venue):
    """"Joensuu, Tapio 4" -> "Tapio 4". Blank when it only repeats the venue name."""
    raw = _txt(show, "TheatreAuditorium")
    name = raw.split(",", 1)[1].strip() if "," in raw else raw.strip()
    return "" if name.lower() == venue["short"].lower() else name


def _https(url):
    return re.sub(r"^http://", "https://", (url or "").strip())


def get(url, tries=3, timeout=40):
    """Vista's XML web services. The 40 s timeout is passed through rather than left to
    common's 30 s default: a whole area's Schedule response is large and slow."""
    return fetch(url, cache=True,
                 headers={"user-agent": UA, "accept": "application/xml, text/xml, */*"},
                 tries=tries, timeout=timeout).decode("utf-8", "replace")


def parse_schedule(xml_text, site, venues):
    """-> {venue_id: [show, ...]} for the venues present in this area's response."""
    per_venue = {}
    by_theatre = {v["theatre"]: v for v in venues}
    root = ET.fromstring(xml_text)
    shows = root.find("Shows")
    for s in (shows if shows is not None else []):
        venue = by_theatre.get(_txt(s, "TheatreID"))
        if not venue:
            continue        # another theatre in the same area that we do not list
        start = _start(s)
        if not start:
            continue
        img = _https(_txt(s, "Images", "EventMediumImagePortrait")
                     or _txt(s, "Images", "EventSmallImagePortrait"))
        method = ", ".join(x for x in (_txt(s, "PresentationMethod"),
                                       _txt(s, "EventSeries")) if x)
        per_venue.setdefault(venue["id"], []).append({
            "eventId": _txt(s, "EventID"),
            "title": _txt(s, "Title"),
            "original": _txt(s, "OriginalTitle"),
            "len": _txt(s, "LengthInMinutes"),
            "rating": _rating(_txt(s, "Rating")),
            "genres": _txt(s, "Genres"),
            "method": method,
            "theatre": venue["name"],
            "aud": _aud(s, venue),
            "start": start,
            "url": _https(_txt(s, "ShowURL")),
            "img": img,
            "lang": _lang(s),
            "soldOut": False,          # seat counts are not in the public XML
            "price": "",
            "provider": site["provider"],
            "venue": venue["id"],
        })
    return per_venue


def synopses(xml_text):
    """-> {EventID: finnish synopsis}. Tag names vary between Vista versions, so try a
    few and treat a miss as "no synopsis" rather than an error: TMDB fills the gap."""
    out = {}
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return out
    for e in root.iter("Event"):
        eid = _txt(e, "ID")
        if not eid:
            continue
        for tag in ("Synopsis", "ShortSynopsis", "SynopsisShort", "Description"):
            text = _txt(e, tag)
            if text:
                out[eid] = TAGS_RE.sub(" ", text).replace("&nbsp;", " ").strip()
                break
    return out


def fetch_site(site, sleep=1.5):
    base = site["base"].rstrip("/")
    days = site.get("days", 31)
    venues = site["venues"]

    syn = {}
    try:
        syn = synopses(get(f"{base}/xml/Events/"))
    except Exception as e:
        print(f"[{site['provider']}] Events unavailable, TMDB will cover it: {e}")

    per_venue = {}
    areas = []
    for v in venues:                    # preserve order, one request per distinct area
        if v["area"] not in areas:
            areas.append(v["area"])
    for area in areas:
        here = [v for v in venues if v["area"] == area]
        xml_text = get(f"{base}/xml/Schedule/?area={area}&nrOfDays={days}")
        for vid, shows in parse_schedule(xml_text, site, here).items():
            per_venue.setdefault(vid, []).extend(shows)
        time.sleep(sleep)

    for shows in per_venue.values():
        for s in shows:
            text = syn.get(s["eventId"])
            if text:
                s["_syn"] = text
    return per_venue


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) > 1:               # offline: parse a saved Schedule response
        body = open(sys.argv[1], encoding="utf-8", errors="replace").read()
        res = parse_schedule(body, SITES[0], SITES[0]["venues"])
    else:
        res = fetch_site(SITES[0])
    for vid, shows in sorted(res.items()):
        print(f"{vid}: {len(shows)} showtimes")
        for s in shows[:3]:
            print(f"   {s['start'][:16]}  {s['title'][:30]:32} {s['rating']:5} "
                  f"{s['aud']:12} {s['lang']}")
    print(json.dumps(next(iter(res.values()))[0], ensure_ascii=False, indent=1))
