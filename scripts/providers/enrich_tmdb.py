#!/usr/bin/env python3
"""Add TMDB ratings and trailers to providers that publish neither.

Finnkino gets these via films.json/tmdb.json keyed by its own filmId. The other
providers have no such id, so this pass keys a cache on the normalised title and
writes `tmdb` (rating) and `tr` (trailer URL) straight onto each show.

Idempotent and cache-first: re-runs cost nothing once a title is known. Titles with
no trailer are re-checked once a day, like the Finnkino path.
"""
import datetime, json, os, pathlib, re, sys, time, urllib.parse, urllib.request

DATA = pathlib.Path("data")
CACHE = DATA / "tmdb-titles.json"
SKIP_PREFIXES = ("area-1",)          # Finnkino ids are numeric and already enriched
UA = "kino-enrich/1.0"


def norm(t):
    """Cache key. Keep the whole title: 'Dyyni: Osa kolme' must not collide with 'Dyyni'."""
    t = re.sub(r"[^\w\s]", " ", (t or "").lower().strip(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def queries(title):
    """Full title first, then the part before a dash/colon as a fallback."""
    out = [title]
    head = re.split(r"\s+[-–]\s+|:\s+", title, maxsplit=1)[0].strip()
    if head and head.lower() != title.lower() and len(head) > 3:
        out.append(head)
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
        if isinstance(c, dict) and (c.get("v") or c.get("c") == today):
            continue
        try:
            mid = c.get("i") if isinstance(c, dict) else None
            rating = (c.get("r") or 0) if isinstance(c, dict) else 0
            if not mid:
                for cand in queries(display or k):
                    res = get("https://api.themoviedb.org/3/search/movie?query="
                              + urllib.parse.quote(cand), th)
                    hits = res.get("results") or []
                    if hits:
                        mid = hits[0].get("id")
                        rating = hits[0].get("vote_average") or 0
                        break
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
                        "i": mid or "", "c": today}
            rechecked += 1 if isinstance(c, dict) else 0
            looked += 0 if isinstance(c, dict) else 1
            time.sleep(0.25)
        except Exception as e:
            print(f"[enrich] {display}: {e}")

    CACHE.write_text(json.dumps(cache, ensure_ascii=False))

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
        if changed:
            p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            touched += 1

    hit = sum(1 for c in cache.values() if isinstance(c, dict) and c.get("r"))
    print(f"[enrich] {len(titles)} titles, {looked} new, {rechecked} re-checks, "
          f"{hit} with rating, {touched} files updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
