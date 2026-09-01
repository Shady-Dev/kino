#!/usr/bin/env python3
"""Generic provider runner.

    python3 scripts/providers/run.py biorex nexxo etiketti ...
    python3 scripts/providers/run.py --where cloud      # module list from the registry
    python3 scripts/providers/run.py --where local      # the three modules with local sites

Replaces the five near-identical fetch_*.py orchestrators. Every adapter module
exposes exactly two things:

    SITES             list of sites. One module can serve several providers
                      (nexxo -> kinoset, etiketti -> kotkanleffat), so the provider
                      id lives on the site, not on the module:
                        {provider, label, venues: [{id, name, short, city}, ...]}
    fetch_site(site)  -> {venue_id: [show, ...]}. A failed venue may be absent.

Written per site: data/area-{venueId}.json and data/venues-{provider}.json.

A venue with no showtimes keeps its previously committed area file, so the app does
not go empty on a parse regression; a venue that never had a file gets an empty one,
so the picker never links to a 404 (same two rules as fetch_data.py for Finnkino).
venues-{provider}.json always lists **every** venue of the site: it is what the client
builds its picker from, so dropping a failed venue would make its still-committed area
file unreachable while the health line stays green — the silent failure this pipeline
is designed against.

A venue that keeps its previous file is recorded as *stale*, not failed: at this layer
an empty parse and a cinema with nothing on today both arrive as `[]`, so they cannot be
told apart, and treating either as a failure would fail the run on an ordinary closure.
A venue with no shows and none before it splits two ways. If the adapter's module sets
`EMPTY_VENUES_CONFIRMED` and reported the venue explicitly, its emptiness is positive
evidence — the upstream answered in schema and listed nothing — and the venue is
*pending*: a programme that has not started, quiet on the health line. Otherwise it is
*unverified*: never any data, and "a venue added before its programme is published" and
"one whose parse has never worked" are not distinguishable here, so it must stay visibly
degraded. The file therefore carries `status`, `stale`, `unverified`, `pending` and
`oldest`, and `oldest` is what the health line ages on: a
provider is as fresh as its weakest venue, but a venue that never had data does not drag
that down. Only a site where *every* venue came back empty is a failure, since nothing
else would notice that.

Sites on different hosts are fetched at the same time, sites on the same host one after
the other. The pacing inside an adapter's fetch_site is what a cinema experiences and is
untouched by this; serialising *across* unrelated hosts was never a decision, only how
the loop was written when a module had two sites. See host_groups and MAX_HOSTS.
"""
import concurrent.futures
import datetime
import importlib
import json
import os
import pathlib
import sys
import threading
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common              # noqa: E402
import registry            # noqa: E402
import strands             # noqa: E402
import synmerge            # noqa: E402

OUT = pathlib.Path("data")


def previous(path):
    """What is already committed for a venue. -> (generated, show count).

    The count is the part that matters. `path.exists()` conflates two different states:
    a venue holding real older data, and a venue whose only file is the empty one written
    so the picker would not link to a 404. Keying on existence marks the second as
    "keeping previous data" from its second run onward, which claims data that was never
    there and drags the provider's `oldest` down forever.

    Unreadable is unknown rather than an error: a torn or hand-edited file must not stop
    the run publishing showtimes.
    """
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc.get("generated") or "", len(doc.get("shows") or [])
    except Exception:
        return "", 0


def generated_of(path):
    """The `generated` already committed for a venue. -> str, or '' if unreadable."""
    return previous(path)[0]


# What the TMDB pass stamps onto a show and an adapter cannot know. `gids` is the one
# that matters most: it drives the genre names the client renders and the kids filter's
# id rule, so losing it is not just a missing score ring.
ENRICHED = ("tmdbId", "tmdb", "votes", "tr", "gids")


