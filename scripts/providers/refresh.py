"""When a cached TMDB rating is due to be read again. Pure; no I/O, no network.

Two caches hold ratings. `data/tmdb.json` is keyed by Finnkino's filmId and written by
scripts/fetch_data.py; `data/tmdb-titles.json` is keyed by a normalised title and written
by providers/enrich_tmdb.py. Deciding when to re-read one is the same question in both,
and it was answered twice -- which is how the same defect came to sit in both files and
be fixed in one. It is answered here now.

The two differ in exactly one thing, so that is the one thing they pass in: what a
complete entry looks like. The Finnkino cache carries no synopsis and no poster, because
Finnkino publishes both itself, so requiring them there would mark every entry incomplete
for ever. Each pass keeps its own schema contract and hands it over as `complete`.

The rule, and why each half of it is there:

  * A rating goes stale. Finding a trailer used to end an entry's life -- the skip was
    `v or c == today`, so a film with one was never looked at again and its rating and
    vote count froze. Age decides instead, against `c`.
  * `c` is when TMDB last answered with a usable rating and vote count, not when it was
    last asked. An entry whose detail request failed keeps the date it had, so it stays
    due rather than being parked for a week on figures nothing re-read.
  * `a` is when a refresh was last *attempted*, and it is what the queue sorts on.
    Ordering on `c` would starve it: an id that can never be read keeps `c` where it is,
    ages further every day and outranks everything else for ever, so a dozen of them
    would hold the whole budget on every run while the rest of the backlog never moved.
    Least recently attempted first, never attempted ahead of all of them, so it rotates.
  * The budget bounds the catch-up. Without it the first run after an age rule lands
    re-reads the whole backlog at once, stamps it all with one date, and it comes due
    together again a week later, for ever.

`a` is deliberately not part of any `complete` predicate: it is scheduling bookkeeping
rather than anything a client reads, and requiring it would cost a full re-check pass to
introduce -- absence already means "never attempted", which is the state that sorts first.
"""
import datetime
import os

# How long a cached rating may stand, and how many stale ones one pass will re-read.
#
# In the steady state the ceiling is not reached: ~96 entries at a seven-day age come due
# at about fourteen a day, which is roughly two per run. It is a bound on the catch-up
# rather than a running cost. Overridable in the style of KINO_PAGE_BUDGET.
RATING_MAX_AGE = int(os.environ.get("KINO_TMDB_MAX_AGE") or 7)
REFRESH_BUDGET = int(os.environ.get("KINO_TMDB_REFRESH") or 12)


def numeric(v):
    """A usable number from a TMDB field. -> the value, or None.

    Zero is a value: a film nobody has voted on comes back with `vote_count` 0 and
    `vote_average` 0.0, and reading that is a successful read. Absent, null or a string
    is not, and must not become a zero written over a rating that was real.
    """
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def age_days(entry, today, field="c"):
    """Days since one of this entry's dates. -> int, or None if there is not one.

    None is not zero. An entry with no `c` was written by a shape neither pass produces
    any more and is the oldest thing there is; an entry with no `a` has never been
    attempted, which puts it at the head of the queue.
    """
    try:
        return (datetime.date.fromisoformat(today)
                - datetime.date.fromisoformat(entry.get(field) or "")).days
    except (TypeError, ValueError):
        return None


def due(keys, cache, today, complete, max_age=None, budget=None):
    """Which cached entries a pass should fetch. -> (keys, refreshes, deferred).

    `keys` is what the pass has work for -- normalised titles for one caller, Finnkino
    film ids for the other -- and `complete` says what a fully-formed entry looks like in
    that cache. `refreshes` comes back as keys rather than a count so the caller can
    report what became of each: a scheduled refresh whose detail request fails is not a
    refreshed rating. `deferred` is what the budget left for the next run, so a caller can
    say so rather than trimming silently.

    Four states:

      * not cached -- fetched.
      * cached in an older shape, missing a field -- fetched, so adding a field costs one
        pass rather than a cache wipe.
      * complete with no trailer -- once a day, looking for a trailer that may not have
        existed when the film opened.
      * complete with a trailer -- re-read once `c` is `max_age` days old, at most
        `budget` a run, least recently attempted first.
    """
    max_age = RATING_MAX_AGE if max_age is None else max_age
    budget = REFRESH_BUDGET if budget is None else budget
    work, stale = set(), []
    for k in keys:
        c = cache.get(k)
        if not complete(c):
            work.add(k)
            continue
        age = age_days(c, today)
        if not c.get("v"):
            # Read today already is the only reason to skip.
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


def report(scheduled, settled, deferred, budget=None):
    """The one line a pass prints about its rating refreshes. -> str, or "" if silent.

    Printed after the loop, because whether a scheduled refresh re-read anything is not
    knowable before it. A failure here is not an error -- the entry keeps its figures and
    its date and comes back round -- but a run where every refresh failed must not read
    like a run where every one worked, and a ceiling nobody can see reads as "everything
    is current".
    """
    if not scheduled and not deferred:
        return ""
    budget = REFRESH_BUDGET if budget is None else budget
    return (f"rating refresh: {scheduled} scheduled, {settled} re-read, "
            f"{scheduled - settled} failed and still due, {deferred} deferred "
            f"(budget {budget})")
