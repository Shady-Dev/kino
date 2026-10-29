"""Bio Savoy, Mariehamn, Åland. Stdlib only.

Rebuilt 2026-10-29 for the cinema's new site, which went live on 2026-10-28 with a Let's
Encrypt certificate issued that morning. The old Drupal site was http only. The new one
answers on https and redirects http to it, so every URL here is https.

The site is a server-rendered Laravel app with no API: its one script only opens menus and
tabs, its Content-Security-Policy allows connections to its own origin only, and `/api`
answers 404. Two kinds of page are read.

`/spelschema` lists the week, "framställs veckovis, fredag till torsdag, och uppdateras på
tisdagar":

    <h2 class="schedule__day-heading ...">Torsdag <span>29/10</span></h2>
    <a class="show-row show-row--link ..." href="/film/whalefall">
      <span class="show-row__time ...">18.00</span>
      <span class="show-row__title">WHALEFALL</span>
      ... <span class="chip">Sal 1</span>

The day carries no year, so `common.resolve_year` places it with the Swedish weekday. A
heading or a row this parser cannot read fails the site.

`/film/{slug}` is fetched once per distinct film. Its facts list gives "Speltid",
"Åldersgräns" and "Pris", and its own schedule repeats each screening with an ISO date and
the screening's price:

    <div class="schedule__panel" id="film-day-2026-10-29" data-tab-panel>
      <span class="show-row__time">20.30</span>
      <span class="show-row__title block">Sal 2</span>
      <span class="show-row__meta mt-1 block">15 €</span>

The price is taken from that row, matched on date, time and hall, and only when the row
states a single amount. A screening the film page does not list keeps an empty price.
Read 2026-10-29 across all ten films: 39 rows, 15 € on 28 and 13 € on the 11 children's
screenings.

The synopsis is Swedish and is published as `{"sv": ...}`. Åland's only official language
is Swedish, and in the Finnish slot it would be served as Finnish to every chain showing
the film. A paragraph reading "SVENSKT TAL!" is the screening's language and leaves the
synopsis, as does a local "PREMIÄR" date.

The film pages carry the cinema's own pictures. No poster is published from them, because
nothing grants that; the TMDB pass fills what it can.

`book="door"`: "Bokningar tas emot per telefon 0457 3459 788 ... Vi tar enbart emot
bokningar fram till dagen före aktuell föreställning." A showtime opens the film's page.

The city is keyed `Mariehamn`, the town's only official name. `CITY_SV` in `index.html`
translates Finnish keys for the Swedish interface, and a Finnish exonym here would be shown
untranslated in Swedish.
"""
import datetime
import html as html_mod
import re
import sys
import time
from zoneinfo import ZoneInfo

from common import capped, fetch, resolve_year, served

BASE = "https://www.biosavoy.ax"
LISTING = "/spelschema"
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"
TZ = ZoneInfo("Europe/Mariehamn")

VENUE = {"id": "savoy-mariehamn", "name": "Bio Savoy", "short": "Bio Savoy",
         "city": "Mariehamn"}

SITES = [{"provider": "biosavoy", "label": "Bio Savoy", "base": BASE, "venues": [VENUE]}]

# The page published Thursday to the next Thursday on 2026-10-29. A week is the horizon.
WINDOW = (30, 60)

SV_WEEKDAYS = {"m\u00e5ndag": 0, "tisdag": 1, "onsdag": 2, "torsdag": 3, "fredag": 4,
               "l\u00f6rdag": 5, "s\u00f6ndag": 6}

SECTION_RE = re.compile(r'data-section="schedule"')
DAY_RE = re.compile(r'<h2 class="schedule__day-heading[^"]*">(.*?)</h2>(.*?)'
                    r'(?=<h2 class="schedule__day-heading|</section>|\Z)', re.S)
DAY_TEXT_RE = re.compile(r"^(\S+)\s+(\d{1,2})/(\d{1,2})$")
ROW_RE = re.compile(r'<a class="show-row[^"]*"\s+href="(/film/[^"/]+)"\s*>(.*?)</a>', re.S)
TIME_RE = re.compile(r'class="show-row__time[^"]*">\s*(\d{1,2})[.:](\d{2})\s*<')
TITLE_RE = re.compile(r'class="show-row__title[^"]*">(.*?)</span>', re.S)
CHIP_RE = re.compile(r'class="chip">(.*?)</span>', re.S)

