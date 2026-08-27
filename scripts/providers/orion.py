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

The programme includes third-party events (festivals, HopeaCine, Orion Club), which are
real screenings at this venue and belong in the data. They arrive with prefixes like
"Espoo Ciné:"; that is enrich_tmdb.clean()'s problem, not this adapter's, and the title
is stored exactly as published so norm() keys stay in agreement with the client.

Single screen, so `aud` stays blank. The table has no age limits, runtimes or seat
counts, and there is no per-film page in it, so those fields stay empty and the TMDB
pass fills what it can.
"""
import datetime, html as html_mod, re, sys, urllib.request
from zoneinfo import ZoneInfo

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
TITLE_ATTR_RE = re.compile(r'title=["\']([^"\']*)["\']', re.I)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
DATE_RE = re.compile(r'(\d{1,2})\.(\d{1,2})\.')
TIME_RE = re.compile(r'(\d{1,2})[:.](\d{2})')
EUR_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:€|eur\b)', re.I)
TAGS_RE = re.compile(r"<[^>]+>")
DEACCENT = str.maketrans("äöåÄÖÅéèêüÜçñ", "aoaAOAeeeuUcn")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))).strip()


def _slug(title):
    s = _txt(title).lower().translate(DEACCENT)
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
            title = _txt(cells.get("title", ("", ""))[1])
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
                "eventId": _slug(title),
                "title": title,
                "original": "",
                "len": "",
                "rating": "",
                "genres": "",
                "method": "",
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
