#!/usr/bin/env python3
"""Add TMDB ratings, trailers, synopses and posters to providers that publish none.

Finnkino gets these via films.json/tmdb.json keyed by its own filmId. The other
providers have no such id, so this pass keys a cache on the normalised title and
writes `tmdb` (rating) and `tr` (trailer URL) straight onto each show.

Idempotent and cache-first: a re-run is cheap once a title is known. Titles with no
trailer are re-checked once a day, looking for one; a cached rating is re-read once it is
a week old, oldest first and a bounded number a run. See `due()`.

Only a trusted match publishes: an exact title match or a hand-written alias id, `x` in
the cache. A weak candidate is kept in the cache for the log and the retry, and nothing
of it reaches a show or films-extra.json; what an earlier run wrote from one is taken
back. See `trusted()`.
"""
import datetime, json, os, pathlib, re, sys, time, urllib.parse, urllib.request

import common
import mirror_posters
import refresh

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


age_days = refresh.age_days


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
#
# The audio-language markers are the half that was missing until 2026-09-14: `suomeksi`
# was here and its counterparts were not, so a cinema selling the dubbed and the
# subtitled run as two films had one of them searchable and the other not. Measured
# across the committed data that day: `englanniksi` in three spellings at six providers
# (18 showtimes as `(englanniksi)`, 9 as a trailing ENGLANNIKSI, 5 as `, englanniksi`),
# `(på svenska)` at two and `(suomeksi puhuttu)` at one, 32 showtimes and five distinct
# titles in all, every one of them cached unmatched. A marker names the audio, never the
# film, so it belongs off the search string exactly as `suomeksi` already was.
# 2026-09-19: `(Puhumme suomea!)` is TMB's spelling of the same claim, on all four of its
# cinemas at once -- 16 showtimes of Kojootti vs ACME across Toijala, Sampo, Mania and Elo,
# every one unmatched, while the chains spelling it `(suomeksi)` matched 1204680 from the
# first run. The exclamation mark is the operator's and is matched with the rest.
PAREN_NOISE = re.compile(
    r"\(\s*(?:(?:19|20)\d{2}|suomeksi(?:\s+puhuttu)?|englanniksi|p[åa]\s+svenska"
    r"|puhumme\s+suomea!?|dubattu|dub\.?|orig\.?|re-?release"
    r"|uudelleenjulkaisu|uusi\s+kopio|live\s?action|liveaction|2d|3d|imax|4k)\s*\)", re.I)
TRAIL_NOISE = re.compile(
    r",?\s*\b(?:suomeksi|englanniksi|dubattu|or[i]?ginaali\s+äänillä)\b\s*$",
    re.I)

# Two terminal version markers still reaching TMDB, measured 2026-09-20 in the committed
# data. TMB publishes "Kojootti vs ACME Orginaali äänillä" with no brackets and with
# the operator's missing i, 8 showtimes across Toijala, Sampo, Mania and Elo, every one
# an initials tile, while every other spelling of that film matched 1204680. "(eng)" and
# "(sub)" name the audio run and the subtitled one in three letters, and had sat
# unmatched in the cache since 2026-09-14. Both are anchored to the end: "eng" and
# "sub" are ordinary syllables, and a rule that fired mid-title would cut real words
# out of real names.
TRAIL_VERSION = re.compile(r"\s*\(\s*(?:eng|sub)\s*\)\s*$", re.I)

# A calendar names events, not films. Tähti Kino's three rows on 2026-09-19 read
# "Hetki ennen valoa -elokuvanäytös", "Presidentin kyyditys -elokuvan näytös" and
# "Ryhmä Hau: Dinoelokuva -elokuvanäytös", all three unmatched, while every chain
# publishing the bare titles matched. The words say "film screening", which the event's
# own category already establishes, so they are noise on the search string. Anchored to
# the end and requiring the dash, so a film actually called that keeps its name.
EVENT_NOUN = re.compile(r"\s*[-–]\s*elokuva(?:n\s+)?n[äa]yt[öo]s\s*$", re.I)

# A bare format token at the end of the title, with no brackets for PAREN_NOISE to find.
# Measured 2026-09-23 over the committed data: exactly two titles carry one, and both are
# decoration rather than a name. "Spider-Man: Brand New Day 2D" at Kino 123 and Trio 123
# was the worse of the two: it matched 557, which is Spider-Man (2002), so the row carried
# the wrong film's poster and rating while every other cinema's spelling matched 969681.
# "Avengers: Endgame Encore 2D" at Kinopalatsi Kotka, 7 showtimes, was an initials tile.
#
# The client already reads these four as noise anywhere in a title -- `mergeKey` strips
# them to fold a city page's cards -- so the search string is where they were still being
# taken as part of the name. Anchored to the end and requiring a word in front, so a film
# actually called "3D" keeps its name, and repeatable, because "... 2D IMAX" is one row
# away and reads the same.
#
# The limit, recorded rather than guarded: a film whose name really ends in one, such as
# the 2008 concert film "U2 3D", would be searched as "U2". Nothing in the committed data
# is such a film, the client has read these tokens as noise for longer than this has, and
# a match is still only taken on an exact title, so the failure needs a real film titled
# exactly like the truncation. Revisit if one is ever published.
TRAIL_FORMAT = re.compile(r"(?<=\w)(?:\s+(?:2d|3d|imax|4k)\b)+\s*$", re.I)

