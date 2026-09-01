"""Shared helper: merge provider-supplied Finnish synopses into films-extra.json.

Providers run before the TMDB pass and their own text is better, so this only ever
fills an empty slot — it never clobbers.
"""
import json, pathlib, re, threading

import common

# films-extra.json is one file for the whole run and merge() is a read-modify-write of
# it, while run.py now fetches independent hosts in parallel. Two sites merging at once
# would each write back a document built from what they read, so whichever finished
# second would drop the other's synopses -- silently, since neither is an error and the
# only symptom is a film with no Finnish blurb until some later run happens to add it.
#
# Serialised here rather than hoisted out of run_site and merged once after the pool
# joins, because merging in place keeps "[label] synopses merged: N" inside that site's
# own block in the committed log, and the merge itself is a few milliseconds against a
# site's minutes of paced fetching. The lock lives on the function rather than at the
# call site so a second caller cannot reintroduce the race by not knowing about it.
_lock = threading.Lock()

# Which site supplied each synopsis this run, by its index in the module's SITES.
#
# The lock alone only stops a lost write. It does not decide *whose* text lands when two
# sites publish different `_syn` for the same normalised title -- two chains showing the
# same film, each with its own blurb. Fill-if-empty then means "whichever host answered
# first", which with a pool is a property of the network: measured 2026-09-01 with one
# slow site and one fast one, `workers=1` published the first site's synopsis and
# `workers=2` published the second's, from the same data.
#
# The winner is the earlier site in SITES order, which is what the sequential loop
# produced and is the same on every run at every pool size. A site that is earlier may
# therefore replace text a later site already merged **during this run**; text that was
# in the file before the run began is never touched, which is the rule that matters --
# the provider's own synopsis still beats TMDB's, and the first provider in SITES order
# beats the rest.
_claimed = {}


def reset():
    """Forget this run's claims. run.py calls it before each module's sites are fetched.

    Per module rather than per process: modules run one after the other, so a later
    module's site 0 must not outrank an earlier module's site 5. Once a module is done
    its text is simply what is in the file, and the next module leaves it alone.
    """
    with _lock:
        _claimed.clear()


def norm(t):
    r"""Must match enrich_tmdb.norm() and normTitle() in index.html.

    `_` is stripped explicitly; \w keeps it, the client's \p{L}\p{N} does not.
    """
    t = re.sub(r"[^\w\s]|_", " ", (t or "").lower().strip(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def merge(out: pathlib.Path, per_venue: dict, label: str, order: int = 0) -> None:
    """Fold this site's synopses into films-extra.json. `order` is its index in SITES.

    A slot is filled when it is empty, and taken over when this site is earlier in SITES
    order than the site that filled it earlier in the same run. See `_claimed`.

    `synopses merged: N` counts what this call wrote. A later site's line can therefore
    be superseded by an earlier site's, which is visible in the committed log as two
    non-zero lines for one film and is the correct outcome rather than a miscount.
    """
    path = out / "films-extra.json"
    with _lock:
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
                key = norm(s["title"])
                e = films.setdefault(key,
                                     {"s": {"fi": "", "en": ""}, "r": 0, "tr": ""})
                e.setdefault("s", {"fi": "", "en": ""})
                if e["s"].get("fi"):
                    claimed = _claimed.get(key)
                    # Text from before this run, or from a site at least as early as
                    # this one. Either way it stands.
                    if claimed is None or order >= claimed:
                        continue
                e["s"]["fi"] = syn
                _claimed[key] = order
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
