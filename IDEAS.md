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

81 providers, 132 venues, 96 cities, declared and committed alike, measured 2026-09-21.
Check for an existing platform first. Every candidate assessed, with its evidence, is in
[docs/research/ticketing-platforms.md](docs/research/ticketing-platforms.md).

- **Eight read 2026-09-21.** Built: Kino Akustiikka (Ylivieska), on the town's Localhub
  calendar and the first tenant of `localhub.py`, and Kino-Huovi (Harjavalta), its own
  parser. The other six are blocked below or in the entries above them, each with what it
  waits on. **Next action:** none from these.
- **Earlier batches:** thirty-two triaged 2026-09-18, five from the nytleffaan diff, six on
  2026-09-20. Bio Pallas, Huvimylly, Alatalo, Cinema Sheryl, Kino Hannikainen, Kino Virta,
  Matin-Tupa and Kino Kuusamotalo were built from them; eight need a browser and eight have
  nothing. Bio-Salo, Bio Sydväst and Kinoma publish nothing readable.
- **Sun Kino:** `allproducts.json` closed (403, session required); another source untested.
  **Eventio:** closed 2026-09-19. Its one known tenant is Kino Regina, already built.
- **Complete:** eTiketti (twenty), Nexxo (eight), Kinola (four), Johku (seven),
  Cinemahouse (three), TMB (four), MyCloudCinema's two, Vista's one, the parser-shaped.

### Heureka's own posters still wait for written permission

The initials tiles are gone. Three planetarium films draw Leffavuoro's own title cards as
of 2026-09-20: abstract art this repository generates, plus the published title, never a
poster and never derived from anyone's artwork. **That supersedes the decline of generated
artwork**; a weak TMDB match and a cropped 16:9 still stay declined. Heureka's *own*
artwork is unchanged, licensed to nobody, and public availability is not permission.
The decision, its safeguards and what was measured are in
[docs/archive/2026-09-providers.md](docs/archive/2026-09-providers.md).
**Next action:** written permission from Heureka's media contact, if its artwork is ever
wanted. Nothing is blocked on it now.

### Credential hygiene and rotation

Tracked in private notes outside this repo. The Finnkino token is fetched fresh at run
time and used within seconds, so there is no stored credential and nothing to rotate;
this item covers the rest.


## Blocked

### Helsinki is full at eight chains, and two candidates now trigger it

No colour in the L* band clears 14.4 dE00 against Helsinki's eight. Re-swept 2026-09-21
over the whole cube: 0 of the 94,359 in-band colours clear it, best reachable 12.12
(`#886098`, 12.1 against Gilda by `accent_check.py --candidate`).
`test_every_combined_city_pair_clears_the_floor` holds the city view without exception.
**Decided 2026-09-20 by the maintainer:** a full palette is **not** on its own a reason to
reject a Helsinki cinema.
**Kino K13 and Kino Helios are the real candidates**, both read and parsed against live
data on 2026-09-21 and neither registered: 4 timed rows on `ses.fi/kinok13/` and 22 exact
Kino Helios rows from Malmitalo's event service. The data and the parse are settled; only
the accent is not. Evidence:
[docs/research/ticketing-platforms.md](docs/research/ticketing-platforms.md).
**Next action:** the maintainer's, on what the city view does when a city is full. Nothing
here lowers the floor, widens the L* band or edits that test to fit a candidate.

### Kino Konepaja has no programme to read

A real Kinola tenant publishing no screening, so it gets a `SITES` entry the day it lists
one. Re-read 2026-09-20: `/naytokset/` now redirects to the front page, whose event list
still says "Ei tulevia tapahtumia." above a coming-soon grid, and the site states the
cinema is shut and reopening soon. The silence has a stated cause for the first time.
Evidence in [docs/research/kinola.md](docs/research/kinola.md); the classifier and the
three tenants that do publish are in
[docs/archive/2026-09-providers.md](docs/archive/2026-09-providers.md).
**Next action:** re-read the listing, at the front page now.

### Staleness monitor: the ping

The repo half is done, `scripts/check_staleness.py`: a pure function of a file and a
clock, answering "did a run happen", which `check_runs.py` cannot. Its threshold is
`STALE_H` from `index.html` and a test fails if the two drift apart.
**Next action:** the external ping that calls it. The schedule, the file location and the
recipient are machine-specific and live in the wrapper outside this repo, so this item
cannot close here.

### Kino Kaustinen has no screening to verify against

