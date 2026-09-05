"""Heureka Planetaario (Vantaa) -- the science centre's daily programme. Stdlib only.

Heureka runs a Shopify storefront, and its "Päivän ohjelma" page renders three arrays
straight into the HTML from Shopify metaobjects: `window.eventCalendarData` (every
programme item with a category, a duration, a date range and a list of times per
weekday), `window.eventExceptionsData` (a replacement weekday schedule for one item over
one date range) and `window.disabledHolidays` (days the whole house is closed). The
page's own script expands those three into the day a visitor picks. This adapter reads
the same three arrays and expands them the same way for the days ahead, which is the
nearest thing the site has to a structured feed: there is no JSON endpoint for the
calendar, and the rendered list is built client-side from exactly this data.

Only `kategoria == "Planetaarioelokuvat"` is a screening. The same calendar carries the
rat feeding, the laboratory sessions, the science shows on the sphere and all-day
exhibition events, none of which belong in a cinema listing.

Screenings are included in Heureka's day admission and there is no planetarium ticket
to buy, so every showtime links to the ticket collection, `price` stays empty and the
registry marks the provider `book="admission"`: the footer verb and the page intro say
the ticket is the admission ticket, and the price compartment stays blank the way it
does for every cinema that publishes no price. Admission has several categories and
changing promotions (measured 2026-09-05: five products in the collection, from 0 to
26 euro), so one figure on a showtime would be wrong for most readers.

The planetarium admits from five years of age, whatever the film. That is a limit of
the room and the per-show `age` field holds that kind of limit; `rating` stays blank
because no KAVI classification is published. Heureka's own per-film "Ikäsuositus" (7+,
10+, 5–10) is a recommendation, so it travels as a `method` tag -- "Suositus 10+" --
which the client renders as the small uppercase pill it uses for every other passive
tag. The rating chip is for classifications and stays out of this.

Per film, the blog article behind the calendar item gives the runtime (also in the
calendar), the recommendation, the audio languages (the film is dubbed; other languages
are heard through headphones) and the synopsis. The synopsis is the description block
alone: the article's FAQ repeats the admission and reservation rules and quotes a
school-group price, which `synmerge` would refuse anyway and which are not a synopsis.
Posters are not taken: Heureka publishes 16:9 stills, and a still cropped into a 2:3
tile is the Orion case IDEAS already declines. The TMDB pass fills what it can.

Conditional requests are not used: the calendar page answers `If-None-Match` with a
full 200 and a fresh ETag every time (checked 2026-09-05), so storing a 1.6 MB body per
URL would buy nothing.
"""
import datetime
import html as html_mod
import json
import re
import sys
import time
import unicodedata
from zoneinfo import ZoneInfo

import common
from etiketti import LANG_NAMES

BASE = "https://www.heureka.fi"
CALENDAR = "/pages/tapahtumakalenteri"
TICKETS = "https://www.heureka.fi/collections/liput"
CATEGORY = "Planetaarioelokuvat"
DAYS = 21                    # like the Nexxo window: the schedule is a weekly rule
AGE = "K-5"                  # the planetarium's own floor; not a KAVI classification
FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"
HEADERS = {"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"}

VENUE = {"id": "hk-vantaa", "provider": "heureka", "name": "Heureka Planetaario",
         "short": "Planetaario", "city": "Vantaa"}

SITES = [{"provider": "heureka", "label": "Heureka", "base": BASE, "venues": [VENUE]}]

WEEKDAYS = ["maanantai", "tiistai", "keskiviikko", "torstai", "perjantai",
            "lauantai", "sunnuntai"]                        # date.weekday(): 0 = Monday
TIME_RE = re.compile(r"^(\d{1,2})[.:](\d{2})$")
TAGS_RE = re.compile(r"<[^>]+>")
DT_RE = re.compile(r'<dt class="detail-list__term">\s*(.*?)\s*</dt>\s*'
                   r'<dd class="detail-list__desc">\s*(.*?)\s*</dd>', re.S)
DESC_RE = re.compile(r'<div class="image-with-text__text rte body">(.*?)</div>', re.S)
LANGS_RE = re.compile(r"Kielivaihtoehdot:\s*(?:</strong>)?\s*(.*?)</p>", re.S)
MINUTES_RE = re.compile(r"(\d+)\s*min")
REC_OVER_RE = re.compile(r"yli\s+(\d+)-vuot", re.I)
REC_RANGE_RE = re.compile(r"(\d+)\s*[–-]\s*(\d+)-vuot", re.I)
REC_ADULTS_RE = re.compile(r"aikuisille", re.I)


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))).strip()


