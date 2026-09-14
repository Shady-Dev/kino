# TMDB matching: what the search can and cannot find

Probes of TMDB's search endpoint against the titles Finnish cinemas actually publish.
Written 2026-09-14. Nothing here is a rule; the open items it feeds are in
[IDEAS.md](../../IDEAS.md) and the decisions in
[docs/archive/2026-09-pipeline.md](../archive/2026-09-pipeline.md).

## Findings

**What the search index covers** (probed 2026-08-27, re-confirmed 2026-09-14). Original
title, English title, and *registered alternative titles*. A translation is not the same
field as an alternative title and is not searched. `language=fi-FI` localises the
**response** only; it does not widen the match. So a Finnish distributor title reaches a
film only when someone has registered it on TMDB as an alternative title.

**Pressure / Myrskyn ikkuna, read 2026-09-14.** 17 providers publish the film, 93
showtimes, every one with no `tmdbId`. The title is clean: no marker, no strand, no
parenthesis, so `clean()` leaves it and the search string is the published title.

| query | result |
|---|---|
| `search/movie?language=fi-FI&query=Myrskyn ikkuna` | **0 results** |
| `search/movie?query=Myrskyn ikkuna` | **0 results** |
| `movie/1318413/translations` | no `fi` entry |
| `movie/1318413/alternative_titles` | BR, US, SA, LV, PL only, no Finnish row |

So the cache entry reading `x:false` with no id is a search that ran and found nothing, not
a skipped search and not a candidate the acceptance rules rejected.

**Identity of the candidate**, checked before anything was written, because two 2026 films
are called Pressure:

| | 1318413 | 1701077 |
|---|---|---|
| runtime | 101 min | 5 min |
| votes | 390 | 0 |
| genres | Thriller, History, War, Drama | Horror, Thriller, Comedy |
| alternative titles | LV and PL both name the Normandy D-Day story | none |

All 17 providers publish 100 min and K-12. 1318413 is the film; 1701077 is a short.

**The language-marker keys, measured 2026-09-14** by running `clean()` and `queries()` over
the published titles and searching with the exact strings they produce:

| published title | search string | outcome |
|---|---|---|
| `Kojootti vs. ACME (englanniksi)` | `Kojootti vs. ACME` | exact 1204680 |
| `Kojootti vs. ACME (på svenska)` | `Kojootti vs. ACME` | exact 1204680 |
| `Kojootti vs. ACME (suomeksi puhuttu)` | `Kojootti vs. ACME` | exact 1204680 |
| `Kojootti vs. ACME (Dub)` | `Kojootti vs. ACME` | exact 1204680 |
| `Gråben vs. ACME (på svenska)` | `Gråben vs. ACME` | 1 hit, 1204680, **not exact** |
| `Kojootti vs. ACME ENG` | `Kojootti vs. ACME ENG` | **0 results** |
| `Kojootti vs. ACME SUB` | `Kojootti vs. ACME SUB` | **0 results** |
| `Kätyrit & Monsterit (englanniksi)` | — | film is in no area file any more |

Three distinct outcomes, which is what the marker fix had to be told apart from: four
searched and matched, one searched with its only candidate refused by the exact-title rule,
two searched with no candidate at all.

## Inferences and open questions

- **The Gråben refusal is correct, not a gap.** TMDB has no Swedish title for the film, so
  the only hit is not an exact match and the trust gate withholds the id. No change to the
  marker handling can alter that; only a registered Swedish alternative title would.
- **`ENG` and `SUB` are bare suffixes with no parentheses**, which `clean()` does not
  touch. Adding them to `TRAIL_NOISE` would close both keys. Not done: they are short,
  ambiguous tokens where `englanniksi` is not, so eating a real trailing title word is a
  live risk. Open, and the maintainer's call.
- **`gilda.py` publishes `original` with the strand prefix still attached** on six shows
  (`"Seniorikino: Myrskyn Ikkuna"`) while `title` has it split off, which is what put
  `seniorikino myrskyn ikkuna` in the cache's `o` field. Found in passing on 2026-09-14.
  It does not cause any miss here, since the cleaned original dedupes against the published
  title, but it feeds `reconsider()`'s evidence comparison. Unfixed.

## Status and next step

Myrskyn ikkuna is aliased to 1318413 in `scripts/providers/tmdb-aliases.json`, which both
passes read. The alias takes effect on the next cloud run; the check is that
`logs/run-enrich.log` stops listing the title and the shows gain a `tmdbId`.

The four marker keys need a run that publishes after 00:00 UTC, because `refresh.due`
skips an entry already checked today and all eight were stamped `c: 2026-09-14`. Next step
for both: read the committed cache and `logs/run-enrich.log` after that run.
