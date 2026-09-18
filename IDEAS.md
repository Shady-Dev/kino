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

### Provider coverage, and what is next

56 providers, 101 venues, 69 cities, declared and committed alike, measured 2026-09-18.
Nothing is unpublished. Check for an existing platform first. Every candidate assessed on
2026-09-15 and 2026-09-18, with its evidence, is in
[docs/research/ticketing-platforms.md](docs/research/ticketing-platforms.md).

- **Thirty-two triaged 2026-09-18.** **Next action:** the maintainer's ranking. Kino Myyri
  is a Kinola tenant, four Johku storefronts share one reader, Kino Helios comes off a city
  service, ten server-render to a plain fetch, eight need a browser, eight have nothing.
- **Sun Kino:** the `allproducts.json` endpoint is demonstrably closed (403, session
  required). Whether any *other* public source exists for those four cinemas is untested.
- **Eventio is not closed:** no customer sweep was ever run.
- **Kino Kaustinen** is a real eTiketti tenant publishing no screening, so no ticket
  destination can be checked. **Next action:** re-read its listing on a later Monday.
- **Complete:** eTiketti (twenty), Nexxo (eight), Cinemahouse (three), TMB (four),
  MyCloudCinema's two readers, the Korttelikinot, Vista's one Finnish site, and the
  parser-shaped ones.

### Kinola: published, and Konepaja still has no programme

Kino Kilta and Kino Laika ship as `kinola.py` under the policy adopted 2026-09-15. The
classifier is the labelled director or genre field and nothing else: validated over 65
film pages, 53 publish and 12 carry no field, of which eleven are billed live acts and one
is a film, *A Fox Under a Pink Moon*, which is the override list's only entry. A runtime
and an age classification are not evidence, because Laika's live acts carry both. Omitted
on the day it was written, 11 films over 12 of 105 screenings, none force-excluded.
Published 2026-09-15 in `87437a3f`, 92 showtimes across the two venues. Decisions and
measurements: [docs/archive/2026-09-providers.md](docs/archive/2026-09-providers.md).
**Next action:** nothing here. Kino Konepaja gets a `SITES` entry when it lists a
screening: re-read 2026-09-15, its event list still says "Ei tulevia tapahtumia."

### Browser checks name their engines, and CI runs two

Promoted into [CLAUDE.md](CLAUDE.md) under "Testing" on 2026-09-18, which this entry
records because a finding becomes a rule only with one. The landing pages' layout check
runs as the `pages-layout` job in Chromium and WebKit and both must pass, and any claim of
browser verification has to say which engines and widths it covers.
**Why:** the phone layout shipped correct in Chromium and broken in WebKit, green through
the unit suite, the design contract and a Chromium-only browser check, and a reader found
it on their phone. The record is in
[docs/archive/2026-09-app.md](docs/archive/2026-09-app.md).
**Next action:** none here. Whether `tests/browser/test_client_browser.py` should also run
in WebKit is open; it drives `index.html` and has only ever run in Chromium, so that is its
own change.

### Seven venues the runner cannot read

In the 17:17 UTC run of 2026-09-16, `cinemahouse`, `tmb`, `kirkkonummi` and `nexxo` failed
together over seven domains after two green runs the same day. Nexxo's log shows 403s, and
every one of those hosts served its real page to an ordinary connection minutes later. The
guards now record what was served (`common.served`), so the next occurrence can be
diagnosed from the log; the record is in
[docs/archive/2026-09-pipeline.md](docs/archive/2026-09-pipeline.md).
**Next action:** the maintainer's, on one run's evidence. Either it clears by itself, as
the Nexxo timeout of 2026-09-14 and the Kino Kilta 500 of the same morning did, or these
providers move to `where="local"` as Cine and Star did on 2026-09-08. That adds about a
dozen venues to the laptop and makes the item below worse.

### Move the local fetch off the laptop

Eight providers block or challenge datacenter addresses (Finnkino, Kino Akseli, Kino
Engel, Joutsan Kino, Savon Kinot, Kino Regina, Cine, Elokuvateatteri Star), so 30 of 101
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


## Blocked

### Finnkino prices

Blocked by the access rule rather than by difficulty. The programme response the adapter
already reads carries no price field anywhere, scanning it for any key containing price,
amount, cost, ticket, fee, tariff or currency returns zero matches, and the obvious
ticket-type paths answer 404. The only route left is the seat-selection flow, which this
repo does not call or inventory.
The one route left open, a visitor-facing price *page*, is **deferred** by the maintainer
on 2026-09-16 for Finnkino and BioRex alike: neither is easily done. Nothing is probed and
nothing is scheduled. Evidence: [docs/research/prices.md](docs/research/prices.md).

### Kino Engel prices

The price rows are drawn by Johku's widget from an API that needs the widget's key. A
headless render was measured on 2026-09-13 at about 6 s a page for roughly 15 pages a run,
and deferred by the maintainer the same day: no more polling on the local half for now.
`price` and `aud` stay empty for Engel. The options left are that headless render on the
local half, or asking the cinema or Johku for a feed.