# An event attached to the screening rather than to the film: the director in the room,
# a book club after it, a discussion. The "+" says the event sits beside the title, and
# the noun after it says which event. Measured 2026-09-23 over the committed data: three
# rows carry one, "P\u00e4ivien lumo + tekij\u00e4vierailu" at Kino Tapiola, "Don Quijote
# Barcelonassa (+leffalukupiiri)" and "Suomi radalla (+keskustelutilaisuus)" at Kino
# Aurora, and all three were initials tiles. The bare "P\u00e4ivien lumo" already matched
# 1563565 at Kino Laika, Kino Kilta and Kino Regina, so only the suffix was in the way.
#
# Each noun is named and the whole thing is anchored to the end, because "+" belongs to
# real titles and a rule that ate everything after one would destroy them: "Romeo +
# Juliet" matches 454 at Cinema Niagara today, and Kino Regina's double bill "Sylvi +
# anna-liisa" is two works joined by it. Both keep every word under this.
#
# Refused, and why: "+ keskustelua" inside Kino Kuvakukko's "Vilimit-festivaali: Retkeily
# kansallispuistossa ... visuaalinen luento + keskustelua, vapaa p\u00e4\u00e4sy)", because it is
# not terminal and the row is a walk and a lecture rather than a film. A bare trailing
# "+" with no noun, because nothing in the data has one and it would be a guess.
# "keskustelutilaisuus" is here although it closes nothing today: "Suomi radalla" has no
# TMDB record either way, and leaving the noise on its search string would be wrong even
# where the answer does not change.
TRAIL_EVENT = re.compile(
    r"\s*\(?\s*\+\s*(?:tekij[\u00e4a]vierailu|leffalukupiiri|keskustelutilaisuus)\s*\)?\s*$",
    re.I)

# A strand can sit in a trailing parenthesis instead of in front of a colon. The content
# is matched against the one shared list in strands.py rather than against a pattern, so
# a parenthesis holding anything else -- an original title ("Beginnings (Begyndelser)"),
# an edition ("Nirvana 'Nevermind' (35th Anniversary)"), a screening note -- is left
# alone, and a strand added for either position covers both.
PAREN_STRAND = re.compile(r"\(\s*([^()]{1,40}?)\s*\)\s*$")


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
    m = PAREN_STRAND.search(t)
    if m and m.group(1).lower() in EVENT_PREFIXES and t[:m.start()].strip():
        t = t[:m.start()].strip()
    t = EVENT_NOUN.sub(" ", t)
    t = TRAIL_EVENT.sub(" ", t)
    t = TRAIL_FORMAT.sub(" ", t)
    t = TRAIL_NOISE.sub(" ", PAREN_NOISE.sub(" ", TRAIL_VERSION.sub(" ", t)))
    return re.sub(r"\s{2,}", " ", t).strip(" -–:,")


# A rating is only worth showing once enough people have voted. A festival premiere
# with three votes gives a clean 10.0 or 5.0, which reads as a verdict and is noise.
MIN_VOTES = 25


# The refresh schedule lives in refresh.py, because data/tmdb.json answers the same
# question and used to answer it separately -- which is how the frozen-rating defect came
# to sit in both files. What stays here is this cache's own shape.
def is_complete(c):
    """Every field the title cache writes is present. -> bool.

    A missing field means incomplete rather than wrong, so adding one -- "n" arrived with
    the MIN_VOTES gate -- costs a single re-check pass instead of a cache wipe. This is
    the predicate handed to refresh.due(); the Finnkino cache has its own, because it
    carries neither synopsis nor poster.
    """
    return (isinstance(c, dict) and ("fi" in c or "en" in c)
            and "p" in c and "n" in c and "x" in c and "g" in c)


def due(titles, cache, today, max_age=None, budget=None):
    """This pass's entries that are due. -> (keys, refreshes, deferred). See refresh.due."""
    return refresh.due(titles, cache, today, is_complete, max_age, budget)


# --- what may be published -----------------------------------------------------------------
# The cache keeps a weak candidate: its id is what the log names and what the daily retry
# starts from. Publishing is a separate question, answered once, here. Kino Regina's
# "Naisen kasvot" (1938) fell back to TMDB 4780, De Palma's "Obsession" (1976): the weak
# flag withheld the tmdbId, and the wrong film's poster, rating, votes, trailer, genre
# ids and synopses went onto the show and into films-extra.json regardless, where run.py
# then carried them from one venue file into the next. A cinema's own fields are never
# touched by any of this: only what this pass itself writes is gated, and only what this
# pass itself could have written is taken back.
TMDB_IMG = "https://image.tmdb.org/t/p/w342"
# The show fields this pass writes. `img` is handled apart, because a cinema publishes
# posters too.
PUBLISHED = ("tmdb", "votes", "tr", "gids", "tmdbId", "oyear")

# The film's own first release year, published as `oyear` and read by the client and by
# build_pages to render "Carrie (1976)".
#
# **It is TMDB's `release_date` on an exact match and nothing else.** Three other years
# are in reach here and every one of them is a different fact:
#
#   * `show["year"]` is the year *the cinema published*, which gather() collects as a
#     search hint. Two adapters set it and it is not checked against anything.
#   * Finnkino's `releaseDate`, which fetch_data.py reads, is the Finnish release. For a
#     reissue that is the reissue's date, so it would print Carrie (2026).
#   * The screening's own date, which is never the film's.
#
# A weak match's year is the wrong film's, so `oyear` is written only where `trusted()`
# holds, the same gate `tmdbId` passes. Missing stays missing: no fallback, no inference,
# and no year assembled out of a title. An entry cached before this field existed has no
# `ry` and shows no year until the refresh re-reads it, which is correct rather than a
# gap to paper over.


def trusted(c):
    """Whether a cache entry may supply public metadata: an exact title match or a
    hand-written alias id, and an id to go with it."""
    return isinstance(c, dict) and bool(c.get("x")) and bool(c.get("i"))


