"""Nexxo Scope platform adapter (WordPress plugin used by Finnish cinemas).

One JSON endpoint per site, filtered by locationid:
  GET {base}/wp-content/plugins/nexxo-scope/public_api.php
      ?action=exportdailyshows&locationid=N&days=D&lang=fi&upcoming=0
Response: {"shows": {"YYYY-MM-DD": [ ... ]}}

Adding another Nexxo cinema means adding an entry to SITES, not writing code.
"""
import datetime, json, re, time, urllib.parse
from zoneinfo import ZoneInfo

from common import fetch

FI = ZoneInfo("Europe/Helsinki")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SITES = [
    {"provider": "kinoset", "base": "https://kinoset.fi", "label": "Kinoset",
     "programme": "/ohjelmisto/", "venues": [
         {"id": "ks-huittinen", "locationid": "1", "name": "Kino 1-2",
          "short": "Kino 1-2", "city": "Huittinen"},
         {"id": "ks-loimaa", "locationid": "2", "name": "Kinema",
          "short": "Kinema", "city": "Loimaa"},
         {"id": "ks-sastamala", "locationid": "3", "name": "Bio",
          "short": "Bio", "city": "Sastamala"},
     ]},
]


def api_url(site, locationid, days):
    q = urllib.parse.urlencode({"action": "exportdailyshows", "locationid": locationid,
                                "days": days, "lang": "fi", "upcoming": "0"})
    return f"{site['base']}/wp-content/plugins/nexxo-scope/public_api.php?{q}"


def _codes(v):
    """'FI-SE' / 'FI/SE' -> ['FI','SV']; OV (original version) means unspecified.

    Nexxo writes Swedish as SE, the country code. This app uses the ISO 639-1 language
    code SV, so it is corrected here rather than carried into the data."""
    out = [c for c in re.split(r"[^A-Za-z]+", (v or "").upper()) if c and c != "OV"]
    return ["SV" if c == "SE" else c for c in out]


def _lang(row):
    """code_language / code_subtitles -> Finnkino-style FI-A / FI-S tags."""
    parts = [f"{c}-A" for c in _codes(row.get("code_language"))]
    parts += [f"{c}-S" for c in _codes(row.get("code_subtitles"))]
    return ", ".join(parts)


def _iso(start):
    """'2026-08-26 17:00:00' -> ISO with the correct Helsinki offset (DST-aware)."""
    try:
        naive = datetime.datetime.strptime(start.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ""
    return naive.replace(tzinfo=FI).isoformat()


def parse(payload, site, venue):
    groups = payload.get("shows") or {}
    rows = [r for v in groups.values() for r in v] if isinstance(groups, dict) else list(groups)
    shows = []
    for r in rows:
        iso = _iso(r.get("startTime") or "")
        if not iso or not r.get("startDate"):
            continue                      # upcoming-only entries carry no showtime
        age = str(r.get("ageLimit") or r.get("agelimit") or "").strip()
        poster = (r.get("posterurl") or "").strip()
        price = r.get("priceIncludingTax") or ""
        try:
            price = f"{float(price):.2f}".rstrip("0").rstrip(".") + "€" if float(price) else ""
        except (TypeError, ValueError):
            price = ""
        shows.append({
            "eventId": str(r.get("movieId") or r.get("id") or ""),
            "title": (r.get("movieTitle") or r.get("title") or "?").strip(),
            "original": "",   # code_external_title holds a distributor code, not a title
            "len": str(r.get("duration") or "").strip().lstrip("0") or "",
            "rating": f"K-{age}" if age.isdigit() else age,
            "genres": ", ".join(g.strip().capitalize()
                                for g in (r.get("genre") or "").split(",") if g.strip()),
            "method": (r.get("showTypeTitle") or "").replace("Tavallinen näytös", "").strip(),
            "theatre": venue["name"],
            # roomTitle repeats the venue name at single-screen sites — drop it there.
            "aud": ("" if (r.get("roomTitle") or "").strip() in
                    (venue["name"], venue["short"]) else (r.get("roomTitle") or "").strip()),
            "start": iso,
            "url": f"{site['base']}{site['programme']}?location={venue['locationid']}",
            "img": (f"{site['base']}/wp-content/plugins/nexxo-scope/banners/{poster}"
                    if poster else ""),
            "lang": _lang(r),
            "soldOut": False,
            "price": price,
            "provider": site["provider"],
            "venue": venue["id"],
            "_syn": (r.get("description") or "").strip(),
        })
    shows.sort(key=lambda s: s["start"])
    return shows


def fetch_venue(site, venue, days=21, tries=3):
    """Retry with backoff: the host answers 403 when hit too often in a short window.

    backoff=6 is kept rather than common's 5: this is the one adapter whose retry
    exists to wait out a rate limit rather than a transient fault, so the longer
    gap is the point. Only the request is retried now, not the parse.
    """
    headers = {"user-agent": UA, "accept": "application/json",
               "accept-language": "fi-FI,fi;q=0.9",
               "referer": f"{site['base']}{site['programme']}?location={venue['locationid']}"}
    body = fetch(api_url(site, venue["locationid"], days), headers=headers, cache=True,
                 tries=tries, backoff=6)
    return parse(json.loads(body.decode("utf-8", "replace")), site, venue)


def fetch_site(site, sleep=2.5):
    out = {}
    for v in site["venues"]:
        try:
            out[v["id"]] = fetch_venue(site, v)
            print(f"[{site['provider']}] {v['name']} ({v['city']}): {len(out[v['id']])} showtimes")
        except Exception as e:
            print(f"[{site['provider']}] {v['name']} FAILED: {e}")
        time.sleep(sleep)
    return out