def enrichment_of(path):
    """Previously committed enrichment, keyed by title. -> {title: {field: value}}.

    A run rewrites a venue file wholesale from what the adapter returned, so every
    enrichment field in the old file is dropped. In the cloud that is invisible, because
    enrich_tmdb runs straight afterwards and puts them back. On the local half nothing
    does: Kino Engel and Kino Akseli lose their ratings, trailers and genre ids on every
    run and get them back only when the next cloud run lands, and the same happens to
    anyone running run.py by hand -- the trap IDEAS already records as having cost 1201
    showtimes their tmdbId.

    Keyed by title because that is what the TMDB pass itself keys on, and because these
    are properties of the *film*, not of the screening. Carried values are a floor, never
    an override: `setdefault` leaves anything the adapter supplied alone, and the next
    enrichment pass overwrites the lot with fresh figures.
    """
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for s in doc.get("shows") or []:
        title = s.get("title")
        if not title or title in out:
            continue
        keep = {k: s[k] for k in ENRICHED if s.get(k) is not None and s.get(k) != ""}
        if keep:
            out[title] = keep
    return out


def run_site(mod, site, now, order=0):
    """Fetch and write one site. -> (venues_written, showtimes). Raises on fetch failure.

    `order` is the site's index in the module's SITES, and only synmerge uses it: two
    sites publishing different synopses for one film are decided by SITES order rather
    than by which host answered first. A caller that fetches one site alone can leave it
    at 0.
    """
    label = site.get("provider") or mod.__name__
    per_venue = mod.fetch_site(site)
    # A strand prefix belongs in `method`, not in the title: left there it fragments the
    # film, blocks the TMDB match and gives every film in the strand the same fallback
    # tile. Applied centrally so a new adapter gets it without knowing it exists.
    split = sum(bool(strands.apply(s)) for shows in per_venue.values() for s in shows)
    if split:
        print(f"[{label}] strand prefix split off {split} showtimes")
    synmerge.merge(OUT, per_venue, label, order)

    live = total = 0
    stale = []            # kept its previous file: the data is real, just older
    unverified = []       # never any data, emptiness unconfirmed: parse rot looks the same
    pending = []          # never any data, and the adapter confirmed the programme is empty
    for v in site["venues"]:
        shows = per_venue.get(v["id"]) or []
        path = OUT / f"area-{v['id']}.json"
        prev_gen, prev_shows = previous(path)
        if not shows and prev_shows:
            stale.append(v["id"])
            print(f"[{label}] {v['name']}: no showtimes, keeping previous data "
                  f"from {prev_gen or 'an unknown time'}", file=sys.stderr)
            continue
        if not shows:
            # Never produced a showtime. Two different states hide here, and only the
            # adapter can tell them apart: a module that sets EMPTY_VENUES_CONFIRMED
            # promises that a venue it reported with an empty list is *known* empty --
            # the upstream answered in schema and listed nothing -- so that venue is
            # pending, a programme that has not started. Anything else stays
            # unverified: "added before its programme is published" and "a parse that
            # has never worked" are not distinguishable here, so it is recorded rather
            # than judged and must not read as healthy. Both still get the empty file,
            # so the picker does not link to a 404, and both are stamped fresh so a
            # venue with no data cannot drag the provider's `oldest` down.
            if getattr(mod, "EMPTY_VENUES_CONFIRMED", False) and v["id"] in per_venue:
                pending.append(v["id"])
                print(f"[{label}] {v['name']}: no programme yet (adapter confirmed "
                      f"the venue empty); publishing an empty file", file=sys.stderr)
            else:
                unverified.append(v["id"])
                print(f"[{label}] {v['name']}: no showtimes and none previously; "
                      f"publishing an empty file", file=sys.stderr)
        shows.sort(key=lambda s: s["start"])
        synmerge.strip_helpers(shows)
        # Read before the write, so a venue keeps its ratings, trailers and genre ids
        # rather than losing them for however long it takes the next enrichment pass to
        # run. Never overrides what the adapter itself produced.
        carried = enrichment_of(path)
        for sh in shows:
            for field, val in (carried.get(sh.get("title")) or {}).items():
                sh.setdefault(field, val)
        days = sorted({s["start"][:10] for s in shows if s.get("start")})
        common.write_json(path,
            {"generated": now, "dates": days, "horizon": days[-1] if days else "",
             "shows": shows})
        if shows:
            live += 1
            total += len(shows)
            print(f"[{label}] {v['name']}: {len(shows)} showtimes, {len(days)} dates")

    # Every venue, not just the fresh ones — see the module docstring. Written only
    # when at least one venue produced shows, so a fully dead site does not stamp a
    # fresh `generated` and green the health line on total failure.
    #
    # `oldest` is the honest number and `generated` was not. `generated` says when this
    # file was written, which is now; the health line was reading it and calling the
    # whole provider fresh while one of its venues sat on week-old data. Taken from the
    # files on disk rather than from `stale`, so it cannot drift from what was actually
    # written. Same rule the combined city view already applies: a group is as fresh as
    # its weakest member.
    if live:
        stamps = [generated_of(OUT / f"area-{v['id']}.json") or now
                  for v in site["venues"]
                  if (OUT / f"area-{v['id']}.json").exists()]
        common.write_json(OUT / f"venues-{site['provider']}.json",
            {"generated": now, "oldest": min(stamps) if stamps else now,
             "status": "partial" if (stale or unverified) else "ok",
             "stale": stale, "unverified": unverified, "pending": pending,
             "provider": site["provider"],
             "venues": [{k: v[k] for k in ("id", "name", "short", "city")}
                        for v in site["venues"]]})
    return live, total, stale, unverified, pending


