"""Kino Kirkkonummi, Munkinmäentie 17. Stdlib only.

Probed 2026-09-15. A WordPress site built in Elementor, and the whole cinema is one page.
It was deferred on 2026-09-15 as too fragile to parse, on the grounds that the showtimes
are hand-authored inside page-builder markup with no year and no booking host. That was a
maintenance judgement rather than a demonstration, and it does not survive contact with
the page: the screenings are server-rendered in a consistent shape and three of them a
week is not a hard parse. It is implemented here.

The markup carries no semantic class for a screening. What it does carry is a film title
in a heading and its screenings in a following icon list:

    <p class="elementor-heading-title ...">Myrskyn Ikkuna</p>
    ...<span class="elementor-icon-list-text">20.9. Sunnuntai klo18.00</span>
    ...<span class="elementor-icon-list-text">22.9. Tiistai klo19.00</span>

So the parser walks headings and list items **in document order**, keeping the last
heading as the current film. Four things about this page decide the rest:

- **Every block is published twice**, once for desktop and once for mobile: 21 headings
  and 46 list items for 6 films. Each screening therefore arrives twice and is deduplicated
  on (film, start). A parser that trusted the count would double every showtime.
- **A list item is a screening only if it reads `D.M. Weekday kloHH.MM`.** The same element
  carries cast lists, directors, notes like "vain tämä näytös", the street address and the
  phone number. None of them match, so no exclusion list is needed for those.
- **"Tulossa 25.9. alkaen" is a release date, not a screening.** It names a day and a month
  and no time at all, so the same rule drops it. The word `tulossa` also appears as a
  decorative heading above several films that *do* have screenings, so it is not usable as
  a marker either way; only the shape of the row decides.
- **No year, but every row carries a weekday**, and that determines the year rather than
  guessing it. See `common.resolve_year`. A weekday matching no candidate year leaves the
  row unplaced and counted.

The time is written `klo18.00`, with no space and a dot for minutes.

There is no per-film page and no booking host: the site is one page and tickets are
reserved by phone. So a showtime opens that page and the registry entry is `book="list"`,
which is what that mode is for. No auditorium is published either. The page mentions two
seat counts, 112 and 68, but never says which screening is in which, so none is invented.
"""
import datetime
import html as html_mod
import re
import sys
from zoneinfo import ZoneInfo

import synmerge
from common import EmptyProgramme, fetch, resolve_year, weekday_index

BASE = "https://kinokirkkonummi.fi"
LISTING = BASE + "/"
FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

VENUE = {"id": "kirkkonummi", "name": "Kino Kirkkonummi", "short": "Kino Kirkkonummi",
         "city": "Kirkkonummi"}

SITES = [{"provider": "kirkkonummi", "label": "Kino Kirkkonummi", "base": BASE,
          "venues": [VENUE]}]

CONTAINER_RE = re.compile(r'elementor-icon-list-text', re.I)
HEAD_RE = re.compile(r'<p class="elementor-heading-title[^"]*">(.*?)</p>', re.S | re.I)
ITEM_RE = re.compile(r'<span class="elementor-icon-list-text">(.*?)</span>', re.S | re.I)
SHOW_RE = re.compile(r'^(\d{1,2})\.(\d{1,2})\.\s*([A-Za-zÄÖäö]{2,12})\s*klo\s*'
                     r'(\d{1,2})[.:](\d{2})\s*$', re.I)

# Headings that are not films. `tulossa` labels a film that is coming and sits *above* its
# title, so it must not become one; the two seat counts belong to the auditoriums and sit
# in the footer.
NOT_A_TITLE = re.compile(r'^(?:tulossa|elokuvateatteri|\d+\s*paikkaa)$', re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))
                  .replace("\xa0", " ")).strip()


def parse(page, today=None):
    """The one page -> [show]. Raises when no icon list is present, and `EmptyProgramme`
    when the lists are there with no screening row in them."""
    if not CONTAINER_RE.search(page):
        raise RuntimeError(
            f"{LISTING}: no icon list on the page, so this is not the programme this "
            f"parser reads. Treating it as a fetch or template failure rather than a "
            f"cinema with nothing on")
    today = today or datetime.datetime.now(FI).date()
    # Headings and list items interleaved in document order: the heading above an item is
    # the film it belongs to.
    stream = sorted([(m.start(), "head", m.group(1)) for m in HEAD_RE.finditer(page)] +
                    [(m.start(), "item", m.group(1)) for m in ITEM_RE.finditer(page)])
    shows, seen, unplaced, title = [], set(), [], None
    for _, kind, raw in stream:
        text = _txt(raw)
        if kind == "head":
            if text and not NOT_A_TITLE.match(text):
                title = text
            continue
        m = SHOW_RE.match(text)
        if not m or not title:
            continue                # cast, director, a note, an address, or "Tulossa 25.9."
        day, month, wd, hh, mm = (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
        day, month = int(day), int(month)
        year = resolve_year(day, month, today, weekday_index(wd))
        if year is None:
            unplaced.append(f"{wd} {day}.{month}.")
            continue
        try:
            start = datetime.datetime(year, month, day, int(hh), int(mm), tzinfo=FI)
        except ValueError:
            continue
        eid = synmerge.norm(title)
        key = (eid, start.isoformat())
        if key in seen:
            continue                # the desktop and mobile copies of the same screening
        seen.add(key)
        shows.append({
            "eventId": eid,
            "title": title,
            "original": "",
            "len": "",
            "rating": "",
            "genres": "",
            "method": "",
            "theatre": VENUE["name"],
            "aud": "",
            "start": start.isoformat(),
            "url": LISTING,
            "img": "",
            "lang": "",
            "soldOut": False,
            "price": "",
            "provider": "kirkkonummi",
            "venue": VENUE["id"],
        })
    if unplaced:
        print(f"[kirkkonummi] {len(unplaced)} row(s) whose weekday matches no candidate "
              f"year, skipped: {', '.join(unplaced[:5])}")
    if not shows:
        raise EmptyProgramme(f"{LISTING} lists films but no screening row")
    shows.sort(key=lambda s: s["start"])
    return shows


def get_listing():
    return fetch(LISTING, cache=True,
                 headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"},
                 timeout=30).decode("utf-8", "replace")


def fetch_site(site=SITES[0]):
    """Runner contract: one page, one venue."""
    shows = parse(get_listing())
    print(f"[kirkkonummi] {len(shows)} showtimes, "
          f"{len({s['eventId'] for s in shows})} films, "
          f"{len({s['start'][:10] for s in shows})} dates")
    return {VENUE["id"]: shows}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = (parse(open(src, encoding="utf-8", errors="replace").read()) if src
            else fetch_site()[VENUE["id"]])
    for s in data:
        print(f"  {s['start'][:16]} {s['title'][:40]:42} {s['eventId'][:24]}")
