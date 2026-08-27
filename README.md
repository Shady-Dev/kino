# Leffavuoro

Finnish cinema showtimes as a fast, installable web page.

**Live at https://leffavuoro.fi**

## What it does

Showtimes for **37 venues in 27 cities** across six providers: Finnkino,
BioRex, Kinoset, Kotkan Leffat, Riviera and Kino Akseli. Pick a venue and a
date, see films with posters, TMDB ratings, age limits, runtimes, genres,
languages and, where the cinema publishes them, ticket prices and seat
availability. Tapping a showtime opens that cinema's own booking page.

Cities with more than one venue also get a **combined view** ("Kaikki
Helsinki"), which merges the same film across chains into one card, labels
every showtime with its venue, and lets you filter by chain.

Works as a PWA: add to home screen, opens fullscreen, serves the last loaded
schedule when offline. Remembers your venue, starred home theatre, day,
language and theme in `localStorage`. Nothing leaves the device.

## How it works

The page never calls a cinema at load time. A pipeline fetches everything
ahead of time and commits static JSON, which GitHub Pages serves from the
same origin. No CORS, no third-party requests, no API keys in the client.

Providers run in one of two places, because two of them block datacenter IPs:

| Provider | Venues | Auth | Runs |
|---|---|---|---|
| Finnkino | 17 | 12 h JWT scraped at run time | Mac ([redacted]) |
| BioRex | 12 | none | GitHub Actions |
| Kinoset | 3 | none | GitHub Actions |
| Kotkan Leffat | 2 | none | GitHub Actions |
| Riviera | 2 | none | GitHub Actions |
| Kino Akseli | 1 | none | Mac ([redacted] elsewhere) |

The Mac runs `~/kino-auth/localfetch.sh` on a [redacted] schedule four times a
day: it fetches a fresh Finnkino token via [redacted] driving real Chrome,
runs the Finnkino and Kino Akseli fetchers, pushes the data, then triggers
the cloud workflow with `dispatch_cloud.sh`. GitHub's own cron is left
enabled as a fallback but has proved unreliable.

A final pass (`scripts/providers/enrich_tmdb.py`) fills in TMDB ratings,
trailers, Finnish synopses and posters for anything a provider does not
supply itself. It **merges** and never overwrites a cinema's own text.

TMDB cannot be searched by Finnish distributor title, so that pass strips
event prefixes and format noise from the query and falls back to
`tmdb-aliases.json` for the rest. Titles that still find nothing are named in
`run-enrich.log`.

## Files

    index.html                       the whole app
    manifest.webmanifest             PWA manifest
    sw.js                            service worker (network-first)
    CNAME                            custom domain for GitHub Pages
    scripts/fetch_data.py            Finnkino fetcher (Vista OCAPI)
    scripts/providers/registry.py    single source of truth: id, label, host, accent,
                                     book mode, adapter module, where it can run
    scripts/build_providers.py       registry -> data/providers.json
    scripts/providers/run.py         generic runner for every adapter
    scripts/providers/{name}.py      one adapter per provider or platform
    scripts/providers/enrich_tmdb.py TMDB ratings, trailers, synopses, posters
    scripts/providers/tmdb-aliases.json  overrides for titles TMDB cannot be searched by
    scripts/providers/synmerge.py    shared synopsis merge helper
    .github/workflows/fetch.yml      Finnkino (cron + dispatch)
    .github/workflows/biorex.yml     all cloud providers + enrichment
    data/                            generated JSON and posters (committed by CI)
    IDEAS.md                         architecture notes, provider research, backlog
    cf-worker/                       dead end, kept for reference (see below)

## Data shape

Every provider writes the same thing, so the client has no per-provider code
beyond a display name and an accent colour:

    data/providers.json          [{id, label, host, accent, book}] for the client
    data/area-{venueId}.json     {generated, dates[], horizon, shows[]}
    data/venues-{provider}.json  {generated, provider, venues[{id,name,short,city}]}
    data/films-extra.json        title-keyed synopses, posters, trailers
    data/areas.json              Finnkino venue list (legacy shape, numeric ids)

A showtime carries: `title, start (ISO, Europe/Helsinki), theatre, aud, url,
img, len, rating, genres, lang, method, soldOut, price, provider, venue`.

`lang` uses Finnkino's convention (`FI-A`, `FI-S`) for every provider, so one
filter works across all of them.

## Adding a provider

1. Write `scripts/providers/{name}.py` exposing two things:

       SITES             [{provider, label, venues:[{id, name, short, city}]}]
       fetch_site(site)  -> {venue_id: [show, ...]}

   One module can serve several providers, which is why the provider id lives
   on the site rather than the module (`nexxo` serves Kinoset, `etiketti`
   serves Kotkan Leffat).
2. Add an entry to `scripts/providers/registry.py`: id, label, host, accent,
   `book` mode, the module name and `where` it can run (`cloud` or `mac`).

That is all. The cloud workflow loops over `registry.py --cloud`, so it needs
no edit, and the client reads `data/providers.json`, so `index.html` needs no
edit either. A `mac` provider goes into `localfetch.sh` instead, because the
site blocks datacenter IPs.

Adding a **venue** to an existing provider is a one-line entry in that
adapter's `SITES`/`VENUES`.

Run one by hand with:

    python3 scripts/providers/run.py biorex
    python3 scripts/providers/run.py --where cloud

## Token maintenance

None. The Finnkino JWT is fetched fresh at every run and used within seconds,
so its 12-hour expiry no longer matters. `TMDB_SECRET_TOKEN` is a normal TMDB
read token in the repository secrets.

`cf-worker/worker.js` was an attempt to fetch the token from Cloudflare's
network instead of a residential IP. It is not deployed and not used.

## Data sources

Schedule data belongs to the respective cinemas: Finnkino Oy, BioRex Cinemas,
Kinoset, Kotkan Leffat, Riviera Cinemas and Kino Akseli. Ratings, trailers and
fallback synopses and posters by TMDB. Every showtime links to the cinema's own
booking page, and the footer credits the source being displayed.

This is a personal, non-commercial project with no affiliation to any of them.
Fetches run four times a day regardless of visitor numbers.
