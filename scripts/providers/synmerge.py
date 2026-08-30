"""Shared helper: merge provider-supplied Finnish synopses into films-extra.json.

Providers run before the TMDB pass and their own text is better, so this only ever
fills an empty slot — it never clobbers.
"""
import json, pathlib, re

import common


def norm(t):
    r"""Must match enrich_tmdb.norm() and normTitle() in index.html.

    `_` is stripped explicitly; \w keeps it, the client's \p{L}\p{N} does not.
    """
    t = re.sub(r"[^\w\s]|_", " ", (t or "").lower().strip(), flags=re.UNICODE)
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


def repair_from_twin(films: dict, extra: dict) -> int:
    """Restore characters Finnkino's payload dropped to "?", using another chain's copy
    of the same distributor text. -> number of strings repaired.

    Finnkino publishes "Catherine Laga?aia" and "Auli?i Cravalho" where the name carries
    an okina (U+02BB). It is their CMS and not this pipeline: in the same string `®`,
    `“ ”` and every `ä` survive, `json.loads` would raise on malformed UTF-8 rather than
    emit "?", and the one decode in fetch_data.py uses errors="replace", which produces
    U+FFFD. Several chains run the distributor's blurb verbatim, so a clean copy of the
    same sentence is usually already in films-extra.json.

    A "?" cannot be decoded back on its own -- it could stand for an apostrophe, an okina
    or a real question mark -- so nothing here guesses. A twin is used only when it is
    the same length and differs *only* at positions where this text has "?", which makes
    the substitution a transcription of a string we already hold rather than a repair of
    one we do not. A twin that disagrees anywhere else is a different text and is left
    alone, and a genuine "Mitä?" is never touched because no twin will differ there.
    """
    fixed = 0
    for entry in films.values():
        syns = entry.get("s")
        if not isinstance(syns, dict):
            continue
        title = (entry.get("t") or {}).get("fi") or (entry.get("t") or {}).get("en") or ""
        twin = (extra.get(norm(title)) or {}).get("s") or {}
        for lang, text in syns.items():
            clean = twin.get(lang) or ""
            if not text or "?" not in text or len(clean) != len(text):
                continue
            pairs = [(a, b) for a, b in zip(text, clean) if a != b]
            if pairs and all(a == "?" and b != "?" for a, b in pairs):
                syns[lang] = clean
                fixed += len(pairs)
    return fixed


def strip_helpers(shows) -> None:
    for s in shows:
        s.pop("_syn", None)
        s.pop("movieUrl", None)
