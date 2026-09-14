# Kino: open work and decision index

This file is the index of open work. It holds proposals, priorities, statuses and the
dated decision records that are still live. It stopped holding history on 2026-09-15,
when 4,790 lines of closed records and investigation evidence moved to
[docs/archive/](docs/archive/) and [docs/research/](docs/research/). The map is at the
bottom, under "Where the rest went".

## How to read this file

- **Active work** is open and has a next action. The next action is written down.
- **Blocked** is open and cannot proceed without something outside this repo: a
  maintainer decision, a third party, or an endpoint that does not exist.
- **Deferred** is decided against for now, with the reason. A deferred line is not a
  backlog item; it is a record so the same idea is not re-proposed from scratch.
- Anything closed is in `docs/archive/`, with the entry as it was written. The heading
  text is unchanged, so a reference that names a heading still resolves.
- Accepted working rules are not here. They are in [CLAUDE.md](CLAUDE.md), and the visual
  contract is in [DESIGN.md](DESIGN.md). A finding does not become a rule by being
  written down: promoting one into `CLAUDE.md` needs an entry here like any other change.

One role nothing else can take: `scripts/check_design_push.py` requires an `IDEAS.md`
change in the same commit as a `DESIGN.md` or `tests/test_design_contract.py` change. A
contract change is explained here, never in `docs/research/`.

## Active work

### Two verifications waiting on a cloud run (opened 2026-09-14)

One of the two is closed. The remaining one needs a cloud run that completes **and**
publishes *after* 00:00 UTC, which the 22:35 run of 2026-09-14 was not: it ran on the same
UTC day the entries were last stamped, so `refresh.due` skipped them again, exactly as this
entry predicted. Re-measured at `3147f45e`: the eight keys still read `c: 2026-09-14` with
no id.

1. **The TMDB marker fix is deployed and not yet exercised.** `f3b61ee8` takes
   `englanniksi`, `på svenska`, `suomeksi puhuttu` and a parenthesised strand off the
   search string. Eight cache keys still carry `c: 2026-09-14` from the 17:13 UTC run,
   which predates it, and `refresh.due` skips an entry already checked today:
   `kojootti vs acme englanniksi`, `… på svenska`, `… suomeksi puhuttu`, `… dub`,
   `… eng`, `… sub`, `gråben vs acme på svenska`, `kätyrit monsterit englanniksi`.
   The boundary is `datetime.date.today()` at `enrich_tmdb.py:613`, the runner's date,
   and the pass runs only from `biorex.yml:68` with no `TZ`, so it rolls at midnight UTC
   and not at midnight Helsinki. Expected match for the Kojootti and Gråben family is
   1204680.
   **Next action:** after the first run that completes and publishes past 00:00 UTC, read
   the committed cache and `logs/run-enrich.log` and tell three outcomes apart: searched and
   matched, searched and still unmatched (a different cause, and the marker fix would not
   be sufficient alone), or skipped again. An unchanged entry read *before* publication is
   not a failed retry.
2. **Järvelän Kino recovered (closed 2026-09-14).** The 22:35 UTC cloud run `3147f45e`
   reads `[jarvelankino] Järvelän Kino (Järvelä): 8 showtimes` over 6 dates, and
   `logs/run-nexxo.log` ends `exit=0`, `10 venues, 110 showtimes, 0 stale, 0 failures`.
   The 20:37 timeout was transient, which is what a timeout carrying no mechanism usually
   turns out to be. Nothing was changed for it. Investigate only if it fails again.

### Provider coverage, and what is next

42 providers, 86 venues, 57 cities as of 2026-09-14. Check for an existing platform
first: a cinema on Vista, MyCloudCinema, Nexxo, eTiketti, Johku or `cinema-reservations`
is a `SITES` entry, not a parser. What each platform publishes is in
[docs/research/ticketing-platforms.md](docs/research/ticketing-platforms.md).

- **Unstarted candidates:** the Nexxo timetable sites (Bio-Salo, Stara, Jukola),
  Kaustinen, Union, Iso-Hannu, Julia, Kirkkonummi, Diana. **Next action:** probe as a
  visitor and classify by platform before writing anything.
