"""The City of Helsinki's culture centres: Kino Helios at Malmitalo, Vuotalo and Kanneltalo.
Stdlib only.

All three houses belong to the city's culture and leisure division: Linked Events names one
publisher for every row read here, `ahjo:u48040010` "Kulttuuripalvelukokonaisuus", and
Kanneltalo's own footer lists the three among the division's houses (read 2026-10-24,
issue #16). One provider holds them, keeping the `helios` id and the `helios-helsinki`
venue, and each house is read by GET from the City's open Linked Events API by its place,
paged by `meta.next`:

    https://api.hel.fi/linkedevents/v1/event/?location=tprek:8740&start=YYYY-MM-DD
        &end=YYYY-MM-DD&page_size=100&sort=start_time

Until 2026-10-21 this read the POST the house's own calendar made, `GetEvents` on
www.malmitalo.fi. From 15:26 UTC that day the host redirected to the city's outage copy and
the POST answered 404, while this API carried the same twelve screenings. The answer is the
whole house's programme: concerts, courses, exhibitions and the cinema together. The data is
CC BY 4.0 by the API's own front page, read 2026-10-21, and its credit is on /status/.

Which rows of each house are cinema, read 2026-10-24:

- **Malmitalo**: `... – Kino Helios`, and `HopeaCine: ...`, whose ticket the house sells as
  "Kino Helios esittää". The series also screens at Vuotalo and at Cinema Orion, which has
  its own provider. The house's other strands, `Yleisön suosikit` and `Joululomaleffa`,
  stay out.
- **Vuotalo**: `HopeaCine: ...`.
- **Kanneltalo**: `... – Kino Kuutamo | Maksuttomat maanantait`, free Monday screenings.
  The strand after the dash names neither the house nor the venue, so it is kept in
  `method`, where Kino Helios's suffix is the venue's own name and goes nowhere.

A series row leaves here with its prefix, and run.py's central pass moves `HopeaCine`, a
registered strand in `strands.py`, into `method` before anything is written. A row whose
offer says `is_free` is published as free entry; any other offer amount is not a price, as
below.

What shapes the parser, measured on the live API 2026-10-21:

- **Three fields pick this cinema out**, and all three are needed: the place, the keyword
  `kulke:29` ("Elokuvat", the old calendar's film type 29), and a Finnish name ending
  `– Kino Helios`. The place held 100 events over 90 days, 21 with that keyword: 12 Kino
  Helios, 3 `HopeaCine: ...`, 2 `Yleisön suosikit` and 4 `Joululomaleffa: ...`, which are
  other strands of the same house, as `Doc Helios` was on the old calendar.
- **`start_time` is a UTC instant**, `2026-10-21T12:00:00Z` for the 15.00 screening. A
  value with no offset, or a date alone, is left out and counted: nothing here states the
  clock a second time, so no zone is guessed.
- **The age limit is a suffix on the title**, `Kerro kaikille (12) – Kino Helios`. It is
  read into `rating` and taken off the published title, because the title is the key for
  `normTitle()`, `films-extra.json` and the combined city view: the same film screens
  elsewhere without the house's age marker. `enrich_tmdb.clean` does not strip a bare
  `(12)` and is not changed for this.
- **No runtime is published.** `end_time` and the description's `Kesto` line are not read,
  and `len` stays empty as it did on the old service.
- **No price is published.** Each row's offer states one amount, `9 €` or `7 €`, but the
  house's own Kino Helios page gave its tariff as a floor, "alkaen 9 EUR" (2026-09-18), so
  the amount does not settle what a given screening costs.
- **The language is in the description.** `description.fi` ends with the film's facts,
  `Kieli: suomi <br>Tekstitys: suomi`, the lines the house's own event record carried and
  this module read one POST per screening for. One listing now settles all of them.
- **The synopsis declares its language.** `common.syn_language` places
  `short_description` and withholds it when nothing is settled.
- **No hall is named.** `location_extra_info` was empty on all twelve rows, so `aud` is
  that field or empty.
- **The house writes state into the name.** Two other events at the place that day read
  `LOPPUUN MYYTY Antti Autio: ...` and `... kurssi PERUTTU`. On a film either would key
  as another title, so a leading `LOPPUUN MYYTY` sets `soldOut` and comes off, and a row
  saying `PERUTTU`, or whose `event_status` is cancelled or postponed, is left out and
  counted. Every row read said `EventScheduled` or `EventRescheduled`, so the status is
  not read for anything else.
- **The images are `event_only`** and not published.

**Zero rows fails the site.** The API answers the whole house, so zero Kino Helios rows
among a payload full of other events is as consistent with a renamed strand as with a dark
fortnight, and this reader cannot tell those apart. `common.EmptyProgramme` takes positive
evidence and there is none here.

**`book="buy"`.** Every row carries a `lippu.fi` ticket link in its offer.
"""
import datetime
import html
import json
import re
import sys
import time
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

