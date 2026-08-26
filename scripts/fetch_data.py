"""Fetch Finnkino schedule via digital-api (Vista OCAPI) and write JSON into data/."""
import datetime, gzip, json, os, re, sys, time, pathlib
import urllib.request

DIGITAL_API = "https://digital-api.finnkino.fi/WSVistaWebClient/ocapi/v1"
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PAGE_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip",
}
ATTR_RE = re.compile(r"^\dD$|^(IMAX|4DX|Dolby|ScreenX|D-BOX|LUXE|iSense|HFR|Laser|PLF)", re.I)
THEATER_SLUGS = {
    "Cine Atlas Tampere": "finnkino-cine-atlas",
    "Fantasia Jyväskylä": "finnkino-fantasia",
    "Flamingo Vantaa": "finnkino-flamingo",
    "Itis Helsinki": "finnkino-itis",
    "Kinopalatsi Helsinki": "finnkino-kinopalatsi-helsinki",
    "Kinopalatsi Turku": "finnkino-kinopalatsi-turku",
    "Kuvapalatsi Lahti": "finnkino-kuvapalatsi",
    "LUXE Mylly Raisio": "finnkino-luxe-mylly",
    "Maxim Helsinki": "finnkino-maxim",
    "Omena Espoo": "finnkino-omena",
    "Plaza Oulu": "finnkino-plaza",
    "Plevna Tampere": "finnkino-plevna",
    "Promenadi Pori": "finnkino-promenadi",
    "Scala Kuopio": "finnkino-scala",
    "Sello Espoo": "finnkino-sello",
    "Strand Lappeenranta": "finnkino-strand",
    "Tennispalatsi Helsinki": "finnkino-tennispalatsi",
}

def http_get(url, headers, timeout=25):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw

def get_token():
    worker = os.environ.get("TOKEN_WORKER_URL", "").strip()
    if worker:
        data = json.loads(http_get(worker, {"Accept": "application/json", "User-Agent": "kino-fetch/1.0"}))
        tok = (data.get("token") or "").strip()
        if tok:
            print("[token] acquired via CF Worker")
            return tok
        raise RuntimeError(f"worker returned no token: {data}")
    print("[token] TOKEN_WORKER_URL not set, trying direct fetch (local dev)")
    for i, u in enumerate(["https://www.finnkino.fi/",
                           "https://www.finnkino.fi/teatterit/finnkino-tennispalatsi/"], 1):
        try:
            html = http_get(u, PAGE_HEADERS).decode("utf-8", "replace")
            m = JWT_RE.search(html)
            if m:
                print(f"[token] direct from {u}")
                return m.group(0)
        except Exception as e:
            print(f"[token] {u}: {e}")
        time.sleep(1 + i)
    raise RuntimeError("no token available — set TOKEN_WORKER_URL repository variable")

def api(path, token):
    return json.loads(http_get(DIGITAL_API + path, {
        "authorization": f"Bearer {token}",
        "accept": "application/json",
        "user-agent": UA,
        "referer": "https://www.finnkino.fi/",
    }))

def t(obj, *keys):
    for k in keys:
        obj = obj.get(k, {}) if isinstance(obj, dict) else {}
    return obj if isinstance(obj, str) else ""

def main() -> int:
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    token = get_token()

    raw_sites = api("/sites", token)
    raw_sites = raw_sites.get("sites", raw_sites) if isinstance(raw_sites, dict) else raw_sites
    sites = [{"id": str(s["id"]), "name": t(s, "name", "text")} for s in raw_sites
             if s.get("id") and t(s, "name", "text")]
    if not sites:
        print("ERROR: no sites", file=sys.stderr); return 1
    sites.sort(key=lambda s: s["name"])
    (out / "areas.json").write_text(json.dumps({"generated": now, "areas": sites},
                                               ensure_ascii=False), encoding="utf-8")
    print(f"[sites] {len(sites)} cinemas")

    qs = "&".join(f"siteIds={s['id']}" for s in sites)
    per_site = {s["id"]: [] for s in sites}
    today = datetime.date.today()
    for d in range(7):
        date = (today + datetime.timedelta(days=d)).isoformat()
        try:
            data = api(f"/showtimes/by-business-date/{date}?{qs}", token)
        except Exception as e:
            print(f"[schedule] {date} failed: {e}", file=sys.stderr); continue
        rd = data.get("relatedData", {})
        films = {str(f["id"]): f for f in rd.get("films", [])}
        scr = {str(s["id"]): s for s in rd.get("screens", [])}
        rat = {str(r["id"]): r for r in rd.get("censorRatings", [])}
        att = {str(a["id"]): a for a in rd.get("attributes", [])}
        n = 0
        for s in data.get("showtimes", []):
            film = films.get(str(s.get("filmId", "")), {})
            site_id = str(s.get("siteId", ""))
            if site_id not in per_site:
                continue
            attr_names = " · ".join(
                lbl for aid in (s.get("attributeIds") or [])
                if (lbl := (t(att.get(str(aid), {}), "shortName", "text")
                            or t(att.get(str(aid), {}), "name", "text")))
                and ATTR_RE.match(lbl))
            rating_raw = t(rat.get(str(film.get("censorRatingId", "")), {}), "classification", "text")
            m = re.match(r"^\d+", rating_raw)
            rating = f"K-{m.group(0)}" if m else rating_raw
            site_name = next((x["name"] for x in sites if x["id"] == site_id), "")
            slug = THEATER_SLUGS.get(site_name, "")
            runtime = film.get("runTime") or film.get("runtimeInMinutes") or ""
            per_site[site_id].append({
                "eventId": str(s.get("filmId", "")),
                "title": t(film, "title", "text") or "?",
                "original": t(film, "originalTitle", "text"),
                "len": str(runtime) if runtime else "",
                "rating": rating,
                "genres": "",
                "method": attr_names,
                "theatre": site_name,
                "aud": t(scr.get(str(s.get("screenId", "")), {}), "name", "text"),
                "start": t(s.get("schedule", {}) if isinstance(s.get("schedule"), dict) else {}, "startsAt")
                         or (s.get("schedule", {}) or {}).get("startsAt", ""),
                "url": f"https://www.finnkino.fi/teatterit/{slug}/" if slug else "https://www.finnkino.fi/",
                "img": "",
            })
            n += 1
        print(f"[schedule] {date}: {n} showtimes")
        time.sleep(0.4)

    for sid, shows in per_site.items():
        (out / f"area-{sid}.json").write_text(
            json.dumps({"generated": now, "shows": shows}, ensure_ascii=False), encoding="utf-8")
    print("done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
