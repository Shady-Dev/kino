"""Kino Kuvakukko (Kuopio) and Nilsiän Kino Manttu, on one page. Stdlib only.

Probed 2026-09-15. Both cinemas are the city of Kuopio's, and both schedules live on a
single WordPress page, `/ohjelmisto/kuvakukon-ja-kino-mantun-ohjelmisto/`. One provider,
two venues, one request, the shape `vista.py` and `nexxo.py` already use for an operator
whose venues share a source.

    <h2 class="wp-block-heading">Kino Kuvakukon esitysaikataulu</h2>
    <p class="wp-block-paragraph">Tiistai 15.9.<br>
      Klo 13: <a href="https://isak.fi/hopeatahti-elokuvasarja/">Hopeatähti-sarja: ...</a><br>
      Klo 17.30: <a href=".../tulossa-hetki-ennen-valoa/" data-id="2698">Hetki ennen valoa</a></p>
    ...
    <h2 class="wp-block-heading">Nilsiän Kino Mantun esitysaikataulu</h2>

Five things that shape the parser:

- **The two headings are the venue boundary.** Everything between one `<h2>` and the next
  belongs to that cinema. Reading the page without them would file Nilsiä's weekend under
  Kuopio, which is the kind of error nothing downstream would catch.
- **A paragraph is a day**, and only if it opens with a weekday and a date. The same
  element type carries the addresses, the prices and the opening hours, and those simply
  do not match, so no list of things to exclude is needed.
- **The date has no year but the day has a weekday**, `Tiistai 15.9.`, and that determines
  the year: the same day and month falls on a different weekday in each candidate year, so
  exactly one can match. `common.resolve_year` does it. A weekday matching none of them
  leaves the row unplaced and counted rather than moved to a date the page did not mean.
- **Manttu publishes every other weekend**, so its section is routinely a schedule that has
  already passed. That is correct output, not staleness to correct: the weekday places the
  rows in the past where they belong and the client filters them. Nothing here treats a
  past date as a reason to shift a year.
- **The time is written two ways**, `Klo 13:` and `Klo 17.30:`, hours alone or hours and
  minutes with a dot.

Titles are published verbatim, including a strand prefix like "Hopeatähti-sarja: ". The
central pass in `run.py` splits the prefixes `strands.EVENT_PREFIXES` names, and that list
is exact on purpose; adding a name to it is its own decision and is not made here.

`book="door"` for both: the page states "Lipunmyynti vain Kuvakukossa" and, for Manttu,
"Ei ennakkovarauksia, lipunmyynti vain Mantulla. Maksuvälineenä käy vain käteinen." There
is no online sale to link to, so a showtime opens the film's own page on this site when it
has one and the programme page when it does not.
"""
import datetime
import html as html_mod
import re
import sys
from zoneinfo import ZoneInfo

import synmerge
from common import EmptyProgramme, fetch, resolve_year, weekday_index

BASE = "https://www.kuvakukko.fi"
LISTING = BASE + "/ohjelmisto/kuvakukon-ja-kino-mantun-ohjelmisto/"
FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

VENUES = [
    {"id": "kk-kuopio", "match": "kuvakuk", "name": "Kino Kuvakukko",
     "short": "Kuvakukko", "city": "Kuopio"},
    {"id": "kk-nilsia", "match": "mantu", "name": "Kino Manttu", "short": "Manttu",
     "city": "Nilsiä"},
]

SITES = [{"provider": "kuvakukko", "label": "Kuvakukko", "base": BASE, "venues": VENUES}]

# One cinema's heading present with no day paragraph under it, while the other has rows,
# is positive evidence that it is between programmes: both schedules are on the same page,
# so the read cannot have half-failed. Both empty raises EmptyProgramme instead.
EMPTY_VENUES_CONFIRMED = True

# A heading is present with no day paragraph under it only when that cinema has nothing
# on; a page with no heading at all is a changed template.
CONTAINER_RE = re.compile(r'<h2[^>]*>[^<]*esitysaikataulu', re.I)
HEADING_RE = re.compile(r'<h2[^>]*>(.*?)</h2>', re.S | re.I)
PARA_RE = re.compile(r'<p[^>]*class="[^"]*wp-block-paragraph[^"]*"[^>]*>(.*?)</p>', re.S | re.I)
DAY_RE = re.compile(r'^\s*([A-Za-zÄÖäö]{2,12})\s+(\d{1,2})\.(\d{1,2})\.', re.I)
ROW_RE = re.compile(r'Klo\s*(\d{1,2})(?:[.:](\d{2}))?\s*:\s*'
                    r'(?:<a\s+href="([^"]*)"[^>]*>(.*?)</a>|([^<]{2,80}))',
                    re.S | re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))
                  .replace("\xa0", " ")).strip()


