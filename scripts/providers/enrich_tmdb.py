#!/usr/bin/env python3
"""Add TMDB ratings, trailers, synopses and posters to providers that publish none.

Finnkino gets these via films.json/tmdb.json keyed by its own filmId. The other
providers have no such id, so this pass keys a cache on the normalised title and
writes `tmdb` (rating) and `tr` (trailer URL) straight onto each show.

Idempotent and cache-first: a re-run is cheap once a title is known. Titles with no
trailer are re-checked once a day, looking for one; a cached rating is re-read once it is
a week old, oldest first and a bounded number a run. See `due()`.
"""
import datetime, json, os, pathlib, re, sys, time, urllib.parse, urllib.request

import common

DATA = pathlib.Path("data")
CACHE = DATA / "tmdb-titles.json"
# id -> localized name, one map per language. TMDB's Finnish names are real translations
# (18 of 19 differ from English, probed 2026-08-27), so the client can render genres in
# either language from ids alone -- which also fixes English mode showing Finnish genres.
GENRES = DATA / "tmdb-genres.json"
EXTRA = DATA / "films-extra.json"     # title-keyed synopses for the movie sheet
SKIP_PREFIXES = ("area-1",)          # Finnkino ids are numeric and already enriched

# TMDB's genre lists are community-translated and two entries are not translated at all:
# id 10402 comes back as "Music" under sv-SE and id 10770 as "TV Movie" under fi-FI.
# Checked against the whole committed map on 2026-08-30 rather than assumed -- the five
# other Swedish names identical to English (Action, Drama, Fantasy, Science Fiction,
# Thriller) are correct Swedish and are left alone. 10402 is live: 107 showtimes across
# 9 films carry it today, so a Swedish reader sees one English word among Swedish ones.
# 10770 appears on nothing today and is fixed anyway, because the mechanism is the same
# on the day it does. Applied to the response rather than hand-edited into
# data/tmdb-genres.json, which the next run would overwrite.
GENRE_FIX = {"sv": {"10402": "Musik"}, "fi": {"10770": "TV-elokuva"}}
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"
# Hand-maintained escape hatch for titles TMDB cannot be searched by. See the file's
# own _comment. Lives next to the script, not in data/, because data/ is generated.
ALIAS_FILE = pathlib.Path(__file__).resolve().parent / "tmdb-aliases.json"