from common import UA, check_shows, fetch, get_text, syn_language
from etiketti import strict_codes

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "helios", "label": "Helsingin kulttuurikeskukset",
     "base": "https://api.hel.fi",
     "path": "/linkedevents/v1/event/",
     "keyword": "kulke:29",
     # One entry per house: `strand` is a name suffix after a dash, `series` a title prefix
     # before a colon. The first entry is Malmitalo, the provider's original venue.
     "places": [
         {"place": "tprek:8740", "venue": "helios-helsinki", "strand": "Kino Helios",
          "series": "HopeaCine"},
         {"place": "tprek:7260", "venue": "vuotalo-helsinki", "series": "HopeaCine"},
         {"place": "tprek:7255", "venue": "kanneltalo-helsinki", "strand": "Kino Kuutamo"},
     ],
     "venues": [{"id": "helios-helsinki", "name": "Kino Helios", "short": "Kino Helios",
                 "city": "Helsinki"},
                {"id": "vuotalo-helsinki", "name": "Vuotalo", "short": "Vuotalo",
                 "city": "Helsinki"},
                {"id": "kanneltalo-helsinki", "name": "Kanneltalo", "short": "Kanneltalo",
                 "city": "Helsinki"}]},
]

# Days ahead to ask for. The old calendar reached 33 days out; 90 is one page of 100 events
# at this place, measured 2026-10-21.
HORIZON = 90
PAGE_SIZE = 100
# The listing carries the schedule, so a place that outgrows this fails instead of
# publishing the front of its programme.
MAX_PAGES = 5
PAUSE = 1.0

