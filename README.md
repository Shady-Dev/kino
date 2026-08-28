# Leffavuoro

Finnish cinema showtimes as a fast, installable web page.

**Live at https://leffavuoro.fi**

## What it does

Showtimes for **46 venues in 31 cities** across nine providers: Finnkino,
BioRex, Kinoset, Kotkan Leffat, Riviera, Savon Kinot, Gilda, Cinema Orion and
Kino Akseli. Pick a venue and a
date, see films with posters, TMDB ratings, age limits, runtimes, genres,
languages and, where the cinema publishes them, ticket prices and seat
availability. Tapping a showtime opens that cinema's own booking page.

Cities with more than one venue also get a **combined view** ("Kaikki
Helsinki"), which merges the same film across chains into one card, labels
every showtime with its venue, and lets you filter by chain.

Works as a PWA: add to home screen, opens fullscreen, serves the last loaded
schedule when offline. Remembers your venue, starred home theatre, day,
language and theme in `localStorage`. See [Privacy](#privacy) for what does and
does not leave the device.

## How it works

The page never calls a cinema's schedule API at load time. A pipeline fetches
everything ahead of time and commits static JSON, which GitHub Pages serves from
the same origin. No CORS, no API keys in the client. Poster images and the
typeface are the exception and are covered under [Privacy](#privacy).

Providers run in one of two places, because two of them block datacenter IPs:

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
| Kino Akseli | 1 | none | Local (blocks datacenter IPs) |

A local machine runs the two providers that block datacenter IPs, four times a
day: it obtains a fresh short-lived Finnkino token from a real browser session,
runs `scripts/fetch_data.py` and `scripts/providers/run.py kinoakseli`, pushes
the data, then triggers the cloud workflow. There is **no cloud fallback** for
Finnkino: a runner cannot obtain a token at all, because the site answers
Cloudflare 403 to datacenter IPs, so the workflow that pretended to be one was
removed. Staleness shows in the app instead — the per-provider health line turns
amber past 8 h. Machine setup and scheduling specifics are kept in local notes
rather than here.

Each fetcher runs with its exit code captured to its own committed log rather
than aborting the script, so one failing provider never blocks the others from
publishing. Read those logs (`run.log`, `run-{module}.log`) rather than the
Actions logs.

A final pass (`scripts/providers/enrich_tmdb.py`) fills in TMDB ratings,
trailers, Finnish synopses and posters for anything a provider does not
supply itself. It **merges** and never overwrites a cinema's own text.

TMDB cannot be searched by Finnish distributor title, so that pass strips
event prefixes and format noise from the query and falls back to
`tmdb-aliases.json` for the rest. Titles that still find nothing are named in
`run-enrich.log`, alongside two other lists worth reading: **weak match**, where
no result matched the title exactly and the most popular one was taken, and
**rating held back**, where a rating was hidden for having fewer than 25 votes.

Genres come from TMDB **ids**, not from provider strings: the chains disagree
(four spellings for the family genre) and their strings are Finnish even in
English mode. `data/tmdb-genres.json` maps ids to names per language.

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
    scripts/providers/enrich_tmdb.py TMDB ratings, trailers, synopses, posters
    scripts/providers/tmdb-aliases.json  overrides for titles TMDB cannot be searched by
    scripts/providers/synmerge.py    shared synopsis merge helper
    scripts/providers/strands.py     event strand prefixes, split off titles into method
    .github/workflows/biorex.yml     all cloud providers + enrichment
    data/                            generated JSON and posters (committed by CI)
    IDEAS.md                         architecture notes, provider research, backlog

## Data shape

Every provider writes the same thing, so the client has no per-provider code
beyond a display name and an accent colour:

    data/providers.json          [{id, label, host, accent, book}] for the client
    data/area-{venueId}.json     {generated, dates[], horizon, shows[]}
    data/venues-{provider}.json  {generated, provider, venues[{id,name,short,city}]}
    data/films-extra.json        title-keyed synopses, posters, trailers
    data/tmdb-genres.json        {fi,en} genre id -> name, for rendering `gids`
    data/areas.json              Finnkino venue list (legacy shape, numeric ids)

A showtime carries: `title, start (ISO, Europe/Helsinki), theatre, aud, url,
img, len, rating, age, genres, gids, lang, method, soldOut, price, provider,
venue, tmdbId`.

`rating` is the film's age classification; **`age` is a limit the screening adds
on top of it** — a licensed bar auditorium is 18+ whatever the film is rated, so
it is rendered on the showtime rather than on the film. `tmdbId` and `gids` are
written only for exact TMDB matches, because a weak id would merge two different
films in a combined city view.

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
   `book` mode, the module name and `where` it can run (`cloud` or `local`).

That is all. The cloud workflow loops over `registry.py --cloud`, so it needs
no edit, and the client reads `data/providers.json`, so `index.html` needs no
edit either. A `local` provider is added to the local wrapper instead, because
its site blocks datacenter IPs.

Adding a **venue** to an existing provider is a one-line entry in that
adapter's `SITES`/`VENUES`.

Run one by hand with:

    python3 scripts/providers/run.py biorex
    python3 scripts/providers/run.py --where cloud

## Token maintenance

None. The Finnkino token is obtained fresh at every run and used within
seconds, so its short expiry no longer matters. `TMDB_SECRET_TOKEN` is a normal
TMDB read token in the repository secrets.

`cf-worker/worker.js` was an abandoned attempt to obtain the token from an edge
network instead of a local machine. It is not deployed and not used.

Note that the local wrapper hard-resets its checkout to `origin/main` at the
start of every run, so edits made inside that clone do not survive. The wrapper
itself lives outside the clone.

## Indexable pages

The app is one JS-rendered URL, so on its own it is a single entry in a search index.
`scripts/build_pages.py` renders static pages from the same committed JSON the app reads,
at the end of every pipeline run:

    /teatteri/{slug}/     one venue        /en/theatre/{slug}/
    /kaupunki/{slug}/     a whole city     /en/city/{slug}/

51 pages in each language: 46 venues, plus the five cities that have more than one venue
(Espoo, Helsinki, Kotka, Savonlinna, Tampere). A city page for a one-venue city would be
the venue page at a second URL, so single-venue cities are covered by putting the city in
the venue page's title and JSON-LD address instead.

Each page carries real HTML showtimes for the next few days, `hreflang` pairs, and
`ScreeningEvent` / `MovieTheater` structured data for today and tomorrow. No
`aggregateRating`: the ratings are TMDB's, and presenting another party's ratings as the
page's own is against Google's guidelines, so the rating is shown as credited text and
left out of the markup.

These pages make no third-party requests at all: inline CSS, no webfont, and only
same-origin posters. A page is rewritten only when its bytes change, which in practice is
once a day when the date window shifts.

## Privacy

No accounts, no cookies, no analytics, no tracking scripts, no ads. Your venue,
starred home theatre, day, language and theme live in `localStorage` and are
never transmitted. Schedule data is static JSON from this origin, so browsing
showtimes tells no cinema anything.

Three things do reach other hosts, and it is worth being exact about them rather
than claiming the page is self-contained:

- **The typeface** loads from Google Fonts on every visit, so Google sees your IP
  address.
- **About a third of poster images** are hot-linked from where the cinema
  publishes them (`mycloudcinema.com`, `cdn.etiketti.app`, `kinoset.fi`, an Azure
  blob host) and from `image.tmdb.org`. Those hosts see your IP address and which
  poster file was requested. Every `<img>` carries `referrerpolicy="no-referrer"`,
  so no page URL is sent with it. The remaining two thirds come from
  `data/posters/` on this origin.
- **Tapping a showtime or a trailer** hands you off to the cinema's booking page
  or to YouTube, which is the point of the link.

GitHub Pages serves the site and therefore logs requests, the same as any host
would.

Self-hosting the font and the rest of the posters would close the first two.
Neither is done yet.

## Data sources

Schedule data belongs to the respective cinemas: Finnkino Oy, BioRex Cinemas,
Kinoset, Kotkan Leffat, Riviera Cinemas, Savon Kinot, Gilda and Kino Akseli. Ratings, trailers and
fallback synopses and posters by TMDB. Every showtime links to the cinema's own
booking page, and the footer credits the source being displayed.

This is a personal, non-commercial project with no affiliation to any of them.
Fetches run four times a day regardless of visitor numbers.