# How many hosts this end reads at the same time. Not a rate limit at any cinema: the
# sleep inside each adapter's fetch_site is that, and host_groups below keeps every site
# on one host in a single thread so that sleep still describes what the host sees. What
# this number bounds is this end -- open sockets, and the response bodies in flight, at
# most MAX_HOSTS * common.MAX_BODY.
#
# 8 is twice the four vCPUs an ubuntu-latest runner has, which is the usual shape for a
# pool that spends most of its time waiting and parses HTML in between. It caps bodies in
# flight at 160 MB against the runner's 16 GB, covers Nexxo's six host groups outright,
# and takes eTiketti's cloud half -- 16 of its 17 sites, since Joutsan Kino is routed
# local -- in two waves instead of sixteen sites in a row. "As many as there are sites"
# was rejected as a default: it would raise the ceiling every time a cinema is added,
# with nobody deciding to.
#
# KINO_MAX_HOSTS overrides it, in the style of KINO_PAGE_BUDGET and KINO_MAX_BODY. 1 is
# the sequential path this replaced, and the tests use it to show that path still writes
# the same files and prints the same summary line.
MAX_HOSTS = int(os.environ.get("KINO_MAX_HOSTS") or 8)


def host_of(site):
    """The host a site is read from. -> netloc, or "" when the adapter holds it.

    `base` is where the API lives; `site`, where a module carries one, is where a visitor
    is sent. Bio Säde is the case: its showtimes come from kinohirvi.fi and its ticket
    links go to biosade.fi. The pacing key is the host actually read, so it is `base` and
    never `site`.

    A site with no `base` keeps its host inside the adapter, out of reach from here.
    Those all answer "" and so share one group, which reads them one after the other
    rather than assuming they are different cinemas. Treating an unknown host as its own
    would put two requests at one server at once; treating two servers as one costs
    seconds.
    """
    return urllib.parse.urlsplit(site.get("base") or "").netloc


def host_groups(sites):
    """Sites grouped by the host they are read from. -> [[(index, site), ...], ...].

    Groups in the order their host is first seen and members in SITES order, so a run
    reads the same way every time.

    This is the unit the pool works in, and the host is the key rather than the site
    because the data says so today, not hypothetically: kinoaurora.fi serves both
    kinoaurora and kinometso, and kinohirvi.fi serves both kinohirvi and biosade. Keyed
    on the site, two of Nexxo's eight would be read concurrently against one cinema's
    server at twice the rate its adapter paces for -- which is the courtesy the whole
    access story rests on. One thread per host is what keeps that pacing accurate.
    """
    groups = {}
    for i, site in enumerate(sites):
        groups.setdefault(host_of(site), []).append((i, site))
    return list(groups.values())


class _Buffer:
    """One captured stream: quacks like the real one and files its writes with `rec`."""

    def __init__(self, rec, real):
        self.rec, self.real = rec, real

    def write(self, text):
        return self.rec.write(self, text)

    def flush(self):
        self.real.flush()

    def __getattr__(self, name):
        return getattr(self.real, name)


