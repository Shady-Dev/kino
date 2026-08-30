# Leffavuoro

Finnish cinema showtimes as a fast, installable web page.

**Live at https://leffavuoro.fi**

## What it does

Showtimes for 63 venues in 44 cities across 24 providers: Finnkino, BioRex,
Kinoset, Kotkan Leffat, Riviera, Savon Kinot, Gilda, Cinema Orion, Kino Engel,
Bio Rex Kokkola, Kino Akseli, Kinopirtti, Leffabuumi, Studio 123 Järvenpää,
Studio 123 Kouvola, Kino 123, Ihme Kompleksi, Kinotar 123, Kino Juha, Bio Grand,
Bio Vuoksi, Kino Iiris, K-Kino and Bio Grani. Films with posters, TMDB ratings, age limits,
runtimes, genres, languages, plus ticket prices and sold-out marks where the
cinema publishes them. Tapping a showtime opens that cinema's own booking page.

Cities with more than one venue get a combined view that merges the same film
across chains into one card. Installs as a PWA and serves the last loaded
schedule offline. Venue, home theatre, day, language and theme live in
`localStorage`.

## How it works

No cinema API is called at load time. A pipeline fetches ahead of time and
commits static JSON, which GitHub Pages serves from the same origin: no CORS, no
keys in the client, no third-party requests. Three providers block datacenter
IPs, so it runs in two places.

| Provider | Venues | Auth | Runs |
|---|---|---|---|
| Finnkino | 17 | short-lived token | Local |
| BioRex | 12 | none | GitHub Actions |
| Savon Kinot | 6 | none | GitHub Actions |
| Kinoset | 3 | none | GitHub Actions |
| Kotkan Leffat | 2 | none | GitHub Actions |
| Riviera | 2 | none | GitHub Actions |
| Gilda | 2 | none | GitHub Actions |
| Cinema Orion | 1 | none | GitHub Actions |
| Bio Rex Kokkola | 1 | none | GitHub Actions |
| Kino Engel | 1 | none | Local |
| Kino Akseli | 1 | none | Local |

A local machine runs those three four times a day, pushes, then triggers the
cloud workflow. It takes a fresh Finnkino token from a real browser session each
run, so there is no stored credential and nothing to rotate. There is no cloud
fallback: a runner cannot obtain a token at all, since the site answers
Cloudflare 403 to datacenter IPs.

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

    tests/                           python3 -m unittest discover -s tests
    .github/workflows/biorex.yml     all cloud providers + enrichment

## Data shape

Every provider writes the same thing, so the client has no per-provider code.

    data/providers.json          [{id, label, host, accent, book}]
    data/area-{venueId}.json     {generated, dates[], horizon, shows[]}
    data/venues-{provider}.json  {generated, oldest, status, stale[], unverified[],
                                  provider, venues[{id,name,short,city}]}
    data/films-extra.json        title-keyed synopses, posters, trailers
    data/tmdb-genres.json        {fi,sv,en} genre id -> name, for rendering `gids`
    data/areas.json              Finnkino venue list (legacy shape, numeric ids)

A showtime carries `title, start (ISO, Europe/Helsinki), theatre, aud, url, img,
len, rating, age, genres, gids, lang, method, soldOut, price, provider, venue,
tmdbId`.

Two fields are easy to confuse. `rating` is the **film's** age classification;
`age` is a limit the **screening** adds on top, since a licensed auditorium can
be 18+ whatever the film is rated. `tmdbId` and `gids` are written only for
exact TMDB matches, because a weak id folds two different films into one card.

On a provider file, `generated` is when it was written and `oldest` is its
weakest venue's timestamp. The health line ages on `oldest`; `status` is `ok` or
`partial`, and `stale`/`unverified` name the venues behind it.

## Adding a provider

1. Write `scripts/providers/{name}.py` exposing two things:

       SITES             [{provider, label, venues:[{id, name, short, city}]}]
       fetch_site(site)  -> {venue_id: [show, ...]}

