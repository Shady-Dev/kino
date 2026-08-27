#!/usr/bin/env python3
"""Fetch BioRex showtimes -> data/area-br-*.json + data/venues-biorex.json.

Runs anywhere (no auth, no datacenter-IP block), so this is the GitHub Actions half
of the pipeline. Finnkino stays on a residential IP; see IDEAS.md.
"""
import datetime, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import biorex


def norm(t):
    """Must match enrich_tmdb.norm() and normTitle() in index.html."""
    t = re.sub(r"[^\w\s]", " ", (t or "").lower().strip(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def merge_synopses(out, per_venue):
    """BioRex publishes Finnish synopses; keep them in the shared title-keyed file so
    area files stay small. Merge, never clobber: the TMDB pass runs after this."""
    path = out / "films-extra.json"
    try:
        doc = json.loads(path.read_text())
    except Exception:
        doc = {}
    films = doc.get("films") or {}
    added = 0
    for shows in per_venue.values():
        for s in shows:
            syn = s.get("_syn")
            if not syn:
                continue
            k = norm(s["title"])
            entry = films.setdefault(k, {"s": {"fi": "", "en": ""}, "r": 0, "tr": ""})
            entry.setdefault("s", {"fi": "", "en": ""})
            if not entry["s"].get("fi"):
                entry["s"]["fi"] = syn
                added += 1
    doc["films"] = films
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print(f"[biorex] synopses merged: {added}")


def main() -> int:
    out = pathlib.Path("data"); out.mkdir(exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    per_venue = biorex.fetch_all()
    if not per_venue:
        print("ERROR: no BioRex venues fetched", file=sys.stderr)
        return 1

    merge_synopses(out, per_venue)

    written = 0
    for v in biorex.VENUES:
        shows = per_venue.get(v["id"])
        if shows is None:
            continue    # failed venue: leave the previous file in place
        shows.sort(key=lambda s: s["start"])
        for s in shows:            # helper fields, not for the client
            s.pop("_syn", None); s.pop("movieUrl", None)
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
