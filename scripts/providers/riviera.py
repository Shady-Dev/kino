"""Riviera Cinemas (Helsinki: Kallio, Punavuori). WordPress admin-ajax, no auth.

  POST /wp/wp-admin/admin-ajax.php
       action=filter_movies&date=&movie=&area=1040&singlemovie=&initial=1
  -> {"success":true,"data":{"movies":"<ul class=movielist>…</ul>"}}

One request returns every showtime for both venues across the whole published window,
so the adapter splits by the `location` field ("Kallio, Sali 1") rather than by request.

Parameterised by base URL: every field the endpoint needs lives on the site dict, so
another cinema on the same WordPress theme (Gilda) is a SITES entry with no new parser.
Confirm the ajax action matches before adding one.
"""
import datetime, html as html_mod, json, re, urllib.parse
from zoneinfo import ZoneInfo

from common import fetch

FI = ZoneInfo("Europe/Helsinki")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SITE = {"provider": "riviera", "label": "Riviera",
        "base": "https://www.rivieracinemas.fi",
        "ajax": "/wp/wp-admin/admin-ajax.php",
        "listing": "/elokuvat/",
        # `area` is ignored by their backend (1040 all / 1024 Kallio / 1039 Punavuori),
        # which is why venues carry a `match` against the location field instead.
        "area": "1040",
        "venues": [
    {"id": "rv-kallio",    "match": "kallio",    "name": "Riviera Kallio",
     "short": "Kallio",    "city": "Helsinki"},
    {"id": "rv-punavuori", "match": "punavuori", "name": "Riviera Punavuori",
     "short": "Punavuori", "city": "Helsinki"},
]}
SITES = [SITE]

ITEM_RE = re.compile(r'<li class="movielist__item single-show[^"]*">(.*?)</li>', re.S)
DATE_RE = re.compile(r'class="date">\s*([^<]+?)\s*<')
TIME_RE = re.compile(r'class="time">\s*(\d{1,2})[:.](\d{2})')
LOC_RE = re.compile(r'class="location">\s*([^<]+?)\s*<')
TITLE_RE = re.compile(r'class="movielist__item__title title">\s*([^<]+?)\s*<')
SEATS_RE = re.compile(r"Varatut paikat:\s*(\d+)\s*/\s*(\d+)")
LEN_RE = re.compile(r"Kesto:\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*min)?")
HREF_RE = re.compile(r'href="([^"]+)"')
DISABLED_RE = re.compile(r"<button[^>]*\bdisabled\b")
TAGS_RE = re.compile(r"<[^>]+>")
# "To 27.8.2026" -> day, month, year
DMY_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


def _txt(x):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", x or ""))).strip()


def parse(page_html, listing=""):
    """-> list of raw showings; venue assignment happens in fetch_site.

    `listing` is the fallback URL for a showing whose block has no absolute href.
    """
    out = []
    for block in ITEM_RE.findall(page_html):
        d = DATE_RE.search(block)
        t = TIME_RE.search(block)
        ti = TITLE_RE.search(block)
        if not (d and t and ti):
            continue
        dmy = DMY_RE.search(d.group(1))
        if not dmy:
            continue
        day, mon, year = (int(x) for x in dmy.groups())
        loc = _txt(LOC_RE.search(block).group(1)) if LOC_RE.search(block) else ""
        venue_name, _, room = loc.partition(",")
        seats = SEATS_RE.search(block)
        taken, total = (int(seats.group(1)), int(seats.group(2))) if seats else (None, None)
        ln = LEN_RE.search(block)
        minutes = ""
        if ln and (ln.group(1) or ln.group(2)):
            minutes = str(int(ln.group(1) or 0) * 60 + int(ln.group(2) or 0))
        href = HREF_RE.search(block)
        out.append({
            "loc": venue_name.strip().lower(),
            "aud": room.strip(),
            "title": _txt(ti.group(1)),
            "start": datetime.datetime(year, mon, day, int(t.group(1)), int(t.group(2)),
                                      tzinfo=FI).isoformat(),
            "len": minutes,
            # A disabled button plus every seat taken is the sold-out signal.
            "soldOut": bool(seats and total and taken >= total) or bool(DISABLED_RE.search(block)),
            "url": (href.group(1) if href and href.group(1).startswith("http")
                    else listing),
        })
    return out


def fetch_site(site=SITE, tries=3):
    base = site["base"].rstrip("/")
    ajax = base + site.get("ajax", "/wp/wp-admin/admin-ajax.php")
    listing = base + site.get("listing", "/elokuvat/")
    body = urllib.parse.urlencode({"action": "filter_movies", "date": "", "movie": "",
                                   "area": site.get("area", "1040"),
                                   "singlemovie": "", "initial": "1"}).encode()
    # POST, so `data` is passed to common.fetch; same tries=3, 5 s * n backoff and 30 s
    # timeout as the loop this replaces. The parse sits outside the retry now.
    payload = json.loads(fetch(ajax, data=body, headers={
        "user-agent": UA, "accept": "application/json, text/javascript, */*",
        "content-type": "application/x-www-form-urlencoded",
        "x-requested-with": "XMLHttpRequest",
        "referer": listing}, tries=tries).decode("utf-8", "replace"))

    rows = parse((payload.get("data") or {}).get("movies") or "", listing)
    per_venue = {v["id"]: [] for v in site["venues"]}
    unmatched = 0
    for r in rows:
        venue = next((v for v in site["venues"] if v["match"] in r["loc"]), None)
        if not venue:
            unmatched += 1
            continue
        per_venue[venue["id"]].append({
            "eventId": "", "title": r["title"], "original": "", "len": r["len"],
            "rating": "", "genres": "", "method": "",
            "theatre": venue["name"], "aud": r["aud"], "start": r["start"],
            "url": r["url"], "img": "", "lang": "", "soldOut": r["soldOut"],
            "price": "", "provider": site["provider"], "venue": venue["id"],
        })
    if unmatched:
        print(f"[{site['provider']}] {unmatched} showtimes with an unrecognised location")
    for k in per_venue:
        per_venue[k].sort(key=lambda s: s["start"])
        for s in per_venue[k]:
            s["eventId"] = re.sub(r"[^\w]+", "-", s["title"].lower()).strip("-")
    return {k: v for k, v in per_venue.items() if v}
