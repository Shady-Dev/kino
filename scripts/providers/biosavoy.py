"""Bio Savoy, Mariehamn, Åland. Stdlib only.

Probed 2026-09-15. Drupal, server-rendered, and the only source added this week that needs
nothing inferred: every screening carries a full ISO instant with its offset, in the
markup, put there by Drupal's own date field.

    <h2 class="block-title">Filmvisningar - Sal 1</h2>
    ...<a href="/film/dog-stars"><span class="date-display-single" property="dc:date"
         datatype="xsd:dateTime" content="2026-09-15T18:00:00+03:00">18:00</span>
       - THE DOG STARS</a>

- **The `content` attribute is the time**, not the `18:00` next to it. It carries the date,
  the clock and `+03:00`, so there is no year to resolve, no weekday to verify and no
  timezone to assume. `common.resolve_year` is not used here and should not be.
- **Two halls, two blocks.** `Filmvisningar - Sal 1` and `Filmvisningar - Sal 2` are
  separate `block-filmer-schema-block` sections, and the hall comes from the block title
  rather than from anything on the row. Reading the rows without their block would lose it.
- **The film's slug is the id**, from `/film/{slug}`, and the title is the text after the
  dash.

**This site is http only, and that is deliberate here rather than an oversight.** Port 443
is refused on both `biosavoy.ax` and `www.biosavoy.ax` (checked 2026-09-15), and
`http://biosavoy.ax/` redirects to `http://www.biosavoy.ax/`. So every URL this adapter
publishes is http: the alternative is inventing https support the host does not have,
which would hand the reader a link that cannot connect. `safeUrl()` in the client accepts
http, and no repository rule forbids an http destination. If that is ever to change it has
to change at the cinema.

The site publishes no poster, age limit or runtime anywhere, so those stay empty and the
TMDB pass fills what it can; there is no site image to mirror.

`book="door"`: "Bokningar tas emot per telefon 0457 3459 788 ... Vi tar enbart emot
bokningar fram till dagen före aktuell föreställning." No online sale exists, so a showtime
opens the film's own page.

The city is keyed `Mariehamn`, the town's only official name: Åland's sole official
language is Swedish. Every other city key here is a Finnish name because `CITY_SV` in
`index.html` translates them for the Swedish interface, and that table cannot gain an entry
without editing a file this project keeps frozen. Keying the Finnish exonym would therefore
show it untranslated in Swedish, which is the wrong way round for Åland.


## The price, from each film's own page

Each `/film/{slug}` carries a labelled field:

    <section class="field field-name-field-price"><h2 class="field-label">Pris:</h2>
      <ul class="field-items"><li class="field-item even">15 €</li></ul></section>

The film's own statement, not a rule to derive, which is why it can be published where TMB's
and Cine Mäntsälä's tariffs cannot: there is nothing to work out about the day, the format or
the length. Surveyed across **all thirteen** films on 2026-09-16, not a sample: every one
carried the field, every one held a single amount, 15 € except two children's films at 13 €,
and no page carried a second amount or any per-screening note. That agrees with what
`/om-oss` says the two gift-card denominations are for, "13€ (barnfilmer samt filmer med
svenskt tal)".

**What that establishes is the field, not a guarantee.** Thirteen pages on one day say the
field exists and is single-valued today; they cannot say it always will be. So the reader
publishes nothing rather than something whenever it cannot be sure: no field, more than one
distinct amount under it, a page that did not answer, or a film past the request budget. A
screening whose film was not read keeps an empty `price` and the rest of the schedule is
unaffected.

**One request per distinct film**, paced, cached and budgeted -- thirteen today against the
one this adapter used to make. The front page carries only the gift-card sentence, "13€
(barnfilmer) och 15€" and 135 € for ten tickets, which is not a tariff and is not read.
See `docs/research/prices.md`.
"""
import datetime
import html as html_mod
import re
import sys
import time

from common import EmptyProgramme, capped, fetch

BASE = "http://www.biosavoy.ax"
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

VENUE = {"id": "savoy-mariehamn", "name": "Bio Savoy", "short": "Bio Savoy",
         "city": "Mariehamn"}

SITES = [{"provider": "biosavoy", "label": "Bio Savoy", "base": BASE, "venues": [VENUE]}]

CONTAINER_RE = re.compile(r'block-filmer-schema-block', re.I)
BLOCK_RE = re.compile(r'<h2 class="block-title">([^<]*)</h2>(.*?)(?=<h2 class="block-title">|\Z)',
                      re.S | re.I)
HALL_RE = re.compile(r'Filmvisningar\s*-\s*(.+?)\s*$', re.I)
ROW_RE = re.compile(r'<a href="(/film/[^"]+)">\s*<span class="date-display-single"[^>]*'
                    r'content="([^"]+)"[^>]*>[^<]*</span>\s*-\s*([^<]+)</a>', re.S | re.I)
