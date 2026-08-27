#!/usr/bin/env python3
"""eTiketti sites -> data/area-*.json + data/venues-{provider}.json."""
import datetime, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import synmerge
import etiketti


def main() -> int:
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    total = ok = 0
    for site in etiketti.SITES:
        try:
            per_venue = etiketti.fetch_site(site)
        except Exception as e:
            print(f"[{site['provider']}] FAILED: {e}", file=sys.stderr)
            continue
        synmerge.merge(out, per_venue, site["provider"])
        live = []
        for v in site["venues"]:
            shows = per_venue.get(v["id"])
            if not shows:
                continue          # no data: keep whatever is already committed
            synmerge.strip_helpers(shows)
            days = sorted({s["start"][:10] for s in shows})
            (out / f"area-{v['id']}.json").write_text(json.dumps(
                {"generated": now, "dates": days, "horizon": days[-1],
                 "shows": shows}, ensure_ascii=False), encoding="utf-8")
            live.append({k: v[k] for k in ("id", "name", "short", "city")})
            total += len(shows); ok += 1
            print(f"[{site['provider']}] {v['name']}: {len(shows)} showtimes, {len(days)} dates")
        if live:
            (out / f"venues-{site['provider']}.json").write_text(json.dumps(
                {"generated": now, "provider": site["provider"], "venues": live},
                ensure_ascii=False), encoding="utf-8")
    print(f"[etiketti] {ok} venues, {total} showtimes")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
