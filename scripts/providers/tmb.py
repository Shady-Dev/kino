"""TMB Cinema Oy: Kino-Toijala, Kino-Sampo, KinoMania and Elokuvateatteri Elo.

Probed 2026-09-15. Four cinemas, one operator, four sites built on the same template
(footer: "Mediapalvelu W3D"). None of them is on a platform this repo already reads: the
eTiketti listing path answers 200 with no film links on all four, and the
`cdn.etiketti.app/studio123/...` URLs in their markup are syndicated opera posters, not a
sign of an eTiketti tenancy. So this is one adapter for four sites, not four parsers.

**They are four cinemas, not one mirrored four times.** That had to be established before
adding any of them, because the pages look alike and the schedules coincide: Kino-Toijala
and Kino-Sampo published an identical set of 23 screenings on the day this was written,
and KinoMania and Elo an identical set of 32. What separates them is the booking id. For
the same film at the same minute, `?varaa=` is 21001 at Toijala, 21006 at Sampo, 21012 at
Elo and 21015 at Mania: four rows in the operator's system, one per cinema, a chain
booking the same films at the same times. Their screen counts differ too, which a mirror
could not do: Mania and Elo print `, sali 1` / `, sali 2` and the other two print no
auditorium at all.

**One request per venue.** `{base}/?lista=1` is the whole published programme as a list,
each row a screening:

    <small>TI&nbsp;15.09.2026 klo&nbsp;14:00, sali&nbsp;1</small></b>
    <h2 ...><a href="?ohjelmisto=842">Hetki ennen valoa</a></h2></td>
    <td ...><img ... src="/files/images/ikaraja_2.png" alt="Ikäraja">

The date carries its year, so nothing is inferred. Every row in this view is a timed
screening; the coming-soon entries live in the default grid view and are not read here.

Three things this parser deliberately does not do:

- **It does not link to `?varaa=`.** That is the seat-reservation action, and this repo
  does not call booking endpoints, so a link there could never be checked before being
  published. Six Nexxo sites once shipped dead ticket links exactly that way. The showtime
  links to `?ohjelmisto={id}`, the public film page, which carries the screening list and
  the site's own booking buttons. Hence `book="reserve"` in the registry.
- **It does not invent an age limit.** The rating is only in the image filename, and the
  film page states it nowhere in text. `ikaraja_2`, `_3` and `_4` were checked against
  this repo's own committed data for five films that other providers also carry (K-7,
  K-12 twice, K-16 twice) and agree. `ikaraja_1` appears only on opera events, which no
  provider here rates, so it is **not** mapped: a sequence that looks like S, K-7, K-12,
  K-16 is a guess, and a wrong classification is worse than none. An unmapped image
  yields no rating and the TMDB pass fills what it can.
- **It does not read the film page.** That page carries a runtime and a per-screening
  price, and reading it would cost one request per film per venue, about 68 a run against
  a third party. The runtime stays unpublished for that reason; the price no longer has
  to, see below.

## The price, from the site's own price page

Added 2026-09-16 on the maintainer's instruction, and **not** from the film page. Each
list view already links the operator's price page in its own nav -- `?hinnat=2` at
Toijala, `3` at Sampo, `4` at Mania, `1` at Elo -- so the number is read from the page in
hand rather than written down per site, and the cost is **one request per venue**, not one
per film. Read as a visitor 2026-09-16; all four state the same table.

    Liput   2D  Aikuinen 14.45 €  Eläkeläinen 12.45 €  Lapsi 11.45 €
                LA, SU ja arkipyhät +0.50 €
            3D  Aikuinen 16.95 €  Eläkeläinen 15.95 €  Lapsi 13.95 €

Published as `"14.45€ / 12.45€ / 11.45€"`, the three tiers in the order the page prints
them, which is the shape `julia.py` already publishes and which `build_pages.price_label`
renders as a floor. The Saturday and Sunday surcharge is applied, because the page states
it and the film page confirms it: a Sunday row reads 14.95 / 12.95 / 11.95.

**Two things it cannot know, stated rather than papered over.**

- *Arkipyhä.* The same rule adds 0.50 on a weekday public holiday. Which days those are is
  a calendar this repo does not carry, so a screening on one is published 0.50 low. The
  rendered label is a floor, so it understates rather than overstates.
- *3D.* The list view carries no 3D marker at all -- the three `3D` strings on the page are
  the `<title>` and the W3D footer -- so a 3D screening is indistinguishable from a 2D one
  and would be published at the 2D price. No row on any of the four sites was 3D when this
  was written. Nothing here notices if one appears; the remedy is a marker on the row, and
  guessing from a title is what this adapter already refuses to do for age limits.

A price page that cannot be read or parsed costs the prices and nothing else: the
screenings publish with `price` empty and the run stays green, because a missing price is
metadata and the schedule is not.

A list view whose container is present with no screening row is a confirmed empty
programme; a page without the container is a template change and fails the venue.
"""
import datetime
import html as html_mod
import re
import sys
import time
from zoneinfo import ZoneInfo