class Recorder:
    """Holds a pooled run's output back so the committed log still reads in site order.

    Sites finish out of order, so printing as they go shuffles `[provider] Venue: N
    showtimes` into a list nobody can read downwards. Each worker's output is collected
    instead and replayed when its turn comes, which leaves every site's lines contiguous
    and in SITES order however long that site took.

    Both streams, not stdout alone: run_site reports stale, pending and unverified venues
    on stderr and the workflow merges the two (`> run-$m.log 2>&1`), so capturing one of
    them would move half the lines. They share one list per thread, so the order the two
    were written in is the order they come back in. That also changes what a committed
    log looks like: today stdout is block-buffered into a redirected log while stderr is
    line-buffered, so a stderr line written last can land first in the file, which is why
    run-nexxo.log opens with kinometso's empty-venue notice from the eighth site of eight.
    """

    def __init__(self):
        self._local = threading.local()
        self.out = _Buffer(self, sys.stdout)
        self.err = _Buffer(self, sys.stderr)

    def install(self):
        """Stand in for sys.stdout and sys.stderr. A thread that is not capturing writes
        straight through, so anything printed outside a worker is unaffected."""
        sys.stdout, sys.stderr = self.out, self.err

    def remove(self):
        sys.stdout, sys.stderr = self.out.real, self.err.real

    def capture(self):
        """Start collecting this thread's writes. -> the list they land in."""
        self._local.chunks = chunks = []
        return chunks

    def release(self):
        self._local.chunks = None

    def write(self, buf, text):
        chunks = getattr(self._local, "chunks", None)
        if chunks is None:
            return buf.real.write(text)
        chunks.append((buf, text))
        return len(text)

    def replay(self, chunks):
        """Write one site's captured output back out, in the order it was written.

        Both real streams are flushed at every switch between them, and before the first
        write, because once the workflow merges them they are two buffers over one file
        descriptor: without the flushes the file would be ordered by whichever buffer
        filled up first, which is the reordering this class exists to remove.
        """
        self.out.real.flush()
        self.err.real.flush()
        buf = None
        for b, text in chunks:
            if buf is not None and b is not buf:
                buf.real.flush()
            buf = b
            buf.real.write(text)
        if buf is not None:
            buf.real.flush()


def run_sites(mod, sites, now, workers=None):
    """Fetch a module's sites, hosts at once and each host's sites in order.

    Yields (label, result, error) in SITES order, `result` being run_site's tuple or None
    when `error` holds what it raised. Yielded one at a time, after that site's output has
    been replayed, so the caller's own line about a site -- `no programme published`,
    `FAILED` -- still lands inside that site's block in the log.

    The exception travels back rather than out. One site failing has never stopped the
    rest of a run, and in a pool a raise would take its host group's remaining sites with
    it as well.
    """
    workers = MAX_HOSTS if workers is None else workers
    synmerge.reset()          # this module's sites decide their own synopsis winners
    groups = host_groups(sites)
    slots = [None] * len(sites)
    done = [threading.Event() for _ in sites]
    fatal = []                # a BaseException out of a worker, re-raised by the reader
    rec = Recorder()

    def read_host(group):
        """One host's sites, one after the other.

        An ordinary failure is caught per site and travels back as that site's error,
        which is the isolation a pool needs: one cinema refusing must not take the rest
        of its host with it, let alone the run.

        Anything that is not an ordinary failure -- a `SystemExit` out of adapter code --
        ended a sequential run and has to end this one. Left alone it would not: the
        thread dies, `ThreadPoolExecutor` puts the exception on a future nobody reads,
        and the run carries on and publishes. So it is recorded here and re-raised by the
        reader, which is the thread a sequential run would have raised it on. Recorded
        rather than reported: a `SystemExit` is not a cinema that could not be fetched and
        must not be written into the log as one.

        The two `finally` blocks stop the reader waiting on a site that will never
        report. The inner one releases a site once it has an outcome; the outer one
        releases everything still held, and runs *after* `fatal` is recorded, so the
        reader always sees the exception before it can reach an empty slot.
        """
        try:
            for i, site in group:
                label = site.get("provider") or mod.__name__
                chunks = []
                try:
                    chunks = rec.capture()
                    slots[i] = (label, run_site(mod, site, now, i), None, chunks)
                except Exception as e:
                    slots[i] = (label, None, e, chunks)
                finally:
                    rec.release()
                    # Set only once there is an outcome to read. A site whose thread is
                    # being unwound has none yet, and releasing the reader first would
                    # hand it an empty slot before `fatal` was there to be seen.
                    if slots[i] is not None:
                        done[i].set()
        except BaseException as e:          # noqa: BLE001 -- forwarded, not handled
            fatal.append(e)
        finally:
            for i, _ in group:
                done[i].set()

    rec.install()
    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, min(workers, len(groups) or 1)))
    try:
        for group in groups:
            pool.submit(read_host, group)
        for i in range(len(sites)):
            done[i].wait()
            if fatal:
                # Raised on this thread, which is where a sequential run would have
                # raised it. The `finally` below has already cancelled what was queued
                # and put the streams back by the time it leaves here.
                raise fatal[0]
            label, result, error, chunks = slots[i]
            rec.replay(chunks)
            yield label, result, error
    finally:
        # cancel_futures, so a run being torn down -- Ctrl-C, a closed laptop, a caller
        # that stops reading -- stops asking hosts it has not reached yet. The hosts
        # already in flight are still waited for: a thread part-way through writing a
        # venue file has to finish, and `wait=True` is what makes the atomic write mean
        # something. Nothing is cancelled on the normal path, where every group has run
        # by the time the drain ends.
        pool.shutdown(wait=True, cancel_futures=True)
        rec.remove()