FACTS_RE = re.compile(r'<section class="film-facts"(.*?)</section>', re.S)
FACT_RE = re.compile(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", re.S)
PANEL_RE = re.compile(r'id="film-day-(\d{4}-\d{2}-\d{2})"[^>]*data-tab-panel[^>]*>(.*?)</ul>',
                      re.S)
PANEL_ROW_RE = re.compile(r'<li class="show-row[^"]*">(.*?)</li>', re.S)
META_RE = re.compile(r'class="show-row__meta[^"]*">(.*?)</span>', re.S)
LEAD_RE = re.compile(r'<p class="film-about__lead">(.*?)</p>', re.S)
BODY_RE = re.compile(r'<div class="film-about__body[^"]*">(.*?)</div>', re.S)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)
TAGS_RE = re.compile(r"<[^>]+>")

# The whole value must be one amount. "15 €" is read; "15 € / 13 €" and "Slutsåld" are not.
AMOUNT_RE = re.compile(r"^(\d{1,3}(?:[.,]\d{1,2})?)\s*\u20ac$")
# "1 h 48 min". The hours must be digits: the old site once published "XXh 00min".
LENGTH_RE = re.compile(r"^(\d{1,2})\s*h\s*(\d{1,2})\s*min$", re.I)
AGE_RE = re.compile(r"^(?:till\u00e5ten\s+)?fr\u00e5n\s+(\d{1,2})\s*\u00e5r$", re.I)
ALL_AGES_RE = re.compile(r"^till\u00e5ten\s+f\u00f6r\s+alla$", re.I)
SWEDISH_RE = re.compile(r"^svenskt\s+tal\s*!?$", re.I)
SCREENING_PARA_RE = re.compile(r"^(?:svenskt\s+tal\s*!?"
                               r"|premi\u00e4r\s*:?\s*\d{1,2}\.\d{1,2}\.?\s*\d{4})$", re.I)


class ShowRowError(RuntimeError):
    """A heading or row on the schedule that cannot be placed. Fails the site."""


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))
                  .replace("\xa0", " ")).strip()


def _clock(h, m):
    return f"{int(h):02d}:{int(m):02d}"


def parse(page, today=None):
    """The schedule page -> [show]. Raises when the schedule section is missing, when a day
    or row cannot be read, and when no row is found: no empty state has been read off this
    site, so zero rows is a failure and never `common.EmptyProgramme`."""
    today = today or datetime.datetime.now(TZ).date()
    if not SECTION_RE.search(page):
        raise RuntimeError(
            f"{BASE}{LISTING}: no schedule section on the page, so this is not the "
            f"programme this parser reads. Treating it as a fetch or template failure "
            f"rather than a cinema with nothing on")
    shows, seen = [], set()
    for heading, body in DAY_RE.findall(page):
        text = _txt(heading)
        m = DAY_TEXT_RE.match(text)
        weekday = SV_WEEKDAYS.get(m.group(1).lower()) if m else None
        if weekday is None:
            raise ShowRowError(f"biosavoy: the day heading {text!r} is not a Swedish "
                               f"weekday with a day and month")
        day, month = int(m.group(2)), int(m.group(3))
        year = resolve_year(day, month, today, weekday, WINDOW)
        if year is None:
            raise ShowRowError(f"biosavoy: {text!r} falls on that weekday in no year inside "
                               f"the window, so its screenings cannot be placed")
        for href, row in ROW_RE.findall(body):
            clock, title = TIME_RE.search(row), TITLE_RE.search(row)
            name = _txt(title.group(1)) if title else ""
            if not clock or not name:
                raise ShowRowError(f"biosavoy: a row under {text!r} linking {href} has no "
                                   f"readable time or title")
            hall = CHIP_RE.search(row)
            aud = _txt(hall.group(1)) if hall else ""
            start = datetime.datetime(year, month, day, int(clock.group(1)),
                                      int(clock.group(2)), tzinfo=TZ)
            slug = href.rsplit("/", 1)[-1]
            key = (slug, start.isoformat(), aud)
            if key in seen:
                continue
            seen.add(key)
            shows.append({
                "eventId": slug,
                "title": name,
                "original": "",
                "len": "",
                "rating": "",
                "genres": "",
                "method": "",
                "theatre": VENUE["name"],
                "aud": aud,
                "start": start.isoformat(),
                "url": f"{BASE}{href}",
                "img": "",
                "lang": "",
                "soldOut": False,
                "price": "",
                "provider": "biosavoy",
                "venue": VENUE["id"],
            })
    if not shows:
        raise RuntimeError(
            f"{BASE}{LISTING}: schedule section present but no screening row found "
            f"({served(page)}). No empty state is known for this site, so this is a parse "
            f"or template failure")
    shows.sort(key=lambda s: (s["start"], s["aud"]))
    return shows


def _amount(text):
    m = AMOUNT_RE.match(text)
    if not m:
        return ""
    return f"{float(m.group(1).replace(',', '.')):.2f}".rstrip("0").rstrip(".") + "\u20ac"


