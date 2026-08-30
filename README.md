# Leffavuoro

Finnish cinema showtimes as a fast, installable web page.

**Live at https://leffavuoro.fi**

## What it does

Showtimes for 48 venues in 33 cities across eleven providers: Finnkino,
BioRex, Kinoset, Kotkan Leffat, Riviera, Savon Kinot, Gilda, Cinema Orion, Kino
Engel, Bio Rex Kokkola and Kino Akseli. Pick a venue and a date, see films with
posters, TMDB ratings, age limits, runtimes, genres, languages, and ticket
prices and sold-out marks where the cinema publishes them. Tapping a
showtime opens that cinema's own booking page.

Cities with more than one venue also get a combined view ("Kaikki Helsinki"). It
merges the same film across chains into one card, labels every showtime with its
venue, and can filter by chain.

Works as a PWA: add to home screen, opens fullscreen, serves the last loaded
schedule when offline. Your venue, starred home theatre, day, language and theme
are kept in `localStorage`. See [Privacy](#privacy) for what does and does not
leave the device.

## How it works

The page never calls a cinema's schedule API at load time. A pipeline fetches
everything ahead of time and commits static JSON, which GitHub Pages serves from
the same origin. That means no CORS and no API keys in the client. Posters and
the typeface are served from this origin too, so a page load reaches no other
host at all.

Three providers block datacenter IPs, so the pipeline runs in two places:

| Provider | Venues | Auth | Runs |
|---|---|---|---|
| Finnkino | 17 | short-lived token | Local (blocks datacenter IPs) |
| BioRex | 12 | none | GitHub Actions |
| Kinoset | 3 | none | GitHub Actions |
| Kotkan Leffat | 2 | none | GitHub Actions |
| Riviera | 2 | none | GitHub Actions |
| Savon Kinot | 6 | none | GitHub Actions |
| Gilda | 2 | none | GitHub Actions |
| Cinema Orion | 1 | none | GitHub Actions |
| Kino Engel | 1 | none | Local (blocks datacenter IPs) |
| Kino Akseli | 1 | none | Local (blocks datacenter IPs) |

A local machine handles those three, four times a day. It gets a fresh
short-lived Finnkino token from a real browser session, runs
`scripts/fetch_data.py` and `scripts/providers/run.py engel kinoakseli`, pushes
the data, then triggers the cloud workflow.

There is no cloud fallback for Finnkino. A runner cannot get a token at all,
because the site answers Cloudflare 403 to datacenter IPs. The workflow that
claimed to be a fallback failed on every run for two days before it was removed.
If Finnkino data goes stale the app says so: the per-provider health line turns
amber past 8 h. Machine setup and scheduling live in local notes, not in this
repo.

Every fetcher captures its exit code to its own committed log instead of
aborting the script, so one failing provider never blocks the others from
publishing. Those logs (`run.log`, `run-{module}.log`) are the ones to read. The
Actions logs are not.

`scripts/providers/enrich_tmdb.py` runs last and fills in TMDB ratings,
trailers, Finnish synopses and posters for anything a provider does not supply
itself. It merges, and never overwrites a cinema's own text.

TMDB cannot be searched by Finnish distributor title. That pass strips event
prefixes and format noise from the query, and falls back to `tmdb-aliases.json`
for what is left. Titles that still find nothing are named in `run-enrich.log`.
Two other lists there are worth reading: **weak match**, where no result matched
the title exactly and the most popular one was taken, and **rating held back**,
where a rating was hidden for having fewer than 25 votes.

Genres come from TMDB ids, not from provider strings. The chains disagree with
each other (four spellings for the family genre), and their strings stay Finnish
in English mode. `data/tmdb-genres.json` maps ids to names per language.

## Files

    index.html                       the whole app
    manifest.webmanifest             PWA manifest
    robots.txt                       crawl rules; /data and run-*.log are not pages
    sitemap.xml                      generated; every venue and city page, both languages
    scripts/build_pages.py           renders the indexable pages from the committed JSON
    teatteri/, kaupunki/, en/        generated pages (committed by CI)
    sw.js                            service worker (network-first)
    CNAME                            custom domain for GitHub Pages
    scripts/fetch_data.py            Finnkino fetcher (Vista OCAPI)
    scripts/providers/registry.py    single source of truth: id, label, host, accent,
                                     book mode, adapter module, where it can run
    scripts/build_providers.py       registry -> data/providers.json
    scripts/providers/run.py         generic runner for every adapter
    scripts/providers/{name}.py      one adapter per provider or platform
    scripts/providers/common.py      shared fetch with retry, atomic writes
    scripts/providers/enrich_tmdb.py TMDB ratings, trailers, synopses, posters
    scripts/providers/tmdb-aliases.json  overrides for titles TMDB cannot be searched by
    scripts/providers/synmerge.py    shared synopsis merge helper
    scripts/providers/strands.py     event strand prefixes, split off titles into method
    scripts/providers/mirror_posters.py  mirrors hot-linked posters into data/posters/
    scripts/accent_check.py          chain accent separation, normal + deuteranope
    tests/                           python3 -m unittest discover -s tests
    .github/workflows/biorex.yml     all cloud providers + enrichment
    data/                            generated JSON and posters (committed by CI)
    fonts/                           self-hosted Archivo woff2 subsets + OFL licence
    IDEAS.md                         architecture notes, provider research, backlog

## Data shape

Every provider writes the same thing, so the client needs no per-provider code.
All it takes from the registry is a display name and an accent colour.

    data/providers.json          [{id, label, host, accent, book}] for the client
    data/area-{venueId}.json     {generated, dates[], horizon, shows[]}
    data/venues-{provider}.json  {generated, provider, venues[{id,name,short,city}]}
    data/films-extra.json        title-keyed synopses, posters, trailers
    data/tmdb-genres.json        {fi,en} genre id -> name, for rendering `gids`
    data/areas.json              Finnkino venue list (legacy shape, numeric ids)

A showtime carries: `title, start (ISO, Europe/Helsinki), theatre, aud, url,
img, len, rating, age, genres, gids, lang, method, soldOut, price, provider,
venue, tmdbId`.

`rating` is the film's age classification. `age` is a separate limit that the
screening itself adds: a licensed bar auditorium is 18+ whatever the film is
rated, so it belongs on the showtime and not on the film.

`tmdbId` and `gids` are written only for exact TMDB matches. A weak id would
fold two different films into one card in a combined city view.

`lang` uses Finnkino's convention (`FI-A`, `FI-S`) for every provider, so one
filter works across all of them.

## Adding a provider

1. Write `scripts/providers/{name}.py` exposing two things:

       SITES             [{provider, label, venues:[{id, name, short, city}]}]
       fetch_site(site)  -> {venue_id: [show, ...]}

   One module can serve several providers, which is why the provider id sits on
   the site and not on the module (`nexxo` serves Kinoset, `etiketti` serves
   Kotkan Leffat).
2. Add an entry to `scripts/providers/registry.py`: id, label, host, accent,
   `book` mode, the module name and `where` it can run (`cloud` or `local`).

Nothing else needs editing. The cloud workflow loops over `registry.py --cloud`,
and the client reads `data/providers.json`. A `local` provider is added to the
local wrapper instead, because its site blocks datacenter IPs.

Adding a venue to an existing provider is a one-line entry in that adapter's
`SITES`/`VENUES`.

Check for an existing platform before writing a parser. A cinema running Vista,
MyCloudCinema, Nexxo or eTiketti is a `SITES` entry against an adapter that is
already here.

Run one by hand with:

    python3 scripts/providers/run.py biorex
    python3 scripts/providers/run.py --where cloud

## Token maintenance

There is none to do. The Finnkino token is fetched fresh at every run and used
within seconds, so its short expiry does not matter. `TMDB_SECRET_TOKEN` is an
ordinary TMDB read token in the repository secrets.

The local wrapper hard-resets its checkout to `origin/main` at the start of
every run, so edits made inside that clone do not survive. The wrapper itself
lives outside the clone.

## Indexable pages

The app is one JS-rendered URL, so by itself it is a single entry in a search
index. `scripts/build_pages.py` renders static pages from the same committed
JSON the app reads, at the end of every pipeline run:

    /teatteri/{slug}/     one venue        /en/theatre/{slug}/
    /kaupunki/{slug}/     a whole city     /en/city/{slug}/

53 pages in each language: 48 venues, plus the five cities that have more than
one venue (Espoo, Helsinki, Kotka, Savonlinna, Tampere). A city page for a
one-venue city would just be the venue page at a second URL, and the two would
compete with each other. Single-venue cities get the city into the venue page's
title and JSON-LD address instead.

Each page carries real HTML showtimes for the next few days, `hreflang` pairs,
and `ScreeningEvent` / `MovieTheater` structured data for today and tomorrow.

There is no `aggregateRating` in the markup. The ratings are TMDB's, and
presenting another party's ratings as the page's own is against Google's
guidelines, so the rating appears as credited text instead.

These pages make no third-party requests either: inline CSS, system fonts, and
only same-origin posters, in the markup as well as in the structured data. A
poster that failed to mirror is dropped from `<img>` but kept in the JSON-LD,
since a URL in markup is fetched by the crawler and never by the reader's
browser.

A page is rewritten only when its bytes change. That happens more often than
intended. The pages hold no timestamp and no sold-out state, but the schedule
underneath them shifts through the day as cinemas drop screenings that have
started, so a typical run rewrites 16 to 100 of the 104 pages and costs 25 to
130 kB of packed history.

Every page links into the app as `/?area={venueId}` (or `/?area=city:{City}`),
so arriving from a search opens on that venue instead of on whatever was last
browsed.

## Privacy

No accounts, no cookies, no analytics, no tracking scripts, no ads. Your venue,
starred home theatre, day, language and theme live in `localStorage` and are
never transmitted. Schedule data is static JSON from this origin, so browsing
showtimes tells no cinema anything.

**A page load makes no third-party requests.** Measured 2026-08-29: every poster
reference in the committed data comes from `data/posters/` on this origin (3274
references that day, across 213 distinct images), and the typeface is served
from `fonts/`. Every `<img>` also carries `referrerpolicy="no-referrer"`.

That claim was false until 2026-08-29, and this section said so at the time. The
typeface came from Google Fonts on every visit, and about a third of the posters
were hot-linked from the cinemas' own hosts (`mycloudcinema.com`,
`cdn.etiketti.app`, `kinoset.fi`, an Azure blob host) and from `image.tmdb.org`.
The pipeline now mirrors both. The history stays here because a privacy claim is
only as good as the record of when it was wrong.