2. Add an entry to `scripts/providers/registry.py`: id, label, host, accent,
   `book` mode, module, and `where` it runs (`cloud` or `local`).

Nothing else needs editing. The workflow loops over `registry.py --cloud` and
the client reads `data/providers.json`. One module can serve several providers,
which is why the provider id sits on the site (`nexxo` serves Kinoset,
`etiketti` serves Kotkan Leffat and Bio Rex Kokkola).

**Check for an existing platform first.** A cinema running Vista, MyCloudCinema,
Nexxo or eTiketti needs a `SITES` entry against the existing adapter. Adding a
venue to an existing provider is one line. Pick the accent with
`accent_check.py`; do not judge it by eye.

    python3 scripts/providers/run.py biorex
    python3 scripts/providers/run.py --where cloud
    python3 -m unittest discover -s tests

## Indexable pages

The app is one JS-rendered URL, so `build_pages.py` renders static pages from
the same committed JSON at the end of every run:

    /teatteri/{slug}/     one venue        /en/theatre/{slug}/
    /kaupunki/{slug}/     a whole city     /en/city/{slug}/

72 per language, 145 sitemap URLs: 63 venues plus the nine cities with more than
one venue. A one-venue city would duplicate its venue page and compete with it,
so those get the city into the venue page's title and address instead.

Each page carries real HTML showtimes, `hreflang` pairs, and
`ScreeningEvent`/`MovieTheater` structured data. No `aggregateRating`: the
ratings are TMDB's, and presenting another party's ratings as the page's own is
against Google's guidelines, so it appears as credited text. Every page links
into the app as `/?area={venueId}`.

## Privacy

No accounts, cookies, analytics, tracking or ads. Preferences stay in
`localStorage`. Schedule data is static JSON from this origin, so browsing tells
no cinema anything.

**A page load makes no third-party requests.** Counted 2026-08-30: all 3157
poster references resolve to `data/posters/` on this origin, across 304 files,
and the typeface is served from `fonts/`. Every `<img>` carries
`referrerpolicy="no-referrer"`.

That was false until 2026-08-29, when the typeface came from Google Fonts and
about a third of the posters were hot-linked from the cinemas' hosts and
`image.tmdb.org`. Both are mirrored now. This paragraph stays so the privacy
claim can be checked against when it was wrong.

Two things reach other hosts. Tapping a showtime or a trailer hands you to the
cinema's booking page or to YouTube. GitHub Pages serves the site and logs
requests, as any host would.

## Data sources

Schedule data belongs to the respective cinemas: Finnkino Oy, BioRex Cinemas,
Kinoset, Kotkan Leffat, Riviera Cinemas, Savon Kinot, Gilda, Cinema Orion, Kino
Engel, Bio Rex Kokkola and Kino Akseli. Ratings, trailers and fallback synopses
and posters come from TMDB. Every showtime links to the cinema's own booking
page, and the footer credits the source being displayed.

Every provider is read through the same public interface its own site uses, under
an honest User-Agent, **on a schedule that no visitor can influence**. The app
loads static JSON from this origin, so browsing it, reloading it or leaving it
open reaches no cinema. That property holds by construction: the client has no
code that calls a cinema.

Data is refreshed by a scheduled job and by a refresh triggered after each local
collection run. Under the normal configured cadence the three local providers are
read four times a day, and the eight cloud providers usually up to eight, since
runs are queued rather than merged. **Those figures describe the typical cadence
and the configuration does not enforce them.** Scheduled execution is best-effort
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

**tiles-39nomads@icloud.com**

The pipeline reads every provider as `Leffavuoro/1.0 (+https://leffavuoro.fi)`.
That URL resolves to this page so a cinema can identify who is reading them and
reach the address above.

If you run one of the cinemas above and would rather not be included, say so and
the adapter comes out. It is one entry in `scripts/providers/registry.py`, and
no reason has to be given. Questions about how a schedule is read, or a wrong
showtime, are welcome at the same address.