def poster_refs(c):
    """Every form the entry's poster takes in published data: the w342 URL this pass
    writes, and the path mirror_posters rewrites it to on the same run."""
    p = (c.get("p") or "") if isinstance(c, dict) else ""
    if not p:
        return set()
    url = TMDB_IMG + p
    return {url, f"data/posters/{mirror_posters.key_for(url)}.jpg"}


def tmdb_poster(img, c):
    """Whether a show's `img` is TMDB's: any image.tmdb.org address, or the mirrored
    copy of this entry's poster. A cinema's own poster, mirrored or not, is neither."""
    img = (img or "").strip()
    return bool(img) and (img.startswith("https://image.tmdb.org/") or img in poster_refs(c))


def unpublish(show, c):
    """Take back what this pass may have written onto a show from an untrusted entry.
    -> whether anything changed. The cinema's own poster stays.

    A poster is TMDB's when it is one of this entry's forms, an image.tmdb.org address,
    or marked `isrc: "tmdb"`: the mark is set by this pass on every poster it writes and
    by run.py on a mirrored poster it carries from the previous file for a show whose
    adapter published none, so a poster that came from an earlier candidate is caught by
    the mark where the path alone could not tell it from a cinema's own mirrored poster."""
    changed = False
    for field in PUBLISHED:
        if field in show:
            del show[field]
            changed = True
    if tmdb_poster(show.get("img"), c) or show.get("isrc") == "tmdb":
        show.pop("img", None)
        changed = True
    if show.pop("isrc", None) is not None:
        changed = True
    return changed


def publish_poster(show, c):
    """Put a trusted entry's poster on a show that has none of its own. -> changed.

    A cinema's own poster is never replaced. A poster marked as TMDB's is this entry's to
    correct: "Naisen kasvot" was weak one day and aliased the next, and the show went on
    carrying the wrong film's mirrored poster because only a blank was ever filled. A
    marked poster the entry cannot replace, having none, comes off."""
    own = TMDB_IMG + c["p"] if c.get("p") else ""
    if show.get("isrc") == "tmdb" and show.get("img") not in poster_refs(c):
        if own:
            show["img"] = own
        else:
            show.pop("img", None)
            show.pop("isrc", None)
        return True
    if not show.get("img") and own:
        show["img"], show["isrc"] = own, "tmdb"
        return True
    return False


def unpublish_extra(e, c):
    """Take back what merge_extra may have written into a films-extra entry from an
    untrusted candidate. `r`, `tr`, `img` and the English synopsis are written by nothing
    else, so they go. The Finnish slot is the cinema's or TMDB's, and only text equal to
    this candidate's own overview is known to be TMDB's; other text stands. `kr`/`krs`
    belong to merge_shared, which decides them from scratch every run."""
    e["r"] = 0
    e["tr"] = ""
    e.pop("img", None)
    s = e.setdefault("s", {"fi": "", "en": ""})
    s["en"] = ""
    if s.get("fi") and isinstance(c, dict) and s["fi"] == (c.get("fi") or ""):
        s["fi"] = ""
# --- end what may be published -------------------------------------------------------------


def pick(hits, query, year=None, original=None):
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

    With `year`, the published year decides among the hits whose title matches exactly.
    The year itself beats a neighbouring year; among hits at the same distance, a hit
    whose original title is the published `original` beats the rest. What is left has
    to be one film: two different ids still standing is a tie, returned as *not* exact,
    whatever order TMDB listed them in. An exact title whose year is further off than
    YEAR_TOL is not exact either: a 1981 "All Night Long" is not the 1962 one. Without a
    year the first exact hit wins, as before. A hit with no release date cannot
    contradict a year and is accepted.
    """
    q = norm(query)
    exact = [h for h in hits
             if norm(h.get("title")) == q or norm(h.get("original_title")) == q]
    if not exact:
        return hits[0], False
    if not year:
        return exact[0], True
    near = [h for h in exact if plausible(release_year(h), year)]
    if not near:
        return exact[0], False
    best = min(abs(int(release_year(h)) - int(year)) if release_year(h) else YEAR_TOL
               for h in near)
    tier = [h for h in near
            if (abs(int(release_year(h)) - int(year)) if release_year(h) else YEAR_TOL) == best]
    if len({h.get("id") for h in tier}) > 1 and norm(original):
        named = [h for h in tier if norm(h.get("original_title")) == norm(original)]
        if named:
            tier = named
    return tier[0], len({h.get("id") for h in tier}) == 1


def alias_supersedes(alias, entry):
    """Does a hand-written alias replace what the cache already holds?

    An alias is a hand decision with its evidence written beside it, so it outranks
    whatever the search arrived at. Two cases, and the second is why this is a function.

    - *A weak entry.* The original case: an alias exists precisely because the search could
      not settle the title, and a complete entry would otherwise be skipped before the
      alias was ever read.
    - *An exact entry whose id disagrees.* An exact title match is not proof of the right
      film. A Finnish distributor title can be another film's registered one:
      `Practical Magic: Lumotut sisaret` is how thirty-two providers published the 2026
      sequel and is also what TMDB holds for the 1998 original, so 256 showtimes carried
      1998's poster, score and trailer with `x: True` against them. Nothing automatic can
      see that; the alias is the correction, and it has to be able to reach an entry the
      matcher was sure of.

    A search-string alias cannot be compared with an id, so an exact entry stands: the
    string is a better query, not a verdict on a film.
    """
    if not alias:
        return False
    if not isinstance(entry, dict) or not entry.get("x"):
        return True
    return str(alias).isdigit() and entry.get("i") != int(alias)


def load_aliases():
    try:
        return {k: v for k, v in json.loads(ALIAS_FILE.read_text()).items()
                if not k.startswith("_")}
    except Exception:
        return {}


def queries(title, alias=None, original=None):
    """Cleaned title, the original title, the head before a dash/colon, the raw title.

    An alias that is not a bare TMDB id goes first. The original title comes second:
    TMDB searches original, translated and alternative titles, so it is the string most
    likely to hit when the Finnish distributor title matches nothing, and it is tried
    only after the published title has failed, so a film that already matched keeps its
    match. Candidates are deduplicated case-insensitively, so an original title equal
    to the published one costs no request. The raw title stays last so a wrong cleanup
    costs an extra request rather than a missing film.
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
    add(clean(original))
    head = re.split(r"\s+[-–]\s+|:\s+", c, maxsplit=1)[0].strip()
    if len(head) > 3:
        add(head)
    add(title)
    return out


