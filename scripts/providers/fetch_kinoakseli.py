#!/usr/bin/env python3
"""Kino Akseli -> data/area-ka-nummela.json + data/venues-kinoakseli.json."""
import datetime, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kinoakseli


def main() -> int:
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    try:
        shows = kinoakseli.fetch()
    except Exception as e:
        print(f"[kinoakseli] FAILED: {e}", file=sys.stderr)
        return 1
    if not shows:
        print("[kinoakseli] no showtimes parsed — page layout may have changed", file=sys.stderr)
        return 1
    days = sorted({s["start"][:10] for s in shows})
    (out / f"area-{kinoakseli.VENUE['id']}.json").write_text(json.dumps(
        {"generated": now, "dates": days, "horizon": days[-1], "shows": shows},
        ensure_ascii=False), encoding="utf-8")
    (out / "venues-kinoakseli.json").write_text(json.dumps(
        {"generated": now, "provider": "kinoakseli",
         "venues": [{k: kinoakseli.VENUE[k] for k in ("id", "name", "short", "city")}]},
        ensure_ascii=False), encoding="utf-8")
    print(f"[kinoakseli] {len(shows)} showtimes, {len(days)} dates, horizon {days[-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