A real eTiketti tenant publishing none, so no ticket destination can be checked, which is
the rule six dead Nexxo links bought. Re-read 2026-09-20: "Ei ohjelmistoa saatavilla."
Blocked on the cinema's own programme, not on work here; it is one `SITES` entry the day
it lists a film. Evidence:
[docs/research/ticketing-platforms.md](docs/research/ticketing-platforms.md).
**Next action:** re-read on a later Monday.

### Search Console re-read

The five-day baseline is too thin to change anything on, and the queued "ohjelmisto"
experiment waits on it. Blocked twice over: the 2026-09-18 to 2026-10-02 window has not
closed, and no Search Console access exists from here.
**Next action:** read the same tables after 2026-10-02, once access exists. Evidence:
[docs/research/seo-and-search.md](docs/research/seo-and-search.md).

### Finnkino prices

Blocked by the access rule rather than by difficulty. The programme response the adapter
already reads carries no price field anywhere, scanning it for any key containing price,
amount, cost, ticket, fee, tariff or currency returns zero matches, and the obvious
ticket-type paths answer 404. The only route left is the seat-selection flow, which this
repo does not call or inventory.
The one route left open, a visitor-facing price *page*, is **deferred** by the maintainer
on 2026-09-16 for Finnkino and BioRex alike: neither is easily done. Nothing is probed and
nothing is scheduled. Evidence: [docs/research/prices.md](docs/research/prices.md).

### Iobio, Inkoo: readable only through two exceptions

The third host on The Events Calendar, and the one `tribe.py` does not read. Its films
carry no category of their own and are marked by an "IoBio:" title prefix, with each
screening duplicated across a Finnish and a Swedish calendar. Both exceptions are ones this
repo has written against: a word in a title is not a classifier, and a bilingual dedup has
to pick a canonical row, which double-publishes in one direction and drops a screening in
the other with nothing in a count to show it.
**What would change it:** Iobio publishing a film category of its own, or one calendar
rather than two. Then it is an ordinary `SITES` entry. Evidence:
[docs/research/ticketing-platforms.md](docs/research/ticketing-platforms.md).

### Kino Engel prices

The price rows are drawn by Johku's widget from an API that needs the widget's key. A
headless render was measured on 2026-09-13 at about 6 s a page for roughly 15 pages a run.
**Declined outright 2026-09-20 by the maintainer**, not merely deferred: no headless price
extraction on the local half. `price` and `aud` stay empty for Engel, and the one route
left open is the cinema or Johku publishing a feed.

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