def half_of(argv):
    """Which half of the pipeline is running -> "cloud", "local" or "all".

    Routing used to be per *module*, so a single site that has to be fetched from an
    ordinary connection dragged its whole adapter with it: marking one eTiketti provider
    local would have put all sixteen sites in both halves, with two writers on the same
    files. That cost Joutsan Kino, which parses fine at home and answers a runner with a
    Cloudflare 403.

    Derived rather than passed, because the cloud workflow calls this per module with a
    bare name and adding a flag there is a change to a file this could not touch. Actions
    always sets GITHUB_ACTIONS and nothing else here does, so the workflow keeps working
    unchanged and starts skipping the sites it was never able to fetch.

    The default off Actions is "all", not "local": `run.py etiketti` on a laptop is how
    an adapter gets exercised, and silently fetching one site of fifteen would make that
    useless. The local *wrapper* therefore has to be explicit -- `--where local` -- which
    is also what keeps one writer per provider file.
    """
    for flag in ("--half", "--where"):
        if flag in argv:
            return argv[argv.index(flag) + 1]
    return "cloud" if os.environ.get("GITHUB_ACTIONS") else "all"


def module_names(argv):
    """The module names in argv -> list.

    A flag's *value* is not a module name. Dropping only the flags left "local" behind
    for `run.py etiketti --half local`, which run.py then tried to import: "[local]
    unusable: No module named 'local'", counted as a failure, and printed the word in
    the run summary. Caught by running it rather than by reading it.
    """
    skip = {argv.index(f) + 1 for f in ("--half", "--where") if f in argv}
    return [a for i, a in enumerate(argv) if not a.startswith("-") and i not in skip]


def sites_for(mod, half):
    """The sites in this module that belong to `half`, in SITES order.

    A site whose provider has no registry entry is kept rather than dropped: that is a
    misconfiguration, and tests/test_registry_sites.py is where it should be reported,
    not here by silently fetching nothing.
    """
    if half == "all":
        return list(mod.SITES)
    out = []
    for site in mod.SITES:
        p = registry.by_id(site.get("provider") or "")
        if p is None or p.get("where") == half:
            out.append(site)
    return out


def summary_line(names, venues, shows, partial, pendings, empty, failures):
    """The run's one-line verdict, in the committed log's fixed vocabulary.

    Pending is counted here even though it is neither a failure nor a partial state:
    the summary is what a sweep of the log reads, and a venue publishing nothing must
    be visible in it rather than looking like a venue that does not exist.
    """
    return (f"[run] {' '.join(names)}: {venues} venues, {shows} showtimes, "
            f"{sum(len(i) for _, i, _ in partial)} stale, "
            f"{sum(len(u) for _, _, u in partial)} unverified, "
            f"{sum(len(i) for _, i in pendings)} pending, "
            f"{len(empty)} with no programme, {failures} failures")


