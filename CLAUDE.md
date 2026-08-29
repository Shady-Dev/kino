# Working on this repo

Leffavuoro (leffavuoro.fi): Finnish cinema showtimes from nine chains in one app. A
single-file vanilla JS PWA served from GitHub Pages, backed by a Python pipeline that
commits static JSON. No build step, no framework, no dependencies beyond the standard
library in the pipeline.

## Read IDEAS.md first

It holds the architecture decisions, the per-provider API research, and a long list of
approaches that were **tried and rejected, with the reasoning**. Several obvious
improvements are in there as dead ends. Argue with a recorded decision rather than
quietly reversing it, and update IDEAS.md in the same commit as the change it explains.

Write **why**, not what. The diff already says what.

## How to work

- **One commit per item.** Do not batch unrelated changes.
- **Stop and ask rather than guess.** If an endpoint is unreachable or a claim cannot be
  checked against the data, say so plainly instead of inferring. A wrong fact stated
  confidently costs more than a missing one.
- **Measure counts against the data before writing them down.** Numbers taken from an
  older document have been wrong three times: the city count, the poster count, the page
  rewrite frequency. Count it, then write it.
- **Verify a claim before documenting it.** The README asserted "nothing leaves the
  device" and "no third-party requests" while loading a webfont and 1500 hot-linked
  posters. Factual accuracy in documentation is not negotiable.

## Client changes (`index.html`, `sw.js`)

- Bump the `CACHE` version in `sw.js` in **every** commit that touches `index.html`.
- Extract the inline script block and `node --check` it before pushing.
- A hard refresh verifies. No workflow dispatch is involved.
- Anything the language toggle can reach must be redrawn by `applyLang()`.
- Escape provider text at every `innerHTML` interpolation (`esc()`), and run every
  provider URL through `safeUrl()`. Adapters publish verbatim text on purpose, because
  the raw title is the key for `normTitle()`, `films-extra.json` and `tmdb-aliases.json`.
- **No `localStorage` assumptions beyond the existing keys.** Renaming `kino-prefs` or
  `kino-theme` wipes every user's saved venue, theme and starred cinema.

## Pipeline changes (`scripts/**`)

- After the commit, dispatch the cloud workflow, then read the **committed**
  `run-*.log` to verify. Not the Actions logs.
- Page changes show up in `run-pages.log`, poster mirroring in `run-posters.log`.
- `scripts/fetch_data.py` and the local-only adapters cannot run on a runner. Compile
  check them, and **say clearly when a change needs a run from an ordinary connection**.
- A provider that parses zero showtimes fails the run on purpose. An empty parse that
  silently left old data ageing is the failure this pipeline is built against.

## Adding a provider

A registry entry plus an adapter. No `index.html` edit.

- `scripts/providers/registry.py` is the single source of truth. `data/providers.json`
  is generated from it and the client derives every label, host, accent and footer verb.
- An adapter exposes `SITES` and `fetch_site(site) -> {venue_id: [shows]}`.
- **Platform before site.** Adding a cinema that runs Vista, MyCloudCinema, Nexxo or
  eTiketti is a `SITES` entry, never a new parser. Check for an existing platform first.
- Accents are **measured against the set**, not picked. A new chain has to be separable
  from every chain sharing a city in normal *and* deuteranope vision. IDEAS carries the
  numbers and the method.
- Check field-presence assumptions in the client, not just in the parser. Every frontend
  bug on the day multi-provider landed came from a field only Finnkino populated.

## Hard rules

- **Never use `raw.githubusercontent.com` to read this repo.** Its CDN served a
  two-commit-stale `index.html` minutes after a push and silently reverted a fix. Use the
  Contents API with `Accept: application/vnd.github.raw`, or a tarball of `main`.
- **Never commit a raw probe dump.** A third party's page carries whatever they ship to
  visitors; one such dump put someone else's API key in this repo and tripped secret
  scanning. Probe, read the answer, write the *finding* in IDEAS, commit nothing raw.
  `.gitignore` blocks `probe/` and `probe-*`.
- **Nothing machine-specific in this repo.** It is public. No paths, no hostnames, no
  schedules, no credentials, no token retrieval, no third-party endpoint inventories
  beyond the read endpoints an adapter actually uses. Operational detail lives in private
  notes outside the repo.
- **Never inflect Finnish city names in generated text.** Helsinki -> Helsingissä,
  Tampere -> Tampereella. Suffixing a case ending onto the nominative produces
  "Helsinkissä", which is exactly how a reader spots a generated page. Nominative with a
  separator, always.
- **Keep anything volatile out of generated pages**, or `write_if_changed` stops working:
  no build timestamp, no sold-out state in markup.
- **Do not read a site from a datacenter IP and conclude it is unreachable.** Several
  providers challenge datacenter addresses and answer an ordinary connection fine, and
  the block is often on one endpoint rather than the whole host.

## Access and ethics

Every provider is read through the same public interface its own site uses, four times a
day regardless of traffic, and every showtime links back to the cinema's own page.

Reading a site as an ordinary visitor is fine. Residential proxies, fingerprint spoofing,
solving a captcha, and using credentials that were never issued to a visitor are not.
Booking, payment and administrative endpoints are never called and are not inventoried.
If a cinema would rather not be included, the adapter comes out: one registry entry.

## Testing

A fixture has to exercise the **loop**, not just the body. A one-item fixture once passed
while the pacing branch it never entered was missing an import, and `py_compile` does not
resolve names. Two items minimum wherever there is pacing or an index.