- Precaching the app shell on install. **Declined 2026-09-20 by the maintainer**, and the
  recorded cache-deletion design is preserved: `sw.js` carries `/data/` across a version
  bump and deliberately does not carry `index.html`, so an old shell cannot come back as
  the offline fallback. The cost accepted with it is that a reader who updates and closes
  the tab has no page to launch offline until one online load. Record:
  [docs/archive/2026-09-app.md](docs/archive/2026-09-app.md).
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
- Bio Savoy's `accept-language: sv-AX,sv;q=0.9` and eTiketti's extra `accept` header. Both
  were left in place on 2026-09-19 when the twelve accidental page getters were folded
  into `common.get_text`: each has an obvious story and neither has a probe showing the
  host's response varies on it, and settling that is a read per host rather than a
  refactor. Measured per adapter in
  [docs/research/adapter-http.md](docs/research/adapter-http.md).
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
- A cross-host redirect escapes the host claim. `common._claim` claims the request's host
  before sending and `urlopen` follows redirects, so the target is read unpaced and
  outside `hosts_attempted`. Swept 2026-09-19 over all 31 committed provider logs: every
  hostname they name is its module's own `base` or `reads`, and none carries a `refused
  to` line. The claim is taken before the request, so a redirect's target would not show
  up there either way, which makes this no evidence rather than a proof. Two sites name
  no `base` at all, Kino Engel and Kino Akseli; both are local-half, where the cloud
  pool's base-less group does not apply.

**Ops and pages**

- A distance figure on the region rows. `km` was deleted on 2026-09-18 rather than
  re-measured: nothing read it, it was never published, and the one figure that was
  measured fitted neither metric the others fitted. A radius, if one is ever wanted, gets
  measured once on one stated metric with its source. The record is in
  [docs/archive/2026-09-providers.md](docs/archive/2026-09-providers.md).
- Rewriting the history to drop the `Co-Authored-By` lines an earlier tooling default
  added. Measured and declined 2026-09-18: the practice already stopped, the line is
  cosmetic attribution rather than a name or a secret, and a rewrite would falsify every
  commit SHA the decision records cite. The figures are in
  [docs/archive/2026-09-ops.md](docs/archive/2026-09-ops.md).
- A README workflow badge. Measured and declined 2026-09-20. `ci.yml` runs only on a push
  touching `index.html`, `sw.js`, `scripts/**` or `tests/**`, and this repository's
  ordinary push is data or pages, which none of those cover. A badge would therefore show
  the verdict from whenever code last changed, not the state of the repository, and it
  would be doing that right now: the newest `ci.yml` run on `main` is the failure on
  `fb3c6beb7`, whose cause was fixed in `165629c60` the same evening, and that fix touched
  only `pages/**` so it could not turn the run green. Reversible in one commit if it is
  wanted anyway.
- Moving the local fetch off the laptop. **Decided 2026-09-20 by the maintainer:** local
  fetching stays on the laptop, and replacing the infrastructure is outside this
  repository. The constraint is unchanged and is why the item existed: eight providers
  block or challenge datacenter addresses (Finnkino, Kino Akseli, Kino Engel, Joutsan
  Kino, Savon Kinot, Kino Regina, Cine, Elokuvateatteri Star), so 30 of 116 venues ride on
  one machine, and no cloud VM keeps that coverage.
- The stale red `ci.yml` verdict on `main`, cleared 2026-09-20 by `2b2d81102` and kept
  for the mechanism. The failure was on `fb3c6beb7`, from 34 pages an `enrich_tmdb` run
  left stale; the fix landed hours later in `165629c60`, a `pages/**` commit outside the
  workflow's path filter, so it could not turn that run green. It stayed red until an
  unrelated code push re-ran the workflow. No no-op commit was used, and none is to be.
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

## Documentation state (2026-09-21, twenty-first pass)

Counts in README and here are re-measured against `data/`, the registry and `sitemap.xml`
on every provider change, because carried-over counts have been wrong repeatedly: the city
count, the poster count, the page rewrite frequency, the venue and provider counts, and
once a count stated twice in one file where only one copy moved.

Latest, re-measured 2026-09-21 after Kino Akustiikka and Kino-Huovi were fetched and their
snapshot committed. The twentieth pass measured the same day, before that batch, and is
superseded by this one. Declared and committed agree at 132 venues, so nothing is declared
and unpublished. The poster figures and the mirrored file count move with every run and are
the rows that go stale without anything being wrong.

| | |
|---|---:|
| providers / venues / cities (declared) | 81 / 132 / 96 |
| venues in committed data | 132 |
| local providers (venues) | 12 (34) |
| venues per adapter, largest | eTiketti 30, Finnkino 17, Nexxo 13, BioRex 12, Johku 7 |
| generated pages per language | 149 |
| sitemap URLs | 299 |
| poster references (shows / films-extra) | 4294 (3891 / 403) |
| off-origin poster references | 0 |
| mirrored poster files | 1376 |
| `sw.js` CACHE | `leffavuoro-v211` |

Pages per language is the sitemap's figure: 132 venue pages plus the 17 cities with more
than one venue. Theatre directories on disk outnumber it by two, the Studio 123 redirect
stubs from `737bf3138`, kept and deliberately left out of the sitemap.

README carries the same provider, venue, city, page and sitemap figures and was current
when this pass measured it. Poster counts live here and not in README: they move with every
run, and stating them there made the file wrong within hours twice on 2026-09-14. README
carries the behaviour instead, which does not move.

Earlier passes, and what each of them measured, are in
[docs/archive/2026-09-ops.md](docs/archive/2026-09-ops.md).

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
| [docs/research/runner-challenges.md](docs/research/runner-challenges.md) | why a cloud run can fail on many unrelated cinemas at once, and what it costs |

**Accepted rules** were not moved into either. They were already in
[CLAUDE.md](CLAUDE.md) and [DESIGN.md](DESIGN.md), which are authoritative, and the
duplicate prose here is gone rather than copied. The one that used to live here and is
worth naming: "Access and ethics", now in `CLAUDE.md`, with the historical record of how
each rule was arrived at in `docs/archive/2026-09-ops.md`.

Two anchors that used to point inside this file and now point into the archive:
"Seven backlog items closed without building them" and "The landing pages belong to the
product" are both in
[docs/archive/2026-09-app.md](docs/archive/2026-09-app.md).
