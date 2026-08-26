#!/usr/bin/env python3
"""Fetch BioRex showtimes -> data/area-br-*.json + data/venues-biorex.json.

Runs anywhere (no auth, no datacenter-IP block), so this is the GitHub Actions half
of the pipeline. Finnkino stays on a residential IP; see IDEAS.md.
"""
import datetime, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import biorex


def main() -> int:
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    per_venue = biorex.fetch_all()
    if not per_venue:
        print("ERROR: no BioRex venues fetched", file=sys.stderr)
        return 1

    written = 0
    for v in biorex.VENUES:
        shows = per_venue.get(v["id"])
        if shows is None:
            continue    # failed venue: leave the previous file in place
        shows.sort(key=lambda s: s["start"])
        days = sorted({s["start"][:10] for s in shows if s.get("start")})
        (out / f"area-{v['id']}.json").write_text(json.dumps(
            {"generated": now, "dates": days, "horizon": days[-1] if days else "",
             "shows": shows}, ensure_ascii=False), encoding="utf-8")
        written += 1

    (out / "venues-biorex.json").write_text(json.dumps(
        {"generated": now, "provider": "biorex",
         "venues": [{k: v[k] for k in ("id", "name", "short", "city")}
                    for v in biorex.VENUES if per_venue.get(v["id"]) is not None]},
        ensure_ascii=False), encoding="utf-8")

    total = sum(len(x) for x in per_venue.values())
    print(f"[biorex] {written}/{len(biorex.VENUES)} venues, {total} showtimes")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
