#!/usr/bin/env python3
"""Riviera -> data/area-rv-*.json + data/venues-riviera.json."""
import datetime, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import riviera, synmerge


def main() -> int:
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    try:
        per_venue = riviera.fetch_site()
    except Exception as e:
        print(f"[riviera] FAILED: {e}", file=sys.stderr)
        return 1
    if not per_venue:
        print("[riviera] no showtimes parsed", file=sys.stderr)
        return 1

    synmerge.merge(out, per_venue, "riviera")
    live, total = [], 0
    for v in riviera.SITE["venues"]:
        shows = per_venue.get(v["id"])
        if not shows:
            continue
        synmerge.strip_helpers(shows)
        days = sorted({s["start"][:10] for s in shows})
        (out / f"area-{v['id']}.json").write_text(json.dumps(
            {"generated": now, "dates": days, "horizon": days[-1], "shows": shows},
            ensure_ascii=False), encoding="utf-8")
        live.append({k: v[k] for k in ("id", "name", "short", "city")})
        total += len(shows)
        print(f"[riviera] {v['name']}: {len(shows)} showtimes, {len(days)} dates")
    if live:
        (out / "venues-riviera.json").write_text(json.dumps(
            {"generated": now, "provider": "riviera", "venues": live},
            ensure_ascii=False), encoding="utf-8")
    print(f"[riviera] {len(live)} venues, {total} showtimes")
    return 0 if live else 1


if __name__ == "__main__":
    sys.exit(main())