One thing does leave this origin, by design: tapping a showtime or a trailer
hands you off to the cinema's booking page or to YouTube.

GitHub Pages serves the site and therefore logs requests, the same as any host
would.

## Data sources

Schedule data belongs to the respective cinemas: Finnkino Oy, BioRex Cinemas,
Kinoset, Kotkan Leffat, Riviera Cinemas, Savon Kinot, Gilda, Cinema Orion, Kino
Engel, Bio Rex Kokkola and Kino Akseli. Ratings, trailers and fallback synopses
and posters come from TMDB. Every showtime links to the cinema's own booking
page, and the footer credits the source being displayed.

Every provider is read through the same public interface its own site uses, four
times a day regardless of traffic. Booking, payment and administrative
endpoints are never called. If a cinema would rather not be included, removing
it is one registry entry; see Contact below.

This is a personal, non-commercial project with no affiliation to any of them.

## Licence

The **code** is [AGPL-3.0](LICENSE). Use it, change it, run it. The one condition
that matters for a site like this one: if you deploy a modified version where
people can reach it over a network, you have to offer them its source. That is
AGPL section 13, and it is the reason for AGPL over plain GPL-3.0: GPL's
copyleft triggers on distribution, and hosting a fork distributes nothing, so a
GPL fork of a website could stay closed. Practically, a modified deployment
should link back to its own source the way this one links to `LICENSE`.

**The licence covers the code and nothing else in this repository.** Three kinds
of file here are not mine to relicense:

    data/area-*.json     showtimes, belonging to the cinemas listed above
    data/posters/        poster art from the cinemas' own CDNs and TMDB
    fonts/archivo-*      Archivo, under the SIL Open Font Licence (fonts/OFL.txt)

Forking the code does not carry any right to that material. Read the providers
yourself under your own name and User-Agent, the way this does, and see
[Access and ethics](IDEAS.md) before you point it at anyone.

## Contact

**tiles-39nomads@icloud.com**

The pipeline reads every provider under the User-Agent
`Leffavuoro/1.0 (+https://leffavuoro.fi)`. That URL is there so a cinema can find
out who is reading them, which only works if there is something to find. This is
it.

If you run one of the cinemas listed above and would rather not be included, say
so at that address and the adapter comes out. It is one entry in
`scripts/providers/registry.py`, the change is a few minutes, and no reason has
to be given. The same address is on every page of the site, in the app footer
and on the generated venue and city pages.

Questions about how a schedule is read, a wrong showtime, or anything else are
welcome at the same place.