def screening_prices(page):
    """{(date, "HH:MM", hall): price} from the film page's own schedule. -> dict.

    A key whose rows state two different prices maps to "": the page has stopped saying
    one thing about that screening.
    """
    out = {}
    for date, body in PANEL_RE.findall(page):
        for row in PANEL_ROW_RE.findall(body):
            clock, hall, meta = TIME_RE.search(row), TITLE_RE.search(row), META_RE.search(row)
            if not clock:
                continue
            key = (date, _clock(clock.group(1), clock.group(2)),
                   _txt(hall.group(1)) if hall else "")
            price = _amount(_txt(meta.group(1))) if meta else ""
            out[key] = price if out.get(key, price) == price else ""
    return out


def _paragraphs(page):
    lead = LEAD_RE.search(page)
    body = BODY_RE.search(page)
    paras = [lead.group(1)] if lead else []
    if body:
        paras += P_RE.findall(body.group(1)) or [body.group(1)]
    return [t for t in (_txt(p) for p in paras) if t]


def film_facts(page):
    """-> {"prices", "len", "rating", "syn", "lang"} for one film page, each empty where
    the page does not say it plainly."""
    facts = {}
    block = FACTS_RE.search(page)
    if block:
        facts = {_txt(k): _txt(v) for k, v in FACT_RE.findall(block.group(1))}
    length = LENGTH_RE.match(facts.get("Speltid", ""))
    age_text = facts.get("\u00c5ldersgr\u00e4ns", "")
    age = AGE_RE.match(age_text)
    rating = (f"K-{int(age.group(1))}" if age
              else "S" if ALL_AGES_RE.match(age_text) else "")
    paras = _paragraphs(page)
    return {"prices": screening_prices(page),
            "len": str(int(length.group(1)) * 60 + int(length.group(2))) if length else "",
            "rating": rating,
            "syn": " ".join(p for p in paras if not SCREENING_PARA_RE.match(p)),
            "lang": "SV-A" if any(SWEDISH_RE.match(p) for p in paras) else ""}


def get(url):
    return fetch(url, cache=True,
                 headers={"user-agent": UA, "accept-language": "sv-AX,sv;q=0.9"},
                 timeout=30).decode("utf-8", "replace")


def film_facts_by_slug(slugs, sleep=1.5, get=None):
    """{slug: facts} for every film page that answered. -> dict.

    One request per distinct film, paced, cached and bounded by the shared page budget.
    `capped`, not `budget_or_raise`: these pages carry no showtime the schedule lacks, so a
    film past the cap or one whose page fails loses its facts and keeps its screenings.
    """
    get = get or globals()["get"]
    out = {}
    for n, slug in enumerate(capped(slugs, "biosavoy")):
        if n:
            time.sleep(sleep)
        try:
            out[slug] = film_facts(get(f"{BASE}/film/{slug}"))
        except Exception as e:
            print(f"[biosavoy] film page {slug}: {type(e).__name__}: {e}", file=sys.stderr)
    return out


BLANK = {"prices": {}, "len": "", "rating": "", "syn": "", "lang": ""}


def fetch_site(site=SITES[0], sleep=1.5, today=None):
    """Runner contract: the schedule, then one film page per distinct film."""
    shows = parse(get(BASE + LISTING), today)
    facts = film_facts_by_slug(sorted({s["eventId"] for s in shows}), sleep=sleep)
    for s in shows:
        f = facts.get(s["eventId"]) or BLANK
        s["price"] = f["prices"].get((s["start"][:10], s["start"][11:16], s["aud"]), "")
        s["len"], s["rating"], s["lang"] = f["len"], f["rating"], f["lang"]
        if f["syn"]:
            s["_syn"] = {"sv": f["syn"]}
    print(f"[biosavoy] {len(shows)} showtimes, {len({s['eventId'] for s in shows})} films, "
          f"{len({s['start'][:10] for s in shows})} dates, "
          f"halls {sorted({s['aud'] for s in shows})}, "
          f"{sum(1 for s in shows if s['price'])} priced, "
          f"{sum(1 for s in shows if s['len'])} timed, "
          f"{sum(1 for s in shows if s['rating'])} rated, "
          f"{sum(1 for s in shows if s.get('_syn'))} with a Swedish synopsis")
    return {VENUE["id"]: shows}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = (parse(open(src, encoding="utf-8", errors="replace").read()) if src
            else fetch_site()[VENUE["id"]])
    for s in data:
        print(f"  {s['start'][:16]} {s['aud']:7} {s['title'][:34]:36} {s['url']}")