# --- what a show says about the film -----------------------------------------------------
# The optional `year` field is the film's release year as the cinema published it, four
# digits as a string. A cinema that prints it in the title instead, "Trainspotting (1996)",
# is read the same way, before clean() strips it from the search string. A screening date
# is never a year: a repertory house shows a 1962 film in 2026.
YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
YEAR_IN_TITLE = re.compile(r"\(\s*((?:19|20)\d{2})\s*\)\s*$")


def published_year(show):
    """The film's year as the cinema published it, or ""."""
    y = str(show.get("year") or "").strip()
    if YEAR_RE.match(y):
        return y
    m = YEAR_IN_TITLE.search(show.get("title") or "")
    return m.group(1) if m else ""


def gather(shows):
    """Every published title with the evidence its shows carry.
    -> {key: {"t": display title, "o": original title, "y": year}}.

    One title can be published by several chains. The original title and the year are
    used only when every show that carries one agrees: two different originals or two
    different years under one title is not evidence either way, and the search runs on
    the title alone as it did before either field existed. A show from older data, with
    neither field, contributes nothing and changes nothing.
    """
    out = {}
    for s in shows:
        k = norm(s.get("title"))
        if not k:
            continue
        e = out.setdefault(k, {"t": s.get("title"), "_o": {}, "_y": set()})
        o = (s.get("original") or "").strip()
        if o and norm(o):
            e["_o"].setdefault(norm(o), o)
        y = published_year(s)
        if y:
            e["_y"].add(y)
    for e in out.values():
        originals, years = e.pop("_o"), e.pop("_y")
        e["o"] = next(iter(originals.values())) if len(originals) == 1 else ""
        e["y"] = next(iter(years)) if len(years) == 1 else ""
    return out


def release_year(hit):
    """A search hit's release year, or "" when TMDB has none."""
    d = str((hit or {}).get("release_date") or "")
    return d[:4] if re.match(r"^\d{4}", d) else ""


# A published year and TMDB's primary release year differ by one for a good share of
# older films: production year against premiere, or a festival year against the
# general release. Two apart is another film with the same title.
YEAR_TOL = 1


def plausible(hit_year, year):
    """Whether a hit's year can be the published one. Unknown cannot contradict."""
    if not hit_year or not year:
        return True
    return abs(int(hit_year) - int(year)) <= YEAR_TOL


def search(cand, year, headers, lang="fi-FI"):
    """One search request. -> hits. `year` filters on TMDB's primary release year
    (documented as a string parameter on /3/search/movie); "" sends no filter.

    `lang` only localizes the response's `title`; it does not widen which titles TMDB
    searches. That is the whole point of the en-US second pass below: the same hits come
    back either way and only the string they are compared against changes.
    """
    url = (f"https://api.themoviedb.org/3/search/movie?language={lang}&query="
           + urllib.parse.quote(cand))
    if year:
        url += f"&primary_release_year={year}"
    return get(url, headers).get("results") or []


# How many exact matches one pass may re-judge on new evidence. The first pass after a
# cinema starts publishing years has every one of its films to re-judge; each costs the
# searches and the detail calls again, so the catch-up is spread over runs.
RECONSIDER_BUDGET = int(os.environ.get("KINO_TMDB_RECONSIDER") or 25)