from common import EmptyProgramme, fetch

FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

SITES = [
    {"provider": "kinotoijala", "label": "Kino-Toijala", "base": "https://toijalan-kino.info",
     "venues": [{"id": "tmb-toijala", "name": "Kino-Toijala", "short": "Kino-Toijala",
                 "city": "Akaa"}]},
    {"provider": "kinosampo", "label": "Kino-Sampo", "base": "https://kinosampo.info",
     "venues": [{"id": "tmb-sampo", "name": "Kino-Sampo", "short": "Kino-Sampo",
                 "city": "Valkeakoski"}]},
    {"provider": "kinomania", "label": "KinoMania", "base": "https://kino-mania.info",
     "venues": [{"id": "tmb-mania", "name": "KinoMania", "short": "KinoMania",
                 "city": "Pieksämäki"}]},
    {"provider": "kinoelo", "label": "Elokuvateatteri Elo", "base": "https://elokuvat-elo.info",
     "venues": [{"id": "tmb-elo", "name": "Elokuvateatteri Elo", "short": "Elo",
                 "city": "Heinola"}]},
]

# See the docstring: the list container is what separates "nothing on" from a changed
# template, so an empty result is only ever published on its evidence.
EMPTY_VENUES_CONFIRMED = True

CONTAINER_RE = re.compile(r'Valkokankaalla', re.I)
ROW_RE = re.compile(
    r'<small>\s*([A-ZÄÖ]{2})(?:&nbsp;|\s)(\d{1,2})\.(\d{1,2})\.(\d{4})\s*klo(?:&nbsp;|\s)'
    r'(\d{1,2}):(\d{2})([^<]*)</small>\s*</b>\s*'
    r'<h2[^>]*>\s*<a\s+href="\?ohjelmisto=(\d+)"\s*>([^<]+)</a>\s*</h2>',
    re.S | re.I)
AGE_RE = re.compile(r'ikaraja_(\w+)\.png', re.I)
SALI_RE = re.compile(r'sali(?:&nbsp;|\s)*([\w-]+)', re.I)

# The price page, and the tiers on it. The link is read from the list view rather than
# written per site: each of the four numbers its own, and a number copied between sites is
# how six Nexxo links once shipped dead.
PRICE_LINK_RE = re.compile(r'\?hinnat=(\d+)')
TIER_RE = re.compile(r'(Aikuinen|El\u00e4kel\u00e4inen|Lapsi)\s*(\d{1,3}[.,]\d{2})\s*\u20ac', re.I)
# "LA, SU ja arkipyhät +0.50 €". Only the amount is read; which days it applies to is in
# the module docstring, and only the two this parser can identify are applied.
SURCHARGE_RE = re.compile(r'\+\s*(\d{1,3}[.,]\d{2})\s*\u20ac')
# In the order the page prints them, which is the order they are published in.
TIERS = ("aikuinen", "el\u00e4kel\u00e4inen", "lapsi")

# Measured against this repo's own committed ratings for films other providers also carry.
# 1 and 5 are deliberately absent; see the docstring.
AGE = {"2": "K-7", "3": "K-12", "4": "K-16"}

# The row prints the weekday the operator published. It is not used to build the date --
# the date is complete on its own -- but a row whose weekday contradicts its date means
# the template moved fields around, and that is worth counting rather than publishing.
WEEKDAYS = ("MA", "TI", "KE", "TO", "PE", "LA", "SU")

TAGS_RE = re.compile(r"<[^>]+>")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))
                  .replace("\xa0", " ")).strip()


def parse(page, site, venue):
    """`{base}/?lista=1` -> [show] for the one venue the site serves."""
    if not CONTAINER_RE.search(page):
        raise RuntimeError(
            f"{site['base']}: no 'Valkokankaalla' programme container in the response, so "
            f"this is not the list view this parser reads. Treating it as a fetch or "
            f"template failure rather than a cinema with nothing on")
    shows, seen, wrong_day = [], set(), 0
    for m in ROW_RE.finditer(page):
        wd, day, month, year, hh, mm, tail, fid, title = m.groups()
        title = _txt(title)
        if not title:
            continue
        try:
            start = datetime.datetime(int(year), int(month), int(day), int(hh), int(mm),
                                      tzinfo=FI)
        except ValueError:
            continue
        if WEEKDAYS[start.weekday()] != wd.upper():
            wrong_day += 1
            continue
        sali = SALI_RE.search(tail or "")
        aud = f"Sali {_txt(sali.group(1))}" if sali else ""
        # The age image sits in the row's second cell, just past the title.
        age = AGE_RE.search(page[m.end():m.end() + 400])
        key = (fid, start.isoformat(), aud)
        if key in seen:
            continue
        seen.add(key)
        shows.append({
            "eventId": fid,
            "title": title,
            "original": "",
            "len": "",
            "rating": AGE.get(age.group(1), "") if age else "",
            "genres": "",
            "method": "",
            "theatre": venue["name"],
            "aud": aud,
            "start": start.isoformat(),
            "url": f"{site['base']}/?ohjelmisto={fid}",
            "img": "",
            "lang": "",
            "soldOut": False,
            "price": "",
            "provider": site["provider"],
            "venue": venue["id"],
        })
    if wrong_day:
        print(f"[tmb] {site['provider']}: {wrong_day} row(s) whose weekday contradicts "
              f"their date, skipped")
    if not shows:
        raise EmptyProgramme(f"{site['base']}/?lista=1 lists no screening")
    shows.sort(key=lambda s: (s["start"], s["aud"]))
    return shows


