# Leffavuoro

Finnish cinema showtimes as a fast, installable web page.

**Live at https://leffavuoro.fi**

## What it does

Showtimes for 76 venues in 52 cities across 34 providers: Finnkino, BioRex,
Kinoset, Kotkan Leffat, Riviera, Savon Kinot, Gilda, Cinema Orion, Kino Engel,
Bio Rex Kokkola, Kino Akseli, Kinopirtti, Leffabuumi, Studio 123 Järvenpää,
Studio 123 Kouvola, Kino 123, Ihme Kompleksi, Kinotar 123, Kino Juha, Bio Grand,
Bio Vuoksi, Kino Iiris, K-Kino, Joutsan Kino, Bio Grani, Kino Aurora, Kino
Hirvi, Bio Säde, Kino Marilyn, Kino Olympia, Järvelän Kino, Kino Metso,
Cinema Niagara and Heureka. Films
with posters, TMDB ratings, age limits, runtimes, genres, languages, plus ticket
prices and sold-out marks where the cinema publishes them. Tapping a showtime
opens that cinema's own booking page, or the ticket shop where the screening is
included in a general admission ticket (Heureka's planetarium).

Cities with more than one venue get a combined view that merges the same film
across chains into one card. The theatre picker is searchable, and "jarvela"
finds Järvelä. Installs as a PWA and serves the last loaded schedule offline.
Venue, home theatre, day, language and theme live in `localStorage`.

## How it works

No cinema API is called at load time. A pipeline fetches ahead of time and
commits static JSON, which GitHub Pages serves from the same origin: no CORS, no
keys in the client, no third-party requests. Five providers can only be read
from an ordinary connection, so the pipeline runs in two places. One adapter can
serve many providers, because most small cinemas run one of a few ticketing
platforms:

| Adapter | Providers | Venues | Auth | Runs |
|---|---|---|---|---|
| Finnkino (Vista OCAPI) | 1 | 17 | short-lived token | Local |
| eTiketti | 18 | 26 | none | GitHub Actions; Savon Kinot and Joutsan Kino local |
| BioRex | 1 | 12 | none | GitHub Actions |
| Nexxo | 8 | 13 | none | GitHub Actions |
| Riviera | 1 | 2 | none | GitHub Actions |
| Gilda (MyCloudCinema) | 1 | 2 | none | GitHub Actions |
| Cinema Orion | 1 | 1 | none | GitHub Actions |
| Kino Engel | 1 | 1 | none | Local |
| Kino Akseli | 1 | 1 | none | Local |
| Heureka | 1 | 1 | none | GitHub Actions |

A local machine runs the local half four times a day, pushes, then triggers the
cloud workflow. It takes a fresh Finnkino token from a real browser session each
run, so there is no stored credential and nothing to rotate. There is no cloud
fallback: a runner cannot obtain a token at all, since the site answers
Cloudflare 403 to datacenter IPs. Routing is per site, not per adapter, which is
how one eTiketti cinema can be local while the other sixteen run on Actions.

Each fetcher writes its exit code to its own committed log rather than aborting,
so one failing provider never blocks the rest. **The committed `run.log` and
`run-{module}.log` are the authoritative record; the Actions logs are not.**
`enrich_tmdb.py` runs last and fills
in ratings, trailers, synopses and posters a provider does not supply, merging
rather than overwriting the cinema's own text.

Why any of it is shaped this way is in [IDEAS.md](IDEAS.md), along with the
per-provider research and the approaches tried and rejected.

## Files

    index.html                       the whole app
    sw.js                            service worker
    manifest.webmanifest             PWA manifest
    fonts/                           self-hosted Archivo subsets + OFL licence
    robots.txt, sitemap.xml          crawl rules; the sitemap is generated
    teatteri/, kaupunki/, en/        generated pages (committed by CI)
    data/                            generated JSON and posters (committed by CI)

    scripts/fetch_data.py            Finnkino fetcher (Vista OCAPI)
    scripts/providers/registry.py    single source of truth for every provider
    scripts/providers/run.py         generic runner for every adapter
    scripts/providers/{name}.py      one adapter per provider or platform
    scripts/providers/common.py      shared fetch with retry, atomic writes
    scripts/providers/enrich_tmdb.py TMDB ratings, trailers, synopses, posters
    scripts/providers/mirror_posters.py  mirrors hot-linked posters same-origin
    scripts/build_providers.py       registry -> data/providers.json
    scripts/build_pages.py           renders the indexable pages
    scripts/accent_check.py          chain accent separation, incl. deuteranope
    scripts/check_inline_js.py       node --check on the inline script and sw.js
    scripts/check_runs.py            fails when any committed run log did not end exit=0
    scripts/check_staleness.py       fails when data/areas.json is older than 8 h
    scripts/indexnow.py              tells IndexNow which generated pages a push changed

    tests/                           python3 -m unittest discover -s tests
    .github/workflows/biorex.yml     all cloud providers + enrichment
    .github/workflows/logs.yml       runs check_runs.py on any push that touches a log
    .github/workflows/indexnow.yml   runs indexnow.py on page changes
    .github/workflows/ci.yml         suite, JS check and regeneration, on code pushes

## Data shape

Every provider writes the same thing, so the client has no per-provider code.

    data/providers.json          [{id, label, host, accent, book}]
    data/area-{venueId}.json     {generated, dates[], horizon, shows[]}
    data/venues-{provider}.json  {generated, oldest, status, stale[], unverified[],
                                  provider, venues[{id,name,short,city}]}
    data/films-extra.json        title-keyed synopses, posters, trailers
    data/tmdb-genres.json        {fi,sv,en} genre id -> name, for rendering `gids`
    data/areas.json              Finnkino venue list (legacy shape, numeric ids)

A showtime carries `eventId, title, original, start (ISO, Europe/Helsinki),
theatre, aud, url, img, len, rating, age, genres, gids, lang, method, soldOut,
price, provider, venue, tmdbId, tmdb, votes, tr`. The last three are TMDB's
score, its vote count and a trailer, written by the enrichment step.

Two fields are easy to confuse. `rating` is the **film's** age classification;
`age` is a limit the **screening** adds on top: a licensed auditorium can be 18+
whatever the film is rated, and Heureka's planetarium admits from five. `tmdbId`
and `gids` are written only for exact TMDB matches, because a weak id folds two
different films into one card.

On a provider file, `generated` is when it was written and `oldest` is its
weakest venue's timestamp. The health line ages on `oldest`; `status` is `ok` or
`partial`, and `stale`/`unverified` name the venues behind it.

## Adding a provider

1. Write `scripts/providers/{name}.py` exposing two things:

       SITES             [{provider, label, venues:[{id, name, short, city}],
                          base (optional, see below)}]
       fetch_site(site)  -> {venue_id: [show, ...]}

2. Add an entry to `scripts/providers/registry.py`: id, label, host, accent,
   `book` mode (`buy`, `reserve`, `door`, `list` or `admission`), module, and
   `where` it runs (`cloud` or `local`).

Nothing else needs editing. The workflow loops over `registry.py --cloud` and
the client reads `data/providers.json`. One module can serve several providers,
which is why the provider id sits on the site: `etiketti` serves eighteen
providers today and `nexxo` eight.

`base` is the host the adapter reads, and it is optional: several single-site
adapters keep their host inside `fetch_site` and work fine. What it buys is
concurrency. `run.py` paces on `base`, reading sites on different hosts at the
same time and sites sharing a host one after the other, and it cannot tell two
unnamed hosts apart -- so every site in a module without a `base` is grouped
together and read one at a time.

A module with more than one site should therefore name the host it actually
reads, or its sites gain nothing from the pool. Two entries against the *same*
server must name it, or they would be read at twice the rate their adapter paces
for. Where a visitor is sent can be a different host and belongs in `site`.

**Check for an existing platform first.** A cinema running MyCloudCinema, Nexxo
or eTiketti needs a `SITES` entry against the existing adapter; `vista.py` keeps
a working Vista XML parser with no sites, since the last Finnish deployment
migrated to eTiketti. Adding a venue to an existing provider is one line. Pick
the accent with `accent_check.py`; do not judge it by eye. Fetch the page a
showtime will link to and check it answers before writing it down: the ticket
links of six Nexxo sites once 404'd because one site's path was copied onto all
of them.

    python3 scripts/providers/run.py biorex
    python3 scripts/providers/run.py --where cloud
    python3 -m unittest discover -s tests

## Indexable pages

The app is one JS-rendered URL, so `build_pages.py` renders static pages from
the same committed JSON at the end of every run:

    /teatteri/{slug}/     one venue        /en/theatre/{slug}/
    /kaupunki/{slug}/     a whole city     /en/city/{slug}/

86 per language, 173 sitemap URLs: 76 venues plus the ten cities with more than
one venue, and the front page. A one-venue city would duplicate its venue page
and compete with it, so those get the city into the venue page's title and
address instead.

Each page carries real HTML showtimes, `hreflang` pairs, and
`ScreeningEvent`/`MovieTheater` structured data. No `aggregateRating`: the
ratings are TMDB's, and presenting another party's ratings as the page's own is
against Google's guidelines, so it appears as credited text. Every page links
into the app as `/?area={venueId}&lang={fi|en}`, so a reader lands on the
cinema or city they were reading about, in the language they were reading it
in, and the app's saved favourite is left alone.

Since 2026-09-02 the pages share the app's look: its wordmark, its typeface
(the same self-hosted Archivo files, one same-origin request), its light and
dark tokens following the OS, its FI · SV · EN selector, and ticket-shaped
showtimes. The card is the app's: score ring, rating, genres, runtime, and the
language once when every screening shares it, on the screening when they differ.
A price is never the film's: it sits on the screening's ticket. A theatre page's
ticket shows time, room and price, and ends in a 56 px price compartment behind
the dashed seam and its notches, blank when the cinema publishes none, so a priced
and an unpriced screening keep one shape. A city page's ticket puts a 64 px time
compartment first, then cinema and room, then the price where there is one and
no compartment where there is none, with a colour rule per chain, and a second
column only where a 240 px ticket fits. Tickets are 40 px tall, in the app and
here. Swedish has no static page
yet, so its selector entry opens the app on the same area in Swedish. The theme
toggle reads and writes the same `kino-theme` key as the app, so a choice made
on either side carries to the other; that is the only script on the page, and
it renders nothing. Nothing volatile, so a page is rewritten only when its
showtimes change.

## Privacy

No accounts, cookies, analytics, tracking or ads. Preferences stay in
`localStorage`. Schedule data is static JSON from this origin, so browsing tells
no cinema anything.

**A page load makes no third-party requests.** Counted 2026-09-05: all 4297
poster references resolve to `data/posters/` on this origin — 4159 on showtimes
and 138 in `films-extra.json`, across 650 mirrored files, none off-origin — and
the typeface is served from `fonts/`. Every `<img>` carries
`referrerpolicy="no-referrer"`.

That was false until 2026-08-29, when the typeface came from Google Fonts and
about a third of the posters were hot-linked from the cinemas' hosts and
`image.tmdb.org`. Both are mirrored now. This paragraph stays so the privacy
claim can be checked against when it was wrong.

Two things reach other hosts. Tapping a showtime or a trailer hands you to the
cinema's booking page or to YouTube. GitHub Pages serves the site and logs
requests, as any host would.

## Data sources

Schedule data belongs to the respective cinemas — the 34 providers listed at the
top of this page. Ratings, trailers and fallback synopses and posters come from
TMDB. Every showtime links to the cinema's own booking page, and the footer
credits the source being displayed.

Every provider is read through the same public interface its own site uses, under
an honest User-Agent, **on a schedule that no visitor can influence**. Unrelated
cinemas are read at the same time; any one cinema is read one request at a time,
at the pace its own adapter sets. The app
loads static JSON from this origin, so browsing it, reloading it or leaving it
open reaches no cinema. That property holds by construction: the client has no
code that calls a cinema.

Data is refreshed by a scheduled job and by a refresh triggered after each local
collection run. Under the normal configured cadence the five local providers are
read four times a day, and the cloud providers usually up to eight, since runs
are queued rather than merged. **Those figures describe the typical cadence and
the configuration does not enforce them.** Scheduled execution is best-effort
and may be delayed or missed, and a manual refresh adds runs.

Booking, payment and administrative endpoints are never called. If a cinema would
rather not be included, removing it is one registry entry; see Contact below.

This is a personal, non-commercial project with no affiliation to any of them.

## Licence

    Leffavuoro
    Copyright (C) 2026  Shady-Dev
    Licensed under the GNU Affero General Public License, version 3 or later.

The **code** is [AGPL-3.0](LICENSE). Use it, change it, run it. The condition
that matters for a site like this: deploy a modified version where people reach
it over a network and you must offer them its source. That is AGPL section 13,
and it is why AGPL rather than GPL-3.0, whose copyleft triggers on a
distribution that hosting a fork never performs.

**The licence covers the code and nothing else here.** Not mine to relicense:

    data/area-*.json     showtimes, belonging to the cinemas listed above
    data/posters/        poster art from the cinemas' own CDNs and TMDB
    fonts/archivo-*      Archivo, under the SIL Open Font Licence (fonts/OFL.txt)

Forking the code carries no right to that material. Read the providers yourself,
under your own name and User-Agent, and see Access and ethics in
[IDEAS.md](IDEAS.md) first.

## Contact

**leffavuoro@gmail.com**

The pipeline reads every provider as `Leffavuoro/1.0 (+https://leffavuoro.fi)`.
That URL resolves to this page so a cinema can identify who is reading them and
reach the address above.

If you run one of the cinemas above and would rather not be included, say so and
the adapter comes out. It is one entry in `scripts/providers/registry.py`, and
no reason has to be given. Questions about how a schedule is read, or a wrong
showtime, are welcome at the same address.