- **Cinemahouse is now a platform** (three cinemas, 2026-09-14), so a fourth
  `cinema-reservations` site is a `SITES` entry.
- **Eventio** is a ticketing platform with cinema customers and is unprobed. It surfaced
  as KAVI's shop under Kino Regina. **Next action:** probe one customer site.
- **Cinema Niagara and Kino Metso are done** (2026-09-02 and 2026-08-31); both were the
  parser-shaped leftovers of their sweeps.
- **Complete:** eTiketti (twenty providers), Nexxo (eight), the Korttelikinot, and Vista's
  one Finnish site. Cinamon and other non-Finnish Vista users are untested.
- Roughly 196 cinemas and 306 screens exist in Finland (2009), and the tail clusters onto
  a few platforms. Platform adapters first; a bespoke site only when a cinema is on none.

### Language codes normalised end to end

The adapter and client fixes landed 2026-09-02 (sw.js v99). `fetch_data.lang_tag` maps
through `FINNKINO_LANG`, `nexxo._lang` drops `XX` from the subtitle role, and the client's
`LN` plus the generator's mirror gained `LT` and `ML`. After the 2026-09-02 cloud run `XX`
was gone; `TU-A` and `MA-A` were still awaiting a local run.
**Next action:** grep the committed `data/area-*.json` after a local run. When none carries
`TU`, `MA` or `XX`, delete `CODE_ALIAS`, `NO_SUBTITLES` and `LN_EXTRA` from
`build_pages.py` with their tests. Evidence:
[docs/research/languages.md](docs/research/languages.md).

### Move the local fetch off the laptop

Eight providers block or challenge datacenter addresses (Finnkino, Kino Akseli, Kino
Engel, Joutsan Kino, Savon Kinot, Kino Regina, Cine, Elokuvateatteri Star), so 30 of 86
venues ride on one machine. Cloud VMs cannot replace it and the MovieXchange credential
route is closed, so there is no way off the laptop that keeps the coverage.
**Next action:** an always-on box on the same network. Nothing in this repo changes; the
wrapper outside it moves.

### Staleness monitor: the ping

The repo half is done, `scripts/check_staleness.py`: a pure function of a file and a
clock, answering "did a run happen", which `check_runs.py` cannot. Its threshold is
`STALE_H` from `index.html` and a test fails if the two drift apart.
**Next action:** the external ping that calls it. The schedule, the file location and the
recipient are machine-specific and live in the wrapper outside this repo, so this item
cannot close here.

### Landing pages: two open items

Both recorded 2026-09-02, neither built. The pages are `scripts/build_pages.py` alone.

1. **The screening list could span the full film width on narrow phones.** At 320 px the
   list stays inside the 206 px information column beside the poster even after the poster
   has ended, so a city stub wraps to three lines while the 72 px poster column below the
   poster sits empty. Structural, so it is its own change, and it has to be measured on
   films with and without a synopsis, since the list's starting height differs.
2. **The city cinema links read as a passive colour key.** They are links to the theatre
   pages. A restrained link affordance would fix it; large primary-style buttons would
   compete with the one CTA on the page.

### Heureka's missing posters wait for written permission

Three of four planetarium films render initials tiles. No weak match, so no wrong poster
is on the site. Heureka's own site carries portrait key visuals for two of them.
Public availability is not permission to copy and redistribute, and Heureka's FAQ licenses
none of its promotional artwork.
**Next action:** written permission from Heureka's media contact. If it arrives, the
accepted implementation is the article's portrait `og:image` only, same-site source, a
valid image type and verified dimensions. Declined regardless: a weak TMDB match,
generated artwork, a cropped 16:9 still. Full entry:
[docs/archive/2026-09-providers.md](docs/archive/2026-09-providers.md).

### Two small ones

- **README workflow badge.** Not built.
- **Credential hygiene and rotation.** Tracked in private notes outside this repo. The
  Finnkino token is fetched fresh at run time and used within seconds, so there is no
  stored credential and nothing to rotate; this item covers the rest.

### The run logs moved to logs/, and the local half had to be changed by hand (2026-09-15)