def reconsider(facts, cache, aliases, budget=None):
    """Exact matches and unmatched titles whose evidence has changed since they were
    judged. -> (keys to re-judge, how many more wait for the next run).

    A cached id is kept for ever once `x` is set, so a film matched on its Finnish title
    alone stays matched when the cinema starts publishing the year that says it is the
    other film of that name. A title with no id is re-searched once a day, so one whose
    original title and year arrive after today's search would wait until tomorrow: three
    Regina films did on 2026-09-13. An entry records the original title and year it was
    judged on (`o`, `y`; absent in older entries, read as none). When the shows now carry
    different evidence, and some, the entry is dropped and searched again, exact and
    unmatched alike, out of one budget in key order so a pass that defers the rest picks
    up where it left off. Weak entries are dropped on every load anyway, and a key with
    an alias is a hand decision and is left alone. An unmatched title whose evidence has
    not changed keeps its daily retry and nothing else.

    **`q` is the evidence this side owns, and it is checked first.** A strand added to
    strands.py changes `clean()` for a title the cinema has not touched, so `o` and `y`
    are identical and the entry would keep its daily retry: the strand would not apply
    until tomorrow. That cost a hand edit of three cache entries on 2026-09-19. The
    comparison sits *above* the `("", "")` guard on purpose, because the guard reads "the
    cinema published no evidence, so none of it can have changed" and one of those three,
    `Kino Iglu: Tokyo Story`, has neither an original title nor a year; checked after the
    guard this would miss exactly the case it was written for.

    It compares `norm(clean(title))` rather than the cleaned string, because one key is
    reached by several spellings and `gather()` keeps whichever show it met first. A bare
    comparison re-judges 26 settled matches every pass on the committed data; normalised,
    none.

    **`q` carries no year and must not be made to.** `clean()` strips a trailing `(1996)`
    from the search string, so `q` is `trainspotting` while the year lives in `y` alone.
    That separation is the point: a cinema correcting 1987 to 1988 is the cinema's
    evidence moving and `y` is what should notice it. Putting the year back into `q` would
    trip both comparisons on one change and re-judge the entry twice for nothing.

    **A missing `q` now reads as due, which it did not until 2026-09-23.** It used to
    re-judge nothing, so that the entries written before the field existed would not all
    be re-searched in one pass. The budget above already prevents that, and reading it as
    "unknown, leave it" froze an entry on whatever a long-gone cleaner decided: on
    2026-09-23 `Spider-Man: Brand New Day 2D` at Kino 123 and Trio 123 still carried 557,
    which is Spider-Man (2002), and no change to `clean()` could ever reach it because the
    entry predates `q`. 262 of 609 entries were in that state. They drain at the budget's
    rate, 25 a run in key order, and once an entry has been re-judged once it has a `q`
    and behaves like every other.

    An entry with `x` set and a changed `q` **is** re-judged, which re-searches a match
    that was good: that is what a changed `o` or `y` already does, and the alternative is a
    strand, or a cleaner rule, that never reaches the titles it was added for. The risk it
    carries is the rule's own, not this function's: a prefix or a suffix stripped off a
    title can widen the search onto a different film, which is why strands.py and the
    trailing rules above record what was measured and refused.
    """
    budget = RECONSIDER_BUDGET if budget is None else budget
    due = []
    for k in sorted(facts):
        c, f = cache.get(k), facts[k]
        if not isinstance(c, dict) or aliases.get(k):
            continue
        if c.get("i") and not c.get("x"):
            continue                          # weak: dropped on load, not this list
        if c.get("q") != norm(clean(f.get("t") or k)):
            due.append(k)                     # the search string changed, or is unknown
            continue
        now = (norm(f.get("o")), f.get("y") or "")
        if now == ("", ""):
            continue
        if now != (c.get("o") or "", c.get("y") or ""):
            due.append(k)
    return due[:budget], max(0, len(due) - budget)


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

# --- shared KAVI classification -------------------------------------------------------
# A cinema that publishes no age rating is not saying the film is unrestricted; it is
# saying it publishes none, and a good fraction of showtimes are in that state. The
# classification is KAVI's and national, so a cinema is reporting the same fact rather
# than forming an opinion, and the data agrees: no film rated at more than one chain has
# yet been rated differently. The measured counts move with every run and live in
# docs/archive/2026-09-pipeline.md rather than here.
#
# Borrowing is deliberately narrow.
#   * Only exact TMDB matches take part. A weak match neither donates nor receives: 13
#     titles were weak in the run this was written against, one of them "Kapina" ->
#     "Matilda ja lasten kapina", and a children's classification landing on the wrong
#     film fails in the unsafe direction for the Lapsille filter. Same rule the cross-
#     chain merge already applies to `tmdbId`.
#     The `x` checks below cannot be made to fail today, and that is worth knowing rather
#     than trusting: main() deletes every weak entry that carries an id as it loads the
#     cache, so one never reaches this pass in the first place. That deletion is described
#     there as a one-off for a shape change, so it is the wrong thing to depend on, and
#     these checks are what is left if it goes.
#   * Every non-empty rating for the film has to agree. Disagreement publishes nothing
#     and is logged with the film, the sources and the values; taking the strictest was
#     rejected, because two cinemas disagreeing about a national classification means one
#     of them is wrong and the run should say so rather than paper over it.
#   * Runtimes have to be compatible where both sides publish one. The measured gaps fall
#     into a tight cluster at nought to one minute and a far one around twenty, with
#     nothing between; the far cluster was Riviera's 110-minute "Practical Magic" against
#     a 130-minute listing, an alternate cut. Five minutes sits in the gap between them.
#   * A cinema's own rating is never replaced. The shared value only fills a blank.
RUNTIME_TOL_MIN = 5


def _minutes(v):
    """A published runtime in whole minutes, or None. Providers write it as a string."""
    m = re.match(r"^\s*(\d+)\s*$", str(v if v is not None else ""))
    return int(m.group(1)) if m else None


def shared_ratings(rated):
    """Exact-matched shows that carry a rating -> ({tmdbId: entry}, [disagreements]).

    `entry` is {"rating", "sources", "runtimes"}: the agreed classification, the chains
    that published it, and the runtimes they published it with.

    A value this pass wrote itself is not evidence. run.py keeps a stale venue's previous
    data, so a borrowed rating survives into the next run, and counting it as a source
    would let a loan outlive the cinema it was borrowed from and then donate itself
    onward. `rsrc` marks those, and only a cinema's own rating is a source.
    """
    seen = {}
    for s in rated:
        if s.get("rsrc") == "shared":
            continue
        fid, r = s.get("tmdbId"), (s.get("rating") or "").strip()
        if not fid or not r:
            continue
        e = seen.setdefault(fid, {"ratings": {}, "runtimes": set(), "title": s.get("title")})
        e["ratings"].setdefault(r, set()).add(s.get("provider") or "finnkino")
        mins = _minutes(s.get("len"))
        if mins is not None:
            e["runtimes"].add(mins)
    table, clashes = {}, []
    for fid, e in seen.items():
        if len(e["ratings"]) > 1:
            clashes.append({"tmdbId": fid, "title": e["title"],
                            "values": {r: sorted(ps) for r, ps in sorted(e["ratings"].items())}})
            continue
        rating, sources = next(iter(e["ratings"].items()))
        table[fid] = {"rating": rating, "sources": sorted(sources),
                      "runtimes": sorted(e["runtimes"])}
    return table, clashes


