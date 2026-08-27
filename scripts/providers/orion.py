"""Cinema Orion (Helsinki, Eerikinkatu 15, run by ELKE ry) — front page table. Stdlib only.

Everything the app needs is server-rendered on one page: a `<table class="kinola-day">`
per day, one `<tr>` per screening carrying date, time, title, price and the ticket link.
One request, no per-film follow-up.

Two things the source dictates:
  * **Ticket URLs come from the markup, never built.** Most point at
    orion.kinola.ee/web/screening/{uuid}, but festival screenings link to the festival's
    own box office instead (Espoo Ciné -> boxoffice.espoocine.fi). A templated URL would
    be dead for exactly the screenings that are hardest to find elsewhere. A row with no
    link at all (free admission) falls back to the programme page.
  * The price cell's `title` attribute carries the full ticket-type breakdown, so a
    screening with cheaper types reads "alkaen 8.5€" rather than the base price alone.

The title cell has two shapes and both matter:

    <td class='title'> Espoo Ciné: Four Minus Three </td>
    <td class='title'><a href='/elokuvat/{slug}/' title ="Film"> Film
      <span class="descrption">Finnish blurb<span> </a></td>

The linked shape wraps the title together with a screening blurb, so the film title is
read from the anchor's `title` attribute, not from the cell's text: flattening the cell
glues the blurb onto the title, which splits one film into one "film" per blurb and
leaves TMDB nothing to match. `descrption` is the site's spelling, and its inner
`<span>` is never closed, so that span is cut at whatever tag comes next. The blurb
goes to `_syn`; it mixes screening notes ("Ensi-iltaelokuva, klubialennus.") into the
synopsis, but synmerge only ever fills an empty slot.

`eventId` comes from the film page slug where there is one, so repeat screenings of the
same film share an id. Festival rows have no film page and fall back to a slug of the
title.

A known event prefix ("Espoo Ciné:", "Pieni elokuvakerho:") is split off the title into
`method`, where the client already renders it as a pill. The film title then stands
alone, which is what the poster fallback tile and the TMDB search both need: with the
prefix left in, every Espoo Ciné screening rendered the same "EC" tile and none of the
17 titles could be searched. The list is `enrich_tmdb.EVENT_PREFIXES`, shared so a new
strand is added in one place (`strands.py`), matched exactly, never as a colon pattern, or
"Dyyni: Osa kolme" loses its head.

The programme includes third-party events (festivals, HopeaCine, Orion Club), which are
real screenings at this venue and belong in the data. They arrive with prefixes like
"Espoo Ciné:"; that is enrich_tmdb.clean()'s problem, not this adapter's, and the title
is stored exactly as published so norm() keys stay in agreement with the client.

Single screen, so `aud` stays blank. The table has no age limits, runtimes or seat
counts, and there is no per-film page in it, so those fields stay empty and the TMDB
pass fills what it can.
"""
import datetime, html as html_mod, re, sys, unicodedata, urllib.request
from zoneinfo import ZoneInfo

from strands import split as split_strand

URL = "https://cinemaorion.fi/"
FI = ZoneInfo("Europe/Helsinki")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

VENUE = {"id": "or-helsinki", "provider": "orion", "name": "Cinema Orion",
         "short": "Cinema Orion", "city": "Helsinki"}

# Single screen, so one site with one venue. See run.py for the contract.
SITES = [{"provider": "orion", "label": "Cinema Orion", "venues": [VENUE]}]

# <h3><span>Torstai</span> 27.08.</h3> then <table class="kinola-day">...
BLOCK_RE = re.compile(r'<h3\b[^>]*>(?P<head>.*?)</h3>'
                      r'|<table\b[^>]*class=["\'][^"\']*kinola-day[^"\']*["\'][^>]*>'
                      r'(?P<table>.*?)</table>', re.S | re.I)
ROW_RE = re.compile(r'<tr\b[^>]*>(.*?)</tr>', re.S | re.I)
CELL_RE = re.compile(r'<td\b([^>]*)>(.*?)</td>', re.S | re.I)
CLASS_RE = re.compile(r'class=["\']([^"\']*)["\']', re.I)
ANCHOR_RE = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.S | re.I)
TITLE_ATTR_RE = re.compile(r'title\s*=\s*["\']([^"\']*)["\']', re.I)
HREF_RE = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.I)
SLUG_URL_RE = re.compile(r'/elokuv[au]t?/([^/?#"\']+)', re.I)
# The site spells it "descrption", and the span inside it is never closed, so stop at
# whatever tag comes next rather than at a </span> that may not exist.
DESCR_RE = re.compile(r'<span[^>]*class=["\'][^"\']*descrption[^"\']*["\'][^>]*>'
                      r'(.*?)(?:</span>|<span\b[^>]*>|</a>|$)', re.S | re.I)
DATE_RE = re.compile(r'(\d{1,2})\.(\d{1,2})\.')
TIME_RE = re.compile(r'(\d{1,2})[:.](\d{2})')
EUR_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:€|eur\b)', re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))).strip()


