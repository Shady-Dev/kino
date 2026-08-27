#!/usr/bin/env python3
"""Add TMDB ratings, trailers, synopses and posters to providers that publish none.

Finnkino gets these via films.json/tmdb.json keyed by its own filmId. The other
providers have no such id, so this pass keys a cache on the normalised title and
writes `tmdb` (rating) and `tr` (trailer URL) straight onto each show.

Idempotent and cache-first: re-runs cost nothing once a title is known. Titles with
no trailer are re-checked once a day, like the Finnkino path.
"""
import datetime, json, os, pathlib, re, sys, time, urllib.parse, urllib.request

DATA = pathlib.Path("data")
CACHE = DATA / "tmdb-titles.json"
EXTRA = DATA / "films-extra.json"     # title-keyed synopses for the movie sheet
SKIP_PREFIXES = ("area-1",)          # Finnkino ids are numeric and already enriched
UA = "kino-enrich/1.0"
# Hand-maintained escape hatch for titles TMDB cannot be searched by. See the file's
# own _comment. Lives next to the script, not in data/, because data/ is generated.
ALIAS_FILE = pathlib.Path(__file__).resolve().parent / "tmdb-aliases.json"


def norm(t):
    """Cache key. Keep the whole title: 'Dyyni: Osa kolme' must not collide with 'Dyyni'."""
    t = re.sub(r"[^\w\s]", " ", (t or "").lower().strip(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


# Event prefixes a cinema puts in front of the real title. Exact list, not a pattern:
# "Dyyni: Osa kolme" must keep its head, so anything before a colon cannot be dropped
# blindly. Extend as new arthouse strands appear.
# Also read by orion.py, which splits a matching prefix off the title into `method`
# so the film title stands alone. Add a strand here and both uses get it.
EVENT_PREFIXES = (
    "kesäkino", "kesakino", "vauvakino", "barnsöndagar", "barnsondagar",
    "klassikko", "klassikkosarja", "elokuvakerho", "filmiklubi", "seniorikino",
    "perhekino", "lastenkino", "sunnuntaikino", "ennakkonäytös", "ennakko",
    # Added 2026-08-27 from the first Orion run's no-match list. Festival and strand
    # names, not film titles. "pitchblack playback" and "hopeacine" will still miss
    # TMDB (a music playback night has no entry), but they belong in `method`.
    "espoo ciné", "espoo cine", "pieni elokuvakerho", "pitchblack playback",
    "hopeacine",
)
# Screening-format and re-release noise in brackets, including a bare year.
PAREN_NOISE = re.compile(
    r"\(\s*(?:(?:19|20)\d{2}|suomeksi|dubattu|dub\.?|orig\.?|re-?release"
    r"|uusi\s+kopio|live\s?action|liveaction|2d|3d|imax|4k)\s*\)", re.I)
TRAIL_NOISE = re.compile(r",?\s*\b(?:suomeksi|dubattu)\b\s*$", re.I)


def clean(title):
    """Strip event prefixes and format noise before searching TMDB.

    Only the *search string* is cleaned. norm() keys the cache and films-extra.json on
    the title as the cinema published it, and normTitle() in index.html has to agree
    with that key, so the key itself must never be touched here.
    """
    t = (title or "").strip()
    low = t.lower()
    for pre in EVENT_PREFIXES:
        if low.startswith(pre + ":"):
            t = t[len(pre) + 1:].strip()
            break
    t = TRAIL_NOISE.sub(" ", PAREN_NOISE.sub(" ", t))
    return re.sub(r"\s{2,}", " ", t).strip(" -–:,")


def load_aliases():
    try:
        return {k: v for k, v in json.loads(ALIAS_FILE.read_text()).items()
                if not k.startswith("_")}
    except Exception:
        return {}


def queries(title, alias=None):
    """Cleaned title, then its head before a dash/colon, then the raw title.

    An alias that is not a bare TMDB id goes first. The raw title stays last so a
    wrong cleanup costs an extra request rather than a missing film.
    """
    out = []

    def add(x):
        x = (x or "").strip()
        if len(x) > 2 and x.lower() not in [o.lower() for o in out]:
            out.append(x)

    if alias and not str(alias).isdigit():
        add(str(alias))
    c = clean(title)
    add(c)
    head = re.split(r"\s+[-–]\s+|:\s+", c, maxsplit=1)[0].strip()
    if len(head) > 3:
        add(head)
    add(title)
    return out


def get(url, headers, timeout=25):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main() -> int:
    token = os.environ.get("TMDB_TOKEN", "").strip()
    if not token:
        print("[enrich] no TMDB_TOKEN, skipping")
        return 0
    th = {"Authorization": f"Bearer {token}", "accept": "application/json", "user-agent": UA}
    today = datetime.date.today().isoformat()
    aliases = load_aliases()
    try:
        cache = json.loads(CACHE.read_text())
    except Exception:
        cache = {}

    files = [p for p in sorted(DATA.glob("area-*.json"))
             if not p.name.startswith(SKIP_PREFIXES)]
    titles = {}
    for p in files:
        try:
            doc = json.loads(p.read_text())
        except Exception as e:
            print(f"[enrich] {p.name}: unreadable ({e})")
            continue
        for s in doc.get("shows", []):
            k = norm(s.get("title"))
            if k:
                titles.setdefault(k, s.get("title"))

    looked = rechecked = 0
    for k, display in sorted(titles.items()):
        c = cache.get(k)
        complete = isinstance(c, dict) and ("fi" in c or "en" in c) and "p" in c
        if isinstance(c, dict) and complete and (c.get("v") or c.get("c") == today):
            continue
        try:
            mid = c.get("i") if isinstance(c, dict) else None
            rating = (c.get("r") or 0) if isinstance(c, dict) else 0
            alias = aliases.get(k)
            if not mid and alias and str(alias).isdigit():
                mid = int(alias)          # id given outright, no search needed
            if not mid:
                for cand in queries(display or k, alias):
                    res = get("https://api.themoviedb.org/3/search/movie?query="
                              + urllib.parse.quote(cand), th)
                    hits = res.get("results") or []
                    if hits:
                        mid = hits[0].get("id")
                        rating = hits[0].get("vote_average") or 0
                        poster = hits[0].get("poster_path") or ""
                        break
                    time.sleep(0.2)
            poster = (c.get("p") or "") if isinstance(c, dict) else ""
            syn_fi = syn_en = ""
            if mid:
                # Finnish overview when TMDB has one, English as the fallback.
                for langcode, slot in (("fi-FI", "fi"), ("en-US", "en")):
                    try:
                        d = get(f"https://api.themoviedb.org/3/movie/{mid}?language={langcode}", th)
                        text = (d.get("overview") or "").strip()
                        poster = poster or (d.get("poster_path") or "")
                        if slot == "fi":
                            syn_fi = text
                            if text:
                                break
                        else:
                            syn_en = text
                    except Exception:
                        pass
                    time.sleep(0.2)
            yt = ""
            if mid:
                vids = (get(f"https://api.themoviedb.org/3/movie/{mid}/videos", th)
                        .get("results") or [])
                for pref in (lambda v: v.get("type") == "Trailer" and v.get("official"),
                             lambda v: v.get("type") == "Trailer",
                             lambda v: v.get("type") == "Teaser"):
                    hit = next((v for v in vids if v.get("site") == "YouTube" and pref(v)), None)
                    if hit:
                        yt = hit.get("key") or ""
                        break
            cache[k] = {"r": round(rating, 1) if rating else 0, "v": yt,
                        "i": mid or "", "c": today,
                        "fi": syn_fi, "en": syn_en, "p": poster}
            rechecked += 1 if isinstance(c, dict) else 0
            looked += 0 if isinstance(c, dict) else 1
            time.sleep(0.25)
        except Exception as e:
            print(f"[enrich] {display}: {e}")

    CACHE.write_text(json.dumps(cache, ensure_ascii=False))

    # Synopses live in their own file so area files stay small: one synopsis repeated
    # across 158 showtimes would add roughly 80 kB per venue.
    # Merge: providers write their own (better) Finnish synopses into this file before
    # this pass runs, so never clobber an existing fi text.
    try:
        doc = json.loads(EXTRA.read_text())
    except Exception:
        doc = {}
    films = doc.get("films") or {}
    for k, c in cache.items():
        if not isinstance(c, dict):
            continue
        if not (c.get("fi") or c.get("en") or c.get("v") or c.get("r")):
            continue
        e = films.setdefault(k, {"s": {"fi": "", "en": ""}, "r": 0, "tr": ""})
        e.setdefault("s", {"fi": "", "en": ""})
        if not e["s"].get("fi"):
            e["s"]["fi"] = c.get("fi", "")
        if not e["s"].get("en"):
            e["s"]["en"] = c.get("en", "")
        e["r"] = e.get("r") or c.get("r", 0)
        # w342 is plenty for a 72-110 px tile and keeps the payload small.
        if not e.get("img") and c.get("p"):
            e["img"] = "https://image.tmdb.org/t/p/w342" + c["p"]
        if not e.get("tr") and c.get("v"):
            e["tr"] = "https://www.youtube.com/watch?v=" + c["v"]
    EXTRA.write_text(json.dumps({"generated": today, "films": films}, ensure_ascii=False))

    touched = 0
    for p in files:
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        changed = False
        for s in doc.get("shows", []):
            c = cache.get(norm(s.get("title")))
            if not isinstance(c, dict):
                continue
            if c.get("r") and s.get("tmdb") != c["r"]:
                s["tmdb"] = c["r"]; changed = True
            if c.get("v"):
                url = "https://www.youtube.com/watch?v=" + c["v"]
                if s.get("tr") != url:
                    s["tr"] = url; changed = True
            if not s.get("img") and c.get("p"):
                s["img"] = "https://image.tmdb.org/t/p/w342" + c["p"]; changed = True
        if changed:
            p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            touched += 1

    # Name the titles that found nothing: these are the candidates for tmdb-aliases.json.
    missing = sorted(display for k, display in titles.items()
                     if not (cache.get(k) or {}).get("i"))
    if missing:
        print(f"[enrich] no TMDB match ({len(missing)}): " + " | ".join(missing))

    hit = sum(1 for c in cache.values() if isinstance(c, dict) and c.get("r"))
    syn = sum(1 for c in cache.values() if isinstance(c, dict) and (c.get("fi") or c.get("en")))
    pics = sum(1 for c in cache.values() if isinstance(c, dict) and c.get("p"))
    print(f"[enrich] {len(titles)} titles, {looked} new, {rechecked} re-checks, "
          f"{hit} with rating, {syn} with synopsis, {pics} with poster, "
          f"{touched} files updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
