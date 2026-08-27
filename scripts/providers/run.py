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

A venue with no showtimes writes **no file**, so previously committed data stays up
rather than the app going empty on a parse regression. That is also why an empty parse
is logged loudly and counts as a failure: nothing else would notice, since the health
line only sees a file's age, not whether it still has content.
"""
import datetime
import importlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import registry            # noqa: E402
import synmerge            # noqa: E402

OUT = pathlib.Path("data")


def run_site(mod, site, now):
    """Fetch and write one site. -> (venues_written, showtimes). Raises on fetch failure."""
    label = site.get("provider") or mod.__name__
    per_venue = mod.fetch_site(site)
    synmerge.merge(OUT, per_venue, label)

    live, total = [], 0
    for v in site["venues"]:
        shows = per_venue.get(v["id"])
        if not shows:
            print(f"[{label}] {v['name']}: no showtimes, keeping previous data",
                  file=sys.stderr)
            continue
        shows.sort(key=lambda s: s["start"])
        synmerge.strip_helpers(shows)
        days = sorted({s["start"][:10] for s in shows if s.get("start")})
        (OUT / f"area-{v['id']}.json").write_text(json.dumps(
            {"generated": now, "dates": days, "horizon": days[-1] if days else "",
             "shows": shows}, ensure_ascii=False), encoding="utf-8")
        live.append({k: v[k] for k in ("id", "name", "short", "city")})
        total += len(shows)
        print(f"[{label}] {v['name']}: {len(shows)} showtimes, {len(days)} dates")

    if live:
        (OUT / f"venues-{site['provider']}.json").write_text(json.dumps(
            {"generated": now, "provider": site["provider"], "venues": live},
            ensure_ascii=False), encoding="utf-8")
    return len(live), total


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
                v, s = run_site(mod, site, now)
            except Exception as e:
                print(f"[{label}] FAILED: {e}", file=sys.stderr)
                failures += 1
                continue
            venues += v
            shows += s
            if not v:
                failures += 1

    print(f"[run] {' '.join(names)}: {venues} venues, {shows} showtimes, "
          f"{failures} failures")
    return 1 if failures or not venues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