def _slug(title):
    """Fallback id for a row with no film page. NFKD rather than a hand-written accent
    table: festival programmes bring accents no fixed table anticipates."""
    s = unicodedata.normalize("NFKD", _txt(title).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")[:60] or "naytos"


def _num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _price(cell_text, breakdown):
    """Display price. Several ticket types -> "alkaen {cheapest}€"."""
    amounts = sorted({float(a.replace(",", "."))
                      for a in EUR_RE.findall(f"{cell_text} {breakdown}")})
    if len(amounts) > 1:
        return f"alkaen {_num(amounts[0])}\u20ac"
    if amounts:
        return f"{_num(amounts[0])}\u20ac"
    return _txt(cell_text)          # "Vapaa pääsy" and anything else non-numeric


def _film(cell_html):
    """Title cell -> (title, blurb, slug). Two shapes, see the module docstring."""
    a = ANCHOR_RE.search(cell_html)
    if not a:
        return _txt(cell_html), "", ""
    attrs, inner = a.group(1), a.group(2)
    d = DESCR_RE.search(inner)
    blurb = _txt(d.group(1)) if d else ""
    ta = TITLE_ATTR_RE.search(attrs)
    # The attribute is the film title on its own. Without it, cut the anchor text at
    # the blurb span rather than flattening the whole cell.
    title = html_mod.unescape(ta.group(1)).strip() if ta else _txt(inner.split("<span")[0])
    href = HREF_RE.search(attrs)
    sm = SLUG_URL_RE.search(href.group(1)) if href else None
    return title, blurb, (sm.group(1) if sm else "")


def _iso(day, month, hh, mm, today=None):
    """The table carries no year: pick the one that keeps the date near today."""
    today = today or datetime.datetime.now(FI).date()
    for year in (today.year, today.year + 1, today.year - 1):
        try:
            d = datetime.date(year, month, day)
        except ValueError:
            continue
        if -45 <= (d - today).days <= 320:
            return datetime.datetime(year, month, day, hh, mm, tzinfo=FI).isoformat()
    return ""


def _cells(row):
    """{class: (attrs, inner_html)} for one <tr>. Cell order is not assumed."""
    out = {}
    for attrs, inner in CELL_RE.findall(row):
        cls = CLASS_RE.search(attrs)
        for name in (cls.group(1).split() if cls else []):
            out.setdefault(name, (attrs, inner))
    return out


def parse(page, today=None):
    shows, heading = [], ""
    for m in BLOCK_RE.finditer(page):
        if m.group("head") is not None:
            heading = _txt(m.group("head"))
            continue
        for row in ROW_RE.findall(m.group("table")):
            cells = _cells(row)
            title, blurb, slug = _film(cells.get("title", ("", ""))[1])
            title, strand = split_strand(title)
            tm = TIME_RE.search(_txt(cells.get("time", ("", ""))[1]))
            # The row's own date cell first; the day heading above the table is the
            # fallback in case that cell is ever dropped from the markup.
            dm = DATE_RE.search(_txt(cells.get("date", ("", ""))[1])) or DATE_RE.search(heading)
            if not title or not tm or not dm:
                continue
            start = _iso(int(dm.group(1)), int(dm.group(2)),
                         int(tm.group(1)), int(tm.group(2)), today)
            if not start:
                continue
            price_attrs, price_html = cells.get("price", ("", ""))
            bd = TITLE_ATTR_RE.search(price_attrs)
            href = HREF_RE.search(cells.get("link", ("", ""))[1])
            shows.append({
                "eventId": slug or _slug(title),
                "title": title,
                "original": "",
                "len": "",
                "rating": "",
                "genres": "",
                "method": strand,
                "theatre": VENUE["name"],
                "aud": "",
                "start": start,
                "url": html_mod.unescape(href.group(1)) if href else URL,
                "img": "",
                "lang": "",
                "soldOut": False,
                "price": _price(_txt(price_html), html_mod.unescape(bd.group(1)) if bd else ""),
                "provider": "orion",
                "venue": VENUE["id"],
                "_syn": blurb,
            })
    shows.sort(key=lambda s: s["start"])
    return shows


def fetch():
    req = urllib.request.Request(
        URL, headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    if "kinola-day" not in page:
        raise RuntimeError("no kinola-day table on the page (markup changed?)")
    return parse(page)


def fetch_site(site=SITES[0]):
    """Runner contract: one page, one screen, keyed by the venue id."""
    return {VENUE["id"]: fetch()}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = parse(open(src, encoding="utf-8", errors="replace").read()) if src else fetch()
    print(f"{len(data)} showtimes, {len({s['eventId'] for s in data})} films")
    for s in data:
        host = re.sub(r"^https?://([^/]+).*", r"\1", s["url"])
        print(f"  {s['start'][:16]}  {s['title'][:38]:40} {s['price']:12} {host}")
