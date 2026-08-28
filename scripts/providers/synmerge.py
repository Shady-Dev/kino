"""Shared helper: merge provider-supplied Finnish synopses into films-extra.json.

Providers run before the TMDB pass and their own text is better, so this only ever
fills an empty slot — it never clobbers.
"""
import json, pathlib, re

import common


def norm(t):
    """Must match enrich_tmdb.norm() and normTitle() in index.html."""
    t = re.sub(r"[^\w\s]", " ", (t or "").lower().strip(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def merge(out: pathlib.Path, per_venue: dict, label: str) -> None:
    path = out / "films-extra.json"
    try:
        doc = json.loads(path.read_text())
    except Exception:
        doc = {}
    films = doc.get("films") or {}
    added = 0
    for shows in per_venue.values():
        for s in shows:
            syn = (s.get("_syn") or "").strip()
            if not syn:
                continue
            e = films.setdefault(norm(s["title"]), {"s": {"fi": "", "en": ""}, "r": 0, "tr": ""})
            e.setdefault("s", {"fi": "", "en": ""})
            if not e["s"].get("fi"):
                e["s"]["fi"] = syn
                added += 1
    doc["films"] = films
    common.write_json(path, doc)
    print(f"[{label}] synopses merged: {added}")


def strip_helpers(shows) -> None:
    for s in shows:
        s.pop("_syn", None)
        s.pop("movieUrl", None)
