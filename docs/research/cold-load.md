# Cold load: what the app fetches before anything is chosen

The `IDEAS.md` entry "Every cold load reads all 82 venue lists" asked for a measurement of
what the chooser needs before a lazy load is proposed. This is that measurement.

## Findings

- **Requests per cold load**, the 2026-09-25 audit (Chromium, Playwright 1.62.0, a clone of
  the repository served locally, the worker blocked): chooser 88 requests, a venue 89, the
  Helsinki city view 115 (16 area files and 10 posters on top). All three fetch every
  provider's `venues-{id}.json` and `areas.json`.
- **Size of the venue lists**, the committed `data/`, read 2026-09-26: 82
  `venues-*.json` files holding 117 venues, 25 KiB together and 15 KiB gzipped each on its
  own; the median file is 275 B. `areas.json` (Finnkino) is under 1 KiB. Every file carries
  `generated`, `oldest`, `pending`, `provider`, `stale`, `status`, `unverified` and
  `venues`.
- **Who asks for them**, `index.html` read the same day: boot prefetches every
  `venues-{id}.json` named in `PROV_FALLBACK` before anything else, then `loadAreas()`
  awaits all of them through `fetchVenueLists()` and fills the picker. Each answer from
  the service worker starts a background revalidation (`cache: 'no-cache'`), so a warm
  load also sends 82 conditional requests.
- **What the plain chooser draws from them**: nothing until the picker opens. The city
  links are static markup, the day chips are built before the lists arrive, and the
  language control does not wait for them. A `?area=` link or a stored favourite does
  need them: `knownArea()` validates the location against the venues and the city and
  region groups built from them.

## Inferences

- The cost is the request count and the revalidations, not bytes: 15 KiB gzipped is less
  than one poster.
- Deferring the fetch until the picker opens saves the requests only for a reader who never
  opens it, and delays the first open for everyone else; with a link or a favourite the
  lists are needed at boot anyway.
- One file holding all 82 as committed would turn 82 requests into one on every load, cold
  or warm, without changing what the client knows.

## Proposal

`data/venues.json`: every provider file as committed, keyed by provider id, written by the
cloud job's build step from the committed `venues-*.json` and read first by
`fetchVenueLists()`, with the per-provider files as the fallback when it is missing or
unreadable.

- **One writer.** The local half does not write it, so a local commit landing during a
  cloud run cannot conflict on it; `biorex.yml`'s rebase fails on a content conflict by
  design.
- **Lag.** It trails a local run by the cloud run the laptop dispatches after it, normally
  minutes. During that window the picker and the health line read the previous local
  state, which the per-provider files would have shown already.

## Open questions

- Whether the health line may lag a local run by that window, or should keep reading the
  per-provider files for the ages while the combined file serves the picker.
- Whether the service worker should revalidate the combined file only, and leave the
  per-provider files to the fallback path.

## Status

Not built. Next step: the maintainer's decision; if accepted, the build step, the client's
read with its fallback, and a drift check that the combined file matches the committed
per-provider files.