def norm(t):
    r"""Cache key. Keep the whole title: 'Dyyni: Osa kolme' must not collide with 'Dyyni'.

    `_` is stripped explicitly: Python's \w includes it, the client's \p{L}\p{N} does
    not, so leaving it in would key an underscored title differently here and there.
    """
    t = re.sub(r"[^\w\s]|_", " ", (t or "").lower().strip(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


# The strand list lives in strands.py: one list, used both for the TMDB search here
# and for splitting the prefix off published titles in run.py and fetch_data.py.
from strands import EVENT_PREFIXES  # noqa: E402

# Screening-format and re-release noise in brackets, including a bare year.
PAREN_NOISE = re.compile(
    r"\(\s*(?:(?:19|20)\d{2}|suomeksi|dubattu|dub\.?|orig\.?|re-?release"
    r"|uudelleenjulkaisu|uusi\s+kopio|live\s?action|liveaction|2d|3d|imax|4k)\s*\)", re.I)
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


# A rating is only worth showing once enough people have voted. A festival premiere
# with three votes gives a clean 10.0 or 5.0, which reads as a verdict and is noise.
MIN_VOTES = 25


# How long a cached rating is allowed to stand, and how many stale ones one pass will
# re-read.
#
# Finding a trailer used to end an entry's life: the skip was `c.get("v") or c.get("c")
# == today`, so a film with a trailer was never looked at again and its rating and vote
# count froze at whatever they were the day the trailer turned up. Measured against the
# committed cache on 2026-09-01: 154 entries, 94 of them with a trailer, and 71 of those
# 94 had not been re-read since 2026-08-27 -- five days, with nothing in the code that
# would ever read them again. A vote count moves fastest in the weeks after release,
# which is exactly when a film is in these cinemas.
#
# So age decides, not the presence of a trailer. The budget is what stops that becoming a
# re-fetch of everything: without it the first run after this change re-reads all 71 at
# once, stamps them all with the same date, and they all come due together again a week
# later, for ever. In the steady state the ceiling is not reached -- 96 entries at a
# seven-day age come due at about fourteen a day, which is roughly two per run -- so it
# is a bound on the catch-up rather than a running cost.
#
# Which of the backlog a run takes is decided by `a`, when a refresh was last *attempted*,
# and not by `c`, when one last succeeded. Ordering on `c` alone starves the queue: an id
# that can never be read keeps `c` where it is, ages further every day and so outranks
# everything else for ever, and a dozen of those would spend the whole budget on every
# run while the rest of the backlog never moved. Least recently attempted goes first, an
# entry never attempted ahead of all of them, so the budget rotates.
#
# `a` is deliberately not part of is_complete(): it is this pass's own bookkeeping rather
# than anything the client reads, and requiring it would cost a full re-check pass to
# introduce for no gain.
RATING_MAX_AGE = int(os.environ.get("KINO_TMDB_MAX_AGE") or 7)
REFRESH_BUDGET = int(os.environ.get("KINO_TMDB_REFRESH") or 12)


def _numeric(v):
    """A usable number from a TMDB field. -> the value, or None.

    Zero is a value: a film nobody has voted on comes back with `vote_count` 0 and
    `vote_average` 0.0, and reading that is a successful read. Absent, null or a string
    is not, and must not become a zero written over a rating that was real.
    """
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def is_complete(c):
    """Every field the current cache shape writes is present. -> bool.

    A missing field means incomplete rather than wrong, so adding one -- "n" arrived with
    the MIN_VOTES gate -- costs a single re-check pass instead of a cache wipe.
    """
    return (isinstance(c, dict) and ("fi" in c or "en" in c)
            and "p" in c and "n" in c and "x" in c and "g" in c)


def age_days(entry, today, field="c"):
    """Days since one of this entry's dates. -> int, or None if there is not one.

    `c` is when TMDB last answered with rating and vote data, `a` when a refresh was last
    attempted. None is not zero in either case: an entry with no `c` was written by a
    shape this code no longer produces and is the oldest thing there is, and an entry
    with no `a` has never been attempted, which puts it at the head of the queue.
    """
    try:
        return (datetime.date.fromisoformat(today)
                - datetime.date.fromisoformat(entry.get(field) or "")).days
    except (TypeError, ValueError):
        return None


def due(titles, cache, today, max_age=None, budget=None):
    """Which titles this pass fetches. -> (keys, refreshes, deferred).

    `refreshes` is the subset being re-read only because their rating is old, handed back
    as keys rather than a count so the caller can report what actually became of each --
    a scheduled refresh whose detail request fails is not a refreshed rating. `deferred`
    counts the ones that were also due and did not fit the budget, so the caller can say
    so rather than trimming silently.

    Four states:

      * not in the cache -- fetched, obviously.
      * cached in an older shape, missing a field -- fetched, so a gate change costs one
        pass rather than a wipe.
      * complete with no trailer -- once a day, looking for a trailer that may not have
        existed when the film opened. Unchanged.
      * complete with a trailer -- used to be skipped for ever. Re-read once `c` is
        `max_age` days old, at most `budget` of them a run, least recently *attempted*
        first so that an id which never reads cannot hold the queue. See RATING_MAX_AGE.
    """
    max_age = RATING_MAX_AGE if max_age is None else max_age
    budget = REFRESH_BUDGET if budget is None else budget
    work, stale = set(), []
    for k in titles:
        c = cache.get(k)
        if not is_complete(c):
            work.add(k)
            continue
        age = age_days(c, today)
        if not c.get("v"):
            # Read today already is the only reason to skip, exactly as before.
            if age != 0:
                work.add(k)
            continue
        if age is None or age >= max_age:
            stale.append((age, age_days(c, today, "a"), k))
    # Never attempted first, then longest since the last attempt, then oldest data, then
    # the key -- so the choice is the same on every machine and a test can name it.
    stale.sort(key=lambda p: (0 if p[1] is None else 1, -(p[1] or 0),
                              0 if p[0] is None else 1, -(p[0] or 0), p[2]))
    refresh = {k for _, _, k in stale[:budget]}
    return work | refresh, refresh, len(stale) - len(refresh)


def pick(hits, query):
    """Choose a search hit. -> (hit, exact).

    TMDB sorts by popularity, so hits[0] on a one-word title is whatever is trending:
    "Mother" came back as "Mother Mary". Prefer a hit whose title or original title
    matches the query exactly, and fall back to the popularity order only when nothing
    does — a Finnish distributor title often matches nothing, and a weak match still
    beats no film. The fallbacks are logged so they can be checked.

    Searched with `language=fi-FI` so `title` comes back as the **Finnish** title TMDB
    has registered. Without it TMDB answers in English and the comparison fails on every
    Finnish distributor title: "Autofiktio" vs "Bitter Christmas", "Kuopus" vs "The
    Little Sister", "Kummisetä osa II" vs "The Godfather Part II". All three ids were
    right all along and were being written off as weak matches, which cost them their
    `tmdbId` and their genre ids. `language` localizes the response; it does not widen
    which titles are searched, so this is presentation, not matching.
    """
    q = norm(query)
    for h in hits:
        if norm(h.get("title")) == q or norm(h.get("original_title")) == q:
            return h, True
    return hits[0], False


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


# Write the cache to disk every FLUSH_EVERY titles as well as at the end. The
# per-title body catches its own exceptions, but anything raised outside it -- the
# genre-list calls, the area-file write pass, a killed runner -- used to leave the
# single end-of-run write unreached and threw away every lookup of the run: ~300
# TMDB requests on a cold cache, spent again on the next one. The writes are atomic
# and the cache is idempotent, so a partial one is just a warmer start next time.
FLUSH_EVERY = 25


def merge_extra(cache, today):
    """Fold cached text/ratings/posters into films-extra.json.

    Synopses live in their own file so area files stay small: one synopsis repeated
    across 158 showtimes would add roughly 80 kB per venue. Providers write their own
    (better) Finnish synopses into this file before this pass runs, so an existing fi
    text is never clobbered. Re-reading the file per flush keeps that rule true even
    if a provider wrote to it in between.
    """
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
    common.write_json(EXTRA, {"generated": today, "films": films})


def flush(cache, today):
    common.write_json(CACHE, cache)
    merge_extra(cache, today)


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
    # An entry with no "x" was matched by the old loop, which stopped at the first
    # candidate that returned anything. Its id cannot be re-judged after the fact, so
    # drop it and let the fixed loop search again. One-off per shape change.
    # A weak entry judged before the fi-FI search change compared a Finnish title
    # against an English one, so every one of them has to be re-judged once.
    stale = [k for k, v in cache.items()
             if not (isinstance(v, dict) and "x" in v)
             or (isinstance(v, dict) and v.get("i") and not v.get("x"))]
    for k in stale:
        del cache[k]
    if stale:
        print(f"[enrich] dropped {len(stale)} entries matched by the old picker")
    # Adding an alias has to be able to correct a film that already resolved wrongly.
    # A complete entry is skipped outright, so an alias written for a weak match would
    # never be consulted: "autot re release" kept pointing at Cars 3 with an alias for
    # Cars sitting in the file. An alias plus a non-exact entry means the entry is the
    # thing the alias exists to replace.
    overridden = [k for k, v in cache.items()
                  if aliases.get(k) and not (isinstance(v, dict) and v.get("x"))]
    for k in overridden:
        del cache[k]
    if overridden:
        print(f"[enrich] dropped {len(overridden)} weak entries that now have an alias: "
              + " | ".join(sorted(overridden)))

    # One request per UI language per run, not per film. Written for the client to render
    # genre names in whichever language it is showing; ids on a show mean nothing without
    # it. Swedish joined on 2026-08-29 with the third UI language -- without it a Swedish
    # reader got the provider's own Finnish genre string, which is the gap English had.
    names = {}
    for lang, slot in (("fi-FI", "fi"), ("sv-SE", "sv"), ("en-US", "en")):
        try:
            g = get(f"https://api.themoviedb.org/3/genre/movie/list?language={lang}", th)
            names[slot] = {str(x["id"]): x["name"] for x in (g.get("genres") or [])}
            # Only rename an id TMDB actually returned, so this can never invent a genre.
            names[slot].update({k: v for k, v in GENRE_FIX.get(slot, {}).items()
                                if k in names[slot]})
        except Exception as e:
            print(f"[enrich] genre list {lang}: {e}")
    # fi and en are the bar, as before. Swedish is written when it arrives and omitted
    # when it does not: the client falls through to the provider's own genre string for a
    # language it has no map for, so a missing slot degrades to what that language showed
    # yesterday. Requiring all three would have let a Swedish outage delete the Finnish
    # and English maps too, which is a worse failure than the one it guards against.
    missing = [k for k in ("fi", "sv", "en") if not names.get(k)]
    if missing:
        print(f"[enrich] genre names missing for: {', '.join(missing)}")
    if names.get("fi") and names.get("en"):
        body = json.dumps(names, ensure_ascii=False, indent=1) + "\n"
        if not GENRES.exists() or GENRES.read_text(encoding="utf-8") != body:
            common.write_text_atomic(GENRES, body)
            print(f"[enrich] genre names written ({len(names['fi'])} genres, "
                  f"{'+'.join(sorted(names))})")

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

    todo, refreshes, deferred = due(titles, cache, today)
    settled = set()          # scheduled refreshes that came back with rating/vote data
    looked = rechecked = pending = 0
    weak, thin = [], []      # popularity fallbacks, and ratings held back by MIN_VOTES
    for k, display in sorted(titles.items()):
        if k not in todo:
            continue
        c = cache.get(k)
        replaced = False
        try:
            mid = c.get("i") if isinstance(c, dict) else None
            rating = (c.get("r") or 0) if isinstance(c, dict) else 0
            votes = (c.get("n") or 0) if isinstance(c, dict) else 0
            exact_id = bool(c.get("x")) if isinstance(c, dict) else False
            gids = (c.get("g") or []) if isinstance(c, dict) else []
            poster = (c.get("p") or "") if isinstance(c, dict) else ""
            alias = aliases.get(k)
            if not mid and alias and str(alias).isdigit():
                mid = int(alias)          # id given outright, no search needed
                exact_id = True           # a hand-written id is as good as exact
            if not mid:
                # Do not stop at the first candidate that returns anything: candidate 1
                # ("Die Hard 2 - Die Harder") returns hits, so the loop used to break
                # there and never try candidate 2 ("Die Hard 2"), which matches exactly.
                # Keep going until a candidate matches exactly; remember the first hit
                # of any kind as the fallback. Extra requests are spent only on titles
                # that match nothing exactly.
                fallback = None
                for cand in queries(display or k, alias):
                    res = get("https://api.themoviedb.org/3/search/movie?language=fi-FI&query="
                              + urllib.parse.quote(cand), th)
                    hits = res.get("results") or []
                    if hits:
                        hit, exact = pick(hits, cand)
                        if exact:
                            mid = hit.get("id")
                            poster = hit.get("poster_path") or poster
                            exact_id = True
                            break
                        if fallback is None:
                            fallback = hit
                    time.sleep(0.2)
                else:
                    if fallback is not None:
                        mid = fallback.get("id")
                        poster = fallback.get("poster_path") or poster
                        exact_id = False
                        weak.append(f"{display or k} -> {fallback.get('title')}")
            # Seeded from the cache, not from "". A detail request that fails must leave
            # the text this entry already had: writing "" would empty the cache's copy of
            # a synopsis nothing else can put back, and the pass would report a rating as
            # re-read while carrying the old figures. Only a response that arrived
            # replaces either slot, so a film whose overview TMDB really has emptied
            # still clears.
            syn_fi = (c.get("fi") or "") if isinstance(c, dict) else ""
            syn_en = (c.get("en") or "") if isinstance(c, dict) else ""
            detail_ok = False
            if mid:
                # Finnish overview when TMDB has one, English as the fallback.
                for langcode, slot in (("fi-FI", "fi"), ("en-US", "en")):
                    try:
                        d = get(f"https://api.themoviedb.org/3/movie/{mid}?language={langcode}", th)
                    except Exception:
                        time.sleep(0.2)
                        continue
                    text = (d.get("overview") or "").strip()
                    poster = poster or (d.get("poster_path") or "")
                    # Both fields or neither. A response carrying only `vote_count` used
                    # to set the rating to 0 over the top of a real one and then stamp the
                    # entry as read; one carrying only `vote_average` was not noticed at
                    # all. Either way it is not the pair the entry is parked on.
                    fresh_n = _numeric(d.get("vote_count"))
                    fresh_r = _numeric(d.get("vote_average"))
                    if fresh_n is not None and fresh_r is not None:
                        votes, rating = fresh_n, fresh_r
                        detail_ok = True
                    # Genre ids cost nothing: they are in the response this pass
                    # already fetches for the synopsis. Ids, not names, so one
                    # id->name map per language covers every film.
                    if d.get("genres"):
                        gids = [g["id"] for g in d["genres"] if g.get("id")]
                    if slot == "fi":
                        syn_fi = text
                        if text:
                            break
                    else:
                        syn_en = text
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
            shown = round(rating, 1) if rating and votes >= MIN_VOTES else 0
            if rating and not shown:
                thin.append(f"{display or k} ({round(rating, 1)} / {votes} votes)")
            # "x" = the id came from an exact title match (or a hand-written alias id).
            # Only those are safe to merge films on: a weak id would fold two different
            # films into one row, which is worse than showing two rows.
            # `c` is what parks an entry for a week, so only a detail response that
            # carried rating and vote data may move it. A film whose id has no readable
            # detail keeps the date it had and stays due on the next run rather than
            # being recorded as re-read on figures nothing looked at. A title that
            # matched no id at all is not in that state: there is nothing to read, and
            # it keeps its daily re-check as before.
            stamp = today if (detail_ok or not mid) else (
                (c.get("c") or "") if isinstance(c, dict) else "")
            # `a` is every attempt, `c` only the ones that answered. Keeping them apart is
            # what lets a failed entry stay due without outranking the rest of the backlog
            # for ever -- see RATING_MAX_AGE.
            attempt = today if mid else ((c.get("a") or "") if isinstance(c, dict) else "")
            cache[k] = {"r": shown, "n": votes, "v": yt, "x": bool(mid) and exact_id,
                        "g": gids, "i": mid or "", "c": stamp, "a": attempt,
                        "fi": syn_fi, "en": syn_en, "p": poster}
            replaced = True
            if detail_ok and k in refreshes:
                settled.add(k)
            rechecked += 1 if isinstance(c, dict) else 0
            looked += 0 if isinstance(c, dict) else 1
            pending += 1
            if pending >= FLUSH_EVERY:
                flush(cache, today)
                pending = 0
            time.sleep(0.25)
        except Exception as e:
            print(f"[enrich] {display}: {e}")
            # A scheduled refresh that got as far as being attempted has to record that,
            # even when nothing else about the entry can be written. `attempt` is set
            # only just before the write, after the video request, so anything raising
            # ahead of it -- that request, the arithmetic under it -- left the entry
            # saying it had never been attempted. Which puts it back at the head of the
            # queue on the next run and every run after: exactly the starvation `a`
            # exists to stop, reachable through the one path that skips the write.
            #
            # Only the marker moves. `c`, the rating, the votes, the synopses, the
            # trailer and the id are whatever was already cached, so a title that aborts
            # keeps all of it and stays due -- `c` still advances only where a detail
            # response carried the vote pair. Guarded on `replaced`, so an exception
            # *after* the write cannot put the old entry back over a good one.
            if k in refreshes and isinstance(c, dict) and not replaced:
                cache[k] = {**c, "a": today}

    flush(cache, today)

    # After the loop, because whether a scheduled refresh actually re-read anything is
    # only known once its detail request has answered. A failure here is not an error --
    # the entry keeps its figures and its date and comes back to the head of the queue --
    # but a run where every refresh fails must not read like a run where every one
    # worked. Deferred is what the budget left for the next pass; a ceiling nobody can
    # see reads as "everything is current".
    if refreshes or deferred:
        print(f"[enrich] rating refresh: {len(refreshes)} scheduled, "
              f"{len(settled)} re-read, {len(refreshes) - len(settled)} failed and "
              f"still due, {deferred} deferred (budget {REFRESH_BUDGET})")

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
            # The sample size travels with the score: 7.1 from 41 votes and 7.1 from
            # 15 000 are not the same claim, and the client says which it is.
            if c.get("r") and c.get("n") and s.get("votes") != c["n"]:
                s["votes"] = c["n"]; changed = True
            if c.get("v"):
                url = "https://www.youtube.com/watch?v=" + c["v"]
                if s.get("tr") != url:
                    s["tr"] = url; changed = True
            if not s.get("img") and c.get("p"):
                s["img"] = "https://image.tmdb.org/t/p/w342" + c["p"]; changed = True
            # The film's identity across chains. Only an exact match is written: the
            # combined city view merges on it, and a weak id would fold two different
            # films into one row. Chains publish the same film under different titles
            # ("Mutiny" vs "Mutiny - Lavastettu syylliseksi"), which no title key fixes.
            if c.get("x") and c.get("i") and s.get("tmdbId") != c["i"]:
                s["tmdbId"] = c["i"]; changed = True
            # Genres the client can localize, and the only reliable signal for the kids
            # filter: provider genre strings disagree across chains and use four spellings
            # for the family genre alone.
            if c.get("g") and s.get("gids") != c["g"]:
                s["gids"] = c["g"]; changed = True
        if changed:
            common.write_json(p, doc)
            touched += 1

    # Name the titles that found nothing: these are the candidates for tmdb-aliases.json.
    missing = sorted(display for k, display in titles.items()
                     if not (cache.get(k) or {}).get("i"))
    if missing:
        print(f"[enrich] no TMDB match ({len(missing)}): " + " | ".join(missing))
    # A weak match is a wrong poster waiting to happen; a thin one is a rating hidden
    # on purpose. Both are for reading, not for acting on automatically.
    if weak:
        print(f"[enrich] weak match, no exact title ({len(weak)}): " + " | ".join(sorted(weak)))
    if thin:
        print(f"[enrich] rating held back, under {MIN_VOTES} votes ({len(thin)}): "
              + " | ".join(sorted(thin)))

    ids = sum(1 for c in cache.values() if isinstance(c, dict) and c.get("x") and c.get("i"))
    hit = sum(1 for c in cache.values() if isinstance(c, dict) and c.get("r"))
    syn = sum(1 for c in cache.values() if isinstance(c, dict) and (c.get("fi") or c.get("en")))
    pics = sum(1 for c in cache.values() if isinstance(c, dict) and c.get("p"))
    print(f"[enrich] {len(titles)} titles, {looked} new, {rechecked} re-checks, "
          f"{hit} with rating, {syn} with synopsis, {pics} with poster, "
          f"{ids} mergeable by id, "
          f"{touched} files updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