Bug: 20 run logs sat at the repo root, 20 of its 45 tracked entries, so the root read as
build output rather than as the product.
Fix: `logs/`. Every dependency moved in the same commit, and three of them would have
failed *silently* rather than loudly, which is why the map was built before anything moved:
`logs.yml`'s path filter was `run*.log` and a GitHub glob does not cross a `/`, so the only
job that runs `check_runs.py` would simply have stopped firing; `robots.txt` closed the logs
with the root-anchored `/run.log` and `/run-`, which would have gone dead and left the logs
crawlable under `Allow: /`; and `tests/test_robots.py` asserted the old URLs were blocked,
which stays green for ever because a rule that matches nothing still refuses a path nothing
serves. The loud ones were `biorex.yml`'s `git add run-*.log` (unmatched pathspec) and
`check_runs.py`'s zero-logs branch.
`check_runs.py` gained two things rather than a new caller: a `--dir` default derived from
the file's own location, so the documented command works from any cwd, and `strays()`,
which fails on any `run*.log` left at the repo root. That last one is the guard for the one
failure this may not have, a writer that was not migrated publishing to the old place while
the check reads the moved copies and calls them green.
**The local half is not in this repo.** Its wrapper was edited by hand, the same day: seven
`tee` targets, seven `exit=` appends, the staging list and an explicit `mkdir -p logs`. A
repo change does not reach it, which is the standing hazard with anything the wrapper
writes.
**Both writers verified the same evening.** The local wrapper ran at 22:28 UTC and pushed
`a9704850`: it reset to the new tree, wrote and staged `logs/run.log`,
`logs/run-posters-local.log` and `logs/run-pages-local.log`, and finished clean. It
dispatched the cloud run, which pushed `3147f45e` with six fresh logs under `logs/`
(cinemahouse, enrich, nexxo, pages, posters, riviera). Neither recreated a root log: the
root is 26 entries with no `run*.log`, and `check_runs.py` on that tree reads
`20 run log(s), 0 failed`. The earlier `Check run logs` red proved only the reader half,
discovery and checking after the move, not that a fetch writes where it should; keeping
those two apart is why this entry names which run proved which half.
Tests: `test_check_runs.py` +2 (the default finds the repo's own logs; a root log fails),
`test_robots.py` +1 reading the committed tree rather than a list. Three mutations red.

## Blocked

### Kinola: whether to publish a row the film page cannot classify

Three cinemas (Kilta, Laika, Konepaja). The three templates, the film-versus-concert rule,
the sample it rests on and the four required fixtures are in
[docs/research/kinola.md](docs/research/kinola.md).
Open, and the maintainer's to decide: include the unclassifiable rows and some live events
show as films; omit them and thin-metadata films vanish. A per-title override covers
either. **Next action:** ask before writing the adapter. This blocks only Kinola.

### Finnkino prices

Blocked by the access rule rather than by difficulty. The programme response the adapter
already reads carries no price field anywhere, scanning it for any key containing price,
amount, cost, ticket, fee, tariff or currency returns zero matches, and the obvious
ticket-type paths answer 404. The only route left is the seat-selection flow, which this
repo does not call or inventory.
**Open on one possibility:** a visitor-facing price *page* would be ordinary content and a
legitimate source. Not probed. Evidence:
[docs/research/prices.md](docs/research/prices.md).

### Kino Engel prices

The price rows are drawn by Johku's widget from an API that needs the widget's key. A
headless render was measured on 2026-09-13 at about 6 s a page for roughly 15 pages a run,
and deferred by the maintainer the same day: no more polling on the local half for now.
`price` and `aud` stay empty for Engel. The options left are that headless render on the
local half, or asking the cinema or Johku for a feed.

## Deferred

Each of these was looked at and set down, with the reason. None is scheduled.

**App and client**

- Sparse-date dimming in the date picker: `<input type="date">` cannot disable individual
  days without a custom picker.
- A timer for a tab left visible all day, which never fires `visibilitychange`. The
  resume and rollover refreshes cover everything else.
- `aria-busy` on the picker trigger until the venue lists arrive. It is the honest ready
  signal and a two-line client change; `index.html` is frozen by the maintainer's
  instruction of 2026-09-14, so it stays a proposal. The browser tests click until the
  picker opens instead.
- `safeUrl` still accepts a scheme-less URL, so the next provider publishing a bare path
  repeats Cinema Orion's 2026-09-06 fault. Whether the client should reject one or resolve
  it against the provider host is a separate change.
- Keyed DOM reuse in the render path: at this list size it buys nothing over
  `content-visibility:auto` and costs a rewrite.
- Seat counts on screen. They are parsed and deliberately not published: data is hours old
  and "12 vapaata" can be zero, while sold-out survives staleness. Do not restore them
  without solving the staleness.
- A floating theme button or a duplicate in the pinned strip. Theme and language are set
  about once a month and reintroducing them costs the 58 px v70 recovered.
- The tools row wrapping to two lines at 320 px. Forcing five controls onto one line costs
  tap targets, abbreviations or squeezed Finnish and Swedish labels.

**Pipeline**

- Routing `enrich_tmdb.py` through `common.fetch`. It uses a bare `urlopen` with no retry,
  so a TMDB 429 skips that title.
- `api()` in `fetch_data.py` has no retry, unlike `common.fetch`.
- A dataclass for the fetch result. `run.py` already models it.
- A single shared TMDB pass. The two stay separate and agree on the rules, so the same
  film can briefly carry two ratings.
- Finnkino's editorial children's-film list as the authority for the Lapsille filter. It
  would work cross-chain by title and is another scrape on the local-only half. Watch the
  genre rule first.
- Pruning a poster once its film stops screening. A few MB a year.
- Closing the window where SITES and the venue files disagree: comparing them directly
  fails every provider addition until the pipeline has run.

**Ops and pages**

- A Pages artifact deploy, to stop the committed pages growing the repo by roughly the
  gzipped delta per day (~390 kB worst case). It would move the traffic path behind
  Actions scheduling.
- A data branch: decided against 2026-09-01. Branching does not shrink history and every
  way off `main` is worse.
- `og:image` as a 1200x630 card rather than `icon-512.png`. It would preview better.
- A venue or city count in the meta description. It would be a third copy of a number that
  goes stale.
- The SEO experiment: "ohjelmisto" in Finnish theatre-page titles and descriptions on a
  subset against an unchanged control. Waits on the Search Console re-read.
- A Tuesday ~15:00 Helsinki local slot for Finnkino's weekly drop. Not built on a sample
  of one. Evidence:
  [docs/research/publication-rhythm.md](docs/research/publication-rhythm.md).
- A native Finland-Swedish reader for the Swedish interface strings, which are drafted
  rather than translated. The contact line matters most.
- Making showtime pages indexable. It would turn a personal app into a directory
  competing with the cinemas' own listings.
- Hidden text, `<noscript>` content that differs from what a visitor sees, or any other
  cloaking. Spam by every engine's definition.

## Documentation state (2026-09-14, eleventh pass)

Counts in README and here are re-measured against `data/`, the registry and `sitemap.xml`
on every provider change, because carried-over counts have been wrong repeatedly: the city
count, the poster count, the page rewrite frequency, the venue and provider counts, and
once a count stated twice in one file where only one copy moved.

Latest, measured 2026-09-14 at `6b50bd4f` with data at `712ebc7e`:

| | |
|---|---:|
| providers / venues / cities | 42 / 86 / 57 |
| local providers (venues) | 8 (30) |
| generated pages per language | 98 |
| sitemap URLs | 197 |
| poster references (shows / films-extra) | 4044 (3791 / 253) |
| off-origin poster references | 0 |
| mirrored poster files | 1023 |
| `sw.js` CACHE | `leffavuoro-v157` |

Poster counts live here and not in README: they move with every run, and stating them
there made the file wrong within hours twice on 2026-09-14. README carries the behaviour
instead, which does not move.

Earlier passes, kept as a record of what was true on the day: Kino Regina 2026-09-05
(37 / 79 / 52, 89 pages, 179 sitemap URLs, 5 local providers over 26 venues, 3900 poster
references over 658 files), Tapiola (36 / 78 / 52), Korjaamo (35 / 77 / 52), Heureka
(34 / 76 / 52), Kino Metso 2026-09-01 (32 / 74 / 52), the Nexxo sweep 2026-08-31
(31 / 70 / 50), Bio Rex Kokkola 2026-08-30 (25 / 64 / 45). Counts inside a dated archive
entry record that day and are left alone.

Where each document's content belongs is a rule, and it is in
[CLAUDE.md](CLAUDE.md) under "Where it goes".

## Contact

**leffavuoro@gmail.com**

The address is written once as static markup in `status/index.html`. It is repeated here
and in `README.md` on purpose: `tests/test_contact_address.py` discovers it from the page
and requires both documents to carry the same one, so a half-finished rotation fails the
suite instead of shipping. The test also refuses any other address in any tracked file,
which is the leak guard. Do not remove this section without changing `SOURCES` in that
test, and do not add an address anywhere else.

The pipeline reads every provider as `Leffavuoro/1.0 (+https://leffavuoro.fi)`, and that
URL resolves to a page carrying this address, so a cinema can identify who is reading
them. If a cinema would rather not be included, the adapter comes out: one entry in
`scripts/providers/registry.py`, and no reason has to be given. The access rules are in
[CLAUDE.md](CLAUDE.md) under "Access and ethics".

## Where the rest went

Moved 2026-09-15. Nothing was deleted; 4,790 lines of closed records and evidence moved
out of this file and each entry kept its heading.

**Closed decision records**, one archive file per area:

| File | What is in it |
|---|---|
| [docs/archive/2026-09-app.md](docs/archive/2026-09-app.md) | `index.html`, `sw.js`, the generated landing pages, `/status/`, accessibility, Finnish copy, the ticket's shape, and the `Done` checklist |
| [docs/archive/2026-09-pipeline.md](docs/archive/2026-09-pipeline.md) | `run.py`, `common.py`, the TMDB passes, the shared price and poster steps, the show contract, the rules every adapter is held to |
| [docs/archive/2026-09-providers.md](docs/archive/2026-09-providers.md) | one section per provider or sweep: what was probed, what the adapter decided, the accent, and the run that settled `where` |
| [docs/archive/2026-09-ops.md](docs/archive/2026-09-ops.md) | workflows, the checks that gate a push, hosting and DNS, the licence, IndexNow, crawler and snippet work, monitoring |
| [docs/archive/2026-09-gotchas.md](docs/archive/2026-09-gotchas.md) | the "Notes / gotchas" list: traps that cost a debugging session and did not become rules |

**Investigation evidence**, one topic file each:

| File | What is in it |
|---|---|
| [docs/architecture.md](docs/architecture.md) | how the pieces fit and the constraints behind them; a standing document, not an archive |
| [docs/research/ticketing-platforms.md](docs/research/ticketing-platforms.md) | BioRex, Nexxo, eTiketti, Vista, Johku, and the directory and domain sweeps |
| [docs/research/kinola.md](docs/research/kinola.md) | the three templates, films against other events, the four required fixtures |
| [docs/research/tooling-evaluation.md](docs/research/tooling-evaluation.md) | the seven tools measured on 2026-09-14 |
| [docs/research/prices.md](docs/research/prices.md) | where a ticket price can be read and where it cannot, per provider |
| [docs/research/accent-colour.md](docs/research/accent-colour.md) | how a chain accent is measured, the corrected ΔE figures, what binds a new one |
| [docs/research/languages.md](docs/research/languages.md) | which providers publish which languages, and the language-code measurement |
| [docs/research/seo-and-search.md](docs/research/seo-and-search.md) | the Search Console baseline and what the pages rank for |
| [docs/research/publication-rhythm.md](docs/research/publication-rhythm.md) | when cinemas publish, measured and as Finnkino states it |

**Accepted rules** were not moved into either. They were already in
[CLAUDE.md](CLAUDE.md) and [DESIGN.md](DESIGN.md), which are authoritative, and the
duplicate prose here is gone rather than copied. The one that used to live here and is
worth naming: "Access and ethics", now in `CLAUDE.md`, with the historical record of how
each rule was arrived at in `docs/archive/2026-09-ops.md`.

Two anchors that used to point inside this file and now point into the archive:
"Seven backlog items closed without building them" and "The landing pages belong to the
product" are both in
[docs/archive/2026-09-app.md](docs/archive/2026-09-app.md).
