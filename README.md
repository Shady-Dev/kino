# kino

Finnkino showtimes as a fast, installable web page.

Live at: https://shady-dev.github.io/kino/

## What it does

Shows movie schedules for all Finnkino cinemas in Finland: pick a theatre
and a date, see the movies with posters, TMDB ratings, age limits, genres
and formats. Tapping a showtime opens seat selection on finnkino.fi.

Works as a PWA: add to home screen, opens fullscreen, shows the last
loaded schedule when offline. Remembers the selected cinema, day and
theme.

## How it works

Finnkino removed their public XML API. The site now uses a Vista OCAPI
backend (digital-api.finnkino.fi) that requires a bearer token embedded
in finnkino.fi pages. The token can only be fetched from a residential
IP and expires every 12 hours.

So the page does not call Finnkino directly. Instead:

1. A GitHub Actions workflow (`.github/workflows/fetch.yml`) runs
   `scripts/fetch_data.py` four times a day.
2. The script calls the OCAPI with a stored token, fetches sites and
   seven days of showtimes, downloads new posters, and looks up TMDB
   ratings for new films (cached in `data/tmdb.json`).
3. Results are committed as static JSON under `data/`, which GitHub
   Pages serves next to the page.
4. `index.html` reads that JSON from its own origin. No CORS, no
   third-party calls at page load.

## Files

    index.html               the whole app
    manifest.webmanifest     PWA manifest
    sw.js                    service worker
    scripts/fetch_data.py    data fetcher run by CI
    .github/workflows/       fetch schedule
    data/                    generated JSON and posters (committed by CI)
    IDEAS.md                 backlog

## Token maintenance

The Finnkino token lives in the repository secret `FINNKINO_SECRET` and
expires every 12 hours. When data goes stale the page shows a warning
banner. Refresh: open finnkino.fi in a browser, extract the `eyJ...`
token from the page source, update the secret. TMDB uses a normal API
read token in `TMDB_SECRET_TOKEN`.

## Data sources

Schedule data belongs to Finnkino Oy. Ratings by TMDB. This is a
personal, non-commercial project with no affiliation to either.