def price_url(page, base):
    """The site's own price page, from the link its list view carries. -> url, or "".

    Read rather than written down: the four sites number it 2, 3, 4 and 1, and a number
    copied from one site onto another is exactly how six Nexxo ticket links once shipped
    dead. No link, no price page, no price.
    """
    m = PRICE_LINK_RE.search(page)
    return f"{base}/?hinnat={m.group(1)}" if m else ""


def price_tiers(page):
    """The 2D ticket prices and the weekend surcharge. -> ([float, ...], float).

    Empty when the block is not there or does not hold all three tiers: a partial table is
    not published, because which tier a lone amount belongs to would be a guess.

    Bounded to the 2D block, between `Liput` and the `3D` heading after it. The 3D tiers
    are 2.50 higher and sit immediately below, so an unbounded search publishes those; the
    page `<title>` also carries "3D-elokuvat", which is why the search starts at `Liput`
    rather than at the first `3D` on the page.
    """
    text = _txt(page)
    start = text.find("Liput")
    i = text.find("2D", start) if start >= 0 else -1
    if i < 0:
        return [], 0.0
    j = text.find("3D", i + 2)
    block = text[i:j if j > i else i + 300]
    found = {k.lower(): float(v.replace(",", ".")) for k, v in TIER_RE.findall(block)}
    if not all(k in found for k in TIERS):
        return [], 0.0
    m = SURCHARGE_RE.search(block)
    return [found[k] for k in TIERS], float(m.group(1).replace(",", ".")) if m else 0.0


def _amount(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def price_of(tiers, surcharge, start):
    """One screening's price. -> "14.45€ / 12.45€ / 11.45€", or "" with no table.

    The surcharge applies on Saturday and Sunday, which the price page states and the film
    page confirms. It also applies on a weekday public holiday, which nothing here can
    identify; see the module docstring.
    """
    if not tiers:
        return ""
    bump = surcharge if start.weekday() >= 5 else 0.0
    return " / ".join(f"{_amount(v + bump)}\u20ac" for v in tiers)


def get(url):
    return fetch(url, cache=True,
                 headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"},
                 timeout=30).decode("utf-8", "replace")


def get_list(site):
    return get(site["base"] + "/?lista=1")


def fetch_site(site, sleep=1.0):
    """Runner contract: one list view, one venue, and one price page after it."""
    venue = site["venues"][0]
    page = get_list(site)
    shows = parse(page, site, venue)
    tiers, surcharge = [], 0.0
    url = price_url(page, site["base"])
    if url:
        time.sleep(sleep)
        try:
            tiers, surcharge = price_tiers(get(url))
        except Exception as e:
            # The schedule is already parsed and is what this venue is for. A price page
            # that will not answer costs the prices and nothing else.
            print(f"[tmb] {site['provider']}: {url}: {e}; publishing without prices",
                  file=sys.stderr)
    if not tiers:
        print(f"[tmb] {site['provider']}: no price table read from "
              f"{url or 'a page that links none'}", file=sys.stderr)
    for s in shows:
        s["price"] = price_of(tiers, surcharge,
                              datetime.datetime.fromisoformat(s["start"]))
    print(f"[tmb] {site['provider']}: {len(shows)} showtimes, "
          f"{len({s['eventId'] for s in shows})} films, "
          f"{len({s['start'][:10] for s in shows})} dates, "
          f"{sum(1 for s in shows if s['price'])} priced")
    return {venue["id"]: shows}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else None
    for site in SITES:
        if which and site["provider"] != which:
            continue
        data = fetch_site(site)[site["venues"][0]["id"]]
        for s in data[:6]:
            print(f"  {s['start'][:16]} {s['aud'] or '-':8} {s['title'][:34]:36} "
                  f"{s['rating']:5} {s['url'][-22:]}")