## Deferred

Each of these was looked at and set down, with the reason. None is scheduled.

**App and client**

- A Swedish synopsis from TMDB. `enrich_tmdb` fetches `fi-FI` and `en-US` overviews and
  breaks out of the loop once Finnish answers, so adding `sv-SE` would be a third request
  per film per run and a restructure of that loop. Out of scope on 2026-09-16 by the
  maintainer's instruction; the slot exists and Bio Savoy fills it, so this would only
  widen the coverage.
- Swedish generated pages. `build_pages.py` builds `fi` and `en`; the Swedish link sends a
  reader to the app on purpose, and `L` carries no Swedish page copy. Unchanged.

- Sparse-date dimming in the date picker: `<input type="date">` cannot disable individual
  days without a custom picker.
- A timer for a tab left visible all day, which never fires `visibilitychange`. The
  resume and rollover refreshes cover everything else.
- `aria-busy` on the picker trigger until the venue lists arrive. It is the honest ready
  signal and a two-line client change; `index.html` is frozen by the maintainer's
  instruction of 2026-09-14, so it stays a proposal. The browser tests click until the
  picker opens instead. What the file has done since that instruction, with dates, is in
  [docs/archive/2026-09-app.md](docs/archive/2026-09-app.md); this entry does not read an
  authorisation for this change out of it.
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

## Documentation state (2026-09-18, eighteenth pass)

Counts in README and here are re-measured against `data/`, the registry and `sitemap.xml`
on every provider change, because carried-over counts have been wrong repeatedly: the city
count, the poster count, the page rewrite frequency, the venue and provider counts, and
once a count stated twice in one file where only one copy moved.

Latest, re-measured 2026-09-18 with data at `17cadbac`. Declared and committed agree.
Three rows below had gone stale since the 2026-09-15 pass: the poster references, the
mirrored file count and the service-worker version. Two counts in the prose above were a
batch behind as well, in "Provider coverage" and in "Move the local fetch off the laptop",
which is the failure this section exists to catch. Every figure README states was measured
again and was already correct.

| | |
|---|---:|
| providers / venues / cities (declared) | 56 / 101 / 69 |
| venues in committed data | 101 |
| local providers (venues) | 8 (30) |
| venues per adapter, largest | eTiketti 30, Finnkino 17, Nexxo 13, BioRex 12, TMB 4 |
| generated pages per language | 116 |
| sitemap URLs | 233 |
| poster references (shows / films-extra) | 5647 (5344 / 303) |
| off-origin poster references | 0 |
| mirrored poster files | 1244 |
| `sw.js` CACHE | `leffavuoro-v175` |

Nothing is declared and unpublished. Kino Kilta and Kino Laika published in `87437a3f`,
which took the pages to 116 per language and the sitemap to 233, both as predicted, and
gave Turku a combined city page. That run **failed** at the city-link gate all the same,
and the chooser was synchronised afterwards in `56723020`.

The batch before them is published. **13 venues, 12 providers, 9 adapters** landed in
`d216607b`: Iso-Hannu (Rauma), the four TMB cinemas (Akaa, Valkeakoski, Pieksämäki,
Heinola), Julia 1&2 (Hyvinkää), Bio-Kaari (Forssa), Kino Vaakuna (Lohja), Kino Kuvakukko
(Kuopio), Kino Manttu (Nilsiä), Kino Kirkkonummi, Bio Savoy (Mariehamn) and Cine Mäntsälä
(Mäntsälä). The three figures stay apart because Kuvakukko is one provider with two venues
and TMB one adapter with four providers. Eleven new cities; Hyvinkää and Kuopio were
already covered and each reached two venues, which gave them a combined city page and left
`index.html`'s chooser stale, the gate that failed the run.

The predictions this section carried before that run were right: 113 pages per language
and 227 sitemap URLs, both measured after it. They are recorded as having held because the
per-provider entries in the archive each predicted their own increment and were wrong for
the opposite reason, all thirteen having landed at once.

**Why none of them has published.** The last cloud run was created 2026-09-15 07:55 UTC on
`bb409cc0` and committed `887a7988`; all twelve landed on `main` between 08:46 and 11:22
UTC, so no run has yet existed on code that declares any of them. The 02:30 and 10:30 cron
slots created no run at all. Scheduled execution is best-effort, as CLAUDE.md says under
"Access and ethics".

Earlier, measured 2026-09-14 at `c3fe4915` with data at `3147f45e`: 42 / 86 / 57,
98 pages per language, 197 sitemap URLs, 4193 poster references (3940 / 253) over 1029
files, `sw.js` `leffavuoro-v157`.

Two README numbers were wrong when this pass measured them and are corrected with it: the
adapter table said eTiketti served 29 venues against 30 in the venue files, and the cadence
paragraph said six local providers against the registry's eight. Both are registry-derived,
which is the class of number this section exists to catch.

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