def borrowed_rating(show, table, tol=RUNTIME_TOL_MIN):
    """The classification this show may borrow, or None.

    The caller has already established that the show's title is an exact TMDB match.
    """
    if (show.get("rating") or "").strip():
        return None                       # a cinema's own rating is never replaced
    e = table.get(show.get("tmdbId"))
    if not e:
        return None
    mine = _minutes(show.get("len"))
    if mine is not None and e["runtimes"]:
        if min(abs(mine - d) for d in e["runtimes"]) > tol:
            return None                   # an alternate cut, not this film
    return e["rating"]
# --- end shared KAVI classification ----------------------------------------------------



def merge_extra(cache, today):
    """Fold cached text/ratings/posters into films-extra.json.

    Synopses live in their own file so area files stay small: one synopsis repeated
    across 158 showtimes would add roughly 80 kB per venue. Providers write their own
    (better) Finnish synopses into this file before this pass runs, so an existing fi
    text is never clobbered. Re-reading the file per flush keeps that rule true even
    if a provider wrote to it in between.

    Trusted entries fill. Every other key in the file, an untrusted entry's or one the
    cache no longer holds, gives back what a run before this rule wrote from a weak
    candidate: a weak entry is dropped as the cache loads, so a film that then left the
    programme is exactly the key with residue and no entry. See unpublish_extra.
    """
    try:
        doc = json.loads(EXTRA.read_text())
    except Exception:
        doc = {}
    films = doc.get("films") or {}
    for k, e in films.items():
        if isinstance(e, dict) and not trusted(cache.get(k)):
            unpublish_extra(e, cache.get(k))
    for k, c in cache.items():
        if not trusted(c):
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
    common.write_films_extra(EXTRA, {"generated": today, "films": films})