TAGS_RE = re.compile(r"<[^>]+>")
# The film page's labelled price field. Every `field-item` under it is captured, so a second
# one is seen rather than silently ignored: two different amounts mean the page no longer
# says one thing and nothing is published for that film.
PRICE_BLOCK_RE = re.compile(r'field-name-field-price(.*?)</section>', re.S | re.I)
PRICE_ITEM_RE = re.compile(r'<li[^>]*class="field-item[^"]*"[^>]*>(.*?)</li>', re.S | re.I)
AMOUNT_RE = re.compile(r'(\d{1,3}(?:[.,]\d{1,2})?)\s*\u20ac')


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))
                  .replace("\xa0", " ")).strip()


def parse(page):
    """The front page -> [show]. Raises when no schedule block is present, and
    `EmptyProgramme` when the blocks are there with no screening row."""
    if not CONTAINER_RE.search(page):
        raise RuntimeError(
            f"{BASE}: no schedule block on the page, so this is not the programme this "
            f"parser reads. Treating it as a fetch or template failure rather than a "
            f"cinema with nothing on")
    shows, seen = [], set()
    for title, body in BLOCK_RE.findall(page):
        hall = HALL_RE.match(_txt(title))
        if not hall:
            continue                    # "Dela", the share block, and anything else
        aud = _txt(hall.group(1))
        for href, when, name in ROW_RE.findall(body):
            try:
                start = datetime.datetime.fromisoformat(when.strip())
            except ValueError:
                continue
            if start.tzinfo is None:
                continue                # the offset is what makes this instant unambiguous
            name = _txt(name)
            slug = href.rsplit("/", 1)[-1]
            if not name or not slug:
                continue
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
        raise EmptyProgramme(f"{BASE} has its schedule blocks but no screening row")
    shows.sort(key=lambda s: (s["start"], s["aud"]))
    return shows


def film_price(page):
    """The film's own price. -> "15\u20ac", or "" when the page does not say one thing.

    Empty for a page with no price field, for one whose field holds no readable amount, and
    for one holding two different amounts -- there the page has stopped saying a single
    thing and picking either would publish the doubt. The same amount twice is not two
    things.
    """
    block = PRICE_BLOCK_RE.search(page)
    if not block:
        return ""
    amounts = set()
    for item in PRICE_ITEM_RE.findall(block.group(1)):
        m = AMOUNT_RE.search(_txt(item))
        if m:
            amounts.add(float(m.group(1).replace(",", ".")))
    if len(amounts) != 1:
        return ""
    return f"{amounts.pop():.2f}".rstrip("0").rstrip(".") + "\u20ac"


def get(url):
    return fetch(url, cache=True,
                 headers={"user-agent": UA, "accept-language": "sv-AX,sv;q=0.9"},
                 timeout=30).decode("utf-8", "replace")


def get_page():
    return get(BASE + "/")


def film_prices(slugs, sleep=1.5, get=None):
    """{slug: price} for the films whose page said one thing. -> dict.

    One request per **distinct** film, paced and cached, and bounded by the shared page
    budget -- `capped`, not `budget_or_raise`, because these pages carry no showtime: a film
    past the cap loses its price and keeps its screenings, which is the right way round.

    A page that will not answer costs that film's price and nothing else. The schedule is
    already parsed by the time this runs, and a cinema's whole programme must not go stale
    because one film page 500s.
    """
    get = get or globals()["get"]
    out = {}
    for n, slug in enumerate(capped(slugs, "biosavoy")):
        if n:
            time.sleep(sleep)
        try:
            out[slug] = film_price(get(f"{BASE}/film/{slug}"))
        except Exception as e:
            print(f"[biosavoy] film page {slug}: {type(e).__name__}: {e}", file=sys.stderr)
    # Films whose page said nothing are in here as "", which is what the caller publishes
    # for them anyway. Filtering them out would be a branch nothing can observe.
    return out


def fetch_site(site=SITES[0], sleep=1.5):
    """Runner contract: the front page, then one film page per distinct film."""
    shows = parse(get_page())
    prices = film_prices(sorted({s["eventId"] for s in shows}), sleep=sleep)
    for s in shows:
        s["price"] = prices.get(s["eventId"], "")
    print(f"[biosavoy] {len(shows)} showtimes, {len({s['eventId'] for s in shows})} films, "
          f"{len({s['start'][:10] for s in shows})} dates, "
          f"halls {sorted({s['aud'] for s in shows})}, "
          f"{sum(1 for s in shows if s['price'])} priced")
    return {VENUE["id"]: shows}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = (parse(open(src, encoding="utf-8", errors="replace").read()) if src
            else fetch_site()[VENUE["id"]])
    for s in data:
        print(f"  {s['start'][:16]} {s['aud']:7} {s['title'][:34]:36} {s['url']}")
