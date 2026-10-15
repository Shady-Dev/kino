"""Kannusali, Espoo's culture house in Espoon keskus. Stdlib only.

Reads the POST to `https://www.espoo.fi/api/events` that the venue's own event listing
sends, filtered to the place `tprId` 21430 and the topic "Elokuvat", paged until `total`
is covered. Two kinds of hit are dropped and counted: a span over 24 hours, which is a
festival row with no screening time, and a second hit at a start minute already taken,
since the one hall cannot hold two screenings at once (the smallest id is kept).
The age rating is read from the mark that closes the title, the only place it is stated.
The published title leaves out that mark and a leading "Elokuva:". Each film's own event
page is read once for the sentence that names its spoken and subtitle languages.
"""
import datetime
import html
import json
import re
import sys
import time
from zoneinfo import ZoneInfo

from common import UA, capped, check_shows, fetch, get_text
from etiketti import strict_codes

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "kannusali", "label": "Kannusali",
     "base": "https://www.espoo.fi",
     "path": "/api/events",
     "tpr": "21430", "topic": "Elokuvat",
     "venues": [{"id": "kannusali-espoo", "name": "Kannusali", "short": "Kannusali",
                 "city": "Espoo"}]},
]

# The listing page's own page size.
PER_PAGE = 12
# 20 pages is 240 hits; the live film topic held 11 on 2026-10-13.
MAX_PAGES = 20
PAUSE = 1.0
SPAN_MAX = datetime.timedelta(hours=24)
# `Elokuva: Flow. (K7)`. Only the KAVI classes, and only as the last thing in the title.
RATING_RE = re.compile(r"\((S|K-?(7|12|16|18))\)$")
FILM_PREFIX = "elokuva:"
# The one sentence a film's description gives its languages in, read on all ten film pages
# on 2026-10-15: "Elokuva on ruotsinkielinen ja siinä on tekstitys suomeksi.", "... ja siinä
# on ruotsinkielinen tekstitys." and "... ja siinä on tekstitys kielillä suomi ja ruotsi."
# The listing's `eventInLanguages` puts both kinds in one list. Any other wording gives "".
LANG_RE = re.compile(r"^Elokuva on (\w+kielinen)(?: ja siinä on (?:tekstitys (\w+ksi)"
                     r"|(\w+kielinen) tekstitys|tekstitys kielillä (\w+(?: ja \w+)*)))?\.$")
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                          re.S)
PARA_RE = re.compile(r"<p>(.*?)</p>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


class EventRowError(RuntimeError):
    """A hit this parser could not read. It fails the site so the previous files stand."""


def body(site, offset):
    """The listing page's request body, as captured from its own fetch."""
    return {"filters": {"age": "", "areas": [], "attributes": [], "categories": [],
                        "endDate": None, "languages": [], "startDate": None,
                        "targetGroups": [], "topics": [site["topic"]], "extras": [],
                        "fixedFilters": {"areas": [], "keyword": None, "targetGroups": [],
                                         "topics": [], "tprId": site["tpr"]}},
            "langcode": "fi",
            "pagination": {"offset": offset, "perPage": PER_PAGE},
            "showLongLastingEvents": True,
            "type": "event"}


def post(site, offset):
    url = site["base"] + site["path"]
    data = json.dumps(body(site, offset)).encode("utf-8")
    return json.loads(get_text(url, fetcher=fetch, data=data, cache=False,
                               headers={"content-type": "application/json",
                                        "accept": "application/json",
                                        "user-agent": UA}))


def total_of(answer):
    total = answer.get("total") if isinstance(answer, dict) else None
    if isinstance(total, dict):
        total = total.get("value")
    if not isinstance(total, int) or isinstance(total, bool):
        raise RuntimeError(f"the events service answered no integer total ({str(answer)[:120]})")
    return total


def read_all(site):
    """Every hit's `_source`, page by page. -> [dict]."""
    out, offset, total = [], 0, None
    for n in range(MAX_PAGES):
        if n:
            time.sleep(PAUSE)
        answer = post(site, offset)
        total = total_of(answer)
        hits = answer.get("hits")
        if not isinstance(hits, list):
            raise RuntimeError(f"the events service answered no hits list at offset {offset}")
        if offset < total and not hits:
            raise RuntimeError(f"the events service answered no hits at offset {offset} "
                               f"of a total of {total}")
        out += [h.get("_source") or {} for h in hits]
        offset += len(hits)
        if offset >= total:
            return out, total
    raise RuntimeError(f"the events service has {total} hits, more than {MAX_PAGES} pages "
                       f"of {PER_PAGE}")


def instant(value, field, hit_id):
    """`2026-11-04T12:00:00Z` -> an aware Helsinki datetime."""
    try:
        t = datetime.datetime.fromisoformat(str(value))
    except ValueError:
        t = None
    if t is None or t.tzinfo is None:
        raise EventRowError(f"hit {hit_id!r}: {field} {value!r} is not an instant with an offset")
    return t.astimezone(FI)


def slug_of(title):
    return re.sub(r"-{2,}", "-", re.sub(r"[^\w]+", "-", (title or "").lower(),
                                        flags=re.UNICODE)).strip("-")


def rating_of(title):
    """`Elokuva: Flow. (K7)` -> "K-7", `(S)` -> "S", and "" when no mark closes the title."""
    m = RATING_RE.search(title)
    if not m:
        return ""
    return f"K-{m.group(2)}" if m.group(2) else "S"


def shown_title(title):
    """`Elokuva: Flow. (K7)` -> "Flow.". A title that would be left empty stays as it is."""
    t = RATING_RE.sub("", title).rstrip()
    if t.lower().startswith(FILM_PREFIX):
        t = t[len(FILM_PREFIX):].strip()
    return t or title


def description(page):
    """An event page -> its description as plain-text paragraphs, [] when it has none."""
    m = NEXT_DATA_RE.search(page)
    if not m:
        return []
    state = (json.loads(m.group(1)).get("props") or {}).get("graphQLState") or {}
    for entry in state.values():
        data = entry.get("data") if isinstance(entry, dict) else None
        event = data.get("Event") if isinstance(data, dict) else None
        if isinstance(event, dict):
            return [html.unescape(TAG_RE.sub("", p)).replace("\xa0", " ").strip()
                    for p in PARA_RE.findall(event.get("description") or "")]
    return []


def lang_of(paras):
    """Description paragraphs -> "SV-A, FI-S", or "" unless one paragraph is the sentence."""
    for p in paras:
        m = LANG_RE.match(p)
        if not m:
            continue
        audio = strict_codes(m.group(1))
        named = m.group(2) or m.group(3) or m.group(4)
        subs = strict_codes(named) if named else []
        if len(audio) != 1 or (named and not subs):
            return ""
        return ", ".join([f"{audio[0]}-A"] + [f"{c}-S" for c in subs])
    return ""


def languages(site, shows):
    """One event page per film, its language sentence put on every screening of it."""
    pid, by_film = site["provider"], {}
    for s in shows:
        by_film.setdefault(s["title"], []).append(s)
    read = 0
    for n, (title, films) in enumerate(capped(by_film.items(), pid)):
        if n:
            time.sleep(PAUSE)
        try:
            lang = lang_of(description(get_text(films[0]["url"], fetcher=fetch, tries=2,
                                                backoff=3, timeout=20)))
        except Exception as e:
            print(f"[{pid}] event page for {title}: {type(e).__name__}: {e}")
            continue
        read += bool(lang)
        for s in films:
            s["lang"] = lang
    print(f"[{pid}] languages read for {read} of {len(by_film)} film(s)")


def rows(site, hits):
    """-> (shows, report). One row per screening minute."""
    venue = site["venues"][0]
    report = {"hits": len(hits), "long": [], "collapsed": []}
    kept = {}
    for hit in hits:
        hid = str(hit.get("id") or "")
        title = (hit.get("title") or "").strip()
        path = hit.get("path") or ""
        if not title:
            raise EventRowError(f"hit {hid!r} has no title")
        # The topic filter runs on the server, so a hit without it means the filter changed.
        if site["topic"] not in (hit.get("topics") or []):
            raise EventRowError(f"hit {hid!r} ({title}) is not under the topic {site['topic']!r}")
        if not isinstance(path, str) or not path.startswith("/"):
            raise EventRowError(f"hit {hid!r} ({title}) has no path: {path!r}")
        if not hit.get("eventStartTime"):
            raise EventRowError(f"hit {hid!r} ({title}) has no eventStartTime")
        start = instant(hit["eventStartTime"], "eventStartTime", hid)
        if hit.get("eventEndTime"):
            end = instant(hit["eventEndTime"], "eventEndTime", hid)
            if end - start > SPAN_MAX:
                report["long"].append(f"{hid} ({title})")
                continue
        minute = start.replace(second=0, microsecond=0)
        row = (hid, title, path, minute, hit.get("isFreeEvent") is True)
        other = kept.get(minute)
        if other is None:
            kept[minute] = row
            continue
        keep, drop = (row, other) if hid < other[0] else (other, row)
        kept[minute] = keep
        report["collapsed"].append(f"{drop[0]} ({drop[1]}), same start as {keep[0]}")
    out = []
    for hid, title, path, minute, free in kept.values():
        out.append({
            "eventId": slug_of(shown_title(title)),
            "title": shown_title(title),
            "original": "",
            "len": "",
            "rating": rating_of(title),
            "genres": "",
            "method": "",
            "theatre": venue["name"],
            "aud": "",
            "start": minute.isoformat(),
            "url": site["base"] + path,
            "img": "",
            "lang": "",
            "soldOut": False,
            "price": "Vapaa pääsy" if free else "",
            "provider": site["provider"],
            "venue": venue["id"],
        })
    out.sort(key=lambda s: (s["start"], s["title"]))
    return out, report


def fetch_site(site):
    """Runner contract: the listing's own POST, one request per page."""
    pid, venue = site["provider"], site["venues"][0]
    hits, total = read_all(site)
    # Zero hits cannot be told from a broken server-side filter, so it is never empty.
    if not hits:
        raise RuntimeError(f"{site['base']}{site['path']}: no hit for place {site['tpr']} "
                           f"and topic {site['topic']!r}")
    shows, report = rows(site, hits)
    if not shows:
        raise RuntimeError(f"{site['base']}{site['path']}: {total} hit(s) and no screening "
                           f"among them")
    languages(site, shows)
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, from {len(hits)} hit(s) of a total of {total}")
    if report["long"]:
        print(f"[{pid}] {len(report['long'])} hit(s) spanning over 24 h left out: "
              f"{', '.join(report['long'])}")
    for note in report["collapsed"]:
        print(f"[{pid}] collapsed {note}")
    return per_venue


if __name__ == "__main__":
    for s in fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]:
        print(f"   {s['start'][:16]}  {s['title'][:44]:46} {s['price']:12} {s['url']}")
    sys.exit(0)