def merge_shared(shared, today):
    """Publish the shared classification into films-extra.json: `kr` is the value, `krs`
    the chains it came from. Keyed like everything else in that file.

    Every existing `kr` is dropped first and the current set written fresh, so this is the
    whole answer rather than an accumulation. A film loses its shared value when its donor
    leaves the programme, when a second chain starts disagreeing, or when the runtime rule
    starts refusing it, and none of those write anything to notice: only clearing first
    removes them. For the same reason it runs on an empty set, which is exactly the case
    where every previous value has to go."""
    try:
        doc = json.loads(EXTRA.read_text())
    except Exception:
        doc = {}
    films = doc.get("films") or {}
    for e in films.values():
        if isinstance(e, dict):
            e.pop("kr", None)
            e.pop("krs", None)
    for k, v in shared.items():
        e = films.setdefault(k, {"s": {"fi": "", "en": ""}, "r": 0, "tr": ""})
        e["kr"], e["krs"] = v["kr"], v["krs"]
    common.write_films_extra(EXTRA, {"generated": today, "films": films})


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
    # thing the alias exists to replace, and so does an alias id that disagrees with an
    # exact one: see `alias_supersedes`.
    overridden = [k for k, v in cache.items() if alias_supersedes(aliases.get(k), v)]
    for k in overridden:
        del cache[k]
    if overridden:
        print(f"[enrich] dropped {len(overridden)} entries an alias replaces: "
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
            # Only rename an id TMDB returned, so this can never invent a genre.
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
    shows = []
    for p in files:
        try:
            doc = json.loads(p.read_text())
        except Exception as e:
            print(f"[enrich] {p.name}: unreadable ({e})")
            continue
        shows.extend(doc.get("shows", []))
    facts = gather(shows)
    titles = {k: f["t"] for k, f in facts.items()}

    # A match judged, or a search that found nothing, before the original title or year
    # was published is judged again now that it is. Bounded per run, aliases excluded.
    rejudge, held = reconsider(facts, cache, aliases)
    matched = sum(1 for k in rejudge if (cache.get(k) or {}).get("i"))
    # Kept, not discarded: the entry comes out so the search runs clean, and goes back if
    # that search raises. See the restore in the per-title handler for why.
    rejudged = {k: cache.pop(k) for k in rejudge}
    if rejudge or held:
        print(f"[enrich] re-judging {len(rejudge)} title(s) on new title or year evidence "
              f"({matched} exact match(es), {len(rejudge) - matched} unmatched), "
              f"{held} wait for the next run: " + " | ".join(rejudge))

    todo, refreshes, deferred = due(titles, cache, today)
    settled = set()          # scheduled refreshes that came back with rating/vote data
    looked = rechecked = pending = 0
    weak, thin = [], []      # popularity fallbacks, and ratings held back by MIN_VOTES
    en_tried = 0             # en-US second searches, one per title the fi-FI pass missed
    en_settled, en_differs = [], []
    offyear = []             # exact titles refused on the published year
    ties = []                # several films of that title and year; none trusted
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
                fact = facts.get(k) or {"o": "", "y": ""}
                for cand in queries(display or k, alias, fact["o"]):
                    # The year filters the search, except on an alias string: an alias
                    # exists because the search needs a hand, and "Cars" with a reissue
                    # year returned "The Boy Who Counted Cars" in the Finnkino pass.
                    year = fact["y"] if cand != str(alias or "") else ""
                    hits = search(cand, year, th)
                    hit, exact = (pick(hits, cand, year, fact["o"]) if hits
                                  else (None, False))
                    if year and not exact:
                        # Nothing of that year matched exactly. Ask without the filter:
                        # TMDB's primary release year can sit a year off the published
                        # one, and pick() still holds the hit to the year, so a same-
                        # titled film from another decade comes back as weak, never as
                        # the match.
                        alt = search(cand, "", th)
                        if alt:
                            a_hit, a_exact = pick(alt, cand, year, fact["o"])
                            if a_exact or hit is None:
                                hit, exact = a_hit, a_exact
                    if hit and exact:
                        mid = hit.get("id")
                        poster = hit.get("poster_path") or poster
                        exact_id = True
                        break
                    if hit and fallback is None:
                        fallback = hit
                    time.sleep(0.2)
                else:
                    # **One en-US search, and only here.** The fi-FI pass matched no
                    # candidate exactly, which is the only state this can improve.
                    # `language` decides what `title` comes back as, so a cinema that
                    # publishes TMDB's own English title can never match under fi-FI where
                    # TMDB holds no Finnish one. Decided 2026-09-19 with these bounds: it
                    # fills an empty or weak slot, it never replaces a cached id -- this
                    # whole branch is inside `if not mid`, so there is none to replace --
                    # and an id that disagrees with the weak candidate is named for the
                    # alias file rather than published. One request per title, counted.
                    en_cand = queries(display or k, alias, fact["o"])[0]
                    try:
                        en_hits = search(en_cand, fact["y"], th, lang="en-US")
                    except Exception:
                        en_hits = []
                    en_tried += 1
                    en_hit, en_exact = (pick(en_hits, en_cand, fact["y"], fact["o"])
                                        if en_hits else (None, False))
                    if en_exact and en_hit:
                        if fallback is None or fallback.get("id") == en_hit.get("id"):
                            mid = en_hit.get("id")
                            poster = en_hit.get("poster_path") or poster
                            exact_id = True
                            en_settled.append(f"{display or k} -> {en_hit.get('title')}")
                            fallback = None          # settled, so not a weak entry
                        else:
                            # Two defensible ids and nothing automatic to choose between
                            # them. The weak one stands and the disagreement is named.
                            en_differs.append(
                                f"{display or k}: fi-FI {fallback.get('title')} "
                                f"({fallback.get('id')}) vs en-US {en_hit.get('title')} "
                                f"({en_hit.get('id')})")
                    if fallback is not None:
                        mid = fallback.get("id")
                        poster = fallback.get("poster_path") or poster
                        exact_id = False
                        hy = release_year(fallback)
                        titled = any(norm(fallback.get(f)) == norm(c) for f in ("title", "original_title")
                                     for c in queries(display or k, alias, fact["o"]))
                        if fact["y"] and titled and hy and not plausible(hy, fact["y"]):
                            offyear.append(f"{display or k} ({fact['y']}) -> "
                                           f"{fallback.get('title')} ({hy})")
                        elif fact["y"] and titled:
                            ties.append(f"{display or k} ({fact['y']}) -> "
                                        f"{fallback.get('title')} ({hy or '?'})")
                        else:
                            weak.append(f"{display or k} -> {fallback.get('title')}")
            # Seeded from the cache, not from "". A detail request that fails must leave
            # the text this entry already had: writing "" would empty the cache's copy of
            # a synopsis nothing else can put back, and the pass would report a rating as
            # re-read while carrying the old figures. Only a response that arrived
            # replaces either slot, so a film whose overview TMDB really has emptied
            # still clears.
            syn_fi = (c.get("fi") or "") if isinstance(c, dict) else ""
            syn_en = (c.get("en") or "") if isinstance(c, dict) else ""
            # Same seeding rule as the synopses: a detail request that fails leaves the
            # year the entry already had rather than blanking it.
            ry = (c.get("ry") or "") if isinstance(c, dict) else ""
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
                    # release_date is the film's own first release and is the same in
                    # both language responses, so this costs no request of its own.
                    ry = release_year(d) or ry
                    # Both fields or neither. A response carrying only `vote_count` used
                    # to set the rating to 0 over the top of a real one and then stamp the
                    # entry as read; one carrying only `vote_average` was not noticed at
                    # all. Either way it is not the pair the entry is parked on.
                    fresh_n = refresh.numeric(d.get("vote_count"))
                    fresh_r = refresh.numeric(d.get("vote_average"))
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
            # for ever -- see refresh.py.
            attempt = today if mid else ((c.get("a") or "") if isinstance(c, dict) else "")
            # `o` and `y` are the evidence the id was judged on, so reconsider() can
            # tell a match made before the cinema published them from one made after.
            # `q` is the *search string* it was judged on, normalised: the evidence
            # this side owns. A strand added to strands.py changes clean() for a title
            # the cinema has not touched, and without this the entry keeps its daily
            # retry and the new strand does not apply until tomorrow.
            #
            # norm() around it, not the bare cleaned string, and that is load-bearing.
            # One cache key can be reached by several spellings -- 34 keys in the
            # committed data, "HETKI ENNEN VALOA" beside "Hetki ennen valoa" -- and
            # gather() keeps whichever show it met first, so a bare comparison flips on
            # 26 of them every pass and re-judges settled matches for ever. Measured
            # 2026-09-19 before this was written. Normalising compares what the search
            # would actually ask for, which is the question.
            fact = facts.get(k) or {"o": "", "y": ""}
            cache[k] = {"r": shown, "n": votes, "v": yt, "x": bool(mid) and exact_id,
                        "g": gids, "i": mid or "", "c": stamp, "a": attempt,
                        "fi": syn_fi, "en": syn_en, "p": poster,
                        "o": norm(fact["o"]), "y": fact["y"], "ry": ry,
                        "q": norm(clean(display or k))}
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
            # A re-judged entry was deleted before its search so the search would not read
            # the judgement it is replacing. If that search raised -- a TMDB 429, a
            # timeout -- the key is simply absent, and an absent key is not a neutral
            # state: `trusted(None)` is False, so the pass below strips the id, the
            # poster, the rating and the trailer off every showtime of that film and it
            # renders an initials tile until a later run succeeds. Putting the old
            # judgement back keeps it published; `reconsider()` sees the same differing
            # evidence next run and tries again, so nothing is lost but a day.
            #
            # **Only this drop site is restored.** The old-picker sweep and the alias
            # override above remove a judgement that is *known wrong*, and putting one of
            # those back after a failed search would republish the wrong film for a run.
            # Unpublishing is the safer failure there and is left alone.
            if k in rejudged and not replaced:
                cache[k] = rejudged[k]

    flush(cache, today)

    # After the loop, because whether a scheduled refresh re-read anything is
    # only known once its detail request has answered. A failure here is not an error --
    # the entry keeps its figures and its date and comes back to the head of the queue --
    # but a run where every refresh fails must not read like a run where every one
    # worked. Deferred is what the budget left for the next pass; a ceiling nobody can
    # see reads as "everything is current".
    line = refresh.report(len(refreshes), len(settled), deferred)
    if line:
        print(f"[enrich] {line}")

    # A first pass over every area file, so a rating published at one chain can fill a
    # blank at another. Only exact matches take part, on both sides.
    docs = {}
    donors = []
    for p in files:
        try:
            docs[p] = json.loads(p.read_text())
        except Exception:
            continue
        for s in docs[p].get("shows", []):
            c = cache.get(norm(s.get("title")))
            if isinstance(c, dict) and c.get("x") and c.get("i"):
                donors.append({**s, "tmdbId": c["i"]})
    table, clashes = shared_ratings(donors)
    for d in clashes:
        values = " ".join(f"{r}={'/'.join(ps)}" for r, ps in d["values"].items())
        print(f"[enrich] rating disagreement, nothing shared: {d['title']} "
              f"(tmdb {d['tmdbId']}) {values}")
    shared_by_key = {}          # films-extra key -> the entry it publishes
    filled = 0

    touched = 0
    for p, doc in docs.items():
        changed = False
        for s in doc.get("shows", []):
            # Anything this pass wrote before goes first, ahead of the cache guard. A show
            # whose cache entry has since gone, because its title changed or the entry was
            # pruned, still reaches `continue` below, and clearing after that point would
            # never run: the loan would sit there with nothing left to justify it.
            was = ((s.get("rating") or ""), s.get("rsrc"))
            if s.get("rsrc") == "shared":
                s["rating"] = ""
                s.pop("rsrc", None)
            c = cache.get(norm(s.get("title")))
            if not trusted(c):
                # A weak candidate, a title that matched nothing, or no entry at all:
                # nothing is written, and what an earlier run wrote from a weak candidate
                # comes off, run.py having carried it here from the previous file.
                if unpublish(s, c):
                    changed = True
                if ((s.get("rating") or ""), s.get("rsrc")) != was:
                    changed = True
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
            if publish_poster(s, c):
                changed = True
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
            # The film's own release year. Same gate as `tmdbId` above, because a weak
            # candidate's year belongs to a different film; see PUBLISHED for the three
            # other years this must not be.
            if c.get("x") and c.get("ry") and s.get("oyear") != c["ry"]:
                s["oyear"] = c["ry"]; changed = True
            # A classification another chain published for the same film, filling a blank
            # only. `rsrc` is provenance: the UI shows a borrowed rating exactly like a
            # published one, and nothing else can tell them apart afterwards.
            #
            # Decided from scratch every run. A value this pass wrote earlier was cleared
            # above, so what is left in `rating` is the cinema's own and a loan that no
            # longer qualifies simply does not come back. Without that it outlives its
            # donor.
            borrowed = None
            if c.get("x") and c.get("i"):
                borrowed = borrowed_rating({**s, "tmdbId": c["i"]}, table)
            if borrowed:
                s["rating"], s["rsrc"] = borrowed, "shared"
            if ((s.get("rating") or ""), s.get("rsrc")) != was:
                changed = True
            if borrowed:
                filled += 1
                shared_by_key[norm(s.get("title"))] = {"kr": borrowed,
                                                       "krs": table[c["i"]]["sources"]}
        if changed:
            common.write_json(p, doc)
            touched += 1
    if filled or clashes:
        print(f"[enrich] shared classification: {filled} blank rating(s) filled from "
              f"{len(shared_by_key)} title(s), {len(clashes)} disagreement(s)")
    merge_shared(shared_by_key, today)

    # Name the titles that found nothing: these are the candidates for tmdb-aliases.json.
    missing = sorted(display for k, display in titles.items()
                     if not (cache.get(k) or {}).get("i"))
    if missing:
        print(f"[enrich] no TMDB match ({len(missing)}): " + " | ".join(missing))
    # A weak match publishes nothing (see trusted()) and is listed here so it can be
    # verified and aliased; a thin one is a rating hidden on purpose. Both are for
    # reading, not for acting on automatically.
    if weak:
        print(f"[enrich] weak match, no exact title ({len(weak)}): " + " | ".join(sorted(weak)))
    if en_tried:
        print(f"[enrich] en-US second search: {en_tried} title(s) asked, "
              f"{len(en_settled)} settled, {len(en_differs)} disagreed with the fi-FI "
              f"candidate and were left for the alias file")
    if en_settled:
        print(f"[enrich] settled on the English title ({len(en_settled)}): "
              + " | ".join(sorted(en_settled)))
    if en_differs:
        print(f"[enrich] en-US names a different film ({len(en_differs)}): "
              + " | ".join(sorted(en_differs)), file=sys.stderr)
    if offyear:
        print(f"[enrich] year mismatch, exact title refused ({len(offyear)}): "
              + " | ".join(sorted(offyear)))
    if ties:
        print(f"[enrich] several films match the title and year, none trusted ({len(ties)}): "
              + " | ".join(sorted(ties)))
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
