# Working on this repo

Leffavuoro (leffavuoro.fi): Finnish cinema showtimes from ten chains in one app. A
single-file vanilla JS PWA served from GitHub Pages, backed by a Python pipeline that
commits static JSON. No build step, no framework, no dependencies beyond the standard
library in the pipeline.

## Read IDEAS.md first

It holds the architecture decisions, the per-provider API research, and a long list of
approaches that were tried and rejected, with the reasoning. Several obvious improvements
are in there as dead ends. If you disagree with a recorded decision, argue with it in the
file instead of quietly reversing it, and update IDEAS.md in the same commit as the change
it explains.

Write down why a change was made. The diff already shows what changed.

## How to work

- **One commit per item.** Do not batch unrelated changes.
- **Ask instead of guessing.** If an endpoint is unreachable or a claim cannot be checked
  against the data, say so plainly. A wrong fact stated confidently costs more than a
  missing one.
- **Measure counts against the data before writing them down.** Numbers carried over from
  an older document have been wrong five times now: the city count, the poster count, the
  page rewrite frequency, and then the venue and provider counts after Kino Engel landed.
  Count it, then write it.
- **Verify a claim before documenting it.** The README asserted "nothing leaves the
  device" and "no third-party requests" while the page loaded a webfont from Google and
  hot-linked posters from seven other hosts. Documentation has to be factually accurate.

## Client changes (`index.html`, `sw.js`)

- Bump the `CACHE` version in `sw.js` in **every** commit that touches `index.html`.
- Extract the inline script block and `node --check` it before pushing.
- A hard refresh verifies. No workflow dispatch is involved.
- Anything the language toggle can reach must be redrawn by `applyLang()`.
- Escape provider text at every `innerHTML` interpolation (`esc()`), and run every
  provider URL through `safeUrl()`. Adapters publish verbatim text deliberately, because
  the raw title is the key for `normTitle()`, `films-extra.json` and `tmdb-aliases.json`.
- **No `localStorage` assumptions beyond the existing keys.** Renaming `kino-prefs` or
  `kino-theme` wipes every user's saved venue, theme and starred cinema.

## Pipeline changes (`scripts/**`)

- After the commit, dispatch the cloud workflow, then verify against the **committed**
  `run-*.log` files. The Actions logs are not the ones to read.
- Page changes show up in `run-pages.log`, poster mirroring in `run-posters.log`.
- `scripts/fetch_data.py` and the local-only adapters cannot run on a runner. Compile
  check them, and **say clearly when a change needs a run from an ordinary connection**.
- A provider that parses zero showtimes fails the run deliberately. The failure this
  guards against is an empty parse that silently leaves old data ageing.

## Adding a provider

A registry entry plus an adapter. No `index.html` edit.

- `scripts/providers/registry.py` is the single source of truth. `data/providers.json`
  is generated from it, and the client derives every label, host, accent and footer verb.
- An adapter exposes `SITES` and `fetch_site(site) -> {venue_id: [shows]}`.
- **Platform before site.** A cinema running Vista, MyCloudCinema, Nexxo, eTiketti or
  Johku is a `SITES` entry against an existing adapter. Check for a platform first, and
  only write a parser if it is on none of them.
- **Measure a new accent against the whole set** with `python3 scripts/accent_check.py`.
  `--search {id}` proposes one, `--candidate HEX --city A,B` tests one, `--selftest`
  checks its own CIEDE2000 against published reference data. Never trust an accent number
  with no script behind it: the figures that used to sit in IDEAS were CIE76 mislabelled
  as ΔE and were wrong by a factor of five. Helsinki is the only city with more than one
  chain in it, so it is the only place the rule binds.
- Check field-presence assumptions in the client as well as in the parser. Every frontend
  bug on the day multi-provider landed came from a field only Finnkino populated.

## Hard rules

- **Never use `raw.githubusercontent.com` to read this repo.** Its CDN served a
  two-commit-stale `index.html` minutes after a push and silently reverted a fix. Use the
  Contents API with `Accept: application/vnd.github.raw`, or a tarball of `main`.
- **Never commit a raw probe dump.** A third party's page carries whatever they ship to
  visitors, and one such dump put someone else's API key in this repo and tripped secret
  scanning. Probe, read the answer, write the *finding* in IDEAS, commit nothing raw.
  `.gitignore` blocks `probe/` and `probe-*`.
- **Nothing machine-specific in this repo.** It is public. No paths, no hostnames, no
  schedules, no credentials, no token retrieval, no third-party endpoint inventories
  beyond the read endpoints an adapter actually uses. Operational detail lives in private
  notes outside the repo.
- **No real name and no personal address, in a file or in a commit.** Commit as
  `Shady-Dev <19388620+Shady-Dev@users.noreply.github.com>`; if you ever see an author
  line that is not that or a `kino-bot`/`kino-local` identity, stop and say so rather
  than carrying on. A real name reached 18 commits once and cost a history rewrite.
  `tests/test_contact_address.py` fails if any address other than the contact alias
  appears in a tracked file, generated pages included.
- **Never inflect Finnish city names in generated text.** The correct forms are
  Helsinki -> Helsing**i**ssä and Tampere -> Tampereella: the stem changes, and Finnish
  cities do not all take the same case. Gluing a case ending onto the nominative instead
  gives Helsin**ki**ssä, which is wrong and is how a reader spots a generated page
  immediately. Always use the nominative with a separator.
- **Keep anything volatile out of generated pages**, or `write_if_changed` stops working:
  no build timestamp, no sold-out state in markup.
- **Do not read a site from a datacenter IP and conclude it is unreachable.** Several
  providers challenge datacenter addresses and answer an ordinary connection fine, and the
  block is often on a single endpoint while the rest of the host serves normally.

## Access and ethics

Every provider is read through the same public interface its own site uses, four times a
day regardless of traffic, and every showtime links back to the cinema's own page.

Reading a site as an ordinary visitor is fine. Residential proxies, fingerprint spoofing,
solving a captcha, and using credentials that were never issued to a visitor are not.
Booking, payment and administrative endpoints are never called and are not inventoried.
If a cinema would rather not be included, removing it is one registry entry.

## Testing

    python3 -m unittest discover -s tests

Stdlib `unittest`, no dependencies, no runner config. Run it before pushing anything
under `scripts/`.

A fixture has to exercise the loop, not only the body. A one-item fixture once passed
while the pacing branch it never entered was missing an import, and `py_compile` does not
resolve names. Use two items minimum wherever there is pacing or an index.

**A test earns its place by failing.** Write it, break the code it covers, watch it go
red, then restore. A test that has never failed is a test you have not checked. Every
cap, fallback and error path in here has to be verified by tripping it, because one of
them looked correct and silently published a half-empty schedule until it was actually
triggered.

Tests talk to a real local HTTP server rather than a mocked `urlopen` where the behaviour
under test is partly urllib's -- which exception a 429 raises, what `e.headers` holds. A
mock there encodes the assumption instead of checking it.