def main(argv) -> int:
    half = half_of(argv)
    names = (registry.modules(argv[argv.index("--where") + 1])
             if "--where" in argv else module_names(argv))
    if not names:
        print("usage: run.py <module>... [--half cloud|local|all] | "
              "run.py --where cloud|local", file=sys.stderr)
        return 2

    OUT.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    venues = shows = failures = 0
    partial = []          # (provider, [venue ids]) for every site that kept old data
    pendings = []         # (provider, [venue ids]) whose adapter confirmed no programme
    empty = []            # sites whose listing loaded and had no films on it
    skipped = []          # modules with no sites for this half, which is not a problem

    for name in names:
        try:
            mod = importlib.import_module(name)
            mod.SITES          # a module without it is unusable, and says so here
        except Exception as e:
            print(f"[{name}] unusable: {e}", file=sys.stderr)
            failures += 1
            continue
        sites = sites_for(mod, half)
        if not sites:
            # Not a failure: the module's sites all belong to the other half. The cloud
            # workflow iterates every cloud module, so this is the normal answer for a
            # module whose only local site is fetched at home.
            print(f"[{name}] no sites for the {half} half")
            skipped.append(name)
            continue
        for label, result, error in run_sites(mod, sites, now):
            if isinstance(error, common.EmptyProgramme):
                # Not a failure, and deliberately still noisy: a cinema with nothing on
                # is a fact worth seeing in the committed log, and one that stays empty
                # for weeks is worth chasing even though no run went red over it.
                print(f"[{label}] no programme published: {error}")
                empty.append(label)
                continue
            if error is not None:
                print(f"[{label}] FAILED: {error}", file=sys.stderr)
                failures += 1
                continue
            v, s, stale, unverified, pending = result
            venues += v
            shows += s
            if stale or unverified:
                partial.append((label, stale, unverified))
            if pending:
                pendings.append((label, pending))
            if not v:
                failures += 1

    # Every request this run asked an upstream for, and how it was asked. Printed
    # because the alternative is a claim: the pipeline says it revalidates where it can
    # and never stores what an origin marks no-store, and this is the line that shows
    # whether that is true on the day. `full` is not waste -- most origins here offer no
    # validator at all, so there is nothing to revalidate with.
    c = common.cache_stats()
    if c["hit"] or c["miss"]:
        print(f"[run] http: {c['hit']} revalidated (304), {c['miss']} full, "
              f"{c['nostore']} not stored (origin said no-store), "
              f"{c['stored']} cache entries written")

    # Silent on a normal run. When it does appear, it is a provider telling us the
    # rate is wrong, which is worth seeing in the committed log rather than inferring
    # from a failure four hours later.
    t = common.throttle_stats()
    if t["asked"]:
        print(f"[run] throttled: {t['asked']} Retry-After responses, "
              f"{t['waited']:.0f}s waited, {t['refused']} not retried "
              f"(asked for longer than a run can wait)")

    # Named, not counted. A venue that kept its previous data is not a failure the run
    # can act on -- at this layer an empty parse and a cinema with nothing on today are
    # the same signal, `[]`, so failing here would fire on every ordinary closure. What
    # it must not do is disappear: the venue file is published with a `partial` status
    # and the health line ages on the oldest venue, so the app stops claiming the
    # provider is fresh, and this line puts the venue names in the committed log.
    # Pending is neither a failure nor a partial state -- the adapter confirmed the
    # programme is empty -- but a venue publishing nothing is a fact the committed log
    # must state, or the summary line reads as if the venue did not exist.
    for label, ids in pendings:
        print(f"[run] pending: {label} has {len(ids)} venue(s) with no programme "
              f"yet: {', '.join(ids)}")
    if partial:
        for label, ids, new_ids in partial:
            if ids:
                print(f"[run] partial: {label} kept previous data for "
                      f"{len(ids)} venue(s): {', '.join(ids)}")
            if new_ids:
                print(f"[run] partial: {label} has {len(new_ids)} venue(s) that have "
                      f"never produced a showtime: {', '.join(new_ids)}")

    print(summary_line(names, venues, shows, partial, pendings, empty, failures))
    # `not venues` is still a failure, because a run that wrote nothing and cannot say
    # why is the case this whole check exists for. It stops being one only when every
    # site said so itself -- an empty listing, or no sites on this half at all.
    return 1 if failures or (not venues and not empty and not skipped) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
