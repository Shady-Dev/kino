#!/usr/bin/env python3
"""Generic provider runner.

    python3 scripts/providers/run.py biorex nexxo etiketti ...
    python3 scripts/providers/run.py --where cloud      # module list from the registry
    python3 scripts/providers/run.py --where local      # the two that need a local fetch

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
The file therefore carries `status`, `stale` and `oldest`, and `oldest` is what the
health line ages on — a provider is as fresh as its weakest venue. Only a site where
*every* venue came back empty is a failure, since nothing else would notice that.
"""
import datetime
import importlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common              # noqa: E402
import registry            # noqa: E402
import strands             # noqa: E402
import synmerge            # noqa: E402

OUT = pathlib.Path("data")


def generated_of(path):
    """The `generated` already committed for a venue. -> str, or '' if unreadable.

    A venue that keeps its previous file keeps that file's timestamp, so this is what
    the provider is really as fresh as. Unreadable is treated as unknown rather than as
    an error: a torn or hand-edited file must not stop the run publishing showtimes.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("generated") or ""
    except Exception:
        return ""


def run_site(mod, site, now):
    """Fetch and write one site. -> (venues_written, showtimes). Raises on fetch failure."""
    label = site.get("provider") or mod.__name__
    per_venue = mod.fetch_site(site)
    # A strand prefix belongs in `method`, not in the title: left there it fragments the
    # film, blocks the TMDB match and gives every film in the strand the same fallback
    # tile. Applied centrally so a new adapter gets it without knowing it exists.
    split = sum(bool(strands.apply(s)) for shows in per_venue.values() for s in shows)
    if split:
        print(f"[{label}] strand prefix split off {split} showtimes")
    synmerge.merge(OUT, per_venue, label)

    live = total = 0
    stale = []            # venues whose previous file was kept, so their data is older
    for v in site["venues"]:
        shows = per_venue.get(v["id"]) or []
        path = OUT / f"area-{v['id']}.json"
        if not shows and path.exists():
            stale.append(v["id"])
            print(f"[{label}] {v['name']}: no showtimes, keeping previous data "
                  f"from {generated_of(path) or 'an unknown time'}", file=sys.stderr)
            continue
        # No shows and no file yet (new venue whose first parse failed): write an
        # empty file, or the picker below would link to a 404.
        shows.sort(key=lambda s: s["start"])
        synmerge.strip_helpers(shows)
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
             "status": "partial" if stale else "ok", "stale": stale,
             "provider": site["provider"],
             "venues": [{k: v[k] for k in ("id", "name", "short", "city")}
                        for v in site["venues"]]})
    return live, total, stale


def main(argv) -> int:
    if "--where" in argv:
        names = registry.modules(argv[argv.index("--where") + 1])
    else:
        names = [a for a in argv if not a.startswith("-")]
    if not names:
        print("usage: run.py <module>... | run.py --where cloud|local", file=sys.stderr)
        return 2

    OUT.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    venues = shows = failures = 0
    partial = []          # (provider, [venue ids]) for every site that kept old data

    for name in names:
        try:
            mod = importlib.import_module(name)
            sites = mod.SITES
        except Exception as e:
            print(f"[{name}] unusable: {e}", file=sys.stderr)
            failures += 1
            continue
        for site in sites:
            label = site.get("provider") or name
            try:
                v, s, stale = run_site(mod, site, now)
            except Exception as e:
                print(f"[{label}] FAILED: {e}", file=sys.stderr)
                failures += 1
                continue
            venues += v
            shows += s
            if stale:
                partial.append((label, stale))
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
    if partial:
        for label, ids in partial:
            print(f"[run] partial: {label} kept previous data for "
                  f"{len(ids)} venue(s): {', '.join(ids)}")

    print(f"[run] {' '.join(names)}: {venues} venues, {shows} showtimes, "
          f"{sum(len(i) for _, i in partial)} stale, {failures} failures")
    return 1 if failures or not venues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
