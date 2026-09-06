# Kino — Improvement Ideas

## Current backlog

The 9 items still open, with the section that holds each one and its reasoning. Presence
here means open; the `[ ]` / `[x]` marker on the item itself stays the only status, and a
ticked item is closed whether it was built or decided against -- the line says which.
Drop a line from this list when its item is ticked below.

Seven items were closed in one pass on 2026-09-01 without code: see
"[Seven backlog items closed without building them](#seven-backlog-items-closed-without-building-them-2026-09-01)".

**[App](#app)**

- Landing pages: the screening list could span the full film width on narrow phones
  once the poster column has ended, with a two-level label
- Landing pages: the city legend's cinema names link to theatre pages and look like a
  passive key
- Heurekan planetaario posters: Asteroid Quest and Metsän sydän have portrait key
  visuals on heureka.fi, mirrored only with Heureka's written permission; The Stellars has
  no portrait source. See "[Heureka's missing posters wait for written
  permission](#heurekas-missing-posters-wait-for-written-permission-2026-09-05)"

**[Pipeline](#pipeline)**

- Language codes normalised end to end: the adapter and client fixes landed 2026-09-02;
  open until the committed data holds no `TU`, `MA` or `XX` and the landing-page aliases go
- Move the local fetch off the laptop to an always-on box on the same network — 26 of 75
  venues ride on that machine and cloud VMs cannot replace it
- Finnkino prices -- **blocked, not merely unbuilt**: the public programme API carries
  no prices at all, and the only route left is the booking flow, which this repo does
  not call. See "[Finnkino publishes no prices outside the booking
  flow](#finnkino-publishes-no-prices-outside-the-booking-flow-2026-09-01)"
- README workflow badge
- Credential hygiene and rotation — tracked in private notes outside this repo

**[Ops](#ops)**

- Staleness monitor: the verdict landed as `scripts/check_staleness.py`; the
  external ping that calls it is still to build, and lives outside this repo

## Done
- [x] Self-hosted posters (moviexchange CDN → data/posters/, onerror fallback tiles)
- [x] TMDB ratings — ★ badge, cached in data/tmdb.json
- [x] Genres + formats from OCAPI, rendered as pill badges (two-line meta)
- [x] Real ticket deep links — stub → /liput/valitse-paikat/?showtimeId={id}
- [x] Stale-data banner — amber warning when data older than 8 h
- [x] PWA — manifest, service worker (network-first, offline fallback), icons
- [x] One-screen date row — 5 chips + 📅 native picker (horizon = today+6)
- [x] Remembers cinema, day, theme (localStorage)
- [x] Movie sheet — synopsis, trailer, week's showtimes (bottom-sheet mobile, modal desktop)
- [x] Language toggle fi/en
- [x] Trailers via TMDB YouTube links, MX CDN as fallback (41 yt / 8 mx / 4 none @ 2026-08-26)
- [x] Sheet layout — pinned head + scrolling day list (desktop modal no longer clips)
- [x] TMDB re-check — films with no trailer re-checked once per day, cached movie id reused
- [x] **Token automation — solved via local fetch** (see below)
- [x] **Multi-provider** — 35 venues / 27 cities across 5 providers (see below)
- [x] City-grouped venue picker, chain-prefixed labels ("Finnkino Itis"), city in the optgroup
- [x] Per-provider health line above the footer — every source's age, ⚠ past 8 h
- [x] Ticket prices where a provider publishes them ("12€", "alkaen 5€")
- [x] **Live at https://leffavuoro.fi** (GitHub Pages + custom domain)
- [x] **Combined city view** — "Kaikki {city}" for cities with 2+ venues, cross-chain merge
- [x] Star a home theatre; it opens on every visit (localStorage `fav`)
- [x] Finnish synopses for every provider (their own text first, TMDB as fallback)
- [x] Runtime + genres for BioRex and Kotka from their film pages
- [x] Drag the sheet header down to dismiss on mobile
- [x] **Rebrand to Leffavuoro** (title, wordmark, manifest, L. icons, sw cache bumped).
      localStorage keys stay `kino-prefs` / `kino-theme` on purpose: renaming them would
      wipe the saved star, theme and last venue. Repo stays `kino`.
- [x] Compact mobile pass: venue picker and star share one row, tighter header, chip
      labels stop clipping (“Huomenna”)
- [x] Star carries a label (“Tallenna” / “Tallenna oma teatteri”) until a home venue is
      set, then collapses to the glyph
- [x] **Riviera** added (2 venues, seats + runtime, 24-date horizon)
- [x] **Cinema Orion** added (1 venue, Helsinki; ticket-type prices, own Finnish blurbs)
- [x] TMDB posters for providers that publish none, written onto each show by the
      pipeline so the client needed no change
- [x] Chain key in combined views doubles as a quick filter, and it is additive:
      from the default (nothing selected, everything shown) the first click *isolates* that
      chain rather than hiding it, then each further click adds one. It used to seed the set
      with every chain, so the first click subtracted, which read backwards. Deselecting the
      last one, or selecting them all, means "no filter" again. Not persisted, resets on
      venue change.
- [x] TMDB ★ + trailers for every provider via `scripts/providers/enrich_tmdb.py`
      (title-keyed cache `data/tmdb-titles.json`, daily re-check of misses)
- [x] Provider-aware footer wording from the registry's `book` field: buy tickets /
      reserve seats / sold at the door / open the programme (`list`, for a provider with no
      per-show page — currently unused)
- [x] Language meta reads "englanti · tekstit suomi/ruotsi": the audio language bare,
      subtitles labelled once and grouped, rather than repeating the role word per language
      ("engl. puhe, suom. tekstit, ruots. tekstit"). `LN` therefore holds full nominatives
      (suomi, englanti, ruotsi), not the old abbreviated forms. A Finnish dub is just
      "suomi"; if that ever reads wrong, the fix is keeping the word for audio only.
- [x] Horizon-aware empty states — `dates` + `horizon` per area file; "ei näytöksiä" vs
      "ohjelmistoa ei ole vielä julkaistu" vs "ei enää näytöksiä tänään"
- [x] Helsinki-time day/clock everywhere (`Intl` + `Europe/Helsinki`) — correct days and
      showtimes when the device is in another timezone; 00:30 shows land on the right day
- [x] Auto-advance to the next day with shows when today is over (chip labels Tänään/Huomenna)
- [x] Date picker range widened to +13, clamped to each venue's real horizon
- [x] The picked day is remembered as an **ISO date**, not as an offset from today
      (2026-08-28). `dayIdx` had to be clamped to the chip range on every `buildDays()`,
      which was harmless while every horizon was a fortnight out. With Gilda publishing
      into December, picking a far date and then reloading or toggling the language put
      the user on today+13 with an empty list and no hint why. Restore validates the date
      against today..horizon and falls back to today; a stored `dayIdx` from before the
      change is ignored, which is the same fallback.

## Token automation — how it works now
The token is fetched fresh at run time and used within seconds, so nothing has to survive
the 12 h JWT expiry.

- The local wrapper: get token → `scripts/fetch_data.py` → `scripts/providers/run.py` for
  the local modules → push data, posters and logs, then dispatch the cloud workflow.
- Both fetchers run inside a `set +e` window with `echo "exit=$?"` appended to their own
  log, so one failure cannot abort the push or take fresh Finnkino data with it.
- The wrapper hard-resets the clone to `origin/main` before every run, so a manual edit
  inside `repo/` is destroyed at the next slot. Test edits belong in a separate clone.
- The TTL guard runs before `cd repo`, so a bad Finnkino token aborts the whole script.
- No cloud fallback. `.github/workflows/fetch.yml` was deleted 2026-08-27: a runner cannot
  obtain a token (www.finnkino.fi answers Cloudflare 403 to datacenter IPs) and the stored
  `FINNKINO_SECRET` was stale within 12 hours, so it had failed on every push for two days,
  which hid the run that broke. A stale Finnkino shows in the app's own health line.
- `get_token()` reads `FINNKINO_TOKEN` from the environment first; that path must not be
  removed. The direct-fetch fallback only works from an ordinary connection.

Machine setup, schedule, token retrieval and credentials live in local private notes.
Superseded: pushing the token into repository secrets and rotating it. The leftover
`FINNKINO_SECRET` should be deleted in repository settings.

## Multi-provider — current state
Goal: coverage for everyone, including small towns. Shape: one adapter per provider, or
better per platform, each running where it can.

| Provider | Venues | Auth | Runs where | Data |
|---|---|---|---|---|
| Finnkino | 17 | short-lived token | Local (blocks datacenter IPs) | full; sold-out flag, no seat counts |
| BioRex | 12 | none | Actions | no runtime/genres/seats |
| Kinoset (Nexxo) | 3 | none | Actions | prices, duration, genres |
| Kotkan Leffat (eTiketti) | 2 | none | Actions | prices, duration, seats |
| Riviera | 2 | none | Actions | seats, duration, 24-date horizon |
| Savon Kinot (eTiketti since 2026-08-30) | 6 | none | Local since 2026-09-04 (Cloudflare 403 to datacenter IPs) | fullest feed: original title, ISO langs, posters, deep links |
| Cinema Orion | 1 | none | Actions | ticket-type prices, own Finnish blurbs; no seats, runtimes or age limits |
| Gilda (MyCloudCinema) | 2 | none | Actions | posters, own synopses, formats; no seats or deep links |
| Kino Engel | 1 | none | Local (blocks datacenter IPs) | own synopses, rating, runtime, genres; no price, room or booking URL |
| Kino Akseli | 1 | none | Local (blocks datacenter IPs) | prices, no booking links |

Ratings and trailers come from the shared TMDB enrichment pass. eTiketti and Riviera
publish seat counts, Finnkino a sold-out flag; only the flag survives into the data (see
"Seat counts are parsed and deliberately not published").

76 venues / 52 cities across 34 providers (2026-09-05). Each provider writes
`data/area-{venueId}.json` in one shape (`{generated, dates, horizon, shows[]}`) plus
`data/venues-{provider}.json` (`{id, name, short, city}`). Finnkino still uses
`data/areas.json` with numeric ids. A registry entry generates `data/providers.json`, and
the client derives every label, host, accent and footer verb from it.

Conventions:
- An age limit can belong to the screening, not the film. A licensed bar auditorium admits
  18+ whatever the film is rated (BioRex Seinäjoki names it in the room: "2 REX (K-18)"),
  so `age` is a per-show field separate from `rating`, set from an explicit `(K-nn)` in
  the auditorium name. The client renders it on the stub as an outlined chip (`.agelim`),
  not red and not KAVI's official symbol, which denotes a legal classification this is not.
- Two glyphs only: `Ⓐ` for anniskelu and `18+` for the screening's age limit, on stubs,
  where the label column is about 75 px. `LUXE`, `iSense`, `IMAX` and `2D` stay words.
  Monochrome, with `title` and `aria-label`; `tagKey()` renders a legend only when the
  day's shows carry the tag.
- The calendar chip shows a date only while that date is being viewed (`resetCalChip()`).
- A stub names the cinema, not the district: combined views use the chain-prefixed label
  from `labelOf()` ("Riviera Punavuori"), which omits the prefix when the short already
  starts with the chain.
- The chain tint stays on in every combined view, including single-chain days: a palette
  is learnable only if always present, and the label carries the meaning. The legend
  keeps the two-chain rule.
- Glyphs have their own column (`.glyphs` is `margin-left:auto`, top-aligned in the grid).
- A stub label does not repeat the room name: a tag the `aud` string contains is dropped,
  and plain `2D` is dropped outright.
- The glyph key sits in the footer, not under the chain legend.
- Finnkino's rule (finnkino.fi/leffaherkut/anniskelunaytokset/): anniskelu screenings are
  K18 except in anniskelualuesalit, where the age limit does not apply and alcohol is not
  served at S/7 family films. `Annisk_K18` carries K18; plain `Anniskelu` marks a licensed
  room and carries no limit. The data agrees: plain `Anniskelu` appears on S and K-7 films
  (K-12 334 plain / 83 K18, K-16 116 / 43, S 8 / 5, K-7 2 / 1). `biorex.py` therefore no
  longer infers `K-18` from the tag, which had put the badge on 99 screenings including an
  S-rated documentary; only an explicit `(K-nn)` in the room name sets `age`. Bring the
  inference back only with a citation from BioRex.
- `method` is per showtime and must not render per film: 47 film/day combinations mix an
  Anniskelu screening with normal ones. The card shows tags every showtime shares; the
  rest go on their stub.
- `lang` is normalised to Finnkino's tags (`FI-A`, `FI-S`) so the "Suom. puhe" filter
  works for every provider.
- Event and venue tags (Anniskelu, Plus, SenioriKino, Perheleffa) go in `method`.
- `aud` is blank when the room name repeats the venue (single-screen sites).
- Chain accents are chosen against the set (2026-08-27): every chain sharing a city must
  be separable in normal and red-green colourblind vision, since the 3 px rule is the only
  visual cue between chains. Kino Akseli took the vacated gold because it never appears in
  a combined view. Every number this bullet carried was wrong and was removed; see "The
  accent numbers, re-derived" and run `scripts/accent_check.py`.
- A failed venue writes no file, keeping previous data.
- Verify the response belongs to the venue asked for (the BioRex cookie note).

### Combined city view (done)
- The picker gets `city:{name}` entries for cities with 2+ venues.
- `loadCity()` fetches each venue file in parallel and folds them; `dates`/`horizon` are
  the union, `generated` the oldest so the stale banner reflects the weakest link. A venue
  that fails to load is named in `missing`, not fatal.
- The payload carries `oldest`, the provider `generated` came from: the banner used to look
  the name up in `venueIndex[state.area]`, which has no `city:` entry, and blamed Finnkino.
- Identity: each show's `eventId` is rewritten to `mergeKey(title)`, which strips
  `2D/3D/IMAX/4K`, `(suomeksi)` and `, suomeksi` before normalising, so "Spider-Man: Brand
  New Day 2D" merges with the plain title while "Dyyni: Osa kolme" stays distinct from
  "Dyyni". The provider's own id is kept as `_eid` for films.json lookups.
- Differentiation: venue `short` in every stub, a 3 px left border per chain, a chain
  legend above the list and in the sheet. Never colour alone. Stubs use a CSS grid.
- Auditorium names stay verbatim, since that is what the ticket prints.

Since done elsewhere: TMDB id as a merge signal (see "The score ring"). Still open: a
curated "Pääkaupunkiseutu" entry (Helsinki + Espoo + Vantaa), and sparse-date dimming,
which `<input type="date">` cannot do without a custom picker.

### BioRex API — probed and confirmed 2026-08-26
WordPress + admin-ajax. No auth, no nonce, no Cloudflare block. **12 requests per run**
(`date=-1` returns all dates at once).

```
GET  https://biorex.fi/elokuvat/                      # session cookie
POST https://biorex.fi/teatterin-valinta/   location={venueId}
POST https://biorex.fi/wp-admin/admin-ajax.php?lang=fi
     action=br_movies_handler&genre=-1&date=-1&format=-1&language=-1&activeType=showtimes
```

- Response is `{"posts": "<html>"}` — HTML in JSON, parse with BeautifulSoup
- **The cookie step is required.** Without it you silently get BioRex Verkatehdas
  instead of an error, so a missing session = wrong data, not a failure
- `?cinema_id=` in page URLs is decorative; the cookie decides the venue
- `f_cinemas={slug}` query param handles the within-city sub-filter (`all`/`helsinki`/`redi`)
- Each `.showtime-item` carries a `data-click-data-layer` JSON attribute:
  `movieId, movieName, showId, showCinemaId, showCinemaName, showDate, showTime,
  showDateTime (ISO +03:00), showWeekday` — use this, not text scraping
- Also in the item: `.showtime-item__place__value` ("BioRex Tripla, Sali 6"),
  `.showtime-item__movie-rating` ("(K-16)"), `.showtime-item__format` (["EN","FI&SV"] =
  audio, subs), `icon-puhekieli` class = Finnish dub, poster `data-srcset` (1080w variant,
  `web.biorex.mycloudcinema.com`), booking href via `biorex.fi/secure-redirect/`
- Missing vs Finnkino: runtime, genres, synopsis, sold-out state. TMDB covers
  rating/trailer/poster via `movieName`; runtime would need the film page
- Venue ids: 13 Helsinki Tripla, 14 Helsinki Redi, 1 Hämeenlinna, 9 Hyvinkää, 7 Kajaani,
  4 Pietarsaari, 10 Porvoo, 8 Riihimäki, 2 Rovaniemi, 12 Seinäjoki, 3 Tornio, 5 Vaasa
- Dates are sparse (e.g. 27–31.8, 1–3.9, then 5.9, 9.9, 11–13.9, 30.9) — special
  events, not a rolling window. Scrape `#dayselect` options rather than generating dates.
  `<input type="date">` cannot disable individual days, so dimming unavailable dates
  would need a custom picker — deferred until BioRex is actually in.

Other Finnish aggregators exist (leffajat.fi, kinoon.fi) — useful as prior art for which
chains exist and how they present multi-cinema. Take data from the chains' own sources.

### Nexxo Scope is a platform serving several sites (probed 2026-08-26)
Kinoset runs the **Nexxo Scope** WordPress plugin, which exposes a clean JSON API. Other
Finnish cinemas use the same plugin, so adding one is a **config entry, not a new parser** —
append to `SITES` in `scripts/providers/nexxo.py` with base URL, locationid, name, city.

```
GET {base}/wp-content/plugins/nexxo-scope/public_api.php
    ?action=exportdailyshows&locationid=N&days=21&lang=fi&upcoming=0
-> {"shows": {"YYYY-MM-DD": [ {...} ]}}
```

- `upcoming=1` returns the coming-soon list with `startDate: null` — use `upcoming=0`
- Fields: `movieTitle, startTime, klo, roomTitle, ageLimit, duration, genre,
  priceIncludingTax, posterurl, showId, code_language, code_subtitles, showTypeTitle`
- Posters: prefix `posterurl` with `{base}/wp-content/plugins/nexxo-scope/banners/`
- `code_subtitles` can be multi ("FI-SE") -> split to `FI-S, SE-S`; `OV` = unspecified
- `code_external_title` is a distributor code, not a title
- No per-show booking URL, so link to `/ohjelmisto/?location=N`
- The same API also exposes write actions. Not used, not probed.
- Kinoset ids: 1 Huittinen (Kino 1-2, 2 screens), 2 Loimaa (Kinema), 3 Sastamala (Bio)
- Their film week runs Fri–Thu, published Tuesdays

### Kino Akseli (probed 2026-08-26)
Single screen, Nummela, WordPress + Elementor, showtimes server-rendered in the page.
**Datacenter IPs are challenged, so this one runs locally.**
- Parse: iterate `<h2 class="elementor-heading-title"><a href=".../elokuva-...">`, then the
  nearest following `Näytösajat` paragraph; genres/age/price sit in the paragraph *before*
- `Pe 28.08. klo 19:00` has no year — infer by keeping the date within roughly
  [today-45d, today+320d], otherwise January rolls over wrong
- `(dub.)` = Finnish audio; films showing `Näytösajat –` have no showtimes, skip them
- Gives price and genres; no runtime, auditorium or booking URL; ~3-day horizon

### eTiketti — a platform (probed 2026-08-26)
Kotkan Leffat runs **eTiketti** (etiketti.app). The API host
`{customer}.etiketti.app/api/yleiset/...` is behind Cloudflare, so the adapter reads
the cinema's own server-rendered pages instead. Another eTiketti cinema = a `SITES` entry
in `scripts/providers/etiketti.py`.

```
/elokuvat/ohjelmistossa      -> movie links /elokuvat/{id}/{slug}
/elokuvat/{id}/{slug}        -> every screening for that film
```

Per screening, inside `<div class="item ... date-D.M.YYYY">`:
- `date-27.8.2026` class carries the full date including year; time from `klo HH.MM`
- `TRIO 123 | VIP-SALI` — but **Kinopalatsi screenings have no room and no `|`**, so the
  room must be optional in the regex (this silently dropped 17 showtimes first time)
- `Lippu 18,00€` and `Vapaat paikat 13/22` -> price and real sold-out state
- Booking link `/salikartta?id=NNNN`
Film-level: `<h1>` title, `ikarajat/fi-16.svg` -> rating, `Kesto: 2 h 53 min` -> minutes,
`Kieli:` / `Tekstitys:` -> language tags, `<img class="poster-img">` -> poster.
Roughly 1 listing + ~15 movie pages per run, paced 1.2 s apart.
Kotka venues: Kinopalatsi (no rooms, ~236 seats), Trio 123 (SALI 1/2, VIP-SALI).

### Synopses and enrichment
`scripts/providers/enrich_tmdb.py` runs last in the cloud workflow and merges into
`data/films-extra.json` — it never overwrites text a provider already supplied.

Priority: the cinema's own text (Finnkino `films.json`, or provider page text merged via
`scripts/providers/synmerge.py`) > TMDB Finnish > TMDB English.

- `films-extra.json` is keyed by normalised title. **Three implementations of that
  normalisation must agree**: `enrich_tmdb.norm()`, `synmerge.norm()` and `normTitle()` in
  index.html. A mismatch fails silently with no synopsis and no error.
- The two Python ones strip `_` explicitly (`[^\w\s]|_`). `\w` counts the underscore as a
  word character, `\p{L}\p{N}` in the client does not, so a title containing one would
  have keyed two different ways and lost its synopsis with nothing in the log. No title
  has used one yet — checked at the change, 90 keys in each cache, zero underscores — so
  this is a latent divergence closed before it fires, not a bug fix.
- Synopses live in that one file rather than on each show: a 300-char synopsis repeated
  across BioRex Tripla's 158 showtimes would add ~50 kB to a single venue file.
- Provider helper fields `_syn` / `movieUrl` are stripped before area files are written.
- BioRex fetches ~28 film pages per run (0.4 s apart) for synopsis, runtime and genres.
- Kinoset's API `description` is mostly empty and it only tags genres on some shows, so
  those fall back to TMDB.
- **Match on the title, not on TMDB's popularity order** (2026-08-27). `hits[0]` sent
  Orion's "Mother" to the poster for "Mother Mary": TMDB search sorts by popularity, so
  a short generic title lands on whatever is trending. `pick()` prefers a hit whose
  `title` or `original_title` normalises exactly to the query and only then falls back to
  the popularity order, because a Finnish distributor title often matches nothing exactly
  and a weak match still beats no film. Fallbacks are named in `run-enrich.log` as
  **weak match**, which is the list to read when a poster looks wrong.
- **A title can carry two strand prefixes, and `split()` takes one per call.** Orion
  published "Espoo Ciné: Artist in Focus: Mare's Nest": the festival, then its section.
  The adapter's own `split_strand` took "Espoo Ciné" and stopped, so the section stayed
  in the title, TMDB matched nothing and the film lost its poster, rating, trailer, genre
  ids and merge-by-id — all four, not just the poster that made it noticeable.
  `run.py` applies `strands.apply` centrally *after* the adapter, so a second known
  prefix does come off, which is why adding "artist in focus" to `EVENT_PREFIXES` is the
  whole fix here. A provider that does not also split in its own adapter gets one pass
  only and would still need a loop. Not looping in `split()` on purpose: one call, one
  prefix keeps the exact-list guarantee easy to reason about, and two-prefix titles are
  so far a single showtime.
- **A programme is not a film and will never match.** "Follow The Plants" (Orion, a
  curated multi-artist assembly) and the Gilda playback nights sit in the no-match list
  permanently and correctly. The list is for finding *missed* films; entries that belong
  there are not a backlog.
- **Both passes must log the titles that match nothing, not just the weak ones.**
  `fetch_data.py` printed weak matches and held-back ratings but never a no-match list, so
  "Ryhmä Hau: Dinoelokuva" sat with an empty id for a day — no rating, no genres, a clean
  log. A weak match is at least visible; a missing one was not. Both passes now print it.
- **Search with `language=fi-FI`, or the exact-title test can never fire on a Finnish
  title** (2026-08-27). Without it TMDB answers in English, so `pick()` compared
  "Autofiktio" against "Bitter Christmas", "Kuopus" against "The Little Sister" and
  "Kummisetä osa II" against "The Godfather Part II" — and wrote all three off as weak
  matches. The ids were right the whole time; TMDB has registered Finnish titles and
  had matched them. The cost of the mistake was not a wrong film but a missing one:
  a weak entry gets no `tmdbId` and no `gids`, so 29 films were excluded from cross-chain
  merging and from genre-based filtering for no reason.
  `language` localizes the response, it does not widen which titles are searched, so this
  is presentation rather than matching — the fix is one query parameter, not 29 aliases.
  **Verify before writing aliases**: a "weak match" line is a claim about the comparison,
  not about the film.
### The score ring (2026-08-27)
The score is a ring: arc length for the glance, the number inside, the vote count beside
it, since 7.1 from 41 votes and 7.1 from 15 000 are different claims. A rating under
`VOTE_SOLID` = 25 votes is dimmed rather than hidden.

Two departures from TMDB's widget: one hue, not green/amber/red, since colour is spent on
chain identity and red-vs-green is the classic colourblind failure; and not a copy of
their component, which would imply an endorsement. IMDb's ratings dataset names
"where/what/how to watch applications" as a licensed commercial use, so it is out; Trakt
and Leffatykki are unexplored alternatives.

- A rating needs votes: `vote_average` written straight through showed ★10 on a festival
  premiere with three votes. Ratings come from the movie detail call and are stored only
  above `MIN_VOTES` = 25; the count lives in the cache as `n`, held-back ratings are
  logged. The cache was rebuilt once when `pick()` landed.
- The search loop tries every candidate until one matches exactly and keeps the first
  hit as the fallback: "Die Hard 2 - Die Harder" returned *Die Hard* on candidate 1 while
  candidate 2 matched exactly.
- Film identity across chains is the TMDB id: BioRex publishes "Mutiny", Finnkino "Mutiny
  - Lavastettu syylliseksi". Both passes write `tmdbId`, only for an exact match (`x` in
  both caches), since a weak id would fold two films into one. Dropping everything after a
  dash in `mergeKey()` was rejected: it would merge "Mission: Impossible - Dead Reckoning"
  into "Mission: Impossible".
- Reissue markers belong in `mergeKey()`: `(re-release)`, `(uudelleenjulkaisu)`, `(uusi
  kopio)` alongside `(suomeksi)`, and `PAREN_NOISE` gained `uudelleenjulkaisu`.
- Name merging is still required for films where one chain got no exact match.
- Finnkino publishes the bar-screening attributes; `EVENT_ATTRS` keeps `Annisk_K18`,
  `Anniskelu` and `EventCine`, and `Annisk_K18` sets `age`. Dropped attributes are logged.
- The release-year filter defeats aliases and reissues: `Autot (uudelleenjulkaisu)`
  carries the reissue year. The search retries without the year whenever it produced no
  exact match, and never applies a year to an alias search string.
- `fetch_data.py` needs candidate queries too: `_queries()` yields the de-noised title,
  the raw title, then the head before a dash. Never before a colon, which would search
  "Mission" for "Mission: Impossible - Dead Reckoning". `enrich_tmdb.queries()` still
  splits on a colon, which is worth watching.

### Strand prefixes are split off centrally (2026-08-27)
`scripts/providers/strands.py` owns the exact list and the split. `enrich_tmdb.clean()`
imports the list for the TMDB search; `run.py` applies the split to every adapter's shows
and `fetch_data.py` to Finnkino's, so a strand goes to `method` and the bare film title
stays in `title`. Only `orion.py` did this before, which left Gilda selling
"Seniorikino: Hetki Ennen Valoa" as a film of its own — fragmented from the plain title,
unmatchable on TMDB, and sharing an initials tile with every other Seniorikino screening.

- **Exact list, never a `^\w+:` pattern.** In one day's data the colon prefixes are
  "Spider-Man:" ×443, "Ryhmä Hau:" ×272, "Insidious:" ×159 against "Seniorikino:" ×4 and
  "Pieni elokuvakerho:" ×3. A pattern would behead every franchise in the schedule.
- Real strands are rare (about 10 showtimes a day, Gilda and Riviera), so this is
  structure rather than volume: a new adapter inherits it without knowing it exists, and
  a new strand is one line that fixes the search, the merge and the tile at once.

### Genres come from TMDB ids (2026-08-27)
Provider genre strings are unusable as data: four spellings for the family genre, trailing
spaces, Orion publishes none, and in English mode they stay Finnish. Both TMDB passes keep
the genre ids from the `/movie/{id}` response they already fetch; ids land on each show as
`gids`, and `data/tmdb-genres.json` holds the id -> name map for `fi`, `sv` and `en`.

- TMDB's Finnish genre names are real translations: 18 of 19 differ from English.
- The kids filter cannot whitelist Animation and Family: TMDB tags "Marsupilami" as
  Adventure, Comedy. The rule: rating gate first, then ids `16`/`10751` mean kids,
  `99`/`18` without them mean not kids, no ids means rating alone.
- Provider strings stay as the fallback. Entries without `g` count as incomplete.
- Film facts fold from every showtime; screening facts from the surviving ones. Toggling
  "Suom. puhe" changed a card's genres because Finnkino and Gilda disagree on "Laula
  minulle Arja". `tmdb`, `tr`, `img`, `len`, `genres`, `rating` and `original` fold from
  the unfiltered set, genres taking the longest string; `lang` stays on the filtered set.
- Chains disagree more than expected: for one documentary Kotkan Leffat published `SV-S`,
  which the client's `LN` map keyed on `SE` rendered as a bare "SV". Fixed in `etiketti.py`.
- The sheet's chain key is sticky (`position:sticky; top:0` with negative side margins).
  Day headings are not, since the legend wraps at narrow widths.
- The times list carries the venue on the meta line as a `.theatre-tag` in a combined
  view, and the stub gains the chain tint.
- English titles resolve through `_eid`: `disp()` looked up `films.json` with the merge
  key and showed the Finnish title in every combined view. `filmEntry()` scans the
  group's showtimes for the Finnkino member and falls back to the show's `original`.
- Never translate `s.title` itself: it is the key for `mergeKey()`, `normTitle()`, the
  TMDB title cache and `tmdb-aliases.json`. English titles are a render-time substitution.
- Merge on the union of both signals: keying by `tmdbId` when present unmerged "Maailman
  rikkain nainen", which had an id at Gilda and none at Finnkino. `mergeIds()` unions the
  title key with the id key.
- A merged card folds metadata by first non-empty, not from `times[0]`.
- `tmdb-aliases.json` is read by both passes; an alias id triggers a `/movie/{id}` call in
  `fetch_data.py` so the vote floor still applies. Aliases are keyed by the title as each
  chain publishes it (`autot re release`, `autot uudelleenjulkaisu` both map to `Cars`).
- The two TMDB passes stay separate and agree on the rules (exact-match preference,
  `MIN_VOTES` = 25, `n` and `x` in both caches) but fetch at different times, so the same
  film can briefly carry two ratings. A single shared pass is not written.

### Riviera (added 2026-08-27)
WordPress admin-ajax, no auth, one request covers both venues:
```
POST /wp/wp-admin/admin-ajax.php
     action=filter_movies&date=&movie=&area=1040&singlemovie=&initial=1
-> {"success":true,"data":{"movies":"<ul class=movielist>…</ul>"}}
```
- `area` (1040 all / 1024 Kallio / 1039 Punavuori) is ignored by their backend, so the
  adapter splits on the `location` field ("Kallio, Sali 1") instead.
- Per `<li class="movielist__item single-show">`: `.date` ("To 27.8.2026"), `.time`,
  `.location`, `.movielist__item__title`, `Varatut paikat: 50/50`, `Kesto: 1 h 48 min`.
- Sold out = all seats taken or the button carries `disabled`.
- 24 dates out to +5 weeks, the longest horizon of any provider. Repertory titles
  (Amélie, Trainspotting, Twin Peaks) so the TMDB pass picks up a lot of new entries.
- The bundle that revealed the endpoint: `/app/themes/riviera/public/js/app.*.js`.

### Vista public XML — a *platform*, and the one to grow (added 2026-08-27)
`scripts/providers/vista.py`. Vista is the ticketing system behind Finnkino, and its web
front end exposes unauthenticated XML services. A Vista cinema that leaves them open is a
`SITES` entry with a base URL and a venue list. Test a candidate with
`{base}/xml/TheatreAreas/`.

```
GET {base}/xml/TheatreAreas/                    -> ID + Name per area
GET {base}/xml/Schedule/?area={id}&nrOfDays=31   -> every Show in the window
GET {base}/xml/ScheduleDates/                   -> published date list
GET {base}/xml/Events/                          -> per-film synopsis, cast, credits
```

- No auth, no Cloudflare, datacenter IPs fine. Runs on Actions.
- `nrOfDays=31` is honoured, so one request per area covers the window. A one-day fetch is
  not enough: Kitee had 0 shows today and 7 in the window.
- Areas map to one or two theatres and each Show carries `TheatreID`, so venues split from
  the data.
- Richest field set of any provider: `OriginalTitle`, `LengthInMinutes`, `Genres`,
  `PresentationMethod`, four poster sizes, nested language elements with ISO codes, a
  per-show deep link in `ShowURL`. No seat counts.
- Handled in the adapter: `Rating` is `"K-7 (4)"` or `"Sallittu kaikenikäisille"`, not a
  bare `"K-7"`, which the client's kids filter would silently miss; parse
  `dttmShowStartUTC` and convert through `Europe/Helsinki`; `SubtitleLanguage2` can carry a
  `Name` with an empty ISO code; `TheatreAuditorium` is `"Joensuu, Tapio 4"`, so strip the
  city and blank a room that repeats the venue; synopsis tag names vary between versions.

### Gilda / MyCloudCinema (added 2026-08-27)
`scripts/providers/gilda.py`. Two Helsinki venues: Gilda salit 1-3 and Bio Rex Lasipalatsi
(the historic cinema, not the BioRex chain). The listing is a React app whose API config
the page prints for anonymous visitors:

```
GET {base}/wp-json/gilda-react-booking/v1/movies
-> {"fi": {"data": [ {film..., show_times:[...]} ], "resultCode": 0}}
GET {base}/wp-json/gilda-react-booking/v1/cinemas    -> cinema_id 15, Narinkka 2
```

- One request covers everything (35 films / 101 shows / 22 dates). The namespace also
  holds write and administrative routes, closed to anonymous callers, never called, not
  inventoried.
- Venues split by `cinema_screen_id`: screens 66/67/68 are Gilda 1-3, 69 is Lasipalatsi.
- Handled: `rating_name` is bare ("12", "16", "S", "T", "EI MÄÄR."); `screen_name` for
  Lasipalatsi carries "(K-18)", a door policy, not a rating; `subtitle_lang` arrives as
  Finnish words, codes or "-"; `description` is HTML with entities; `show_time` is UTC.
- Posters need the movie id and a width: `{host}/media/posters/{movie_id}/1080/{uuid}.jpeg`.
  A bare `/media/posters/{uuid}` guessed from the bundle 404'd for every film and the
  client's fallback tile hid it. The correct shape was visible in BioRex's committed poster
  URLs, since both are on MyCloudCinema.
- Per-film pages exist at `/elokuva/{slug}/`, which is where showtimes link. The booking
  API carries no slug, so the mapping comes from `GET /wp-json/wp/v2/movies?per_page=100
  &_fields=link,title`, matched on `movie_name` then `original_title` ("Maailman rikkain
  nainen" resolves via its original title). No fuzzy matching: prefix and substring rules
  sent a film to three unrelated club screenings. Coverage 99/100; twelve generated URLs
  were status-checked before shipping. Look at the site before concluding a link does not
  exist: the first conclusion came from searching the React bundle only.
- The main house is Gilda Kamppi; `short` carries "Kamppi" so the client does not render
  "Gilda Gilda". The sibling keeps `short: "Bio Rex Lasipalatsi"`.
- Seat counts would need the closed seatplan endpoint, so `soldOut` is always false.

### Cinema Orion (added 2026-08-27)
`scripts/providers/orion.py`. One venue, Eerikinkatu 15, Helsinki, run by ELKE ry. Single
screen, so `aud` stays blank. One request to the front page: `<table class="kinola-day">`
per day, one `<tr>` per screening. First live run: 31 showtimes over 11 dates, 28 films.
Runs on Actions; only `tickets.cinemaorion.fi` blocks datacenter IPs and the adapter never
touches it.

```html
<td class='date'> Torstai 27.08. </td>
<td class='time'>17:15</td>
<td class='title'> Espoo Ciné: The Good Daughter </td>
<td class='price' title="Peruslippu, alennusryhmät: 13 €, Peruslippu: 13 €"> 13&nbsp;€ </td>
<td class='link'> <a rel="external" title="..." href='https://orion.kinola.ee/web/screening/{uuid}'>Liput</a> </td>
```

- The title cell has two shapes. A row with a film page is `<a href='/elokuvat/{slug}/'
  title ="Film"> Film <span class="descrption">blurb<span> </a>`; flattening it glued the
  blurb onto the title and split one film into one "film" per blurb (31 shows, 30 ids).
  The title is read from the anchor's `title` attribute and `eventId` from the slug.
- `descrption` is the site's spelling and its inner span is never closed. The blurb goes
  to `_syn`; synmerge only fills an empty slot.
- Attribute quoting is loose (`title ="Film"`, `13&nbsp;€`).
- The price cell's `title` attribute carries the ticket-type breakdown, so a screening
  with cheaper types shows "alkaen {cheapest}€".
- Ticket URLs come from the markup, never built. On 2026-08-27 every row pointed at
  `orion.kinola.ee/web/screening/{uuid}`, so the festival box-office case is unexercised.
- Third-party events (festivals, HopeaCine, Pieni elokuvakerho, playback nights) are real
  screenings and stay. The strand name is split off into `method` from the shared list;
  added `espoo ciné`, `espoo cine`, `pieni elokuvakerho`, `pitchblack playback`,
  `hopeacine`. Titles with no TMDB entry ("Follow The Plants", a Coltrane playback) keep
  their initials tile.
- The bad first run left 13 glued-title keys in `data/tmdb-titles.json`; pruned.
- `/wp-json/wp/v2/elokuvat` gives film pages (636 over 7 pages) with no posters:
  `featured_media` null, no `<img>` in content, only Yoast's 16:9 `og_image`. Do not swap
  Orion's stills in for TMDB posters: a 16:9 still cropped to 2:3 is a downgrade, and the
  one gap with a slug is a 1600x900 TIFF Chrome will not render.
- Wrong assumptions recorded so they are not repeated: ELKE's "Rajapinnat" page is an
  arts programme, not an API; the `naytokset` post type answers 200 with an empty list;
  Kinola exposes only an admin login and screening pages rendered client-side.

### Kino Engel (added 2026-08-29)
`scripts/providers/engel.py`, one venue, runs locally. Accent `#B47ACC`.

- The accent was measured with a broken metric; re-measured 2026-08-30 with
  `accent_check.py` its worst same-city pair is 18.5 normal, 15.2 deutan (against Gilda),
  above the set's floor. See "The accent numbers, re-derived".
- Parses rows, not day headings: each row carries its own "La 29.08." beside "klo 17:30".
- No room, price, runtime or rating in the listing; the row's only link is the film page,
  so `book` is `buy` pointing there. Dates carry no year; the [today-45d, today+320d]
  window picks it.
- Deduplicates on (eventId, start, aud): a film appears in a carousel and in the day list.
- Attribute quoting is mixed (WordPress double, the Johku widget single); the first
  version matched double only and every poster came back empty. Every attribute regex
  accepts both.
- Posters are hosted on `johku.com` and go through `mirror_posters.py`.
- The programme is rendered twice and the second copy has no times. The first version
  counted every timeless row as an upcoming film (46, 44 of them duplicates). The log now
  reports only dates no timed row covers (2 on 2026-08-29).

First live run, 2026-08-29: 41 showtimes, 17 films, 11 dates, 6 KesäKino, 41 posters, 0
failures. Two rows needed aliases: "Minioner & monster" and "Kokuho - kabukin mestari"
matched correctly but weakly, verified against the cache before writing
`tmdb-aliases.json`. Expect this from any provider with a Swedish-language strand.

Engel writes no `rating` on any show: the front page carries no age limit, runtime or
price. The film pages close that gap (next entry).

### Engel's film pages, and the Johku wall (2026-08-29)
`/elokuva/{slug}/` carries the rating, runtime, genres, spoken and subtitle languages,
original title and the cinema's own Finnish synopsis, none of which is in the listing.
`engel.enrich()` fetches one page per showing film, 17 on the first run, paced 0.5 s.

- **The rating is in the class, not in the text.** The markup is
  `<span class="rating K-12"><span>Ikäraja ei vielä tiedossa</span></span>`, so reading
  the text gives every film the same placeholder. The sibling spans (`seksi`,
  `paihteet`, and presumably `vakivalta`/`kauhu`) are KAVI content descriptors, which
  this app does not render, so only a `K-nn` or `S` token is kept.
- **A one-item fixture skipped the only line that mattered.** `enrich()` shipped without
  `import time`, and both the compile check and the unit test passed: `py_compile` does
  not resolve names, and the test had a single film, so `n` was never non-zero and
  `time.sleep(0.5)` was never reached. It failed on the first real call. A fixture has to
  exercise the loop, not just the body — two items, not one, whenever there is pacing or
  an index in the code.
- Labels repeat their wrapper class: `cmd-ohja` holds both OHJAAJA and IKÄRAJA,
  `cmd-kieli` both KIELI and LISÄTIEDOT. Parse on the `<label>` text, never the class.
- Languages come out as "puhuttu kieli: englanti" + "Suomi-Ruotsi" and map to
  `EN-A, FI-S, SE-S`. **`SE`, not `SV`** — etiketti.py already had to be fixed for
  publishing `SV-S`, which the client's `LN` map renders as a bare "SV".
- Genres are published in caps ("KOMEDIA,DRAAMA") and are capitalised on the way in.
  They are only the fallback for films TMDB misses, since the cards render from `gids`.

#### The Johku chase, and why it stopped (2026-08-29)
Six rounds of probing for a Johku showtime feed. Outcome: none usable; the front-page parse
stands.

The film page renders a table with the year, the auditorium, the per-screening price and a
booking button, cleanly classed (`_kj_showtime_*`), and none of it is in the 81 kB the
server sends. The path: `johku.com/kinoengel/allproducts.json` 403 (wrong path);
`widget-module.js` publishes the shop id and locale, and `settings/public.json`,
`storefrontsettings.json` and `widgets/{id}.json` are public;
`categories/2/allproducts.json?details=true` is 200 with 781 products but carries only the
next show per product; per-product detail is empty, 404 or 403; the `rs-johku-wordpress`
loader hands off to an authenticated widget call. The show list is reachable only with the
widget's `X-ApiKey`, which is the line in "Access and ethics".

Consequences accepted: `price` and `aud` stay empty for Engel, a showtime opens the film
page, and dates whose times exist only behind the widget stay missing. Two wrong
assumptions cost round trips: that the first 403 meant a closed API, and that
`widget-module.js` rendered the table. Find the code that builds the URL before trying
URLs. Johku remains a platform lead: another cinema rendering `rs-johku-schedule` would be
a `SITES` entry against the same parser.

### Probed but not yet added (2026-08-27)
Kino Engel (kinoengel.fi, Sofiankatu 4, Helsinki), added 2026-08-29; the probe notes:

- Every path answers HTTP 202 with a 169-byte meta-refresh shell and `SG-Captcha:
  challenge` to a runner: SiteGround's protection on IP reputation. Runs on the local half.
- The WordPress REST API is open from an ordinary connection (`/wp-json/` 200, 372 kB) and
  `/xml/TheatreAreas/` is a clean 404, so Vista is out.
- The front page carries the KesäKino screenings, so `/kesakino/` is a landing page, not a
  second source.
- The prefix is in the slug as well as the title (`autofiktio`, `kesakino-autofiktio`), so
  identity comes from the cleaned title, never the slug.
- `acf` is empty on every `wp/v2/elokuva` post and the endpoint returns the whole archive
  (899 films), so REST holds no schedule.
- Three strand prefixes: `KESÄKINO:`, `BARNSÖNDAGAR:`, `BARNFESTIVAL:`. Kesäkino is a room
  and goes to `aud`, not a strand and not a separate venue: a room is not a cinema, and a
  seasonal venue would sit empty for nine months in a picker that lists every venue.

### Swedish: who actually publishes it (probed 2026-08-29)
Four covered cities are Swedish-strong (Vaasa, Pietarsaari, Porvoo, Kokkola), 23 of 48
venues sat in bilingual municipalities and 1920 showtimes carried Swedish subtitles, so a
Swedish mode has an audience. It has little Swedish source text.

- BioRex publishes a real Swedish edition: `admin-ajax.php?lang=sv` returns genuine
  Swedish distributor titles (Autot -> Bilar, Päivien lumo -> Skimrande dagar); 6 of 22
  differ, and its 12 venues include Vaasa, Pietarsaari and Porvoo.
- Finnkino has none: `hreflang` declares `fi-fi` and `en`, `/sv/` redirects to Finnish,
  and the site's configuration API accepts only `fi-FI` and `en`.
- eTiketti has none: `/sv/` on kotkanleffat.fi and biorex.org is a soft-404 with zero film
  links. Count the films, not the 200s.
- Savon Kinot's `/sv` is a 404.

Decision: Swedish UI everywhere, Swedish titles at BioRex when built, and Finnish as the
fallback title, not English: the Finnish distributor title is what the ticket and the
cinema's page print. The UI strings need no pipeline change and are most of the value;
Swedish titles would cost BioRex a second fetch per venue and a new per-show field, since
`title` is the merge key.

### Bio Rex Kokkola, the first site off the sweep (added 2026-08-29)
`biorex.org`, one venue, `etiketti.py`, no parser change. The existing adapter returned 41
showtimes over 10 dates with rating, runtime, genres, languages, price, booking links and
seat counts, plus 18 synopses, so eTiketti sites are worth adding on the platform alone.

- Not the BioRex chain (`biorex.org` against the chain's `biorex.fi`), so the label spells
  the city out and the accent was chosen away from BioRex blue.
- One venue, three rooms (DIGI 1, DIGI 2, SALI 3) under one place name; the room stays in
  `aud`.
- Accent `#006655`, unconstrained since Kokkola has no other chain. The numbers first
  recorded here were unreproducible; see "The accent numbers, re-derived".

### The cinema-list lead: nytleffaan.fi, probed 2026-08-29
`nytleffaan.fi/elokuvateatterit/`, run by Suomen Filmikamari, lists every Finnish cinema:
225 entries across 152 hosts, each linking the cinema's own site. The page needs a browser
to render, which is why it sat unprobed.

Swept 103 of the 152 from an ordinary connection, two requests per host: the homepage for
a platform fingerprint and `/xml/TheatreAreas/`. A signature in someone's HTML proves they
are a platform's customer, not that the platform answers us, so hits were verified against
the endpoint each adapter needs.

- eTiketti: 22 hosts carry `etiketti.app`; 16 serve the `/elokuvat/ohjelmistossa` listing
  (biorex.org 31 film links, kinopirtti.fi 16, arthousecinemaniagara.fi 15, leffabuumi.fi
  13, studiot123.com 12, ihmekompleksi.fi 10, kino123.fi 9, jamsankinotar.fi 8,
  kinojuha.fi 8, studio123.fi 8, biogrand.fi 7, biovuoksi.fi 7, kinoiiris.com 7,
  kino.joutsa.fi 4, k-kino.fi 3, biograni.fi 2). Counting links proved less than it reads
  as: Cinema Niagara renders its screenings in a different template.
- Nexxo: all 10 hosts carrying `nexxo-scope` answer `public_api.php`; six have live shows.
  kinohirvi.fi serves two locationids, so a host is not a venue. Corrected by the sweep:
  ksek.fi and kinoaurora.fi are one deployment, and kinohirvi.fi's id 4 is Bio Säde. Four
  hosts return valid JSON with zero shows at every id.
- Johku: `kuvatahti.johku.com` is in the directory; the widget claims for kinotapiola.fi,
  kulttuurimylly.com and virtasali.fi were corrected on 2026-09-05 (see "The Johku sweep").
- MyCloudCinema: mantsala.cine.fi.

Required before any of it lands: venue counts per host, overlap with covered venues, and
accents measured per city.

Competitive picture: nytleffaan.fi (industry-run, gets exhibitor data, excludes event
cinema and festivals), elokuviin.com (includes festivals), kinossa.fi. "Suomen kattavin" is
not a defensible claim against 225 directory entries and two services claiming full
coverage. What is true and checkable: chains merged into one city view, festival and
strand screenings included, sold-out marks and prices where published, no ads and no
tracking. Say the count and let it grow.

### The eTiketti sweep lands: fourteen hosts, sixteen venues (2026-08-30)
Every host the nytleffaan.fi probe lists as serving `/elokuvat/ohjelmistossa` became a
`SITES` entry against the existing parser. 11 chains to 25, 48 venues to 64, 33 cities to
45, measured from `run-pages.log` and the committed data. Measured end to end into a
throwaway directory first: 19 venues, 331 showtimes, 0 failures.

- Cinema Niagara was held back: it serves the listing but renders screenings in a
  different template (no `klo`, bare `10,00€`, "Seats available", an attribute between
  `<div` and `class`), which this parser read as zero. Added 2026-09-02; see the Pipeline
  entry.
- The colour rule bound in three new towns and the obvious pick was wrong in two. Green
  against Finnkino's orange measures 13.6 dE00 deutan, below the set's floor. Kouvola's
  first pick, magenta against teal, reads 43.5 normal and 6.9 deutan; repicked to blue
  against orange at 73.5, since both Kouvola chains are single-city. Vantaa settled on
  violet (57.4), Lahti on blue (60.3).
- Hues repeat across cities on purpose: the accent renders only in a combined city view,
  so the only pairs that exist are inside one town.
- A registry entry and a `SITES` entry are joined by a bare string, so
  `tests/test_registry_sites.py` asserts the join in both directions and that no two
  adapters claim one venue id.
- `book="buy"` for all fourteen: every screening row carries a `/salikartta?id=` link.
- A venue `short` that is a prefix of its chain label rendered twice ("Studio 123
  Järvenpää Studio 123"). Fixed in the adapter: `short` repeats the full label, which the
  existing guard collapses. The slug still doubles the city, the house pattern.
- Kouvola, not Kuusankoski: both sites give a Kuusankoski postal address, and the industry
  directory and searchers say Kouvola. Bio Grand is Vantaa, not Tikkurila.
- Joutsan Kino 403s a runner and was deleted to get the cloud run green; restored the same
  day once routing was per site. Deleting converted an infrastructure limit into missing
  coverage.
- The empty-site problem became live: K-Kino publishes 3 showtimes and Kino Saimaa 2. See
  "A quiet week is not a broken parser".

### Vista sweep — tried and failed (2026-08-27)
Guessed 45 Finnish cinema domains and probed `/xml/TheatreAreas/`: zero hits beyond Savon
Kinot. Azure blob enumeration on the shared asset host and a search for the vendor's client
list were also dead. Re-swept 2026-08-29 with the real 103-host list: still zero. Ten hosts
answered 200 with the site's own HTML, a soft-404; the first bytes are not `<?xml`, so
status alone would have reported ten false hits. The sweep was blocked for two days on a
presumed missing input (the domain list) that turned out not to be what made it fail;
korjaamokino.fi was not among the hosts probed and is a Vista site (see "The Johku sweep").

### The Johku sweep: three integrations, no shared listing (2026-09-05)
Do the four known Johku cinemas render the `rs-johku-schedule` markup `engel.py` parses?
Read as a visitor from an ordinary connection on 2026-09-05. No: Johku is the shop behind
the button, and each cinema renders its programme with its own site builder.

- Kino Tapiola (Espoo): its own WordPress theme. Johku is the basket embed and a per-film
  schedule widget drawn client-side. The programme is server-rendered on `/elokuvat/`, one
  `div.movie-list-movie` per screening with the date and year ("lauantai 5.9.2026 – Klo
  12:00"). The slug is per run (`autofiktio-4`, `-5`, `-6`), so the `eventId` cannot be the
  slug. No age rating on the film page, no `og:image`, no per-show booking URL. A
  non-residential fetcher got the rows. Parser-shaped, Engel-sized.
- Kulttuurimylly (Helsinki): Squarespace, programme only inside `<johku-widget>` filled by
  `johku.com/widget.js`. The Johku storefront is a Nuxt app whose `__NUXT_DATA__` carries
  `showschedule-*` keys, empty today since public screenings resume in autumn 2026. Re-read
  when the programme resumes; if the array fills, the storefront HTML is the read.
- KuvaTähti (Kuvala, Kauttuan Kuva): kuvatahti.fi is the Johku storefront behind Cloudflare;
  showtimes load client-side through `/api/auth/widget-session` and `X-ApiKey`, the route
  declined in "The Johku chase". Both venues listed nothing during a maintenance break.
- Virtasali (Kalajoki): WordPress, no Johku, a municipal culture hall with 0 of 12 events in
  `category-elokuvat`. Dropped.

Two probe details: Cloudflare answers the storefront with an HTTP 103 Early Hints interim
response, which `urllib` reports as the final status while curl reads through it; and
`?k=elokuvat` needs quoting in zsh.

Korjaamo Kino is a Vista site with the public services open: `/xml/TheatreAreas/` answers
`[{"ID":1007,"Name":"Korjaamo"}]`, JSON by default and XML on `Accept: application/xml`,
and `/xml/Schedule/`, `/xml/ScheduleDates/` and `/xml/Events/` do the same. 16 shows over 6
dates, one screen, `EventSeries` "HelAFF" on 10 of 16, `Images` empty, `Rating` "Ei
tiedossa" on 10. The 103-host Vista sweep missed it because korjaamokino.fi was not among
the hosts probed.

Kino Regina (KAVI's cinema at Oodi): WordPress theme `kinoregina2`; every showtime list is
injected by the theme's own PHP. `getShowtimesMoviesV2.php` with a POST body
`getShowtimesMovies=YYYY-MM-DD` returns the day list from that date as server-rendered HTML
(9 dates, 21 rows), each row with a `.time`, `a.title[href="/elokuva/{id}"]`, a `.start`
with the year, and a `kauppa.kavi.fi` ticket link. The film page renders showtimes too,
with Ohjaaja, Maa, Tekstitys, Kesto and Kopiotieto.

Order built: Korjaamo Kino, then Kino Tapiola, then Kino Regina. Korttelikinot coverage is
then complete: Orion, Riviera, Korjaamo, Regina.

### Korjaamo Kino: the Vista module gets a Finnish site (2026-09-05)
A `SITES` entry against `vista.py`, which had no site since Savon Kinot left it. The
committed snapshot: 16 showtimes, 6 dates, one screen, 10 of 16 in the Helsinki African
Film Festival. Verified as a visitor first: the Schedule XML names "Korjaamo Kino"
(TheatreID 1045, area 1007), korjaamokino.fi's `/cinemas` page gives Töölönkatu 51 B, and
the `/websales/show/{id}` ticket links answer 200.

Changes in the module:
- "Ei tiedossa" is no rating: `_rating()` returns "" for it; the Savon Kinot shapes ("K-7
  (4)", "Sallittu kaikenikäisille", "K16") are pinned by a test.
- A bare "Sali" is no room: `_aud()` blanks it, as Orion and Heureka publish none.
- The tag separator is the client's " · ", not ", ", so "2D" and "HelAFF" are two tags.
- Arabic gets a name in `NAMES`; the client's `LN` already renders `AR`.
- HelAFF is a strand prefix: `strands.split` takes it off five features ("HelAFF: Fez
  Summer 55") and leaves the shorts alone; `apply()` does not add the series twice.
- The docstring stops saying Savon Kinot was the only Finnish Vista site.

Accent `#C07E7E`: 19.7 / 18.5 / 17.7 dE00 (normal / Viénot / Machado) from Finnkino's
orange and 21.3 / 20.1 / 17.9 from Gilda's magenta, L* 59.6. Every darker rose tried
(`#AE6A72`, `#A4626B`, `#B5707A`) fell to 13.8 to 14.4 deutan against Gilda. Helsinki's
worst pair stays Finnkino/Cinema Orion at 14.4. `where="cloud"` was provisional.

Counts re-measured: 35 providers, 77 venues, 52 cities, 87 pages per language, 175 sitemap
URLs. `tests/test_vista.py`, 21 tests; 13 mutations, 12 red and one void (dropping
`dttmShowStartUTC` falls back to the local time, identical in the fixture).

Accepted: `price` empty (the XML carries none), `soldOut` false, posters from TMDB, "useita
kieliä" yields no audio tag.

First cloud run 2026-09-05 12:24 UTC (data commit `14888ed1`): 16 showtimes, `exit=0`, so
`where="cloud"` holds. Enrichment matched six films exactly and the four HelAFF features
weakly to their Arabic-titled TMDB entries; the four posters were checked by eye and are
right. Live: the venue is in the picker and in "Helsinki – kaikki teatterit (13)".

### Kino Tapiola: a parser for one listing page, keyed on the title (2026-09-05)
`scripts/providers/tapiola.py` reads `/elokuvat/` once and one film page per film. The
committed snapshot: 15 showtimes, 11 films, 6 dates, every showtime rated from its film
page. Verified first: the three Autofiktio runs (`autofiktio-4`, `-5`, `-6`) are identical
pages except the Johku show ids, which the fixture pins.

Decisions:
- `eventId` is `synmerge.norm(title)`, the key `normTitle` and the synopsis cache use, so
  the runs are one film. Nothing strips a trailing number ("Fez Summer 55").
- No images from the site (3:2 stills, no `og:image`); posters come from TMDB.
- The `cat-` class is the strand (`cat-seniorikino` → "Seniorikino" in `method`).
- Rows without a time are not screenings (`/elokuvat/tulossa/`), and an impossible date
  (31.2.) is skipped. The `/erikoisnaytokset/` pages repeat rows and are not read.
- `div.movie-list` present with no rows is a confirmed empty programme; the container
  missing is a changed template and fails the venue.
- Film page: age limit from the class (`info-icon age-limit-K-12`), "Elokuvan kesto 1h
  52min" to minutes, "Kieli OV" yields no audio tag, "Tekstitys Suomi/Ruotsi" to `FI-S,
  SV-S`, synopsis from the description minus the press quote.
- `book="buy"`: the film page is where the Johku embed sells the ticket.

Accent `#003CFC`: 52.7 / 80.4 / 71.6 dE00 from Finnkino's orange, Espoo's only other
chain, L* 38.3. `where="cloud"` provisional. Counts: 36 providers, 78 venues, 52 cities,
88 pages per language, 177 sitemap URLs. `tests/test_tapiola.py`, 20 tests; 15 mutations
red.

Accepted: `price` empty, `soldOut` false, "Myrskyn ikkuna (ennakkonäytös!)" and "Päivien
lumo + tekijävierailu" keep their suffixes and will not match TMDB until the run ends.

First cloud run 2026-09-05 14:29 UTC (data commit `535032dd`): 15 showtimes, 15 of 15
rated, `exit=0`. Enrichment matched nine of eleven films. Before that run the cards showed
initials tiles and no scores for about 45 minutes: a provider commit carries the raw
adapter output, and everything TMDB supplies waits for the next cloud run.

### Kino Regina: the theme's own schedule endpoint, read from a runner first (2026-09-05)
`scripts/providers/regina.py` posts to the theme's `getShowtimesMoviesV2.php` and reads one
film page per film. The committed snapshot: 21 showtimes, 17 films, 9 dates, every showtime
rated, 17 synopses from the cinema's own text.

The runner probe: a throwaway workflow on a branch (deleted after reading) fetched the
listing, the POST and a film page from a GitHub runner with the adapters' User-Agent, one
pass-or-fail step per finding, readable from the unauthenticated jobs API. All six green,
no challenge header. The pattern costs one branch push and a token with the `workflow`
scope, and answers "does this host challenge a datacenter address" before a parser exists.

The endpoint: a POST body `getShowtimesMovies=YYYY-MM-DD` returns server-rendered HTML, one
`div.movie` per screening with the time, the title linked to `/elokuva/{id}`, the start
with its year and the show's KAVI ticket link. A past start date is clamped to today; each
answer covers about two weeks and ends with a "Lataa lisää" button naming the next window.
The adapter follows the button while a window has screenings, at most four times.

Decisions:
- `eventId` is the film id from `/elokuva/{id}`.
- "Myynti on päättynyt." is not sold out; the door may still sell.
- The ticket URL is the show's own KAVI buybox link; a row without one falls back to the
  film page. The footer credits kinoregina.fi, where the schedule is read.
- Teemat is a strand tag only for a concise named series (at most 26 characters, four
  words, no colon, none of the cinema's scheduling words). Kopiotieto only for a film gauge
  (8, 16, 35, 70 mm). Kuvaus alone is the synopsis; Lisätieto is never appended.
- The age limit is an image: `alt="Ikäraja: K12"` becomes "K-12".
- Titles are recased (revised the same evening). The site writes every title in capitals.
  A title with no lowercase letter becomes sentence case, roman numerals kept; then the
  film page's Kuvaus is searched for the same title in its own casing and that spelling
  wins. Every key that touches a title lowercases it first, so no cache or merge key
  moves. Two things moved in `run.py`'s carry-over of the previous file's enrichment: it is
  keyed on `synmerge.norm` rather than the exact title, and a mirrored TMDB poster is
  carried when the fresh show has none (a provider's remote URL is not). Both pinned in
  `test_run_partial.py`.
- No images from the site (16:9); posters come from TMDB.
- An empty answer is never an empty programme (revised the same evening, below).

Accent `#8A4854`: 18.4 / 19.9 / 18.4 dE00 from Gilda's magenta, 47.8 / 18.4 / 16.3 from
Riviera's teal, 50.7 / 16.9 / 16.3 from Cinema Orion's green, L* 39.0; Helsinki's floor
stays 14.4. A lead not chased: the film page's rows carry an Eventio `events.json` URL with
the page's key, so KAVI's shop runs on Eventio.

Counts: 37 providers, 79 venues, 52 cities, 89 pages per language, 179 sitemap URLs.
Korttelikinot coverage complete. `tests/test_regina.py`, 25 tests; 19 mutations red.

First cloud run 2026-09-05 15:51 UTC (data commit `164e45b9`): 21 showtimes, `exit=0`. Ten
exact ids; two weak matches right (The Turin Horse, part III of Once Upon a Time in China)
and two wrong (part I went to a 2021 documentary, part II took part IV's poster).
`tmdb-aliases.json` pins all three to Tsui Hark's films (10617, 10618, 10619, via Wikidata).

The evening run emptied the venue (16:57 UTC, data commits `164e45b9` then `19ec143a`): a
runner got one window with no screenings and a listing with no `shows-coming`, and the
emptiness rule published an empty file for an hour, while an ordinary connection got 21
rows. Two contentless answers in one minute from a host with `sg-f-cache` headers is
SiteGround's reputation challenge, the HTTP 202 shell that keeps Kino Engel local, which
`fetch` accepts as success. Fix the same day: `challenged()` names the shell and fails the
venue; an empty first window is asked for once more and then fails; `EMPTY_VENUES_CONFIRMED`
is gone from the module; the listing is not read. Whether Regina joins Engel on the local
half is a decision for the run logs.

Decided 2026-09-06: local. Of the six cloud runs after the fix, three were challenged (23:19,
05:19 and 13:44 UTC), each recovering on the next run. The 13:44 diagnostics artifact
(`ci_diag.py`) shows the same 167-byte shell for the homepage from that runner (centralus,
HTTP 202), so SiteGround refuses the address for the whole host and an in-run retry cannot
help. Failures came from northcentralus, westcentralus and centralus; passes from westus and
westus3. Nothing selects a region on hosted runners. `where="local"` on the registry entry
routes the module to the local half. The wrapper outside the repo got its block, its own
`run-regina.log` and its `git add` entry on 2026-09-06, placed before the poster step like
Joutsan Kino's so the run mirrors the posters it brings in: 15 of the venue's 20 showtimes
carry one. No `--half` flag, because the module has one site, that site is local, and off a
runner `half_of` defaults to `all`, which selects the same site. A fetch from an ordinary
connection that evening returned 20 showtimes over 8 dates and exit 0, so the routing is
the whole fix. The committed `run-regina.log` still ends `exit=1` and keeps `Check run
logs` red until the first local run overwrites it.

### Next providers
- **eTiketti is done** (2026-08-30): fourteen hosts, sixteen venues, see the sweep entry
  above. Cinema Niagara is the one host left behind, and it needs parser work rather than
  a `SITES` entry -- its screenings are server-rendered in a second eTiketti template.
- **Nexxo is done** (2026-08-30): six cinemas on five hosts, see the sweep entry above.
  Kino Metso, the touring locationid at kinoaurora.fi, is the piece left -- it needs the
  room-splitting `match` that `etiketti.py` already has.
- **Cinema Niagara** is the other parser-shaped leftover: eTiketti's second template.
- **Vista has one Finnish site after all: Korjaamo Kino**, probed and added on
  2026-09-05; see "Korjaamo Kino: the Vista module gets a Finnish site" above. Cinamon
  and other non-Finnish Vista users remain untested.
- **Johku is a ticketing platform, not a listing template** (2026-09-05). The four known
  sites render three different HTML shapes and none of them Engel's widget. Kino Tapiola
  got its own parser the same day; see "Kino Tapiola: a parser for one listing page"
  above. KuvaTähti and Kulttuurimylly are Johku-hosted storefronts to re-read once their
  programmes resume. Virtasali is a Kalajoki culture hall with no films listed.
- **Korttelikinot are complete** (2026-09-05): Orion, Riviera, Korjaamo Kino and Kino
  Regina. Korjaamo runs Vista, Regina a WordPress theme with its own showtime endpoint
  and KAVI's ticket shop; see their entries above.
- **Eventio** is a ticketing platform with cinema customers — another possible platform win.
- ~196 cinemas / 306 screens in Finland (2009), but the tail clusters onto a few platforms.
  Platform adapters first; bespoke sites only when a cinema is on none.

## Hosting

- GitHub Pages, free. Custom domain leffavuoro.fi (Nordweb, 12 €/yr, renews 12 €/yr).
- DNS at Nordweb: four apex A records `185.199.108-111.153`, `www` CNAME -> `leffavuoro.fi.`
- `CNAME` file in the repo root holds the domain; Pages + Enforce HTTPS on.
- `.fi` cannot be bought from Traficom directly — always through an approved registrar.
  Watch for registrars bundling parking/DNS services: the same domain quoted 12 €, 20 € and
  73 € depending on what was silently attached.
- Old `shady-dev.github.io/kino/` now redirects. A PWA installed from the old origin keeps
  its own service worker, so reinstall after the domain change.

## Refactor to do before adding more providers
Adding a venue to an existing platform is one line. Adding a platform used to cost four
files plus five frontend edits; all fixed:

- [x] `data/providers.json`, generated by `scripts/build_providers.py` from
      `scripts/providers/registry.py`. The frontend derives every label, host, accent and
      footer verb from it. No `generated` field, so identical bytes mean no diff. index.html
      keeps a hardcoded fallback list for a missing file or a stale service worker.
- [x] One generic runner, `scripts/providers/run.py <module>... | --where cloud|local`.
      Every adapter exposes `SITES` and `fetch_site(site) -> {venue_id: [shows]}`.
- [x] The cloud workflow loops over `registry.py --cloud`. Failure flags go to
      `$RUNNER_TEMP`, never into a commit; data is committed before the failure check so one
      dead provider still publishes the rest. The enrich gate reads its exit code from
      `$RUNNER_TEMP` rather than grepping `exit=0` out of a log that also carries film
      titles and TMDB error text.
- [x] `riviera.py` is parameterised by base URL.
- [x] Repertory titles: `clean()` in enrich_tmdb strips a trailing "(YYYY)", bracketed
      format noise, a trailing ", suomeksi" and a known-list event prefix. Only the search
      string is cleaned; `norm()` still keys on the published title.
- [x] `venues-{provider}.json` lists every venue of the site, and a venue with no shows and
      no file gets an empty one (2026-08-28). The file is written only when at least one
      venue produced shows.
- [x] A whole site parsing zero showtimes fails the run; `common.EmptyProgramme` on positive
      evidence of an empty listing is counted as `empty`. `tests/test_empty_programme.py`.

## Pipeline
- [x] **TMDB cannot be searched by Finnish distributor title.** Probed 2026-08-27:
      "Maailman rikkain nainen" gives 0 hits and `&language=fi-FI` also gives 0, while the
      original "La femme la plus riche du monde" gives exactly 1. `language` localises the
      *response* only; it does not widen the match, which covers original + English +
      registered alternative titles. Escape hatch: `scripts/providers/tmdb-aliases.json`,
      keyed by `norm()` of the published title, valued either a TMDB id (skips the search)
      or a replacement search string. `run-enrich.log` now names every title that found
      nothing, which is the input to that file. Wikidata (P4947 = TMDB id, matched on the
      Finnish label) is the automated version if this outgrows a hand list.
- [x] **MovieXchange API credentials, decided against 2026-08-29.** Server-side
      client_credentials would have moved the whole pipeline back to Actions. Not requested:
      an approach to a third party with no promise of free access. Reopen only if
      MovieXchange publishes open access terms. Consequence: the split pipeline is the final
      architecture. The MX CDN is a public read reached through Finnkino's own
      `moviexchangeReleaseId` and never needed credentials.
- [x] **Cinema Niagara, Tampere (built and live 2026-09-02).** The one eTiketti host the
      2026-08-30 sweep left behind: the same platform in a second template. Re-probed as a
      visitor: nginx, no Cloudflare, robots.txt disallows `/salikartta`, `/tili` and
      `/ostoskori`, which this repo never reads. Each film page renders its screenings as
      `<div\n class="item tampere date-3.9.2026">` with `<div class="time"><span>16.15`,
      `<div class="show-price"> 13,00€`, `Paikkoja vapaana: 126/127`, tags in `movie-specs`
      and no place line, where Kotka prints `KE 2.9. klo 20.00`, `TRIO 123 | SALI 2<br>
      Lippu 15,00€<br> Vapaat paikat 27/35`. Labels carry no colon; genres sit under a
      label reading `genre`. `/?shows=all` renders every screening twice (desktop and
      mobile wrappers).
      **Design.** A `SITES` entry with `etiketti.py` taught the second template: every
      regex is an alternation of exactly the two shapes; the place falls back to the item's
      place class (`tampere`) so `match` still selects the venue; `movie-specs` tags go into
      `method`; `_lang` reads Finnish language names through `LANG_NAMES`, the inverse of
      the client's `LN.fi` and asserted equal to it, matched on the first four letters.
      Shows are keyed on the `/salikartta?id=` href so a duplicated surface cannot double a
      show; a row without an id is keyed on film, start, place and auditorium, recorded
      only once a registered venue took the row. The ticket href is never fetched. Registry:
      `id="niagara"`, `book="buy"`, `module="etiketti"`, venue `cn-tampere`, accent
      `#6A4FBF` (47.0 / 68.1 / 60.6 dE00 against Finnkino; greens fail deutan). Seats are
      read only to derive `soldOut`; counts stay unpublished.
      **Tests:** `tests/test_etiketti_templates.py`, 32 tests; seventeen mutations red.
      **Live** (first cloud run 2026-09-02 10:40Z, data commit a7b2b8f7): 47 showtimes, 12
      dates, 0 failures, no `/salikartta` request; poster, runtime, genres and language on
      47 of 47, TMDB id on 39; language codes DA, EN, ES, FI, FR, IT, NO, SV, TR, every one
      the client names. Counts: providers 33, venues 75, canonical pages 170, sitemap 171.
      Deferred: seat counts on screen; credits.
- [ ] **Language codes normalised end to end (code landed 2026-09-02, sw.js v99).** Four
      codes in the data were not in the client's name table: `TU-A` 62 rows and `MA-A` 3
      rows (Finnkino's Turkish and Malayalam), `XX-S` 46 rows (Nexxo's "no subtitles"),
      `LT-A` 1 row (Lithuanian). `fetch_data.lang_tag` maps through `FINNKINO_LANG`
      (`SE`→`SV`, `TU`→`TR`, `MA`→`ML`), never touching the role letter; `nexxo._lang`
      drops `XX` from the subtitle role; the client's `LN` gains `LT` and `ML` in all three
      languages, and the generator's mirror too. Still open until a re-measure of
      data/area-*.json finds no `TU`, `MA` or `XX`, when `CODE_ALIAS`, `NO_SUBTITLES` and
      `LN_EXTRA` in `build_pages.py` go with their tests. After the 2026-09-02 cloud run
      `XX` was gone; `TU-A` and `MA-A` await a local run. `tests/test_lang_normalization.py`.
- [ ] Move the local fetch off the laptop onto an always-on box on the same network.
      Cloud VMs are not an option for the five providers that block datacenter IPs
      (Finnkino, Kino Akseli, Kino Engel, Joutsan Kino, and Savon Kinot since
      2026-09-04), and with the MovieXchange route closed above there is no other way off
      the laptop at all. 26 of 75 venues ride on that machine.
- [x] Finnkino ratings whitelisted to `S` and `K-n` (2026-08-28). The OCAPI
      classification text passed through raw when it did not start with a digit, and the
      live values include "Tulossa" and "-" (verified in committed data: 5 and 7
      showtimes), which rendered inside the age-limit chip and silently failed every
      `rating ===` comparison. Same bug class as the Vista "K-7 (4)" gotcha. Anything
      else now blanks; "coming soon" is premiere-chip material, not a rating.
- [ ] Finnkino prices. **Probed 2026-09-01 and blocked by the access rule rather than
      by difficulty**; see the entry below. The programme response the adapter already
      reads carries no price field anywhere, the obvious ticket-type read paths under the
      same API all answer 404, and the remaining route is the seat-selection flow, which
      this repo does not call or inventory. Left open only because a visitor-facing price
      *page* would be a legitimate source, and that has not been looked at.
- [x] **Commit run.log only on failure -- decided against 2026-09-01.** Across the last
      300 commits no routine run produced a log-only commit; logs ride inside data commits
      that happen anyway, and an unchanged log is not committed. A green run that commits
      nothing would leave the last red log on `main` forever, so `check_runs.py` would
      report the same failure every day (the `run-vista.log` incident). And the green logs
      are the record: the per-venue counts in a successful log are the only place a soft
      regression is visible. Reopen only if run logs start forming commits of their own.
- [x] Finnkino no longer publishes an empty area file when a venue returns no shows: it
      keeps the previously committed one, matching `run.py`. A file is still written when
      none exists, because `areas.json` lists every site regardless of shows and the picker
      would otherwise link to a 404. New log line: `N venue files written, M kept as-is`.
- [x] Dropped `data/attrs.json` and `data/film-sample.json`: written every Finnkino run,
      read by nothing.
- [x] Retry/backoff for transient API errors (2026-08-28). One transient 502 counted as a
      total site failure with the next cron four hours away. Shared
      `providers/common.py::fetch(url, headers, data, tries=3, backoff=5, opener)`, named
      `common` because a local `http.py` would shadow the stdlib. All nine adapters migrated
      one per commit, each keeping its own timeout and backoff (Vista 40 s, Gilda 45 s, Nexxo
      backoff 6). `common.fetch` retries only the request, not the parse: a 200 with a
      non-JSON body is a shape change to look at.
- [x] **Refresh on resume, not only on date rollover** (2026-08-28). An installed PWA is
      resumed, not reloaded, so `providerMeta` stayed frozen while the age counted up. The
      threshold is 10 minutes because Pages serves data with `max-age=600`.
      `fetchVenueLists` was split out of `loadAreas` so a refresh does not bounce the reader
      off their venue. Still open: a tab left visible all day never fires
      `visibilitychange`; a timer was not added.
- [x] Search input debounced 120 ms (2026-08-28): every keystroke rebuilt the whole list
      through innerHTML — ~90 cards in a combined Helsinki view — and the intermediate
      frames were discarded anyway. 120 ms is below the point where the list feels
      detached from the typing. Keyed DOM reuse is the real fix and was rejected: at this
      list size it buys nothing and costs a rewrite of the render path.
- [x] `fetchJSON` aborts after 8 s (2026-08-28): `fetch()` has no timeout, so a connection
      that opens and then stalls — a phone walking out of coverage, not a refused one —
      never settled and never rejected. The spinner ran forever with no error and nothing
      to retry, which reads as a broken app rather than a broken network. AbortController
      lets the existing `netErrorHtml` catch fire. 8 s because the files are small and a
      slow 3G first byte is still well inside it.
- [x] Atomic data writes (2026-08-28): every writer went through bare `write_text`, so a
      run killed mid-write left truncated JSON. Harmless on Actions (ephemeral runner),
      real locally: the wrapper writes into a checked-out repo and the next run's
      `git add data` would commit the torn file — and cancel-in-progress means
      mid-run kills happen. `common.write_json` / `write_text_atomic`
      (sibling .tmp + os.replace, atomic on one filesystem on both platforms) used by
      run.py, synmerge, enrich_tmdb and fetch_data. *.tmp gitignored for the narrow
      window between write and replace.
- [x] enrich_tmdb checkpoints its cache (2026-08-28): `tmdb-titles.json` and
      `films-extra.json` are written every 25 titles, not only after the loop. Each
      per-title body already catches its own exceptions, but anything raised outside one
      — the two genre-list calls, the area-file write pass, a cancelled runner — skipped
      the single end-of-run write and discarded every lookup of the run, ~300 TMDB
      requests on a cold cache, to be spent again four hours later. Cheap because the
      writes are atomic and the cache is idempotent: a partial write is simply a warmer
      start. Every 25 rather than every title because films-extra.json is re-read and
      rewritten whole on each flush.
- [x] **A cached TMDB rating stops being permanent** (2026-09-01). The skip was `complete
      and (c.get("v") or c.get("c") == today)`, so a trailer stopped an entry ever being
      read again. Measured on 2026-09-01: 156 entries, 96 with a trailer, 71 of those last
      read on 2026-08-27. Now age decides: `due()` fetches uncached or incomplete entries,
      keeps the daily no-trailer check, and re-reads a complete entry once it is
      `RATING_MAX_AGE` (7) days old, `REFRESH_BUDGET` (12) a run. The budget bounds the
      catch-up, since without it the first run re-reads all 71 at once and they come due
      together for ever; what it defers is printed.
      Three review findings fixed with it. The success path wrote the old rating stamped
      with today's date when both localized detail requests failed, and emptied the cached
      text: synopsis slots are now seeded from the cache and only a response that arrived
      replaces them, and `c` moves to today only when a detail response carried rating and
      vote data. The queue is ordered on `a`, the last attempt, not `c`: an unreadable id
      would otherwise outrank everything for ever. `a` is recorded even when the title
      aborts after its detail read, from the `except`, so a failing title cannot camp at the
      head. A rating needs both halves of the pair: a response carrying only `vote_count`
      had set the rating to 0 over a real one; zero counts as usable.
      `tests/test_tmdb_recheck.py`, 22 tests against a fabricated cache and `main()` with
      TMDB stubbed by URL; twenty-six breaks red.
- [x] **The same defect on the Finnkino path, fixed 2026-09-01.** `data/tmdb.json` had
      the same rule (46 of 59 entries frozen, 45 last read on 2026-08-28), and its detail
      request was conditional on `not votes or not gids`, so an age rule alone would have
      fetched nothing. The schedule is `providers/refresh.py`, shared by both passes; the
      Finnkino cache passes in its own `complete` predicate, since it carries no synopsis or
      poster. A failed video read no longer writes an empty string over a cached trailer.
      Tested with the pass lifted into `enrich_cached_ratings()` and TMDB stubbed by URL;
      the first fixture omitted `y` and every cached-entry test passed anyway, which an
      uncached film caught with `KeyError: 'y'`. The next local run is the operational
      check.
- [x] **Independent hosts are fetched at the same time** (2026-09-01). `run.py` pools
      over *hosts*, not over sites, and each host is still read by one thread at the pace
      its adapter sets. See "A run reads unrelated hosts at once" below for the host
      sharing that makes the site the wrong unit, the four hazards and what each cost.
- [ ] README workflow badge
- [ ] Credential hygiene and rotation: tracked in local private notes

### Ensi-illat renders as a badge on the film card (2026-08-27)
Finnkino has coming-soon pages, and the temptation is a "Tulossa" view. Rejected: every
row in this app ends in a bookable link, and an upcoming film has nothing to tap. Those
pages also carry placeholder metadata — "Kesto 0t 1min" on films months out — and **only
Finnkino publishes a coming-soon feed at all**, so the app would know about premieres at
one chain and be silently blind at eight.

What is worth showing is the premiere date of a film that is *already selling tickets*:
advance sales open days ahead, so a bookable showtime can sit in front of an opening
night, and then the date changes a decision. `films.json` keeps the full `releaseDate` as
`rd` (it was being truncated to a year), and the card shows an `Ensi-ilta 5.9.` chip while
the date is still ahead. Once the film has opened the chip disappears, because by then it
is noise. Finnkino-only by design; a guessed premiere is worse than none.

- Finnkino also curates https://www.finnkino.fi/elokuvat/lasten-elokuvat/ , an editorial
  list of children's films. That is a better authority for the kids filter than TMDB
  genre ids, and it would work cross-chain by title. It is also another scrape to
  maintain, on the local-only half of the pipeline, so it is worth it only if the genre
  rule proves wrong in practice. Watch the filter first.

### Swedish is the third UI language (2026-08-29)
Segmented `FI | SV | EN` in the header, replacing the two-state toggle, which cannot show
where you are at three. The control is the `.seg` pill already used for Leffat/Ajat.

- `flex:0 0 auto` on the pill is required: it clips its own overflow and silently ate "EN".
- `#themeToggle` needed `flex:0 0 38px`, or the language control squeezed it into an oval.
- At 320 px a `max-width:360px` block tightens the wordmark, segments and toggle: 103 + 86
  + 38 px plus gaps against 292 px, zero overflow.
- Swedish titles fall back to Finnish, not English: the Finnish distributor title is what
  the ticket prints.
- Cities get Swedish display names (Helsinki -> Helsingfors, Turku -> Åbo, Vaasa -> Vasa,
  Porvoo -> Borgå); `cityGroups`, prefs and the `?area=` links stay keyed by the Finnish
  name.
- Sorting is per language, one `Intl.Collator` rebuilt on switch. `<html lang>` follows.
- The Swedish strings are drafted, not translated, and need a native Finland-Swedish reader;
  the contact line is the one a cinema is most likely to read.

Genres were the last thing still Finnish in Swedish mode. The enrichment pass asks TMDB for
`sv-SE` as well, one more request per run; `fi` and `en` remain the bar for writing the file
and Swedish is included when it arrives. Verified 2026-08-30: 13 of 19 Swedish names differ
from English; of the six that match, five are correct Swedish and one is TMDB's own gap (id
10402 "Music", Swedish "Musik"; Finnish has 10770 "TV Movie" untranslated). `GENRE_FIX` in
`enrich_tmdb.py` renames those two after the response arrives, only for an id TMDB
returned. Exercised against live TMDB: exactly one override firing in `fi` and one in `sv`,
the body byte-identical to the committed map. A `genre names written` line reappearing, or
a diff on `data/tmdb-genres.json`, means `GENRE_FIX` stopped applying, most likely because
TMDB translated one upstream.

## App
- [x] **Segmented controls are rounded rectangles, not capsules** (2026-08-30, sw.js
      v72). Follow-up to the polish pass below: once the filter chips dropped to 7px,
      the two full pills left — FI/SV/EN and Leffat/Ajat — read as strays rather than
      as the primary tier. Both now share an 8px outer radius (a value already in use:
      poster, calendar buttons, dropdown options); the inner segments carry no radius
      of their own, the container's overflow:hidden clips them to its corners, so
      selected-segment fill, dimensions and hit areas are unchanged. The shape system:
      segmented controls 8px, filter chips and stubs 7px, date chips and inputs 10px,
      theme toggle a circle, stubs keep the perforation.
- [x] **Visual polish pass: boxes only where something is tappable or official**
      (2026-08-30, sw.js v71). Form controls lost their drop shadows; `.fmt` tags (2D,
      ANNISKELU, runtime, price) lost box and border and are small uppercase muted type;
      the premiere tag keeps weight through the accent colour. `.rating` and `.agelim` keep
      their boxes: an official classification is the chip shape's job. Filter chips dropped
      to the stub's 7px radius. Hover states added where transitions existed, `.stub:active`
      mirrors `:hover` for touch. Date labels get `text-overflow:ellipsis`. Untouched: stub
      shadow and perforation, the score ring, chain rules, the date chips' layout.
- [x] **XML/CORS-proxy fallback deleted** (2026-08-28). ~80 lines (PROXIES, fetchXML,
      the `state.mode='xml'` branches, the attempts log, the `content://` help text from
      the pre-hosting single-file era). It fired only when same-origin `data/areas.json`
      failed — the site broken or the visitor offline on first visit — and the proxies
      fail in both of those too. It also almost certainly could not succeed when reached:
      the proxies hit finnkino.fi from datacenter IPs, which answer Cloudflare 403. It
      silently routed visitor traffic through three third parties, against the README's
      privacy claims, and covered Finnkino only — a "fallback" that worked would have
      shown 17 of 46 venues. Same reasoning as the deleted fetch.yml and cf-worker. A
      failed areas.json now propagates to the boot's catch and the localized error text.
- [x] **Footer, loading and error strings localized** (2026-08-28). renderStatus built
      the line under every Finnish screen from English literals, and the two loading
      states plus the load-failure message never went through `L`. Now they do; the
      booking call to action uses `{host}` template strings per book mode. The static
      markup's loading text is Finnish (the default), swapped from `L` at boot for EN
      prefs. Finnish copy for the act strings is first-draft — polish welcome.
- [x] **Provider strings escape at the innerHTML boundary** (2026-08-28). Every adapter
      strips tags then unescapes, so a source page's entities arrive as live HTML
      metacharacters. One `esc()` at every interpolation of provider data, plus `safeUrl()`
      on every href/src. Adapters keep publishing verbatim text, since the raw title is the
      key for `normTitle()`, `films-extra.json` and `tmdb-aliases.json`. Audited by
      grepping every interpolation inside HTML-producing template literals.
- [x] **The background revalidate has to bypass the HTTP cache** (2026-08-30, sw.js v54).
      The refresh was a plain `fetch(e.request)`, answered from the browser's HTTP cache
      (`max-age=600`), so the stale copy renewed itself on every load. Seen live: Cinema
      Orion's posters missing while the origin had them. `fetch(new Request(req,
      {cache:'no-cache'}))` revalidates with the origin; a 304 is still cheap. A service
      worker cache sits in front of the HTTP cache, and both are consulted.
- [x] **Data JSON is served stale and revalidated behind** (2026-08-29, sw.js v48). For
      `data/*.json` only; the page stays network-first. On a repeat visit the network wait
      was the whole launch cost (1.3 s at 250 ms RTT), and the stale banner and health line
      key on `generated` inside the JSON, so a cached payload reports its own age. The SW
      posts `{fresh: path}` after a background refresh lands on a file it had served stale
      and the page re-derives on a real change. The original 60 s cooldown and the re-read
      through the SW went on 2026-09-05; see "Every cinema in a combined city can refresh
      it".
- [x] **The boot fetches speculatively from prefs** (2026-08-29). The three fetch waves
      (providers, venue lists, schedule) were serial, and every URL is knowable before the
      first byte arrives, so the boot starts all of them and `fetchJSON` consumes the
      in-flight promise. City views store their venue ids in prefs as `cityIds` for the
      prefetch only. Measured behind a 250 ms/request server: the schedule fetch starts at
      273-277 ms instead of 1057-1077 ms. Found while wiring it: `PROV_FALLBACK` had lagged
      the registry by one provider.
- [x] **Offscreen cards skip layout and paint** (2026-08-29). `content-visibility:auto`
      on `.movie`, with `contain-intrinsic-size: auto 173px` matching the real card
      height. render() still rebuilds the whole list through innerHTML -- the keyed-DOM
      rejection above stands -- but the browser now lays out and paints only the ~5 of 45
      cards in view. Ten rebuilds of a full Helsinki day on the same rig: median 51.4 ms
      before, 11.0 ms after, on a fast laptop; the ratio is what a slow phone gets.
      Posters also carry `decoding="async"` so image decode stays off the main thread
      during a rebuild. Verified: bottom card reachable, height estimate matches, scroll
      height stable, cold first visit unaffected.
- [x] **Startup fetches are concurrent** (2026-08-28). First paint waited on ~12 serial
      round trips: providers → genres → areas.json → eight venues files one at a time,
      each a full RTT on mobile. Now the venues files load with Promise.all (array order
      preserved, so picker order is stable), areas.json downloads while providers.json is
      applied, and tmdb-genres.json is off the critical path entirely — genresOf falls
      back to provider strings and ensureGenres invalidates every _hay when the map
      lands, so a search typed early still re-indexes. The one ordering rule, kept and
      commented in the boot sequence: loadProviders must finish before loadAreas, which
      iterates PROVIDERS — racing it against the hardcoded fallback could drop a newly
      registered provider's venues from the picker.
- [x] **"K-18" quick filter: measured and dropped** (2026-08-30). 120 of 3059 showtimes
      (3.9%), only 14 from the film's own rating, and 114 of the 120 are anniskelu
      screenings, so the chip would have been a rare subset of Anniskelu under another name.
      Shipped "Anniskelu" instead; K-18 is findable by typing.
- [x] **Punctuation and spacing do not count in search.** Both the query and the haystack
      are reduced to letters and digits only, with diacritics folded, so "spiderman",
      "spider man" and "spider-man" are one search and "katyrit" finds "Kätyrit". Nobody
      types a hyphen in the right place. The spaced form is kept alongside the collapsed
      one, so a two-word query still behaves normally.
- [x] The placeholder example is drawn from the day on screen — the film with the most
      showtimes, shortened at the colon, so "Spider-Man: Brand New Day" suggests
      "Spider-Man". Costs nothing, never goes stale, and beats a hardcoded title that ages
      out with one schedule. Falls back to a plain description when no film repeats.
- [x] Placeholder teaches by example — "Etsi esim. Dyyni tai komedia" / "Search e.g. Dune
      or comedy" — because a description of the capability ("nimellä tai lajilla") is both
      clumsy in Finnish and easier to skip than an example. The `aria-label` stays an
      explicit description; only the visible text is the example. Pick a franchise
      rather than a current release if it ever needs changing, so it does not age out with
      one schedule.
- [x] Search box matches genres as well as titles, in both languages at once, so
      "comedy" finds a film the Finnish UI calls Komedia. Matched through the same
      id -> name maps the cards render from, with the provider's genre string as fallback
      for films TMDB never matched. The per-show haystack is memoised and cleared when the
      genre maps arrive, or a search typed during that fetch would match titles only.
- [x] **Dropped 2026-09-01: genre / format filter chips.** The typed search already
      matches them -- `haystack()` folds in `genres`, `method` (2D, IMAX, Anniskelu),
      the rating and the age limit, plus the TMDB genre names in both Finnish and
      English. Chips would add a second way to reach the same set, on a mobile filter
      row that already carries five controls.
- [x] **Dropped 2026-09-01: sort toggle and a past-showtimes option.** Not because an
      equivalent exists -- "Ajat" is a screening-level list, one row per screening sorted
      by start time, so it is not the "Leffat" film list re-sorted by first showtime.
      It is dropped because it already covers time-first browsing, which is what the
      sort control was for. The past-showtimes half is answered too, differently in each
      view: "Leffat" collapses a film's earlier screenings behind a "Menneet näytökset"
      toggle *only while that film still has a later one*, so a film whose last screening
      has passed stays fully visible; "Ajat" keeps past rows in place, dimmed to 45% with
      `pointer-events:none`.
- [x] **Dropped 2026-09-01: tile / grid view.** The question this app answers is when and
      where a film plays. A poster-first tile either hides the showtimes or reprints the
      card that is already there, and the open questions recorded here never resolved
      because there was no version that did neither.
- [x] **Fulfilled 2026-09-01: multi-cinema merged view.** The combined city view is this,
      for the case that has evidence behind it: "Kaikki Helsinki (12)". Arbitrary
      cinema-picking is a different feature and wants a user asking for it first.
- [x] **Done: favourites float to top.** `venueRows()` pushes the starred venue, or a
      starred combined city, as the first row under its own heading before any city
      group, and `tests/test_venue_picker.py` asserts the order because Enter picks the
      first row.
- [x] **Merged 2026-09-01 into the Pipeline entry.** "Prices alkaen" and "Finnkino
      prices via the ticket-types endpoint" were the same endpoint from two sides and
      counted twice against the head.
- [x] **`alkaen` prices were parsed away, fixed 2026-09-01 (sw.js v95).** Found while
      checking the claim that the client half was already finished, which it was not:
      `priceLabel()` used parseFloat, so Cinema Orion's "alkaen 10€" was read as NaN and
      rendered nothing -- 23 of its 29 price-bearing showtimes. See the entry below.
- [x] **Landing-page redesign: `/teatteri/`, `/kaupunki/`, `/en/theatre/`, `/en/city/`.**
      Done 2026-09-02; see "[The landing pages belong to the
      product](#the-landing-pages-belong-to-the-product-2026-09-02)". The 168 canonical
      pages plus four legacy redirects are where a search for a named cinema or town lands.
      Two rules constrain them: `write_if_changed` needs deterministic output, and nothing
      volatile goes into a page; the drift step in `Checks` enforces both.
- [ ] **Landing pages: screening list across the full film width on narrow phones.**
      Recorded 2026-09-02, not built. At 320 px the showtime list stays inside the 206 px
      information column beside the poster even after the poster has ended, so a city
      stub such as `Finnkino Tennispalatsi · Sali 10 · englanti · tekstitys suomi/ruotsi`
      wraps to three lines while the 72 px poster column below the poster stays empty.
      A possible answer: below an evidence-based narrow breakpoint, place the list across
      the full film width after the synopsis. Structural, so it is its own change, and it
      has to be measured on representative films with and without a synopsis, since the
      list's starting height differs between the two. The two-level hierarchy this item
      first proposed -- cinema and room, then language -- arrived another way the same
      day: language now sits on the card when every screening shares it, and a city
      stub stacks time over cinema and room like the app's combined view, so what is
      left here is the full-width list itself.
- [ ] **Landing pages: the city cinema links read as a legend.** Recorded 2026-09-02, not
      built. The coloured cinema names under a city page's CTA are links to the theatre
      pages and look like a passive colour key. A possible answer is a restrained link
      affordance -- small padding, a clear hover and focus treatment, perhaps a short
      `Teatterit` / `Cinemas` label in front -- and not large primary-style buttons, which
      would compete with the one CTA on the page.
- [x] **The pressed favourite star reads at 4.5:1 (2026-09-02, sw.js v98).** The glyph was
      painted with `--accent`, 3.25:1 on `--surface` in light theme; the audit had left it
      because a text-rendered icon might count as a graphical object (3:1) rather than text
      (4.5:1). Painted with `--accent-text` (5.32:1) it clears both readings; dark theme is
      unchanged since the two tokens are the same colour there. Measured live before and
      after, both themes. `FavouriteStarTest` in `tests/test_theme_contrast.py` computes the
      ratio per theme; six mutations red. The other half of the item, 18 px title links, was
      dropped: they clear 2.5.8's spacing exception.
- [x] **Light-mode polish + accessibility pass.** Audited against the served page on
      2026-09-01 in both themes, fi/sv/en, at 320/375/720/1440 px. Most of the item was
      already done: focus order and rings, the dialog lifecycle on all three sheets,
      `aria-pressed` on toggles, `aria-current="date"` on day chips, localized names, a
      reduced-motion rule, no horizontal overflow. Four faults fixed:
      1. The selected day chip was unreadable in dark theme: `--ink` inverts with the theme,
         its `small` label on `--accent` did not (1.57:1). Now `--accent-on-ink`, 4.54:1.
      2. The light accent failed as small text: `--accent` #B8860B is chosen for a 3 px
         border (3:1) and measures 3.04:1 on `--bg`, and eight rules coloured text with it.
         They use `--accent-text` (#8A6508, 4.97:1); borders, rings and the wordmark stay.
      3. An empty result was painted and never announced. `#listStatus` is a pre-existing
         polite atomic region and every `main.innerHTML` site writes to it.
      4. The calendar's selected day had no state; the button says `aria-current="date"`.
      26 new guards break-verified, then checked live with transitions disabled: the 250 ms
      theme fade produced phantom failures when measured too early. What the harness cannot
      check: Enter, Space, Escape and arrow keys, since synthetic key events perform no
      default action; those stay verified by hand.
## Ops
- [x] Per-provider health line in the app (⚠ past 8 h, from each `venues-*.json` generated)
- [ ] Staleness monitor (external ping on data/areas.json age). The repo half is
      done -- `scripts/check_staleness.py`, see below. Still open because the
      thing that closes the gap is the ping, and it cannot live here.
- [x] The cloud workflow fails loudly if any provider exits non-zero, and now also if the
      push does not land (the retry loop used to swallow that)
- [x] The local half drives everything: it fetches Finnkino and Kino Akseli, pushes, then
      dispatches the cloud workflow. **GitHub cron did not fire for either workflow across
      four scheduled slots**, a known GitHub weakness rather than a config error; cron
      stays enabled as a bonus.
- [x] Verify the dispatch fires. It is the last step, after the push has already
      succeeded, so when it broke the run still looked healthy and only the seven cloud
      providers went stale. A cloud run should appear within a minute of each local run.
- [x] A provider parsing zero showtimes is now caught in the cloud: `run.py` writes no
      file, logs the venue by name, and exits non-zero, which fails the workflow. Before
      this, an empty parse silently left old data ageing.
      **That was only ever true for a whole site.** One venue of twelve parsing to
      nothing took the `keeping previous data` branch and was counted as neither live nor
      failed, and the provider file then stamped a fresh timestamp over all twelve.
      Fixed 2026-08-30; see "A provider is as fresh as its weakest venue" below.
- [x] The local half no longer only records it. `run-kinoakseli.log` still gets `exit=1`
      and the run still continues by design, so Finnkino keeps publishing -- but the
      commit is now the transport: `scripts/check_runs.py` reads every committed
      `run*.log` and fails on a non-zero or missing `exit=`, and `.github/workflows/
      logs.yml` runs it on any push that touches one. A local failure therefore turns a
      workflow red without the wrapper being edited. Left unchecked after that landed.
- [x] **Decided against 2026-09-01: a data branch.** See "Seven backlog items closed
      without building them": 195 of the last 30 days' commits are the pipeline's and `.git`
      is 49 MB, but nothing has broken, and every way off `main` is worse.
## Documentation state (2026-09-05, tenth pass)
Counts in README and IDEAS are re-measured against `data/`, the registry and `sitemap.xml`
on every provider change, because carried-over counts have been wrong repeatedly (city
count, poster count, page rewrite frequency, venue and provider counts, and once a count
stated twice in one file where only one copy moved).

Latest, 2026-09-05 after Kino Regina: 37 providers / 79 venues / 52 cities, 89 pages per
language, 179 sitemap URLs, 5 local providers (26 venues), 3900 poster references over 658
mirrored files, none off-origin. README's provider list, adapter table, page counts, poster
count and data-sources count moved with it.

Earlier passes: Tapiola (36 / 78 / 52), Korjaamo (35 / 77 / 52), Heureka (34 / 76 / 52),
Kino Metso 2026-09-01 (32 / 74 / 52, when the Nexxo correction reached the README's table
and not its prose), the Nexxo sweep 2026-08-31 (31 / 70 / 50, when the provider table was
regrouped by adapter and the Data sources section stopped carrying a second copy), and
Bio Rex Kokkola 2026-08-30 (25 / 64 / 45). Counts inside dated sections record what was
true on the day and are left alone.

`README.md` covers the product, the two-location pipeline, the data shape every provider
writes, adding a provider, and the contact and opt-out address. `IDEAS.md` holds
architecture decisions, per-provider API research and the backlog. `cf-worker/worker.js`
and the `TOKEN_WORKER_URL` branch in `get_token()` were deleted 2026-08-27. `run-*.log`
files in the repo root are committed per run by design.

## Cloud run diagnostics artifact (2026-09-06, temporary until 2026-09-09)
Problem: three of five cloud runs on 2026-09-05/06 failed against Nexxo and Regina hosts
(origin 403, timeouts, a SiteGround challenge on one window), each cleared by the next run.
Runner region did not explain it: `westus` appeared on both sides. The committed logs do not
record the runner's address, and Actions job logs need a sign-in, so nothing correlated
failures with addresses.

Decision: `scripts/ci_diag.py` runs in `biorex.yml` right after the provider loop. When a
`run-*.log` ends non-zero it probes the failing modules' hosts from the same runner and
records region (Azure IMDS), egress address, DNS answer, status, timing, a fixed header set
and body length. Uploaded with `actions/upload-artifact` (v7.0.1, SHA-pinned), two-day
retention, gated on the step's `report` output. Nothing is committed and no response body
or environment is recorded, for the same reason raw probe dumps are banned. The step
disarms itself after `--until`; remove it and this entry once the answer is in.

Same day, three review findings: both steps are `continue-on-error` with a three-minute
bound and the script exits 0 on its own errors, so diagnostics cannot skip the commit that
publishes the schedule; only the cloud modules' logs count, because the repo root also holds
the local half's committed logs and an old Engel failure started probes; hosts come from
`run.sites_for(mod, "cloud")`, which leaves out etiketti's two local-only sites; the
`HTTPError` response is closed, since CI fails on a `ResourceWarning`.

Validation: `tests/test_ci_diag.py`, 14 tests against a local server, 21 of 21 mutations red.

## Notes / gotchas
- Read the committed `run.log`, not Actions logs.
- A break-and-restore test pass can report the state before the restore. Writing the file
  again with the same byte count inside the same mtime second makes Python reuse the
  `__pycache__` bytecode compiled from the broken source. Clear `__pycache__` between the
  break and the restore, and re-read the final green on a cleared cache.
- `raw.githubusercontent.com` served a two-commit-stale `index.html` minutes after a push,
  and using it as the base for the next edit reverted the previous fix. Read repo files
  through the Contents API with `Accept: application/vnd.github.raw`.
- Splitting the removal of one block across two edits leaves everything between them
  behind; that produced valid syntax referencing a deleted variable and the app died at
  runtime. Delete a block as one contiguous match.
- Anything the language toggle can reach must be redrawn by `applyLang()`.
- Actions run 32985593686 (2026-08-26) failed with "The job was not acquired by Runner":
  GitHub-side runner allocation, nothing to fix.
- Triggering `workflow_dispatch` via the API needs the token's Actions permission; the
  Workflows permission covers editing workflow files only.
- Probing endpoints the sandbox cannot reach: push a throwaway workflow that curls and
  commits the response, read it, delete both. Does not work for sites that block datacenter
  IPs.
- BeautifulSoup re-serialises attributes with single quotes; never write regexes against
  bs4's rendering of a page.
- `workflow_dispatch` runs the workflow file at the ref, but a run already queued uses the
  older file. Check `head_sha` when a change seems not to apply.
- Two writers on one branch (local + Actions), so both push paths need the pull-rebase
  retry.
- The cloud workflow is cron + dispatch only. It used to trigger on pushes to
  `scripts/providers/**`, so an adapter commit spawned a run that raced a manual dispatch.
- A retry loop whose last command is `sleep` exits 0 even when every attempt failed. Set an
  explicit flag and `exit 1`.
- Small hosts rate-limit: Kinoset answered 403 after repeated hits in one hour.
- Every frontend bug on the day multi-provider landed came from a field only Finnkino
  populated: `soldOut`, `s.fi`, and a hash regex `m=([\w-]+)` that truncated ids with
  spaces. Check field-presence assumptions in the client as well as the parser.
- `location.hash = ''` counts as navigating to the top of the document and scrolled the
  list up when the sheet closed. Use `history.replaceState`.
- A helper that raises before the file write, followed by a push, commits the file
  unchanged. Write the file before pushing and check the edit count.
- The Contents API commits one path per call; for a multi-file commit use the Git trees
  API (`git/trees` with `base_tree`, `git/commits`, `PATCH git/refs/heads/main`).
- Pushing through the API means the local clone learns nothing until it pulls. To identify
  the clone that publishes, read the author of the commits touching its data.
- The local wrapper's shell mechanics are in private notes. One general lesson: a final step
  that runs after the push can fail without making the run look failed, so anything that
  matters needs its own check.
- An unmapped language code renders as itself (2026-08-29): `LN` held five languages and
  the data carried twelve, so 133 Spanish showtimes said "ES". A real language code missing
  from `LN` is a client gap; a code that is not a language (SE for Sweden) is an adapter
  bug. `LN` carries every code in the data plus everything the adapters' name maps can emit.
- The Swedish tag is `SV`, migrated from `SE` on 2026-08-29 (SV is the ISO 639-1 language
  code, SE the country). Done in three commits: the client learned both codes, then the
  six adapters that publish Swedish, then `fetch_data.py`; the temporary alias came out
  once no area file carried `SE-`. The shape of a data-format migration with no build step
  and two writers: teach the reader both, change the writers, remove the old spelling once
  the data has turned over, gated on a measurement.
- BioRex published `SV` where the client's map keyed on `SE`, so 644 showtimes said
  "tekstit SV". Normalised at the source; the tag set is Finnkino's, and a provider's own
  spelling is not evidence of anything.
- Adapters carry a referer, three retries with backoff, and a pause between venues.
- The film-list sort (`localeCompare` per comparison) measured identical to a cached
  `Intl.Collator`, about 0.01 ms per 45-title sort. Not worth touching.

## Crawlers and search
- State as of 2026-08-29: pages generated and committed, sitemap submitted, Rich Results
  Test clean on a city page (371 valid, 0 invalid). Remaining warnings are optional fields
  (`priceRange`, `telephone`, `image` on MovieTheater; `director`, `dateCreated` on
  Movie), not chased.
- `<head>` carries a description, canonical, OpenGraph and Twitter tags; `robots.txt` and a
  generated `sitemap.xml` exist (2026-08-28).
- Pre-rendered pages, built 2026-08-28: markup does not create pages and the app is one
  JS-rendered URL, so `scripts/build_pages.py` renders one page per venue and per
  multi-venue city from the committed JSON at the end of every run.
- City pages only where a city has more than one venue, the app's own rule. A one-venue
  city's page would be the venue page at a second URL competing with it.
- Page weight had to be designed: the first render was 13.6 MB across 102 pages with a
  1.2 MB Helsinki page. A four-day window (two for cities), structured data for today and
  tomorrow with theatres as `@id` nodes, and a synopsis printed once per film brought it to
  4.0 MB raw / 388 kB gzipped.
- Nothing volatile in a page, so `write_if_changed` holds: no build timestamp, no
  `availability`. A second consecutive run writes zero files. The test counts only stamps
  with a time component (2026-09-02): `films-extra.json` writes `generated` as a bare date,
  and every page with a screening that day carries the same date in a JSON-LD `startDate`.
- Finnish city names are never inflected by the generator: Helsinki -> Helsingissä and
  Tampere -> Tampereella change the stem and take different cases. Every string uses the
  nominative with a separator.
- Google validates a nested `Movie` against its own rules: without `image` every one came
  back invalid. A showtime with no poster from any source drops `workPresented`.
- A poster URL in JSON-LD is not a privacy leak: the crawler fetches it, the reader's
  browser never does.
- Google reported no Event rich result for `ScreeningEvent`; the plain HTML showtimes carry
  the page.
- Open: the committed pages grow the repo by roughly the gzipped delta per day (~390 kB
  worst case). A Pages artifact deploy would remove that, at the cost of switching Pages
  from branch to Actions. Not attempted.
- `?area=` deep link (2026-08-29): every generated page links to `/?area={venueId}` or
  `/?area=city:{City}`, validated like a stored preference. The parameter was first stripped
  from the URL on arrival; since 2026-09-01 it stays while it is the answer (see "A deep
  link opened the right cinema once, then lost it").
- No venue or city count in the meta description: a third copy of a number that goes stale.
- `og:image` is `icon-512.png`. A 1200x630 card would preview better; not done.
- Not doing: hidden text or markup that differs from what a visitor sees. Cloaking is spam
  by every engine's definition, and `<noscript>` has the same constraint.
- Making thousands of showtime pages indexable would turn a personal app into a directory
  competing with the cinemas' own listings. A deliberate decision, not a side effect of
  markup. See "Access and ethics".

### Secondary page fetches have a ceiling (2026-08-30)
Adapters that read a listing and then fetch one page per film iterated whatever the listing
contained, 15 to 31 films today and unbounded in principle. `common.PAGE_BUDGET` is 120,
about four times the largest real figure, overridable with `KINO_PAGE_BUDGET`.

The two loops are not the same loop, which tripping the cap showed: with the budget forced
to 2, eTiketti went to zero showtimes at Kinopalatsi Kotka and 6 of 34 at Trio 123, and
would have published both, because its film pages carry the screenings, while BioRex and
Engel use film pages only for metadata. `common.capped()` trims and logs, for enrichment
loops; `common.budget_or_raise()` raises, for a loop whose pages are the schedule, so
`run.py` writes no file and the previous data stands. A venue publishing half its day is
worse than one publishing nothing, because half a day looks complete.

### Response bodies have a ceiling too (2026-08-31)
The request count was bounded while each response was read with a bare `r.read()`. Found
by an external review. `common.fetch` reads in 64 KB chunks against a cap (`max_bytes` per
call, `MAX_BODY` 20 MB by default, `KINO_MAX_BODY`) and raises `BodyTooLarge` past it.

- 20 MB is headroom; the largest body legitimately read is a poster source image of a few
  MB.
- A Content-Length past the cap is refused before the body is read, and the chunked loop
  enforces the cap whether or not a header was sent.
- Never retried: the oversize answer is deterministic.
- One cap in `fetch` covers adapters, enrichment and `mirror_posters.download()`; an
  oversize poster lands in the `failed` dict like any other bad download.

Covered in `tests/test_common_fetch.py` against the real local server, including a response
with no Content-Length; each guard break-verified.

### The pipeline identifies itself (2026-08-30)
Every adapter sent `Mozilla/5.0 ... Chrome/126.0.0.0`, an automated reader claiming to be a
person, which made the ethics section's claim untestable by a cinema. Now `Leffavuoro/1.0
(+https://leffavuoro.fi)` everywhere, including `fetch_data.py` and the TMDB pass.

Probed first against every provider: each answers the honest string byte-for-byte
identically to the Chrome string; Finnkino answers 403 to curl under either. Engel's film
page differed between the two agents and also between two requests with the same agent (a
cache-buster in a script URL): a difference is not evidence of discrimination until the same
request twice is ruled out. If a provider ever refuses the honest string, record it here and
keep the browser string for that host deliberately. The URL in the string is where a cinema
that wants out is supposed to look; the contact route closed that on 2026-08-30.

### Conditional GETs, and what the providers actually support (2026-08-30)
`common.fetch(cache=True)` sends a stored `ETag` / `Last-Modified` back as `If-None-Match`
/ `If-Modified-Since`, and a 304 returns the stored body. Verified live against Cinema
Orion: the second fetch was a 304 and 118 kB was not resent.

Measured before building it: only Cinema Orion sends a validator.

| origin | ETag | Last-Modified | Cache-Control |
|---|---|---|---|
| cinemaorion.fi | no | **yes** | – |
| kotkanleffat.fi (eTiketti) | no | no | `no-store, no-cache, must-revalidate` |
| kinoset.fi (Nexxo) | no | no | `no-store, no-cache, must-revalidate, max-age=0` |
| biorex.org, kinoengel.fi, gilda.fi, rivieracinemas.fi | no | no | – |
| savonkinot.fi (Vista) | no | no | `private` |

So this saves about one request per run. It stays because it is the correct way to ask,
costs nothing where the origin offers nothing, and picks up a provider that starts sending
validators. `run.py` prints the shape of every run so the claim can be checked:

    [run] http: 1 revalidated (304), 85 full, 48 not stored (origin said no-store),
          0 cache entries written

Rules: a response marked `no-store` or `no-cache` is never written to disk, and neither is
one without a validator. The cache lives in `.http-cache/`, gitignored, never committed
(it holds verbatim third-party pages, the `probe/` rule). The workflow restores it with
`actions/cache`. Never enabled on a POST: `fetch` forces `cache=False` when `data` is
given, since a POST response is not addressed by its URL alone.

### Retry-After is honoured on the interval the upstream names (2026-08-30)
`common.fetch` retried every HTTP error on the same fixed `backoff * n`, so a provider
answering `429 Retry-After: 60` got three more requests inside 15 seconds. A 429 or 503
carrying `Retry-After` is now retried on the interval named. A 500, a reset, a 429 without
the header and a 403 keep the fixed backoff.

Two ceilings, because "sleep as long as you are told" hands a stranger a lever on the
pipeline: `RETRY_AFTER_MAX` (120 s) bounds one wait and `RETRY_AFTER_BUDGET` (300 s) the
whole process. Past either, the request fails, `run.py` keeps the previous file and the
health line ages. Both overridable (`KINO_RETRY_AFTER_MAX`, `KINO_RETRY_AFTER_BUDGET`) so
tests can trip them. `Retry-After` is delta-seconds or an HTTP-date; a past date means
now; an unparseable value falls back to the fixed backoff.

    [run] throttled: 2 Retry-After responses, 60s waited, 1 not retried
          (asked for longer than a run can wait)

Printed only when it fires. Tested against a local server scripted to 429: the stated wait
is honoured, a `Retry-After: 9999` costs one request and no sleep, the budget refuses the
second of two 2-second asks under a 3-second budget, an HTTP-date is parsed, a past date
waits zero, a plain 500 still takes three tries.

Not covered: `enrich_tmdb.py` uses a bare `urlopen` with no retry, so a TMDB 429 skips
that title. Routing it through `common.fetch` is a separate change.

### A refusal has to say which layer refused (2026-08-30)
Cloud run #110 went red on `nexxo`: all three Kinoset venues answered 403. Nothing was lost
(previous files kept, venues published `stale`, commit before the gate, the next run 43
minutes later served everything), but the log said `HTTP Error 403: Forbidden` three times
and nothing else. An edge block and an origin throttle want opposite responses (move the
endpoint to the local half, or wait), and the block was gone before anyone read the log.

`common.fetch` prints one line for a request it gives up on:

    [http] 403 from kinoset.fi, gave up after 3 attempt(s) -- Server: LiteSpeed

- Three headers, never the body: `Server`, `CF-Ray`, `Retry-After`. The log is committed
  to a public repo and a third party's error page carries whatever they ship; one raw dump
  already put someone else's API key in here. `X-Powered-By` was dropped for that reason.
- Measured live: `kinoset.fi` answers `Server: LiteSpeed` with no `CF-Ray`, so a Kinoset
  403 is the origin refusing. `Server: cloudflare` would be a different event.
- One line per host per process, not per request: `mirror_posters` has had 185 failures
  against one host in a run. The ray id is unique per request, so its presence identifies
  the layer and the line carries the first value seen.

Rejected: deferring a failed venue to a second pass (an interface change across eleven
adapters, against a block that took under 43 minutes to clear); and not failing the
workflow when every venue kept usable data (a permanently dead provider would publish
green runs while the data aged). Six mutations red, including logging on success or once
per attempt.

### The site answers the User-Agent (2026-08-30)
`Leffavuoro/1.0 (+https://leffavuoro.fi)` points every provider at this site, and the site
said nothing about who was reading them or how to ask to be left out.

`leffavuoro@gmail.com` appears in three places: the app footer (translated, redrawn by
`applyLang()`), every generated venue and city page, and a `## Contact` section in the
README. Plain text: every obfuscation that survives a headless-browser scraper also
defeats a screen reader, copy-paste and tap-to-mail, and the address is a disposable alias.

Rotation has to be one reliable act. The address is hand-written in four files (twice in
`index.html`, since the markup keeps a literal) and stamped onto every generated page.
`tests/test_contact_address.py` discovers it from the client's `CONTACT` constant and
compares everything else against it, and refuses any other address in a tracked file.

`renderContact()` is separate from `renderStatus()`, which returns early until schedule
data has loaded; it runs once at boot and from `applyLang()`. Constant, so
`write_if_changed` converges after one rewrite of the pages.

### The accent numbers, re-derived (2026-08-30)
The recorded ΔE figures could not be reproduced. Re-derived with `scripts/accent_check.py`
(sRGB -> linear via IEC 61966-2-1; deuteranope simulation on linear RGB by
Viénot–Brettel–Mollon 1999 and Machado–Oliveira–Fernandes 2009 at severity 1.0; XYZ ->
CIELAB D65; CIEDE2000; `--selftest` against 15 pairs of Sharma, Wu & Dalal's reference
data), the result: the old figures were CIE76 labelled ΔE, and one same-city pair was a
single colour to a deuteranope.

CIE76 reproduces three recorded normal-vision numbers to the decimal:

| recorded as | pair | CIE76 | CIEDE2000 |
|---|---|---|---|
| 25.9 | old Finnkino / old Gilda | **25.9** | 15.3 |
| 46.9 | BioRex / Riviera, normal | **46.9** | 23.3 |
| 36.9 | Engel / BioRex, normal | **36.9** | 18.5 |

The recorded deuteranope figures (34.5, 28.0, 37.3, 5.0) match no model at any severity
and are not quoted again. Corrected, with the harsher model:

| claim | recorded | measured |
|---|---|---|
| worst same-city pair, normal | 46.9 | 18.5 (Engel/Gilda) |
| worst same-city pair, deutan | 28.0 | **3.9 (BioRex/Riviera)** |
| old Finnkino / old BioRex, deutan | 5.0 | 1.8 |
| global minimum, any pair, deutan | 32.1 | 0.7 (Finnkino/Kino Akseli) |

Four of 45 cities had more than one chain on 2026-08-30 (Helsinki with six, Vantaa, Lahti,
Kouvola); Kotka has one chain, so the old "Kotka only ever shows two chains" claim is
retired. Superseded 2026-09-01: Kino Metso made Jyväskylä a third chain city, 5 of 52;
its worst pair is 26.9 ΔE00 deutan and the set's worst stays Helsinki's 14.4.

Decisions:
- Riviera moved from `#7B3FD4` to `#0C6464`: blue and violet differ mostly in the red-green
  channel a deuteranope lacks, so BioRex and Riviera sat 3.9 apart in the one city where
  they meet. Riviera rather than BioRex because Riviera's two venues are both in Helsinki
  while BioRex is unconstrained in twelve towns. The tiebreak among candidates clearing
  14.4 was normal vision: `#0C6464` scores 16.5 deutan / 28.1 normal against `#24664E` at
  19.1 / 18.8. Only six hue families clear the ceiling, all at L* 38-39.
- Kino Akseli's gold at 0.7 from Finnkino's orange stays: Nummela has one chain.
- "About the ceiling for six chains" was wrong. Five of the six Helsinki colours are free,
  and a greedy max-min search over the same L* band reaches 19.5 deutan / 21.0 normal.
  Not applied: it moves five learned accents and the current floor hurts nobody.
- `--city` took a list and used only the first entry, so a candidate could be cleared in
  Helsinki while colliding in Tampere. Fixed to measure every city; a bare string is
  wrapped rather than iterated.

### Six days out of seven is not a Finnkino schedule (2026-09-01)
`fetch_data.py` asks OCAPI for seven business dates, one request each. A request that
raised was logged and skipped, and the remaining days were written as a new snapshot with a
current timestamp and exit 0. `dates` is built from the shows that arrived, and the client
reads a date's absence as "not published yet", so one transient error took a whole day out
of all seventeen Finnkino venues with nothing to surface it. Reproduced with OCAPI stubbed
and day three raising.

Decision: all seven or none. On a failure the previous file stands, its age moves past
eight hours, and the non-zero exit turns `check_runs.py` red; a published six-day week
moves nothing a reader can see. The last day of the horizon is refused on the same terms.
`areas.json` moved down with the schedule files, since a run that published nothing still
stamped the one file whose age answers "when did Finnkino last refresh". Poster downloads
and the token fetch have already happened by then and are not rolled back.

Not retried before giving up: `api()` has no retry, unlike `common.fetch`. A separate
change.

Thirteen tests drive the real `main()` with OCAPI stubbed by URL. Break-verified six ways:
the guard removed (9 red), logging without returning (8), returning 0 after refusing (6),
aborting only when all seven fail (8), tolerating the last day (1), `areas.json` above the
loop (3).

### A provider is as fresh as its weakest venue (2026-08-30)
One venue of twelve parsing to nothing kept its previous file, and `venues-{provider}.json`
then stamped `generated: now` across all twelve, so the app said BioRex was an hour old
while one cinema sat on week-old showtimes.

`venues-{provider}.json` gains three additive fields: `oldest`, the minimum `generated`
across the provider's venue files, read off disk after the run and what the health line
ages on; `status`, `ok` or `partial`; `stale`, the venue ids whose previous file was kept.
`generated` keeps its meaning.

Stale, not failed: at this layer a broken parser and a cinema with nothing on today both
arrive as `[]`, so failing on a venue-level empty would fire on every Monday closure.
`[run] partial:` names the venues in the log and the status carries them to the client,
which shows `⚠ Riviera 119h (1/2)` rather than blaming the whole chain. A site where every
venue came back empty still fails.

Fixed the same day: age alone still hid a partial refresh. `healthState(m, ageH)` returns
`gone | behind | partial | ok` in severity order; `partial` is separate from `behind`
because two-hour-old data is not behind, and calling it that is the false alarm that
teaches people to ignore the line. Fourteen harness cases; reverting to age-only turns
four red. One term was unpinned at first (`m.unverified > 0` could be deleted with
everything green), found by deleting it.

Added the same pass: a venue that has never produced a showtime is `unverified`, not
`stale`. A new venue with no shows and no file fell through every branch and published
`status: "ok"`; on the next run its empty file existed, so it went down the stale branch
and its ageing `generated` dragged `oldest` down. The discriminator is whether the previous
file contains shows. An unverified venue's empty file is rewritten with a fresh
`generated`, `status` is `partial` while either list is non-empty, and it clears itself
when the venue starts producing. Not a failure: a venue added before its programme and a
parse that never worked look the same here.

Covered by `tests/test_run_partial.py` with three venues and the stale one in the middle;
two venues would let "the last venue's state" pass.

### A dead provider stays on the health line (2026-08-30)
`providerMeta` was built only from what loaded: `fetchJSON(...).catch(() => null)` then
`if(!j) return`. So a provider whose venue file failed entirely disappeared from the
health line *and* from the picker, and the app looked exactly as it does when that chain
was never configured. The one state the line most needs to show was the only one it could
not: total failure rendered as absence.

Now seeded from `PROVIDERS` before any fetch, so every expected provider has a row from
the start and a successful load overwrites it. A provider that never arrives reads
`⚠ Riviera ei saatavilla`.

- Distinct from the existing `?`, which means a file *did* arrive carrying a timestamp
  that could not be read. Two different faults, two different words.
- No `loading` state. The boot already shows a spinner over the whole list, and a row
  that says "loading" for 300 ms is noise rather than information.
- Verified by removing `data/venues-riviera.json` and reloading with the service worker
  unregistered and its caches cleared -- the SW serves data cache-first, so without that
  the test would have been answered from the last good copy and proved nothing. Eleven
  rows instead of ten, Riviera named in all three languages.

### A combined city says how many cinemas it is actually showing (2026-08-30)
`loadCity` fetched each venue with `catch(_) => null` and then skipped the nulls. A city
could therefore render a confident, complete-looking programme with a whole cinema
missing, and nothing else would have caught it: the health line is per *provider*, and
the provider whose venue failed to load may be perfectly fresh everywhere else.

The expected id list stays the source of truth. `loadCity` returns `missing` (venue
names, not ids, since the reader has to recognise them) and `expected`, and a notice
above the list reads `Näytetään 11/12 teatteria. Ei saatu ladattua: Kallio.`

- **Painted before the `generated` guard in `renderStatus`, not after.** A city where
  *every* part fails has no timestamp at all, so the guard would have skipped exactly the
  worst case. Tested by deleting both Kotka venue files: the notice reads `0/2` above the
  list, where without it the page says "Ei enää näytöksiä tänään" -- a total load failure
  rendering as an ordinary quiet evening.
- Its own element rather than reusing `#stale`. They are different claims -- "this is
  old" and "this is incomplete" -- and both can be true at once, so one box cannot say
  both. Neutral border rather than the amber one, since a missing venue is not
  necessarily a stale one.
- **The first attempt at testing this proved nothing.** Deleting the file and reloading
  still showed no notice, because the browser's own HTTP cache answered the request with
  the copy it already had -- the service worker was unregistered, which is not the same
  thing. Re-served on a fresh port so no cached entry applied. As with the SWR bug, a
  service worker cache sits in front of the HTTP cache; clearing one leaves the other
  populated.

### The service worker stopped caching failures (2026-08-30)
Two of the three fetch branches called `cache.put` on whatever came back. The data-JSON
branch already checked `r.ok`; the poster and generic branches did not.

**The poster one is the damaging one, because that branch is cache-first.** A cached 404
is not a stale entry that expires -- it is a tile that stays broken for the life of the
cache version, since the request never reaches the network again to find out it was
fixed. A deploy race or a poster pruned upstream was enough. The generic branch holds
`index.html`, and its cached copy is what the offline fallback serves, so a cached 500
would be served to a reader who is merely offline.

**Tested against the real `sw.js`, not a copy of its logic.** The harness browser blocks
service-worker registration outright -- `navigator.serviceWorker.register` fails with
"an unknown error occurred when fetching the script" on any port, and
`getRegistrations()` has been empty all along -- so `tests/sw_fetch_harness.js` loads the
actual file into a `vm` context with stubbed `caches`/`fetch`, drives its registered
fetch listener, and records which URLs the code chose to store. Stubbing is the right
instrument here: the thing under test is a decision this file makes, not behaviour the
Cache API contributes. `tests/test_sw_cache.py` runs it and skips when node is absent.

Nine cases: 404 and 500 on each branch, 200 on each branch, plus cross-origin and
non-GET, which must not be intercepted at all rather than merely not cached. Verified by
restoring the unconditional `put` -- three tests go red.

### A cache write must outlive the response (2026-08-31)
The poster and generic branches in sw.js wrote `cache.put` fire-and-forget. Once no
extend-lifetime promise remains the browser may terminate the worker, and the write that
loses that race is the one the offline fallback needed. Found by an external review. Both
branches now pass the `caches.open().then(put)` chain to `e.waitUntil`, as the data-JSON
branch already did.

The harness could not catch this until it modelled termination: `put` now settles on a
macrotask and `stored` is read only after the response and every `waitUntil` promise have
settled. Restoring the fire-and-forget form turns `poster_200` and `page_200` red. No CACHE
bump: the byte diff alone updates the worker and nothing cached went stale.

A review claimed `e.waitUntil` inside `fetch().then()` throws `InvalidStateError`, citing
MDN's "must be initially called within the event callback". The spec's rule is narrower: it
throws only when the event is not active, and an event is active while its dispatch flag
is set or its pending promises count is above zero; `respondWith(r)` adds `r` to those
promises. Confirmed against production Chrome on the live site. The review was right that
the harness stub accepted `waitUntil` at any time; it now models the activity rule and a
`waitUntil` deferred behind `setTimeout` goes red.

### The footer credits only the source on screen (2026-08-30)
The footer carried a per-source age for all eleven providers, a credit line naming the
chain twice, and the contact line. Now one `<footer>` with three short lines and the
per-source list behind a native `<details>`.

- The summary states the answer and names what is wrong: `⚠ Lähteitä jäljessä: Riviera,
  Gilda`, truncated past three.
- Native `<details>`: keyboard operable and announced correctly with no code.
- The glyph key stays visible, since it explains symbols on screen right now.
- The credit line dropped one of its two chain names; the book-mode phrase already ends
  in the host.

Measured at 375 px: 110 px closed against 166 px open. Rejected: a separate freshness page.
Generated pages cannot carry anything volatile, and a client-rendered route is a router
for something that fits on one line.

For future layout work: the harness browser reports `innerWidth: 0` until `resize_window`
is called, and every measurement before that is wrong.

### The app is operable from a keyboard (2026-08-30)
Four faults fixed as one pass.

- Movie details could not be opened without a mouse: the trigger was a bare `<article>`
  with a delegated click handler. The title is now a real `<a>`, since opening the sheet
  is hash navigation; the times view's `.tinfo` became an anchor the same way, and the
  card-wide click defers to the link so both paths run the same code.
- The sheet claimed `role="dialog" aria-modal="true"` at all times while hidden by a
  transform. `inert` now toggles on the sheet when closed and on the background roots
  when open (zero focusable elements remain outside it); `inert` rather than `hidden`
  because the sheet animates. Escape closes; focus moves to the close button on open and
  back to the trigger on close, guarded by `document.contains`.
- `role="tablist"` with no tab pattern behind it. Days take `aria-current="date"`, the
  segment and filter chips `aria-pressed`, the calendar chip `aria-haspopup="dialog"`
  with `aria-expanded`.
- Accessible names were hard-coded in two languages. `applyAriaLabels()` runs from
  `applyLang()`.

### A venue with no programme yet is not a failed refresh (2026-08-31)
Kino Metso Tikkakoski publishes into late October from day one, so it sat in the 21-day
window with zero showtimes for a month, and the health line read "⚠ Osa teattereista ei
päivittynyt: Kino Metso": the fetch was fresh, and a month-long warning teaches readers to
ignore the line.

`healthState` gained `pending` below `partial`: a quiet "Ei vielä ohjelmistoa: {venue}"
with no warning mark, named by venue since "Kino Metso" reads as the whole chain.

The first version quieted every `unverified` venue; a review caught that as overreach,
since run.py cannot tell "added before its programme" from "a parse that has never
worked". `pending` is granted only where the adapter has positive evidence: a module that
sets `EMPTY_VENUES_CONFIRMED` (nexxo, whose schema check means a venue with zero rows was
answered and listed empty) vouches for the venues it reported empty. eTiketti must not set
the flag: its venue match is a substring test over markup. Severity: stale and unverified
outrank pending, age outranks all three. The provider row's tooltip names each kind ("ei
päivittynyt", "ei ole vielä saatu näytöksiä", "ei vielä ohjelmistoa").

A second review tightened the evidence: nexxo's `parse()` silently skipped rows whose
start could not be read, so a renamed field would have emptied every row and read as
pending. It now raises when relevant rows exist and none produced a showtime; an empty
payload, a room filter owning no rows, and `isUpcoming` rows stay legitimate empties, and
one malformed row among parseable ones is still dropped. The runner's summary counts
pending with its own `[run] pending:` line. Nine guards, nine reds when broken.

### The installed iOS app stops smearing the status bar (2026-08-31)
Installed to an iPhone home screen, the top of the page showed a blurred smear behind the
clock. Three causes, shipped as v84–v86 and verified on an iPhone 17 Pro simulator with the
site installed from Safari:

- Nothing painted the status-bar strip. A `position:fixed` strip the height of
  `env(safe-area-inset-top)` now paints `--bg` behind the bar; sticky cannot do it, since
  the pinned row leaves the viewport under scroll.
- The insets were dead until `apple-mobile-web-app-status-bar-style: black-translucent`
  opted in. The meta is read at install time, so an installed icon has to be re-added.
- `theme-color` was hardcoded dark, and iOS derives the clock's colour from it.
  `applyTheme()` writes the current `--bg` into the meta on every toggle.

One device resists: an iPhone 15 Pro Max on iOS 27 smears at launch even from a fresh
install, while an iPhone 17 and the 26.5 simulator launch clean. Two page-side workarounds
(a one-frame `translateZ(0)` in v87, a sheet-grade inert flip 700 ms after load in v88)
were removed the same day when the device disproved them; a real sheet open still clears
it. Parked as an iOS 27 compositor bug. Do not add a third guess without a way to
instrument the phone. Same pass: the venue list's 6px top padding slit is gone, and the
full-screen venue sheet pads past the inset so its search row clears the Dynamic Island.

### The month picker gets the sheet's modal lifecycle (2026-08-31)
The keyboard pass gave the movie sheet real modality and left the month picker claiming
it: `role="dialog" aria-modal="true"` in the markup with focus staying on the chip, the
background tabbable and no focus return. Found by an external review.

It now runs the sheet's lifecycle: `BEHIND()` roots inert on open, Escape and the backdrop
close it, focus lands on the selected day (falling back to any day, then an arrow) and
returns to the calendar chip. Month navigation redraws the grid through `innerHTML`, so the
redraw refocuses the same-direction arrow, falling back to the other, then a day. The
dialog is labelled by its month heading (`aria-labelledby="calTitle"`).

No unit test: the lifecycle is DOM-and-focus behaviour, and a source-grep test would pin
the implementation. Verified live: open, initial focus, both inert states, Escape,
backdrop, month-nav focus survival, date-picked focus return, clean console.

### "Huomenna" was ellipsised on a 402px phone (2026-09-01, sw.js v94)
Six chips at `flex:1 1 0`, each a sixth of the row; the label steps from .6rem to .66rem
above a breakpoint at 400px. A .66rem "Huomenna" needs 53.43px and a sixth of a 402px row
(iPhone 17) offers 53.00. The breakpoint was two pixels early: `(vw - 28 - 30) / 6 - 4 >=
53.43` needs vw >= 403.

| viewport | label size | column | "Huomenna" | |
|---|---|---|---|---|
| 320 | 9.6px | 40.00 | 48.57 | over by 8.57 |
| 375 | 9.6px | 49.00 | 48.57 | fits by 0.43 |
| 393 | 9.6px | 52.00 | 48.57 | fits |
| 402 | 10.56px | 53.00 | 53.43 | **over by 0.43** |
| 430 | 10.56px | 58.00 | 53.43 | fits |

Three changes: the breakpoint moves 400 -> 410; `.day` gets `min-width:max-content` so the
one chip that needs more takes it (spread 0px from 375px up, 10.7px at 320px); the gap
drops 6px -> 5px below 410, because at 375px the margin was 0.26px. `min-height:44px` on
the chip fixes a pre-existing 42.5px tap target; padding was the wrong instrument since the
shortfall differs per band. Verified at 320, 375, 393, 402 and 430 in all three languages
and both themes, and at 402 on an iPhone 17 simulator (132 device pixels at 3x). Finnish
is the binding case: "Huomenna" is 5.06 em-widths against "Tomorrow" 4.67 and "I morgon"
4.08.

`tests/test_day_chip_fit.py` reads padding, gap, font sizes and breakpoints out of
`index.html` and recomputes the column against glyph widths measured once, demanding a 1px
margin; that requirement surfaced the 375px case. The CSS parser took four attempts, each
failure a test that passed while checking nothing: comments read as part of a selector, an
anchored regex skipping every second rule, `index()` finding the first of two identical
media openers, and a unit regex reading `padding:0 14px 8px` as 8px. Seven mutations red.

### A deep link opened the right cinema once, then lost it (2026-09-01, sw.js v96)
Reproduced: star Finnkino Cine Atlas, follow a generated Tapio page's `/?area=sk-tapio`
link, reload. Cine Atlas opens. `?area=` was applied and deleted from the URL in the same
step, so the next load fell through to the stored restore, where the favourite beats the
stored area.

Decision: keep the parameter while it is the answer, rewrite it when the reader picks
something else (`selectVenue` updates an `area` parameter that is already present, and
only then), strip a parameter that decided nothing. Arriving through a link writes `area`,
the last-browsed slot, never `fav`. Both writes are `replaceState`, so back and forward
leave the page.

Measured on the served page with Cine Atlas starred: `/?area=sk-tapio` keeps the parameter
across reloads and shows Tapio; picking Maxim rewrites it to `sk-maxim`;
`/?area=city:Helsinki` is kept; `/?area=sk-gone-forever` is stripped and Cine Atlas opens;
`/?area=sk-tapio&lang=en` keeps both. The favourite stayed 1094 in every case.

`startupArea()` and `areaParamAfterSelect()` are extracted verbatim by
`tests/area_routing_harness.js`, 18 tests. Break-verified seven ways: `keepParam` false for
a deep link (2 red), the favourite checked before the link (5), the link written into `fav`
(1), a stale link left in the URL (1), selection not rewriting the parameter (5), selection
always writing one (1), the stored area checked before the favourite (4).

### The deep link carries the language too (2026-09-02, sw.js v97)
The generated pages exist in Finnish and English and linked to `/?area=...`, while the app
read its language from `kino-prefs` alone and defaulted to Finnish, so an English page
opened a Finnish app for a reader with nothing stored. Fixed ahead of the landing-page
redesign, so the pages could link to `&lang=fi` and `&lang=en`.

`startupLang(param, stored, LANGS)` sits in the same marker block as `startupArea` and
follows the same rules: a supported value in the URL wins on arrival (exact match, so `EN`
and `xx` decide nothing); it stays in the URL while it is the answer; it seeds `prefs.lang`
only when nothing valid is stored, and never writes `fav` or `area`; the toggle rewrites a
`lang` already present, and only then; an unsupported value is stripped with
`replaceState`. Read before any render, so every `L[state.lang]` lookup and the English
`films.json` fetch see the same value.

Thirteen cases in `tests/test_area_routing.py`, seven mutations red. Checked live on a
fresh origin: `/?area=sk-tapio&lang=en` opened Tapio in English and seeded `en`; FI rewrote
the URL to `lang=fi`; the English link again applied English and left the stored `fi`
alone; `lang=xx` and `lang=EN` were stripped while `area` stayed.

### Confirmed empty beats kept data (2026-09-05, sw.js v107)
Kino Metso's Muurame had its last screening on 2026-09-04. The next cloud run found the
town empty and took the "no showtimes, keeping previous data" branch: the past show was
kept, the venue read `stale`, the provider `partial`, and `oldest` was pinned to an old
stamp while three venues were fresh. The 2026-08-31 rule honoured `EMPTY_VENUES_CONFIRMED`
only for venues that had never had data.

The order the loop checks now:

1. Confirmed empty from a successful adapter response (the module sets
   `EMPTY_VENUES_CONFIRMED` and reported the venue) publishes a fresh empty file and
   records the venue as `pending`, whether or not old data exists.
2. Zero rows without that confirmation keeps the previous file and marks the venue `stale`.
3. A fetch, schema or parse failure never reaches the loop: the site fails as a whole.

`pending` now means "no programme at the moment" rather than "not started": "Ei ohjelmistoa
juuri nyt", "Inget program just nu", "No programme right now". No new state, no schema
change. eTiketti does not set the flag and keeps rule 2.

`tests/test_run_partial.py`, `ConfirmedEmptyTest`: confirmed empty with and without an old
file, zero rows without the flag, a confirming module that did not report the venue, a
failing fetch, and Kino Metso's four-venue shape. Four mutations red.

### Heurekan planetaario: a science centre's daily programme as a venue (2026-09-05, sw.js v108, revised v109)
Heureka's planetarium in Vantaa shows four films a day on a weekly pattern, included in the
day admission, admitting from five years whatever the film. Added as the 34th provider
with the ordinary templates, one new booking mode and one generic page sentence.

Source, read as a visitor on 2026-09-05: heureka.fi is a Shopify storefront behind
Cloudflare. Its "Päivän ohjelma" page renders three arrays from Shopify metaobjects,
`window.eventCalendarData` (22 items in nine categories, six `Planetaarioelokuvat`),
`window.eventExceptionsData` (a replacement weekday schedule over a date range, newest
start wins) and `window.disabledHolidays`. No feed exists. The adapter expands the arrays
21 days ahead, planetarium films only. Each film's article gives `Kesto`, `Ikäsuositus`,
the description and a `Kielivaihtoehdot` line; the FAQ below repeats admission rules and
stays out of the synopsis. 192 showtimes, 4 films, five requests of about 1.6 MB.
Conditional GETs are off: the page answers `If-None-Match` with a full 200 every time.
Heureka's own pages: one ticket covers exhibitions, planetarium films and shows; five
ticket products from 0 to 26 euro; "Ikäraja: 5 vuotta"; recommendations are not limits.

Decisions:
- Blank price compartment. The word "Liput" was measured to fit but declined: a ticket is
  already the link to tickets. Reversal is one line per renderer.
- `book="admission"`, a fifth registry mode: footer "Sisältyy pääsylippuun · Näytösajasta
  lippukauppaan – heureka.fi", tooltip "Osta pääsylippu", page intro "Esitykset sisältyvät
  pääsylipun hintaan. Pääsylipun voi ostaa osoitteesta heureka.fi." No Heureka string in
  the client or the generator. Reservation guidance is not shown.
- Five-year floor as the per-show `age`, `K-5`, the field a licensed auditorium's 18+
  uses. `rating` stays blank. `age_note()` appends "Näytösten ikäraja on 5 vuotta." to a
  generated page when every screening in its window shares a limit.
- Recommendations become a `method` tag: "Suositus yli 10 v", "Suositus 5–10 v", "Suositus
  aikuisille". "Suositus 10+" was rejected as turning "over ten" into "ten and over".
- Provider `heureka`, venue `hk-vantaa`, name and short "Heurekan planetaario". The first
  name "Heureka Planetaario" was not Finnish; the branch was unpublished, so no redirect.
  Audio languages from `Kielivaihtoehdot` as `FI-A, EN-A, SV-A`. No poster: 16:9 stills.
- Accent `#0B8468`: 26.5 / 26.0 ΔE00 from Finnkino's orange and 30.3 / 27.9 from Bio
  Grand's violet in Vantaa, best of 22 candidates.
- `where="cloud"`, provisional on the first cloud run.

Emptiness: a calendar with no planetarium film returns the venue as an empty list and the
module sets `EMPTY_VENUES_CONFIRMED`. The first version raised `EmptyProgramme`, which
writes nothing, so a paused programme would have kept the last screenings indefinitely.
`run.py` now treats a site whose every venue is confirmed empty as answered: fresh empty
files, all `pending`, `status: ok`, exit 0. A page without the arrays or with unparseable
clocks raises and keeps the previous file.

Measured on the served tree at 320, 375 and 1200: 4 cards and 10 stubs with the
recommendation pills; Ajat rows 120 × 40 px; Vantaa combined view 19 cards and 41 stubs
with the 5+ glyph; static page 36 tickets, every href the ticket collection.

`tests/test_heureka.py` covers the arrays, the weekday expansion with holiday, exception
and ended run, the film page, four runs through `run.main` with the fetch stubbed, the
registry entry, client strings, generator intro and age sentence; `test_run_partial` and
`test_empty_programme` gain the confirmed-empty site cases. 29 mutations red.

Accepted and open: the Lapsille filter never admits a Heureka film (it reads the KAVI
rating first, and Heureka publishes none); the static pages carry the intro sentence only;
a closed day not in Heureka's holiday list publishes screenings the way the page does.

### Heureka's missing posters wait for written permission (2026-09-05)
Three of the four planetarium films render initials tiles: Asteroid Quest and The Stellars
have no TMDB entry, Metsän sydän has one (1732662) without a poster. No weak match, so no
wrong poster is on the site. Heureka's own site carries portrait key visuals for two.

Not mirrored. Public availability is not permission to copy and redistribute
(Tekijänoikeuslaki 404/1961), and Heureka's FAQ licenses none of its promotional artwork.
The route is written permission from Heureka's media contact. If it arrives, the accepted
implementation is the article's portrait `og:image` only, same-site source, a valid image
type and verified dimensions; no "first portrait image" fallback. Declined regardless:
weak TMDB matches, generated artwork, cropped 16:9 stills.

### Film metadata refreshes under an open sheet, and a failed fetch is not memoised (2026-09-05, sw.js v116)

Regina films showed no synopsis for a reader. The data was fine; the client was not.
`ensureExtraFilms()` memoised `{}` after a failed fetch, so no later sheet in the tab had a
synopsis. `fresh` messages were handled for area files only, so a metadata copy that
landed after the tab opened waited for a reload.

`makeExtraStore(io)` replaces the memo. One shared fetch per load; a failure memoises
nothing. `fresh()` reads the cached copy from Cache Storage and compares the serialised
`films` map, since `generated` is a bare date. A real change swaps the map in and redraws
an open sheet: `refreshOpenSheet()`, same film, scroll kept, cinema, day, filters and
fragment untouched. A load in flight is awaited before the read, because the worker
answers a load from cache before it refreshes. `readCached` moved next to the store.

Seven harness scenarios, seven tests. Each rule removed goes red.

### A slot refilled during a background read keeps the refill (2026-09-05, sw.js v115)
The handler's guard against `refreshAll` was "is there still an entry" after the await. On
resume `refreshAll` deletes every entry and `loadSchedule` refills the selected one, both
inside a read's latency, so a read started against the 06:00 payload answered with a 09:00
snapshot after the refill had put 10:00 there, and overwrote it. Found by an external
review.

`reread` takes the entry object before the await and writes only if the slot still holds
that object. An invalidation counter would have needed `refreshAll` and `loadSchedule` to
bump it. The coalesced follow-up takes the current entry as its baseline, so a message
queued behind a discarded read still gets its read, and one queued behind a slot that
stayed empty costs no read. Three harness scenarios; removing the identity test or taking
the identity after the await turns two red, and removing the empty-slot return fails the
harness run.

### The reproducibility check is told the day the pages were built for (2026-09-05)
`ci.yml` regenerates the committed pages and requires a clean tree, but `main()` read
`datetime.now(FI).date()` and every page lists a window of days starting there, with the
sitemap stamped the same day. Identical input built on 2026-09-05 and on -06 differed in
165 files on the reviewer's checkout and 173 of 183 here, so the check went red after
midnight with nothing changed. Found by an external review.

`main(today=None)` takes the day; `build_pages.py --date YYYY-MM-DD` passes one; `--date
recorded` reads back the day the committed sitemap carries, since every URL's `lastmod` is
written from `today` and a test pins that. A tree without a sitemap has nothing to
reproduce and the flag says so. `ci.yml` uses `--date recorded`; `biorex.yml` and the
local wrapper build for today.

Rejected: a dedicated date file (a second record of the same fact); a page-level stamp (the
volatile-markup rule); freezing CI's clock to the commit's date (a build straddling
midnight would be irreproducible). `tests/test_build_date.py` builds a synthetic two-venue
city against a patched clock.

### Every cinema in a combined city can refresh it (2026-09-05, sw.js v114)
`loadCity` sets `generated` to the oldest member's timestamp for the stale banner. The
background-refresh handler compared that value to detect change, so when a newer member
refreshed and the oldest did not, the fresh schedule was thrown away. Found by an external
review.

`cityPayload`, the fold sliced out of `loadCity`, returns `stamp`: one `id@generated`
entry per expected member, `-` for a member whose file could not be read. `refreshKey()`
compares a city on its stamp and a venue on its `generated`; the banner keeps reading
`generated` and `oldest`.

The 60 s cooldown had to go: with the detector fixed it would have applied one member's
message and dropped the rest, which is the reported case. It was needed because the
re-read went through the service worker, whose data branch answers from cache and starts a
background refresh, and every refresh that lands posts another message. Listener-side
alternatives each fail: a per-file cooldown multiplies re-reads (N² revalidations) and
still loops past the window; coalescing dropped messages into a read at window end re-arms
from its own second wave every 60 s; reading one member loops at network latency. The SW
comparing bytes before messaging works but changes the worker's contract.

`readCached` reads the copy the worker just wrote from Cache Storage. A cache read starts
no refresh and posts no message, so the handler cannot feed itself and needs no cooldown.
One read per area at a time; messages during a read fold into one follow-up. The `caches`
global is guaranteed: the handler runs only on a message from a registered worker.

Measured live on v115, real Chrome: Helsinki on screen, Sello's cached copy doctored, the
picker switched to Espoo with a MutationObserver recording `#main`. Load spinner at 9 ms,
doctored copy at 20 ms, three worker messages at 24 to 26 ms, real schedule at 35 ms with
no spinner between; nothing further over 118 s.

Harness and tests grew from nine to nineteen; the sandbox has no `fetch`. Mutations red:
comparing `generated` (2), dropping the missing marker (1), reading the selection after the
await (3); dropping the coalescing or reading through fetch fails the harness run.

### A background refresh lands in the slot it was asked for (2026-09-05, sw.js v113)
The `{fresh: path}` handler re-read the file and then compared and assigned
`jsonCache[state.area]`, reading the selection after the await. A reader who picked cinema B
while A's read was in flight had A's answer written into B's slot for the life of the tab.
Found by an external review.

The area is read once, before the await; only that slot is compared and written; a render
happens only if that area is still on screen. A payload for a cinema the reader has left
is kept for `loadSchedule`. A slot emptied by `refreshAll` meanwhile stays empty.

The handler became `makeFreshHandler(io)`, sliced verbatim by
`tests/swr_refresh_harness.js`, with reads the scenario settles by hand. Nine tests;
reading `io.area()` after the await turns three red, rendering regardless of selection and
writing into an emptied slot one each.

### The past-times control inflects its count (2026-09-05, sw.js v112)
"Näytä 1 aiempaa" is not Finnish: one hidden screening is "Näytä aiempi", two or more
"Näytä {n} aiempaa", the reverse action "Piilota aiemmat". The label is `pastLabel(open, n,
T)`, sliced verbatim by `tests/past_label_harness.js`, with a `showPastOne` string in all
three languages. Six tests; five mutations red.

### The Finnish interface copy, reviewed (2026-09-05, sw.js v109)
A reader's review of the Finnish strings this repo owns found translated-sounding
constructions. Every Finnish string in `index.html` and `build_pages.py` was read;
provider titles, synopses and room names are untouched. `tests/test_finnish_copy.py` pins
the result.

- Booking lines name the showtime: "Näytösajasta lipunmyyntiin – {host}", "Näytösajasta
  paikkavaraukseen", "Näytösajasta teatterin ohjelmistoon", "Näytösajasta teatterin
  omalle sivulle" for a combined view. "Napauta näytöstä ostaaksesi liput" was
  device-specific. Tooltips stay "Osta liput", "Varaa paikat", "Avaa ohjelmisto", "Osta
  pääsylippu". Generated intros read "Näytösajasta pääset", the admission intro
  "Esitykset sisältyvät pääsylipun hintaan. Pääsylipun voi ostaa osoitteesta {host}.", the
  empty state "Lähipäiville ei ole julkaistu näytöksiä." The manifest name takes the en
  dash.
- Freshness describes the data: "Näytöstiedot" replaces "Aikataulut", "näytöstiedot eivät
  ole päivittyneet" the stale banner, "Vanhentuneet näytöstiedot" and "Osa näytöstiedoista
  ei päivittynyt" the summaries, "Näytöstiedot eivät päivittyneet {n}/{m} teatterilta" the
  tooltip.
- Combined rows read "{city} – kaikki teatterit (n)", city first so the trigger's ellipsis
  eats the generic tail; unclipped at 320 and 375. Generated city chips keep "Kaikki
  teatterit – {city}".
- Controls and states: "Näytä 2 aiempaa" / "Piilota aiemmat"; "Oma teatteri valittu –
  avautuu jatkossa automaattisesti"; "Valitussa teatterissa ei ole näytöksiä tänään.";
  "Tämän päivän ohjelmistoa ei ole vielä julkaistu."; "Valittavissa ovat vain päivät,
  joille on näytöksiä."; "Näytöstietoja ei juuri nyt saatu ladattua."; a `#m=` link to a
  film the venue is not showing reads "Ei näytöksiä valitussa teatterissa."
- Subtitles are a labelled field, "tekstitys: suomi/ruotsi", one formatter rule each and a
  test that they agree.
- Finnish price typography: "10 €", "10,50 €", "alkaen 10 €" with a non-breaking space in
  `priceLabel` and `price_label`; Swedish and English decimals pinned to stay as they were.

Left as they were: the day chips, filter chips, search placeholder, contact and licence
lines, "Ei enää näytöksiä tänään.", "Seuraavat näytökset", "Menneet näytökset",
"loppuunmyyty", "Ensi-ilta", the controls' accessible names. 89 pages rewritten once.

### Search Console baseline, 2026-08-29 to 2026-09-02 (read 2026-09-04)
First export, web search, five days. The tables do not share a denominator: chart, devices
and countries sum to 1776 impressions and 12 clicks (CTR 0.68 %); pages to 1951, since an
impression counts once per URL; queries to 1300, since rare queries are anonymised. A later
export is comparable only table by table over the same window.

Theatre pages carried about 92 % of page-level impressions; 74 of 170 canonical pages
appeared; small-town cinemas led (Leffabuumi Kinolinna and Kino Ritz 168 and 167
impressions at positions 5 to 7, Savon Kinot's four pages about 300 together) while
Finnkino pages sat at 12 to 20. Visible queries: the cinema's name (746), "elokuvat
<city>" (285), "<cinema> ohjelmisto" (248, two of three attributed clicks); none contained
"leffavuoro". Mobile position 8.4, desktop 23.6.

Decisions, 2026-09-04: no broad SEO change on five days of data; re-read after two to four
weeks. No city pages for one-cinema towns, which would compete with the theatre pages that
rank. The one experiment, when run: "ohjelmisto" in Finnish theatre-page titles and
descriptions on a subset against an unchanged control, measured over two to four weeks.
Desktop position and the absence of brand queries: watch.

### Savon Kinot moves to the local half (2026-09-04)
Cloud fetches #158 and #159 failed on www.savonkinot.fi: `403` on all three attempts,
`Server: cloudflare` with a CF-Ray from the Dallas edge and no `Retry-After`. Every run
from 09-02 23:14 to 09-04 07:23 UTC had read the site normally; the other 16 eTiketti
hosts fetched in the same runs.

Not the polling rate: Cloudflare's rate limiter answers `429` with `Retry-After`, the
refusal hit the first request after 3.7 hours of no contact, and it held across runner
addresses, so it keys on the address range. From an ordinary connection the site answered
200 with the adapter's exact User-Agent.

The registry entry moved from `where="cloud"` to `where="local"`, the route Finnkino, Kino
Akseli, Kino Engel and Joutsan Kino take; the local half is now five providers and 26 of
75 venues, recorded against the open item about moving that half off the laptop. Adapter,
headers and pacing unchanged. Exercised from an ordinary connection into a scratch
directory before the push: six venues, `exit=0`. `tests/test_run_routing.py` pins the two
local eTiketti sites.

### A screening note is not a synopsis (2026-09-03)
Found by an external review: Cinema Niagara's sheet for "Keltaiset kirjeet" opened with
Gilda's senior-screening paragraph, its price and its coffee.

`films-extra.json` holds one Finnish synopsis per normalised title, filled by the first
provider to publish one. Gilda's MyCloudCinema `description` is HTML in paragraphs, and its
senior-screening entries open with the cinema's own paragraph (7 of 41 on 2026-09-03). The
adapter stripped tags and merged the whole thing under the plain key, and fill-if-empty
kept it there. Measured: 10 of 166 entries held a note, five under plain keys read by every
cinema, plus Bio Vuoksi's "Liput 8€ maksetaan Pennittömien edustajalle" as a whole text.

Two rules, at two layers:
- At the adapter, `synmerge.drop_notes_html(desc, names)` splits on `</p>` and drops a
  paragraph that quotes a price or names the cinema (stems as word prefixes, so "Gilda"
  catches "Gildan"). The paragraph is the source's own boundary; a sentence split would
  guess ("klo 18.15", "la 12.9." end sentences that are not).
- At the merge, `synmerge.is_note(text)` is true for a price in either order (`9€`,
  `€ 10`, `12 euroa`, `5 EUR`), and `merge()` refuses such text, counting it as
  `synopses skipped as screening notes (price): N`. The slot stays empty for TMDB.

Rejected: per-provider provenance, reusing text only for the supplying provider's cinemas.
That gives up the sharing, and the distributor's blurb is the same text at every cinema.
Accepted: Cinema Orion's "Ainoa näytös, klubialennus." lines carry no price and no cinema
name and still merge.

The cache was repaired in the same commit: the Gilda paragraph stripped from nine entries,
nouvelle vague blanked. `tests/test_synopsis_notes.py`; five mutations red.

### A direct film link opens its sheet on load (2026-09-03, sw.js v106)
Found by an external review: `/?area=cn-tampere&lang=fi#m=61` loaded the list with the
fragment intact and the sheet closed, and a refresh with a sheet open closed it.
`syncSheet()` ran on `hashchange` and inside `applyLang()` only. It now also runs after the
boot's `await loadSchedule()`, guarded on a fragment being present, because `showSheet`
reads the film's screenings from `jsonCache[state.area]`, and before the `catch`, so a
failed load renders the error and opens nothing.

`tests/test_sheet_direct_load.py` pins the call, its position and the `hashchange`
listener. One mutation red.

### A tag the room already names is said once, and the Ⓐ stays on the stub (2026-09-03, sw.js v105)
Two faults found the day the Ajat ticket lost its room. The meta line read "LUXE 6 · K-16
· 172 min · 2D · Anniskelu · LUXE": the room carries the format and the method tag repeats
it. Measured: 774 rows in five classes (LUXE 319, "N Plus" and Plus 256, iSense 88, Prime
50, IMAX 21); no tag is repeated inside one method string. The Ajat line now runs
`stubTags`, the stub label's rule since 2026-08-27: drop a tag the room name contains,
case-folded, and drop plain 2D (2524 of 5020 rows). The card's shared pills still show 2D
when every screening is 2D.

Second, the Anniskelu filter made every Ⓐ disappear: with every survivor sharing the tag it
folded onto the card as a pill and left the stubs. A tag drawn as a glyph never folds
(`common` skips `glyphOf(f)`), so the Ⓐ stays on every anniskelu stub. Words still fold.

Measured on the served tree at 1200 and 375: no room word twice, no 2D, 11 Ⓐ on 11 stubs
under the filter and no card pill. `tests/test_stub_tags.py` with
`tests/stub_tags_harness.js`; five mutations red.

### The Ajat ticket is time and price (2026-09-03, sw.js v104)
Reported from a desktop screenshot of Finnkino Sello's Ajat list: titles at three x
positions. Since v100 the time-mode stub grew to its content, 158 to 220 px ("Sali 3"
170.2, "LUXE 5 Ⓐ" 201.8), leaving a phone title 64 to 96 px at 320.

Decision: in the Ajat list the ticket is time and price, 62 + 56 + 2 = 120 px by
construction (122 with a chain rule). The room, the venue tag of a combined view and the
screening's age limit move onto the meta line, venue first: "Finnkino Plevna · Sali 5 · S
· 78 min · …". The 18+ pill (`ageGlyph`) sits after the room; the Anniskelu glyph is not
carried over because the line says the word. The room never wraps (`.room{white-space:
nowrap}`); the widest, "KINOLINNA | SALI 1" at 103 px, fits the 201 px column at 375. The
card's row ticket and the sheet's keep the room; a test pins that exactly two renderers
still emit `.aud`.

| viewport | before: stub / title column | after: stub / title column |
|---|---|---|
| 320 | 170.2 to 201.8 / 64 to 96, three columns | 120 / 146, one column |
| 375 | 170.2 to 201.8 / 119 to 163 | 120 / 168 to 201 |
| 402 | 170.2 to 201.8 / 146 to 190 | 120 / 168 to 228 |
| 1200 | 170.2 to 201.8 / 845 and up | 120 / one column |

Declined: a fixed 204 px stub with the room inside (22 venues publish no room and would
pay 34 px of title for a blank); one shared column per list via `subgrid` and
`fit-content(220px)`, which aligns titles but leaves 119 px of title at 375 and moves when
a filter removes the rows that set it. Learned there: a `column-gap` set on a subgrid but
not its parent is applied as item margins, and `fit-content` with `overflow-wrap:anywhere`
lets the column shrink to the wrapped label.

`tests/test_compact_ticket.py`, `TimeModeTicketTest`; five mutations red. Generated pages
untouched: `build_pages.py` has no times view.

### Tickets are 40 px (2026-09-02, sw.js v103)
A reader found the tickets heavy on a phone: the row ticket had gone from 32 to 44 px with
the price compartment, and the combined view's were 44. Rendered at 44, 40 and 36 with the
app's stylesheet and chose 40: lighter, and the two-line "alkaen 10€" (27 px) still fits.
A uniform 160 px ticket for every view was mocked and declined: combined-view venue names
truncate and a no-room cinema gets a blank line.

Only `min-height` changed, 44 to 40, in the client's row and grid tickets and the
generator's. WCAG 2.5.8 asks 24 px. Measured live at 375: 33 Tampere tickets at 40, two at
43.5 where the venue label wraps; sheet and time mode 40; Niagara theatre page 19 at 40.
Pinned in `tests/test_compact_ticket.py` and `tests/test_ticket_anatomy.py` for both
renderers; three mutations back to 44 red. The header's 44 px controls, the CTA and the
language segments are not tickets and did not change.

### The single-cinema ticket has a price compartment (2026-09-02, sw.js v102)
After the price moved onto the screening it trailed the room as a small muted word, and a
ticket without a price was a different shape from one with; the perforation sat after the
time, 3.8 px off its own seam.

Decision, presentation only: the last 56 px of every row ticket are the price compartment.
The dashed seam is its left border and the notches are centred on that seam from the same
variable (`--pw`, `right:calc(var(--pw) - 4px)`). The compartment is always present and
blank when the cinema publishes no price, so priced and unpriced tickets share one
silhouette. The price is `var(--ink)`, 700, .78rem, centred on the time's axis; the time
stays .92rem/800. "alkaen 10€" and "från 10€" wrap to two lines inside the compartment. The
generated theatre pages carry the same anatomy. The combined and "all" views are untouched,
and an empty compartment collapses there (`:empty`).

Measured live at 375 and 1200 in both themes: Niagara 143.8 × 44 px, compartment 56, seam
and notch centre both at 86.8; Plevna 25 blank compartments aligned; Orion in Swedish
"från 10€" on two lines; generated Niagara page 121.8 × 44, seam and notch 64.8.

`tests/test_compact_ticket.py`, 13 tests across both renderers; nine mutations red. 170
pages rewritten once, the second regeneration writes nothing.

### The combined view's stub is the same ticket (2026-09-02, sw.js v101)
The combined city view hid the stub's perforation (`.stubs.grid .stub::before,
.stubs.grid .stub::after{display:none}`) and the generated city pages hid their notches,
because the stacked stub put the time above the place and a notch at the row stub's seam
pointed at nothing. Beside a single-cinema view the combined stubs read as generic cards.

Decision: every showtime is the same ticket in every view. The combined stub is the row
stub adapted: a time compartment on the left, `--tw:64px` (12 + 41.8 + 10, the row stub's
padding around a tabular "00:00" at .92rem), the details compartment beside it with a
dashed left border as the seam, the price at the trailing edge, notches at `calc(var(--tw)
- 4px)` so seam and notch share one x by construction. The generated city pages use the
same grid; their notches moved from `-5px` to `-4px`, centred on the seam. `min-width:0` and
`overflow-wrap:anywhere` on the details side break "Tennispalatsi" instead of letting it
run under the price.

A second column needs a 240 px ticket. The grid had `minmax(168px, 1fr)` and a phone
override of 140 px from the stacked stub; in the 335 px sheet at 375 two 163 px columns left
4 px of details and "Cinema Orion" broke letter by letter over nine lines. Both grids now
use `minmax(min(240px, 100%), 1fr)`: one column at 375, 402 and 520, two from 600.

Measured live in the Tampere combined view at 320, 375, 402 and 1200: 37 stubs, seam 64.0
and notch centre 64.0 on every one, 44 to 56 px, no overflow. Generated Tampere city page
90 stubs aligned. The row stub's own 3.8 px notch offset was noted and fixed in the next
entry.

`tests/test_ticket_anatomy.py`; mutations red in both renderers, including 240 back to 168.

### A price is the screening's, never the film's (2026-09-02, sw.js v100)
Reported from the Tampere combined view: Autofiktio had Cinema Niagara 16:15 at `11€` and
two Finnkino Plevna screenings with no published price, and the card read "espanja ·
tekstit suomi/ruotsi 11€" with no stub carrying a price. Both renderers folded
`priceLabel` over the film's screenings, which skips rows without a price, so a priced
subset became a film-wide figure; the generator's "differing prices go on the screening"
rule counted the empty string as a differing price and printed `11€` twice.

Decision: the price is the ticket's. Each screening's own `priceLabel([s])` renders in a
`<span class="price">` inside its stub, and nothing on the card or in the sheet header,
even when every screening agrees. A screening without a price gets no element. A
provider's floor survives ("alkaen 10€", "från", "from"). JSON-LD was already per
screening.

Design: the price is a child span at the trailing edge, .72rem, muted like the room, so
the time stays the strongest element. In the stacked stub the grid is `"time price" /
"aud aud"`. The fixed 158 px time-mode stub, where "alkaen 10€" ran 4 px past the edge,
grows to its content capped at 220 px and the title ellipsises instead. Measured live on
the Tampere case at 320 to 1200 in both themes: every stub 45.5 px, price inset 1 px, zero
euro signs in any card meta.

Tests in both renderers, including the whole-page property that a euro sign occurs only
inside a stub's price element (synopsis prose excluded). Mutations red: film-level fold
restored (98), one price copied to every stub (4), price element dropped (7), the client's
fold restored. 170 pages rewritten once.

### The landing pages belong to the product (2026-09-02)
The 168 canonical pages under `/teatteri/`, `/kaupunki/`, `/en/theatre/` and `/en/city/`
were indexable and looked nothing like the app: system font, boxed cards, a sentence-long
CTA and showtimes printed as `16:00 Sali Tapio 4 FI-S, SV-S`. Redesigned in
`build_pages.py` alone: no JavaScript that renders content, no new data, the same 4-day and
2-day horizons, JSON-LD, titles, canonicals and hreflang pairs, the four legacy redirects
byte-identical.

What a page is: wordmark and the FI · SV · EN selector in a header bar; the h1; a subline
(`Joensuu · savonkinot.fi`, or `12 teatteria`); a two-sentence intro; one CTA; sticky day
headings; a film per row with the app's poster sizes, rating chip, credited TMDB score,
runtime, genres and the synopsis once; ticket-shaped showtimes; on a city page a chain
legend and the venue links as 44 px chips. Tokens and the two self-hosted Archivo files
are the app's.

- The CTA is `/?area={id}&lang={fi|en}`, labelled `Avaa koko ohjelmisto` / `See the full
  programme`, one line, 48 px, the app's selected-segment treatment. A two-line version
  measured 64 px and read as a hero panel.
- `stub_parts()` returns room, spoken language and subtitle languages on a theatre page,
  and the chain-prefixed cinema first on a city page, joined with ` · `, empty parts
  dropped. The room is the adapter's value verbatim. Superseded the same day by "The card
  is the app's card" for where language and price sit.
- Language codes render as words. `lang_parts()` is the app's `langTxt`; the name tables
  are the client's `LN.fi` and `LN.en`, and a test reads the client's out of `index.html`
  and asserts equality. The subtitle word is the page's own ("tekstitys", "… subtitles").
- Four codes in the data were not in the client's table on 2026-09-02: `TU` (62) and `MA`
  (3) are Finnkino's Turkish and Malayalam, `XX` (46) is Nexxo's "no subtitles", `LT` (1)
  is Lithuanian. The generator carries `CODE_ALIAS` (TU → TR, MA → ML), `NO_SUBTITLES` (XX)
  and `LN_EXTRA` (LT, ML), each named in a test. The adapter and client halves were done
  under "Language codes normalised end to end". Not ported: `stubTags`, `priceLabel`
  (later ported, see the card entry) and the metadata fold.
- Wrapping is per part: cinema and language phrases may break at spaces and, via `<wbr>`
  after each slash, between joined names (Chrome does not break after a solidus; Kino
  Engel's six-language screening clipped a 206 px column). The room stays on one line.
  The grid's column floor is `min(260px, 100%)`, so a 320 px phone gets one column.
- The selector marks the page's language with `aria-current="page"`, links the other
  static language with `hreflang`, and opens the app in Swedish via `?area=…&lang=sv`
  since there is no Swedish page. No Swedish `hreflang` in `<head>`.
- The intro promises what the registry's `book` mode offers (`venue_intro`): ticket sale,
  seat reservation, the programme page, or tickets at the door. A city says `kun linkki on
  saatavilla` / `where available`. Venue names appear only in nominative positions.
- The synopsis is clamped to three lines below 560 px with the full text in the markup.

Measured on the served pages at 320, 360, 375, 402 and 1200 in both themes: no horizontal
overflow, no clipped label part, CTA 48 px, every selector segment and venue chip 44 px,
stubs 44 to 88.9 px (the six-language Engel stub at 320). The 172 files grew from 5.15 MB
to 8.32 MB; `write_if_changed` holds and the drift check stays green.

`tests/test_landing_pages.py`, 28 tests from the committed data plus synthetic shows for
the shape rules. Break-verified 26 ways, from the theatre stub repeating the venue to the
selector in the wrong order, each red.

### The landing pages follow the app's theme (2026-09-02)
The redesign chose the theme by `prefers-color-scheme` alone. Reproduced live: `kino-theme`
set to light in the app, OS dark, `/kaupunki/helsinki/` opened dark beside the light app.
"No JavaScript" became "no JavaScript that renders content".

Two constants in `build_pages.py`, both the app's own behaviour: `THEME_HEAD_JS`, in
`<head>` before the stylesheet, reads `kino-theme` in the app's try/catch, applies a stored
`dark` or `light` (any other stored value is treated as absent, since it becomes a CSS
selector) and otherwise asks `matchMedia`, setting `data-theme` before first paint;
`THEME_BODY_JS`, at the end of `<body>`, is the toggle: flip the attribute, write the same
key, repaint `theme-color` from `--bg`. The stylesheet holds the dark tokens under both
`:root[data-theme=dark]` and `@media (prefers-color-scheme: dark)` for
`:root:not([data-theme=light])`. `html:not([data-theme]) #themeToggle{display:none}` hides
the button when the script did not run.

The toggle is a 44 px circle and the header padding dropped from 12 to 8 px; at 320 px the
wordmark drops to .6rem so the row (wordmark, three 44 px segments, toggle) fits in 292 px.

Tests read every page: head script present, before `<style>`, with the two-value guard;
both token blocks; the hidden-without-script rule; the toggle with a localised name; the
body script writing the same key; no script containing `innerHTML`, `document.write`,
`createElement`, `appendChild`, `fetch(` or `textContent`; both scripts pass `node
--check`. Ten mutations red. Checked live: stored light opens light with both `theme-color`
metas at `#F6F7F9`, the landing toggle stores `dark`, the app opens dark, and back.

### The card is the app's card (2026-09-02)
Side by side at 402 px the landing page and the app shared materials and assembled them
differently: a text star for the score ring, language words on every stub, side-by-side
stubs where the combined view stacks them, tighter padding. The app is the blueprint.

- Film facts fold first-non-empty across the day's screenings (`first()`): rating,
  runtime, genres, score, votes, poster. A chain that publishes no rating must not blank
  the card when another did.
- Language and price sit on the card once when every screening shares them and on the
  screening when they differ. `price_label` is the app's `priceLabel`, and the test runs
  the client's harness cases through both.
- The score is the app's ring, with `role="img"` and the label "TMDB 7.1/10 · 41 ääntä";
  `thin` under 25 votes. No `aggregateRating`.
- Stubs follow the view: a theatre page is a row of ticket stubs, a city page a grid of
  stacked ones (`.stubs.grid`, 168 px columns, 140 below 520), 44 px floor on both.
- Card spacing is the app's: 20 px between films, 18 px poster gap, meta rows at 7 and
  5 px. The stub's time and place lines get `line-height: 1.2`, since the page body's 1.5
  made a stacked stub 54 px against the app's 46.

Measured after: no overflow or clipped part at 320, 402 and 1200. The Helsinki page grew
from 33 251 to 40 190 px at 402, the app's own trade in its combined view; the page-length
item stays on the backlog. Not ported: `stubTags`, the premiere chip, glyphs, the age chip.
Ten mutations red.

### The venue picker is searchable (2026-08-31)
The native `<select>` had nowhere to hang a search field over 70 venues. The trigger keeps
the select's face and place; tapping it opens a dialog on the same modal lifecycle as the
movie sheet and the month picker (`BEHIND()`/inert, Escape, backdrop, focus restore).

- The keyboard never opens uninvited: the sheet opens with focus on the close button, and
  the search field, pinned to the top, gets focus only when tapped. On a fine pointer the
  field is focused immediately.
- Search folds diacritics both ways ("jarvela" finds Järvelä; NFD-strip keeps `<mark>`
  offsets aligned with the NFC original), matches label and city, hides emptied city
  groups and keeps the combined "Kaikki {city} (n)" rows findable by their own text. Esc
  clears the query first and closes second.
- Selection is the old code path (`state.area`, `prefs`, `syncFav`, `loadSchedule`), so
  the saved venue, the star, `?area=` links and city ids behave as before. Rows carry the
  `chain-{id}` classes for the dot colour.
- Costs accepted: the select's type-ahead, and the Chromium `::picker(select)` block.

Reviewed the same day, three row-model faults fixed: the combined row appeared whenever
any venue in the city matched and sorted first, so "itis" plus Enter picked Kaikki
Helsinki; a saved `city:*` favourite never showed under "Oma teatteri"; in Swedish a Turku
venue was findable as "Åbo" but not "Turku". The row list is now `venueRows()`, a pure
function extracted verbatim by `tests/venue_picker_harness.js`, with row order asserted
because Enter makes order behaviour. Each fix break-verified. Focus, inert, Escape and
keyboard plumbing stay live-verified.

### A newline hid the scheme from `safeUrl` (2026-09-01)
`safeUrl` read the scheme off the raw string with `^([a-z][a-z0-9+.-]*):`. A URL parser
deletes ASCII tab, LF and CR anywhere in the URL and strips control characters off both
ends before it looks for a scheme, so `java<LF>script:alert(1)` matched no scheme, was
read as relative, and resolved to `javascript:` when followed. Reproduced through a real
parser:

    javascript:alert(1)        rejected
    java<LF>script:alert(1)    ACCEPTED  -> javascript:
    java<CR>script:alert(1)    ACCEPTED  -> javascript:
    java<TAB>script:alert(1)   ACCEPTED  -> javascript:
    <NUL>javascript:alert(1)   ACCEPTED  -> javascript:

The NUL case was not in the report: `trim()` removes whitespace, NUL is not whitespace, and
a parser strips it anyway. Every one reaches an href built from provider JSON.

Decision: reject any control character rather than clean. Cleaning would have to reproduce
exactly what the parser strips, which is what this code was wrong about. `trim()` still
runs first, so an adapter's trailing newline is fine. `safeAssetUrl` did not have the hole
(a control character cannot walk a path out of the `data/posters/` allowlist) and shares
the guard anyway.

Both are sliced verbatim by `tests/safe_url_harness.js`, which resolves every accepted
result through node's WHATWG URL parser and asserts the protocol. Five mutations red,
including the guard narrowed to LF and CR only, which lets tab and NUL back in.

### Poster URLs are checked against the origin and path (2026-08-30)
`safeUrl` answered two questions with one rule. A ticket or trailer URL is meant to leave
this origin; a poster is not, since an `<img>` is a request the browser makes on its own
and the README's no-third-party-requests claim rests on every poster being local.

`safeAssetUrl` is a path allowlist, same origin and inside `data/posters/`, rather than an
origin check, because `mirror_posters.py` leaves a hot-linked URL in the data when a
download fails, so the client has to hold the invariant itself. Every poster reference in
the committed data was `data/posters/` on 2026-08-30 (3059 on shows, 98 in
`films-extra.json`). Tested by injecting three hostile forms into a venue file: absolute,
protocol-relative and padded uppercase all fell back to the placeholder tile, zero
off-origin images.

### A refused request held its socket until the collector noticed (2026-09-01)
A suite run printed 24 ResourceWarnings. Thirteen were real: `urllib.error.HTTPError` is
the response object, and `common.fetch` kept the last one across the retry loop and raised
it, so every refusal left a socket open until garbage collection. Against a host refusing
everything (`mirror_posters` has had 185 failures against one host) that is 185 sockets.

`e.close()` on entering the handler. `code`, `reason` and `headers` survive the close, no
caller reads the body, and `close()` is idempotent. The other eleven were fixtures:
`shutdown()` leaves the listening socket open and two of the three local servers never
called `server_close()`.

`-W error::ResourceWarning` does not enforce this: the socket warnings are raised while
the interpreter shuts down, after the result is reported (measured 2026-09-01, exit 0 with
the leak reintroduced). `Checks` greps the captured suite output instead. Four new tests in
`test_common_fetch.py` go red with `e.close()` removed; `server_close()` removed puts the
warning back in the output the workflow reads.

### Checks needs the whole history, not the tip (2026-09-01)
The first run of the workflow failed on four tests in `test_indexnow.py`: `actions/checkout`
fetches a single commit, `RealHistoryTest` diffs two named commits against their parents,
and two `PushRangeTest` cases need `HEAD^` to resolve. Reproduced with a `--depth 1` clone.
`fetch-depth: 0`; a full clone is 22 MB against 15 MB shallow, since the posters dominate
both.

### A failing check has to say what failed (2026-09-01)
The first `Checks` run went red with only "Process completed with exit code 1": the two
gates emit `::error::` lines, a plain test failure did not, and `set -o pipefail` ended the
step at the `unittest` call. The Actions log answers 403 without a token and this repo does
not read Actions logs; check-run annotations are readable over the public API. The step now
captures the suite's exit code, emits one `::error::` per `FAIL:` or `ERROR:` line, and
writes the summary to `$GITHUB_STEP_SUMMARY`.

The first version emitted the annotations with `grep ... | while read`. grep exits 1 on a
green suite, and under pipefail that fails the step (measured: `bash -e` exits 0, `bash -e
-o pipefail` exits 1). `awk` exits 0 either way.

### The suite is a workflow rather than an instruction (2026-09-01)
Three workflows existed and none ran a test; every check was a CLAUDE.md instruction to a
person. The client is the worst case: no build step, so a syntax error in `index.html`'s
script block ships and the service worker keeps serving the last good copy to whoever
pushed it.

`Checks` runs on any push touching `index.html`, `sw.js`, `scripts/**` or `tests/**`:

- The JavaScript parses: `scripts/check_inline_js.py` pulls the inline block out, `node
  --check`s it and `sw.js`, parses `application/ld+json` as JSON, pads the fragment to its
  offset so node's line numbers are the file's, and fails on a page with no inline script.
- Regeneration produces no diff: `build_providers.py` and `build_pages.py` in a clean
  checkout must change nothing. A generator changed without regenerated output is the
  author's to fix; committed data whose pages were never rebuilt means the live site
  disagrees with its own JSON.
- A skipped test fails the run: every dependency is installed on the runner, so a skip
  means one went missing. Pillow pinned to `12.3.0`.
- `check_runs.py` is not in it; `logs.yml` runs it on pushes that touch a log.

`push` and not `pull_request`: history is linear and direct-pushed. The path filter keeps
it off the data commits. Not verified before the first run: that the five poster tests pass
with `pillow==12.3.0` on a runner.

### The workflow's dependencies are pinned (2026-08-30)
`actions/checkout@v4`, `actions/cache@v4` and a bare `pip install pillow` sat in a job with
`contents: write` that pushes to `main`. A tag can be re-pointed; a SHA cannot. The pip
install is worse: the runner installs it fresh every run.

- `actions/checkout` -> `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1)
- `actions/cache` -> `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` (v6.1.0)
- `pillow` -> `12.3.0`

Both actions moved off v4 on 2026-08-31 when runs warned that they target Node.js 20; v7.0.1
and v6.1.0 declare `node24` in their `action.yml`, checked at the resolved SHA. Inputs were
checked before the bump: `checkout` takes none here, `cache` v6.1.0 accepts `path`, `key`
and `restore-keys`. `logs.yml` carries the same `checkout` pin. Resolved from the GitHub and
PyPI APIs; the readable version stays in a comment beside each SHA.

No interpreter on the machine has PyYAML, so the edited lines were verified structurally
(indentation, list position, 40-character SHAs) rather than by a parse; the first real run
proves the file.

### The third quick filter is Anniskelu, and it excludes Lapsille (2026-08-30)
Chips are for the two or three intents worth permanent horizontal space. Measured across
3059 showtimes:

| filter | showtimes | share | films |
|---|---|---|---|
| Lapsille *(existing)* | 737 | 24.1% | 36 |
| Suom. puhe *(existing)* | 612 | 20.0% | 22 |
| **Anniskelu** | 528 | 17.3% | 34 |
| IMAX / LUXE / 4DX | 244 | 8.0% | 18 |
| price shown | 133 | 4.3% | 54 |
| K-18 | 120 | 3.9% | 24 |
| 3D | 8 | 0.3% | 1 |
| sold out | 6 | 0.2% | 6 |

Everything from IMAX down is search material, so the haystack gained `method`, `rating` and
`age`: IMAX, LUXE, iSense, Prime, Plus, Senioribio, Perheleffa, Espoo Ciné, K-18 and
Kuvaileva tekstitys (10 showtimes, never a chip, previously unfindable) are searchable.

Lapsille and Anniskelu exclude each other; once both read their own rule the overlap is 0,
so the exclusion guards against a confusing empty state. On restore, Lapsille wins a stored
pair. The Lapsille gate also now checks `age`: an S-rated film in an Annisk_K18 screening
satisfied it (five showtimes, all caught by the genre rule by luck).

The filter reads the documented rule. `fetch_data.py` maps both Finnkino attributes onto
`Anniskelu`: `annisk_k18` (drinks, 18+, sets `age`) and plain `anniskelu` (a permanently
licensed room), and Finnkino states that alcohol is not served at S/7 family films in
those rooms. Of 528 tagged showtimes, 114 are `Annisk_K18`, 396 plain on non-family
ratings and 18 plain on S/K-7 films; the filter drops the 18 (11 of them BioRex, whose
anniskelu semantics are unsettled; applied anyway, since not promising a bar is the safe
direction).

Space: at 375 px the tools row had 78 px free and an "Anniskelu" chip measures 78, so mobile
chip padding went from 11px to 9px. All four chips and the segment sit on one 37 px row in
all three languages. Swedish and English labels are "Bar".

### Seat counts are parsed and deliberately not published (2026-08-30)
README said the app shows "seat availability". It shows a sold-out mark. Finnkino gives an
`isSoldOut` boolean; eTiketti (`Vapaat paikat N / M`) and Riviera (`Varatut paikat: N / M`)
give counts, reduced to `soldOut: free == 0`; everyone else gives nothing.

The counts are thrown away on purpose. The data is refreshed a few times a day, so a count
is up to six hours old when read; "12 vapaata" can be zero by then and would be shown with
the authority of a figure. Sold-out survives staleness better. Do not restore the counts
without solving the staleness. 6 of 3059 showtimes were sold out on the day.

### AGPL-3.0, and why not MIT or GPL (2026-08-30)
Requirements: keep the copyright, stay open, make copiers credit the original. No licence on
GitHub's list requires a visible credit in a running app; MIT, Apache, BSD and the GPLs
require the notice to survive in source and distributed copies only. Asking in the README
is what is available.

AGPL over GPL-3.0 because this is a website: GPL's copyleft triggers on distribution, and
hosting a fork distributes nothing, while AGPL section 13 covers a competing deployment.
AGPL over MIT because MIT gives that fork away. The cost: AGPL deters some users and many
companies ban it, acceptable for a one-author hobby project and not for a library.

- `LICENSE` is gnu.org's text byte-for-byte with the placeholders left as they are. The
  first version filled them in, which was wrong: the licence says changing it is not
  allowed, and GitHub ships the placeholders untouched too.
- The notice is a comment block at the top of `index.html` and the same three lines in
  the README, not on each pipeline script.
- Copyright holder `Shady-Dev`, the GitHub identity.
- The licence covers the code only: showtimes belong to the chains, posters to their CDNs
  and TMDB, Archivo is under the SIL OFL (`fonts/OFL.txt`). The README says so.
- The footer gained a source link, the example section 13 needs; four footer lines, 129 px
  against 110 at 375 px.

### The branding row stops holding a third of the screen (2026-08-30)
The whole `<header>` was sticky, so the logo, language toggle and theme button stayed
pinned for a 45-card list:

| viewport | header | share | list fold | cards fully visible |
|---|---|---|---|---|
| 320x812 | 290 | 35.7% | 522 | 1 |
| 375x812 | 257 | 31.7% | 555 | 2 |
| 390x844 | 257 | 30.5% | 587 | 2 |
| 430x932 | 258 | 27.7% | 674 | 2 |
| 1280x900 | 246 | 27.3% | 654 | 2 |

The sticky moved off `<header>` onto a `.pinned` wrapper around the picker, search, dates
and filters; the branding row scrolls away as ordinary content. No height constant
(`top: -58px` would rot when the row changes), and no layout shift: the header's flow
height is identical before and after at every width. Recovered 58 px on mobile and 66 on
desktop, a quarter-card more of the next film, not an extra film.

Not verified: how it feels while scrolling. The harness browser will not scroll. Real-device
checks still wanted: the row leaving naturally, the pinned strip staying still, Safari
overscroll, the keyboard, returning to the top, rotation.

### Two things left alone on purpose (2026-08-30)
The tools row wraps to two lines at 320 px (header 290 px against 257 elsewhere, one card
whole). Forcing five controls onto one line would cost smaller tap targets, abbreviations,
a scrolling strip or squeezed Finnish and Swedish labels. Revisit only if a real 320 px
device feels cumbersome.

Theme and language are unreachable without scrolling to the top, by design: they are
configuration set about once a month. Do not add a floating theme button or a duplicate in
the pinned strip; that reintroduces the cost v70 removed.

### parseFloat only reads a leading number, so 23 of Orion's 29 prices vanished (2026-09-01, sw.js v95)
Found while checking a claim in this file before pushing it. `priceLabel()` read every
price with `parseFloat`, which takes a number at the start of a string only, so Cinema
Orion's own floor came back NaN and was filtered out as unpriced:

| Orion price string | rows | rendered before |
|---|---:|---|
| `alkaen 10€` | 22 | nothing |
| `alkaen 12€` | 1 | nothing |
| `10€` | 5 | `10€` |
| `8.5€` | 1 | `8.50€` |

No other provider was affected: all 1014 of their price strings begin with the number.

Two questions had been one: what the cheapest price is, and whether to introduce it as a
floor. The number is the first one anywhere in the string (no price string in the data
carries a second, across 1043). The floor is either two different amounts in the list or
anything left in the source string once number, currency and spacing are removed, tested
on shape because the word is in the provider's language; `13 €` stays exact, `alkaen 10€`
does not. The prefix comes from `L[state.lang].from`. The sign stays inside the match:
without it `-5€` matched as `5` and passed the `v > 0` guard, which a test caught.

Eighteen tests through `tests/price_label_harness.js`, with the three `from` translations
read out of `index.html` and one test asserting they differ. The 23-of-29 count is a dated
measurement and nothing asserts it. Seven mutations red.

### Listing data leaves four fifths of showtimes unpriced (2026-09-01)
| | |
|---|---:|
| showtimes with a price on the listing we read | **1,043 of 5,079** |
| showtimes without | 4,030 |
| providers publishing at least one listing price | 27 of 32 |
| unpriced showtimes contributed by Finnkino | 2,333 |
| unpriced showtimes contributed by BioRex | 1,364 |

The provider count flatters it: the two largest chains are among the five that publish
nothing, so showtimes are the denominator. An earlier draft claimed cinemas publish prices
on the booking page; that was not measured, booking pages were not inspected, and the claim
is removed.

The booking flow stays out of bounds: booking, payment and administrative endpoints are
never called and not inventoried, and per-showtime prices would mean about 4,000 extra
fetches at the current cadence against small ticketing platforms. Not looked at: a
visitor-facing price page, which would be ordinary content and could give per-ticket-type
pricing.

### Finnkino publishes no prices outside the booking flow (2026-09-01)
Two backlog entries wanted Finnkino prices and were the same endpoint counted twice. An
earlier draft said the client half was done and that the price cell carried a ticket-type
breakdown in a `title`; both were wrong (the `title` belongs to Cinema Orion's page markup),
and checking found the parseFloat bug above.

The programme response carries no prices: a showtime object is `areaCategories,
attributeIds, eventId, filmAdvanceBookingRuleId, filmId, id, isAllocatedSeating,
isSoldOut, requires3dGlasses, restrictions, schedule, screenId, seatLayoutId, siteId`, and
scanning the whole response for any key containing price, amount, cost, ticket, fee,
tariff or currency returns zero matches. Per-showtime, per-site and bare ticket-type paths
answer 404; four attempts, not inventoried further.

The only route left is the seat-selection flow, which the access rule forbids: blocked by
the repo's own rule, not by difficulty. Open on one possibility: a visitor-facing price
page, not probed. The probe was one `/sites`, two programme reads and four 404s; nothing
raw was written to the repo.

### Seven backlog items closed without building them (2026-09-01)
The backlog had 13 entries. Seven closed without code, each checked against the source
first; 7 remain.

- Genre / format chips: dropped. `haystack()` already folds `genres`, `method`, the rating,
  the age limit and the TMDB genre names in both languages into the search string.
- Sort toggle and past-showtimes option: dropped. "Ajat" is browsing by time. Past
  showtimes are already handled: `renderMovies` shows only `ahead` while a film has a
  future screening and puts the rest behind "Menneet näytökset"; `renderTimes` keeps past
  rows at 45% opacity with `pointer-events:none`.
- Tile / grid view: dropped. A poster-first tile hides when and where a film plays, or
  reprints the card.
- Multi-cinema merged view: fulfilled by "Kaikki Helsinki (12)". An arbitrary set of
  cinemas waits for someone asking.
- Favourites float to top: done. `venueRows()` puts the starred venue or city first under
  its own heading; `tests/test_venue_picker.py` asserts the order.
- 18 px title links: pass 2.5.8's spacing exception by about a pixel. The favourite star
  at 3.25:1 stayed open (whether 1.4.3 or 1.4.11 governs a text-rendered icon).
- A data branch: decided against. 195 of the last 30 days' commits are the pipeline's and
  `.git` is 49 MB against 25 MB of `data/`, but nothing has broken. Pages serves a branch,
  the client reads `data/*.json` from the same origin, and every way out is worse:
  `raw.githubusercontent.com` is forbidden by a hard rule, a Pages build assembling two
  branches puts the traffic path behind Actions scheduling, and splitting off only logs and
  posters reworks `check_runs.py` and `logs.yml`. Branching does not shrink history
  either. Reopen if repository size costs something measurable.

### Two rejected in the same pass
Denser cards (`.movie{gap:14px; padding:16px 0}` against 18px/20px): rejected on
measurement. `.movie` is a flex row, so `gap` does nothing vertically; the padding change
takes the card from 214 to 206 px and the document from 10937 to 10577 px, 3.3 per cent,
without changing the number of fully visible cards at 320, 375, 390, 430 or 1280.

Result count: rejected. Every placement adds a row above the list at the moment the reader
is looking at filtered results, and the number of cards is the film count.

### "Did a run happen" is a different question from "did it fail" (2026-09-01)
`check_runs.py` fails on a non-zero or missing `exit=` in a committed log. It cannot see a
run that never starts (laptop asleep, launchd unloaded, wrapper edited into silence): a log
reading `exit=0` four days ago passes. `scripts/check_staleness.py` reads `data/areas.json`
and exits non-zero when it is older than eight hours, cannot be parsed, or carries a
timestamp that cannot be trusted.

- `data/areas.json` is the file to watch because the local half writes it, and since
  `3189906` it is written with the schedule files rather than before them, so its age
  means "when did a complete publish last happen". A day earlier the monitor would have
  measured the wrong thing.
- Eight hours, strictly greater: `STALE_H` in `index.html`, read by a test so the monitor
  and the banner cannot drift apart.
- A future timestamp fails rather than reading as fresh. A few minutes of drift between
  the writer's and reader's clocks is tolerated; past that the age is not evidence, and a
  future stamp would silence the monitor for as long as the skew lasts.
- An unreadable file is reported as unreadable, never as an age.
- The limit is validated: `--hours inf` and `--hours nan` exited 0 and reported the data
  fresh for ever; a negative limit exited 1 and reported it stale. Both now exit 2,
  argparse's code for a wrong invocation. Zero stays valid.
- Verdict to stdout, failures to stderr, so a wrapper can keep only the complaints. cron
  mails either stream, so quiet-on-success is the wrapper's decision.
- No test reads the committed file. A test against `data/areas.json` passed only while
  that file was fresh; one with `--hours 0` failed when the publisher's clock ran a few
  minutes fast, because a future stamp is clamped to `0.0 h old`. The default path is
  exercised from a temporary directory holding a file the test wrote.

This repo supplies the verdict: a pure function of a file and a clock. The schedule, the
file location and the notification route are machine-specific and live in the wrapper.
The backlog item stays open until the ping exists.

Break-verified fourteen ways, among them `>=` at the threshold, the age check removed,
naive timestamps treated as UTC, the future check disabled, the drift tolerance removed,
an unreadable file reported as fresh, the threshold moved off `STALE_H`, the limit taken
on trust, a bad invocation exiting 1, and failures printed to stdout.

### A page build that dies partway published half a generation (2026-09-01)
`build_pages.main()` wrote each page as it produced it. Each write was atomic, the set was
not: an exception mid-render left the tree holding pages from two generations, and
`biorex.yml` stages and pushes the pages before it checks the exit code, so the mixture
was published. Measured with a perturbed schedule and an exception on the 41st render: 40
of 172 pages new, 132 old, all staged. A city page is built after the venues it merges
and the sitemap after both, so the mixture can serve a city page disagreeing with the
venue pages it links to, and `write_if_changed` leaves the stale half indistinguishable
from a correct page.

Decision: collect the pages as `(path, text)` and write them in one loop at the end, so a
build that raises writes nothing. Batched in the generator rather than gated in the
workflow: `biorex.yml` has an unmerged branch against it, and a failed build now stages
no page changes while the run's fresh data still publishes. Holding the set costs 4.5 MB.

The flush itself is the remaining window (only the disk can stop it), pinned by a test
asserting the error propagates. Enrichment and poster mirroring were left ungated: a page
missing a rating is a correct page with less on it, a page set from two generations is not.

Break-verified four ways: written as produced (6 red), flushed before the city pass (2),
flushed before the redirects (2), the flush wrapped in a `try` (1). The failure-position
test derives its boundary from the venue count; a hard-coded 140 sat inside the venue pass
and let the half fix pass.

### A cancelled cloud run cost two venues every poster (2026-08-30)
Kino Engel and Kino Akseli rendered placeholder tiles for every film for hours. Three
causes lined up: the local half publishes those posters as the cinemas' own URLs and only
the cloud run mirrors them (38 of 38 Engel and 12 of 12 Akseli showtimes remote);
`cancel-in-progress: true` cancelled the run doing the mirroring when a manual dispatch
landed on a scheduled run, and nothing retries; and since v64 the client refuses a remote
poster, correctly. The normal window between publishing a remote URL and the cloud
rewriting it is a 2.7 minute median, 6.9 max; a cancellation stretched it to the next cron.

Two changes: `cancel-in-progress: false`, which keeps runs serialised and lets the queued
run finish; and `build_pages.py` prints the hosts and count of poster references still
remote (`78 poster references were still remote ... johku.com x58, kinoakseli.fi x20` on
the broken data). The state self-heals on any completed cloud run.

### The same asymmetry, one layer up: enrichment (2026-08-30)
After the poster fix, Kino Engel had no score rings: `enrich_tmdb.py` runs only in the
cloud, Finnkino has its own TMDB pass in `fetch_data.py`, and Engel and Kino Akseli had
neither. A local run took 38 of 38 Engel and 12 of 12 Akseli showtimes from a full set of
`tmdbId`, `tmdb`, `votes`, `tr` and `gids` to zero. `gids` drives the genre names and the
id half of the kids filter; `tmdbId` drives cross-chain merging.

Rejected: running `enrich_tmdb` on the local half. It writes three shared files that the
cloud pass also writes, and the wrapper pushes through `git pull --rebase`; a conflict in a
single-line JSON cache cannot auto-merge and would abort the run.

Decision: `run_site` reads the previous venue file and carries the five fields forward by
title, the key the TMDB pass uses. `setdefault`, so an adapter's own value wins and the
next enrichment pass overwrites all of it. This also covers a failed cloud enrichment and
the old trap of running `run.py` locally for a cloud provider, which once stripped 1201
showtimes of `tmdbId`. Four tests, break-verified.

The local half also runs `mirror_posters.py`. It rewrites only references still remote,
so pointing it at the whole `data/` directory touches Engel and Akseli and nothing else.
It needs Pillow: Akseli publishes 1984x2835 key art, 872 kB per poster against 57 kB
downscaled.

`mirror_posters` checks Pillow once, up front, by using it (open, convert, resize, save a
4x6 JPEG), since `from PIL import Image` succeeds on an install with an incomplete imaging
library. A missing or broken Pillow exits `CANNOT_RUN` (3): exit 0 had made "mirrored
everything" and "could not mirror anything" the same answer, and in the cloud Pillow is
installed inside the job, so a broken install would have gone green. A poster that fails
to download stays exit 0 (kinoakseli.fi fails every cloud run by design). No `--optional`
flag: neither caller stops on the exit code, since the cloud commits data before its gate
and the wrapper collects the code and carries on, so exit 0 only hid the degradation.
The wrapper prints `posters: DEGRADED` for 3 and `posters: FAILED` otherwise.

Covered by `tests/test_mirror_posters.py`. The Pillow-absent cases block the import
through `sys.meta_path`; two tests read `biorex.yml` to hold the mirror step recording
`$?` into `mirrorfail` and the gate comparing it to 0. Break-verified eleven ways. The
cases needing a real Pillow skip on the system interpreter; run them from the venv that
has it. That venv's path was written here once and removed the same day: CLAUDE.md forbids
machine-specific detail.

### Finnkino drops the odd character to "?" (2026-08-30)
The Vaiana live-action synopsis published "Catherine Laga?aia" and "Auli?i Cravalho"; both
names carry an okina (U+02BB). It is Finnkino's payload: `®`, `“ ”` and every `ä` in the
same sentence arrive intact, `json.loads` raises on malformed UTF-8, and the one decode in
`fetch_data.py` uses `errors="replace"`, which yields U+FFFD.

A "?" cannot be decoded back (apostrophe, okina, real question mark), so the repair
transcribes rather than guesses. `films-extra.json` already held the same 823-character
sentence from another chain with the okina intact. `synmerge.repair_from_twin` uses a
twin only when it has the same length and differs only where this text has "?"; a twin
that disagrees elsewhere is a different synopsis, and a genuine "Mitä?" is never touched.

- `tests/test_synopsis_repair.py` covers the refusals: a twin that differs elsewhere, a
  broken twin, a different-length twin, no twin, a real question mark.
- The lookup goes through `synmerge.norm()`, the key `films-extra.json` is written with.
- `data/films.json` was repaired in place in the same commit.
- The call site in `fetch_data.py` runs only from an ordinary connection; `[films] N
  character(s) restored from another chain's copy` in `run.log` confirms it.
- Left alone: `watch?v=` in YouTube URLs, and a missing space after a real question mark
  in a provider's prose.

### IndexNow, and what it is actually worth here (2026-08-31)
`scripts/indexnow.py` and `.github/workflows/indexnow.yml` tell IndexNow which generated
pages a push changed. The key is `9510fcf2085e43b89ff8b86a67f75362.txt` at the site root.

Google has never adopted IndexNow; it reaches Bing, Yandex, Seznam, Naver and Yep. It is
still a fit because showtimes are perishable and git records exactly which pages moved.
Across twelve runs the change set is bimodal: quiet runs rewrite 0-23 pages, day rollovers
and new venues 100-151.

- The URL list comes from the commit range, not the generator. `build_pages.py` stays
  offline and deterministic, and the submission stays out of `biorex.yml`.
- Every status letter is a notification: `A`/`M` submit the page, `D` the URL that is
  gone, `R` both sides. The first version filtered out `noindex` pages, which suppressed
  exactly the notifications worth sending; its test "proved" that four new redirects
  should submit nothing.
- The key is a public ownership token, served openly so the protocol can confirm who
  controls the domain. Its one invariant, that the file contains its own name, is checked.
- `on: push` alone would fire only for hand commits: a push made with `GITHUB_TOKEN` does
  not trigger workflows, and the routine data commits are made that way. The second
  trigger is `workflow_run` on "Fetch cloud providers", rather than a PAT or an edit to
  the fetch workflow.
- The data commit is found inside the run's own window, `run_started_at <= committed <=
  updated_at`, newest match. `workflow_run.head_sha` is where the run started, and taking
  the newest bot commit after that time raced: run A publishes and finishes, run B
  publishes, A's notification job then credits A with B's commit.
- Not gated on `conclusion`: the fetch workflow commits before its failure gate, so a red
  run can still have published pages.
- Branch guards on both triggers, written as an event check so it is not null on a push.
- `ref: main` on the checkout is not required (`GITHUB_SHA` is already the default
  branch's tip on a workflow_run event) and stays because the job depends on which history
  it reads.
- Batched at the protocol's 10,000-URL ceiling, so the limit is explicit.
- The range is the push event's `before`..`after`, not `HEAD^..HEAD`, which would drop
  every earlier commit of a multi-commit push. An all-zero `before` falls back to the
  tip's parent. `fetch-depth: 0` for the same reason.
- 200 and 202 are success (202 while a new key is being validated). 400/403/422 are this
  repo's mistake and are not retried. 429, 5xx and a dead socket get three attempts,
  honouring a sane `Retry-After` capped at 60 s. Exhausting them exits non-zero.

Covered by `tests/test_indexnow.py`, each guard break-verified. The key-file invariant was
first proved by hand only; the test was added.

### Provider text could close the JSON-LD element (2026-08-31)
`ld_json()` serialised provider titles, theatre names and booking URLs with a plain
`json.dumps` inside `<script type="application/ld+json">`. The HTML parser ends a script
element at the first literal `</script>` regardless of the type attribute, so a title
containing one would have opened a live script context on a generated page. Found by an
external review; no current provider ships such a title.

Decision: respell rather than sanitise. `&`, `<`, `>`, U+2028 and U+2029 are replaced with
their `\uXXXX` escapes after serialisation, so a consumer parses the identical value. This
matters because the raw title is the key for `normTitle()`, `films-extra.json` and
`tmdb-aliases.json`. U+2028/U+2029 ride along because `ensure_ascii=False` emits them raw
and they are legal in JSON but not in JavaScript source. A global replace is safe because
those characters can only occur inside JSON string values.

Covered by `tests/test_ld_json.py`, including the whole-document property that a page built
from a hostile title contains exactly one `</script>`. Breaking the escape loop turns three
of four tests red; the losslessness test stays green on purpose.

### Where a run's time actually goes, and what could be taken back (2026-08-31)
Measured off one cloud run's committed logs: eTiketti is about 85% of a run, 185 requests
against 9 for Nexxo, 25 for BioRex, 6 for Gilda and 1 for Orion, about 3.5 minutes of
deliberate `sleep=1.2` between film pages.

Per-host pacing is the design and not negotiable. Serialising across unrelated hosts was
never a decision; it is how the loop was written when the module had two sites. The win
is a pool across hosts with the sleep kept within each host.

The first draft said "over sites", which is wrong: two Nexxo hosts serve two sites each,
so a pool keyed on the site doubles the request rate at those cinemas. The unit is the
host; the next entry is what landed. Hazards named here and resolved there: `common`'s
module-level counters, log interleaving, and the HTTP validator cache's per-URL writes.
Conditional GETs do not help: the eTiketti origins answer `no-store`.

### A run reads unrelated hosts at once (2026-09-01)
`run.py` fetches sites on different hosts concurrently and sites on one host one after the
other. `host_groups` groups by `urlsplit(site["base"]).netloc`, one thread per group, so
the sleep inside `fetch_site` still describes what a host experiences. Measured against
`SITES` on 2026-09-01: eTiketti is 17 sites on 17 hosts (16 read by the cloud); Nexxo is
8 sites on 6 hosts, because kinoaurora.fi serves kinoaurora and kinometso and kinohirvi.fi
serves kinohirvi and biosade. Keyed on the site, those pairs would be read at twice their
adapter's pace. `base` rather than `site`: Bio Säde's showtimes come from kinohirvi.fi
while its ticket links go to biosade.fi. Sites with no `base` share one group.

Hazards and decisions:

- Output is buffered per site and replayed in SITES order, both streams into one list, so
  the committed logs read chronologically. This also fixed the old buffering artefact
  where `run-nexxo.log` opened with the eighth site's stderr notice.
- `common`'s counters are locked. Nothing measurably went wrong under the GIL, but that is
  an implementation accident and false on a free-threaded build. The lock also lets the
  Retry-After ceiling be one decision: seconds are reserved before the sleep.
- `_write_slot` uses a per-thread temp name; two threads writing the same URL slot would
  otherwise truncate each other's `<hash>.tmp`.
- `synmerge.merge()` is a read-modify-write of the shared `data/films-extra.json`, called
  per site. It is serialised inside `merge()`, and the winner for a slot two sites fill in
  the same run is the earlier site in SITES order, tracked per run so the result is the
  same at every pool size. Text already in the file before the run is never touched.
  `synmerge.reset()` clears the map between modules. Probed with one slow and one fast
  site: `workers=1` and `workers=2` published different synopses before the fix.
- Everything else `run_site` writes was already single-writer: 57 venue ids and 31
  provider ids, each unique.
- The pool is 8 (`MAX_HOSTS`, overridable with `KINO_MAX_HOSTS`; 1 is the sequential
  path). It bounds this end only: open sockets and bodies in flight, at most
  `MAX_HOSTS * MAX_BODY` = 160 MB. "As many as there are sites" was rejected because it
  would raise the ceiling every time a cinema is added.
- A worker's exception is recorded and re-raised by the reader thread, which is where a
  sequential run would have raised it. Two earlier versions caught `BaseException` per
  site (a `SystemExit` read as a provider failure) or reported it as `not read` (the run
  exited 1 and still published). Ordinary failures stay per site. Teardown cancels queued
  hosts (`cancel_futures=True`) and waits for hosts in flight, so atomic writes finish.

Measured on the first pooled run: the "Fetch cloud providers" step took 186 s against a
562 s median across eight sequential runs (479-626 s), roughly 2.6-3.4x; one sample. Step
durations are job metadata, not Actions logs. Counters were unchanged for the same work
and every provider exited 0. One `run.py nexxo` from an ordinary connection into a scratch
directory matched the committed log; no second run was made to time it.

Covered by `tests/test_run_pool.py`, 22 tests against real localhost servers, and five for
the fatal path; seventeen break-checks red. Not changed: `fetch_site`, the workflow, the
site list. The local half's modules have one site each and read exactly as before.

Nexxo 403s, recorded so they are not blamed on the pool: the last sequential run before
this landed was refused by kinoset.fi, kinohirvi.fi (`Server: openresty`) and
kino-olympia.fi (`Server: Apache`), origin layer, no CF-Ray, while an ordinary connection
read them hours earlier. On 2026-09-05 the same three hosts refused again in the third
cloud run within 41 minutes, a manual dispatch stacked on two earlier runs. Rule until a
third point says otherwise: do not dispatch a cloud run within an hour of one that already
ran.

### Two cloud runs cannot both rebase their data (2026-08-31)
A cloud run with every provider `exit=0` died on `could not push after 3 attempts`: a
`CONFLICT` on about eighty generated JSON files while rebasing onto a `main` that had moved.

Causes. `actions/checkout` defaults to `github.sha`, resolved when the run is created, so a
queued run started on a base two commits old. Generated data files are whole-file
snapshots and cannot content-merge. And a conflicted rebase leaves the tree unmerged, so
attempts two and three died on `Pulling is not possible because you have unmerged files`.

Decisions, each checked against a reproduction: `git rebase --abort` at the top of each
attempt, so the retries are real; `ref: main` on the checkout, so a queued job fetches the
branch when it starts. `-X theirs` was added and removed the same day: it resolves every
conflict in favour of this run's snapshot, which silently overwrites a human change to a
generator or a generated page pushed mid-run. A conflict now fails the job and the human
change survives. `cancel-in-progress: false` stays.

The failure left no trace in committed logs, since the run died before committing;
`check_runs.py` cannot see that class.

### The local half can now announce a failure (2026-08-30)
A failed cloud provider turns its Actions run red; both of 2026-08-30's outages surfaced
that way. The local half runs outside this repo, writes `exit=1` into a log, pushes it and
carries on, and twenty of seventy venues ride on it. `scripts/check_runs.py` reads every
committed `run*.log` and exits non-zero if any did not end `exit=0`; `logs.yml` runs it on
any push that touches a log.

- Both halves already push their logs, so reading them on push is the signal, without
  touching the wrapper or `biorex.yml`.
- A log with no `exit=` line fails: every writer appends one.
- The last `exit=` wins. The first would report a recovered run as failed; the final line
  would call a log unreadable the moment anything prints after it.
- A stale log counts: `run-vista.log` sat at `exit=1` for hours after its module was
  retired.
- Not covered: staleness. A log saying `exit=0` four days ago is the next entry's problem.

Covered by `tests/test_check_runs.py`, each guard break-verified; two tests were rewritten
until they could tell the break from the original.

### Savon Kinot names the venue inside its own room (2026-09-01)
Joensuu showed `TAPIO | TAPIO 4` beside a venue label that already said Tapio, in the app
and on the pages. `aud` is printed verbatim, which is right for the other sixteen eTiketti
sites. Measured: 127 of Savon Kinot's 157 showtimes carry a piped `aud`, 11 distinct
values across six venues:

| raw | venue | rendered |
|---|---|---|
| `TAPIO \| TAPIO 1..4` | Tapio Joensuu | `Sali Tapio 1..4` |
| `MAXIM \| MAXIM 1..3` | Maxim Varkaus | `Sali Maxim 1..3` |
| `KUVALIPAS \| KUVALIPAS` | Kuvalipas Iisalmi | *(empty)* |
| `KUVALINNA` | Kuvalinna Savonlinna | *(empty)* |
| `KILLA` | Killa Savonlinna | *(empty)* |
| `KINO-HOVI` | Kino-Hovi Kitee | *(empty)* |

Empty for single-screen houses is the family's convention: eight other eTiketti cinemas
publish `aud` as `""`. The name stays with the number (`Sali Tapio 4`, not `Sali 4`) because
a city page lists four cinemas; the casing comes from the registry's `short`. Not a rule for
eTiketti: Leffabuumi pipes too (`KINOLINNA | SALI 1`) and means a real room in one of three
buildings. The normaliser is opt-in per site, `aud_repeats_venue`, set on exactly one
entry, and a test asserts the list is `["savonkinot"]`. Fixed at the parser, since both
consumers read the same field. An unrecognised room is returned unchanged.

No data was regenerated: `run.py` takes a module, so refreshing Savon Kinot alone would
fetch all seventeen eTiketti hosts. The next cloud run replaced the files. Eight mutations
red.

A trap found on the way: a plain `import etiketti` at the top of the new test file turned
three unrelated tests in `test_empty_programme.py` red. Provider modules do `from common
import EmptyProgramme` at import time, and `test_common_fetch.py` calls
`importlib.reload(common)`, which builds a new class; a module imported before the reload
keeps the old one, so `assertRaises(common.EmptyProgramme)` and `run.py`'s handler stop
recognising it. Worked around by importing inside a function; the real fix is at the reload
boundary.

### Savon Kinot left Vista for eTiketti (2026-08-30)
The cloud run went `exit=1` on `vista`: `HTTP Error 404` from `www.savonkinot.fi`, from an
ordinary connection too, while the site served 200. The homepage carried `etiketti.app` and
`/elokuvat/{id}/{slug}` links: a platform migration. The fix was a `SITES` entry; 17 films,
54 screenings verified before and after.

- The venue ids are the ones `vista.py` used, byte for byte (`sk-tapio`, `sk-killa`,
  `sk-kuvalinna`, `sk-kuvalipas`, `sk-maxim`, `sk-kinohovi`): they key the saved home
  cinema in `localStorage` and every `/teatteri/` URL.
- The deployment is the Leffabuumi shape: the town is the place and the cinema is in the
  room field, `JOENSUU | TAPIO | TAPIO 3`; `match` runs against the two joined.
- `vista.py` keeps its parser and loses its sites (`SITES = []`), so `registry.modules()`
  no longer names it and `run.py vista` exits 0. The "Vista sweep" entry's one Finnish
  deployment is now zero.
- `run-vista.log` was deleted with the sites: a retired module's log would sit at `exit=1`
  forever in the one place a sweep for failures looks.

### The Nexxo sweep: six cinemas, and two hosts that are not what they look like (2026-08-30)
Six more cinemas on the adapter that served Kinoset: 25 chains to 31, 64 venues to 70,
measured into a throwaway directory first (9 venues, 102 showtimes, 0 failures).

Two of the ten probed hosts were not separate cinemas: `ksek.fi` and `kinoaurora.fi` are
one deployment (identical payloads at locationid 1 and 2), and adding both would have
published every showtime twice under two chain names in one city. `kinohirvi.fi` serves Bio
Säde on locationid 4, in Mänttä, 80 km from Kino Hirvi; `biosade.fi` serves an empty
programme while its schedule is published on another host. A host list is not a venue
list; ids were discovered by asking the endpoint.

- Orange, the intuitive accent for Kino Aurora, measures 4.7 dE00 against Finnkino's in
  Jyväskylä; indigo at 63.7 instead.
- `book="reserve"` for all six: Nexxo publishes no per-show booking URL.
- `common.EmptyProgramme` is raised here too: `biojukola.fi`, `biosalo.fi` and
  `biostara.fi` answer with valid JSON and no shows, permanently, and are not added.
- Deferred, then done 2026-08-31: Kino Metso, a touring operation whose `roomTitle` values
  are towns, needs the room-splitting `match` eTiketti has.

### Kino Metso: five towns on one locationid (2026-08-31)
KSEK's touring cinema, added as four venues that share `kinoaurora.fi` locationid 2. A
venue entry takes a `rooms` list of roomIds; `fetch_site` fetches each locationid once and
parses it per venue.

- Its home is ksek.fi: `ksek.fi/kino-metso/{town}/` exists per town and filters the plugin
  by the same roomId, verified 200 with showlist markup before writing. The site entry
  carries `site` (ksek.fi) beside `base` (kinoaurora.fi), and a venue with a `page` links
  to its own town's page.
- Matching is on `roomId`, never `roomTitle` (Muurame 2, Petäjävesi 4, Tikkakoski 11,
  Vaajakoski 12, Riihivuori 21, Hankasalmi 19).
- Riihivuori folds into Muurame (a resort hill in the municipality, no page of its own);
  Vaajakoski and Tikkakoski read as Jyväskylä, so they join its combined view.
- Hankasalmi and Laukaa are not added: pages exist, programme does not. Rows no venue owns
  are printed as `unclaimed room {id} "{title}": N showtime(s) not published`, which is how
  a new town announces itself.
- Accent `#227D63`, worst same-city deutan pair 26.9 dE00 in Jyväskylä; the intuitive olive
  scored 6.3.

Covered by `tests/test_nexxo_rooms.py`, each guard break-verified. Two test traps: the
empty-programme tests patched `fetch_venue`, which the one-fetch change no longer calls, so
they now patch `fetch_payload`; and `test_common_fetch`'s `reload(common)` rebinds
`EmptyProgramme`, so nexxo references it through the module.

### The Nexxo sweep shipped six dead ticket links (2026-08-31)
A reader in Järvelä reported a 404 ticket link. The sweep copied Kinoset's `programme:
"/ohjelmisto/"` onto every site without fetching it; only Kinoset has that page, so every
showtime link for six of seven Nexxo providers was dead from day one. The API is the
platform's and identical everywhere; the visitor-facing page is each site's WordPress.

Paths verified live for the plugin's showlist markup: Kino Aurora and Kino Olympia
`/naytokset/`, Kino Marilyn `/esitysajat/`, Järvelän Kino `/naytoslista/`, Kino Hirvi and
Bio Säde the front page. Bio Säde needed a second base: its front page renders the
location-4 schedule by calling kinohirvi.fi's API, so the entry carries `site` (biosade.fi)
beside `base` (kinohirvi.fi). The missing check costs one request per site and no offline
test can hold it. A dispatch followed rather than a wait for the cron.

### A quiet week is not a broken parser (2026-08-30)
"A whole site parsing zero showtimes fails the run" catches a silently broken parser, and
after the eTiketti sweep eight sites are a single small venue (K-Kino 3 showtimes, Kino
Saimaa 2), so a quiet week turned the run red.

`common.EmptyProgramme` may be raised only after a listing was fetched and parsed and held
no films. A listing with films whose parse yields no showtimes keeps failing.

- No per-site "allow empty" flag: it would switch the check off permanently for the site
  most likely to need it. Emptiness is decided per run.
- An empty site writes no `venues-{provider}.json`, so the health line ages rather than
  going green on an empty answer.
- Previously published data is kept, since the discriminator can be wrong.
- The log line is `[provider] no programme published: ...` and the summary counts them.
- One break did not go red: removing `not venues` from the exit condition changed nothing,
  because an all-empty site is already counted earlier. That clause guards a module with
  no sites for this half, which must exit 0; it had no test until the break said so.

Covered by `tests/test_empty_programme.py`. Only `etiketti` raised it at the time; Nexxo
followed.

### Routing is per site, not per module (2026-08-30)
`where` on a registry entry decided which half fetched a whole adapter, so marking one
eTiketti provider local would have put all sixteen sites in both halves with two writers on
the same files. That is why Joutsan Kino was deleted, which was the wrong answer.

`run.py` filters `SITES` by each site's provider `where`.

- The half is derived, not passed: Actions sets `GITHUB_ACTIONS`, so the cloud workflow's
  bare `run.py <module>` keeps working without an edit to `biorex.yml`.
- Off Actions the default is `all`: `run.py etiketti` on a laptop exercises the adapter.
  The local wrapper says `--where local`, which keeps one writer per provider file.
- A site whose provider has no registry entry is kept in both halves;
  `tests/test_registry_sites.py` reports it.
- `tests/test_run_routing.py` asserts against the live registry that the halves are
  disjoint and complete.
- `run.py etiketti --half local` took `local` for a module name; `module_names()` is fixed
  and tested.
- The wrapper needs `run.py --where local` for the eTiketti module, or Joutsan Kino
  publishes nothing.

Joutsan Kino was fetched from an ordinary connection and committed with this change; its
posters stayed hot-linked until a cloud run mirrored them.

### Measuring when cinemas publish (2026-08-30)
`scripts/poll_windows.py` reads committed data and walks every pair of consecutive data
commits, reporting when new schedule data first became visible, so polling slots can follow
the publication rhythm.

Its first three runs reported 125, 20 and 4 arrivals over one history; the difference was
its own bugs, now fixtures in `tests/test_poll_windows.py`:

- ISO strings are not comparable across offsets: the local half commits `+03:00` and the
  runner `+00:00`. Starts are epoch seconds.
- The weekday was the committer's, not the cinema's. Everything is normalised to
  `Europe/Helsinki`.
- An adapter commit usually touches no data file, so the Orion parser landing read as Orion
  publishing 27 screenings. The check covers the whole range since the previous observation.
- A venue whose file is momentarily empty names no provider, so `seen` stopped advancing.
  Venues are attributed globally and first-population is tracked explicitly.

First-seen titles are the weakest signal; the primary measure is future screenings added
between observations, keyed `venue + title + start + aud`, plus horizon extension. Every
row is an observation window, never a publication time, and can never be narrower than the
polling interval. As of 2026-08-30: 9 organic arrivals over 4.4 days, too few to set
anything by.

### Finnkino publishes weekly, Tuesday ~15:00 -- their own statement (2026-09-01)
Finnkino's site: the new programme, Friday through the following Thursday, goes on sale no
later than about 15:00 on Tuesdays; a holiday can push it a day; special cases sell
earlier. The committed data on the morning of Tue 2026-09-01 matched:

    Finnkino, most venues      horizon 2026-09-03    2 days out
    Finnkino 1101 / 1100       horizon 09-06 / 09-07 the "special cases" selling early
    twelve non-Finnkino venues horizon 2026-09-30    29 days out
    eTiketti tail              out to 2026-12-20

A 2-day Finnkino horizon beside a 29-day small-cinema horizon is Finnkino not having sold
the weekend yet, not under-fetching. Prediction: after ~15:00 on a normal Tuesday the
Finnkino horizons jump a week.

For the weekly drop, read the showtime-count signal, not horizon, which a single
advance-sale screening drags. A local slot shortly after 15:00 Helsinki on Tuesdays would
be the highest-value fetch of the week; deliberately not done on a sample of one, and
Finnkino is local-only so the slot lives in the out-of-repo wrapper. Not surfaced in the
UI: promising one chain's policy on behalf of all would break on holidays and special
cases.

## Access and ethics
- Every provider is read through the same public interface its own site uses, on a
  schedule no visitor can influence, and every showtime links back to the cinema's own
  page. The client reads static JSON from this origin and never calls a cinema, so
  browsing produces no request. The cadence is not enforced: normally four runs a day for
  the local half, and for the cloud a four-times-daily cron plus one run after every local
  run, usually up to eight. `workflow_dispatch` can push it higher and scheduled execution
  is best-effort. This said "four times a day regardless of traffic" until 2026-08-30,
  which had never been true of the cloud half; a promise to a cinema has to be one the
  configuration keeps.
- Datacenter-IP blocks are a deliberate access control. Reading a site from an ordinary
  connection is fine; residential proxies, fingerprint spoofing and credentials that were
  never issued are not, and none are used.
- Booking, payment and administrative endpoints are never called and not inventoried here.
- Never commit a raw probe dump (2026-08-27): `probe/rv-films.html` contained
  rivieracinemas.fi's Google Maps JS key and tripped secret scanning. The key is public by
  design and there was nothing to rotate, but an alert queue full of other people's keys
  teaches you to ignore alerts. Probe, read, write the finding here, commit nothing raw.
  `.gitignore` blocks `probe/` and `probe-*`.
- If a cinema would rather not be included, the adapter comes out: one registry entry.
- The visitor's browser matters too. The README claimed "no third-party requests" while
  the typeface came from Google Fonts and 1523 of 4279 poster references (36%, 2026-08-28)
  were hot-linked from the cinemas' CDNs and `image.tmdb.org`. Both are closed now; see
  the two entries below.

### Posters are mirrored (2026-08-29)
`scripts/providers/mirror_posters.py` runs after enrichment and before `build_pages`,
downloads every hot-linked poster into `data/posters/` and rewrites the `img` reference on
each show and in `films-extra.json`.

- The count was wrong by an order of magnitude: "1523 of 4279" counted references, not
  files. The data held 194 distinct remote URLs against 3494 references, a ~5 MB job.
- Everything is downscaled to 342 px wide: TMDB serves w342 at ~25 kB, MyCloudCinema only
  1080, Nexxo and Kino Akseli 1984x2835 key art. Pillow is installed in the workflow for
  this only.
- Named `sha1(url)[:16]`: seven hosts with no id namespace in common.
- A failure is logged and left hot-linked; a third party's uptime must not stop the
  pipeline publishing.
- Kino Akseli's posters mirror from a runner: the datacenter challenge is on its pages, and
  `wp-content/uploads/` served all six. "The site blocks datacenter IPs" is a claim about
  the endpoint that was tested.
- Nexxo publishes filenames with spaces, which urllib rejects; `fetch` goes through
  `request_url()`, and the cache key stays the published URL.
- The first run after this rewrote nearly every generated page as the `<img>` tags appeared.
- Open: nothing prunes a poster once its film stops screening; a few MB a year.
- `/data/` is disallowed in `robots.txt`, so the mirrored posters were unfetchable by
  Googlebot until `Allow: /data/posters/` overrode it.

### The webfont is self-hosted (2026-08-29)
`fonts/archivo-latin.woff2` (90 kB) and `fonts/archivo-latin-ext.woff2` (86 kB), with the
`@font-face` rules inlined in `index.html`. Google Fonts was the last third-party request.

- The same two subsets Google serves a modern browser, unicode-ranges kept verbatim, so
  latin-ext is fetched only by a page that needs it. Only latin is preloaded.
- The subsets came from a throwaway workflow, deleted in the commit that used its output.
- Licence in `fonts/OFL.txt` from Omnibus-Type/Archivo. The first attempt committed a
  14-byte "404: Not Found" as the licence file; check the size of anything fetched blind.