def _slug(title):
    s = unicodedata.normalize("NFKD", _txt(title).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")[:60] or "naytos"


# ---------------------------------------------------------------- the three arrays

def _js_to_json(text):
    """A JavaScript array literal as the page writes it -> JSON text.

    Three things have to change: bare keys (`nimi:`), trailing commas, and the doubled
    commas an empty metaobject reference leaves behind (`["2026-03-13",\\n,\\n"2026-12-24",
    \\n]`, which the page itself cleans with `filter(Boolean)`). Strings are copied as
    written, since `\\/` and `\\u0026` are JSON already and a title can contain a colon or
    a comma.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            body = text[i + 1:j]
            if c == "'":
                body = body.replace("\\'", "'").replace('"', '\\"')
            out.append('"' + body + '"')
            i = j + 1
            continue
        j = i
        while j < n and text[j] not in "\"'":
            j += 1
        seg = text[i:j]
        seg = re.sub(r"([A-Za-z_]\w*)\s*:", r'"\1":', seg)
        seg = re.sub(r",(\s*,)+", ",", seg)
        seg = re.sub(r"([\[{])\s*,", r"\1", seg)
        seg = re.sub(r",(\s*[\]}])", r"\1", seg)
        out.append(seg)
        i = j
    return "".join(out)


def js_array(page, name):
    """The array assigned to `window.{name}` on the page -> list, or None if absent."""
    m = re.search(r"window\." + re.escape(name) + r"\s*=\s*\[", page)
    if not m:
        return None
    start = m.end() - 1
    depth, k, quote = 0, start, None
    while k < len(page):
        c = page[k]
        if quote:
            if c == "\\":
                k += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return json.loads(_js_to_json(page[start:k + 1]))
        k += 1
    raise RuntimeError(f"window.{name} never closes")


def calendar_arrays(page):
    """-> (events, exceptions, holidays). Raises when the page is not the calendar."""
    events = js_array(page, "eventCalendarData")
    if events is None:
        raise RuntimeError(f"{BASE}{CALENDAR}: no window.eventCalendarData on the page "
                           f"(markup changed?)")
    if not events:
        # The calendar carries every kind of programme item. An array with none at all
        # means the section failed to render, so this is a parser break and the previous
        # data is kept.
        raise RuntimeError(f"{BASE}{CALENDAR}: eventCalendarData is empty")
    exceptions = js_array(page, "eventExceptionsData") or []
    holidays = [h for h in (js_array(page, "disabledHolidays") or []) if h]
    return events, exceptions, holidays


# ---------------------------------------------------------------- the expansion

def _in_range(day, start, end):
    return not (start and day < start) and not (end and day > end)


def times_on(ev, exceptions, day):
    """The clock strings an event runs on `day`, the way the page's renderDay decides.

    An exception whose range covers the day replaces the event's whole weekday schedule
    -- newest `alkaa` wins when several apply, as on the page -- and while one applies
    the event's own date range is not consulted. Without one, the event runs only inside
    its own range. Times come back as written ("12.30"); blanks are dropped.
    """
    iso = day.isoformat()
    active = [ex for ex in exceptions
              if ev.get("nimi") in (ex.get("appliesToEvents") or [])
              and _in_range(iso, ex.get("alkaa") or "", ex.get("paattyy") or "")]
    if active:
        active.sort(key=lambda ex: ex.get("alkaa") or "", reverse=True)
        sched = active[0].get("ajat") or {}
    else:
        if not _in_range(iso, ev.get("alkamispaiva") or "", ev.get("paattymispaiva") or ""):
            return []
        sched = ev.get("ajat") or {}
    raw = sched.get(WEEKDAYS[day.weekday()]) or []
    return [re.sub(r'[\[\]"]', "", str(t)).strip() for t in raw if t and str(t).strip()]


def _iso(day, clock):
    m = TIME_RE.match(clock)
    if not m:
        return ""
    hh, mm = int(m.group(1)), int(m.group(2))
    if hh > 23 or mm > 59:
        return ""
    return datetime.datetime(day.year, day.month, day.day, hh, mm, tzinfo=FI).isoformat()


def _event_id(ev):
    blog = (ev.get("tapahtumasivu_blog_post") or "").rstrip("/")
    return blog.split("/")[-1] if blog.startswith("/blogs/") else _slug(ev.get("nimi"))


def parse_calendar(page, today=None, days=DAYS):
    """-> (shows, {blog path: eventId}) for the planetarium films in the window.

    Raises `common.EmptyProgramme` when the calendar parsed and no planetarium film has
    a time in the window, and RuntimeError when planetarium times were listed and not
    one of them could be read -- that is the clock format changing under the parser,
    and returning [] would publish a quiet week over it.
    """
    events, exceptions, holidays = calendar_arrays(page)
    today = today or datetime.datetime.now(FI).date()
    films = [ev for ev in events if ev.get("kategoria") == CATEGORY
             and ev.get("koko_paiva") != "Kyllä"]
    shows, blogs, tokens = [], {}, 0
    for n in range(days):
        day = today + datetime.timedelta(days=n)
        if day.isoformat() in holidays:
            continue
        for ev in films:
            for clock in times_on(ev, exceptions, day):
                tokens += 1
                start = _iso(day, clock)
                if not start:
                    continue
                title = _txt(ev.get("nimi"))
                eid = _event_id(ev)
                blog = (ev.get("tapahtumasivu_blog_post") or "").strip()
                if blog.startswith("/blogs/"):
                    blogs[blog] = eid
                kesto = ev.get("kesto")
                shows.append({
                    "eventId": eid,
                    "title": title,
                    "original": "",
                    "len": str(kesto) if isinstance(kesto, int) and kesto > 0 else "",
                    "rating": "",
                    "genres": "",
                    "method": "",
                    "theatre": VENUE["name"],
                    "aud": "",                       # one dome; the venue is the room
                    "start": start,
                    "url": TICKETS,
                    "img": "",
                    "lang": "",
                    "soldOut": False,
                    "price": "",
                    "age": AGE,
                    "provider": VENUE["provider"],
                    "venue": VENUE["id"],
                    "_syn": "",
                })
    if tokens and not shows:
        raise RuntimeError(f"{BASE}{CALENDAR}: {tokens} planetarium time(s) listed in the "
                           f"next {days} days and none could be read (clock format changed?)")
    if not shows:
        raise common.EmptyProgramme(
            f"{BASE}{CALENDAR}: {len(events)} programme items, no planetarium film "
            f"scheduled in the next {days} days")
    shows.sort(key=lambda s: (s["start"], s["title"]))
    return shows, blogs


# ---------------------------------------------------------------- the film page

def recommendation(text):
    """Heureka's Ikäsuositus wording -> a labelled tag, or "" when it names no age.

    "Sopii parhaiten yli 10-vuotiaille" -> "Suositus 10+"; "5–10-vuotiaille" ->
    "Suositus 5–10 v"; "...aikuisille" -> "Suositus aikuisille". Any other wording
    produces no tag. The word "Suositus" is part of every tag so that it cannot be read
    as an age limit.
    """
    t = _txt(text)
    m = REC_RANGE_RE.search(t)
    if m:
        return f"Suositus {m.group(1)}–{m.group(2)} v"
    m = REC_OVER_RE.search(t)
    if m:
        return f"Suositus {m.group(1)}+"
    if REC_ADULTS_RE.search(t):
        return "Suositus aikuisille"
    return ""


def languages(page):
    """The 'Kielivaihtoehdot' line -> "FI-A, EN-A, SV-A"; "" when the page lists none.

    A film without speech (Recombination) has no such line, so it publishes no language
    the same way a page that was never read does."""
    m = LANGS_RE.search(page)
    if not m:
        return ""
    codes = []
    for word in re.findall(r"[a-zåäö]+", _txt(m.group(1)).lower()):
        code = LANG_NAMES.get(word)
        if code and code not in codes:
            codes.append(code)
    return ", ".join(f"{c}-A" for c in codes)


def film_meta(page):
    """One blog article -> {len, method, lang, _syn}. Missing parts stay empty."""
    details = {_txt(k): _txt(v) for k, v in DT_RE.findall(page)}
    minutes = MINUTES_RE.search(details.get("Kesto", ""))
    desc = DESC_RE.search(page)
    paras = [_txt(p) for p in re.split(r"</p>", desc.group(1))] if desc else []
    return {
        "len": minutes.group(1) if minutes else "",
        "method": recommendation(details.get("Ikäsuositus", "")),
        "lang": languages(page),
        "_syn": " ".join(p for p in paras if p),
    }


# ---------------------------------------------------------------- the fetch

def get(path):
    return common.fetch(f"{BASE}{path}", headers=HEADERS, timeout=40,
                        cache=False).decode("utf-8", "replace")


def fetch_site(site=SITES[0], sleep=1.2, today=None):
    """Runner contract: the calendar, then one article per film, keyed by the venue."""
    shows, blogs = parse_calendar(get(CALENDAR), today)
    for i, path in enumerate(common.capped(sorted(blogs), "heureka film pages")):
        if i:
            time.sleep(sleep)
        try:
            meta = film_meta(get(path))
        except Exception as e:                       # metadata only; the schedule stands
            print(f"[heureka] film page {path} failed: {e}", file=sys.stderr)
            continue
        for s in shows:
            if s["eventId"] != blogs[path]:
                continue
            for k, v in meta.items():
                if v and not s.get(k):
                    s[k] = v
    return {VENUE["id"]: shows}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    if src:
        data, blogs = parse_calendar(open(src, encoding="utf-8", errors="replace").read())
    else:
        data = fetch_site()[VENUE["id"]]
    print(f"{len(data)} showtimes, {len({s['eventId'] for s in data})} films, "
          f"{len({s['start'][:10] for s in data})} dates")
    for s in data[:40]:
        print(f"  {s['start'][:16]}  {s['title'][:40]:42} {s['len']:>3} min  {s['method']:22} "
              f"{s['lang']}")
