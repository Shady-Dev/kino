"""Cinema Orion (Helsinki, Eerikinkatu 15, run by ELKE ry): front page table. Stdlib only.

Everything is server-rendered on one page: a `<table class="kinola-day">` per day, one
`<tr>` per screening with date, time, title, price and the ticket link. One request.

  * Ticket URLs come from the markup, never built, but they are resolved against the
    site before they are stored. The site published absolute orion.kinola.ee links until
    2026-09-06 and now publishes site-relative ones (`/checkout/{uuid}`); a bare path
    reaches the client as a bare path, and the browser resolves it against leffavuoro.fi,
    which answers 404. urljoin leaves an absolute link alone, so festival screenings
    keep pointing at the festival's own box office (Espoo Ciné ->
    boxoffice.espoocine.fi). A row with no link (free admission) falls back to the
    programme page.
  * The price cell's `title` attribute carries the ticket-type breakdown, so a screening
    with cheaper types reads "alkaen 8.5€".

The title cell has two shapes:

    <td class='title'> Espoo Ciné: Four Minus Three </td>
    <td class='title'><a href='/elokuvat/{slug}/' title ="Film"> Film
      <span class="descrption">Finnish blurb<span> </a></td>

In the linked shape the title is read from the anchor's `title` attribute, not the cell
text, which would glue the blurb onto the title and split one film into one "film" per
blurb. `descrption` is the site's spelling and its inner `<span>` is never closed. The
blurb goes to `_syn`; synmerge only fills an empty slot.

`eventId` is the film page slug where there is one; festival rows fall back to a slug of
the title. A known event prefix ("Espoo Ciné:", "Pieni elokuvakerho:") is split off into
`method` from the shared list in `strands.py`, matched exactly, never as a colon pattern.
Third-party events (festivals, HopeaCine, Orion Club) are real screenings here and stay
in the data with the title stored exactly as published, so norm() keys agree with the
client.

Single screen, so `aud` stays blank. No age limits, runtimes or seat counts in the table;
the TMDB pass fills what it can.
"""
import datetime, html as html_mod, re, sys, unicodedata
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from common import fetch
from strands import split as split_strand

URL = "https://cinemaorion.fi/"
FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

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


def _ticket(href):
    """The row's ticket link, resolved against the site. See the module docstring: the
    site moved to site-relative paths, and a bare path stored here becomes a leffavuoro.fi
    link in the client, because safeUrl passes a scheme-less URL through. An absolute
    href, including a festival's own box office, comes back unchanged."""
    return urljoin(URL, href) if href else URL


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
                "url": _ticket(html_mod.unescape(href.group(1)) if href else ""),
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


def fetch_page():
    page = fetch(URL, cache=True,
                 headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"}
                 ).decode("utf-8", "replace")
    if "kinola-day" not in page:
        raise RuntimeError("no kinola-day table on the page (markup changed?)")
    return parse(page)


def fetch_site(site=SITES[0]):
    """Runner contract: one page, one screen, keyed by the venue id."""
    return {VENUE["id"]: fetch_page()}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = parse(open(src, encoding="utf-8", errors="replace").read()) if src else fetch_page()
    print(f"{len(data)} showtimes, {len({s['eventId'] for s in data})} films")
    for s in data:
        host = re.sub(r"^https?://([^/]+).*", r"\1", s["url"])
        print(f"  {s['start'][:16]}  {s['title'][:38]:40} {s['price']:12} {host}")