def _sections(page):
    """-> [(heading text, the markup under it)], split on the `<h2>` headings."""
    heads = list(HEADING_RE.finditer(page))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(page)
        out.append((_txt(h.group(1)), page[h.end():end]))
    return out


def _venue_for(heading):
    low = heading.lower()
    for v in VENUES:
        if v["match"] in low:
            return v
    return None


def parse(page, site=None, today=None):
    """The shared page -> {venue_id: [show]}. Raises when no schedule heading is present,
    and `EmptyProgramme` when the headings are there with no screening under them."""
    site = site or SITES[0]
    if not CONTAINER_RE.search(page):
        raise RuntimeError(
            f"{LISTING}: no 'esitysaikataulu' heading on the page, so this is not the "
            f"programme this parser reads. Treating it as a fetch or template failure "
            f"rather than a cinema with nothing on")
    today = today or datetime.datetime.now(FI).date()
    per_venue = {v["id"]: [] for v in VENUES}
    seen, unplaced = set(), []
    for heading, body in _sections(page):
        venue = _venue_for(heading)
        if venue is None or "esitysaikataulu" not in heading.lower():
            continue
        for para in PARA_RE.findall(body):
            d = DAY_RE.match(_txt(para))
            if not d:
                continue                    # an address, a price list, opening hours
            wd, day, month = d.group(1), int(d.group(2)), int(d.group(3))
            year = resolve_year(day, month, today, weekday_index(wd))
            if year is None:
                unplaced.append(f"{wd} {day}.{month}.")
                continue
            for hh, mm, href, linked, plain in ROW_RE.findall(para):
                title = _txt(linked or plain)
                if not title:
                    continue
                try:
                    start = datetime.datetime(year, month, day, int(hh), int(mm or 0),
                                              tzinfo=FI)
                except ValueError:
                    continue
                own = (href or "").startswith(BASE)
                # The page's own `data-id` is a WordPress post id, and a film gets a new
                # post per run here ("tulossa-hetki-ennen-valoa"), so it identifies the
                # posting rather than the film. The normalised title is the key
                # `synmerge` and the client's `normTitle` already use.
                eid = synmerge.norm(title)
                key = (venue["id"], eid, start.isoformat())
                if key in seen:
                    continue
                seen.add(key)
                per_venue[venue["id"]].append({
                    "eventId": eid,
                    "title": title,
                    "original": "",
                    "len": "",
                    "rating": "",
                    "genres": "",
                    "method": "",
                    "theatre": venue["name"],
                    "aud": "",
                    "start": start.isoformat(),
                    "url": href if own else LISTING,
                    "img": "",
                    "lang": "",
                    "soldOut": False,
                    "price": "",
                    "provider": site["provider"],
                    "venue": venue["id"],
                })
    if unplaced:
        print(f"[kuvakukko] {len(unplaced)} day(s) whose weekday matches no candidate "
              f"year, skipped: {', '.join(unplaced[:5])}")
    if not any(per_venue.values()):
        raise EmptyProgramme(f"{LISTING} has its headings but no screening under them")
    for shows in per_venue.values():
        shows.sort(key=lambda s: s["start"])
    return per_venue


def get_listing():
    return fetch(LISTING, cache=True,
                 headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"},
                 timeout=30).decode("utf-8", "replace")


def fetch_site(site=SITES[0]):
    """Runner contract: one page, two venues.

    A venue with no row is returned as an empty list only when the other one has rows:
    both schedules are on the same page, so one cinema being between programmes is
    positive evidence, while both being empty already raised `EmptyProgramme` above.
    """
    per_venue = parse(get_listing(), site)
    for vid, shows in per_venue.items():
        print(f"[kuvakukko] {vid}: {len(shows)} showtimes, "
              f"{len({s['start'][:10] for s in shows})} dates")
    return per_venue


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = (parse(open(src, encoding="utf-8", errors="replace").read()) if src
            else fetch_site())
    for vid, shows in data.items():
        print(f"== {vid} ==")
        for s in shows[:8]:
            print(f"  {s['start'][:16]} {s['title'][:44]:46} {s['eventId'][:18]}")
