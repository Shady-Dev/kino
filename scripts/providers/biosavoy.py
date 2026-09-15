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
"""
import datetime
import html as html_mod
import re
import sys

from common import EmptyProgramme, fetch

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


def get_page():
    return fetch(BASE + "/", cache=True,
                 headers={"user-agent": UA, "accept-language": "sv-AX,sv;q=0.9"},
                 timeout=30).decode("utf-8", "replace")


def fetch_site(site=SITES[0]):
    """Runner contract: one page, one venue."""
    shows = parse(get_page())
    print(f"[biosavoy] {len(shows)} showtimes, {len({s['eventId'] for s in shows})} films, "
          f"{len({s['start'][:10] for s in shows})} dates, "
          f"halls {sorted({s['aud'] for s in shows})}")
    return {VENUE["id"]: shows}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = (parse(open(src, encoding="utf-8", errors="replace").read()) if src
            else fetch_site()[VENUE["id"]])
    for s in data:
        print(f"  {s['start'][:16]} {s['aud']:7} {s['title'][:34]:36} {s['url']}")