# A trailing age limit in brackets: `(7)`, `(12)`, `(S)`.
AGE_RE = re.compile(r"\s*\((S|\d{1,2})\)\s*$", re.I)
SOLD_OUT_RE = re.compile(r"^LOPPUUN\s*MYYTY\s*[:\-–]?\s*", re.I)
CANCELLED_RE = re.compile(r"\bPERUTTU\b", re.I)
OFF_STATUS = ("EventCancelled", "EventPostponed")
FIELD_RE = re.compile(r"(Kieli|Tekstitys)\s*:\s*([^<\r\n]+)", re.I)
# The dubbed films say "Kieli: puhuttu suomeksi" (Unohdettu saari, 2026-10-21).
SPOKEN_RE = re.compile(r"^puhuttu\s+", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def strand_title(name, strand):
    """`Kerro kaikille (12) – Kino Helios` -> `Kerro kaikille (12)`, or None for a name
    that does not end with the strand."""
    got = strand_split(name, strand)
    return got[0] if got else None


def strand_split(name, strand):
    """`Isänpäivä – Kino Kuutamo | Maksuttomat maanantait` -> ("Isänpäivä", "Kino Kuutamo |
    Maksuttomat maanantait"), or None for a name that does not end with the strand."""
    m = re.match(rf"^(.*?)\s+[–-]\s+({re.escape(strand)}(?:\s*\|\s*.+)?)$",
                 (name or "").strip())
    return (m.group(1).strip(), m.group(2).strip()) if m else None


def match(name, place, venue):
    """A row's Finnish name -> (title, method) for a strand or series of this house, or
    None. A strand that is the venue's own name goes in no `method`."""
    if place.get("strand"):
        got = strand_split(name, place["strand"])
        if got:
            title, tail = got
            return title, "" if tail == venue["name"] else tail
    series = place.get("series")
    if series and re.match(rf"^{re.escape(series)}\s*:", (name or "").strip()):
        return (name or "").strip(), ""
    return None


def split_title(title):
    """`Hetki ennen valoa (7)` -> ("Hetki ennen valoa", "K-7"). No suffix -> rating ""."""
    t = (title or "").strip()
    m = AGE_RE.search(t)
    if not m:
        return t, ""
    rest = t[:m.start()].strip()
    if not rest:
        return t, ""
    mark = m.group(1).upper()
    return rest, "S" if mark == "S" else f"K-{int(mark)}"


def instant(value):
    """`2026-10-21T12:00:00Z` -> an aware Helsinki datetime, or None for a date alone or a
    clock with no offset."""
    try:
        dt = datetime.datetime.fromisoformat((value or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(FI) if dt.tzinfo else None


def fi(field):
    """A Linked Events translated field -> its Finnish text, or ""."""
    return ((field or {}).get("fi") or "").strip() if isinstance(field, dict) else ""


def plain(text):
    return html.unescape(TAG_RE.sub(" ", text or "")).strip()


def language(description):
    """`description.fi` -> "FI-A, FI-S", or "" for what it does not state in names every
    word of which is a language."""
    got = {k.lower(): SPOKEN_RE.sub("", v.strip()) for k, v in FIELD_RE.findall(description)}
    parts = [f"{c}-A" for c in strict_codes(got.get("kieli"))]
    parts += [f"{c}-S" for c in strict_codes(got.get("tekstitys"))]
    return ", ".join(parts)


def rows(site, events, today=None, place=None):
    """-> (shows, report). One row per screening one house publishes; the first house
    when `place` is not given."""
    place_cfg = place or site["places"][0]
    venue = next(v for v in site["venues"] if v["id"] == place_cfg["venue"])
    place = f"/place/{place_cfg['place']}/"
    keyword = f"/keyword/{site['keyword']}/"
    out = []
    report = {"rows": 0, "mine": 0, "unreadable": 0, "cancelled": 0}
    for event in events:
        report["rows"] += 1
        if not isinstance(event, dict):
            continue
        got = match(fi(event.get("name")), place_cfg, venue)
        title, method = got if got else (None, "")
        if (title is None
                or not ((event.get("location") or {}).get("@id") or "").endswith(place)
                or not any((k.get("@id") or "").endswith(keyword)
                           for k in event.get("keywords") or [] if isinstance(k, dict))):
            continue
        report["mine"] += 1
        if event.get("event_status") in OFF_STATUS or CANCELLED_RE.search(title):
            report["cancelled"] += 1
            continue
        start = instant(event.get("start_time"))
        if start is None:
            report["unreadable"] += 1
            continue
        sold = bool(SOLD_OUT_RE.match(title))
        title, rating = split_title(SOLD_OUT_RE.sub("", title))
        offer = next((o for o in event.get("offers") or [] if isinstance(o, dict)), {})
        free = offer.get("is_free") is True
        show = {
            "eventId": str(event.get("id") or ""),
            "title": title,
            "original": "",
            "len": "",
            "rating": rating,
            "genres": "",
            "method": method,
            "theatre": venue["name"],
            "aud": fi(event.get("location_extra_info")),
            "start": start.isoformat(),
            "url": fi(offer.get("info_url")) or fi(event.get("info_url")),
            "img": "",
            "lang": language(fi(event.get("description"))),
            "soldOut": sold,
            "price": "Vapaa pääsy" if free else "",
            "provider": site["provider"],
            "venue": venue["id"],
        }
        syn = plain(fi(event.get("short_description")))
        if syn:
            lang = syn_language(syn)
            if lang:
                show["_syn"] = {lang: syn}
        out.append(show)
    out.sort(key=lambda s: (s["start"], s["title"]))
    return out, report


def listing(site, today=None, place=None):
    """Every event at one house in the window, one paged query. -> list."""
    today = today or datetime.datetime.now(FI).date()
    place = place or site["places"][0]
    query = urlencode({"location": place["place"], "start": today.isoformat(),
                       "end": (today + datetime.timedelta(days=HORIZON)).isoformat(),
                       "page_size": PAGE_SIZE, "sort": "start_time"}, safe=":")
    events = []
    for n in range(MAX_PAGES):
        if n:
            time.sleep(PAUSE)
        answer = json.loads(get_text(f"{site['base']}{site['path']}?{query}", fetcher=fetch,
                                     cache=False,
                                     headers={"accept": "application/json", "user-agent": UA}))
        events += answer.get("data") or []
        nxt = (answer.get("meta") or {}).get("next")
        if not nxt:
            return events
        # The next page's query, asked of the declared host whatever host the link names.
        query = urlsplit(nxt).query
    raise RuntimeError(f"Linked Events has more than {MAX_PAGES} pages for place "
                       f"{place['place']}")


def fetch_site(site, today=None):
    """Runner contract: each house's listing, one GET per page of 100 events."""
    pid = site["provider"]
    per_venue, total, mine = {}, 0, 0
    for n, place in enumerate(site["places"]):
        if n:
            time.sleep(PAUSE)
        venue = next(v for v in site["venues"] if v["id"] == place["venue"])
        shows, report = rows(site, listing(site, today, place), today, place)
        per_venue[venue["id"]] = shows
        total, mine = total + report["rows"], mine + report["mine"]
        days = sorted({s["start"][:10] for s in shows})
        print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
              f"{len(days)} dates, {sum(1 for s in shows if s['lang'])} with a language, "
              f"{report['mine']} of {report['rows']} event(s) are this house's cinema")
        for key, note in (("cancelled", "row(s) cancelled or postponed, left out"),
                          ("unreadable", "row(s) whose start is not a timed instant, left out")):
            if report[key]:
                print(f"[{pid}] {venue['name']}: {report[key]} {note}")
    if not any(per_venue.values()):
        raise RuntimeError(
            f"{site['base']}{site['path']}: no cinema row among {total} event(s) at "
            f"{len(site['places'])} houses. The API answers the whole house, so an empty "
            f"result is as consistent with a renamed strand as with a dark fortnight and the "
            f"previous files stand")
    check_shows(per_venue, pid, {v["id"] for v in site["venues"]})
    return per_venue

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        with open(src, encoding="utf-8") as fh:
            shows, report = rows(SITES[0], json.load(fh)["data"])
        print(report)
    else:
        shows = fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]
    for s in shows:
        print(f"   {s['start'][:16]}  {s['title'][:38]:40} {s['rating']:5} {s['lang'][:16]:18} "
              f"{s['url'][-30:]}")
    sys.exit(0)
