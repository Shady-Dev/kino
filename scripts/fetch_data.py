"""Fetch Finnkino schedule via digital-api (Vista OCAPI) and write JSON into data/."""
import datetime, gzip, json, os, re, sys, time, pathlib
import urllib.request
import urllib.parse

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
# A rating below this many votes is noise, not a verdict. Keep in step with
# enrich_tmdb.MIN_VOTES so the two passes cannot disagree about the same film.
TMDB_MIN_VOTES = 25
# The same hand-written escape hatch enrich_tmdb.py uses, keyed by the normalised
# published title. Until now only the cloud pass could read it, so a Finnkino film TMDB
# cannot be searched by title had no fix at all: "Maailman rikkain nainen" already had
# an alias, which corrected Gilda's row and left Finnkino's blank.
ALIAS_FILE = pathlib.Path(__file__).resolve().parent / "providers" / "tmdb-aliases.json"


def load_aliases():
    try:
        return {k: v for k, v in json.loads(ALIAS_FILE.read_text()).items()
                if not k.startswith("_")}
    except Exception as e:
        print(f"[tmdb] no aliases ({e})")
        return {}


def _tnorm(x):
    """Title comparison key. Must behave like enrich_tmdb.norm()."""
    x = re.sub(r"[^\w\s]", " ", (x or "").lower().strip(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", x).strip()


# Search noise in brackets, and a bare year. Same vocabulary as
# enrich_tmdb.PAREN_NOISE: the two passes must not disagree about the same film.
_Q_NOISE = re.compile(r"\(\s*(?:(?:19|20)\d{2}|suomeksi|dubattu|dub\.?|orig\.?"
                      r"|re-?release|uudelleenjulkaisu|uusi\s+kopio|live\s?action"
                      r"|liveaction|2d|3d|imax|4k)\s*\)", re.I)


def _queries(q):
    """Search candidates, best first. Mirrors enrich_tmdb.queries().

    OCAPI's originalTitle is empty for some releases and the Finnish title is used
    instead, so the query can arrive as "Autot (uudelleenjulkaisu)", which matches
    nothing, or "Mutiny - Lavastettu syylliseksi", whose distributor subtitle stops the
    exact-title rule from firing on a hit that is in fact the right film.
    """
    out = []

    def add(x):
        x = (x or "").strip(" -–:,")
        if len(x) > 2 and x.lower() not in [o.lower() for o in out]:
            out.append(x)

    add(re.sub(r"\s{2,}", " ", _Q_NOISE.sub(" ", q or "")))
    add(q)
    # Dash only, never a colon. A Finnish distributor subtitle is appended with a dash
    # ("Mutiny - Lavastettu syylliseksi"), while a colon usually carries the franchise:
    # splitting "Mission: Impossible - Dead Reckoning" would search "Mission", and an
    # exact hit on that now earns a tmdbId and would merge two different films.
    head = re.split(r"\s+[-–]\s+", _Q_NOISE.sub(" ", q or ""), maxsplit=1)[0]
    add(head)
    return out


def _pick(results, query):
    """Choose a search hit. -> (hit, exact).

    TMDB search sorts by popularity, so results[0] on a short title is whatever is
    trending. Prefer a hit whose title or original title matches the query exactly and
    fall back to the popularity order only when nothing does.
    """
    if not results:
        return None, False
    q = _tnorm(query)
    for h in results:
        if _tnorm(h.get("title")) == q or _tnorm(h.get("original_title")) == q:
            return h, True
    return results[0], False
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
    tok = os.environ.get("FINNKINO_TOKEN", "").strip()
    if tok:
        print("[token] using FINNKINO_TOKEN variable")
        return tok
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

def loc(obj):
    """Vista text object -> {'fi': ..., 'en': ...}"""
    if not isinstance(obj, dict):
        return {"fi": "", "en": ""}
    fi = obj.get("text") or ""
    en = ""
    for tr in obj.get("translations") or []:
        if str(tr.get("languageTag", "")).lower().startswith("en"):
            en = tr.get("text") or ""
            break
    return {"fi": fi, "en": en}

def t(obj, *keys):
    for k in keys:
        obj = obj.get(k, {}) if isinstance(obj, dict) else {}
    return obj if isinstance(obj, str) else ""

POSTER_DIR = pathlib.Path("data/posters")
_poster_cache = {}

def download_poster(rid: str) -> str:
    """Download poster once per release id; return relative path or ''. """
    if rid in _poster_cache:
        return _poster_cache[rid]
    POSTER_DIR.mkdir(parents=True, exist_ok=True)
    rel = f"data/posters/{rid}.jpg"
    p = pathlib.Path(rel)
    if not p.exists():
        url = f"https://film-cdn.moviexchange.com/api/cdn/release/{rid}/media/Poster?width=200"
        try:
            raw = http_get(url, {"user-agent": UA, "referer": "https://www.finnkino.fi/",
                                 "accept": "image/*"})
            if len(raw) > 500:
                p.write_bytes(raw)
            else:
                raise RuntimeError("too small")
        except Exception as e:
            print(f"[poster] {rid}: {e}")
            _poster_cache[rid] = ""
            return ""
    _poster_cache[rid] = rel
    return rel

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
    unknown_attrs = set()
    films_meta = {}
    films_full = {}
    today = datetime.date.today()
    for d in range(7):
        date = (today + datetime.timedelta(days=d)).isoformat()
        try:
            data = api(f"/showtimes/by-business-date/{date}?{qs}", token)
        except Exception as e:
            print(f"[schedule] {date} failed: {e}", file=sys.stderr); continue
        rd = data.get("relatedData", {})
        films = {str(f["id"]): f for f in rd.get("films", [])}
        genmap = {str(g["id"]): t(g, "name", "text") for g in rd.get("genres", [])}
        scr = {str(s["id"]): s for s in rd.get("screens", [])}
        rat = {str(r["id"]): r for r in rd.get("censorRatings", [])}
        att = {str(a["id"]): a for a in rd.get("attributes", [])}
        n = 0
        for s in data.get("showtimes", []):
            film = films.get(str(s.get("filmId", "")), {})
            site_id = str(s.get("siteId", ""))
            if site_id not in per_site:
                continue
            fmt_list, lang_list = [], []
            for aid in (s.get("attributeIds") or []):
                a = att.get(str(aid), {})
                lbl = t(a, "shortName", "text") or t(a, "name", "text")
                if not lbl:
                    continue
                if ATTR_RE.match(lbl):
                    fmt_list.append(lbl)
                elif re.match(r"^\.?[A-Z]{2}(?:-[A-Z]{2})?-(?:A|S)$", lbl):
                    lang_list.append(lbl.lstrip("."))
                else:
                    # Anything not a format and not a language code is dropped. That is
                    # fine for marketing labels, but a screening-level age limit (a
                    # licensed bar auditorium is 18+ whatever the film is rated, which
                    # BioRex publishes as "Anniskelu") would be lost silently. Collect
                    # the names once so a run says what is actually on offer here.
                    unknown_attrs.add(lbl)
            attr_names = " · ".join(fmt_list)
            lang_attr = ", ".join(lang_list)
            rating_raw = t(rat.get(str(film.get("censorRatingId", "")), {}), "classification", "text")
            m = re.match(r"^\d+", rating_raw)
            rating = f"K-{m.group(0)}" if m else rating_raw
            site_name = next((x["name"] for x in sites if x["id"] == site_id), "")
            slug = THEATER_SLUGS.get(site_name, "")
            fid = str(s.get("filmId", ""))
            if fid and fid not in films_meta:
                films_meta[fid] = {"q": t(film, "originalTitle", "text") or t(film, "title", "text"),
                                   "fi": t(film, "title", "text"),
                                   "y": (film.get("releaseDate") or "")[:4]}
                trs = film.get("trailers") or []
                tr_uri = ""
                if trs and isinstance(trs[0], dict):
                    tr_uri = trs[0].get("uri") or trs[0].get("url") or ""
                syn = film.get("synopsis") or film.get("shortSynopsis") or {}
                films_full[fid] = {
                    "t": loc(film.get("title")),
                    "o": t(film, "originalTitle", "text"),
                    "s": loc(syn),
                    "tr": tr_uri,
                    "y": films_meta[fid]["y"],
                }
            runtime = film.get("runtimeInMinutes") or film.get("runTime") or ""
            rid = (film.get("externalIds") or {}).get("moviexchangeReleaseId") or ""
            img = download_poster(rid) if rid else ""
            genres = ", ".join(filter(None, (genmap.get(str(gid), "")
                               for gid in (film.get("genreIds") or []))))
            per_site[site_id].append({
                "eventId": str(s.get("filmId", "")),
                "title": t(film, "title", "text") or "?",
                "original": t(film, "originalTitle", "text"),
                "len": str(runtime) if runtime else "",
                "rating": rating,
                "genres": genres,
                "method": attr_names,
                "theatre": site_name,
                "aud": t(scr.get(str(s.get("screenId", "")), {}), "name", "text"),
                "start": t(s.get("schedule", {}) if isinstance(s.get("schedule"), dict) else {}, "startsAt")
                         or (s.get("schedule", {}) or {}).get("startsAt", ""),
                "url": (f"https://www.finnkino.fi/liput/valitse-paikat/?showtimeId={s.get('id')}"
                        if s.get("id") else
                        (f"https://www.finnkino.fi/teatterit/{slug}/" if slug else "https://www.finnkino.fi/")),
                "img": img,
                "lang": lang_attr,
                "soldOut": bool(s.get("isSoldOut")),
            })
            n += 1
        print(f"[schedule] {date}: {n} showtimes")
        time.sleep(0.4)

    tmdb_token = os.environ.get("TMDB_TOKEN", "").strip()
    if tmdb_token:
        cache_p = out / "tmdb.json"
        try:
            tmdb_cache = json.loads(cache_p.read_text())
        except Exception:
            tmdb_cache = {}
        th = {"Authorization": f"Bearer {tmdb_token}", "accept": "application/json",
              "user-agent": "kino-fetch/1.0"}
        # An entry with no "x" was matched before the exact-title rule existed and its
        # id cannot be re-judged after the fact, so drop it and search again. One-off.
        stale = [k for k, v in tmdb_cache.items()
                 if not (isinstance(v, dict) and "x" in v)]
        for k in stale:
            del tmdb_cache[k]
        if stale:
            print(f"[tmdb] dropped {len(stale)} entries matched by the old picker")
        aliases = load_aliases()
        looked = rechecked = 0
        tmdb_weak, tmdb_thin = [], []
        today = datetime.date.today().isoformat()
        for fid, meta in films_meta.items():
            if not meta["q"]:
                continue
            cached = tmdb_cache.get(fid)
            cached = cached if isinstance(cached, dict) else None
            # Skip only if we already have a trailer, or we already re-checked today.
            if (cached and "n" in cached and "x" in cached
                    and (cached.get("v") or cached.get("c") == today)):
                continue
            try:
                mid = cached.get("i") if cached else None
                va = (cached.get("r") or 0) if cached else 0
                votes = (cached.get("n") or 0) if cached else 0
                exact_id = bool(cached.get("x")) if cached else False
                # An alias is either a bare TMDB id, which skips the search, or a
                # replacement search string. Keyed on the Finnish title first, since
                # that is what the cinema publishes and what the file is keyed by.
                alias = aliases.get(_tnorm(meta.get("fi"))) or aliases.get(_tnorm(meta["q"]))
                if not mid and alias and str(alias).isdigit():
                    mid = int(alias)
                    exact_id = True     # a hand-written id is as good as exact
                    va = votes = 0      # rating comes from the detail call below
                if not mid:
                    # Every candidate is tried until one matches the title exactly; the
                    # first hit of any kind is the fallback. Stopping at the first
                    # candidate that returns anything is what sent "Die Hard 2 - Die
                    # Harder" to Die Hard in the cloud pass.
                    fallback = None
                    cands = _queries(meta["q"])
                    if alias and not str(alias).isdigit():
                        cands.insert(0, str(alias))
                    for cand in cands:
                        q = urllib.parse.quote(cand)
                        u = f"https://api.themoviedb.org/3/search/movie?query={q}"
                        res = json.loads(http_get(
                            u + (f"&primary_release_year={meta['y']}" if meta["y"] else ""), th))
                        results = res.get("results") or []
                        # A reissue carries the reissue year, so the year filter has to
                        # be droppable: Autot is a 2026 release of a 2006 film.
                        if not results and meta["y"]:
                            results = json.loads(http_get(u, th)).get("results") or []
                        hit, exact = _pick(results, cand)
                        if hit and exact:
                            mid = hit.get("id")
                            va = hit.get("vote_average") or 0
                            votes = hit.get("vote_count") or 0
                            exact_id = True
                            break
                        if hit and fallback is None:
                            fallback = hit
                        time.sleep(0.2)
                    else:
                        if fallback is not None:
                            mid = fallback.get("id")
                            va = fallback.get("vote_average") or 0
                            votes = fallback.get("vote_count") or 0
                            exact_id = False
                            tmdb_weak.append(f"{meta['q']} -> {fallback.get('title')}")
                # An id that did not come from a search carries no vote data with it
                # (an alias id, or one restored from cache before "n" existed), and this
                # pass otherwise never fetches the movie detail. One request, only in
                # that case, keeps the rating and the vote floor working.
                if mid and not votes:
                    try:
                        d = json.loads(http_get(
                            f"https://api.themoviedb.org/3/movie/{mid}", th))
                        va = d.get("vote_average") or 0
                        votes = d.get("vote_count") or 0
                    except Exception as e:
                        print(f"[tmdb-detail] {meta['q']}: {e}")
                yt = ""
                if mid:
                    try:
                        vids = json.loads(http_get(
                            f"https://api.themoviedb.org/3/movie/{mid}/videos", th)).get("results") or []
                        for pref in (lambda v: v.get("type") == "Trailer" and v.get("official"),
                                     lambda v: v.get("type") == "Trailer",
                                     lambda v: v.get("type") == "Teaser"):
                            hit = next((v for v in vids if v.get("site") == "YouTube" and pref(v)), None)
                            if hit:
                                yt = hit.get("key") or ""
                                break
                    except Exception as e:
                        print(f"[tmdb-videos] {meta['q']}: {e}")
                # A rating needs votes: a premiere with three of them shows a clean
                # 10.0, which reads as a verdict. Same floor as enrich_tmdb.
                shown = round(va, 1) if va and votes >= TMDB_MIN_VOTES else 0
                if va and not shown:
                    tmdb_thin.append(f"{meta['q']} ({round(va, 1)} / {votes} votes)")
                tmdb_cache[fid] = {"r": shown, "n": votes, "v": yt,
                                   "x": bool(mid) and exact_id,
                                   "i": mid or "", "c": today}
                if cached:
                    rechecked += 1
                else:
                    looked += 1
                time.sleep(0.25)
            except Exception as e:
                print(f"[tmdb] {meta['q']}: {e}")
        cache_p.write_text(json.dumps(tmdb_cache))
        if tmdb_weak:
            print(f"[tmdb] weak match, no exact title ({len(tmdb_weak)}): "
                  + " | ".join(sorted(tmdb_weak)))
        if tmdb_thin:
            print(f"[tmdb] rating held back, under {TMDB_MIN_VOTES} votes "
                  f"({len(tmdb_thin)}): " + " | ".join(sorted(tmdb_thin)))
        mergeable = sum(1 for c in tmdb_cache.values()
                        if isinstance(c, dict) and c.get("x") and c.get("i"))
        print(f"[tmdb] {looked} new lookups, {rechecked} re-checks, "
              f"cache {len(tmdb_cache)}, {mergeable} mergeable by id")
        def _rating(c):
            return (c.get("r") if isinstance(c, dict) else c) or 0
        for shows in per_site.values():
            for sh in shows:
                c = tmdb_cache.get(sh["eventId"])
                v = _rating(c)
                if v:
                    sh["tmdb"] = v
                # Cross-chain film identity for the combined city view. Exact matches
                # only: a weak id would merge two different films into one row.
                if isinstance(c, dict) and c.get("x") and c.get("i"):
                    sh["tmdbId"] = c["i"]
        for fid, entry in films_full.items():
            c = tmdb_cache.get(fid)
            if isinstance(c, dict) and c.get("v"):
                entry["tr"] = "https://www.youtube.com/watch?v=" + c["v"]

    (out / "films.json").write_text(
        json.dumps({"generated": now, "films": films_full}, ensure_ascii=False), encoding="utf-8")
    print(f"[films] {len(films_full)} film entries")
    if unknown_attrs:
        print(f"[attrs] dropped, neither format nor language ({len(unknown_attrs)}): "
              + " | ".join(sorted(unknown_attrs)))

    written = kept = 0
    for sid, shows in per_site.items():
        path = out / f"area-{sid}.json"
        # A partial OCAPI response must not blank 17 venues, so an empty result keeps
        # whatever is already committed (same rule as run.py for every other provider).
        # A venue with no file yet still gets one: areas.json lists every site
        # regardless of shows, so the picker would otherwise link to a 404.
        if not shows and path.exists():
            print(f"[schedule] {sid}: no shows, keeping previous file", file=sys.stderr)
            kept += 1
            continue
        # Dates actually present, so the UI can tell "no shows" apart from
        # "schedule not published yet" instead of showing one message for both.
        day_list = sorted({s["start"][:10] for s in shows if s.get("start")})
        path.write_text(
            json.dumps({"generated": now, "dates": day_list,
                        "horizon": day_list[-1] if day_list else "",
                        "shows": shows}, ensure_ascii=False), encoding="utf-8")
        written += 1
    print(f"[schedule] {written} venue files written, {kept} kept as-is")
    print("done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
