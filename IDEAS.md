# Kino — Improvement Ideas

## Current backlog

The 8 items still open, with the section that holds each one and its reasoning. Presence
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
The 12 h JWT problem is gone: the token is fetched fresh at run time and used within
seconds, so nothing has to survive expiry.

- The local wrapper: get token → `scripts/fetch_data.py` →
  `scripts/providers/run.py kinoakseli` → `git push` data/*.json + posters +
  `run.log` + `run-kinoakseli.log`, then dispatch the cloud workflow
- Both fetchers run inside a `set +e` window with `echo "exit=$?"` appended to their
  own log, and `set -e` resumes only afterwards. So a Kino Akseli failure cannot
  abort the push or take fresh Finnkino data with it. Same shape as the cloud workflow.
- Line 10 is `git fetch -q origin main && git reset -q --hard origin/main`: the working
  tree is **discarded at the start of every run**, so any manual edit inside `repo/` is
  destroyed at the next slot, because the wrapper hard-resets the clone to `origin/main`
  before every run. The wrapper lives outside the clone, so it survives. Test edits belong
  in a separate clone.
- The TTL guard runs *before* `cd repo`, so a bad Finnkino token aborts the whole script
  including Kino Akseli, which needs no token. Only worth changing if Kino Akseli is ever
  seen going stale for a reason unrelated to itself.
- The token is obtained from a real browser session on the local machine and handed to the
  fetcher, which uses it within seconds. A TTL guard refuses
  to proceed on a token with too little life left.
- Scheduled locally four times a day. There is no cloud fallback, deliberately.
  `.github/workflows/fetch.yml` was deleted on 2026-08-27: it could not succeed from a
  runner, because `www.finnkino.fi` answers Cloudflare 403 to datacenter IPs, so no token
  can be obtained there — and the stored `FINNKINO_SECRET` it fell back on was a JWT that
  is stale within 12 hours. It had therefore failed on **every push for at least two
  days**, which is worse than having no fallback: a workflow that is always red hides the
  one that just broke. It cost a round trip today to tell an unrelated change apart from
  that noise. If Finnkino data goes stale the app already says so — the per-provider health
  line turns amber past 8 h and the stale banner fires — so the outage is visible in the
  place a visitor actually looks.
- Finnkino's site is not reachable from a datacenter IP, which is why this half of the
  pipeline runs at home rather than on a runner. See "Access and ethics".
- `get_token()` reads `FINNKINO_TOKEN` from the environment first — that is how the local
  wrapper injects the browser-fetched token, so **that path must not be removed**. The
  direct-fetch fallback below it only works from an ordinary connection.

**Machine setup, schedule, token retrieval and credentials live in local private notes,
not here.** This file documents architecture and data contracts. It is not a runbook for
getting at anyone's site.

Superseded: an approach that pushed the token into repository secrets and rotated it.
It worked, but rotating a secret is pointless once the token is obtained per run. The
leftover `FINNKINO_SECRET` is what kept the dead Actions workflow half-alive; delete it in
repository settings (a fine-grained PAT cannot, secrets need their own permission).

## Multi-provider — current state

Goal: good coverage for everyone, including small towns — not just the big chains.
Shape: **one adapter per provider, or better per *platform*, each running where it can.**

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

Ratings and trailers come from the shared TMDB enrichment pass, so what still differs
between providers is what the source itself gives: eTiketti and Riviera publish real seat
counts, Finnkino a sold-out flag and no counts, and the rest nothing at all. Only the
flag survives into the data -- see "Seat counts are parsed and deliberately not
published".

74 venues / 52 cities across 32 providers. Each provider writes `data/area-{venueId}.json` in one shape
(`{generated, dates, horizon, shows[]}`) plus `data/venues-{provider}.json`
(`{id, name, short, city}`). Finnkino still uses `data/areas.json` with numeric ids.
Adding a provider to the frontend is now nothing: a registry entry generates
`data/providers.json`, and the client derives every label, host, accent and footer verb
from it.

Conventions worth keeping:
- **An age limit can belong to the screening, not the film.** A licensed bar auditorium
  admits 18+ whatever the film is rated: BioRex sells K-12 films into `Anniskelu`
  screenings, and at Seinäjoki states it in the room name itself ("2 REX (K-18)"). So
  `age` is a per-show field, separate from `rating`, set from an explicit `(K-nn)` in the
  auditorium name first and inferred from the Anniskelu tag otherwise. The client renders
  it on the showtime stub, which is the thing you tap to book, and suppresses it when
  it merely repeats the film's rating. Rendered as an outlined chip (`.agelim`), a sibling
  of `.fmt` — **not red, and not KAVI's official symbol**. That artwork denotes a legal
  age classification, which this is not: "Spa Weekend" is classified K-12 and the 18+
  comes from the room, so borrowing the official styling would assert a rating that does
  not exist. A red chip would also sit inside stubs whose left rule is already Finnkino
  orange or Kotkan Leffat crimson, competing with the only job colour has here. Shape and
  weight instead, which also survives greyscale and colourblind vision. The room name
  truncates under the stub's 130 px ellipsis; the chip is `flex:0 0 auto` so it cannot be
  the part that gets eaten.
- **Two glyphs, and only two** (2026-08-27). `Ⓐ` for anniskelu and `18+` for the
  screening's age limit, on stubs only; the card keeps the words, because there is room
  there. The case for a glyph is space, not decoration: a stub's label column is about
  75 px and truncates, and "Anniskelu" eats a third of it. `LUXE`, `iSense`, `IMAX` and
  `2D` stay words — they are brand names a visitor already reads, and an invented icon
  for each would need a legend entry to say less than the word does. Strands stay words
  for the same reason. Monochrome, drawn with `currentColor`: inside a stub the chain
  rule is the only thing allowed to carry colour. Every glyph has a `title` and an
  `aria-label` with the Finnish word, and `tagKey()` renders a legend **only when the
  day's shows actually carry the tag**, so it never explains something off screen.
- **The calendar chip must not keep a date it no longer owns** (2026-08-27). Pick 19.9.
  from the picker, then tap a quick chip: the quick chip took the `.active` class but the
  calendar chip kept reading "La 19.9.", so it looked like a shortcut back to that date
  and instead reopened the picker. `resetCalChip()` restores the 📅 face whenever a quick
  chip takes over, from its own handler and from `selectDay()` (which the next-day link
  and the auto-advance also use). The chip shows a date only while that date is the one
  being viewed.
- **A stub names the cinema, not the district** (2026-08-27). Stubs used the bare venue
  `short`, and half of those say nothing about which chain: "Punavuori" and "Kallio" are
  Helsinki neighbourhoods, "Tripla" and "Redi" are shopping centres, "Kamppi" is both.
  The chain colour was silently doing the identifying, which breaks the rule that colour
  never carries meaning alone — and it collapsed completely once the tint was gated on
  two chains being present, because a day served by one chain then had neither colour nor
  legend nor chain name. Combined views now use the chain-prefixed label from `labelOf()`
  ("Riviera Punavuori"), which already omits the prefix when the short starts with the
  chain, so nothing becomes "Finnkino Finnkino Itis". Single-venue views are unchanged:
  there you picked the cinema.
- **The tint stays on in every combined view, including single-chain days** (2026-08-27,
  after a brief detour). It was gated on two chains being present, because colour with no
  legend explained nothing on 19.9. — but that treated the symptom. The fault was the stub
  label failing to name the chain, and once the label carries it ("Riviera Punavuori") the
  colour no longer carries the distinction. Keeping it on then has value: a palette only becomes
  learnable if it is always present, and the app looks better for it. The legend keeps
  the two-chain rule, since a one-item chain filter filters nothing.
- **Glyphs need their own column.** Trailed after the label they landed wherever the text
  happened to end — a different spot on every stub, and on a two-line label they dropped
  onto a line of their own under "Plus". `.glyphs` is `margin-left:auto`, and in the grid
  it is top-aligned, so a row of stubs has its glyphs level on one line no matter how long
  each label runs.
- **A stub label must not repeat the room name.** It was reading
  "Tennispalatsi · LUXE 8 · 2D · LUXE": the auditorium already carries the format. A tag
  the `aud` string contains is dropped, and plain `2D` is dropped outright — it is on
  nearly every screening, so it carries no information; IMAX, 3D and iSense are the
  exceptions a visitor is looking for and they survive.
- The key sits **in the sources line at the foot of the page**, not under the chain
  legend. Above the list it read as a second key row competing with the chain one, and it
  is largely redundant anyway: the word it decodes is already on the card as a pill, in
  the times view's meta line and in the sheet, so the glyph is explained next to itself in
  every view. The footer is where the app already keeps reference material.
- **Finnkino states the rule outright** (finnkino.fi/leffaherkut/anniskelunaytokset/):
  anniskelu screenings are K18, *except* screenings held in **anniskelualuesalit**, which
  the age limit does not cover — and in those rooms alcohol is not served at S/7 family
  films. That is precisely the two attributes: `Annisk_K18` is an anniskelunäytös and
  carries K18; plain `Anniskelu` marks an anniskelualuesali, a permanently licensed room,
  and carries no age limit. Our mapping matches, and the data agrees with the text: plain
  `Anniskelu` appears on S- and K-7-rated films (the family screenings that room hosts
  without service), `Annisk_K18` on films of any rating including S.
- **`Anniskelu` does not mean 18+ — settled by the data, and the BioRex inference is
  gone** (2026-08-27). Finnkino's Anniskelu screenings by film rating: K-12 334 plain / 83
  K18, K-16 116 / 43, **S 8 plain / 5 K18**, K-7 2 / 1. Two conclusions. Plain `Anniskelu`
  covers S- and K-7-rated films, so it cannot mean minors are barred; and `Annisk_K18`
  appears on S-rated films too, so the 18+ marking belongs to the screening and is
  independent of the film's classification. Finnkino's help centre also says drinks are
  not served at S/7 family screenings even in a licensed room, which together with those
  8 S-rated plain tags suggests the word marks *the auditorium is licensed* rather than
  *drinks at this screening*.
  `biorex.py` therefore no longer infers `K-18` from the tag — it had put the badge on 99
  screenings including an S-rated documentary, telling people a screening was closed to
  them when it was not. Only an explicit `(K-nn)` in the room name sets `age` now. Bring
  the inference back only with a citation from BioRex saying their anniskelu screenings
  are 18+. Note Finnkino's own model has it both ways depending on the room, so BioRex's
  "Anniskelu · Plus" rooms are as likely to be permanent licensed areas (no age limit) as
  restricted screenings — which is the reading their Seinäjoki rooms support, since those
  are marked "(K-18)" separately and explicitly.
- ~~**`Anniskelu` does not mean 18+.**~~ (superseded by the entry above) Finnkino's help centre is explicit: the mark means
  drinks bought at the bar may be taken into that screening, those auditoriums count as
  restaurant premises in law, and the separate **`K18 Anniskelunäytös`** is the one minors
  cannot attend — alcohol is not served at S/7 family screenings even in a licensed room.
  The data agrees: 608 of 2756 Finnkino showtimes carry `Anniskelu` (all 35 at one venue)
  against 145 carrying `Annisk_K18`. So only `Annisk_K18` sets `age`. **This casts doubt
  on the BioRex inference** that any Anniskelu tag means K-18, which currently puts a
  K-18 badge on 99 screenings including an S-rated documentary. Their only hard evidence
  is Seinäjoki's room named "2 REX (K-18)" — their own words, and that screening carried
  no Anniskelu tag at all. Over-claiming tells someone a screening is closed to them when
  it is not; verify with BioRex before keeping it.
- **`method` is per-showtime and must not be rendered per-film.** 47 film/day
  combinations at a single venue mix an Anniskelu screening with normal ones, and the film
  card used to inherit the *first* showtime's tags, so "ANNISKELU" appeared above
  showtimes that were not bar screenings (or vanished from ones that were). The card now
  shows only tags every showtime shares; the rest move onto their own stub rather than
  disappearing, so one IMAX screening among 2D ones still says so.
- Normalise `lang` to Finnkino's tags (`FI-A`, `FI-S`) so the "Suom. puhe" filter works for
  every provider with no frontend change
- Event/venue tags (Anniskelu, Plus, SenioriKino, Perheleffa) go in `method`, rendered as
  pills on the card when shared by every showtime and on the stub when not
- Blank `aud` when the room name just repeats the venue (single-screen sites)
- **Chain accents are chosen against the set, not picked one at a time** (2026-08-27).
  Every chain sharing a city has to be separable in normal *and* red-green colourblind
  vision, because the 3 px rule is the only visual cue distinguishing a Finnkino stub
  from a BioRex one. The old palette had three warm chains in Helsinki, so BioRex left
  its own gold for blue and Gilda left brick red for magenta, and Kino Akseli took the
  vacated gold: it is a single-screen house in Nummela and never appears in a combined
  city view, so it cannot clash there. Eleven chains cannot all be mutually distinct
  under colourblind vision while staying this side of neon, so the target is per-city
  separation, not global.
  **Every number this bullet used to carry was wrong and has been removed**; see
  "The accent numbers, re-derived" below. The reasoning above survives the correction,
  which is why it is still here. Run `scripts/accent_check.py` for the current figures
  rather than quoting any that are written down.
- A failed venue writes no file, keeping previous data rather than publishing empty
- Verify the response belongs to the venue you asked for (see the BioRex cookie note)

### Combined city view (done)
- Dropdown gets `city:{name}` entries for cities with 2+ venues: Helsinki (11, five chains),
  Espoo (2), Tampere (2), Kotka (2).
- `loadCity()` fetches each venue file in parallel and folds them into one payload;
  `dates`/`horizon` are the union, `generated` the oldest so the stale banner reflects
  the weakest link. A venue that fails to load is skipped, not fatal.
- The payload also carries `oldest`, the provider `generated` came from. The banner used
  to name the provider via `venueIndex[state.area]`, which has no entry for a `city:` key,
  so every combined view fell through to the Finnkino fallback and blamed the chain that
  refreshes most often for another chain's stale file. Naming the wrong source is worse
  than naming none: it sends the reader to check something that is fine.
- Identity: each show's `eventId` is rewritten to `mergeKey(title)`, which strips
  `2D/3D/IMAX/4K`, `(suomeksi)` and `, suomeksi` before normalising. So "Spider-Man: Brand
  New Day 2D" (Kotka) merges with the plain title (BioRex), while "Dyyni: Osa kolme" stays
  distinct from "Dyyni". The provider's own id is kept as `_eid` — films.json is keyed by
  Finnkino's filmId and has to be reached through it.
- Differentiation: venue `short` name in every stub + 3 px left border per chain + a chain
  legend above the list and in the sheet. Never colour alone. Stubs switch to a CSS grid
  (`auto-fill minmax(168px,1fr)`) so times line up and long venue names stop truncating.
- Auditorium names stay verbatim ("2 Plus", "LUXE 4", "Sali 7") — that is what is printed
  on the ticket, so normalising them would make them harder to match on arrival.

Still open:
- TMDB id as a real `film_key` in the data (the client-side title merge works, but an id
  would be exact). Needed if titles ever diverge more than the suffix rules cover.
  Finnkino `filmId` and BioRex `movieId` are different namespaces, so the same film would
  render as two cards. Also gets BioRex/Kinoset/Akseli their ★ and trailers.
- "Kaikki {city}" entry, only for cities with 2+ venues (Helsinki 6, Espoo 2, Tampere 2),
  plus one curated "Pääkaupunkiseutu" (Helsinki+Espoo+Vantaa = 9).
- Merged views: 3 px left border per chain (Finnkino red, BioRex gold #d69727) + venue
  `short` in the stub's second line. Never colour alone. `render()` already has a
  `multiTheatre` flag doing venue-labelled stubs.
- Sparse-date dimming: `dates` makes it possible, but `<input type="date">` cannot disable
  individual days — needs a custom picker.

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
The score is a ring: arc length for the glance, the number inside for the value, and the
vote count beside it, because 7.1 from 41 votes and 7.1 from 15 000 are not the same
claim and a bare star cannot tell them apart. A rating under `VOTE_SOLID` = 25 votes is
dimmed rather than hidden, so the reader discounts it instead of the app silently
deciding for them.

Two deliberate departures from TMDB's own widget:
- **One hue, not green/amber/red.** This app already spends colour on chain identity; a
  second colour language competing with it costs more than it explains, and a
  red-vs-green score is the classic colourblind failure. The arc and the number both
  carry the value, so it survives greyscale.
- **Not a copy of their component.** We use TMDB's data, not their badge. Looking like
  their widget would imply an endorsement we do not have.

**IMDb was the better source and is not available.** `title.ratings.tsv.gz` is free, daily
and non-commercial, but IMDb's own terms name "where/what/how to watch applications" as a
commercial use case needing a licence — which is exactly what this is, ad-free or not.
Trakt (free non-commercial API, user ratings with counts) and Leffatykki (Finnish user
ratings) are the unexplored alternatives; both need a licence read first.

- **A rating needs votes.** `vote_average` was written straight through, so a festival
  premiere with three votes showed a clean ★10 or ★5, which reads as a verdict. Ratings
  now come from the movie detail call (authoritative, and already fetched for the
  synopsis) and are stored only above `MIN_VOTES` = 25. The count lives in the cache as
  `n`, so the threshold can be retuned without re-fetching, and held-back ratings are
  listed in the log as **rating held back**.
- The cache was rebuilt once when `pick()` landed: an id chosen by the old picker cannot
  be re-judged, since nothing recorded which hit it came from. An entry with no `n` is
  treated as incomplete, so any future gate change costs one re-check pass, not a wipe.
- **The search loop must not stop at the first candidate that returns anything**
  (2026-08-27). `queries()` yields the cleaned title, then its head before a dash or
  colon, then the raw title. The loop broke on the first candidate with any hits, so
  "Die Hard 2 - Die Harder" returned *Die Hard* on candidate 1 and candidate 2
  ("Die Hard 2", which matches exactly) was never tried. `pick()` can only rank within
  one candidate's results, so it could not save this. Now every candidate is tried until
  one matches exactly, and the first hit of any kind is kept as the fallback. Extra
  requests are spent only on titles that match nothing exactly.
- **Film identity across chains is the TMDB id, not the title** (2026-08-27). BioRex
  publishes "Mutiny", Finnkino "Mutiny - Lavastettu syylliseksi", so the combined city
  view listed one film twice, with two ratings fetched hours apart by the two passes.
  Both passes now write `tmdbId` onto each show and `mergeKey()` in the client prefers
  it. **Only an exact match is written** (`x` in both caches): a weak id would fold two
  different films into one row, which is worse than two rows. Extending `mergeKey()` to
  drop everything after a dash was the obvious alternative and is wrong — it would merge
  "Mission: Impossible - Dead Reckoning" into "Mission: Impossible".
- **Reissue markers belong in `mergeKey()`, not just in the search.** BioRex ships
  "Autot (re-release)", Finnkino "Autot (uudelleenjulkaisu)" — the same reissue labelled
  in two languages, so the combined view listed it twice. `mergeKey()` now strips
  `(re-release)`, `(uudelleenjulkaisu)` and `(uusi kopio)` alongside `(suomeksi)`, and
  `PAREN_NOISE` gained `uudelleenjulkaisu` so both passes strip the same vocabulary.
  Reissue labels carry no sequel information, which is why they are safe to drop where a
  subtitle after a dash is not.
- **Name merging is still required.** Merging by `tmdbId` only helps films where *both*
  chains got an exact match, and the films that miss are exactly the Finnish distributor
  titles most likely to be spelled differently by different chains. So the `mergeKey()`
  strip list has to stay current; it is not superseded.
- **Finnkino publishes the bar-screening attributes too**, and they were being dropped.
  The `[attrs] dropped, neither format nor language` line added for exactly this purpose
  answered it on the first local run: `Annisk_K18 | Anniskelu | EventCine | Maxim |
  Pkseutu | SEVERAL | TKU & R | Tampere | Varaus20`. `EVENT_ATTRS` now keeps the first
  three; `Annisk_K18` states the 18+ rule outright and sets `age`, so Finnkino gets the
  same screening-level limit as BioRex. The rest are marketing and region codes and stay
  dropped — still logged, so the next new attribute cannot vanish silently either.
- **The release-year filter defeats aliases and reissues.** `Autot (uudelleenjulkaisu)`
  carries the *reissue* year, so searching the alias `Cars` with `primary_release_year=2026`
  returned "The Boy Who Counted Cars". The unfiltered retry only fired when the filtered
  search returned nothing, not when it returned the wrong thing. It now retries
  whenever the year produced no exact match, and never applies a year to an alias search
  string in the first place.
- **`fetch_data.py` needs candidate queries too** (2026-08-27). Two failures found in one
  local run: OCAPI's `originalTitle` is empty for some releases, so `q` arrived as
  "Autot (uudelleenjulkaisu)" and matched nothing at all; and "Mutiny - Lavastettu
  syylliseksi" matched *Mutiny* only weakly, so no `tmdbId` was written and the row could
  not merge with BioRex's "Mutiny" even though the pipeline had found the right film.
  `_queries()` now yields the de-noised title, the raw title, then the head before a
  dash. Never before a colon: that would search "Mission" for "Mission: Impossible -
  Dead Reckoning", and an exact hit there would earn a `tmdbId` and merge two different
  films. `enrich_tmdb.queries()` still splits on a colon as well — pre-existing, and now
  worth watching, because its exact matches also write ids.
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
Provider genre strings are unusable as data: four spellings for the family genre
("Perhe-elokuva", "Koko perheen", "Koko perheen elokuva", "Perhe"), trailing spaces from
Finnkino, Cinema Orion publishes none, and in English mode every one of them is still
Finnish. Both TMDB passes now keep the genre ids already present in the `/movie/{id}`
response they fetch for the synopsis — no extra requests in the cloud pass, one detail
call per film in `fetch_data.py`, cached after. Ids land on each show as `gids`;
`data/tmdb-genres.json` holds the id -> name map for `fi`, `sv` and `en`, three
requests per run.

- Probed before building: TMDB's Finnish genre names are real translations, **18 of 19**
  differ from English. Ids plus one map per language therefore fix English-mode genres as
  well as the kids filter.
- **The kids filter cannot whitelist Animation and Family.** That was the plan until the
  probe showed TMDB tags "Marsupilami" as Adventure, Comedy — a K-7 family comedy would
  have disappeared from the filter. The rule is: rating gate first (so a restricted film
  can never be admitted, and the cinema enforces the limit at the door anyway), then ids
  `16`/`10751` mean kids, `99`/`18` without them mean not kids, and no ids means rating
  alone. Errors therefore land on "boring for a child", never on "unsuitable".
- Provider strings stay as the fallback, because the four TMDB misses and any provider
  with thin metadata still need something to show.
- Entries without `g` count as incomplete in both caches, so this cost one re-check pass.

- **Film facts fold from every showtime; screening facts fold from the surviving ones**
  (2026-08-27). Toggling "Suom. puhe" changed a card's *genres*, because the fold took the
  first non-empty field across the filtered set and the chains disagree: Finnkino
  publishes "Dokumentti, Kotimainen " (trailing space and all) for "Laula minulle Arja",
  Gilda "Dokumentti". With the filter on, Finnkino's subtitled screenings drop out and the
  card re-folded from Gilda. `tmdb`, `tr`, `img`, `len`, `genres`, `rating` and `original`
  now fold from the unfiltered set, and genres take the longest string rather than the
  first, so the richer of two disagreeing values does not depend on venue load order.
  `lang` deliberately stays on the filtered set: it belongs to the screening, and showing
  "tekstit suomi/ruotsi" from a screening the filter just removed would be wrong.
- Chains disagree about the same film's metadata more than you would expect. For one
  documentary: Finnkino `Dokumentti, Kotimainen ` / `FI-S, SE-S` / rating S, Gilda
  `Dokumentti` / `FI-A, SE-S`, Kotkan Leffat `Dokumentti` / **`SV-S`** and no rating at
  all, Kino Akseli no language. The `SV` was a real bug — the convention is Finnkino's tag
  set and the client's `LN` map keys on `SE`, so `SV-S` rendered as a bare "SV" instead of
  "ruotsi". Fixed in `etiketti.py`.
- **The sheet's chain key is sticky** (2026-08-27). A film with 40+ showtimes across a
  week scrolls the key out of view, and after that the coloured rule on each stub means
  nothing. `.sheet-body > .legend` is `position:sticky; top:0` with negative side margins,
  because the body has 20 px padding and without them the strip leaves gutters the stubs
  slide through behind it. Day headings are not sticky: the legend wraps to two lines
  on narrow screens, so their offset would have to be measured at runtime rather than set
  in CSS, and a guessed value overlaps at some widths.
- **The times list needs the venue too** (2026-08-27). The film cards labelled the venue
  and tinted by chain in a combined view; `renderTimes()` did neither, so "Ajat" on Kaikki
  Helsinki showed "Sali 14" — a room in one of five cinemas, uncoloured, under a chain
  legend it had no connection to. The stub is a fixed 158 px ticket whose label column is
  about 75 px, so putting "Kinopalatsi · Sali 14" in it truncates to "Kinopalat…" and
  loses both halves. So the venue goes on the meta line, which has the full row width,
  as a `.theatre-tag` (a class that already existed and was unused), and the stub keeps the
  room name and gains the chain tint. Single-venue views are unchanged: there the bare room
  name is correct, because the cinema is the thing you picked.
- **English titles have to resolve through `_eid`** (2026-08-27). `disp()` looked up
  `films.json` (keyed by Finnkino's `filmId`) with the show's `eventId`, which in a
  combined city view is the cross-chain merge key, so English mode silently showed the
  Finnish title for every film in every combined view. `showSheet()` already dug the
  real id out of `_eid`; `disp()` now does the same through `filmEntry()`, which also
  scans the group's showtimes so a merged row finds the Finnkino member. Falls back to the
  show's `original` title, which a few providers publish (Savon Kinot) and which beats a
  Finnish distributor title in English mode.
- **Never translate `s.title` itself.** It is the key for `mergeKey()`, for `normTitle()`
  -> `films-extra.json`, for the TMDB title cache and for `tmdb-aliases.json`. Rewriting
  it would unmerge rows, orphan synopses and invalidate every alias key at once. English
  titles are a render-time substitution and nothing else.
- Still Finnish in English mode, by omission rather than design: genres are the
  provider's own strings, stored verbatim, so `Toiminta, Jännitys` shows for every
  provider including Finnkino. Fixing it means storing TMDB's genre list per language in
  the enrichment cache and choosing at render time. Also the film list sorts on
  `title.localeCompare`, so English mode keeps Finnish alphabetical order.
- **Merge on the union of both signals, never on one or the other** (2026-08-27). Keying
  by `tmdbId` *when present* and by title otherwise unmerged a pair that had worked:
  "Maailman rikkain nainen" resolved an id at Gilda and none at Finnkino, so one row was
  keyed `tmdb:1309725` and its identically titled twin by title. `mergeIds()` now unions
  the title key with the id key and takes the group root, so an id merges chains that
  disagree on the title and the title merges chains where only one resolved an id.
- **A merged card must fold metadata by first non-empty**, not from `times[0]`. The group
  inherited the first showtime's fields, so a chain with no rating blanked the ★ even
  though another chain had one — visible on "Autot (uudelleenjulkaisu)" the moment the
  reissue rows merged. Applies to rating, runtime, genres, poster, trailer and language.
- **`tmdb-aliases.json` is read by both passes** since 2026-08-27. It used to be
  cloud-only, so a Finnkino film TMDB cannot find by title had no fix at all: the alias
  for "Maailman rikkain nainen" corrected Gilda's row and left Finnkino's blank. An alias
  id also triggers a single `/movie/{id}` call in `fetch_data.py`, which otherwise never
  fetches the detail, so the rating and the vote floor still apply.
- Aliases are keyed by the title as each chain publishes it, so one film can need
  several keys: `autot re release` (BioRex) and `autot uudelleenjulkaisu` (Finnkino) both
  map to the search string `Cars`, because "Autot" alone matched *Cars 3* by popularity.
- The two TMDB passes are still separate (`fetch_data.py` keyed by Finnkino `filmId` and
  run locally, `enrich_tmdb.py` keyed by normalised title and run in the cloud). They now
  agree on the rules — exact-match preference, `TMDB_MIN_VOTES` = `MIN_VOTES` = 25, `n`
  and `x` in both caches — but they still fetch at different times, so the same film can
  briefly carry two `vote_average` values. Merging by id hides that, because the merged
  row takes one show's rating. A single shared pass is the real fix and is not written.

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
`scripts/providers/vista.py`. Vista is the ticketing system behind **Finnkino**, and its
web front end exposes unauthenticated XML services. Savon Kinot leaves them open, so any
other Vista cinema that does is a `SITES` entry with a base URL and a venue list, no new
parser. Test a candidate with `{base}/xml/TheatreAreas/`.

```
GET {base}/xml/TheatreAreas/                    -> ID + Name per area
GET {base}/xml/Schedule/?area={id}&nrOfDays=31   -> every Show in the window
GET {base}/xml/ScheduleDates/                   -> published date list
GET {base}/xml/Events/                          -> per-film synopsis, cast, credits
```

- **No auth, no Cloudflare, datacenter IPs fine**, unlike Finnkino's own OCAPI. Runs on
  Actions. The irony is that the chain we fight a JWT for is on the same platform.
- `nrOfDays=31` is honoured, so one request per area covers the whole published window
  (8 days in practice). 6 requests per run including Events, paced 1.5 s.
- **A one-day fetch is not enough**: Kitee had 0 shows today and 7 in the window. Anything
  that fetches per day would also have written no file and, under the current runner
  semantics, failed the run.
- Areas map to one or two theatres and each Show carries `TheatreID`, so venues split from
  the data. Savon Kinot: 1006 Joensuu -> Tapio (1038); 1003 Savonlinna -> Killa (1042) +
  Kuvalinna (1044); 1002 Iisalmi -> Kuvalipas (1040); 1005 Varkaus -> Maxim (1039);
  1004 Kitee -> Kino-Hovi (1043).
- **Richest field set of any provider**: `OriginalTitle`, `LengthInMinutes`, `Genres`,
  `PresentationMethod`, four poster sizes in `Images`, nested `SpokenLanguage` /
  `SubtitleLanguage1..2` with `ISOTwoLetterCode`, `ContentDescriptors`, and a real per-show
  deep link in `ShowURL` (`/websales/show/{id}/`). No seat counts.
- Gotchas, all handled in the adapter:
  - `Rating` is `"K-7 (4)"` or `"Sallittu kaikenikäisille"`, not Finnkino's bare `"K-7"`.
    Unnormalised, the client's kids filter (`rating === 'S' || rating === 'K-7'`) silently
    matches nothing. This is the same class of bug as the Finnkino-only-field trap.
  - Both local and UTC times are published. Parse `dttmShowStartUTC` and convert through
    `Europe/Helsinki`, so DST is the library's problem: verified +03:00 in August, +02:00
    in December.
  - `SubtitleLanguage2` can carry a `Name` with an empty `ISOTwoLetterCode`, so fall
    back to mapping the Finnish language name ("ruotsi" -> SE).
  - `TheatreAuditorium` is `"Joensuu, Tapio 4"`: strip the city, and blank it when it only
    repeats the venue name (single-screen houses).
  - Synopsis tag names vary between Vista versions. Only 1 of 48 titles matched
    `Synopsis`/`ShortSynopsis`/`Description` here, so treat a miss as "no synopsis" and let
    TMDB cover it. Worth finding the real tag for this version.

### Gilda / MyCloudCinema (added 2026-08-27)
`scripts/providers/gilda.py`. Two Helsinki venues: Gilda salit 1-3 and Bio Rex
Lasipalatsi (the historic cinema, *not* the BioRex chain). Not the Riviera ajax: the
theme resemblance was superficial. The listing is a React app
(`app/plugins/gilda-react-booking`) and the page prints its own API config for anonymous
visitors.

```
GET {base}/wp-json/gilda-react-booking/v1/movies
-> {"fi": {"data": [ {film..., show_times:[...]} ], "resultCode": 0}}
GET {base}/wp-json/gilda-react-booking/v1/cinemas    -> cinema_id 15, Narinkka 2
```

- One request covers everything: 35 films / 101 shows / 22 dates, no auth on the read
  endpoints. The namespace also holds write and administrative routes; they are closed to
  an anonymous caller, are never called, and are not inventoried here.
- **Venues split by `cinema_screen_id`, not cinema**: one `cinema_id` 15, screens 66/67/68
  are Gilda 1-3, screen 69 is Bio Rex Lasipalatsi.
- Gotchas, all handled:
  - `rating_name` is bare ("12", "16", "S", "T", "EI MÄÄR."). Map to `K-12`/`S` and leave
    unrated blank rather than guessing.
  - `screen_name` for Lasipalatsi is "Bio Rex Lasipalatsi (K-18)" — a venue door policy,
    not a film rating. Strip it or every show there looks adults-only.
  - `subtitle_lang` arrives three ways in the same feed: Finnish words ("suomi, ruotsi"),
    codes ("FI", "SE"), and "-" for none. `audio_lang` is always a code.
  - `description` is HTML with entities; strip tags then `html.unescape`, or the sheet
    renders "Almod&oacute;var".
  - `show_time` is UTC with a +00:00 offset.
- **Posters: the path needs the movie id and a width.**
  `{host}/media/posters/{movie_id}/1080/{uuid}.jpeg`. Only 1080 exists; 720 and 500 are
  404. A bare `/media/posters/{uuid}`, guessed from a string in the React bundle, 404'd for
  every film and shipped — the client's `onerror` gradient tile hid it completely. The
  correct shape was already visible in **BioRex's** committed poster URLs, since BioRex is
  on the same MyCloudCinema backend (`web.biorex.mycloudcinema.com` vs
  `web.atlanticfilm.mycloudcinema.com`; Atlantic Film operates Gilda).
- **Per-film pages exist at `/elokuva/{slug}/`** and that is where showtimes link.
  I first concluded no deep link existed, which was wrong: I searched the React bundle for
  a *showtime* route (there is none, and seat choice really does live in React state) and
  never checked the site itself. The listing is React-rendered, so the film links are not
  in its HTML. **Look at the site before concluding a link does not exist.**
  - The booking API carries no slug and no permalink. The mapping comes from
    `GET /wp-json/wp/v2/movies?per_page=100&_fields=link,title` (~500 posts, paginated),
    matched on the title: first `movie_name`, then `original_title`.
  - That second rule does the real work: "Maailman rikkain nainen" has no post under that
    name but resolves via its original title to
    `/elokuva/the-richest-woman-in-the-world-2/`. Likewise "Jonain Päivänä" ->
    `/elokuva/leave-one-day/` and "Pieni elokuvakerho: Kummisetä osa II" ->
    `/elokuva/pieni-elokuvakerho-the-godfather-part-ii/`.
  - **No fuzzy matching.** Prefix and substring rules were tried and sent
    "Pieni elokuvakerho: Kummisetä osa II" to three unrelated club screenings. A near-miss
    puts someone in front of the wrong film; the fallback to `/elokuvat/` costs a click.
  - Coverage 99/100 showtimes; the one miss is a music playback event. Twelve generated
    URLs were status-checked (200, and each contains the booking widget) before shipping.
  - A `book: "list"` mode exists in the registry and client for a provider that genuinely
    has no per-show page. Gilda does not need it and is back to `buy`.
- Venue naming: the main house is **Gilda Kamppi** (Narinkka 2). `short` carries "Kamppi",
  not "Gilda", because the client prefixes the chain onto `short` and would otherwise
  render "Gilda Gilda". The sibling keeps `short: "Bio Rex Lasipalatsi"`, so it labels as
  "Gilda Bio Rex Lasipalatsi" — long, but shortening it to "Lasipalatsi" would blur the
  fact that this cinema is not part of the BioRex chain, which the app also carries.
- Seat counts would need the closed seatplan endpoint, so `soldOut` is always false.

### Cinema Orion (added 2026-08-27)
`scripts/providers/orion.py`. One venue, Eerikinkatu 15, Helsinki, run by ELKE ry.
Single screen, so `aud` stays blank. One request to the front page and nothing else:
11 `<table class="kinola-day">` blocks, one `<tr>` per screening. First live run: **31
showtimes over 11 dates, 28 films, horizon +27 days**. Runs on Actions — a runner gets
200 and ~122 kB from `https://cinemaorion.fi/`; only `tickets.cinemaorion.fi` blocks
datacenter IPs and the adapter never touches it.

```html
<td class='date'> Torstai 27.08. </td>
<td class='time'>17:15</td>
<td class='title'> Espoo Ciné: The Good Daughter </td>
<td class='price' title="Peruslippu, alennusryhmät: 13 €, Peruslippu: 13 €"> 13&nbsp;€ </td>
<td class='link'> <a rel="external" title="..." href='https://orion.kinola.ee/web/screening/{uuid}'>Liput</a> </td>
```

- **The title cell has two shapes and the second one bites.** A festival row is bare
  text as above; a row with a film page is
  `<a href='/elokuvat/{slug}/' title ="Film"> Film <span class="descrption">blurb<span> </a>`.
  Flattening that cell glues the screening blurb onto the title: the first live run
  produced titles like "Autofiktio Ensi-iltaelokuva, klubialennus. Pedro Almodóvarin
  melodraama…", which split one film into one "film" per blurb (31 shows, 30 ids) and
  left TMDB nothing to match. So the title is read from the **anchor's `title`
  attribute**, and `eventId` from the **`/elokuvat/{slug}/`** slug, which is what makes
  repeat screenings of one film share an id. A fixture built from this file's own markup
  could not catch this; only the live run did.
- `descrption` is the site's spelling, and the span inside it is never closed, so it
  is cut at whatever tag comes next rather than at a `</span>`. The blurb goes to `_syn`
  (5 merged on the first good run). It mixes screening notes ("Ensi-iltaelokuva,
  klubialennus.", guest names) into the synopsis; synmerge only fills an empty slot, so
  that is accepted rather than split.
- Attribute quoting is loose: `title ="Film"` has a space before the `=`, and the price
  cell is `13&nbsp;€`. Attribute regexes allow `\s*=\s*`, and `\s` matches `&nbsp;`
  once unescaped.
- The `price` cell's `title` attribute carries the full ticket-type breakdown, so a
  screening with cheaper types can show the floor: 2+ distinct amounts render
  "alkaen {cheapest}€". First run: 13€ ×17, alkaen 10€ ×9, 10€ ×3, 8.5€ ×1,
  "Vapaa pääsy" ×1.
- **Take the ticket URL from the markup, never build it.** Still the rule, but note the
  earlier claim was not reproduced live: on 2026-08-27 **all 31 rows pointed at
  `orion.kinola.ee/web/screening/{uuid}`**, including every Espoo Ciné row, so the
  festival-box-office case (`boxoffice.espoocine.fi`) is unexercised rather than
  confirmed. A row with no anchor at all falls back to the programme page.
- Third-party events are real screenings here and stay in the data: festivals, HopeaCine,
  Pieni elokuvakerho, Pitchblack Playback, music playback nights. **The strand name is
  split off the title into `method`** (added 2026-08-27, once the first run's no-match
  list named the real prefixes): the client already renders `method` as a pill, and the
  film title has to stand alone for two reasons beyond the TMDB search. The poster
  fallback tile takes the first letter of the first two words, so with the prefix left in
  every Espoo Ciné screening rendered the same "EC" tile; and a strand prefix splits one
  film's showtimes across ids. The list lives in `enrich_tmdb.EVENT_PREFIXES` and is
  shared with `clean()`, so one edit serves both, and Gilda's "Pieni elokuvakerho:"
  titles came along free. Added: `espoo ciné`, `espoo cine`, `pieni elokuvakerho`,
  `pitchblack playback`, `hopeacine`. Left alone: `Follow The Plants` (a shorts
  programme) and `John Coltrane 'Highlights 1957-1964'` — no prefix helps a title with no
  TMDB entry.
- The bad first run left 13 glued-title keys in `data/tmdb-titles.json`. Pruned, on the
  rule that a cache key with no rating, trailer or id and no live showtime is dead.
- `/wp-json/wp/v2/elokuvat` gives film pages (synopsis, slug) and could enrich by slug:
  636 films over 7 pages of 100. Not needed for text — the front page already carries the
  slug and the blurb. And it has no posters (probed 2026-08-27): `featured_media` is
  null on all 100 entries of page 1, `content.rendered` holds no `<img>`, `acf` is empty.
  The only image is Yoast's `og_image`, which is the page's 16:9 header still rather than
  a poster (page 1: 77 jpg, 15 png, 4 webp, 3 jpeg, 1 tif).
- **Do not swap Orion's own images in for TMDB posters.** A 16:9 still cropped into a 2:3
  tile is a downgrade on the rows that already match TMDB, and the 17 Espoo Ciné rows are
  bare text with no `/elokuvat/` link, so they have no slug for this endpoint to key on.
  Filling only the gaps would be safe but currently fixes nothing: the one gap that has a
  slug is "Follow The Plants", whose header image is a **1600x900 TIFF** with no jpg
  derivative, which Chrome will not render. That title keeps its initials tile, which is
  correct — a shorts programme is not a film, same as the Coltrane and Jamiroquai
  playback nights. Putting an image there would mean converting the file and hosting it
  in `data/posters/`.

  Three assumptions that were wrong and cost a detour, recorded so nobody repeats them:
  - ELKE's "Rajapinnat" page is not an API page. It means *interfaces between old and
    new media*: an arts programme about VR and interactive works.
  - The **`naytokset`** post type exists and answers 200, but returns an empty list.
    Registered route, no records. A route listing is not data.
  - **Kinola is not a platform win.** `tickets.cinemaorion.fi` answers 403 to datacenter
    IPs and `orion.kinola.ee` exposes only a Filament/Livewire admin login, whose
    screening pages render seats and prices client-side. Nothing to adapt, and not
    somewhere to go poking.

### Kino Engel (added 2026-08-29)
`scripts/providers/engel.py`, one venue, runs locally. Accent `#B47ACC`.
- **The accent was measured, not picked** -- but with a broken metric, and the numbers
  first recorded here (36.9 normal, 37.3 deutan, against a claimed BioRex/Riviera floor
  of 34.5) do not survive re-derivation. Re-measured 2026-08-30 with
  `scripts/accent_check.py`: `#B47ACC`'s worst same-city pair is **18.5 normal, 15.2
  deutan** (against Gilda), and the real BioRex/Riviera floor is 3.9, not 34.5. The
  conclusion the bullet drew still holds -- Engel does not lower the Helsinki minimum,
  because at 15.2 it sits well above the 3.9 that was already there -- but it held by
  luck rather than by the check that was run. The L* 38-60 constraint is the one part of
  the original search that did not depend on the metric, and `accent_check.py --search`
  keeps it.
- Parses rows, not day headings. Each row carries its own "La 29.08." beside
  "klo 17:30", so the `<h2>` headings and the date `<select>` above them are redundant
  and their markup can change without breaking this.
- No room, no price, no runtime and no rating in the listing, and the row's only link is
  the film page rather than a booking URL, so `book` is `buy` pointing there.
- Dates carry no year, same as Kino Akseli, so the same [today-45d, today+320d]
  window picks it.
- **Deduplicates on (eventId, start, aud)**: a film can appear in a carousel and in the
  day list on the same page, and only one of those is a screening.
- **Attribute quoting is mixed and it cost a live run.** WordPress emits double quotes,
  the Johku schedule widget emits single: `<img src='https://johku.com/...'>`. The first
  version matched double only, so every poster came back empty while the parse otherwise
  looked healthy, 43 showtimes and 17 films. Every attribute regex here accepts both now.
  Same class of thing as the BeautifulSoup re-serialisation note: never assume a page's
  quoting is uniform.
- **Posters are hosted on `johku.com`**, not on the cinema's own domain, so they go
  through `mirror_posters.py` like every other remote poster.
- **The programme is rendered twice, and the second copy has no times.** The timed
  listing gives "Pe 05.09." + "klo 21:30" + "Osta liput"; a second listing repeats the
  same screenings with the weekday written out ("Perjantai 02.10.") and an empty time
  span. 41 timed rows against 46 timeless ones on 2026-08-29.
- **I misread those timeless rows as premieres, and the log caught it.** The first
  version counted every one of them as an upcoming film, which produced a list of 46
  including "Autofiktio 30.08." — a screening that carries a time in the other listing.
  44 of the 46 were duplicates. Only 11.09. and 02.10. appear nowhere with a time, and
  both are in the date `<select>`, so their times are presumably fetched when the reader
  picks the date. The log now reports only dates no timed row covers, which is the
  number that would actually mean something: it is 2 today, and it going to 13 would say
  the timed listing had disappeared. A count that fires on healthy data gets ignored, the
  same way the always-red workflow did.

Johku is a platform lead. The schedule widget's classes are `rs-johku-schedule` and
`rsjohku-ohjelmisto`, and the images come from `johku.com/kinoengel/files/`. Johku is a
Finnish commerce and ticketing service, so its cinema customers may all render the same
widget, which would make each of them a `SITES` entry rather than a parser. Worth a
search for `rs-johku-schedule` and `johku.com` across Finnish cinema sites, alongside the
existing `nexxo-scope` and `etiketti.app` sweeps.

First live run, 2026-08-29: **41 showtimes, 17 films, 11 dates, 6 KesäKino, 41 posters,
0 failures**, and the cloud pass that followed mirrored 24 new posters and generated the
two new pages (47 venues, 105 sitemap URLs). Two rows needed aliases: Engel publishes the
Swedish-dubbed "Minioner & monster" and the Japanese "Kokuho - kabukin mestari",
both of which TMDB matched *correctly but weakly*, so no `tmdbId` was written and neither
could merge with the other chains. The ids were verified against the cache rather than
assumed — Minioner shares 1315772, the trailer key and the genre ids with Kätyrit &
Monsterit — and both are now in `tmdb-aliases.json`. Expect this from any provider that
publishes a Swedish-language strand.

Engel writes no `rating` on any show. That is the listing, not the parser: no age limit,
runtime or price appears anywhere on the front page. Age limits therefore come from
nowhere for this venue, which is a real gap the film pages could close.

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
Six rounds of probing, recorded in full because the trail is plausible at every step and
someone will otherwise walk it again. **Outcome: no usable showtime feed. Route A stands.**

What the page renders and the server does not send: the film page shows a table with the
date *including the year*, the auditorium ("Engel 1"), the per-screening price and a
booking button, all cleanly classed (`_kj_showtime_date`, `_kj_showtime_time`,
`_kj_showtime_hall`, `_kj_showtime_price`, `data-id` = Johku show id). None of it is in
the 81 kB the server returns. A DevTools screenshot shows the built DOM, which is why it
looked available and was not.

The path, and where each step ended:
1. `johku.com/kinoengel/allproducts.json` -> **403**. My guess, wrong shape.
2. `widget-module.js` (912 kB) builds `apiUrl + shopId + "/" + locale + "/" + path`, and
   the page publishes `<johku-widget id="kinoengel/da5a9f02c6dbf044" locale="fi_FI">`. So
   the ids are public and the 403 was a bad path, not a wall. `X-ApiKey` is attached only
   when an `apiKey` is set, so a public storefront does not obviously need one.
3. Public and working: `settings/public.json`, `fi_FI/storefrontsettings.json` (246 kB,
   two categories: 2 Elokuvat, 3 Arvokortit), `widgets/{id}.json` (type `Basket`, left
   alone).
4. `fi_FI/categories/2/allproducts.json?details=true` -> **200, 4.3 MB, 781 products**,
   each with an `ownShow` array carrying exactly what is wanted: `start_date` "30.8.2026",
   `starttime` "15.00", `resource_id`, `pricing_id`, show id. **But only the next show per
   product**: Autofiktio has seven screenings and one entry, and the whole 4.3 MB contains
   no 2026-09 date at all.
5. Per-product detail: `products/{source_id}.json` -> 200 but `ownShow` empty;
   `products/{numeric id}.json` -> 404; `products/{canonical}.json` -> 403. And `ownShow`
   appears zero times in `widget-module.js`, so that module never reads shows either.
   The `_kj_` markup belongs to a different code path: the WordPress plugin
   `rs-johku-wordpress`.
6. That plugin's loader is
   `johku.com/embed/?shopId=kinoengel&productId={n}&identifier={hash}&...`, printed in the
   film page's own HTML, so a `productId` is free per film. It returns 2265 bytes of
   JavaScript that only pushes `_kjProd` and hands off. It did reveal a composite
   product id (`992_5e578e61...`) that none of the earlier attempts used —
   `products/992_5e578e61....json` -> **403**.

So the show list is reachable only by whatever authenticated call the widget makes after
that handoff. Getting at it means lifting the key, which is the line in "Access and
ethics", and is not worth crossing for one single-screen venue out of 47.

**Two things I was wrong about along the way**, both from assuming a mechanism instead of
reading one: that the first 403 meant the API was closed (it meant my path was wrong), and
that `widget-module.js` rendered the table (it does not). Each wrong guess cost a round
trip. The rule that would have saved both: find the code that builds the URL before
trying URLs.

**The showtime table is not in the HTML and the API is closed to us.** The rows a browser
shows on a film page — date *with the year*, auditorium, per-screening price, a real
booking link — are injected by `johku.com/widget.js`, and none of it appears in the
81 kB the server sends. The widget's read endpoints under `johku.com/{shop}/` answer
**403** without the `X-ApiKey` it is issued. Getting at that key is the line in "Access
and ethics", so it was not attempted and the write side of that namespace is deliberately
not inventoried here. Consequences to accept, not to work around: `price` and `aud` stay
empty for Engel, there is no per-show booking URL so a showtime opens the film page, and
11.09. and 02.10. stay missing because their times only exist behind the widget.

Johku is still a platform lead for the listing widget itself: `rs-johku-wordpress`
renders the same `rs-johku-schedule` markup on any of its cinema customers, so another
Johku cinema would be a `SITES` entry against the same parser.

### Probed but not yet added (2026-08-27)
- **Kino Engel** (kinoengel.fi) — Sofiankatu 4, Helsinki. Screens Engel 1 / Engel 2 plus
  an outdoor "KesäKino". Elementor; the front page renders a day-grouped list with title,
  "To 27.08. klo 17:30" and a link to /elokuva/{slug}/. No room or price in the list.
  Title prefixes to handle: `KESÄKINO:` (outdoor) and `BARNSÖNDAGAR:` (Swedish kids).
  - **This one runs locally. It is not on any platform we already have, and a runner
    cannot read it** (probed 2026-08-29). Every path answers **HTTP 202** with a 169-byte
    meta-refresh shell and the headers `SG-Captcha: challenge`, `X-Robots-Tag: noindex`
    and a redirect to `/.well-known/sgcaptcha/?r=%2F&y=ipr:{runner ip}`. That is
    SiteGround's captcha protection firing on **IP reputation**, so the block is the
    datacenter address rather than the request shape; a browser on an ordinary connection
    is not challenged. Solving it is out of bounds under "Access and ethics", so Engel
    joins Finnkino and Kino Akseli on the local half: a `SITES` entry whose module the
    local wrapper runs, and the wrapper's module list has to gain `engel`.
  - **The WordPress REST API is open, and Vista is out** (probed from a residential
    connection, 2026-08-29). `/wp-json/` answers 200 with 372 kB of route listing and
    `/wp-json/wp/v2/types` 200 with 12.5 kB; `/xml/TheatreAreas/` is a clean 404 rather
    than a challenge. So the earlier all-202 result really was the IP and nothing else,
    and there may be no scraper to write here. Read the route list before parsing HTML.
  - **The front page already carries the Kesäkino screenings**, so `/kesakino/` is a
    landing page rather than a second source: `/elokuva/kesakino-keltaiset-kirjeet/` and
    `/elokuva/kesakino-autofiktio/` both appear in the front page's film links. One fetch
    covers the whole programme. `/kesakino/` is worth reading only if it turns out to
    carry something the front page drops, and on 2026-08-29 it held 4 screenings, all at
    21:30, against the front page's eleven published dates.
  - **The prefix is in the slug as well as the title**, which is the part that bites.
    `autofiktio` and `kesakino-autofiktio` are two slugs for one film, so an `eventId`
    taken from the slug the way `orion.py` does it would split one film into two cards in
    the same venue, each with its own poster lookup and its own TMDB miss. Identity has
    to come from the cleaned title, and `KESÄKINO` has to come off before anything keys
    on it.
  - **`acf` is empty on every film, so the REST API holds no schedule** (probed
    2026-08-29). `wp/v2/elokuva` exists and exposes an `acf` key, which looked like the
    whole adapter for a moment, but it comes back empty on all of them. The endpoint also
    returns **899 films over 9 pages**, so it is the site's whole archive rather than
    what is playing. Engel is therefore a parser for the times and REST for the metadata:
    the front page (and `/kesakino/`) carry the dates, and `wp/v2/elokuva?slug=` gives
    `link`, `content` and `featured_media` per film without a second page fetch.
  - **Each strand is its own `elokuva` post.** 3303 `autofiktio` and 3295
    `kesakino-autofiktio` are two records for one film, likewise 3298
    `keltaiset-kirjeet` / 3299 `kesakino-keltaiset-kirjeet`. Of 100 posts on page 1, 23
    were `kesakino-`. So the split is systematic and the merge has to be ours.
  - **Three strand prefixes, not two.** `KESÄKINO:`, `BARNSÖNDAGAR:` and also
    **`BARNFESTIVAL:`** (`barnfestival-nord`, `barnfestival-skurkarnas-skurk`), which the
    first pass missed. Barnsöndagar and Barnfestival are real strands for
    `EVENT_PREFIXES`; Kesäkino is a room and goes to `aud`.
    `ohje-movie-description`, `ohje-movie-schedule`, with times as `La 29.08.   klo
    21:30` (note the run of spaces). The `rsjohku` prefix is worth a look on its own
    terms: if it is a Finnish booking integration used by other cinemas, it is a platform
    lead rather than one site's theme.
  - **KesäKino is an auditorium, not a strand.** `aud` carries the room verbatim because
    that is what is printed on the ticket, and an outdoor screen is exactly the kind of
    thing a reader needs on the showtime stub before turning up. So the adapter sets
    `aud: "KesäKino"` and does not route it through `strands.py`, which would put it in
    `method` next to Anniskelu and SenioriKino. `BARNSÖNDAGAR:` is a real strand and does
    belong in `EVENT_PREFIXES`.
  - **Not a separate venue**, for the same reason LUXE and VIP-SALI are not: a room is not
    a cinema. The seasonal argument settles it independently. A KesäKino venue would sit
    empty for nine months, `venues-{provider}.json` lists every venue whether or not it
    has shows, and a site parsing zero showtimes fails the run. A permanently empty venue
    in the picker is a standing false alarm.

Orion is in; Helsinki's combined view is 11 venues across 5 chains, and Engel would
make it 12 across 6.

### Swedish: who actually publishes it (probed 2026-08-29)
Finland is bilingual and four cities we cover are Swedish-strong (Vaasa, Pietarsaari,
Porvoo, Kokkola), 23 of the 48 venues covered then sat in officially bilingual
municipalities, and 1920 showtimes already carried Swedish subtitles. So a Swedish mode has an audience. What it
does *not* have is much Swedish source text.

- **BioRex publishes a real Swedish edition.** `admin-ajax.php?lang=sv` returns the same
  22 films with genuine Swedish distributor titles, not machine translation: Autot ->
  **Bilar**, Päivien lumo -> **Skimrande dagar**, Ryhmä Hau: Dinoelokuva -> **PAW Patrol:
  Dinosaurie-filmen**. 6 of 22 differ; the rest are international titles identical in both
  languages. 12 venues, and they include Vaasa, Pietarsaari and Porvoo, so the one chain
  with Swedish is the one serving the Swedish-speaking towns.
- **Finnkino has none.** Probed through a browser, since the site answers 403 to anything
  that does not look like one. `hreflang` declares only `fi-fi` and `en`; `/sv/` redirects
  to the Finnish front page and `/se/` is a clean 404; and the site's own configuration
  API accepts exactly two cultures, `fi-FI` and `en` -- `sv` and `sv-FI` are 500, `sv-SE`
  is 404. Whether the OCAPI back office holds Swedish translations that the website never
  surfaces is unverified and needs a token to check, but a chain with a legal and
  commercial reason to serve Swedish that publishes none on its own site almost certainly
  has none to give. 17 venues fall back.
- **eTiketti has none.** `/sv/` on kotkanleffat.fi and biorex.org both return an ~8.7 kB
  page with zero film links -- a soft-404, not a Swedish edition. Status codes lie here
  the same way they did in the Vista sweep; count the films, not the 200s.
- Savon Kinot's `/sv` is a clean 404. Whether the Vista XML takes a language parameter is
  unprobed.

So a Swedish mode means: Swedish UI everywhere, Swedish titles at BioRex, and a fallback
for the other 36 venues. **That fallback has to be Finnish, not English.** The Finnish
distributor title is what is printed on the ticket and on the cinema's own booking page,
so showing a Finland-Swede an English title invents a name that appears nowhere at the
cinema they are standing in -- the same reason auditorium names are kept verbatim. English
is the right fallback for the English UI, where the reader has opted out of local names.

Worth splitting the work: the UI strings need no pipeline change at all and are most of
the value, since what this audience needs first is to read "text finska/svenska" on a
screening. Swedish titles cost BioRex a second fetch per venue (12 requests become 24)
and a new per-show field, because `title` is the merge key and translating it would
unmerge rows and orphan synopses.

### Bio Rex Kokkola, the first site off the sweep (added 2026-08-29)
`biorex.org`, one venue, `etiketti.py`, **no parser change at all**. The first test of
the sweep's central claim, and it held: the existing adapter ran against the site
unmodified and returned 41 showtimes over 10 dates with rating, runtime, genres,
languages, price, per-screening booking links and real seat counts, plus 18 synopses
merged. That is the full Kotkan Leffat field set, so eTiketti sites are worth adding on
the strength of the platform alone.

- **Not the BioRex chain**, despite the name, and the two are unrelated: `biorex.org`
  against the chain's `biorex.fi`. Exactly the Bio Rex Lasipalatsi trap Gilda already
  carries, so the label spells the city out and the accent was chosen *away* from BioRex
  blue rather than near it, since a similar colour would reinforce the confusion.
- **One venue, three rooms.** DIGI 1, DIGI 2 and SALI 3 all report under the single place
  name "BIO 1&2 REX". A room is not a venue, so the room stays in `aud` verbatim.
- Accent `#006655`. Kokkola has no other venue, so the per-city rule leaves this
  unconstrained -- the same reasoning that let Kino Akseli take the vacated gold -- but
  it was measured anyway and is the best available worst-case against the other ten in
  both normal and deuteranope vision.
- **The accent numbers were unreproducible; settled 2026-08-30.** The independent model
  was right and this file was wrong. `scripts/accent_check.py` is the method that was
  missing; see "The accent numbers, re-derived" below. Kokkola still has no other chain
  in it, so this accent remains unconstrained either way.

### The cinema-list lead: nytleffaan.fi, probed 2026-08-29
`nytleffaan.fi/elokuvateatterit/` is a directory of every Finnish cinema, run by Suomen
Filmikamari (the industry umbrella body). It is the list of domains every sweep here
had been blocked on. It yields **225 cinema entries across 152 distinct hosts**, each with
a "TEATTERIN KOTISIVUT" link to the cinema's own site.

The page needs a browser: the directory markup is there, but reading it meant rendering
the page rather than fetching it, which is why this sat unprobed while the list was
described as unavailable. The list was never the hard part. Reaching it was.

Swept 103 of the 152 from an ordinary connection (dropping chains already integrated,
municipal event pages and the aggregators), two requests per host: the homepage for a
platform fingerprint, and `/xml/TheatreAreas/`. Then the fingerprint hits were verified
against the endpoint each adapter actually needs, because **a signature in someone's HTML
proves they are a customer of a platform, not that the platform answers us**.

eTiketti is much bigger than Kotka. 22 hosts carry `etiketti.app`; **16 serve the
`/elokuvat/ohjelmistossa` listing `etiketti.py` already parses**, verified by counting the
`/elokuvat/{id}/` film links in the response. (Counting links proved less than it reads
as: one of the 16, Cinema Niagara, serves the listing and renders its screenings in a
different template that this parser reads as zero. Corrected in the sweep entry above.) biorex.org 31 (Bio Rex Kokkola, which is
not the BioRex chain), kinopirtti.fi 16, arthousecinemaniagara.fi 15, leffabuumi.fi 13,
studiot123.com 12, ihmekompleksi.fi 10, kino123.fi 9, jamsankinotar.fi 8, kinojuha.fi 8,
studio123.fi 8, biogrand.fi 7, biovuoksi.fi 7, kinoiiris.com 7, kino.joutsa.fi 4,
k-kino.fi 3, biograni.fi 2. Six more carry the signature and serve no film links
(elokuvat-elo.info, kino-mania.info, kinokaustinen.fi, kinosampo.info, toijalan-kino.info)
or 404 (elokuvateatteristar.fi).

**Nexxo, likewise.** All 10 hosts carrying `nexxo-scope` answer `public_api.php` with valid
JSON. Six have live shows: kinoaurora.fi 40, ksek.fi 40, kinohirvi.fi 33, kinomarilyn.fi
28, kino-olympia.fi 9, jarvelankino.fi 8. **kinohirvi.fi serves two locationids (2 and 4)**,
so a host is not a venue. Discover the ids, never assume `1`.
(Corrected by the sweep below: ksek.fi and kinoaurora.fi are the *same* deployment, so
this list counted one operator twice, and kinohirvi.fi's id 4 is Bio Säde -- whose own
domain is one of the four "empty" hosts.)

The other four (biojukola.fi, biosade.fi, biosalo.fi, biostara.fi) return valid JSON with
**zero shows at every id 1-6**. That is the case the zero-showtime run failure is waiting
for: a healthy site with an empty programme. Check one against its own page before adding
it, and expect to need the "legitimately empty site" escape hatch that item describes.

**Johku is confirmed as a platform, not one cinema.** `kuvatahti.johku.com` appears in the
directory outright, and kinotapiola.fi, kulttuurimylly.com and virtasali.fi carry the
widget. Unverified: nobody has checked whether they render `rs-johku-schedule`
server-side. Engel's finding applies in advance: the listing parses, the API does not.

**MyCloudCinema:** mantsala.cine.fi, the backend BioRex and Gilda already sit on.

Not measured, and required before any of this lands: venue counts (a host can carry
several; ksek.fi, leffabuumi.fi, studio123.fi, kino123.fi and k-kino.fi each list 2-3 in
the directory), overlap with venues already covered, and accents. Nine chains already
sit near the limit of what stays separable under deuteranopia; twenty would not, and the
per-city rule is what makes that survivable. Measure before promising a chain a colour.

Also the competitive picture, since it comes up when deciding what to claim on the site:
- **nytleffaan.fi** — industry-run, gets exhibitor data rather than scraping, claims every
  cinema in Finland. It excludes special screenings: event cinema (theatre, opera,
  sport) and festival screenings.
- **elokuviin.com** — claims all cinemas large and small, and does include festivals.
- **kinossa.fi** — same aggregation idea.

So **"Suomen kattavin" is not a defensible claim**: 64 venues against the 225 entries
nytleffaan.fi lists (fewer distinct cinemas than that — Kinotour alone accounts for 14
touring venues), and two services already claim full coverage. What is true and
checkable: 25 chains merged into one city view, festival and strand screenings included
where those services drop them, sold-out marks and prices where a cinema publishes
them, no ads and no tracking. Say the count ("25 ketjua, 64 teatteria, 45 kaupunkia") and
let it grow.

### The eTiketti sweep lands: fourteen hosts, sixteen venues (2026-08-30)
Every host the nytleffaan.fi entry above lists as serving `/elokuvat/ohjelmistossa` is
now a `SITES` entry, against the parser that already served Kotka and Kokkola. No new
parser and no `index.html` edit. All fourteen publish: thirteen from the cloud half and
Joutsan Kino from the local one, which needed the site-level routing below. **11 chains
to 25, 48 venues to 64, 33 cities to 45**, measured from `run-pages.log` and the
committed data rather than from the registry.

Measured end to end before committing, by running the adapter into a throwaway output
directory rather than over `data/`: **19 venues, 331 showtimes, 0 failures** across the
whole module, the three existing venues included. Per new venue, smallest first: K-Kino
Kangasala 3, Kino Saimaa 2, Kino Juha 7, Joutsan Kino 8, Bio Grani 8, Bio Grand 9, Bio
Vuoksi 9, Ihme Kompleksi 10, Kinotar 123 15, Kino Iiris 16, Studio 123 Järvenpää 22,
Studio 123 Kouvola 28, Kinolinna 29, Kino 123 35, Kinopirtti 45, Kino Ritz 5.

- **Cinema Niagara is held back, and it is the interesting one.** It carries the
  signature, serves the listing, and answers 14 film links -- and its film pages hold no
  screening block this parser can read. Not a Cloudflare problem and not an empty
  programme: the screenings are server-rendered and visible in the fetched bytes, in a
  *different template*. There is no `klo` before the time (`<div class="time">10.00`),
  the price is a bare `10,00€` rather than `Lippu 10,00`, seats read "Seats available"
  rather than "Vapaat paikat", and an attribute sits between `<div` and `class`, which
  is what defeats `ITEM_RE` outright. Adding it as it stands would parse zero showtimes
  and fail the run. So eTiketti is not one template, and "serves the listing" was the
  wrong test to have stopped at -- the 16-host figure counted film *links*, which is a
  weaker claim than it reads as. The other 14 were verified by parsing screenings out
  of them, not by counting links.
- **The colour rule bound in three new towns, and the obvious pick was wrong in two of
  them.** Vantaa gains a second chain (Finnkino Flamingo + Bio Grand), Lahti likewise
  (Finnkino Kuvapalatsi + Kino Iiris), and Kouvola gets two of this sweep's own at once
  (Kino 123 + Studio 123 Kouvola). Green against Finnkino's orange measures **13.6 dE00**
  under the harsher deutan model -- below the 14.4 that was already the worst pair in the
  set -- so the intuitive "green is nothing like orange" is exactly backwards for a
  deuteranope. Worse, Kouvola's first pick of magenta against teal reads 43.5 dE00 in
  normal vision and **6.9** in deutan: two colours that could not look less alike, and
  that collapse onto each other. Repicked to blue against orange at **73.5**: both Kouvola
  chains are single-city, so both colours are free, and the pair is taken at the maximum
  the L* band allows rather than merely far enough apart. It launched at 35.2, ochre
  against teal, which cleared the rule and left the rest on the table for nothing. Vantaa
  settled on violet (57.4) and Lahti on blue (60.3), where Finnkino's orange is the fixed
  half of the pair.
- **Hues now repeat across cities, deliberately.** Twenty-five chains cannot all be
  separable at once and do not have to be: the accent renders only in a combined city
  view and its legend, so the only pairs that exist are the ones inside one town. Four
  cities have more than one chain -- Helsinki with six, Vantaa, Lahti and Kouvola with
  two. Everywhere else the chain is alone and its accent is free. That is the property
  that makes the number of chains irrelevant, and it should be stated rather than
  rediscovered the next time someone counts the palette and panics.
- **A registry entry and a `SITES` entry are joined by a bare string**, and nothing
  checked it. A provider present on one side only still fetches, still writes
  `data/venues-{id}.json` and still renders -- with no chain label, no accent, no host
  credit and no booking verb, because all four come from the registry entry that is not
  there. One typo's worth of risk at two sites; sixteen now. `tests/test_registry_sites.py`
  asserts the join in both directions, that a `SITES` entry lives in the module the
  registry names, and that no two adapters claim the same venue id -- a collision there
  is one cinema's `data/area-{id}.json` overwriting another's.
- **`book="buy"` for all fourteen, checked rather than assumed.** Every screening row on
  every host carries a `/salikartta?id=` link and a price. Bio Grani is the one that
  publishes no free-seat count, which costs nothing: seat counts are deliberately
  unpublished anyway.
- **A venue `short` that is a *prefix* of its chain label renders twice.** Both
  `label_of` in `build_pages.py` and its mirror in `index.html` drop the chain prefix
  only when the short name already *starts with* the chain, which is the BioRex case
  ("BioRex Tripla" under chain "BioRex"). Studio 123 is the other direction: chain
  "Studio 123 Järvenpää" against short "Studio 123", so the guard did not fire and the
  picker read "Studio 123 Järvenpää Studio 123", with a venue page slugged
  `studio-123-jarvenpaa-studio-123-jarvenpaa` and two such URLs in the sitemap. Fixed in
  the adapter rather than in the two label functions: `short` now repeats the full label,
  which is exactly what Bio Rex Kokkola already does, and the guard collapses it. The
  symmetric fix in `label_of` was measured first and changes these two slugs and no
  others -- but it would have meant editing `index.html` too, to keep the client and the
  pre-rendered pages agreeing on a venue's name. The slug still doubles the city
  (`studio-123-jarvenpaa-jarvenpaa`), which is the house pattern nine BioRex venues
  already follow, and is not worth changing indexed URLs over.
- **Kouvola, not Kuusankoski.** Both Kouvola sites give a Kuusankoski postal address, and
  neither site says either name in its own pages. The industry directory names one of the
  cinemas "Studio 123 Kouvola" outright, and Kouvola is the municipality a visitor
  searches for, so both venues carry it. One registry field if that turns out to read
  wrong locally.
- **Bio Grand says Tikkurila and never Vantaa** on its own site. Vantaa is the postal town
  of the address the directory lists, and it is what the venue picker needs, so the city
  is Vantaa and the district stays out of it.
- **Joutsan Kino 403s a runner, and that turned out to be a routing bug rather than a
  reason to drop a cinema.** It answers an ordinary connection fine and refuses a
  datacenter IP, which is the Finnkino/Engel/Akseli category. It was deleted first, to
  get the cloud run out of `exit=1`, and restored the same day once routing could
  express it -- see "Routing is per site, not per module" below. The deletion was the
  wrong permanent answer: it converted an infrastructure limit into missing coverage,
  and the only thing wrong with the cinema was which IP asked it.
- **This makes the empty-site problem live rather than theoretical.** K-Kino publishes 3
  showtimes and Kino Saimaa 2. A small cinema between programmes will parse zero, and a
  whole site parsing zero fails the run today -- by design, because that is what catches a
  silently broken parse. Fourteen small cinemas is a different bet from two, and the
  escape hatch that item has been waiting for is now the next thing to build, not a
  someday. Until then a quiet week at one cinema turns the run red.

### Vista sweep — tried and failed (2026-08-27)
Guessed 45 plausible Finnish cinema domains and probed each for `/xml/TheatreAreas/`.
**Zero hits** beyond Savon Kinot itself. Also dead: account-level Azure blob enumeration
on the shared asset host (`mcswebsites...?comp=list` -> 404, though a *known* container
lists fine), and searching for the platform vendor's client list.

This said the blocker was a real list of Finnish cinema domains, and that getting it
once would make the sweep trivial. **Both halves were wrong, settled 2026-08-29.** The
list exists and is one rendered page away (see the nytleffaan.fi entry above), and having
it did not produce a single Vista site.

**Re-swept with the real list: still zero.** 103 hosts probed for `/xml/TheatreAreas/`.
Ten answered 200 and every one of them was a soft-404 serving the site's own HTML. The
first bytes are not `<?xml`, so status alone would have reported ten false hits. Savon
Kinot looks like the only Finnish Vista deployment leaving the XML services open.

The sweep was blocked for two days on a *presumed* missing input, and that input turned
out not to be what made it fail. It was cheap to test and was tested last. Test the
assumption that is blocking the work before working around it.

### Next providers
- **eTiketti is done** (2026-08-30): fourteen hosts, sixteen venues, see the sweep entry
  above. Cinema Niagara is the one host left behind, and it needs parser work rather than
  a `SITES` entry -- its screenings are server-rendered in a second eTiketti template.
- **Nexxo is done** (2026-08-30): six cinemas on five hosts, see the sweep entry above.
  Kino Metso, the touring locationid at kinoaurora.fi, is the piece left -- it needs the
  room-splitting `match` that `etiketti.py` already has.
- **Cinema Niagara** is the other parser-shaped leftover: eTiketti's second template.
- **Vista is not the lead and should stop being described as one.** Tampere's Niagara,
  named here as a candidate to test, is an eTiketti site. Cinamon and other non-Finnish
  Vista users are untested and are the only remaining reason to keep the signature
  (`/event/{id}/title/{slug}/`, `/websales/show/{id}/`) written down at all.
- **Johku** is now a confirmed platform with four known Finnish cinemas. Worth a parser
  once one of them is shown to render `rs-johku-schedule` server-side.
- **Korttelikinot** (Helsinki: Orion, Riviera, Korjaamo, Regina) — they cooperate, so there
  may be a shared listing. Not yet probed.
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

Adding a venue to an existing platform is already one line. Adding a platform costs
four files plus five frontend edits, which is the thing to fix at six providers:

- [x] **`data/providers.json`**, generated by `scripts/build_providers.py` from
      `scripts/providers/registry.py`. The frontend derives `CHAIN`, `SOURCE`, the
      provider loop, the footer call to action and the chain palette from it. It carries
      **no `generated` field** on purpose: both push paths run the generator, so identical
      bytes mean no diff and no conflict. index.html keeps a hardcoded fallback list for a
      missing file or a stale service worker.
- [x] **One generic runner**, `scripts/providers/run.py <module>... | --where cloud|local`.
      Contract: every adapter exposes `SITES` (each site carries its own `provider` id,
      because one module can serve several) and `fetch_site(site) -> {venue_id: [shows]}`.
      The five `fetch_*.py` orchestrators are gone; the local wrapper calls
      `run.py kinoakseli` directly (verified locally 2026-08-27: 10 showtimes,
      3 dates, 0 failures).
- [x] The cloud workflow loops over `registry.py --cloud`. Failure flag goes to
      `$RUNNER_TEMP`, never into a commit; `git add data run-*.log` replaced the explicit
      list (`run.log`, Finnkino's, does not match that glob). Data is committed *before*
      the failure check, so one dead provider still publishes the rest. The enrich gate
      also reads its exit code from `$RUNNER_TEMP` (2026-08-28): it used to
      `grep -q "exit=0"` over run-enrich.log, a substring search on a file that also
      carries arbitrary film titles and TMDB error text — the same class of silently
      passing check that hid breakage for days once before. The `exit=` line stays in
      the committed log for humans; the machine reads the temp file.
- [x] `riviera.py` is parameterised by base URL (`base`, `ajax`, `listing`, `area` on
      the site dict). It did not end up buying Gilda, but it is the right shape anyway.
- [x] **Repertory titles**: `clean()` in enrich_tmdb strips a trailing "(YYYY)", bracketed
      format noise ("(dub)", "(re-release)", "(liveaction)", 2D/3D/IMAX/4K), a trailing
      ", suomeksi", and a known-list event prefix. Exact list, not a `^\w+:` pattern,
      which would strip "Dyyni" from "Dyyni: Osa kolme". Only the search string is
      cleaned; `norm()` still keys on the published title, staying in agreement with
      `normTitle()`. 8 of 9 misses fixed.

Still open from this pass:
- [x] `venues-{provider}.json` was rebuilt from live venues only, so a venue whose parse
      broke silently vanished from the picker: its still-committed area file became
      unreachable, and the health line stayed green because the venues file got a fresh
      `generated`. Fixed 2026-08-28: the file now lists every venue of the site, and a
      venue with no shows and no file gets an empty one — the same two rules
      fetch_data.py already applied to Finnkino, for the reasons stated there. The file
      is still only written when at least one venue produced shows, so a fully dead site
      keeps its old `generated` and the health line can go stale honestly.
- [x] A whole site parsing zero showtimes fails the run (a single empty venue only
      logs), and the legitimately empty site this told us to watch for did turn up. It
      is handled rather than still being watched: `common.EmptyProgramme`, raised only on
      positive evidence that the listing rendered its own empty state, is counted as
      `empty` and not as a failure, and a listing that still lists films while the parse
      yields nothing keeps failing. `tests/test_empty_programme.py` pins both halves.
      This copy stayed unchecked after that landed, the same way the repertory-title item
      below did.
- [x] **Repertory titles defeat the TMDB search** -- superseded by the `clean()` entry
      above, which is the same item written twice. This copy stayed unchecked after the
      fix landed, so the backlog advertised work that was already done: "Trainspotting
      (1996)", "Vauvakino: La La Land", "KESÄKINO: Autofiktio" and "BARNSÖNDAGAR: ..."
      are all searched cleaned today. `tests/test_tmdb_queries.py` now pins both halves
      of it -- what gets stripped before the search, and that the exact strand list never
      decapitates "Dyyni: Osa kolme" the way a `^\w+:` pattern would. Remaining misses
      are titles with no TMDB entry at all (music playback nights, shorts programmes),
      which is a `tmdb-aliases.json` job at best.

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
      client_credentials with programmatic refresh needs no browser and no residential IP,
      so it was the one route that could have moved the whole pipeline back to Actions.
      Not being requested: it is an approach to a third party that costs work up front
      with no promise of free access at the end of it. The drafted request at
      moviexchange.com/request-api-access/ was never sent and is not going to be. Reopen
      only if MovieXchange publishes open access terms. Not by asking again.
      Consequence to plan around rather than work around: **the split pipeline is the
      final architecture, not a stopgap.** That promotes the item below from second-best
      to the only remaining fix.
      Unaffected: the MX *CDN* is a public read reached through Finnkino's own
      `moviexchangeReleaseId` (`fetch_data.py`), so mirrored posters and the trailer
      fallback never needed credentials and still do not.
- [x] **Cinema Niagara, Tampere (designed, built and live 2026-09-02).** The one
      eTiketti host the 2026-08-30 sweep left behind, re-probed as an ordinary visitor
      with the pipeline's own user agent: five GETs to cinemaniagara.fi (`/`,
      `/robots.txt`, `/elokuvat/ohjelmistossa`, `/?shows=all`, `/elokuvat/70/the-invite`),
      one HEAD on arthousecinemaniagara.fi, two GETs to kotkanleffat.fi for a
      side-by-side of the two templates. No booking, basket, account or admin path was
      touched and nothing raw is committed.
      **Observed.** arthousecinemaniagara.fi answers 301 to cinemaniagara.fi, which is
      canonical. nginx, no Cloudflare header, no challenge; images on cdn.etiketti.app.
      robots.txt disallows `/salikartta`, `/tili` and `/ostoskori`, the paths this repo
      never reads. The site is eTiketti -- the signature is in every page -- in a *second
      template*. `/elokuvat/ohjelmistossa` is the listing `etiketti.py` already reads:
      `movie-list` container, 20 `item` cards, 20 film links, the same hidden
      `no-results` element Kotka has. Each film page carries its screenings
      server-rendered, but as `<div\n class="item tampere date-3.9.2026">` with
      `<div class="time"><span>16.15`, `<div class="show-price"> 13,00€`, `Paikkoja
      vapaana: 126/127`, tags in `movie-specs` (`<span class="tag">Seniorikino</span>`)
      and no place line, where Kotka prints `<div class="item kotka date-2.9.2026">`,
      `KE 2.9. klo 20.00`, `TRIO 123 | SALI 2<br> Lippu 15,00€<br> Vapaat paikat 27/35`.
      Detail labels read `<span class="label">Kesto </span> 1 h 48 min` with no colon
      (Kotka: `Kesto:</span>`), genres sit under a label literally reading `genre`,
      language `englanti, espanja`, subtitles `Suomi ja ruotsi`, age `ikarajat/fi-12.svg`,
      poster `poster-img` on cdn.etiketti.app as webp with `?w=250`, synopsis in
      `description-container`; Näyttelijät, Ohjaaja, Käsikirjoittaja, Ensi-ilta and
      Levittäjä are printed too, and the shows schema has no field for them. Ticket links
      are `/salikartta?id=NNNNN`, as on every eTiketti site. `/?shows=all` lists 53
      screenings of 26 films over 16 dates, 2026-09-02 to 2026-12-10, each rendered twice
      -- a `desktop` and a `mobile` wrapper, 106 hrefs for 53 ids -- while a film page
      renders each once (film 70: 3 items, 3 ids). Six of the 26 films are pre-sales from
      2026-10-22 on and are not on the listing yet. Prices are per screening: 13,00 (22),
      11,00 (17), 10,00 (9), 8,00 (4), 12,00 (1), and eleven films carry two or three
      different ones. Every screening prints free/total seats, 123-127 of 127, class
      `seats-high`; no sold-out screening was on sale, so the zero case is unobserved
      here. Nine tag strings: Seniorikino, Ensi-ilta, Walhalla - Kuukauden pohjoismainen
      elokuva, Cinemadrome, Viimeinen näytös, Erikoisnäytös, Tekijävierailu, Q&A,
      Ennakkonäytös; Gilda already publishes `Seniorikino` in `method`.
      **Design.** A `SITES` entry against `etiketti.py`, per the platform rule, with the
      adapter taught the second template: an item regex that accepts whitespace between
      `div` and `class` and classes after the date; time from `klo HH.MM` or the `time`
      div; price from `Lippu N` or `show-price`; seats from `Vapaat paikat` or `Paikkoja
      vapaana`; the place falling back to the item's place class (`tampere`) so `match`
      still selects the venue; labels with or without the colon; genres from either
      markup; tags from `movie-specs` into `method`, ` · `-joined, verbatim and
      unescaped; and a Finnish language-name map for `_lang` (the inverse of the client's
      `LN.fi`) so `espanja` becomes `ES-A` instead of vanishing. The read surface stays
      listing + film pages, 21 GETs a run at 1.2 s like the other sixteen hosts;
      `?shows=all` is not read, pre-sales films appear when they enter the listing, and
      screenings are keyed on the `salikartta` id so a duplicated surface cannot double a
      show. Registry: `id="niagara"`, label "Cinema Niagara", host cinemaniagara.fi,
      `book="buy"`, `module="etiketti"`, `where="cloud"` provisionally -- unverified from
      a runner, the first cloud run decides, and one field flips it. Venue `cn-tampere`,
      "Cinema Niagara", Tampere, which becomes the sixth two-chain city, so the accent
      binds against Finnkino #E4551F. Measured with accent_check (normal / Viénot /
      Machado dE00): greens fail deutan (#0E9B63 17.2, #3A7D44 19.1); violet #6A4FBF
      47.0 / 68.1 / 60.6 and blue #1F6FB2 48.6 / 63.6 / 56.8 both clear it and match no
      other chain's hex. Seats: `soldOut` from `free == 0`, the rule the sixteen eTiketti
      sites already use; counts are not published, because the shows schema has no
      `free`/`total` field, runs are hours apart, and a count shown as live would be
      false. That display is a separate decision. Landing pages carry no seat or sold-out
      state, as now.
      **Expected.** Registry 32→33, eTiketti `SITES` +1 (adapter venues 57→58, 74→75 in
      all), `tests/test_etiketti_templates.py` with hand-written fixtures for both
      templates, `data/providers.json` regenerated. After an authorised run:
      `data/venues-niagara.json`, `data/area-cn-tampere.json`, mirrored posters, pages
      `/teatteri/cinema-niagara-tampere/` and `/en/theatre/cinema-niagara-tampere/`
      (canonical 168→170, sitemap 169→171), Tampere city pages regenerate. README 74→75
      venues, 32→33 providers, cities unchanged at 52. Open before Phase 2: the accent
      pick between the two measured, and whether seat counts are ever displayed.
      **Decided and built (Phase 2, 2026-09-02).** Accent `#6A4FBF`. Venue id `cn-tampere`,
      permanent. Seats are read only to derive `soldOut` from zero free seats; no capacity
      field and no count on screen, because data fetched a few times a day would read as
      live while going stale, and that display stays deferred. `etiketti.py` reads both
      templates with one set of regexes, each an alternation of exactly the two shapes:
      the item tag matched on whitespace with the class attribute captured whole and the
      date and place read out of it (`_place_class`, which is what lets `match: "tampere"`
      select a venue the template never names); time from `klo` or the `time` div; price
      from `Lippu` or `show-price`; seats from either phrase; labels with or without the
      colon; genres from `movie-genre` spans or the `genre` label; `movie-specs` tags into
      `method`, ` · `-joined, entity-decoded, whitespace-collapsed, wording kept. Shows are
      keyed on the `/salikartta?id=` href per site, so a page that renders a screening
      twice publishes it once; a row without an id is keyed on film, start, place and
      auditorium together, because a shared host screens one film in two halls at the
      same minute and film-plus-start alone would have folded them, and the key is
      recorded only once a registered venue took the row, so a malformed copy that
      matched nothing cannot suppress the valid copy after it. `_lang` now reads
      Finnish language names through `LANG_NAMES`, the inverse of the client's `LN.fi`
      and asserted equal to it, matched on the first four letters so "suom./ruots." and
      "englanniksi" still resolve; a site that prints "espanja" now publishes `ES-A`
      where it published nothing. The ticket href is published and never fetched -- the
      test stub raises on any `/salikartta` request. Kotka's template parses exactly as
      before: the fixture asserts place, room, `15€`, 27 free seats, `12.5€`, sold out at
      0/120, and empty `method`. Tests: `tests/test_etiketti_templates.py`, 32 of them --
      both templates, four opener variants, two dates with +03:00 and +02:00, responsive
      duplicates and a thrice-repeated id, a no-id screening repeated by markup collapsing
      to one show while two venues or two halls at the same minute stay two, a malformed
      same-id copy not suppressing the valid one, the id winning over the composite,
      three prices on one film, poster/synopsis/
      runtime/age/genres/language, tags, seats to soldOut both ways with no count in the
      show, missing and malformed optionals, an item without a time skipped, credits not
      published, a listing of films whose pages render nothing failing the run and keeping
      the previous file, the platform's empty state, registry and SITES agreeing, the
      venue id unique, the accent at or above the set's worst same-city pair and above
      40 in all three models, and a sold-out Niagara show rendering into a page and its
      JSON-LD with no availability word anywhere. The roster count in
      `test_etiketti_aud.py` moves 16→17. Seventeen mutations, each restored byte-identical
      and each red: single-space item tag, no trailing class, dedup removed, time div
      branch removed, show-price branch removed, second seats phrase removed, soldOut at
      one seat, place fallback emptied, tags dropped, day and month swapped, colon
      required on Kesto, whole-word language names, genre label removed, accent set to a
      green, fallback key back to film-plus-start, key recorded before the venue match,
      the id no longer preferred. Full suite 634, inline JS clean, providers.json
      regenerated to 33, pages
      built twice with nothing written.
      **Live (first cloud run, dispatched 2026-09-02 10:40Z, data commit a7b2b8f7).** The
      runner read cinemaniagara.fi without a challenge, so `where="cloud"` stands.
      run-etiketti.log: `[niagara] Cinema Niagara: 47 showtimes, 12 dates`, 4 synopses
      merged, 25 venues and 874 showtimes across the module, 0 failures, exit 0, and no
      `/salikartta` request anywhere in it. Verified from the committed data, not the
      Actions output: 47 shows, 12 dates 2026-09-02 to 2026-09-17, 47 distinct
      `salikartta` ids, every start Helsinki-offset, no `free`, `seats`, `total` or
      `capacity` field on any show, `soldOut` a bool on all 47 (none sold out today),
      prices 13€ ×22, 11€ ×17, 10€ ×6, 12€ ×1, 8€ ×1 with eleven films carrying two
      prices, tags Seniorikino 13, Ensi-ilta 6, Viimeinen näytös 2, Erikoisnäytös 2,
      Tekijävierailu 2, Q&A 1, Ennakkonäytös 1, Walhalla 1; poster, runtime, genres and
      language on 47 of 47, age on 38, TMDB id on 39, trailer on 24; language values use
      DA, EN, ES, FI, FR, IT, NO, SV and TR, every one a code the client names, which is
      the `LANG_NAMES` map doing its work. Posters: 31 downloaded, 0 failed, every `img`
      a `data/posters/` path. Pages: `/teatteri/cinema-niagara-tampere/` and its English
      twin written, 14 synopses on the Finnish one, both Tampere city pages regenerated,
      none of the four carrying a sold-out or availability word. Counts, measured:
      providers 33, venues 75, canonical pages 170 (85 per language), sitemap 171.
      accent_check now finds the Tampere pair in the venue data: Finnkino vs Cinema
      Niagara 47.0 / 68.1 / 60.6. The 6 pre-sales films from 2026-10-22 on are not
      published, as designed, until they enter the listing. **Deferred**, recorded above:
      exact seat counts on screen; credits.
- [ ] **Language codes normalised end to end (code landed 2026-09-02, sw.js v99).** Four
      codes in the committed data were not in the client's name table, each a defect
      somewhere else, and the landing pages had aliased them meanwhile (see "The landing
      pages belong to the product"). Re-measured before editing, across data/area-*.json:
      `TU-A` 62 rows, all Finnkino, all "Keltaiset kirjeet", which the five other chains
      screening it tag `TR-A` (51 rows); `MA-A` 3 rows, Finnkino, "I'm Game", a
      Malayalam-language film -- the TMDB cache stores no original language, so this one
      rests on the film rather than on a cross-check; `XX-S` 46 rows, all Nexxo sites,
      every one in the subtitle role, beside `FI-A` (32), alone (8), `EN-A` (3) or `SV-A`
      (3), Nexxo's "no subtitles"; `LT-A` 1 row, "Svečias – The Visitor"; `ML` none. 241
      of 5310 rows carry no language at all.
      **Code.** `fetch_data.lang_tag` maps language components through `FINNKINO_LANG`
      (`SE`→`SV`, `TU`→`TR`, `MA`→`ML`); the role letter is never mapped and a compound
      keeps its shape, `.TU-SE-S` → `TR-SV-S`. `nexxo._lang` drops `XX` from the subtitle
      role before the join, so `FI-A, XX-S` publishes `FI-A` and a bare `XX-S` publishes
      "", the value rows without language information already carry; `XX` in the audio
      column is not dropped, because it has never been seen there and a raw code on the
      page is the visible signal the tables are built around. The client's `LN` gains
      `LT` and `ML` in fi, sv and en, appended after `TA` in all three so the existing
      order is untouched, and the generator's fi/en mirror gains them too.
      **Still open, which is why the marker is.** The committed data turns over only when
      the adapters run: Finnkino from an ordinary connection on the local schedule, Nexxo
      on its next provider run. Measured after the 2026-09-02 10:45Z cloud run: `XX` is
      gone from the data (46 → 0), `TU-A` 62 and `MA-A` 3 remain, all Finnkino, awaiting
      the local run; `LT-A` 1 is a real code and now named. `CODE_ALIAS`, `NO_SUBTITLES` and `LN_EXTRA` in
      `build_pages.py` stay exactly as they are until a re-measure of data/area-*.json
      finds no `TU`, `MA` or `XX`; then they go, with the tests that name them, and this
      item closes. Not done in the code commit: no live data refresh.
      Tests in `tests/test_lang_normalization.py`: TU/MA in both roles, SE and compounds
      unchanged, all 673 other two-letter codes pass through, the map is exactly three
      entries; XX-S vanishing beside FI/EN/SV and alone, XX beside a real subtitle code,
      existing Nexxo semantics including kept duplicates, every output a well-formed tag
      list or ""; LT and ML named in all three client tables, one key order across the
      tables with the additions last, the names rendering through `lang_parts`; the alias
      set pinned by value and agreeing with the client's names, and the four legacy
      shapes in the data still rendering as words. Provider modules are imported inside
      the tests, for the `EmptyProgramme` reload trap recorded under "Savon Kinot names the
      venue inside its own room".
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
- [x] **Commit run.log only on failure -- decided against 2026-09-01.** The premise does
      not survive being measured, and the two things that would break are the failure
      signal itself.
      **The noise is not extra commits.** Across the last 300 commits, no routine run has
      ever produced a commit made of run logs alone: the logs ride inside a data commit
      that happens anyway (the only two log-only commits in that range are throwaway probe
      notes). And it is already bounded by content -- an unchanged log is not committed,
      so f4606c8 recorded 5 of the 9 cloud logs and e8458a70 recorded 4. What is left is
      3-9 files and 10-81 changed lines sitting inside a commit that already rewrites
      25-99 data files, about eight times a day.
      **A green run that commits nothing leaves the last red log on `main` forever.**
      Tripped rather than reasoned about: with `run-etiketti.log` at `exit=1` and
      `run-nexxo.log` green, `check_runs.py` reports the failure on day one and reports
      the identical failure on day two, because nothing overwrote it. That is exactly the
      `run-vista.log` incident its docstring records. Deleting the log instead empties the
      directory on an all-green day, and the "no run logs" branch returns 1.
      **And the green logs are the record.** README calls them authoritative and CLAUDE.md
      routes every pipeline verification through them; a run that publishes half a venue's
      showtimes exits 0, so the per-venue counts in a *successful* log are the only place a
      soft regression is visible at all. Truncating a green log to its summary and `exit=`
      lines would keep `check_runs` and the `logs.yml` trigger working, and would throw
      away precisely that, to save about 40 lines a run.
      One part of the item holds: the failure *signal* would have survived, since a
      failing run still commits a log and still fires `logs.yml`. What stops it is the
      stale red on the runs in between. Reopen only if run logs ever start forming commits
      of their own.
- [x] Finnkino no longer publishes an empty area file when a venue returns no shows: it
      keeps the previously committed one, matching `run.py`. A file is still written when
      none exists, because `areas.json` lists every site regardless of shows and the picker
      would otherwise link to a 404. New log line: `N venue files written, M kept as-is`.
- [x] Dropped `data/attrs.json` and `data/film-sample.json`: written every Finnkino run,
      read by nothing.
- [x] Retry/backoff for transient API errors (2026-08-28). One transient 502 counted as
      total site failure for BioRex, Kino Akseli and Orion, and the next cron is four
      hours away — a packet loss cost a provider a quarter of a day. Shared
      `providers/common.py::fetch(url, headers, data, tries=3, backoff=5, opener)`,
      the same loop shape etiketti/gilda/vista/nexxo/riviera already carried
      individually. Named `common`, not `http`: run.py and fetch_data.py put providers/
      first on sys.path, and a local http.py would shadow the stdlib package urllib
      itself imports. The five adapters with their own get() loops migrate to common
      opportunistically, one per change — nine working parsers do not get touched in
      one sweep. All nine adapters now share it (finished 2026-08-28, one per commit): eTiketti,
      Vista, Gilda, Nexxo, Riviera followed BioRex, Orion and Kino Akseli. Each keeps its
      module-level `get()` wrapper so call sites were untouched, and each passed through
      its own timeout and backoff instead of silently adopting common's defaults --
      Vista 40 s, Gilda 45 s, Nexxo backoff 6 to wait out a rate limit.
      One deliberate narrowing as each lands: the local loops wrapped the *parse* in the
      retry too, `common.fetch` retries only the request. A 200 with a complete but
      non-JSON body is a shape change to look at, not a transient to sit out, and a body
      truncated in transit raises inside `fetch` where it is still retried.
      Each keeps its module-level `get()` wrapper so call sites are untouched, and each
      migration must preserve the loop's own tries/backoff/timeout rather than silently
      adopting common's defaults.
- [x] **Refresh on resume, not only on date rollover** (2026-08-28). An installed PWA is
      resumed rather than reloaded, so boot ran once and `providerMeta` stayed frozen while
      `Date.now()` moved: the source line counted upward ("Finnkino 6h") on a phone while a
      desktop tab reading the same repo said 0h. The numbers were honest — the app really
      was holding six-hour-old showtimes and sold-out flags, because `loadSchedule` is
      gated on `jsonCache` and the old `visibilitychange` handler only refetched when the
      day changed. The service worker was never involved; it is network-first and was never
      asked. Threshold is 10 minutes because Pages serves data with `max-age=600`, so a
      keener refresh would be answered from the HTTP cache anyway. `fetchVenueLists` was
      split out of `loadAreas` for this: refreshing through `loadAreas` would re-run
      `fillAreaSelect` and bounce the reader off their selected venue.
      Still open: a tab left visible all day never fires `visibilitychange` and so never
      refreshes. A timer would cover it; not added, because the fix for the reported
      symptom should not quietly grow a polling loop.
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
      mid-run kills actually happen. `common.write_json` / `write_text_atomic`
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
- [x] **A cached TMDB rating stops being permanent** (2026-09-01). The item was
      misdescribed and the real defect was larger. It said the re-check reuses the cached
      rating "since reusing the movie id skips the search call". It does not: the movie
      detail request the re-check already makes carries `vote_count` and `vote_average`,
      and the code overwrites both from it. Reusing the id skips the *search*, not the
      read. The one place cached figures do carry over is an entry with no `mid` at all,
      where there is nothing to read them from, and that is correct.
      What was actually wrong is that most entries were never re-checked. The skip was
      `complete and (c.get("v") or c.get("c") == today)`, so **a trailer stopped the entry
      ever being read again**: its rating and vote count froze at whatever they were that
      day.
      Measured against the committed `data/tmdb-titles.json` on 2026-09-01: 156 entries,
      96 with a trailer, and 71 of those 96 last read on 2026-08-27 -- five days, with
      nothing in the code that would ever read them again. (First measured at 154 / 94 /
      71 earlier the same day; three cloud runs landed in between and the number that
      matters, the 71 nothing would re-read, did not move.) A vote count moves fastest in
      the weeks after release, which is when a film is in these cinemas.
      Now age decides. `due()` is a pure function over the cache: uncached or incomplete
      is fetched, complete-without-a-trailer keeps its daily re-check looking for one, and
      complete-with-a-trailer is re-read once it is `RATING_MAX_AGE` (7) days old --
      `REFRESH_BUDGET` (12) of them a run, both overridable in the style of
      `KINO_PAGE_BUDGET`. The budget is not a running cost: 94 entries at a seven-day age
      come due at about thirteen a day, roughly two per run. It is there for the catch-up,
      because without it the first run re-reads all 71 at once, stamps them with the same
      date, and they come due together again a week later for ever. What it defers is
      printed, since a ceiling nobody can see reads as "everything is current".
      Projected against the 124 titles in today's area files: unchanged on the day it
      landed, because nothing had passed seven days yet, and from 2026-09-03 a run fetches
      62 of them with 12 rating refreshes and 41 more deferred to later runs. A refresh
      costs two requests when TMDB has a Finnish overview and three when it does not.
      Unchanged on purpose: `MIN_VOTES`, `n` travelling with the score so the threshold can
      be retuned without re-fetching, and a missing field counting as incomplete so a gate
      change costs one pass rather than a cache wipe.
      **The success path was wrong too, and a review caught it.** `due()` decided
      correctly and everything after it did not: if both localized `/movie/{id}` requests
      failed while `/videos` answered, the pass wrote the *old* rating stamped with
      today's date, emptied the cached `fi` and `en` text, counted the rating as re-read,
      and parked the entry for another seven days on figures nothing had looked at. So a
      film whose id had become unreadable would report itself refreshed for ever while
      losing its synopsis on the first failure.
      Three changes, all narrow. The synopsis slots are seeded from the cache instead of
      from `""`, and only a response that *arrived* replaces either -- so a failed
      request leaves the text alone and a response TMDB really has emptied still clears
      it. `c` moves to today only when a detail response carried rating and vote data,
      which is what an entry is parked on; a title that matched no id at all is not in
      that state and keeps its daily re-check. And `due()` hands back the refresh keys
      rather than a count, so the pass can say what became of each:
      `[enrich] rating refresh: N scheduled, N re-read, N failed and still due, N
      deferred (budget 12)`, printed after the loop because success is not knowable
      before it.
      **Which of the backlog a run takes is decided by the last attempt, not the last
      success.** Ordering on `c` alone starves the queue, which is the second thing the
      review found: an id that can never be read keeps `c` where it is, ages further
      every day and so outranks everything else for ever, and a dozen of those would hold
      the whole budget on every run while the rest of the backlog never moved. `a` records
      every attempt, success or failure, and it is what the queue sorts on -- least
      recently attempted first, an entry never attempted ahead of all of them. `c` still
      decides whether an entry is *due*; `a` decides whose turn it is. So a failing id
      comes back round rather than camping at the head, and the log still says so:
      `N scheduled, 0 re-read, N failed and still due` on every run it takes part in.
      `a` is deliberately not part of `is_complete()`. It is this pass's own bookkeeping
      rather than anything the client reads, and requiring it would cost a full re-check
      pass to introduce -- absence already means "never attempted", which is exactly the
      state that sorts first.
      **And it has to be recorded even when the title aborts**, which the first version
      of it was not. `a` was written just before the cache entry, after the video
      request, so a title that read its detail and then failed on `/videos` fell to the
      per-title `except`, skipped the write entirely, and kept an entry saying it had
      never been attempted -- back at the head of the queue on the next run and every run
      after, which is the starvation `a` exists to stop, reached through the one path
      that skips the write. A scheduled refresh that got as far as being attempted now
      records it from the `except` as well, and only that: `c`, the rating, the votes,
      the synopses, the trailer and the id stay whatever was cached, so the entry keeps
      everything it had and stays due. Guarded so that an exception *after* the write
      cannot put the old entry back over a refresh that did succeed. Found by review;
      the tests that covered the earlier hole all failed inside the detail handler,
      which is the one place the code already guarded.
      **A rating needs both halves of the pair.** The gate was `"vote_count" in d`, so a
      response carrying only `vote_count` set the rating to 0 over the top of a real one
      and stamped the entry as read, and one carrying only `vote_average` was not noticed
      at all. Both fields must be usable numbers or neither is taken, and zero counts as
      usable -- a film nobody has voted on comes back with 0 and 0, and reading that is a
      successful read that `MIN_VOTES` then gates on its own.
      Covered by `tests/test_tmdb_recheck.py`, which tests the decision rather than the
      network: 22 tests, 15 over a fabricated cache and 7 driving `main()` with TMDB's
      three endpoints stubbed by URL. Each verified by breaking the code under it --
      restoring the old trailer skip, removing the budget, refreshing newest first,
      reading an unknown age as fresh, dropping `n` from completeness, dropping the daily
      no-trailer check, making every trailer entry always stale, not fetching an uncached
      title, resetting the synopses to empty, stamping the date unconditionally, counting
      a failure as a refresh, treating any detail response as a read, keeping stale text
      over an empty overview, dropping the id when the read fails, accepting half of the
      vote pair, keying the gate on either half alone, rejecting a legitimate zero,
      ordering the queue on the last success, never recording an attempt, recording one
      only on success, recording none when the title aborts, rolling a good write back,
      and rewriting more than the marker on the way out. Twenty-six breaks, all red.
- [x] **The same defect on the Finnkino path, fixed 2026-09-01.** `fetch_data.py` carried
      the identical rule and the identical shape: `data/tmdb.json` held 59 entries, 46
      with a trailer and 45 of those last read on 2026-08-28. It was worse than the cloud
      pass, because its detail request is conditional on `not votes or not gids` -- so
      even the daily half never re-read a rating it already held, and an age rule alone
      would have scheduled the entry, fetched nothing and stamped it current.
      The schedule is `providers/refresh.py` now, shared by both passes rather than
      written twice, which is how this defect came to exist in two files and be fixed in
      one. They differ in one thing and pass it in: what a complete entry looks like. The
      Finnkino cache carries no synopsis and no poster, because Finnkino publishes both
      itself, so the title cache's predicate would mark every row incomplete for ever.
      Fixed there and not only in the schedule: a failed video read used to write an
      empty string over a cached trailer.
      Verified without live Finnkino -- that file answers a datacenter address with a
      Cloudflare 403, so no runner can run it and there is no token here. The pass was
      lifted out of `main()` into `enrich_cached_ratings()` so it can be driven directly
      with TMDB stubbed by URL: 18 tests over both cache shapes, the failure paths, and a
      two-run rotation over a backlog larger than the budget. The next run from an
      ordinary connection is the operational check, not the proof.
      One thing only a real pass could have caught: the first fixture omitted `y`, the
      release year the search loop reads, and every cached-entry test passed anyway
      because none of them reached the search. An uncached film raised `KeyError: 'y'`.
      That is the argument for driving the pass rather than a reimplementation of it.
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
Segmented `FI | SV | EN` in the header, replacing the two-state toggle. A toggle that
shows the language you would switch *to* works for two and breaks at three: you cannot
see where you are, and the third is two taps with nothing saying so. The control is the
same `.seg` pill already used for Leffat/Ajat, so it is a pattern the page already has.

- **`flex:0 0 auto` on the pill is required.** It clips its own overflow, so under
  flex pressure it does not widen the row -- it silently eats "EN". A prototype caught
  this; nothing on screen said anything was wrong.
- **`#themeToggle` needed `flex:0 0 38px`.** Fixed width with no shrink guard, so the
  language control squeezed the circle into an oval. Latent since the header was written
  and only reachable once something else shared the row.
- At 320 px the wordmark, three segments and the theme circle do not fit at the 520 px
  sizes. A `max-width:360px` block tightens all three. Measured: 103 + 86 + 38 px plus
  gaps against 292 px of usable row, zero overflow.
- **Swedish titles fall back to Finnish, not English.** No provider gives us a Swedish
  title yet, and the Finnish distributor title is what is printed on the ticket and on
  the cinema's own page, so an English one would send a Finland-Swedish reader looking
  for a film under a name nothing local uses. English mode is different: there the
  reader has opted out of local names.
- **Cities get Swedish names, and only for display.** Helsinki -> Helsingfors, Turku ->
  Åbo, Vaasa -> Vasa, Porvoo -> Borgå. `cityGroups` stays keyed by the Finnish name, and
  so does the `city:` value in prefs and in the `?area=` links the generated pages carry,
  so translating the key would break every deep link ever published. Cities with no
  established Swedish name keep the Finnish one, which is what Finland-Swedish usage does
  for monolingual municipalities anyway.
- **Sorting is per language now.** Every list sorted on Finnish collation regardless of
  UI language, recorded above as an English gap; one `Intl.Collator` rebuilt on switch
  closes it for all three. Free, measured.
- `<html lang>` follows the UI language. It never did, even with two.
- **The Swedish strings are drafted, not translated.** They need a native Finland-Swedish
  reader before anyone leans on them; no measurement here can check them. The contact
  line added on 2026-08-30 ("För biografer: kontakt
  och begäran om borttagning") is in the same state, and it is the one string a cinema
  is most likely to read, so it belongs at the front of that review.

**Genres** were the last thing still Finnish in Swedish mode, because
`data/tmdb-genres.json` carried `fi` and `en` only and `genresOf` falls through to the
provider's own string for a language it has no map for. The enrichment pass now asks for
`sv-SE` as well -- one more request per run, not per film.

Written to degrade rather than fail: `fi` and `en` remain the bar for writing the file at
all, and Swedish is included when it arrives and omitted when it does not. Requiring all
three would have let one Swedish outage delete the Finnish and English maps too, which is
a worse failure than the one it guards against, and the client already falls back
gracefully.

**Verified 2026-08-30**, on the run that followed: `run-enrich.log` says
`genre names written (19 genres, en+fi+sv)` and the map carries a real `sv` slot. TMDB
honours `sv-SE`; it does not fall back to English wholesale. **13 of 19 Swedish names
differ from the English** (Äventyr, Animerat, Komedi, Kriminal, Dokumentär, Familj,
Historisk, Skräck, Mystik, Romantik, TV-film, Krig, Västern).

Of the six that match English, five are correct Swedish -- Action, Drama, Fantasy,
Science Fiction and Thriller are the words Swedish uses. **One is a real gap in TMDB's
own list: id 10402 comes back as "Music", where Swedish is "Musik".** Finnish has the
same kind of hole in the other direction: id 10770 is "TV Movie" untranslated, where
Swedish has "TV-film".

That is worth fixing rather than tolerating, because 10402 is live: **107 showtimes
across 9 films carry it today**, so a Swedish reader sees one English word in a row of
Swedish ones. `GENRE_FIX` in `enrich_tmdb.py` renames those two after the response
arrives, and only for an id TMDB actually returned, so it can never invent a genre.
Applied to the response rather than hand-edited into `data/tmdb-genres.json`, which the
next run would overwrite; the committed map was brought into line through the same
constant and the same serialisation, so the next run produces a byte-identical body.

**Exercised against live TMDB on 2026-08-30, not left to the next run.** Three genre-list
requests with a real token: 19 genres per language, exactly one override firing in `fi`
(`TV Movie` -> `TV-elokuva`) and one in `sv` (`Music` -> `Musik`), none in `en`, and the
serialised body byte-identical to the committed `data/tmdb-genres.json`. Both ids are in
TMDB's response, so the `if k in names[slot]` guard passes rather than silently skipping.

**The check on the next cloud run is therefore a non-event, not a log line.** The file is
written only when the body changes, so a working override means `run-enrich.log` carries
*no* `genre names written` line and `data/tmdb-genres.json` is untouched in that run's
commit. A diff on that file, or the line reappearing, means `GENRE_FIX` stopped applying
-- most likely because TMDB translated one of the two upstream and the id no longer needs
overriding, which is a reason to delete the entry rather than to debug it.

`fi+sv+en` in the log answers "did Swedish arrive" and says nothing about whether the
Swedish is right. Reading the 19 values is what found the one that was wrong. The poster
count failed the same way.

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
      (2026-08-30, sw.js v71). The audit question for every bordered rounded thing:
      is it a control, a classification, or just text wearing a container? Applied:
      form controls (select, search, star) lost their drop shadows — the border is
      the affordance, the shadow was the one treatment making the header read as a
      stock component library; `.fmt` tags (2D, ANNISKELU, runtime, price) lost box
      and border entirely and are now small uppercase muted type, because they are
      passive metadata and were dressed like buttons next to the stubs people actually
      tap; the premiere tag keeps weight through the accent colour instead of a border.
      `.rating` (K-12) and `.agelim` keep their boxes: an official classification is
      the chip shape's job. Filter chips dropped from the full pill to the stub's 7px
      radius so the tools row reads as one primary segment (Leffat/Ajat, still a pill)
      plus quiet toggles, not four equal capsules; the mobile padding measurements from
      the 375px fit stay untouched. Hover states added where transitions existed but
      no state did (.chip, .day, .seg, .lg-btn, .cal-day, select, .fav, title links),
      and `.stub:active` mirrors `:hover` so a touch tap flashes the same inversion —
      hover never fires on touch. Date labels get `text-overflow:ellipsis`: at 320px
      "Huomenna" hard-clipped mid-glyph. Deliberately untouched: stub shadow and
      perforation, the score ring, chain rules, and the date chips' two-line layout.
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
      does `TAGS_RE.sub` then `html.unescape`, so a source page's entities arrive in the
      JSON as live HTML metacharacters — a stored-XSS surface fed by nine third-party
      sites, and a rendering bug on harmless titles ("Movie &lt;3" ate the rest of its
      line). One `esc()` (`&<>"'`) applied at every interpolation of provider data, plus
      `safeUrl()` on every href/src from provider JSON (rejects non-http(s) schemes, so
      a hostile booking URL cannot be `javascript:`; scheme-less stays allowed for
      repo-relative poster paths). Adapters keep publishing verbatim text on purpose:
      the raw title is the key for normTitle(), films-extra.json and tmdb-aliases.json,
      so escaping at the source would silently re-key everything. Audited by grepping
      every `${'{'}` inside HTML-producing template literals and classifying each
      interpolation; the non-escaped remainder is internal (L strings, locale month
      names, digits, ISO dates, pre-escaped glyph markup).
- [x] **The background revalidate has to bypass the HTTP cache** (2026-08-30, sw.js v54).
      The refresh was a plain `fetch(e.request)`, which is answered from the browser's own
      HTTP cache. Pages serves `max-age=600`, so the refresh was handed the same stale
      body the HTTP cache already held and wrote it back into the SW cache -- the stale
      copy renewed itself on every load and the app could sit on it well past ten minutes.
      Caught from a screenshot: Cinema Orion's posters were missing on the live site while
      the origin had them, and `caches.match` and a page `fetch` both reported the *old*
      `generated` while curl got the new one. Two caches in series, and only one of them
      was being told to revalidate. `fetch(new Request(req, {cache:'no-cache'}))` fixes
      it: conditional against the origin, so a 304 is still cheap.
      A service-worker cache sits *in front of* the HTTP cache. Both are consulted, and
      stale-while-revalidate is only as fresh as whatever the inner cache hands back.
- [x] **Data JSON is served stale and revalidated behind** (2026-08-29, sw.js v48).
      Reverses the network-first rule for `data/*.json` only; the page itself stays
      network-first so a fresh index.html still always wins online. The argument: on a
      repeat visit the network wait is the whole launch cost -- measured at 250 ms RTT,
      1.3 s from tap to schedule -- and the thing being waited for changes four times a
      day. The honesty objection is already answered by the app itself: the stale banner
      and the health line key on `generated` inside the JSON, so a cached payload
      truthfully reports its own age, and a launch that fails offline now shows the last
      schedule with an honest age instead of an error after the 8 s abort.
      The SW posts `{fresh: path}` after a background refresh lands on a file it had
      served stale. The page re-reads the active area through the SW (instant, it is the
      copy just cached), compares `generated`, and re-derives only on a real change --
      no spinner, loadSchedule with a warm jsonCache runs synchronously to render. A
      60 s cooldown in the handler stops the loop this would otherwise be, since the
      re-read triggers refreshes of its own. Worst case a visitor sees data as old as
      their previous visit for the first ~2 s of a launch, bounded below by the 10 min
      resume-refresh that already existed.
- [x] **The boot fetches speculatively from prefs** (2026-08-29). Concurrency fixed the
      fetches within a wave; the waves themselves were still serial: providers.json, then
      the nine venue lists (their names come from provider ids), then the schedule file
      (its name needs the venue restore, which needs the lists). Every one of those URLs
      is knowable before the first byte arrives -- venue-list names from the id list, the
      schedule file from the same prefs the restore reads -- so the boot now starts all of
      them immediately and `fetchJSON` consumes the in-flight promise when it reaches the
      same URL. A wrong guess (venue changed on another device) is one wasted request.
      City views store their venue ids in prefs as `cityIds`, because those are otherwise
      only known after the venue lists arrive; the stored ids feed the prefetch only, and
      the live `cityGroups` still decides what `loadCity` loads.
      Measured on a local copy of the repo behind a 250 ms/request server (cold cache, no
      SW, saved venue Kaikki Helsinki, five runs): the schedule fetch used to start at
      1057-1077 ms and now starts at 273-277 ms; data-complete went 1574-1604 ms to
      1307-1312 ms. The completion delta understates the win: the rig is HTTP/1.1 with
      its six-connection cap, Pages is HTTP/2. Found while wiring it: `PROV_FALLBACK`
      had lagged the registry by one provider (Engel), exactly the drift the boot
      comment warned about -- a failed providers.json would have dropped his venues from
      the picker.
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
- [x] **"K-18" quick filter: measured and dropped** (2026-08-30). The predicate was
      right (`rating === 'K-18' || age === 'K-18'`, never inferred from the Anniskelu
      tag) but the case for a permanent chip was not. Measured against the data: 120 of
      3059 showtimes, **3.9%**, against 24.1% for Lapsille and 20.0% for Suom. puhe. Only
      **14** come from the film's own rating; the other 106 are a screening limit, and
      **114 of the 120 (95%) are anniskelu screenings**. So the chip would have been a
      rare subset of anniskelu under a different name, answering a question nobody asks:
      "Lapsille" answers *what can I take my child to*, and nothing answers *I require an
      18+ certificate*. The intent behind it is a night out, and that has a better name.
      Shipped "Anniskelu" instead; K-18 remains findable by typing once `method` and
      `rating` are in the search haystack.
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
      product](#the-landing-pages-belong-to-the-product-2026-09-02)" below. The rest
      of this entry is the state it was written from.
      The 168 canonical venue and city landing pages -- 84 per language -- are where
      venue- and city-specific search results can land. Four additional generated files
      are legacy redirects. Counted 2026-09-01: 172 `index.html` files, 86 per language,
      less the two retired Studio 123 slugs in each.

      Not the only indexable thing here: the homepage is indexed too, and an earlier
      draft of this entry said otherwise. What these pages are is the part a search for
      a named cinema or town can open, and they were built by `build_pages.py` to be
      indexable rather than to be read.

      Prioritised above the README badge on 2026-09-01 because of who it reaches, and
      **no design is decided** -- that is a separate task and nothing here anticipates
      it. Two existing rules will constrain whatever it becomes: `write_if_changed` only
      works while the output stays deterministic, and nothing volatile may go into a
      generated page. The regeneration-drift step in `Checks` enforces both.
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
- [x] **The pressed favourite star reads at 4.5:1 (2026-09-02, sw.js v98).** The glyph
      was painted with `--accent`, which measures 3.25:1 on `--surface` in light theme.
      The 2026-09-01 audit left it there because a text-rendered icon might count as a
      graphical object under 1.4.11, where 3:1 passes, and not as text under 1.4.3,
      where it fails. Settled by clearing the higher bar: `--accent-text`, the token the
      audit created for exactly this case, measures 5.32:1 on `--surface`, so both
      readings pass. Dark theme is unchanged by construction, because `--accent-text`
      and `--accent` are the same #E8B84B there (9.61:1). Measured live against the
      served page before and after, both themes, from computed style: pressed 3.25 ->
      5.32 light and 9.61 -> 9.61 dark; unpressed `--muted` 5.98 / 5.73; the labelled
      first-visit state paints `--ink` at 17.76 / 15.11. None of those moved. The border
      stays on `--accent` (3.25 / 9.61, the 1.4.11 job it was tuned for); hover and the
      shared `button:focus-visible` ring are untouched, and the click path was exercised
      live. `FavouriteStarTest` in `tests/test_theme_contrast.py` resolves the token the
      pressed rule actually names and the token `.fav` paints behind it and computes the
      ratio per theme, so a later retune of `--accent-text` or `--surface` is caught; the
      star moved from `ACCENT_TEXT_ALLOWED` to `TEXT_RULES`, so the routing tests now
      require the text token there. Mutations, each restored byte-identical: glyph back
      on `--accent` (5 red), light `--accent-text` raised to #B8860B (3 red), border
      moved to the text token (1 red), unpressed glyph on `--line` (2 red), pressed rule
      deleted (5 red), light `--surface` darkened to #F4E9CE (4 red); the button surface
      moved to `--bg` stayed green at 4.97 / 10.46, which is correct.
      **The other half of this item was dropped on 2026-09-01**: 18 px title links clear
      2.5.8's spacing exception, by about a pixel, so they pass and there is nothing to
      fix.
- [x] **Light-mode polish + accessibility pass.** Audited against the served page on
      2026-09-01 in both themes, fi/sv/en, at 320/375/720/1440 px. Most of what this item
      stood for was already done and had never been written down: focus order and rings,
      the dialog inert/focus-restore lifecycle on all three sheets, `aria-pressed` on every
      toggle, `aria-current="date"` on the day chips, localized accessible names, a blanket
      reduced-motion rule, no horizontal overflow at any tested width, chain colour used as
      a border with ink text over it, and poster-fallback initials at 4.34-5.24:1. Four
      things were genuinely wrong and are fixed here:

      1. **The selected day chip was unreadable in dark theme.** `.day.active` paints
         `--ink`, which inverts with the theme, while its `small` label was `--accent`,
         which does not: gold on a near-white pill, **1.57:1**. The sibling `<b>` had used
         `--bg` all along and was fine at 16.44:1, which is why it read as a rendering
         fault rather than a colour. Now `--accent-on-ink`: light keeps #B8860B (5.46:1,
         unchanged), dark gets #8A6508 (**4.54:1**).
      2. **The light accent failed as small text.** `--accent` #B8860B is chosen for a 3 px
         border and a focus ring, where the bar is 3:1, and it measures 3.04:1 on `--bg` --
         so every rule colouring text with it failed 1.4.3 while the ring it was picked for
         passed. Eight rules did: `.vrow mark`, `.fmt.prem`, `.trailer`, `.theatre-tag`,
         `.tmdb`, `#fresh summary.bad`, `#sources .src.bad`, `#sources .part`. They now use
         `--accent-text` (light #8A6508, **4.97:1** on `--bg` and 5.32 on `--surface`; dark
         keeps #E8B84B at 10.46). Borders, rings and the wordmark stay on `--accent`, which
         is what its number was chosen for. Dark theme never had the defect, which is how it
         survived: it is invisible to anyone developing in dark.
      3. **An empty result was painted and never announced.** Filtering to nothing swaps the
         list for a sentence while focus stays in the search field, so a screen reader got
         silence -- the same thing it gets from a list still loading. `#listStatus` is now a
         pre-existing polite atomic region and every one of the eight `main.innerHTML` sites
         writes to it: the two empty paths pass `emptyMsg()`, the rest pass `''` so a stale
         "no movies" cannot be announced over a list that has films again. It is markup
         rather than an attribute on the injected node for the same reason `#vnone` is:
         a region that arrives together with its text is not reliably announced.
         `nextDayLink()`'s button stays in the visible block, outside the region.
      4. **The calendar's selected day had no state.** Selection was the `sel` class and
         nothing else, so the grid read as "1, 2, 3" -- while the day chips outside the
         picker had said `aria-current="date"` since they were built. The selectable button
         now says it; the `<span>` a day with no showtimes renders as never does, because it
         is not a control and cannot be current.

      Verified by breaking each of the 26 new guards and watching it go red, then live in
      the browser with transitions disabled -- the 250 ms theme fade had produced nine
      phantom failures and two phantom passes when measured too early, which is worth
      knowing before anyone measures a colour here again. Two findings were left alone on
      purpose and are listed at the top of this file: the favourite star at 3.25:1, where
      whether 1.4.3 or 1.4.11 governs a text-rendered icon is genuinely unsettled, and 18 px
      title links, which clear 2.5.8's spacing exception by about a pixel.

      What the harness could not check: Enter/Space activation, Escape and arrow-key
      navigation. Synthetic key events in the preview browser fire `keydown` but perform no
      default action -- a bare `<button>` with an `onclick` received Enter and logged zero
      clicks -- so those stay verified by hand against the served page, as they always were.

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
- [x] Verify the dispatch actually fires. It is the last step, after the push has already
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
- [x] **Decided against 2026-09-01: a data branch.** Measured first: 195 of the last
      30 days' commits are the pipeline's own (`Update cloud provider data` x116,
      `Update schedule data (local)` x51, `Update schedule data` x28), and `.git` is
      49 MB against 25 MB of `data/`, 21 MB of it mirrored posters. So the churn is
      real. What is not real is a problem: nothing has gone wrong because of it.
      Against that, GitHub Pages serves a branch, and this repo has no build step by
      design -- there is no `deploy-pages` workflow, the client fetches `data/*.json`
      from the same origin as the page, and moving the data off `main` breaks that.
      The three ways out are all worse than the churn: read
      `raw.githubusercontent.com`, which a hard rule forbids after its CDN served a
      two-commit-stale file; add a Pages build that assembles two branches, which puts
      the traffic path behind Actions scheduling; or split off only the logs and
      posters, which reworks `check_runs.py` and `logs.yml` for a smaller win.
      Branching does not shrink history either -- the old blobs stay unless `main` is
      rewritten, and a rewrite has cost this repo once already.

## Documentation state (2026-09-01, ninth pass)

- Ninth pass, 2026-09-01: Kino Metso added four venues and no document moved with
  it. Re-measured against `data/`, the registry and `sitemap.xml`: **32 providers /
  74 venues / 52 cities**, 84 pages per language, 169 sitemap URLs, 4 local providers
  (20 venues), 2933 poster references over 552 mirrored files. The README's Nexxo row
  read 7 providers / 9 venues and is 8 / 13. Two rules moved with the same four
  venues: the accent rule binds in five cities now that Jyväskylä has a third chain,
  and the local half is four providers since Joutsan Kino joined it. Both are
  corrected where they are stated.
  **The Nexxo correction reached the README's table and not its prose.** "`etiketti`
  serves seventeen providers today and `nexxo` seven" survived the sweep three sections
  further down and was found on 2026-09-01 by re-measuring the registry rather than by
  re-reading. A count stated twice in one file needs looking for twice.
- Eighth pass, 2026-08-31: the Nexxo sweep had made the README stale again -- it still
  said 25 providers / 64 venues / 45 cities and 147 sitemap URLs. Every figure was
  re-measured against `data/`, the registry and `sitemap.xml` before being written:
  **31 providers / 70 venues / 50 cities**, 80 pages per language, 161 sitemap URLs,
  4 local providers (20 venues), 2966 poster references over 543 mirrored files. The
  provider table now groups by adapter -- nine rows instead of thirty-one -- and the
  Data sources section points at the single provider list at the top instead of
  carrying a second copy that goes stale on its own schedule. Vista is described as a
  parser with no sites, and the checked-ticket-link rule from the Nexxo link fix is in
  the adding-a-provider steps.
- `README.md` covers: Leffavuoro, **25 providers / 64 venues / 45 cities** (as of the
  seventh pass; superseded above), the
  two-location pipeline with no cloud fallback for Finnkino, the data shape every
  provider writes (including `age`, `gids` and `tmdbId`, and why the last two are
  exact-match only), the three lists worth reading in `run-enrich.log`, a step-by-step
  for adding a provider, and the contact and opt-out address.
  It went a full day stale during the Orion work — check it whenever the provider count,
  the file list or the show shape changes.
- **Bio Rex Kokkola made every count in both files stale and neither was updated with
  it.** README said ten providers / 47 venues / 32 cities and 52 generated pages per
  language; IDEAS said the same in six places. That is the seventh time a carried-over
  count has been wrong here. The counts above were measured against `data/` and
  `teatteri/` on 2026-08-30, re-measured after the eTiketti sweep: 25 registry entries, 64 venue directories,
  45 distinct cities, 73 pages per language, 147 sitemap URLs, 20 on the local half. Two 47s are
  left alone on purpose, both inside dated sections recording what was true on the day.
- `IDEAS.md` (this file) holds architecture decisions, per-provider API research and the
  backlog. Read it before touching the pipeline.
- `cf-worker/worker.js` and the `TOKEN_WORKER_URL` branch in `get_token()` were deleted
  on 2026-08-27. The worker fetched the Finnkino token from Cloudflare's network, was
  never deployed, and solved the problem the local run already solves. Two dead paths into
  the fetcher are two paths that have to keep working for nothing.
- Stray `run-*.log` files in the repo root are committed per run by design (read these,
  not the Actions logs). `run.log` is Finnkino, the rest are per provider.

## Notes / gotchas
- Read the committed `run.log`, not Actions logs
- **A break-and-restore test pass can report the state before the restore.** Reverting a
  break by writing the file again produces the same byte count, and if it lands inside
  the same mtime second Python reuses the `__pycache__` bytecode compiled from the broken
  source: the pass reported the broken module as still broken after it was restored, and
  the same mechanism would just as happily report a broken module as fine and retire a
  test that never actually ran red. Seen on 2026-08-30 with a one-letter provider id,
  where `kinopirtii` -> `kinopirtti` is length-preserving by construction, which is the
  common case for exactly this kind of edit. `find . -name __pycache__ -type d -exec rm
  -rf {} +` between the break and the restore, and re-read the final green on a cleared
  cache before believing it. This bears on the rule in CLAUDE.md rather than on one test:
  a verification method that can silently report the wrong state is not a verification.
- **`raw.githubusercontent.com` served a two-commit-stale `index.html` minutes after a
  push, and using it as the base for the next edit silently reverted the previous fix.**
  Read repo files through the Contents API with `Accept: application/vnd.github.raw`,
  even one pushed seconds ago.
- Splitting the removal of one block across two edits leaves everything between them
  behind. That produced valid syntax referencing a deleted variable, so a syntax check
  passed and the app died at runtime with "staleEl is not defined". Delete a block as one
  contiguous match, or assert on the resulting line count.
- Anything the language toggle can reach must be redrawn by `applyLang()`. The venue
  picker, health line, stale banner and footer were each built once per page load, so a
  toggle left them in the old language until reload.
- Actions run 32985593686 (2026-08-26 15:35) failed with *"The job was not acquired by
  Runner of type hosted even after multiple attempts"* — GitHub-side runner allocation,
  zero billable ms, nothing to fix. A push in the same window also created no run at all.
- Triggering `workflow_dispatch` via the API needs the token's **Actions** permission;
  the "Workflows" permission only covers editing workflow *files*
- Probing external endpoints Claude's sandbox cannot reach: push a throwaway workflow that
  curls and commits the raw response, dispatch it, read the committed output, then delete
  workflow + output. Runners have unrestricted egress. **Does not work for sites that block
  datacenter IPs** (Finnkino, Kino Akseli) — those have to be fetched locally.
- BeautifulSoup re-serialises attributes with single quotes; the raw HTML used double quotes
  with `&quot;`-escaped JSON. Never write regexes against bs4's rendering of a page.
- `workflow_dispatch` runs the workflow file at the ref, but a run already queued from an
  earlier push uses the older file. Check `head_sha` when a change seems not to apply.
- Two writers on one branch (local + Actions), so both push paths need the pull-rebase retry.
- The cloud workflow is cron + dispatch only with `cancel-in-progress: true`. It used to
  trigger on pushes to `scripts/providers/**`, which meant an adapter commit spawned a run
  that raced a manual dispatch; both regenerate the same files, so the loser could not
  rebase and the run went red for no real reason.
- A retry loop whose last command is `sleep` exits 0 even when every attempt failed. Set an
  explicit flag and `exit 1`, or the step goes green having done nothing.
- Small hosts rate-limit: Kinoset started answering 403 after repeated hits in one hour.
- **Every frontend bug today came from a field that only Finnkino ever populated**:
  `soldOut` (four providers can set it now, see below), `s.fi` (Finnish synopsis missing ->
  rendered blank instead of falling back to English), and a hash regex `m=([\w-]+)` that
  silently truncated ids containing spaces. When adding a provider, check field-presence
  assumptions in the client, not just the parser.
- `location.hash = ''` counts as navigating to the top of the document and scrolled the
  list up when the sheet closed. Use `history.replaceState` to strip the fragment.
- A helper defined as `def rep(a,b,t)` that raises before the file write, followed by a
  push, commits the file **unchanged** — two no-op commits came from exactly that. Write the file before pushing, and check the edit count.
- The Contents API commits **one path per call**, so deleting five files made five
  commits. For a multi-file change in one commit, use the Git trees API: get
  `git/ref/heads/main` → its commit's `tree` → `POST git/trees` with `base_tree` and
  `{"path":…, "sha":null}` per deletion → `POST git/commits` → `PATCH git/refs/heads/main`.
- Pushing through the API means the **local clone learns nothing until it pulls**. A clone
  that looked weeks behind was only two hours behind: a day of API commits plus four
  rebrand commits arrived at once and the diff looked alarming. To identify the clone that
  actually publishes, read the author of the commits touching its data
  (`git log -3 -- data/areas.json` → `kino-local`), not the file listing.
- The local wrapper's own shell mechanics (path expansion, scheduling, log rotation) are
  in local private notes. One general lesson worth keeping here: a final step that runs
  *after* the push can fail without making the run look failed, so anything that matters
  needs its own check.
- **An unmapped language code renders as itself, and seven of them were doing it**
  (2026-08-29). Found while verifying the SV migration on the live site: a card read
  "ES · tekstit suomi/ruotsi". `LN` held five languages -- FI, EN, SV, JA, FR -- and the
  data carries twelve. So 133 Spanish showtimes said "ES", plus DE, IT, HI, TR, KA and
  TA on 19 more. Exactly the fault that hid the Swedish bug, found the same day by
  looking at the thing I had just fixed.
  The adapters were right here: ES, DE and the rest are correct ISO 639-1 codes. So the
  fix is the map, not the parser, and the two cases need telling apart -- **a real
  language code missing from `LN` is a client gap; a code that is not a language at all
  (SE for Sweden) is an adapter bug.** The comment in `LN` now says which is which,
  because the previous version said "fix the adapter" and would have sent the next
  reader the wrong way.
  `LN` now carries 24 codes: everything in the data plus everything the adapters' own
  Finnish-name maps can emit (`engel.LANGS` alone knows fifteen). A code appearing that
  is *not* in the map now means a provider has started publishing a language nobody has
  screened here before, which is worth a look rather than a silent bare code.
- **The Swedish tag is `SV`, and it used to be `SE`** (migrated 2026-08-29). SV is the
  ISO 639-1 code for the Swedish *language*; SE is the ISO 3166 code for *Sweden*. The
  app stored the second and meant the first, because the tag set was defined to match
  Finnkino and Finnkino sends SE. Most providers were already correct and the adapters
  were undoing it: `vista.py` and `gilda.py` each carried an explicit `sv -> SE` line
  turning a right code into a wrong one. Nexxo and Finnkino are the two that genuinely
  send SE, so they are corrected on the way in.
  Done in three commits, in this order, because the order is the safe part: the client
  learned to render **both** codes first, then the six adapters that publish Swedish,
  then `fetch_data.py`. Committed data turns over provider by provider across several
  runs, so there is never a moment when a refreshed file carries a code the client does
  not know.
  **Finished the same day.** The local run turned Finnkino over (1596 `SV`, 0 `SE`, and
  all 41 `FI-SE-A` compounds became `FI-SV-A` with `FI-EN-A` and `EN-FR-A` untouched),
  which was the one piece that could only be compile-checked here, since `fetch_data.py`
  needs a token and cannot run on a runner. With no area file containing `SE-` the
  temporary alias came out in the next commit, which was the condition set for it.
  Worth keeping as the shape of a data-format migration in a repo with no build step and
  two writers: **teach the reader both, change the writers, remove the old spelling once
  the data has turned over, and gate the removal on a measurement rather than on a
  belief that the runs have happened.** The check was a throwaway script that counted
  the tags per provider; it reported Finnkino as the sole holdout until the moment it
  was not.
- **BioRex published `SV`, not `SE`, and it had been rendering as a bare "SV" on a fifth
  of the schedule** (found 2026-08-29). `etiketti.py` was fixed for exactly this and
  `biorex.py` never was: BioRex's format spans read "FI&SV", `_lang_str` passed the codes
  through verbatim, and the client's `LN` map keys on Finnkino's `SE`, so `langTxt` fell
  through to the raw code. 644 showtimes said "tekstit SV" where they meant "tekstit
  ruotsi". Normalised at the source, keeping one vocabulary in the data rather than
  teaching the client a second spelling -- an alias in `LN` would have hidden the next
  adapter that invents a code. Worth checking on every new adapter: the tag set is
  Finnkino's, and a provider's own spelling is not evidence of anything.
- Adapters carry a referer, three retries with backoff, and a pause between venues.
- The film-list sort (`title.localeCompare(b.title,'fi')` per comparison) measured
  identical to a cached `Intl.Collator` -- about 0.01 ms per 45-title sort either way,
  V8 caches the collator internally. Benchmarked 2026-08-29 before "fixing" it; not
  worth touching, recorded so nobody re-tries.
## Crawlers and search

- State as of 2026-08-29: pages generated and committed, sitemap submitted, Rich Results
  Test clean on a city page (371 valid, 0 invalid: 10 Local business, 10 Organisation, 351
  Films). Remaining warnings are all optional fields -- `priceRange`, `telephone` and
  `image` on MovieTheater, `director` and `dateCreated` on Movie. None are in the pipeline;
  the first three would be manual data entry across 64 venues and `director` would need a
  per-film TMDB credits call. Deliberately not chased: optional fields do not gate
  eligibility, and the number that decides whether any of this worked is how many of the
  107 URLs turn up in Search Console's Pages report.

- `<head>` carries a description, canonical, OpenGraph and Twitter tags; `robots.txt` and
  a generated `sitemap.xml` exist (2026-08-28).
- **Pre-rendered pages, decided and built 2026-08-28**, superseding the note that deferred
  them. Markup does not create pages and the app is one JS-rendered URL, so
  `scripts/build_pages.py` renders 73 pages per language from the committed JSON at the end
  of every run: 64 venues plus the nine multi-venue cities. Same data, no second fetcher.
- **City pages only where a city has more than one venue.** The original plan said "~31
  cities"; that was wrong, taken from the README's city count rather than measured. Only
  Espoo, Helsinki, Kotka, Savonlinna and Tampere have two or more venues, which is the same
  rule the app's combined view uses. The other 27 would have been the venue page at a
  second URL, and two URLs with identical content compete with each other. Single-venue
  cities get the city into the venue page's title and JSON-LD address instead.
- **Page weight had to be designed, not discovered.** The first render was 13.6 MB across
  102 pages, with a 1.2 MB Helsinki page. Three cuts brought it to 4.0 MB raw / 388 kB
  gzipped: a four-day window (two for cities), structured data for today and tomorrow only
  with theatres as `@id` nodes instead of an address repeated per showtime, and a synopsis
  printed once per film rather than once per day it screens.
- **Nothing volatile in a page**, so `write_if_changed` actually holds: no build timestamp,
  and no `availability` in the markup. Sold-out state flips several times a day and would
  have rewritten every popular page on every run while still being stale in the index. A
  second consecutive run writes zero files; in practice a page changes once a day when the
  date window shifts. The test for this counts only stamps with a time component
  (2026-09-02): `films-extra.json` writes `generated` as a bare date, every page with a
  screening that day carries the same date inside a JSON-LD `startDate`, and the first day
  the two coincided 154 pages failed on a legitimate showtime. It had passed only while
  that stamp lagged a day behind the pages. A leaked build timestamp carries its time of
  day, and a bare date entering the stamp set now fails on its own.
- **Finnish city names are never inflected by the generator. Correct: Helsinki ->
  Helsingi**ssä, Tampere -> Tampereella. The stem changes under consonant gradation, and
  the two cities do not even take the same case. Glue the ending onto the nominative and
  you get Helsin**ki**ssä, which is wrong, and is how a reader spots a generated page. Every
  string uses the nominative with a separator, which stays correct for whatever city a
  future provider brings.
- **Google validates a nested `Movie` against its own Movie rules** (Rich Results Test,
  2026-08-29). The first render nested `workPresented` without an `image` and every one of
  them came back "8 invalid items detected: Missing field 'image'". `director` and
  `dateCreated` are reported too but only as optional. `MovieTheater` passed as both Local
  business and Organisation. Adding an absolute poster URL fixed it; a showtime with no
  poster from any source (one in 3509) now drops `workPresented` and keeps just the event,
  because an item that will always be rejected is worse than a smaller one.
- **A poster URL in JSON-LD is not a privacy leak**, which is why the markup can use
  cinema-CDN and image.tmdb.org addresses the page itself refuses to render as `<img>`.
  The crawler fetches it; the reader's browser never does.
- **Google reported no Event rich result** for `ScreeningEvent`, only Local business,
  Organisation and Movie. The markup is valid schema.org either way and the plain HTML
  showtimes are what carry the page; do not assume an event carousel is coming.
- Open: the pages are committed, so the repo grows by roughly the gzipped delta per day
  (~390 kB worst case). Building them in the workflow and deploying via a Pages artifact
  instead would remove that entirely, at the cost of switching Pages from branch to Actions
  and a real risk of taking the site down while getting it wrong. Not attempted yet.
- **`?area=` deep link** (2026-08-29). Every generated page links to `/?area={venueId}`, or
  `/?area=city:{City}` for a combined page, so a reader arriving from a search for one
  cinema opens on it instead of on whatever the app last had selected. The value goes
  through the same `known()` check as a stored preference, so a stale or hand-edited link
  falls through to the normal restore rather than showing an empty view. It is written to
  prefs on arrival, then stripped from the URL with `replaceState`: leaving it would
  override the picker on every reload, which is wrong for an app people keep open, and the
  link still does its job the first time it is opened.
- Deliberately **no venue or city count in the meta description**. README and IDEAS both
  carry it; a third copy in `index.html` would be a third thing to keep in step, and a
  stale number in a search result is worse than no number.
- `og:image` is `icon-512.png`, the only image on this origin. A 1200x630 card would
  preview better in a chat app. Not done.
- **Not doing: hidden text or markup that differs from what a visitor sees.** Cloaking is
  spam by every search engine's definition, and the whole point of the metadata above is
  that it is machine-readable rather than concealed. `<noscript>` has the same constraint,
  which is part of why it is still absent.
- Making thousands of showtime pages indexable would turn a personal app into a directory
  competing with the cinemas' own listings for their own venue names. That is a decision
  to take deliberately, not a side effect of adding markup. See "Access and ethics".

### Secondary page fetches have a ceiling (2026-08-30)
The adapters that read a listing and then fetch one page per film iterated whatever the
listing contained. Bounded in practice by how many films a cinema shows -- 15 to 31 today
-- and unbounded in principle: a listing that ever returned thousands would have been
fetched in full, paced and still thousands of requests at someone else's expense.
`common.PAGE_BUDGET` is 120, about four times the largest real figure, overridable with
`KINO_PAGE_BUDGET` for testing.

**The two loops are not the same loop, and testing the cap is what showed it.** With the
budget forced to 2, eTiketti went to zero showtimes at Kinopalatsi Kotka and 6 of 34 at
Trio 123 -- and would have published both. Its film pages *carry the screenings*; BioRex
and Engel take screenings from the listing and use film pages only for runtime, genres
and synopsis. So:

- `common.capped()` trims and logs, for enrichment loops. A film past the cap shows
  without metadata until the next run.
- `common.budget_or_raise()` raises, for a loop whose pages are the schedule. `run.py`
  then writes no file, the previous data stands, and the health line ages honestly --
  which is the rule this repo already applies to a failed venue and to a zero-showtime
  parse. **A venue publishing half its day is worse than one publishing nothing**, because
  half a day looks complete.

The first version used the trimming helper everywhere, which is the sort of thing that
reads fine and quietly ships a partial schedule. It was only visible because the cap was
tested by tripping it on a real provider rather than reasoned about.

### Response bodies have a ceiling too (2026-08-31)
The request count was bounded (above) while each response was read with a bare
`r.read()`: a broken or compromised origin answering with gigabytes would have sat in
memory in full before any parser or Pillow saw a byte. Found by an external review.
`common.fetch` now reads in 64 KB chunks against a cap -- `max_bytes` per call,
`MAX_BODY` (20 MB, `KINO_MAX_BODY`) by default -- and raises `BodyTooLarge` past it.

- **20 MB is headroom, not a measured figure** the way `PAGE_BUDGET` is: the sizes that
  would need measuring are the upstreams' to change. The largest body this pipeline
  legitimately reads is a poster source image at a few MB.
- **A Content-Length past the cap is refused before the body is read**, but the header
  is only the origin's claim: the chunked loop enforces the cap whether or not one was
  sent. The tests cover the two shapes separately, and the exception message names
  which layer refused.
- **Never retried.** The oversize answer is deterministic; asking again downloads it
  again at both ends' expense. `fetch`'s retry loop re-raises `BodyTooLarge`
  immediately, and the hit-count assertions are what hold that.
- **One cap in `fetch` covers every caller** -- adapters, enrichment, and
  `mirror_posters.download()`, which already routes through it. An oversize poster
  lands in the per-URL `failed` dict like any other bad download, so the run publishes
  showtimes as usual.
- Covered in `tests/test_common_fetch.py` against the real local HTTP server, including
  a response that declares no Content-Length at all. Verified by breaking each guard:
  the header refusal, the loop cap, the no-retry, and the capped read itself.

### The pipeline identifies itself (2026-08-30)
Every adapter sent `Mozilla/5.0 ... Chrome/126.0.0.0`. That is an automated reader
claiming to be a person at a keyboard, and it was the one thing in here a cinema had no
way to check for itself -- the ethics section above says we read a site the way an
ordinary visitor does, and the User-Agent was quietly making that claim untestable.
Now `Leffavuoro/1.0 (+https://leffavuoro.fi)`, everywhere, including `fetch_data.py` and
the TMDB pass.

**Probed before changing it, against all eleven providers.** Every one answers the honest
string byte-for-byte identically to the Chrome string: BioRex, Kinoset, Kotka, Kokkola,
Riviera, Savon Kinot, Gilda, Orion, Engel, Kino Akseli. Finnkino answers 403 to curl
under either string, which is the fingerprinting already recorded above and not a
UA decision.

One page looked like it discriminated -- Engel's film page differed between the two
agents at identical length. It differs between two requests with the *same* agent too: a
cache-buster timestamp in a script URL. **A difference is not evidence of discrimination
until the same request twice is ruled out.**

So honesty cost nothing here, which is the useful finding: the browser string was never
buying anything. If a provider ever refuses the honest one, record it here and keep the
browser string **for that host, deliberately** -- do not quietly re-disguise the pipeline.

The `+https://leffavuoro.fi` in it is the whole point: it is where a cinema that wants to
know who is reading them, or wants out, is supposed to look. Closed on 2026-08-30 by the
contact route below; until then the URL was half a promise.

### Conditional GETs, and what the providers actually support (2026-08-30)
`common.fetch(cache=True)` sends a stored `ETag` / `Last-Modified` back as
`If-None-Match` / `If-Modified-Since`, and a 304 returns the stored body without the
origin resending it. Verified live against Cinema Orion: second fetch was a real 304 and
118 kB was not sent again.

**Measured before building it, and the measurement is the point.** Across every endpoint
this pipeline reads, **only Cinema Orion sends a validator at all**:

| origin | ETag | Last-Modified | Cache-Control |
|---|---|---|---|
| cinemaorion.fi | no | **yes** | – |
| kotkanleffat.fi (eTiketti) | no | no | `no-store, no-cache, must-revalidate` |
| kinoset.fi (Nexxo) | no | no | `no-store, no-cache, must-revalidate, max-age=0` |
| biorex.org, kinoengel.fi, gilda.fi, rivieracinemas.fi | no | no | – |
| savonkinot.fi (Vista) | no | no | `private` |

So this saves roughly **one request per run**, not the bulk of them. It is in anyway
because it is the correct way to ask, it costs nothing where the origin offers nothing,
and a provider that starts sending ETags is picked up with no further change. Do not
expect it to show up as a bandwidth number.

`run.py` prints the shape of every run, because otherwise all of the above is a claim:

    [run] http: 1 revalidated (304), 85 full, 48 not stored (origin said no-store),
          0 cache entries written

Measured across the full cloud sweep on 2026-08-30: 86 conditional-eligible GETs, 48 of
them from origins that send `no-store`, exactly one that revalidates. `full` is not waste
-- most of these origins offer no validator, so there is nothing to revalidate against.
The line is there so the next person can check the behaviour instead of believing this
entry. Enabled on every plain GET in the pipeline rather than a chosen few, so the counts
are the whole picture; the two ajax POSTs (BioRex, Riviera) are excluded by `fetch`
itself, since a POST response is not addressed by its URL alone.

The half that does matter: **a response marked `no-store` or `no-cache` is never written
to disk.** Two providers send it explicitly, and the pipeline had been ignoring it. A
response with no validator is not stored either -- there would be nothing to revalidate
it against, so the directory would only grow.

- The cache lives in `.http-cache/`, gitignored, **never committed**. It holds verbatim
  copies of third parties' pages, which is the same thing the `probe/` rule exists to
  keep out of a public repo.
- Actions runners are ephemeral, so the workflow restores it with `actions/cache`. Without
  that the one origin that benefits is a cloud provider and the feature would be dormant.
- Never enable on a POST. The response is not addressed by the URL alone, so BioRex's and
  Riviera's ajax calls would collide in one slot; `fetch` forces `cache=False` when
  `data` is given rather than trusting call sites.

### Retry-After is honoured on the interval the upstream names (2026-08-30)
`common.fetch` retried every HTTP error on the same fixed `backoff * n`, so a provider
answering `429 Retry-After: 60` got three more requests inside 15 seconds. That is the
one place an upstream states its own terms in a machine-readable way, and the pipeline
was overriding them. A 429 or 503 carrying `Retry-After` is now retried on the interval
the origin named. Nothing else changes: a 500, a reset, a 429 with no header, all keep
the fixed backoff, and a 403 is still retried because that is the shape Kinoset's
under-load refusal takes and it clears.

**Both ceilings exist because "sleep as long as you are told" hands a stranger a lever on
the pipeline.** `RETRY_AFTER_MAX` (120 s) bounds one wait and `RETRY_AFTER_BUDGET`
(300 s) the whole process, so a host that 429s every request cannot turn one run into an
all-day one -- with `tries=3` and no run-wide budget, 45 requests each asking two minutes
is four and a half hours. Past either ceiling the request fails rather than waiting: the
next run is four hours away regardless, `run.py` keeps the previous file, and the health
line ages honestly. More requests at a host that just said no is the one response that is
definitely wrong. Both are overridable (`KINO_RETRY_AFTER_MAX`, `KINO_RETRY_AFTER_BUDGET`)
so the caps can be tripped in a test instead of reasoned about.

`Retry-After` is delta-seconds *or* an HTTP-date, and both appear in the wild. A date
already past means "now", not a negative sleep. An unparseable value falls back to the
fixed backoff rather than being read as zero -- a malformed header is not a reason to hand
a provider three fast retries.

    [run] throttled: 2 Retry-After responses, 60s waited, 1 not retried
          (asked for longer than a run can wait)

Printed only when it fires, so a normal run's log does not grow. When it does appear it
is a provider saying the rate is wrong, which belongs in the committed log rather than
being inferred from a failure four hours later.

**Tested by tripping it**, against a local server scripted to 429: the stated wait is
honoured rather than the backoff (1 s waited where `backoff=30`), a `Retry-After: 9999`
costs exactly one request and no sleep, the run-wide budget refuses the second of two
2-second asks under a 3-second budget, an HTTP-date is parsed, a past date waits zero,
and a plain 500 still takes its three tries with no throttle accounting. The 200 and 304
paths are unchanged, confirmed live on Nexxo and Orion.

Not covered by this: `enrich_tmdb.py` has its own bare `urlopen` with no retry at all, so
a TMDB 429 skips that title rather than hammering. TMDB is the one upstream here that
reliably rate-limits, and routing it through `common.fetch` would get it this handling.
A separate change, not this one.

### A refusal has to say which layer refused (2026-08-30)
Cloud run #110 went red on `nexxo` alone. All three Kinoset venues answered 403, `run.py`
counted one failure and the workflow's gate fired. Nothing was lost: the previous files
were kept, the three venues were published as `stale` with `status: partial`, and the
commit landed before the gate, so the app aged honestly and the next run 43 minutes later
served all fourteen showtimes again.

**The committed log said `HTTP Error 403: Forbidden`, three times, and nothing else.**
That is the same line whether something in front of the site blocked the address or the
application itself was rate-limiting, and those want opposite responses: an edge decision
does not clear by waiting and means the endpoint has to move to the local half the way
Finnkino already has, while an origin throttle clears on its own and the right move is to
do nothing until the next cron. There was no way to tell them apart, and no way to go and
look afterwards, because the block was gone before anyone read the log. The unattended run
is the only witness a transient refusal ever has.

`common.fetch` now prints one line on the way out of a request it is giving up on:

    [http] 403 from kinoset.fi, gave up after 3 attempt(s) -- Server: LiteSpeed

- **Three headers, and never the body.** `Server`, `CF-Ray`, `Retry-After`. `run-*.log` is
  committed to a public repo and a third party's error page carries whatever they ship to
  visitors — that is the raw-dump rule, and one such dump already put someone else's API
  key in here. Nothing about their stack beyond who answered; `X-Powered-By` was considered
  and dropped for that reason.
- **Measured against the live endpoint before writing this down**: `kinoset.fi` answers
  `Server: LiteSpeed` with no `CF-Ray`, so it is not fronted by Cloudflare at all. A
  Kinoset 403 should therefore read as the origin refusing, which matches the behaviour
  already recorded above — it started answering 403 after repeated hits in one hour. If one
  ever comes back reading `Server: cloudflare`, that is a genuinely different event.
- **One line per host per process, not per request.** `mirror_posters` calls `fetch` once
  per poster and has had 185 failures against one host in a single run; a line each would
  bury the summary the log is read for. The ray id is unique per request so it cannot be
  part of the key — its presence identifies the layer, and the line carries the first value
  seen.
- Both exits are covered: the exhausted retry loop and the `Retry-After` ceiling, which
  raises without retrying. `[run] throttled:` counts those but never names the host.

**Two other fixes were considered and rejected.**

- **Defer a failed venue to a second pass at the end of the run.** The contract is
  `fetch_site(site) -> {venue_id: [shows]}`, one site at a time, so retrying a subset of
  venues means either changing that contract across all eleven adapters or re-fetching the
  whole site — and several adapters take one listing request for every venue, so a subset
  is not a smaller request. That is an interface change on speculation. It would also buy
  very little: nexxo is one site of three venues, so "the end of the module run" is about
  five seconds after the last failure, and even the end of the whole cloud run is minutes,
  against a block that took somewhere under 43 to clear. Retuning retries on a single
  occurrence is tuning against noise.
- **Stop failing the workflow when every venue kept usable previous data.** This reverses
  a decision recorded above deliberately: only a site where *every* venue came back empty
  fails, precisely because nothing else would notice that. Kinoset losing all three venues
  is that case, not a false alarm. The health line is what a visitor sees and it worked,
  but nobody checks the site four times a day — the red run is the one notification there
  is, and downgrading it would let a permanently dead provider publish green runs forever
  while the data quietly aged. The Finnkino fallback workflow is the warning in the other
  direction: it was red on every push for two days and hid the run that had actually
  broken. One red run is not that.

Tested by breaking it six ways: dropping either `_log_refusal` call, dropping the
deduplication, appending the body, removing `CF-Ray` from the set, and printing when the
response carried none of the three. Each turns exactly the tests that pin it red. The
two-venue case runs one refused and one served venue through the loop and asserts a single
line, so a version that logged on success or once per attempt fails.

### The site answers the User-Agent (2026-08-30)
`Leffavuoro/1.0 (+https://leffavuoro.fi)` points every provider at this site, and the
site said nothing about who was reading them or how to ask to be left out. A URL that
leads nowhere is worse than no URL: it looks like an offer of contact and is not one.
IDEAS has claimed since the first multi-provider commit that removing a cinema is one
registry entry, with no address anywhere that a cinema could use to ask for it.

`leffavuoro@gmail.com`, in three places, because a cinema can land on any of them:

- the app footer, on its own line under the source credit, translated in all three
  languages and redrawn by `applyLang()` like everything else the toggle reaches;
- every generated venue and city page, fi and en, in the footer;
- a `## Contact` section in the README, which is what a GitHub visitor finds.

**Plain text, not obfuscated.** Entity-encoding or a JavaScript-assembled address hides
it from a scraper and from the cinema manager it exists for in the same move, and an
address nobody can copy is not a contact route. Reviewed again 2026-08-30 and kept: every
technique that survives a scraper driving a headless browser also defeats a screen reader,
copy-paste or tap-to-mail, and the address is a dedicated alias rather than a personal
mailbox, so exposure costs a rotation rather than a mailbox.

**That plan only works if rotating is one reliable act**, and the address is hand-written
in four files -- twice in `index.html`, since the markup keeps a literal so the line
survives a broken script -- then stamped onto 107 generated pages by `build_pages.py`.
The copy most likely to be missed is the generator's, because nothing reads its output: a
dead address would sit on every venue page until a cinema tried to write and bounced.
`tests/test_contact_address.py` discovers the address from the client's `CONTACT`
constant and compares everything else against it, so it hardcodes none of its own and
keeps working across a rotation.

The same test refuses **any** other address in a tracked file, generated pages included.
That is the cheaper half: a stray personal address in a public repo costs a history
rewrite to remove, and a rewrite only helps if somebody notices in the first place.

`renderContact()` is separate from `renderStatus()` on purpose: `renderStatus` returns
early until schedule data has loaded, and the one line a cinema comes here for must not
depend on a fetch succeeding. It is called once at boot as well as from `applyLang()`,
since `applyLang()` only runs on a toggle and a reader with a stored `lang` would
otherwise get a Finnish contact line under an English footer.

Constant, so `write_if_changed` still converges: the first run rewrote 106 of 107 pages
and the second wrote none. Same knock-on to expect as the poster mirroring, once.

### The accent numbers, re-derived (2026-08-30)
The open item said the recorded ΔE figures could not be reproduced and needed a method
written next to them. They have been re-derived, and the answer is worse than a
bookkeeping error: **the independent model was right, this file was wrong, and one
same-city pair is effectively a single colour to a deuteranope right now.**

`scripts/accent_check.py` is the method. Not a formula in prose, which can be misread,
but a script that runs: it prints every same-city pair under CIEDE2000 in normal vision
and under two independently derived deuteranope models, and `--selftest` checks its own
CIEDE2000 against 15 pairs of Sharma, Wu & Dalal's published reference data before any
of it is believed. What it computes, exactly: sRGB -> linear via the piecewise IEC
61966-2-1 transfer function; deuteranope simulation applied to **linear** RGB by both
Viénot–Brettel–Mollon (1999) and Machado–Oliveira–Fernandes (2009) at severity 1.0;
linear -> XYZ (sRGB primaries, D65) -> CIELAB (D65, 2°); CIEDE2000 with kL=kC=kH=1.

**The old metric was CIE76, called ΔE.** That is the diagnosis, and it is certain rather
than inferred, because plain Euclidean distance in Lab reproduces three of the recorded
normal-vision numbers to the decimal:

| recorded as | pair | CIE76 | CIEDE2000 |
|---|---|---|---|
| 25.9 | old Finnkino / old Gilda | **25.9** | 15.3 |
| 46.9 | BioRex / Riviera, normal | **46.9** | 23.3 |
| 36.9 | Engel / BioRex, normal | **36.9** | 18.5 |

CIE76 overstates differences badly for saturated colours, which is the entire reason
CIEDE2000 exists. Every figure in this file was therefore optimistic in the same
direction, which is why nothing looked wrong.

**The deuteranope figures match nothing at all.** 34.5, 28.0, 37.3 and 5.0 were tested
against Viénot and Machado, in linear and in gamma space, under CIE76 and CIEDE2000, and
against Machado interpolated across the full severity range. The severity that would
explain each number differs per number (0.32, 0.48, 0.00, 1.00), so it is not one
consistent model with the wrong parameter either. Whatever produced them, it cannot be
recovered, and no number from it should be quoted again.

**Corrected, with the harsher of the two models:**

| claim | recorded | measured |
|---|---|---|
| worst same-city pair, normal | 46.9 | 18.5 (Engel/Gilda) |
| worst same-city pair, deutan | 28.0 | **3.9 (BioRex/Riviera)** |
| BioRex/Riviera, deutan | 34.5 | 3.9 |
| Engel `#B47ACC` worst same-city | 36.9 / 37.3 | 18.5 / 15.2 |
| old Finnkino / old BioRex, deutan | 5.0 | 1.8 |
| global minimum, any pair, deutan | 32.1 | 0.7 (Finnkino/Kino Akseli) |

**Four cities have more than one chain in them.** Measured against the data,
not assumed: 4 of 45 cities -- Helsinki with six, Vantaa, Lahti and Kouvola with two. Espoo, Tampere, Kotka and Savonlinna have two venues each
but one chain each, so the combined view there never puts two accents side by side. The
worst pair is still the six chains in Helsinki; the three the eTiketti sweep created
were measured against their city before they landed. This also retires the old bullet's
claim that "Kotka only ever shows two chains" and its 28.7 -> 24.8 figure: Kotka has one
chain and has never had two.

Superseded 2026-09-01: Kino Metso put a third chain in Jyväskylä, which Finnkino and
Kino Aurora already shared, so the constrained set is 5 of 52 cities. Jyväskylä's worst
pair measures 26.9 ΔE00 deutan (Finnkino/Kino Metso) and its best 63.7, so the city
does not move the set's worst pair, which is still the 14.4 in Helsinki.

Two structural conclusions the correction does *not* overturn. Kino Akseli's gold sits
0.7 ΔE00 from Finnkino's orange under deuteranopia -- indistinguishable -- and that is
still fine, because Nummela has one chain and the two never appear together. And six
chains in one city genuinely cannot all be far apart under deuteranopia, who sees
something close to a two-dimensional colour space: the best achievable Helsinki floor is
about 14, not the 28 that was recorded.

**Fixed the same day: Riviera moved from `#7B3FD4` to `#0C6464`.** Blue and violet
differ mostly in the red-green channel a deuteranope does not have, so BioRex and
Riviera sat 3.9 ΔE00 apart in the one city where they appear side by side. The Helsinki
floor is now **14.4**, and the binding pair is Finnkino/Cinema Orion -- orange against
olive, both yellowish under deuteranopia.

**"About the ceiling for six chains" was wrong** (measured 2026-08-30). It read as a
property of the problem and was only a property of hand-picking. Every Helsinki chain but
Finnkino appears in no other multi-chain city, so five of the six colours are free, and a
greedy max-min search over the same L\* 38-60 band reaches a floor of **19.5 deutan and
21.0 normal** -- better than the current palette on *both* axes, at the same mean chroma.
Not applied: it moves five accents Helsinki readers have already learned, and the current
floor is not hurting anyone. Recorded so the number is not quoted as a limit again. The
search is four lines against `accent_check`'s own functions; re-run it before believing
this either.

- **Riviera moved, not BioRex.** Both give the same 14.4, because the floor ends up set
  by a different pair either way. Riviera's two venues are both in Helsinki, so its
  accent only ever matters there; BioRex appears in twelve towns where its blue is
  unconstrained. Change the colour where the problem is.
- **The choice among candidates was not an optimisation.** Anything clearing 14.4 gives
  the same floor, so maximising deutan separation past that point buys nothing. The
  tiebreak was normal vision, where nearly every reader is: `#0C6464` scores 16.5 deutan
  / 28.1 normal, against `#24664E` at 19.1 / 18.8. The higher deutan number is the worse
  colour here.
- **`--city` took a list and used only the first entry** (found in review, fixed
  2026-08-30). The flag advertised comma-separated cities and then `break`s out of the
  loop after the first non-empty one, so a candidate could be cleared in Helsinki while
  colliding with an existing chain in Tampere. A validation tool that can approve falsely
  is worse than no tool, and this one had shipped its first verdict already. It now takes
  a sequence of cities and measures against the existing chains in every one. A bare
  string is wrapped rather than iterated, since iterating one would silently test the
  candidate against the letters of the city name.
- Only six hue families clear the ceiling at all, and every one of them sits at L* 38-39,
  the bottom of the legibility window. Separating from five existing chains under
  deuteranopia forces a dark colour; that is a real constraint on a seventh Helsinki
  chain, not a preference.
- Teal now sits near Kinoset's green and Savon Kinot's teal in the abstract. That is
  allowed and deliberate: neither shares a city with Riviera, the chain accents only
  render in a combined city view, and Helsinki is the only city that has one.

### Six days out of seven is not a Finnkino schedule (2026-09-01)
`fetch_data.py` asks OCAPI for seven business dates, one request each. A request that
raised was logged and stepped over, and the days that did answer were written out as the
new snapshot with a current timestamp and an exit code of 0.

That is not a smaller schedule, it is a wrong one. `dates` is built from the shows that
arrived, and the client reads a date's absence from that list as "schedule not published
yet" rather than "no shows" -- so one transient error took a whole day out of all
seventeen Finnkino venues at once and the app said the cinema had not published it.
Nothing surfaced it either: `check_runs.py` looks for a non-zero `exit=`, the health line
looks at age, and both were clean.

Reproduced by driving `main()` with OCAPI stubbed and day three raising: return code 0,
the failure logged, `dates` going from seven entries to six, and the previous file gone.

**All seven or none.** The alternative on a failure is the file from the last run, which
is hours older and says so -- the age moves, the health line moves past eight hours, and
the non-zero exit is what `check_runs.py` turns red on the next push. A published
six-day week moves nothing a reader can see. This is the rule the rest of the pipeline
already follows: a provider that parses nothing fails its run rather than blanking its
venues, and a partial OCAPI response already refused to blank a venue here.

The last day of the horizon is refused on the same terms, and that was the tempting
exception -- six of seven looks like plenty when the missing one is six days out. It is
still a day the client cannot tell from unpublished, and the next run is a few hours
away.

**`areas.json` moved down with the schedule files.** It was written before the seven
requests, so a run that published nothing still stamped the one file whose age answers
"when did Finnkino last refresh". The external staleness monitor on that age is still on
the backlog; this is what would have made it lie the day it was built.

Poster downloads and the token fetch have already happened by the time the run gives up.
Neither is part of the snapshot -- a poster accumulates under its release id and the
next run re-uses it -- so the abort is not a rollback and is not described as one.

Not retried before giving up, and that is a real cost: a single blip now defers a whole
refresh by up to six hours. `api()` has no retry at all, unlike `common.fetch` which every
other provider goes through. Worth adding, as its own change with its own reasoning,
rather than smuggled in behind this one.

Thirteen tests drive the real `main()` in a temporary directory with OCAPI stubbed by
URL, two sites and seven days, because this file cannot be run against the real endpoint
from anywhere but an ordinary connection. Verified by breaking it six ways: the guard
removed (9 red), logging without returning (8), returning 0 after refusing to publish
(6), aborting only when all seven days fail (8), tolerating the last day (1), and
`areas.json` put back above the loop (3).

### A provider is as fresh as its weakest venue (2026-08-30)
`run.py`'s module docstring said an empty parse "counts as a failure". It did, for a
whole site. One venue of twelve parsing to nothing hit the `keeping previous data`
branch, which incremented nothing and recorded nothing, and then `venues-{provider}.json`
stamped `generated: now` across all twelve. `renderHealth` reads that stamp, so the app
said BioRex was an hour old while one of its cinemas sat on week-old showtimes. The
failure this pipeline was built to prevent, one level down from where it was being
checked.

`venues-{provider}.json` gains three fields, all additive so an older client ignores them:

- `oldest` -- the minimum `generated` across the provider's venue files, read off disk
  after the run rather than tracked alongside it, so it cannot drift from what was
  actually written. This is what the health line ages on now. Same rule the combined city
  view already applied to its parts.
- `status` -- `ok` or `partial`.
- `stale` -- the venue ids whose previous file was kept.

`generated` keeps its old meaning, when the file was written. Redefining it would have
been a silent schema change for anything already reading it.

**Stale, not failed, and the distinction is forced rather than chosen.** At this layer a
broken parser and a cinema with nothing on today both arrive as `[]`. They cannot be told
apart, so failing the run on a venue-level empty would fire on every ordinary Monday
closure. What the run must not do is hide it: `[run] partial:` names the venues in the
committed log, and the published status carries them to the client. Only a site where
*every* venue came back empty still fails, because nothing else would notice that.

The client shows `⚠ Riviera 119h (1/2)` rather than just `⚠ Riviera 119h`. Ageing on the
oldest venue is what makes the number honest, but on its own it reads as "this whole
chain is down" when eleven of twelve cinemas are fine. The count says how much of it is
actually behind, with the venue tally in the title attribute, translated in all three
languages.

**Age alone was still the whole test, and that hid a partial refresh** (fixed later the
same day). A provider whose venue failed to refresh read as healthy for as long as the
data it kept stayed under `STALE_H`, so the collapsed summary said every source was up to
date while the expanded row beside it said `(1/12)`. The two disagreed and the one a
reader sees first was wrong.

`healthState(m, ageH)` now returns `gone | behind | partial | ok`, in that order of
severity. A partial refresh degrades the moment it happens, independent of the retained
data's age, because it is a statement about *this run* rather than about how old the data
is. **`partial` is kept separate from `behind` rather than folded into it**: two-hour-old
data is not behind, and calling it that is the false alarm that teaches people to ignore
the line. So the summary has a second phrase -- `⚠ Osa teattereista ei päivittynyt:
Riviera` -- and `behind` outranks it when a provider is both.

The classifier is pure and sits between two marker comments, so
`tests/health_state_harness.js` slices it out of `index.html` and runs it with no DOM.
Splitting the file to make it testable was the alternative and is explicitly deferred
elsewhere in this document. Fourteen cases, including a file written before `status`
existed. Verified by breaking it: reverting to age-only turns four red.
**One term was not pinned at first** -- the unverified case also set `status: 'partial'`,
so `m.unverified > 0` could be deleted with everything still green. Found by deleting it,
which is the only way that gap ever shows up.

**A venue that has never produced a showtime is `unverified`, not `stale`** (added
2026-08-30, same pass). Two faults, one of which only appeared on the second run:

- A brand-new venue with no shows and no previous file fell through every branch. It got
  its empty file so the picker would not 404, and then nothing recorded it, so a provider
  carrying a venue that had never returned a showtime published `status: "ok"`.
- On the *next* run that empty file existed, so `not shows and path.exists()` sent it
  down the stale branch — claiming previous data that was never there, and letting its
  ageing `generated` drag the provider's `oldest` down for a venue with nothing to be
  stale about.

The discriminator is now whether the previous file **contains shows**, not whether a file
exists. A venue with none either way is listed in `unverified`, its empty file is
rewritten with a fresh `generated` (nothing is being preserved, so nothing should age),
and `status` is `partial` while either list is non-empty. It clears by itself the run the
venue starts producing.

Deliberately not a failure. A venue added before its programme is published and a venue
whose parse has never worked are the same `[]` here, and failing on the first would fail
the run on an ordinary new listing. `unverified` records it instead, and the run log names
the venues.

Covered by `tests/test_run_partial.py`, with **three venues and the stale one in the
middle**: two venues would let an implementation that reports "the last venue's state"
pass, since with one good and one bad those are the same answer. Verified by breaking it
-- reverting `oldest` to `now` turns two tests red, dropping the `stale` bookkeeping
turns three red.

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
The poster and generic branches wrote their `cache.put` fire-and-forget: the response
returned, and the write raced the browser's right to terminate the worker the moment no
extend-lifetime promise remains. Usually the put wins the race; nothing guarantees it.
Online the loss is invisible -- the next visit refetches -- but the write that loses is
exactly the one the offline fallback needed, so this is an offline-reliability hole, not
a correctness bug anyone would see in a tab. Found by an external review. Both branches
now pass the `caches.open().then(put)` chain to `e.waitUntil`, which is what the
data-JSON branch had done for its background refresh all along.

The harness could not catch this before it modelled termination: its
stubbed `put` resolved inline and it read `stored` after awaiting only the response, so
a forgotten write always "finished" in time. `put` now settles on a macrotask -- a real
Cache write is asynchronous work that outlives the response -- and `stored` is read
only after the response *and every promise passed to `e.waitUntil`* have settled. The
existing 200-case assertions thereby became the waitUntil property: verified by
restoring the fire-and-forget form, which turns `poster_200` and `page_200` red. No
`CACHE` bump: that rule binds commits touching `index.html`, the byte-diff alone updates
the worker, and nothing cached went stale.

**Challenged (2026-08-31) and the challenge rejected.** A review claimed calling
`e.waitUntil` inside the `fetch().then()` throws `InvalidStateError` because MDN says it
"must be initially called within the event callback". The spec's actual rule is
narrower: it throws only when the event is **not active**, and an event is active while
its dispatch flag is set *or its pending promises count is above zero* --
`respondWith(r)` adds `r` to those promises "as if event.waitUntil(r) is called", and
the spec's own note pins it: the throw applies when *no* lifetime extension promise was
added in the dispatch task. These calls run inside the `.then` that settles the
respondWith promise, so the event is still active; the data branch has done the same
after an `await` since it was written. Confirmed against production Chrome on the live
site: both branches answer 200 and both cache entries land. What the review was right
about: the harness stub accepted `waitUntil` at *any* time. It now models the activity
rule -- pending-extension counting, `InvalidStateError` when a call comes after every
extension has settled -- verified by deferring a `waitUntil` behind `setTimeout`, which
goes red. A guard built on MDN's summary instead would have failed correct code, which
is the mock-encodes-the-assumption trap in new clothes.

### The footer credits only the source on screen (2026-08-30)
The bottom of the page carried three dense blocks: a per-source age for all eleven
providers, a credit line naming the chain twice, and the contact line. The ages are a
*diagnostic* -- on a normal day they are eleven items all saying the same thing, and the
one bit a reader wants ("is anything wrong?") had to be recovered by scanning them.

Now one `<footer>` with three short lines, the per-source list behind a `<details>`:

- **The summary states the answer, and when something is wrong it names it**:
  `⚠ Lähteitä jäljessä: Riviera, Gilda` rather than a count. A count makes you open the
  disclosure to learn anything; a name is the thing you opened it for. Truncated past
  three, since by then the shape is "most of them" and the list is one click away.
- **Native `<details>`, not a scripted toggle.** Keyboard operable and announced
  correctly with no code, which is the whole argument for it. Verified: the summary takes
  focus, `tabIndex` 0, and toggles.
- The glyph key moved out of the sources line and stays visible, because it explains
  symbols that are on screen right now. Hiding an explanation behind a disclosure is the
  one thing that would have been worse than the crowding.
- The credit line dropped one of its two chain names. It read
  `Aikataulut: Finnkino · ... · Napauta näytöstä ostaaksesi liput — finnkino.fi`, and the
  book-mode phrase already ends in the host for every mode that names one.

Measured rather than asserted: at 375 px the footer block is **110 px closed against
166 px with the list open**, so the disclosure is worth about three rows of provider
ages, roughly a third of the block. On desktop the old list already fit one row, so the
saving there is small -- this is a mobile change.

**Rejected: a separate sub-page for data freshness.** Generated pages must stay free of
anything volatile or `write_if_changed` stops working and every page rewrites on every
run, and provider ages change by the minute. That leaves a client-rendered route, which
is a router, a URL and a second render path for something that fits on one line.

For any future layout work here: the harness browser reports `innerWidth: 0` until
`resize_window` is called, and every measurement taken before that is wrong -- text wraps
to one character per line and a three-line footer measures 396 px. Set a viewport first,
then measure.

### The app is operable from a keyboard (2026-08-30)
Four faults, fixed as one pass because they interlock -- the dialog's close button is
both the first focus target and one of the mislabelled controls.

**Movie details could not be opened without a mouse.** The trigger was a bare
`<article class="movie">` with a delegated click handler: not focusable, no Enter, no
role. The fix is a real `<a>` on the title, not a faked button, because opening the sheet
*is* hash navigation -- `location.hash = 'm=...'` is what the click handler did. The
element now matches what the action already was, so Enter works with no key handling of
ours. The times view's `.tinfo` became an anchor the same way. The card-wide click stays
as a mouse affordance and defers to the link, so the keyboard path and the mouse path run
the same code rather than two.

**The sheet claimed to be an open dialog at all times.** `role="dialog" aria-modal="true"`
sat in the markup permanently and the sheet was hidden with a CSS transform, so it stayed
in the focus order and in the accessibility tree while invisible. Now `inert` toggles on
the sheet when closed, and on the *background* roots when open, which is what real
modality means: measured with the sheet open, **zero focusable elements remain outside
it**. `inert` rather than `hidden` because the sheet animates and `display:none` would
kill the transition. Escape closes it, focus moves to the close button on open and back
to the exact trigger on close -- guarded by `document.contains`, since the list is
rebuilt through `innerHTML` on every render and a stale node would swallow the focus in
silence.

**`role="tablist"` with no tab pattern behind it.** The date chips carried `role="tab"`
with no `aria-selected`, no `aria-controls` and no arrow keys, and the view segment was a
tablist whose children had no role at all. Simplified rather than completed: these are
buttons that pick a day and a view, not tabs with panels. Days take `aria-current="date"`,
the segment and filter chips take `aria-pressed`, and the calendar chip -- which opens a
dialog and was also marked a tab -- takes `aria-haspopup="dialog"` with `aria-expanded`
tracking the picker.

**Accessible names were in two languages at once and followed neither toggle.** Hard-coded
English ("Choose theatre", "Filter movies by title or genre") next to hard-coded Finnish
("Sulje", "Suodata ketjun mukaan"). `applyAriaLabels()` now runs from `applyLang()` like
everything else the toggle reaches. An `aria-label` is a label; the rule that already
covered the picker, the health line and the footer covers it too.

### A venue with no programme yet is not a failed refresh (2026-08-31)
Kino Metso Tikkakoski publishes into late October from day one, so it sits inside the
21-day window with zero showtimes for a month -- and the health line answered with
"⚠ Osa teattereista ei päivittynyt: Kino Metso", which is wrong twice over: the fetch
was an hour old, and a month-long standing warning is the always-red alarm that
teaches readers to ignore the line before a real partial ever fires.

`healthState` gained a `pending` state below `partial`: a quiet "Ei vielä ohjelmistoa:
{venue}" summary with no warning mark, the provider row keeping a muted count. The
summary names the *venue*, not the chain, because "Kino Metso" reads as the whole
chain when only Tikkakoski is waiting.

**The first version quieted every `unverified` venue, and a review caught that as
overreach**: run.py's own comment says "added before its programme is published" and
"a parse that has never worked" are not distinguishable there, so quieting both would
read a rotted venue match as a calm "no programme yet" forever. The state is therefore
granted only where the evidence is positive, and the adapter is the one who has it: a
module that sets `EMPTY_VENUES_CONFIRMED` (nexxo -- its schema check means a venue
with zero rows was answered and listed empty, and a mis-mapped roomed venue lands in
the unclaimed-room log instead of silence) vouches for venues it explicitly reported
empty, and run.py writes those into a `pending` list; everything else stays
`unverified` and keeps reading `partial`. eTiketti must not set the flag: its venue
match is a substring test over markup, and a rotted match yields the same empty list
while the page still lists films. Severity order: stale and unverified outrank
pending, age outranks all three; every rule verified by breaking it on both sides
(five breaks, five reds -- including granting pending without the flag, without the
venue key, and letting pending mark the provider partial).

The same review's second point: the provider row's tooltip called every flagged venue
"ei päivittynyt", which was only true of the stale ones. The count keeps one number,
and the title now names each kind by what is true of it -- stale as "ei päivittynyt",
unverified as "ei ole vielä saatu näytöksiä", pending as "ei vielä ohjelmistoa".

**A second review pass tightened the evidence itself.** The module flag alone still
had a hole: nexxo's parse() silently skipped rows whose startTime/startDate could not
be read, so a renamed row field would wipe every row, return [], and read as a quiet
pending programme. parse() now raises a diagnostic when relevant rows exist and not
one produced a showtime -- naming the row counts and the venue -- so a schema change
under the parser fails the venue loudly instead. The legitimate empties stay empties:
an empty payload, a room filter that owns none of the rows, and rows the upstream
itself marks upcoming-only (`isUpcoming`), which genuinely carry no scheduled
showtime. One malformed row among parseable ones is still dropped rather than fatal --
killing a venue over one bad row would trade a metadata bug for missing showtimes.
And the runner's one-line summary now counts pending ("0 stale, 0 unverified, 1
pending, ...") with its own `[run] pending:` naming line, because run-nexxo.log had
read "0 stale, 0 unverified, 0 with no programme" while Tikkakoski sat pending -- a
venue publishing nothing must not look like a venue that does not exist. Four guards,
four reds when broken: the wipe raise, the upcoming exemption, the guard staying quiet
on partial parses, and the summary's pending term.

### The installed iOS app stops smearing the status bar (2026-08-31)
Installed to an iPhone home screen, the top of the page showed a blurred smear behind
the clock. Three separate causes, shipped as v84–v86 and verified together on a real
notch (iPhone 17 Pro simulator, the site installed from Safari exactly the way a user
does it):

- **Nothing painted the status-bar strip.** The page runs edge-to-edge in standalone,
  and whatever scrolled under the transparent bar showed through iOS's blur material.
  A `position:fixed` strip the height of `env(safe-area-inset-top)` now paints `--bg`
  behind the bar at all times. It cannot ride on the sticky controls row: sticky is
  bound to its parent, and measured on the live site the pinned row leaves the
  viewport under scroll, so only a fixed cover holds.
- **The insets were dead until the app opted in.** Without
  `apple-mobile-web-app-status-bar-style: black-translucent`, iOS lays the page out
  below the bar, keeps `env(safe-area-inset-top)` at zero — the v84 strip computed to
  0px tall — and draws its own smear. The meta is read at install time, so an
  already-installed icon has to be removed and re-added once to pick it up.
- **`theme-color` was hardcoded dark**, and with a translucent bar iOS derives the
  clock's text colour from it: the light theme would have had a white clock on a
  near-white page. `applyTheme()` now writes the current `--bg` into the meta on every
  toggle; Android tints its UI from the same value.

The user's own observation cracked most of the diagnosis: the smear vanished after
opening a film sheet, which forces a full composite. **One device resists: an iPhone
15 Pro Max on iOS 27 smears at launch even from a fresh install**, while an iPhone 17
on the same iOS and the 26.5 simulator launch clean. Two page-side workarounds were
tried and removed the same day when the device disproved them: a one-frame
`translateZ(0)` on the root right after first paint (v87), then a sheet-grade inert
flip on header/main/footer plus the transform, 700 ms after load (v88). A real sheet
open still clears it, so whatever iOS drops on that interaction is not reachable by
page-side layer churn. Parked as an iOS 27 compositor bug on that hardware; the fixes
that survive below are the ones verified on-device. Do not add a third guess without a
way to instrument the phone. Also fixed in the same
pass: the venue list's 6px top padding was a slit rows scrolled through between the
search head and the stuck city header; the padding is gone and the headers' own
padding provides the spacing. The full-screen venue sheet pads past the inset so its
search row clears the Dynamic Island, verified on-device along with the rest:
launch, scroll, picker open, keyboard staying down on touch open.

### The month picker gets the sheet's modal lifecycle (2026-08-31)
The keyboard pass above gave the movie sheet real modality and left the month picker
only claiming it: `role="dialog" aria-modal="true"` in the markup, while focus stayed
on the chip behind it, the background stayed tabbable and closing returned focus
nowhere. A screen reader announced a modal dialog and then found none of the behaviour
the role declares. Found by an external review.

It now runs the sheet's own lifecycle rather than a second mechanism: the same
`BEHIND()` roots go inert on open and come back on close, Escape and the backdrop close
it, focus lands on the selected day (falling back to any day, then an arrow) and returns
to the calendar chip. The chip survives the date-picked path because `selectDay`
mutates the existing chips instead of rebuilding the row. One wrinkle the sheet does not
have: month navigation redraws the grid through `innerHTML`, which replaces the arrow
under focus and would have dropped focus onto an inert page -- the redraw refocuses the
same-direction arrow, falling back to the other one, then a day. The dialog is labelled
by its month heading (`aria-labelledby="calTitle"`), which the redraw re-creates.

No unit test: the lifecycle is DOM-and-focus behaviour that stdlib-only Node cannot
exercise, and a source-grep test would pin the implementation rather than the property.
Verified live instead, against the served page: open, initial focus, both inert states,
Escape, backdrop, month-nav focus survival and the date-picked focus return, plus a
clean console.

### "Huomenna" was ellipsised on a 402px phone (2026-09-01, sw.js v94)
The date row is six chips at `flex:1 1 0`, so each gets a sixth of the row. The label
steps up from .6rem to .66rem above a breakpoint set at 400px. A .66rem "Huomenna"
measures **53.43px** and a sixth of a 402px row leaves **53.00px**, so it lost by 0.43px
and the ellipsis added on 2026-08-30 did what it was there for. An iPhone 17 is 402 CSS
pixels wide.

The breakpoint was simply in the wrong place. Working the column arithmetic backwards,
`(vw - 28 - 30) / 6 - 4 >= 53.43` needs **vw >= 403**, so 401 and 402 were handed the
larger font in a column that could not hold it. Two pixels wide, and a phone landed in it.

Measured across the range before touching anything, Finnish, in Chrome against the
self-hosted Archivo:

| viewport | label size | column | "Huomenna" | |
|---|---|---|---|---|
| 320 | 9.6px | 40.00 | 48.57 | over by 8.57 |
| 375 | 9.6px | 49.00 | 48.57 | fits by 0.43 |
| 393 | 9.6px | 52.00 | 48.57 | fits |
| 402 | 10.56px | 53.00 | 53.43 | **over by 0.43** |
| 430 | 10.56px | 58.00 | 53.43 | fits |

So 402 was the reported failure and 320 was a worse one nobody had reported. Three changes,
all inside the narrow band:

**The breakpoint moves 400 -> 410.** .6rem needs 48.57px and fits from 374px up, so the
smaller size carries the whole band below 410 with room rather than handing over three
pixels early.

**`.day` gets `min-width:max-content` instead of `min-width:0`.** At 320px no size the
rest of the design uses fits an equal sixth, and the six labels are nothing like equal --
eight characters against two. max-content lets the one chip that needs more take it and
leaves the other five sharing the rest, so the row stays even wherever it can be:
**measured spread 0px from 375px up, 10.7px at 320px.** `min-width:0` was there to let a
flex item shrink under its content, which is exactly the behaviour that produced the
squeeze.

**The gap drops 6px -> 5px below 410.** Found by the test rather than by looking: at 375px
-- iPhone SE and mini, the narrowest common phone -- the margin was 0.26px unrounded. That
is inside the noise that produced this bug, so the width was working by luck. 5px makes it
1.10px by arithmetic and 1.43px measured.

**`min-height:44px` on the chip.** Two lines of small type plus the padding come to
42.5px on a phone, under the 44px tap-target floor -- and that was true before this
change, not caused by it. The shortfall is 1.5px, so `min-height` is the whole fix;
`.day` is a `<button>` and centres its own content, so the extra is split evenly and
nothing moves. Measured 44.00px at 320, 375, 393, 402 and 430, and **132 device pixels at
3x on the iPhone 17 simulator, which is 44.00 CSS px**. Desktop is untouched at 47px,
where the same box was already over.

Padding was the wrong instrument for it and an earlier draft of this used it: the
shortfall is not the same at every breakpoint, so matching 44 with padding needs a
different value per band, and once `min-height` is there the padding does not change the
rendered height at all. That draft's extra declaration was removed rather than left in
looking load-bearing.

Verified at 320, 375, 393, 402 and 430 in all three languages, both themes, and on a real
iPhone 17 simulator at 402: no clipping, one row, no overlap, no horizontal scroll, and
the row unchanged at 561px and up. The widest label in each language is Finnish's
"Huomenna" at 5.06 em-widths, ahead of "Tomorrow" at 4.67 and "I morgon" at 4.08, so
Finnish is the binding case and the other two ride along.

`tests/test_day_chip_fit.py` reads the padding, gap, font sizes and breakpoints out of
`index.html` and recomputes the column, against glyph widths measured once and stored per
1px of font-size. It demands a **1px margin**, not merely a fit, because the failing case
missed by 0.43px and a test that accepted "fits" would have passed a layout already inside
the rounding noise -- that requirement is what surfaced the 375px case. What it
deliberately does not do is model rendering: sub-pixel rounding decides the last half
pixel, and the browser and the simulator answered that half.

Getting the parser right took four attempts and each failure is worth naming, because they
all produce a test that passes while checking nothing: comments between `}` and the next
selector get read as part of that selector; an anchored rule regex consumes the previous
rule's `}` and so skips every second rule; `index()` on a media-block opener finds the
first of two identical ones and leaves the rest of them in the base scope; and a findall
for lengths-with-units reads `padding:0 14px 8px` as 8px because the `0` carries no unit.
The parse-pins test exists for exactly this.

Verified by breaking it seven ways: the breakpoint back to 400 (4 red), `min-width` back
to 0 (3), the gap back to 6 (2), the larger label in the narrow band (6), the ellipsis
backstop removed (1), chip padding widened (8), row padding widened (6).

### A deep link opened the right cinema once, then lost it (2026-09-01, sw.js v96)
Reported and reproduced: star Finnkino Cine Atlas, open a generated Tapio page, follow its
`/?area=sk-tapio` link. Tapio opens. Press reload and Cine Atlas opens instead, and the
reader is back in the 46-entry picker the link existed to skip.

**The cause was a tidy-up.** `?area=` was applied and then deleted from the URL in the
same breath:

    if(known(deep)){ state.area = deep; prefs.set({ area: deep });
                     u.searchParams.delete('area'); history.replaceState(...); }
    else { state.area = known(pr.fav) ? pr.fav : ... }

The deletion erased the load's own reason. On the next load `deep` was empty, the else
branch ran, and the favourite beats the stored area -- so the link's venue lost to the
star every time after the first. The stored write was to `area`, the last-browsed slot,
which was right and is kept: **arriving through a link never restars anybody's cinema.**

The old comment's worry was real -- "leaving it in place would override the picker on
every reload" -- and the answer is narrower than throwing the parameter away. Keep it
while it is the answer, and rewrite it when the reader picks something else. `selectVenue`
now updates an `area` parameter that is already present, and only then: an ordinary visit
to `/` must not start growing one because somebody used the picker.

A parameter that decided nothing is stripped instead. A URL reading `?area=sk-gone` beside
a picker showing Cine Atlas is the disagreement the deletion was reaching for, and it is
the only case that actually wants it.

Measured on the served page, favourite Cine Atlas throughout:

| | URL after | picker | favourite |
|---|---|---|---|
| `/` | none | Finnkino Cine Atlas | 1094 |
| `/?area=sk-tapio` | `?area=sk-tapio` | Savon Kinot Tapio | 1094 |
| reload of that tab | `?area=sk-tapio` | Savon Kinot Tapio | 1094 |
| pick Maxim there | `?area=sk-maxim` | Savon Kinot Maxim | 1094 |
| reload again | `?area=sk-maxim` | Savon Kinot Maxim | 1094 |
| `/?area=city:Helsinki` | kept | Kaikki Helsinki (12) | 1094 |
| `/?area=sk-gone-forever` | stripped | Finnkino Cine Atlas | 1094 |
| `/?area=sk-tapio&lang=en` | both kept | Savon Kinot Tapio | 1094 |

The favourite is 1094 in every row, and the star reads unpressed on the Tapio and Maxim
rows, so the picker, the URL and the star agree at each step. No `pushState` is involved
anywhere in this path -- both writes are `replaceState` -- so back and forward leave the
page rather than replaying a state that could disagree with the picker.

`startupArea()` and `areaParamAfterSelect()` are pure and extracted verbatim by
`tests/area_routing_harness.js`, the way `healthState`, `venueRows` and `priceLabel` are;
18 tests drive the shipped functions rather than a copy. Verified by breaking it seven
ways: `keepParam` false for a deep link, which is the original defect (2 red); the
favourite checked before the link (5); the link written into `fav` (1); a stale link left
in the URL (1); selection not rewriting the parameter, so a reload bounces back (5);
selection always writing one, so `/` grows a parameter (1); and the stored area checked
before the favourite (4).

### The deep link carries the language too (2026-09-02, sw.js v97)
The generated pages come in Finnish and English and every one of them linked to
`/?area=...`, while the app read its language from `kino-prefs` alone and defaulted to
Finnish. An English theatre page therefore opened a Finnish app for any reader without a
stored choice, which is most readers arriving from a search. Found while designing the
landing-page redesign and fixed ahead of it, so the pages can link to `&lang=fi` and
`&lang=en` on the day they land.

`startupLang(param, stored, LANGS)` sits in the same marker block as `startupArea` and
follows the same rules, for the same reasons:

- **A supported value in the URL wins on arrival**, over whatever is stored. Exact match
  against `LANGS`, so `EN` and `xx` decide nothing.
- **It stays in the URL while it is the answer**, so a reload applies it again -- the
  lesson of the venue half, where deleting the parameter after applying it lost the
  selection on the second load.
- **It seeds `prefs.lang` only when nothing valid is stored.** A first-time reader keeps
  the language of the page they came through on later plain visits; a Finnish reader who
  follows one English link is not switched for good. It never writes `fav` or `area`.
- **The toggle rewrites a `lang` that is already present**, and only then, so the value
  the reader arrived with cannot put them back on reload and an ordinary visit to `/`
  never grows a parameter. Same shape as `areaParamAfterSelect`.
- **A value the app does not have is stripped** with `replaceState`, and the stored or
  default language applies -- a URL saying `?lang=xx` beside a toggle showing FI is the
  disagreement the venue half already refuses.

Read at the point the stored language used to be read, before any render, so every
`L[state.lang]` lookup and the English `films.json` fetch in boot see the same value a
stored choice would have given them. No new render path.

Extracted verbatim by `tests/area_routing_harness.js` alongside the venue functions and
driven by 13 new cases in `tests/test_area_routing.py`. Verified by breaking it seven
ways: the stored language checked before the link (4 red), a valid link not kept in the
URL (3), the link always overwriting the stored choice (1), the link never seeding a first
visit (1), a case-insensitive match (1), the toggle always writing a parameter (1), and the
default moved off Finnish (3).

Checked live against the served page as well, on a fresh origin with nothing stored:
`/?area=sk-tapio&lang=en` opened Tapio in English with `{"lang":"en","area":"sk-tapio"}`
written and the favourite untouched; pressing FI rewrote the URL to `lang=fi`; opening the
English link again applied English and left the stored `fi` alone; `lang=xx` and `lang=EN`
were stripped while `area` stayed, the city form included.

### Confirmed empty beats kept data (2026-09-05, sw.js v107)

Kino Metso's Muurame had one screening on 2026-09-04 at 19:00, its last for now. The
23:39 UTC cloud run found the town empty and `run.py` took the "no showtimes, keeping
previous data" branch: the file kept the past show, the venue was listed `stale`, the
provider read `partial`, and `oldest` was pinned to 17:43 UTC while three venues were fresh.
Read from the live feed through the adapter's own parser: Muurame 0 shows in 21 days,
Petäjävesi 5, Tikkakoski 0, Vaajakoski 3. Not a fetch or parse failure -- a touring cinema's
town is empty between visits, and the rule from 2026-08-31 honoured the adapter's
confirmation of emptiness (`EMPTY_VENUES_CONFIRMED`) only for venues that had never had data.

**The invariant now**, the user's, and the order the loop checks it in:

1. Confirmed empty from a successful adapter response -- the module sets
   `EMPTY_VENUES_CONFIRMED` and reported the venue explicitly -- publishes a fresh empty
   file and records the venue as `pending`, whether or not old data exists.
2. Zero rows without that confirmation keeps the previous file and marks the venue `stale`.
3. A fetch, schema or parse failure never reaches the loop: the site fails as a whole and
   every file it owns stays as it was.

That distinguishes "the programme has ended" from "we failed to retrieve it", which the
previous order could not. The evidence trusted is exactly what the `pending` rule already
trusted: nexxo's schema check raises on a changed payload and a mis-mapped room lands in
the unclaimed-room log, so its `[]` is positive. eTiketti does not set the flag and keeps
rule 2. No new state, no schema change; `pending` now means "no programme at the moment"
rather than "not started", and the wording follows: "Ei ohjelmistoa juuri nyt", "Inget
program just nu", "No programme right now", in the footer line and the provider tooltip.

**Tests**, `tests/test_run_partial.py`, `ConfirmedEmptyTest`: confirmed empty with an old
file (pending, empty file stamped now, provider ok, `oldest` now), confirmed empty with no
file, zero rows from a module without the flag (stale, kept), a confirming module that did
not report the venue (stale, kept), a failing fetch (every file untouched, no provider
file written), and Kino Metso's shape with four venues -- one ended, one never started,
two live -- reading ok with `oldest` from the live venues. Mutations, each restored
byte-identical and each red: the old order restored (3), the reported-venue condition
dropped (2), pending granted without the flag (9), the fresh stamp on the empty file
replaced by the old one (4).

### Search Console baseline, 2026-08-29 to 2026-09-02 (read 2026-09-04)

First export, web search, five days of data. **The tables do not share a denominator**, so
none of the figures below is a share of another table: the chart, devices and countries
tables sum to **1776 impressions and 12 clicks** (CTR 0.68 %); the pages table sums to
**1951** because an impression counts once per URL and one query can show two of ours; the
queries table sums to **1300** because rare queries are anonymised and left out. A later
export is comparable to this one only table by table, over the same window and filters.

What the five days showed: theatre pages carried about 92 % of page-level impressions, 74 of
the 170 canonical pages appeared, and the front runners were small-town cinemas -- Leffabuumi
Kinolinna and Kino Ritz 168 and 167 impressions at positions 5 to 7, Savon Kinot's four pages
about 300 together, BioRex Seinäjoki 86 -- while Finnkino pages sat at positions 12 to 20.
Visible queries were the cinema's name (746), "elokuvat <city>" (285) and "<cinema>
ohjelmisto" (248, with two of the three attributed clicks); no query contained "leffavuoro".
Mobile position 8.4 against desktop 23.6. The signal is early and small: a page per small
cinema ranks on page one for that cinema's name within days, where competition is thin.

**Decisions on that read**, the user's, 2026-09-04:

- No broad SEO change on five days of data. Re-read after two to four more weeks.
- **No city pages for one-cinema towns.** They would duplicate and compete with the theatre
  pages that already rank; the theatre page carries the city intent.
- **The one experiment, when run: "ohjelmisto" in Finnish theatre-page titles and
  descriptions**, the word searchers actually type and the pages never say. On a subset of
  pages against an unchanged control set, the same pages compared over two to four weeks,
  designed and measured like any other `build_pages` string change.
- **Desktop position and the absence of brand queries: watch, don't act.** Both are too small
  to mean anything yet.

### Savon Kinot moves to the local half (2026-09-04)

Cloud fetches #158 (11:11 UTC) and #159 (14:26 UTC) failed on one provider: www.savonkinot.fi
answered `403` on all three attempts, `Server: cloudflare` with a CF-Ray from the Dallas
edge and no `Retry-After`, so Cloudflare refused at the edge before the cinema's server saw
anything. Every run from 09-02 23:14 to 09-04 07:23 UTC had read the site normally (66 to 73
showtimes at Tapio). The other 16 eTiketti hosts fetched in the same runs.

**Not the polling rate.** Cloudflare's rate limiter answers `429` with `Retry-After`; this
was `403` without one. The refusal hit the first request of the run, the listing page,
after 3.7 hours with no contact, and again 3.2 hours later, longer than any rate window.
The adapter makes one listing request plus one per film -- 23 films that day, about 24
requests at 1.2 s spacing, at most eight runs a day. Runner addresses change between runs
and the block held across two of them, so it keys on the address range, not the address.

**Address-based, so the fix is the address.** From an ordinary connection the site answered
`200` in 0.6 s with the adapter's exact User-Agent, with a browser one and with none. The
registry entry moves from `where="cloud"` to `where="local"`: the cloud run skips the site
and the local wrapper's `run.py etiketti --where local` reads it beside Joutsan Kino, four
times a day instead of up to eight. Same route Finnkino, Kino Akseli, Kino Engel and Joutsan
Kino already take; the local half is now five providers and 26 of 75 venues, which is
recorded against the open item about moving that half off the laptop. Nothing else changes:
adapter, headers and pacing are as they were on 2026-08-30.

**Exercised from an ordinary connection before the push**, from a scratch directory so no
data was hand-committed: `run.py etiketti --where local` read Savon Kinot and Joutsan Kino,
six Savon Kinot venues with showtimes, `exit=0`. The committed data catches up on the
wrapper's next local run, which is the run that matters; the cloud half's next run turns
`run-etiketti.log` green by no longer asking.

`tests/test_run_routing.py` pins the two local eTiketti sites in SITES order and the
registry field; the halves-disjoint-and-complete test already covers the rest.

### A screening note is not a synopsis (2026-09-03)

Found by an external review: Cinema Niagara's sheet for "Keltaiset kirjeet" opened with
"Gildan seniorikinonäytökset joka kuun ensimmäisenä tiistaina. Elokuvaliput seniorikinon
näytöksiin saat hintaan 9€/kpl. Lipun hintaan sisältyy leffakahvit!" -- Gilda's senior
screening, its price and its coffee, on a Tampere cinema that has none of them.

**How it got there.** `films-extra.json` holds one Finnish synopsis per normalised title,
filled by the first provider to publish one and read by every cinema showing the film, and
that is the right design for what it usually holds: several chains run the distributor's
blurb verbatim. Gilda's MyCloudCinema `description` is HTML in paragraphs, and every one of
its senior-screening entries opens with a paragraph of the cinema's own before the blurb
(read once from its movies endpoint on 2026-09-03: 7 of 41 entries, all with the note as
the first `<p>`). The adapter stripped tags and merged the whole thing, a screening
sometimes carries the plain film title, so the note landed under the plain key too, and
fill-if-empty then kept it there: Gilda's *current* description for the film is clean and
could never replace it. Measured across the committed file: **10 of 166 entries** held a
note. Five plain keys read by every cinema -- keltaiset kirjeet, la grazia, myrskyn ikkuna,
rakkautta ja virtahepoja, 70mm the odyssey -- four `seniorikino …` keys that only Gilda's
own screenings read, and Bio Vuoksi's "Juhlanäytös! … Liput 8€ maksetaan Pennittömien
edustajalle" under nouvelle vague, a whole text that is an event notice and not a synopsis.

**Two rules, at two layers, and the shared slot stays shared.**

- Structural, at the adapter. `synmerge.drop_notes_html(desc, names)` splits on `</p>` and
  drops a paragraph that quotes a price or names the cinema (`names` are stems matched as
  word prefixes, so "Gilda" catches "Gildan"); Gilda passes `("Gilda",)`. The paragraph is
  the source's own boundary, so this removes exactly the note and keeps the blurb whole. A
  sentence split would have been a guess ("klo 18.15", "la 12.9." end sentences that are
  not).
- Generic, at the merge. `synmerge.is_note(text)` is true for a price in either order
  (`9€`, `€ 10`, `12 euroa`, `5 EUR`), and `merge()` refuses such text outright, counting it
  as `synopses skipped as screening notes (price): N` in the committed log. A film synopsis
  never quotes a ticket price, so this costs nothing, and it holds for the adapters that
  strip tags before merging, which is all of the others. The slot stays empty for TMDB.

**Provenance was considered and declined.** The review proposed storing which provider
supplied each synopsis and reusing text only for that provider's own cinemas. That fixes the
leak by giving up the sharing: every cinema whose adapter publishes no text would fall
back to TMDB, whose Finnish overview exists for only some films, and the distributor's blurb
is the same text at every cinema, which is why one slot was chosen. The defect was text that
is not a synopsis in a field named as one, and it is fixed where the text is read. What
remains recorded and accepted: Cinema Orion's "Ainoa näytös, klubialennus." lines carry no
price and no cinema name and still merge; the rule for them, if one is ever wanted, would
be Orion's own.

**The cache was repaired in the same commit**, as the Finnkino "?" repair was: the exact
Gilda paragraph stripped from the nine entries that began with it, which leaves the text the
fixed adapter now produces, and nouvelle vague blanked, since the whole text is a notice.
Written back through `common.write_json`, so the next run's serialisation is byte-identical
to it. Nothing needed a run to be exercised: the merge rule is unit-tested on a temporary
file and the adapter rule goes through `gilda.parse()` on a two-paragraph fixture.

**Tests**, `tests/test_synopsis_notes.py`: the paragraph rule on price, on the cinema's
name, on text without paragraphs; `is_note` on prices in either order and on the years and
durations it must not match; `merge()` refusing a priced text, merging the clean one beside
it and staying silent about skipping when nothing was skipped; and `gilda.parse()` yielding
the blurb alone. Five mutations, restored byte-identical and each red: the price rule
removed (3; the Gilda paragraph still falls to the name rule), the name rule removed (1), the merge guard removed (1),
Gilda stripping tags again (1), the skipped line printed unconditionally (1).

### A direct film link opens its sheet on load (2026-09-03, sw.js v106)

Found by an external review: `/?area=cn-tampere&lang=fi#m=61` loaded the Niagara list with
the fragment intact and the sheet closed, and a refresh with a sheet open closed it.
`syncSheet()` reads `#m=<id>` and opens the sheet, and it ran on `hashchange` and inside
`applyLang()` when a sheet was already open -- nothing called it after the first schedule
arrived, so the one way to reach a film from outside the app never opened it. Reproduced
headlessly against the live site with an id from the day's list before changing anything.

The call sits after the boot's `await loadSchedule()`, guarded on a fragment being present:
`showSheet` lists the film's screenings from `jsonCache[state.area]`, which that first load
fills, so a sync placed earlier would open an empty sheet, and an ordinary load must not
touch the sheet at all. Before the `catch`, so a failed load renders the error and opens
nothing. Checked on the served tree: with the fragment the sheet is open, not inert, and
titled with the film; without it the sheet stays inert.

`tests/test_sheet_direct_load.py` pins the call, its position after the load and before the
catch, the `hashchange` listener that still exists, and the reason for the order. One
mutation, the call removed, red; restored byte-identical.

### A tag the room already names is said once, and the Ⓐ stays on the stub (2026-09-03, sw.js v105)

Two things a reader found on the day the Ajat ticket lost its room. First, the meta line
now read "LUXE 6 · K-16 · 172 min · 2D · Anniskelu · LUXE": the room carries the format and
the method tag repeats it. The pair had always been there, split between the stub label and
the meta line, and putting both on one line made it visible. Measured across the committed
data: **774 rows in five classes**, LUXE rooms and LUXE (319 tag rows), "N Plus" rooms and
Plus (256), iSense (88), Prime (50), IMAX (21); no tag is ever repeated inside one method
string, and the one venue whose *name* carries a format, LUXE Mylly, also names it in every
room, so the room rule covers it.

**The room keeps the word.** It is the adapter's value verbatim, what the ticket prints,
and the app's own rule since 2026-08-27 for the stub label: `stubTags` drops a tag the room
name contains, case-folded, and drops plain 2D, which sits on 2524 of 5020 rows and says
nothing. The Ajat line now runs the same function over the screening's tags, so the two
places a screening's tags render agree, and 2D leaves the Ajat line the way it left the
stubs. IMAX in a "Sali 2", 3D anywhere and every word the room does not say survive; the
card's shared pills are untouched and still show 2D when every screening is 2D.

Second, toggling the Anniskelu filter made every Ⓐ disappear. The card folds a tag every
surviving screening shares onto the card, and under that filter every survivor shares
Anniskelu, so it became an ANNISKELU pill on the card and left the stubs -- the filter
removed the marker for the thing it filters on. **A tag drawn as a glyph never folds.**
`common` skips `glyphOf(f)`, so the Ⓐ sits on every anniskelu stub whether or not the
day's screenings all are, and the card never grows the pill; the glyph key in the footer
already renders only when a shown screening carries the tag. Words still fold: a film whose
every screening is LUXE says LUXE once on the card.

Measured on the served tree, Kaikki Helsinki filtered to "odyss", 1200 px: Ajat 18 rows,
no meta line naming a room word twice, no 2D, one line each; Leffat with the Anniskelu
filter on, one card, 11 stubs, 11 Ⓐ, no card pill; without the filter 18 stubs, 11 Ⓐ.
Sello Ajat at 375: 17 rows, no duplicate, no 2D, rows 59 to 70 px.

**Tests**, `tests/test_stub_tags.py` with `tests/stub_tags_harness.js`: `stubTags` is
sliced verbatim between marker comments the way `priceLabel` is and run over the five data
classes, the survivors, the null room, the case fold and an empty tag; the Ajat line is
pinned to run it and the fold to skip glyph tags. Five mutations, restored byte-identical
and each red: the raw method string back on the Ajat line (1), glyph tags folding again
(1), the room clause removed (2), the 2D clause removed (3), a case-sensitive match (1).

### The Ajat ticket is time and price (2026-09-03, sw.js v104)

Reported from a desktop screenshot of Finnkino Sello's Ajat list: the film titles started
at three different x positions. Since v100 the time-mode stub grew to its content between
158 and 220 px, so a "Sali 3" ticket measured 170.2, "Sali 1 Ⓐ" 191.2 and "LUXE 5 Ⓐ"
201.8, and the titles sat at 254, 275 and 286. On a phone the same rows left the title
119 to 163 px at 375 and 64 to 96 at 320.

**Decision.** In the Ajat list the ticket is the time and the price: 62 + 56 + 2 = 120 px by
construction, no floor and no cap, 122 with a chain rule in a combined view. The room, the
venue tag of a combined view and the screening's own age limit move onto the meta line,
which has the full row width: "Sali 1 · K-12 · 145 min · 2D · Anniskelu · englanti · tekstit
suomi/ruotsi", and "Finnkino Plevna · Sali 5 · S · 78 min · …" in Kaikki Tampere, the venue
first so the two read as one address. The 18+ limit keeps its pill markup (`ageGlyph`) and
sits after the room; the Anniskelu glyph is not carried over, because the meta line already
says the word. The sold-out word moves with the room. The room never breaks across lines
(`.room{white-space:nowrap}`); the widest in the data, "KINOLINNA | SALI 1" at 103 px, fits
the 201 px column at 375. Applied at every width: one markup, one rule, and the same
silhouette on a phone and a desktop, rather than a breakpoint with the room rendered twice.
The card's row ticket and the sheet's keep the room, since there the ticket is the only
place the room has; a test pins that exactly two renderers still emit `.aud`.

**Measured on the served tree**, Sello, Ajat, both themes:

| viewport | before: stub / title column | after: stub / title column |
|---|---|---|
| 320 | 170.2 to 201.8 / 64 to 96, three columns | 120 / 146, one column |
| 375 | 170.2 to 201.8 / 119 to 163 | 120 / 168 to 201 |
| 402 | 170.2 to 201.8 / 146 to 190 | 120 / 168 to 228, no title ellipsised |
| 1200 | 170.2 to 201.8 / 845 and up | 120 / one column |

Every ticket 40 px tall, no row or page overflow, meta line one to three lines at 375 (rows
59 / 70 / 87 px) where it ran to four beside a 202 px ticket, and up to four at 320. Kaikki Tampere at 375: 51
rows, 122 px, venue tag first on every row. Orion, which publishes no room, is unchanged
apart from the alignment. The before figures include a pre-existing 2 px poke of the meta
text into the page margin at 320 on the LUXE rows; the page never scrolled horizontally.

**Two candidates measured and declined**, renders in the review folder outside the repo:

- **A fixed 204 px stub with the room inside.** One line of CSS. Orion then shows a 204 px
  ticket with nothing between the time and the price, and every cinema without rooms (22
  venues publish none) pays 34 px of title on a phone for a label it does not have.
- **One shared column per list, room inside**: a grid over the rows with `subgrid` rows and
  `fit-content(220px)`, the label allowed to wrap and the glyphs dropping under it. It
  aligns the titles and sizes the column to the list, Sello 201.8, Orion 158, Kinolinna 220
  with the room on two lines, Plevna 218.9. Declined because the phone title column stays
  119 px at 375 and the column moves when a filter removes the rows that set it. Two
  things learned on the way, kept because the next grid will meet them: a `column-gap` set
  on a subgrid but not on its parent is applied as margins on the subgrid's items, so the
  stub filled 213 of a 220 track until the gap moved to the parent; and `fit-content` with
  `overflow-wrap:anywhere` on the label lets the column shrink to the wrapped label, while
  `break-word` keeps the one-line width.

**Tests**, `tests/test_compact_ticket.py`, `TimeModeTicketTest`: the time-mode stub is time
and price with no `.aud`, `.loc`, glyph row or age glyph inside; the meta line opens with
venue, room, age pill and sold-out word in that order; `.trow .stub` has no width floor or
cap and the `.trow .stub .aud` rule is gone; the room does not wrap; exactly two renderers
still emit `.aud` and three the price. Five mutations, each restored byte-identical and each
red: the room put back into the stub (2), the room dropped from the meta line (1), the venue
placed after the room (1), `min-width:158px` restored (1), the nowrap rule removed (1).
Generated pages are untouched: `build_pages.py` has no times view.

### Tickets are 40 px (2026-09-02, sw.js v103)

A reader found the tickets heavy on a phone. The row ticket had gone from 32 to 44 px that
same morning when it gained the price compartment, and the combined view's tickets were 44
too, so a one-line "17:30 · Plevna · Sali 7" sat in a 44 px band. Rendered the same tickets
at 44, 40 and 36 and at 44 with lighter strokes, with the app's own stylesheet, and chose
40: it takes the weight off without crowding the two-line "alkaen 10€", which sits 27 px
tall inside a 36 px ticket's 34 px interior. A uniform 160 px ticket for every view was
mocked up first and declined: at that width the combined view's venue names truncate on
three of five sample tickets with the chain-prefixed label and on all five as one row, and
a no-room cinema gets a blank second line. The mock is in the review folder outside the
repo; the current anatomy stays.

Only `min-height` changed, in the client's row and grid tickets and the generator's, 44 to
40. WCAG 2.5.8 asks 24 px. Measured live at 375: Tampere combined view 33 tickets at 40,
two at 43.5 where the venue label wraps, time and venue text inside every ticket, no width
overflow; Orion single view and time mode 40 with "alkaen 10€" fitting; Helsinki sheet 109
at 40, one column; Niagara theatre page 19 at 40, prices fitting; Tampere city page 40 with
wrapped labels growing a ticket to 43.7 or 59.5, as before. Pinned in
`tests/test_compact_ticket.py` and `tests/test_ticket_anatomy.py` for both renderers; a
mutation back to 44 on the client's row ticket, the generator's row ticket and the
generator's grid ticket each goes red. 170 pages rewritten once, the second regeneration
writes nothing. Deliberately not changed: the header's 44 px controls, the CTA and the
language segments, which are not tickets.

### The single-cinema ticket has a price compartment (2026-09-02, sw.js v102)

The row stub is the ticket a visitor sees most: one cinema, its screenings in a row. After
the price moved onto the screening it trailed the room as a small muted word with no
compartment of its own, and a ticket without a price was a different shape from one with
-- 125.5 px against wider, 32 px tall, the price .72rem muted at the edge, and the
perforation still after the time where it had always been, 3.8 px off its own seam.

**Decision.** Presentation only; ownership is unchanged. The last 56 px of every row ticket
are the price compartment, the tear-off end: the dashed seam is its left border and the
notches are centred on that seam from the same variable (`--pw`, `right:calc(var(--pw) -
4px)`), so they cannot drift. The compartment is always there and blank when the cinema
publishes no price -- never a dash, "free" or a zero -- so priced and unpriced tickets in
a row share one silhouette. The price is `var(--ink)`, 700, .78rem, centred on the time's
axis; the time stays .92rem/800. No accent, badge, pill, icon or extra border. The seam
after the time is gone: one perforation, at the stub end. "alkaen 10€" and "från 10€"
wrap to two lines inside the compartment (`white-space:normal`, line-height 1.1). The row
ticket gains the 44 px minimum the other views already had. The generated theatre pages
carry the same anatomy, their notches now pseudo-elements of the price compartment. The
combined city and "all" views are untouched: their time compartment, seam and notches stay
where the previous entry put them, and an empty compartment collapses there (`:empty`).

**Measured live**, preview browser. Cinema Niagara at 375 and 1200, both themes: 143.8 ×
44 px, compartment 56, seam and notch centre both at 86.8, price 12.48 px / 700 in ink
(#16181D light, #EDEDEA dark), text 22.4 px wide inside, centred on the time to 0 px, no
clipping or overflow. Kotkan Leffat Trio 123, rooms and prices: 6 tickets, 44 px, rooms
intact, aligned. Finnkino Plevna, no prices: 25 tickets, all blank compartments, 172 px
wide like a priced ticket of the same shape, aligned, notches drawn. Cinema Orion in
Swedish: "från 10€" wraps to two lines, text 23.4 × 27.2 inside the compartment, 44 px.
Time mode: 158 px rows, 44 px, aligned. Generated theatre page for Niagara: 19 tickets,
121.8 × 44, seam and notch 64.8, ink .78rem; Plevna's page: 132 blank compartments,
aligned. Combined Tampere view and city page: seam 64, 44 px, empty compartments hidden,
priced ones still .72rem muted -- unchanged.

**Tests**, `tests/test_compact_ticket.py`, 13: fixed compartment and seam, notches from the
same variable, ink a step below the time, every renderer emits the compartment whether or
not there is a price, the combined view untouched, no film-level or sheet-header price;
generator: priced ticket ends with the price inside the anchor, unpriced ticket has the
same anatomy with a blank compartment, room and price both survive, long localised labels
kept whole and allowed to wrap, compartment and notches match the client, generated
combined view untouched, no film-level price. Nine mutations, restored byte-identical and
each red: compartment unfixed, notches back at 56 px from the left, one renderer emitting
the compartment only when priced, the combined view no longer hiding an empty one, price
muted; and the generator's compartment unfixed, notches back on the room seam, conditional
emission, `:empty` rule removed. 170 pages rewritten once; the second regeneration writes
nothing.

### The combined view's stub is the same ticket (2026-09-02, sw.js v101)

The combined city view hid the stub's perforation on purpose: `.stubs.grid .stub::before,
.stubs.grid .stub::after{display:none}`, "the perforation reads wrong on a stacked stub",
and the generated city pages hid their notches the same way. The stacked stub put the time
above the place, so a notch at the row stub's seam position pointed at nothing. Visual
review of the Tampere view during the price change showed what the choice cost: beside a
single-cinema view whose stubs read as tickets, the combined stubs read as generic rounded
cards, and the chain-coloured left rule was carrying the whole booking affordance alone.

**Decision.** Every showtime is the same ticket component in every view. Suppressing the
signature form was deliberate and is reversed, because it weakened the affordance and the
product's consistency. Not by deleting the rule: the notch has to sit on a real divider.

**Anatomy.** The combined stub is the row stub adapted. A time compartment on the left,
`--tw:64px` wide -- 12 + 41.8 + 10, the row stub's own padding around a tabular "00:00"
at .92rem, measured -- spanning the full height; the details compartment beside it,
wrapping as it needs, with a dashed left border that is the seam; the price at the
trailing edge in its own column. The notches are placed at `calc(var(--tw) - 4px)`, so
the seam and the 8 px notch's centre share one x by construction, in every state. The
generated city pages use the same grid; their notches are pseudo-elements of the details
compartment and now sit at `left:-4px` rather than `-5px`, which puts the centre on the
seam instead of one pixel left of it, on theatre pages too. `min-height:44px` keeps the
touch target where the stacked stub had it. A grid item's default minimum is its content,
so one unbreakable "Tennispalatsi" in a narrow column ran under the price in a fixture;
`min-width:0` and `overflow-wrap:anywhere` on the details side, and the room span allowed
to wrap in grid mode, break the word instead. Past and sold-out stubs keep the silhouette
and their own treatment; the "näytä menneet" control is a button on the meta line and has
no pseudo-element.

**Measured live**, preview browser, Tampere combined view at 320, 375, 402 and 1200 in
both themes: 37 stubs, seam 64.0 and notch centre 64.0 on every one, notches rendered,
heights 44 to 56 px, time compartment full height, no clipping, no overlap, no horizontal
overflow. Fixture page with the app's stylesheet -- sold out, past, "alkaen 10€", a
six-line venue and room, no price -- all six aligned at 64, none crossing the seam or the
price. Generated Tampere city page: 90 stubs aligned at 375 and 1200, heights 44 to 73,
no clipping. The single-cinema row stub is unchanged: 32 px tall, and its notch centre
measures 60 against a seam at 63.8, a 3.8 px offset it has always had -- noted, not
touched here, since the instruction was not to regress that shape.

**A second column needs a 240 px ticket.** The grid had `minmax(168px, 1fr)` and a phone
override of 140 px, inherited from the stacked stub, where the place had the whole width
below the time. With the time compartment beside the details that minimum was far too
small, and the film sheet is where it showed: the sheet is 335 px wide at a 375 px viewport,
so two 163 px columns left 4 px of details beside "alkaen 10€" and "Cinema Orion" broke
letter by letter over nine lines, 151 px tall; at 520 px three 155 px columns left 1 px.
The `overflow-wrap:anywhere` guard made that not overlap, and was never meant to be the
presentation. Both grids now use `minmax(min(240px, 100%), 1fr)` and the phone override
is gone: 240 is 64 of time, up to 75 of floor price and 90 for a cinema name to keep its
words, and `min(…, 100%)` keeps the single track from overflowing a container narrower
than 240. Measured after, real Autofiktio sheet in Helsinki: one column at 375, 402 and
520 (details 176 / 203 / 321 px), two at 600 (276 px tickets, 117 px details) and from 700
up where the sheet is 680 wide (315 px tickets, 156 px details); 109 stubs, 0 broken
words, all 44 px, all aligned. Card view at 1200: three 311 px columns, 0 broken. Helsinki
city page: two 337 px columns at 1200, two 305 px at 768, one 257 px column at 375, 340
stubs aligned, 0 broken words, no clipping, 44 to 59.5 px tall. Pinned in both renderers,
and a mutation back to 168 px is red in each.

**Tests**, `tests/test_ticket_anatomy.py`: the suppression rule is gone in both renderers;
a second column needs a 240 px ticket, in the client and in the generator;
the time compartment, seam and notch position derive from the same variable in the client;
the generator's grid has the seam border and the notch on it; both views share one stub
markup; the price stays inside its own stub; the past-times control is not a ticket; a
rendered city stub keeps venue and room on the details side. Mutations, restored
byte-identical and each red: the client's `display:none` restored, the client's seam
removed, the generator's suppression restored, the generator's seam removed. 170 pages
rewritten once; the second regeneration writes nothing.

### A price is the screening's, never the film's (2026-09-02, sw.js v100)

Reported from a screenshot of the Tampere combined view. Autofiktio had three screenings
on 2026-09-02: Cinema Niagara 16:15 at `11€`, Finnkino Plevna 17:30 and 20:15 with no
published price. The card's metadata line read "espanja · tekstit suomi/ruotsi 11€", and
no stub carried a price. A reader takes that as the film's price at every screening,
including two where Finnkino publishes none and may charge something else.

**Root cause, in both renderers.** The client folded `priceLabel(m.times)` onto the card
(and `priceLabel(all)` onto the sheet). `priceLabel` reads the cheapest positive price
across the rows and skips rows without one, so a priced subset became a film-wide figure.
The generator did the same with `price_label(shows)` on the card, and its "differing
prices go on the screening" rule counted the empty string as a differing price, so the
Tampere case printed `11€` twice: once on the card, once on Niagara's stub.

**Decision.** The price is the ticket's. Provider, time, format and ticket type differ
between screenings, so a value from a non-empty subset must never be promoted to the film.
Both renderers now put each screening's own `priceLabel([s])` in a dedicated
`<span class="price">` inside its stub, and nothing on the card or in the sheet header --
even when every screening happens to agree, because the agreement is a fact about today's
screenings and not about the film. A screening without a price gets no element, so there
is no empty separator or spacing. A provider's own floor survives as `priceLabel` already
kept it: "alkaen 10€" renders "alkaen 10€" in Finnish and "från" / "from" in the other
two. JSON-LD is untouched; it was already per screening.

**Design.** The stub stays one click target: the price is a child span at the trailing
edge, `.72rem`, muted like the room, no border, so the time stays the strongest element
and the price does not read as a second button. In the stacked stub of the combined view
the stub becomes a two-column grid, `"time price" / "aud aud"`, so the price sits on the
time row without a third line and the markup is the same in every view; the row stub keeps
its flex row with the price after the label. The time-mode row stub was a fixed 158 px, and
"alkaen 10€" beside it ran 4 px past the edge under overflow:hidden (measured: price right
231.3 against a stub right of 228); it now grows to its content, no shrink, capped at 220
px, and the film title beside it ellipsises instead, since it can and the price cannot.
Measured after: Cinema Orion in time mode 158 / 162.3 px wide at 320 and 1200 with no
clipped stub, Kotkan Leffat Trio 123 with rooms and prices 158 / 170.6, rooms intact. The
row stub's 32 px height is what it was: the price carries the time's own vertical padding.
Measured live in the preview browser on the
Tampere case at 320, 375, 402 and 1200 px in both themes: every stub 45.5 px, price inset
1 px from the trailing edge, no overlap with the time or the place, no clipped stub, no
horizontal overflow, zero euro signs in any card meta. Helsinki in Swedish at 320, with
Orion's "från 10€" floors: 140 stubs, 3 priced, none clipped. Screenshots before and after
at 375 and 1200 in both themes, app and city page, kept outside the repo.

**Tests.** Generator: one priced screening among two unpriced prices only itself and the
card says nothing (the committed Tampere case, field for field); two different prices stay
with their screenings; the same price three times is on each stub and never the card; no
prices means no price markup and no trailing artefact; "alkaen 10€" survives per language;
city and theatre pages attach the price to the same stub; a hostile price string cannot
reach the page; hrefs, venue labels and rooms are unchanged; and across every generated
page the euro sign occurs only inside a stub's price element, never in a meta line, with
synopsis prose excluded since a cinema's blurb may quote a price. Client: every
`priceLabel(` call folds one row, `priceLabel(m.times)`, `priceLabel(all)` and
`sheetPrice` are gone, and all three stub renderers emit the element. Mutations, restored
byte-identical: film-level fold restored (98 red across the suite), one screening's price
copied to every stub (4 red), price element dropped (7 red), the client's fold restored
(red on the source tests). 170 generated pages rewritten once; the second regeneration
writes nothing.

### The landing pages belong to the product (2026-09-02)
The 168 canonical pages under `/teatteri/`, `/kaupunki/`, `/en/theatre/` and `/en/city/`
were built to be indexable and read like it: system font, boxed cards, a CTA that said
"Ajantasaiset ajat, suodattimet ja koko ohjelmisto: Leffavuoro", and a showtime that
read `16:00 Sali Tapio 4 FI-S, SV-S` with spaces for separators. A reader arriving from a
search saw a page that did not look like the app it was sending them to. Redesigned in
`build_pages.py` alone: no JavaScript on the pages, no new data, the same 4-day and 2-day
horizons, the same JSON-LD, titles, descriptions, canonicals and hreflang pairs, the four
legacy redirects byte-identical.

**What a page is now.** Wordmark and the app's FI · SV · EN selector in a header bar; the
unchanged h1;
a subline (`Joensuu · savonkinot.fi`, or `12 teatteria`); a two-sentence intro; one CTA;
sticky day headings; a film per row with the app's poster sizes (72×104 below 560 px,
92×132 above), rating chip, credited TMDB score, runtime and genres, the synopsis once per
page; ticket-shaped showtimes; on a city page a chain legend after the CTA and the venue
links as 44 px chips at the foot. The tokens are the app's for both themes -- see "The
landing pages follow the app's theme" below for how the theme is chosen -- and the
typeface is the same two self-hosted Archivo files -- one same-origin request, so the
README's privacy claim holds as written. The docstring's old "no webfont" line was about
Google Fonts and is rewritten.

**The CTA carries both halves of the deep link.** `/?area={id}&lang={fi|en}` -- the
language half is the entry above. The label is `Avaa koko ohjelmisto` and `See the full
programme`, one `<a>`, one line, 48 px tall: the app's selected-segment treatment, filled
`--ink` with `--bg` text at weight 800, the only filled element on the page, against the
outlined tickets that link out. It first shipped as a two-line sentence with "– nyt ja
tulevina päivinä" / "and upcoming screenings" under the label, which measured 64 px on a
phone and read as a hero panel rather than a button, pushing the first day heading 15 to
16 px further down; the intro sentence already says the app carries the days ahead, so
the button now says only what it does. Measured after: 48 px at 320, 375, 402 and 1200,
one line in both languages at 320, the arrow 61 px clear of the label at its tightest.

**The showtime label is the requested shape and nothing more.** `stub_parts()` returns
room, spoken language and subtitle languages on a theatre page -- `Sali Tapio 4 ·
englanti · tekstitys suomi/ruotsi`, or `Sali Tapio 4 · English · Finnish/Swedish
subtitles` -- and the chain-prefixed cinema first on a city page, joined with ` · `, empty
parts dropped. The room is the adapter's value verbatim, so Savon Kinot's normalised
`Sali Tapio 4` shows as such and Leffabuumi's `KINOLINNA | SALI 1` keeps its pipe; the
renderer splits nothing. The cinema is the chain-prefixed label, the app's own rule,
because "Tripla" and "Kallio" name nothing on their own. Superseded the same day by "The
card is the app's card" below: language and price moved onto the card when every
screening shares them, and the city stubs stack the way the app's combined view does.

**The language codes become words, and that is the one client rule ported.** `FI-S, SV-S`
is the pipeline's storage format and the first version printed it; a reader has no reason
to know it. `lang_parts()` is the app's `langTxt`: `-A` is the spoken language, `-S` a
subtitle language, a compound `FI-SV-A` is two, duplicates collapse in source order, an
absent role is omitted, and a code no table knows stays visible as itself. The name
tables are the client's `LN.fi` and `LN.en` copied, and a test reads the client's out of
`index.html` and asserts equality, so they cannot drift apart quietly. The subtitle word is
the page's own -- "tekstitys" and "… subtitles" rather than the app's abbreviated
"tekstit" and "subs" -- because a landing page has the room a stub does not.

**Four codes in the committed data are not in the client's table, and each is a defect
somewhere else.** Measured on 2026-09-02 across every area file: `TU` (62) and `MA` (3)
are Finnkino's own vocabulary for Turkish and Malayalam ("Keltaiset kirjeet", "I'm
Game") -- `fetch_data.lang_tag` maps `SE` to `SV` and should map these too; `XX` (46) is
Nexxo's "no subtitles" on dubbed films, not a language, which `nexxo._lang` should drop;
`LT` (1) is Lithuanian, a real code missing from the client's `LN` ("Svečias"). The app
shows all four raw today. So that no page does, the generator carries `CODE_ALIAS`
(TU → TR, MA → ML), `NO_SUBTITLES` (XX) and `LN_EXTRA` (LT, ML), each named in a test so
adding one is a decision rather than a drift, and a test asserts every code in the
committed data resolves. **Follow-ups, not done here:** the two adapter mappings, `LT`
and `ML` in the client's `LN`, and then the removal of these extras once the data has
turned over. Promoted to a Pipeline backlog item and the code half done on 2026-09-02;
see "Language codes normalised end to end". Deliberately **not** ported: the app's `stubTags`, `priceLabel` and the
metadata fold -- each a second implementation of a client rule with its own drift, for a
page whose job is to hand the reader to the app.

**Wrapping is decided per part.** The cinema and the language phrases may break at their
spaces and, through a `<wbr>` after each slash, between joined names -- Chrome does not
break after a solidus on its own, and "suomi/ruotsi/englanti/ranska" on Kino Engel's
six-language screening clipped a 206 px column until it could. The room stays on one
line. The showtime grid's column floor is `min(260px, 100%)`: 260 px so a desktop page
runs two columns of the longer word labels rather than three of clipped ones, capped at
the container so a 320 px phone gets one full-width column instead of a horizontal
scroll -- a bare `260px` floor did exactly that and was caught by the overflow
measurement. An earlier version kept the raw code string on one line and clipped the same
Engel screening in a 223 px column; measured, then fixed, then superseded by the words.

**FI · SV · EN.** The header carries the app's own three-way selector: the page's language
is a plain span marked `aria-current="page"`, the other static language links to its
page with `hreflang`, and Swedish -- which has no static page -- opens the app on this
area in Swedish through the same `?area=…&lang=sv` the CTA relies on, since `startupLang`
already accepts `sv`. Each segment is a 44 px target. No Swedish `hreflang` in `<head>`,
because there is no Swedish canonical to point at. **Swedish landing pages** (84 more
files, a third `hreflang`, a `/sv/` tree) are a possible SEO expansion on their own terms
and are not part of this; the selector only stops Swedish readers being the one audience
the landing pages left out.

**The intro promises what the booking mode offers.** The old copy told every reader the
time opened a ticket page, which was false for Kino Akseli (no links at all) and for the
Nexxo cinemas (the programme page). `venue_intro(t, book, host)` reads the registry's
`book` field: `Katso lähipäivien näytösajat. Kellonajasta pääset lipunmyyntiin sivustolla
savonkinot.fi.`, `...paikkavaraukseen sivustolla...`, `...teatterin ohjelmistoon
sivustolla...`, `Liput myydään ovelta.`, with English equivalents. A city mixes modes, so
its intro says `kun linkki on saatavilla` / `where available`. The venue name is never
inflected: the example tone "Savon Kinot Tapion" works for Tapio and breaks for Itis, so
the venue appears only in nominative positions, the same rule cities already follow.

**The synopsis is clamped, not cut.** Three lines below 560 px by `-webkit-line-clamp`,
the full text in the markup, so the crawler and the reader hold the same document.
Measured on Tapio at 402 px: 19 of 19 synopses clamped to 61 px with their 200
characters intact in the DOM; unclamped at 1200.

**Measured on the generated pages, served from this tree, in the preview browser's
device and colour-scheme emulation** (Helsinki city page unless noted):

| width | horizontal overflow | clipped label parts | stub height | CTA height | poster |
|---|---|---|---|---|---|
| 320 | none | 0 | 44 to 88.9 (the six-language Engel stub) | 48 | 72×104 |
| 360 | none | 0 | 44 to 58.9 | 48 | |
| 375 (city, and Tapio fi/en) | none | 0 | 44 to 58.9 / 44 | 48 | |
| 402 (city fi, theatre fi) | none | 0 | 44 to 58.9 / 44 | 48 | 72×104 |
| 402, dark (city en) | none | 0 | 44 to 58.9 | 48 | body #0D0E12, current segment #EDEDEA |
| 1200 (city, theatre) | none | 0 | 44, two columns of 338 | 48 × 402 | 92×132 |

Every selector segment 44 × 44, venue chips 44, Archivo confirmed loaded,
`a:focus-visible` is the app's 2 px accent ring, no raw `-A`/`-S` code in any details
cell, the Mikkeli page keeps `KINOLINNA | SALI 1` whole at 320 px, and the label reads
`Sali Tapio 4 · tekstitys suomi/ruotsi` on Tapio and `Finnkino Tennispalatsi · Sali 10 ·
englanti · tekstitys suomi/ruotsi` on Helsinki.
Screenshots were rendered by headless Chrome from copies of the generated pages with one
theme pinned, because that Chrome follows the OS appearance and refuses windows under
about 500 px; the numbers above come from the emulated browser reading the untouched
pages.

**Cost.** The 172 generated files went from 5.15 MB to 8.32 MB in total, Helsinki fi
from 260 kB to 351 kB, Tapio fi from 29 kB to 48 kB (measured after the card entry below;
the ring markup and the theme scripts are the growth since the first version) -- the spans around each label part,
the language words being longer than their codes, and the inline CSS. `write_if_changed` holds: a second run writes
0 files, and the drift check in `Checks` stays green.

**Two refinements recorded and not built**, as backlog items above: the screening list
spanning the full film width on narrow phones, with a two-level label; and a link
affordance for the city page's cinema names.

**Tests: one file, `tests/test_landing_pages.py`**, 28 tests. Most run the real `main()`
into a temporary tree from the committed data and read what came out: 84 canonical pages
per language, 4 redirects byte-identical to the committed ones, sitemap equal to the
canonical set, every canonical self-referencing with its hreflang pair, one CTA per page in
the page's language carrying the page's own venue or city and the parameter names
`index.html` reads, every theatre page free of its own name in its stubs while each room
in the window appears verbatim, every city stub naming a known cinema, no leading,
trailing or doubled separator and no empty span inside any stub, every venue intro equal
to its registry mode's sentence, the city intro generic, a second run writing nothing,
no `generated` or `oldest` stamp in any page, no script after `</head>`, no raw `-A`/`-S`
code left in any stub, every code in the committed data resolving to a name, the
generator's name tables equal to the client's `LN.fi` and `LN.en` read out of
`index.html`, and the FI · SV · EN selector on every page with the right segment current
and the right two links. Synthetic shows pin the shape itself: theatre, city, empty room,
time alone, Leffabuumi's pipe, the clock and link, the language rule case by case, and the
page being identical under a shuffled input order.
`test_build_pages_atomic` (9) and `test_legacy_slugs` are unchanged and green; the
`test_ld_json` call to `page()` took the new keyword set.

Verified by breaking the generator thirteen ways, each restored byte-identically with
`__pycache__` cleared between: the theatre stub repeating the venue (6 red), the city stub
dropping it (20), empty parts kept (82), a pipe split in the renderer (2), the CTA language
hard-coded to Finnish (84), the CTA label unlocalised (84), the CTA losing the venue (149),
the intro ignoring the booking mode (1), a build timestamp in the page (1), shows no
longer sorted (1), the canonical always the Finnish page (84), the redirect page gaining
the CTA (4). Then, for the words and the selector, thirteen more: codes rendered raw
(161), duplicates kept (1), the subtitle role dropped (11), XX read as a language (3),
the Finnkino aliases dropped (3), one Finnish name differing from the client's (5), an
unknown code silently dropped (1), the current language rendered as a link (168), no
`aria-current` (168), the SV link losing the area (168), the SV link gaining `hreflang`
(168), a Swedish `hreflang` in `<head>` (168), and the selector in the order EN SV FI
(168). All red.

### The landing pages follow the app's theme (2026-09-02)
The redesign shipped with the theme chosen by `prefers-color-scheme` alone, on the
reasoning that the pages carry no JavaScript and the app's toggle lives in
`localStorage`. Reproduced the same day on the live site: `kino-theme` set to light in the
app, OS dark, open `/kaupunki/helsinki/` -- dark, on the same origin, beside an app the
reader had just set light. That is not a stylistic preference, it is two pages
disagreeing about a choice the reader made, so the "no JavaScript" line gives way to "no
JavaScript that renders content".

Two constants in `build_pages.py`, both the app's own behaviour rather than a new one:

- **`THEME_HEAD_JS`, in `<head>` before the stylesheet**, reads `kino-theme` inside the
  same try/catch the app's `store` uses, applies a stored `dark` or `light`, and otherwise
  asks `matchMedia` -- the app's `applyTheme(store.k || matchMedia(...))` in one
  expression. It sets `data-theme` on `<html>` before first paint, so there is no flash.
  One narrowing: a stored value the app never writes is treated as absent rather than
  applied, since an attribute value is a CSS selector here.
- **`THEME_BODY_JS`, at the end of `<body>`**, is the app's toggle handler: flip the
  attribute, write the same key, and repaint `theme-color` from the applied `--bg` so a
  translucent status bar draws its clock in the right colour. The no-script page carries
  one `theme-color` per scheme; the script rewrites both.

The stylesheet holds the dark tokens twice, once under `:root[data-theme=dark]` and once
under `@media (prefers-color-scheme: dark)` for `:root:not([data-theme=light])`, so a
stored choice wins in both directions and a page with no script still follows the OS.
`html:not([data-theme]) #themeToggle{display:none}` hides the button when the script did
not run: a control that cannot act is worse than none.

The toggle is the app's 44 px circle -- 44 rather than the app's 38, the touch floor the
rest of the page keeps -- and the header's vertical padding dropped from 12 to 8 px so the
bar stays about the app's height. Measured at 320 px with the logo, the three 44 px
selector segments and the toggle in one row: wordmark 92 px, segments 120 to 254, toggle
262 to 306, which is the content edge exactly, bar 63 px, no overflow -- after the
wordmark dropped to .6rem below 360 px, because at .66rem the row measured 297 px in 292
and the toggle sat 5 px into the margin. The segments and the toggle are floors; the
wordmark is the one thing in that row allowed to give.

Tests read every generated page: the head script present, before `<style>`, reading the
key with the two-value guard; both token blocks and the hidden-without-script rule in the
stylesheet; the toggle with its localised accessible name; the body script writing the
same key; no script on any page containing `innerHTML`, `document.write`,
`createElement`, `appendChild`, `fetch(` or `textContent`; and both scripts passing
`node --check`, the same check the app's inline block gets. Verified by breaking it ten
ways, each red: the head script dropped (168), moved after the stylesheet (168), applying
any stored value (168), not reading the key (168), the toggle not persisting (336), dark
tokens only from the OS (168), the toggle shown without the script (168), its name
unlocalised (168), a script writing `innerHTML` (168), and a syntax error in the head
script (1). Checked live on the served pages, OS dark throughout: nothing stored opens
dark; stored light opens light with both `theme-color` metas at `#F6F7F9`; the landing
toggle turns the page dark and stores `dark`; the app then opens dark; the app's toggle
back to light carries to the city page.

### The card is the app's card (2026-09-02)
Compared side by side at 402 px after the redesign shipped, the landing page and the app
shared their materials -- typeface, sizes, tokens, chip shapes, poster -- and assembled
them differently: a text star for the score ring, language words on every stub where the
app folds them onto the card, side-by-side stubs where the combined view stacks them,
tighter card padding. The app is the blueprint, so the differences that were choices went.

- **Film facts fold first-non-empty across the day's screenings** (`first()`), the app's
  own rule: rating, runtime, genres, score, votes, poster. Never the first screening
  alone -- a chain that publishes no rating must not blank the card when another did.
- **Language and price sit on the card once when every screening shares them**, and on
  the screening when they differ. `lang_parts` was already the app's `langTxt`;
  `price_label` is now its `priceLabel`, and the test runs the client's own harness cases
  (`tests/price_label_harness.js`) through both and asserts the same answers, so the port
  cannot drift. Differing prices give the card the app's "alkaen 10€" floor and each
  screening its own amount; differing languages give the card nothing it cannot say for
  all of them. The eighteen-fold "englanti · tekstitys suomi/ruotsi" under one film is
  gone.
- **The score is the app's ring**, the same markup and CSS, with `role="img"` and the
  label "TMDB 7.1/10 · 41 ääntä" so it reads as one thing; `thin` under 25 votes as in
  the app. No `aggregateRating` in the JSON-LD, as before.
- **Stubs follow the view they are in.** The app's single-venue view is a row of ticket
  stubs, its combined view a grid of stacked ones (`.stubs.grid`, 168 px columns, 140
  below 520). A theatre page is the first, a city page the second, with the app's own
  paddings and the perforation dropped on the stacked form as the app drops it. The 44 px
  floor stays on both.
- **Card spacing is the app's**: 20 px between films, 18 px poster gap, meta rows at 7 and
  5 px, meta2 as the app's wrapped spans in its order -- genres, runtime, language,
  price.

One more thing the comparison found and fixed here: the page sets `line-height: 1.5` on
`body` and the app does not, so a stacked stub measured 54 px against the app's 46. The
stub's time and place lines are 1.2 now.

Measured on the generated pages after the change, no horizontal overflow and no clipped
label part at any width:

| width | page | stubs | columns | notes |
|---|---|---|---|---|
| 320 | Helsinki | 48.5 to 76.1 stacked, 202 wide | 1 | header 63, segments 44, toggle 44 |
| 402 | Helsinki | 48.5 to 62.3 stacked, 284 wide | 1 | the app shows one per row here too |
| 402 | Tapio | 44, row stubs 147 wide | wrap | `16:00 │ Sali Tapio 4` |
| 1200 | Helsinki | 48.5 to 62.3 stacked, 222 wide | 3 | poster 92×132 |
| 1200 | Tapio | 44, 147 wide | wrap | |

The card change made the Helsinki page taller, 40 190 px at 402 against 33 251 before
it: a stacked stub is one per row where the old row stub was one per row as well but
shorter. That is the app's own trade in its combined view, and the page-length problem is
the open backlog item about the city page, not this one. Tapio at 402 is 8 657 px.

Not ported, still: the app's `stubTags` fold for format tags (IMAX, Anniskelu), the
premiere chip, glyphs and the age chip. Those are the next step if the card is to be the
app's to the last detail; each is small and each is a further client rule to keep in step.

Verified by breaking it ten ways, each red: film facts from the first screening (1),
language always on the card from the first screening (2), a differing price dropped from
the screening (1), the price floor word ignored (5), the price prefix hard-coded Finnish
(3), the ring without its label (2), `thin` never applied (1), city stubs not stacked
(21), theatre stubs stacked too (141), and the sign dropped from the price number, which
the client's own harness cases catch (1).

### The venue picker is searchable (2026-08-31)
The native `<select>` was free platform UI, but at 70 venues finding one meant reading
a long grouped list, and a native select has nowhere to hang a search field. The
trigger keeps the select's face and its place in the controls row; tapping it opens a
dialog on the same modal lifecycle as the movie sheet and the month picker
(`BEHIND()`/inert, Escape, backdrop, focus restore).

- **The keyboard never opens uninvited.** The classic combobox failure on mobile is
  that tapping the control focuses an input, the on-screen keyboard erupts and covers
  the list the person came to read. Here the sheet opens full-screen with focus on the
  close button; the keyboard appears only when the search field itself is tapped, and
  the field is pinned to the top so the keyboard covers venues, never the field or the
  first results. On a fine pointer the field is focused immediately -- a physical
  keyboard covers nothing.
- **Search folds diacritics both ways** ("jarvela" finds Järvelä; NFD-strip keeps the
  match offsets aligned with the NFC original, so the `<mark>` highlight lands right),
  matches label and city, hides emptied city groups and keeps the combined
  "Kaikki {city} (n)" rows findable by their own text. Esc clears the query first and
  closes second.
- **Selection is the old code path** -- `state.area`, `prefs`, `syncFav`,
  `loadSchedule` -- so the saved venue, the star, `?area=` deep links and the
  city-combined ids behave exactly as before. `buildAreaOptions()` still computes
  `cityGroups`, it just stops writing `<optgroup>` markup.
- The rows carry the existing `chain-{id}` classes, so the dot colour comes from the
  same generated `--chain` variables the stubs and the legend already use.
- Costs accepted: the select's free type-ahead is replaced by the search field, and
  the Chromium `::picker(select)` theming block went with the element.
- Verified live against the served page, desktop and mobile emulation both: trigger
  face unchanged, autofocus only on fine pointers, full-screen top-anchored sheet on
  mobile, inert background, focus restore, two-stage Esc, diacritic search, combined
  row pick, star pinning, sv/en label redraws, `?area=` restore, clean console.

**Reviewed (2026-08-31), three row-model faults fixed, and the model is tested now.**
The first version showed the combined "Kaikki {city}" row whenever *any* venue in the
city matched, sorted above the matches -- and Enter picks the first row, so searching
"itis" and pressing Enter selected Kaikki Helsinki instead of Finnkino Itis, on the
exact path desktop autofocus invites. The combined row now appears only when nothing is
searched or the query matches the row's own text or its city. Two more from the same
review: a saved `city:*` favourite (valid everywhere else) never showed under "Oma
teatteri", which only looked venues up in `venueIndex`; and in Swedish a Turku venue was
findable as "Åbo" but not as "Turku", because the haystack held only the display name.
The venue haystack now carries both city names, and the pinned section renders combined
favourites.

All three were invisible to a manual pass that types a city name, which is the argument
for the change that carries the fixes: the row list is decided in `venueRows()`, a pure
function extracted verbatim by `tests/venue_picker_harness.js` the way `healthState`
already was, with the row *order* asserted because Enter makes order behavior. Verified
by breaking each fix -- the combined-row rule, the `city:` branch, the raw-city alias
and the fold each turn their test red. Focus, inert, Escape and keyboard plumbing stay
live-verified; they are DOM behavior, not model decisions.

### A newline hid the scheme from `safeUrl` (2026-09-01)
`safeUrl` read the scheme off the raw string with `^([a-z][a-z0-9+.-]*):`. A URL parser
does not read it that way. It deletes ASCII tab, LF and CR from anywhere in the URL and
strips the control characters off both ends *before* it looks for a scheme, so the string
the function tested and the URL the browser built out of it were not the same string.

`java<LF>script:alert(1)` matched nothing -- the character class stops at the LF, so the
match fails -- and a failed match was read as "no scheme, therefore relative, therefore
fine". The value went into the href, the browser removed the LF, and the link was
`javascript:`. Reproduced against the function on its own, resolved through a real URL
parser:

    javascript:alert(1)        rejected
    java<LF>script:alert(1)    ACCEPTED  -> javascript:
    java<CR>script:alert(1)    ACCEPTED  -> javascript:
    java<TAB>script:alert(1)   ACCEPTED  -> javascript:
    <NUL>javascript:alert(1)   ACCEPTED  -> javascript:

The fourth was not in the report and turned up while reproducing the first three: `trim()`
removes whitespace, NUL is not whitespace, and a parser strips it anyway. Every one of
these reaches an href built from provider JSON -- the three showtime stubs and the
trailer link -- which is nine third-party sites' text.

**Rejected on any control character rather than cleaned.** Cleaning would mean stripping
exactly what the parser strips, and the whole defect is that this code was wrong about
what the parser strips; the second version would have had to be right about the same
thing. Rejecting needs only the weaker claim that a URL with a control character in it is
not one a cinema published. It costs nothing real either: `trim()` still runs first, so
the trailing newline an adapter leaves on a scraped href is gone before the check sees
it, and that case is pinned by a test.

`safeAssetUrl` did not have the hole -- a control character cannot walk a path out of the
`data/posters/` allowlist, because removing characters cannot change a prefix that has
none -- but it shares the guard. Two sinks that disagree about what a URL is are how the
next one of these opens.

Both are now sliced verbatim out of `index.html` by `tests/safe_url_harness.js`, the way
`healthState` and `venueRows` already were. The harness does one thing those two do not:
every accepted result is resolved through node's WHATWG URL parser and the protocol it
lands on is asserted. A test that only re-read the function's own regex would have passed
against the broken version, because the regex was self-consistent -- it was the
disagreement with the parser that was the bug.

Verified by breaking it, five ways: the guard removed from `safeUrl` (7 red), from
`safeAssetUrl` (1), from both (8), the marker comment deleted so the harness slices
nothing (2 errors, loudly), and -- the one worth having -- the guard narrowed to LF and
CR only, which looks right and lets the tab and NUL payloads back in (4 red).

### Poster URLs are checked against the origin and path (2026-08-30)
`safeUrl` answered two different questions with one rule. A ticket or trailer URL is
*meant* to leave this origin, so http(s) and relative are all correct for it. A poster is
not: an `<img>` is a request the browser makes on its own, and the README's claim that a
page load makes no third-party requests rests on every poster being local. The same
function was clearing `https://third-party/x.jpg` for both roles.

`safeAssetUrl` is a path allowlist -- same origin *and* inside `data/posters/` -- rather
than an origin check, and the reason is `mirror_posters.py`: when a download fails it
logs and leaves the hot-linked URL in the data on purpose, so that a third party's uptime
cannot stop the pipeline publishing showtimes. That makes the privacy invariant something
the client has to hold on its own rather than something it inherits from the pipeline
having behaved.

Measured before writing the rule: **every poster reference in the committed data is
`data/posters/`** -- 3059 on shows and 98 in `films-extra.json`, 2026-08-30 -- so the
allowlist costs nothing today and catches the day one is not.

Tested by injecting three hostile forms into a venue file and loading it:
`https://third-party.example/...`, the protocol-relative `//third-party.example/...`, and
a padded uppercase `  HTTPS://Third-Party.example/...`. All three fell back to the
placeholder tile, and the page rendered **zero off-origin images** against 21 local ones.
This was latent rather than live -- there is no remote poster in the data today -- which
is exactly why it needed a test rather than an inspection.

### A refused request held its socket until the collector noticed (2026-09-01)
A suite run printed 24 ResourceWarnings and they were read as test noise for as long as
they have been there. Thirteen of them were not: `urllib.error.HTTPError` *is* the
response object, and `common.fetch` kept the last one in `last` across the retry loop and
raised it, so every refusal left a socket open until the garbage collector happened to
run. On a run against a host refusing everything -- `mirror_posters` has had 185 failures
against one host in a single run -- that is 185 sockets waiting on a collection nobody
scheduled.

`e.close()` on entering the handler. Nothing ever wanted the body: `code`, `reason` and
`headers` all survive the close, `_log_refusal` and `_server_hint` read only headers, no
caller anywhere calls `.read()` on a caught error, and `raise last` hands the caller an
exception rather than a stream. `close()` is idempotent, so the paths that re-raise the
same object cost nothing.

The other eleven were the fixtures: `shutdown()` stops `serve_forever` and leaves the
listening socket open, and two of the three local servers never called `server_close()`.
`test_run_pool.py` always did, which is what made it findable.

**`-W error::ResourceWarning` does not enforce this**, which is worth writing down
because it is the obvious thing to reach for. The socket warnings are raised while the
interpreter is shutting down, after the test run has already reported its result, so the
exception the flag raises has nothing left to change: measured 2026-09-01, exit 0 with
the leak reintroduced and the warning printed. `Checks` greps the captured suite output
instead, which catches both classes -- unittest enables warnings by default, so they are
in the log with no flag at all.

Verified by breaking both: `e.close()` removed turns four new tests in
`test_common_fetch.py` red, and `server_close()` removed puts the unclosed-socket line
back in the output the workflow reads. The four tests state the symptom as well as the
mechanism -- one asserts the raised error is closed, one that the diagnostic headers
survived it, and one records warnings around a three-attempt failure and forces a
collection, because `closed` is only evidence for the thing that was actually wrong.

### Checks needs the whole history, not the tip (2026-09-01)
The first run of the workflow failed on four tests in `test_indexnow.py`, and none of them
were wrong. `actions/checkout` fetches a single commit unless told otherwise, and those
four ask git questions a one-commit repository cannot answer: `RealHistoryTest` diffs two
named commits against their parents -- deliberately, so its fixtures cannot drift from
what git actually recorded -- and two `PushRangeTest` cases assert the fallback to
`HEAD^`, which does not resolve when HEAD is the only commit there is.

Reproduced exactly by cloning this repo at `--depth 1` and running the suite in the clone:
the same two errors and two failures, in the same four tests. At full depth, green with no
skips and no warnings.

`fetch-depth: 0`. The tests are right to read real history, so the checkout has to carry
it. The cost was measured rather than assumed: a full clone is 22 MB against 15 MB
shallow, because the mirrored posters dominate both and the extra 727 commits of history
are almost free next to them.

Worth keeping in mind for anything else added to this workflow: a runner's checkout is not
the working copy this suite grew up in, and the depth is only the first way that shows.

### A failing check has to say what failed (2026-09-01)
The first `Checks` run went red and left nothing to read. The only annotation on it was
"Process completed with exit code 1": the two gates emit `::error::` lines, but a plain
test failure emitted none, and `set -o pipefail` ended the step at the `unittest` call
before either gate ran.

The Actions log answers 403 without a token, and this repo does not read Actions logs
anyway. Check-run **annotations** are a different thing and are readable over the public
API with no credential at all -- `/repos/{owner}/{repo}/check-runs/{id}/annotations` --
which is what made "exit code 1" visible from outside in the first place. So the step now
captures the suite's exit code instead of dying on it, emits one `::error::` per `FAIL:`
or `ERROR:` line, and writes the summary lines to `$GITHUB_STEP_SUMMARY` as well.

One trap in writing this, worth keeping: the first version emitted the annotations with
`grep ... | while read`. grep exits 1 when it matches nothing, which is the *normal* case
-- a green suite -- and `shell: bash` runs with pipefail, so the pipeline would carry
grep's status and `-e` would end the step. A passing suite reporting failure, from the
step added to make failures legible. Measured both ways against a synthetic log: `bash -e`
exits 0, `bash -e -o pipefail` exits 1. The step gets the plain default today, so it was
one `shell:` key away rather than already broken -- and the step it replaced set pipefail
itself. `awk` exits 0 whether or not it matched, so neither shell matters.

The failure was found by reproducing the runner's checkout locally rather than by reading
anything, which worked and took four wrong guesses to reach. Pillow, flakiness, Python
3.13, TZ=UTC and LC_ALL=C were all eliminated first, each of them green. That is the cost
this change is meant to remove.

### The suite is a workflow rather than an instruction (2026-09-01)
Three workflows existed and none of them ran a test. They fetch data, read committed run
logs and ping IndexNow -- all about what the pipeline *did*, none about whether the code
that did it still parses. Every check that mattered was written down in CLAUDE.md as an
instruction to a person, which holds until the day somebody is in a hurry.

The client is the worst case. There is no build step, so nothing parses `index.html`'s
script block before a browser does: a syntax error ships, the page renders blank, and the
service worker keeps serving the last good copy to everyone who already has it -- so the
person who pushed it sees a working site and the people who did not have it see nothing.

`Checks` runs four things on any push touching `index.html`, `sw.js`, `scripts/**` or
`tests/**`.

**The JavaScript parses.** `scripts/check_inline_js.py` is the CLAUDE.md instruction made
runnable: it pulls the inline block out of the HTML, `node --check`s it and `sw.js`, and
parses any `application/ld+json` as JSON rather than handing it to node, which would
reject a perfectly good one. Node reports line numbers against the fragment it is given,
so the fragment is padded to its offset in the file first -- the number printed is the
line to open. A page with no inline script is a failure, not a no-op: zero blocks in a
page that has one means the tag shape moved and the check has been passing on air.

**Regeneration produces no diff.** The generators are pure functions of committed data
and their output is committed too, so `build_providers.py` and `build_pages.py` in a clean
checkout must change nothing. This is the rule about keeping volatile things out of
generated pages, enforced instead of remembered -- a build timestamp would turn it red
every run. Two different failures land here and they are worth telling apart: a generator
changed without its output regenerated is the author's to fix, while committed data whose
pages were never rebuilt means the live site is serving markup that disagrees with its own
JSON.

**A skipped test fails the run.** Five poster tests skip locally because Pillow is not on
the system interpreter. On a runner every dependency is installed on purpose, so a skip
there means one went missing and coverage shrank with nothing saying so -- and the four
harnesses that need node are the only tests that touch `index.html` at all, so they are
exactly the ones that could vanish unnoticed. Pillow is pinned to `12.3.0`, the same
version and for the same reason as the mirror step.

**`check_runs.py` is deliberately not in it.** `logs.yml` already runs it, on pushes that
touch a run log or the checker, which is the trigger matching what it reads. Running it on
a code change would turn this red for a provider outage that has nothing to do with the
diff.

`push` and not `pull_request`: this history is linear and direct-pushed, a branch is
pushed before any PR exists on it, and a doubled trigger would run everything twice. A
fork would need its own trigger and there has never been one.

The path filter is what keeps this off the data commits. The cloud half pushes with
GITHUB_TOKEN, which does not fire `on: push` at all, but the local half's four pushes a
day do.

Verified here as far as this machine can: the workflow parses, `check_inline_js.py`
passes against the real client and has eleven tests of its own including the line-offset
mapping and a two-block fixture, and regeneration in this tree produced zero drift. The
skip gate was run and fires correctly here, where the five Pillow skips are real. **Not
verified: that the five poster tests pass on a runner with `pillow==12.3.0`** -- they have
never been run anywhere but a laptop without Pillow, so the first Checks run is where
that gets answered.

### The workflow's dependencies are pinned (2026-08-30)
`actions/checkout@v4`, `actions/cache@v4` and a bare `pip install pillow`, in a job that
holds `contents: write` on this repo and pushes to `main`.

A floating major tag is a promise from someone else that no future v4.x will do something
new with that token, and re-pointing a tag is the cheap half of a supply-chain
compromise. A SHA is the only reference that cannot be moved underneath us. The pip
install is worse in kind, not better: the runner installs it fresh every run, so the
unpinned name is whatever PyPI serves that morning.

- `actions/checkout` -> `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1)
- `actions/cache` -> `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` (v6.1.0)
- `pillow` -> `12.3.0`

**Both actions moved off their v4 pins on 2026-08-31**, because a run started warning that
`actions/checkout` and `actions/cache` "target Node.js 20 but are being forced to run on
Node.js 24". The runners still execute them, so this was a deadline rather than a
breakage, and the fix is the same work as the original pinning: resolve the tag to a
commit through the API, confirm the thing you are pinning is what you think, and write the
readable version beside it. Both v7.0.1 and v6.1.0 declare `using: node24` in their own
`action.yml`, checked at the resolved SHA rather than assumed from the version number.

A major-version jump is where a pin stops being a formality, so the inputs were checked
before the bump rather than after the next run: `checkout` is used with no inputs at all
here, and `cache` v6.1.0 still accepts `path`, `key` and `restore-keys`. `.github/
workflows/logs.yml` carries the same `checkout` pin and moved with it.

The claim above about verifying with PyYAML did not hold this time: no interpreter on this
machine has it, including the wrapper's venv. Rather than skip the check or claim one that
did not happen, the edited lines were verified structurally -- indentation and list
position of each `uses:`, no tabs, and every `uses:` a 40-character SHA rather than a
tag. That is weaker than a parse and is worth saying so: the first real run is what
proves the file.

Resolved from the GitHub and PyPI APIs on 2026-08-30, not copied from anywhere. The
readable version stays in a comment beside each, because a bare SHA tells you nothing
about how far behind it has drifted, and a pin nobody can read is a pin nobody will
update. Permissions were not touched; the job already had the narrowest set it can run
with.

Verified by parsing the file with PyYAML rather than by reading it -- a workflow that
fails to parse takes the whole cloud half down, and the failure would look like a cron
that simply did not fire.

### The third quick filter is Anniskelu, and it excludes Lapsille (2026-08-30)
Chips are for the two or three intents worth permanent horizontal space. Measured across
3059 showtimes before choosing:

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

Anniskelu lands in the same band as both existing chips and names a proposition people
actively choose. Everything from IMAX down is search material, not chip material, so the
haystack gained `method`, `rating` and `age` in the same pass. That makes the whole tail
findable at no cost in horizontal space: IMAX, LUXE, iSense, Prime, Plus, Senioribio,
Perheleffa, Espoo Ciné, K-18, and **Kuvaileva tekstitys**, which is the case that settles
the argument -- 10 showtimes, so it can never justify a chip, and until now the readers
who need descriptive subtitles had no way to find it at all. `k18` and `k-18` both match,
since `searchKey` already collapses punctuation.

**The two exclude each other**, and once both read their own rule the overlap is
**exactly 0** -- so the exclusion is a guard against a confusing empty state rather than
the thing doing the work. Clicking either clears the other; on restore, Lapsille wins a
stored pair, being the filter whose failure mode matters.

Getting to 0 needed a fix on the Lapsille side too. Its gate read the *film's* rating and
ignored `age`, the limit a cinema states for the screening, so an S-rated film in an
Annisk_K18 screening satisfied it -- five showtimes today. All five happen to be caught
by the genre rule that removes documentaries and dramas, so nothing leaked, **by luck
rather than by the rule**. The gate's own comment promises errors land on "boring for a
child" and never on "unsuitable"; it now checks `age` so that is actually true.

**The filter reads the documented rule, and the rule was already in this file.**
`fetch_data.py` maps *both* Finnkino attributes onto the one word `Anniskelu`:
`annisk_k18` is an anniskelunäytös (drinks, 18+, sets `age`) and plain `anniskelu` is an
anniskelualuesali, a permanently licensed room. The entry above, citing
finnkino.fi/leffaherkut/anniskelunaytokset/, carries the other half: **in those rooms
alcohol is not served at S/7 family films**. So the tag on a children's film marks the
room, not a bar screening.

Split by that rule, the 528 tagged showtimes are 114 `Annisk_K18`, 396 plain on
non-family ratings, and **18 plain on S/K-7 films**. The filter drops that last group, and
doing so is reading the recorded rule rather than inferring one -- the first version of
this entry called it guessing, which was wrong. The error direction matters as well:
promising a bar that will not be there is the same class of mistake as the BioRex
K-18 inference that told people a screening was closed when it was not.

11 of the 18 are BioRex, whose anniskelu semantics this file records as unsettled. The
rule is applied to them anyway, because no service at a family screening follows from
Finnish alcohol law rather than from one chain's policy, and because the safe direction
is not to promise a bar. Revisit with a citation from BioRex either way.

**Space, measured rather than estimated.** At 375 px the tools row has 347 px usable and
had 269 px used, leaving 78 px. An "Anniskelu" chip measures 78 px, so with the 6 px gap
it overflowed by exactly 6 and wrapped. Mobile chip padding went from `11px` to `9px`
horizontally, which frees 8 px per chip; all four chips and the segment now sit on one
37 px row in all three languages, with 14 / 52 / 31 px to spare in fi / sv / en.
The Swedish and English labels are "Bar", not "Utskänkning" and "Licensed bar" -- both of
those wrapped or left 3 px of margin. The glyph key keeps the fuller wording, so the
term is still taught somewhere.

### Seat counts are parsed and deliberately not published (2026-08-30)
README said the app shows "seat availability where the cinema publishes them". It does
not, and never has: what it shows is a sold-out mark.

What each source actually gives, and what becomes of it:

- **Finnkino** — an `isSoldOut` boolean from the API. No counts exist to publish.
- **eTiketti** (Kotkan Leffat, Bio Rex Kokkola) — a real count, `Vapaat paikat N / M`,
  parsed by `SEATS_RE` and then reduced to `soldOut: free == 0`.
- **Riviera** — a real count, `Varatut paikat: N / M`, reduced the same way.
- Everyone else — nothing, so `soldOut` is always false.

The counts are therefore parsed and thrown away, which reads like an oversight and is
not. **A number goes stale in a way a boolean does not.** The data is refreshed four
times a day, so a count is up to six hours old when it is read: "12 vapaata" can be zero
by the time anyone acts on it, and it would be shown with the authority of a figure.
Sold-out survives that much better -- a screening that filled up stays full, and one that
had not sold out is at worst optimistic in the same direction the reader already assumes.
Do not "restore" the counts without solving the staleness, which the refresh rate rules
out.

When reading the numbers: **6 of 3059 showtimes are sold out today**, all of them at the
three providers that publish enough to tell. The mark is real but rare, so a change to it
is easy to ship broken and hard to notice.

### AGPL-3.0, and why not MIT or GPL (2026-08-30)
Requirements were: keep the copyright, stay open to others, and make copiers credit the
original. Two of those a licence can do; the third it cannot.

**No licence on GitHub's list requires a visible credit in a running app.** MIT, Apache,
BSD and the GPLs all require the notice to survive in the source and in distributed
copies -- not to be shown to anyone using the site. A fork could run at another domain
with the notice buried in a file nobody opens and be fully compliant. The clause that
forced visible credit was BSD's 4-clause advertising clause, deprecated and not offered.
Asking in the README is the whole of what is available.

**AGPL over GPL-3.0 because this is a website.** GPL's copyleft triggers on
*distribution*, and hosting a fork distributes nothing, so a GPL fork of a deployed web
app can stay entirely closed -- which is the realistic way this project would be taken:
someone stands up their own copy at another domain rather than shipping the code. AGPL
section 13 closes exactly that. It is the only option on the list where "stays open"
survives contact with a competing deployment.

**AGPL over MIT** because MIT gives that fork away for free. The cost is real and worth
naming: AGPL deters some users and many companies ban it outright. For a hobby project
with one author that is an acceptable trade, and it would not be for a library.

Two things the file itself needed:

- `LICENSE` is gnu.org's text **byte-for-byte**, sha256 `0d96a4ff68ad6d4b...`, with the
  `<one line...>`, `<year>` and `<name of author>` placeholders left exactly as they are.
  **The first version filled them in, and that was wrong** (caught in review, fixed
  2026-08-30). The licence's own header says "changing it is not allowed", the
  how-to-apply block sits inside the document that covers, and FSF's instruction is to
  *copy* that template out onto the program rather than fill it in place. The commit
  message claimed the placeholders were "meant to be filled" and cited GitHub's picker;
  checking the API showed GitHub ships them untouched too, so the justification was wrong
  on both counts. Nothing about the project's licensing turned on it, but an edited
  licence document is ambiguity for free.
- The notice goes where GNU says instead: a comment block at the top of `index.html`,
  which is the program, and the same three lines in the README. Deliberately **not** on
  each of the fifteen pipeline scripts -- GNU asks for a copyright line and a pointer per
  file, and fifteen headers of boilerplate in a hobby repo buys less than it costs. The
  program a user actually receives carries it, and the footer names the licence and links
  the source on every page.
- The licence text is left unmodified so GitHub's detector recognises it, which is also
  why the scoping note lives in the README rather than as a preamble here. Copyright
  holder is `Shady-Dev`, the GitHub identity: this repo is public and a real name leaked
  into 18 commits once already.
- **The licence covers the code and nothing else in the tree.** A bare `LICENSE` at the
  root reads as covering everything, and three kinds of file here are not ours to
  relicense: 3059 showtimes belonging to the eleven chains, 304 mirrored posters from
  their CDNs and TMDB, and Archivo under the SIL OFL already recorded in `fonts/OFL.txt`.
  The README says so.

The footer gained a source link. Section 13 binds whoever *modifies* and deploys, so it
is not an obligation on the original -- but the clause is toothless without an example,
since a forker who never saw a source link has no idea one is expected, and the licence's
own how-to-apply text suggests precisely this for a web application. Four footer lines
now instead of three, 129 px against 110 at 375 px, one line per language.

### The branding row stops holding a third of the screen (2026-08-30)
The whole `<header>` was sticky, so the logo, language toggle and theme button stayed
pinned for the entire length of a 45-card list. Measured before touching anything, the
header was **27 to 36 per cent of the viewport** at every size tested:

| viewport | header | share | list fold | cards fully visible |
|---|---|---|---|---|
| 320x812 | 290 | 35.7% | 522 | 1 |
| 375x812 | 257 | 31.7% | 555 | 2 |
| 390x844 | 257 | 30.5% | 587 | 2 |
| 430x932 | 258 | 27.7% | 674 | 2 |
| 1280x900 | 246 | 27.3% | 654 | 2 |

The fix is one structural change and no JavaScript: the sticky moves off `<header>` and
onto a `.pinned` wrapper around the picker, search, dates and filters. The branding row
then scrolls away as ordinary content and comes back on its own when the reader returns
to the top, because it *is* ordinary content.

**No height constant anywhere**, which is the reason for this shape rather than
`top: -58px` on the header. A negative offset needs a number that matches the branding
row's height at every breakpoint, and that number silently rots the day the row changes.
The wrapper pins itself at `top:0` and needs to know nothing.

**No layout shift**, and that is measurable rather than argued: the header's flow height
is byte-identical before and after at all five widths (290/257/257/258/246), because a
plain wrapper adds no box. Nothing resizes while scrolling, so the list cannot jump.

Recovered **58 px on mobile and 66 px on desktop**, consistently 8.6 to 11.1 per cent
more list. It does not change how many cards fit *whole* at any tested size -- a card is
214 px and the gain is a quarter of one -- so the honest claim is a quarter-card more of
the next film visible, not an extra film.

**Not verified: how it feels while scrolling.** The harness browser will not scroll, by
`window.scrollTo`, `scrollIntoView`, direct `scrollTop` assignment or injected wheel
events; `scrollY` stays 0 and input injection times out. Everything above is measured
from element geometry, which is real, and the at-rest rendering is unchanged by
screenshot. The scrolled interaction needs a look on a real phone. It is one CSS rule and
one wrapper div to revert.

**The real-device checks this still needs**, since geometry cannot answer any of them:
does the branding row leave naturally rather than seeming to vanish; does the pinned
strip stay completely still; does Safari jitter or bounce it during overscroll; does
focusing search or raising the keyboard move it strangely; does returning to the top
restore the row naturally; does rotating behave. If those are clean, v70 is done.

### Two things left alone on purpose (2026-08-30)
Both are visible in the measurements above and both would look like obvious defects to
someone reading them cold. They are decisions.

**The tools row wraps to two lines at 320 px**, which is why the header is 290 px there
against 257 elsewhere, and why only one card fits whole. Left alone. Forcing five
controls onto one line at that width buys the second row back by spending something
worse: smaller tap targets, cryptic abbreviations, icons that need explaining, a
horizontally scrolling control strip, or Finnish and Swedish labels squeezed until they
stop reading. Two rows on a very narrow screen is the cheapest of those. Revisit only if
a real 320 px device feels cumbersome in the hand, not because the number is ugly.

**Theme and language are unreachable without scrolling to the top**, by design. They are
configuration rather than browsing controls: you set them once and then read a list. v70
exists to stop spending permanent screen space on a control used about once a month. **Do not add a floating theme button**, a
duplicate in the pinned strip, or any other replacement -- that reintroduces the cost
this change removed, in a smaller and harder-to-notice form.

### parseFloat only reads a leading number, so 23 of Orion's 29 prices vanished (2026-09-01, sw.js v95)
Found by writing down a claim that was not true. An entry above said the client half of
the price feature was finished; checking that before it was pushed turned up a live bug
instead.

`priceLabel()` read every price with `parseFloat(String(r.price).replace(',', '.'))`.
parseFloat takes a number at the *start* of a string and stops caring after that, so a
provider that publishes its own floor gets nothing: Cinema Orion writes **"alkaen 10€"**,
which is NaN, which the next line filtered out as unpriced. Counted against the committed
data:

| Orion price string | rows | rendered before |
|---|---:|---|
| `alkaen 10€` | 22 | nothing |
| `alkaen 12€` | 1 | nothing |
| `10€` | 5 | `10€` |
| `8.5€` | 1 | `8.50€` |

**23 of 29.** No other provider was affected -- all 1014 of their price strings begin with
the number -- which is why the cinema with the most interesting pricing was the one
showing none of it.

**Two questions had been collapsed into one.** What the cheapest price is, and whether to
introduce it as a floor. The old code answered the second only with "this list holds two
different amounts", which cannot see a source that has already said so itself. Now:

- *The number* is the first one anywhere in the string. Safe today and checked rather
  than assumed: no price string in the committed data carries a second number, across
  all 1043 of them.
- *The floor* is either two different amounts in the list, or anything left in the source
  string once the number, the currency and the spacing are removed. Tested on shape
  rather than on the word, because the word is in the provider's language and there are
  three of those. `13 €` and `13&nbsp;€` stay exact; `alkaen 10€` does not.
- *The prefix* comes from `L[state.lang].from`, so it reads alkaen, från or from.

The sign stays inside the match, and that is not decoration. Pulling the number out of the
middle of the string without it made `-5€` match as `5` and sail past the `v > 0` guard
the old code had been relying on -- a rejected price turned into an accepted one. A test
caught it; reading the diff had not.

Verified live at 402px against Orion's own data: `alkaen 10€` renders where it used to
render nothing, beside the exact `10€`. Eighteen tests through
`tests/price_label_harness.js`, extracted verbatim the way `healthState` and `venueRows`
are, with the three `from` translations read out of `index.html` rather than retyped so
the localisation is checked against what ships. One of them asserts the three are actually
different, because a harness that returned the same string three times would pass every
localisation test in the file.

The 23-of-29 count above is a dated measurement, not an invariant. Nothing asserts it:
a test that read the committed data would tie `priceLabel()`'s correctness to what Cinema
Orion happens to publish today, so an unrelated code push would go red the week they
switch to plain numbers. The synthetic cases carry the regression on their own.

Verified by breaking it seven ways: parseFloat over the whole string again (1 error), the
floor marker never set (4 red), the floor marker set by any trailing character so every
`13 €` gains a prefix (6), the sign dropped from the match (1), the floor computed and
then ignored (4), the prefix hard-coded to Finnish (2), the zero-and-negative guard
removed (1).

### Listing data leaves four fifths of showtimes unpriced (2026-09-01)
The committed data establishes the size of the gap, not what lies beyond it. Of 5,079
showtimes, **1,043 carry a price on the listing we read and 4,030 do not.** Obtaining
prices for the remainder would require another legitimate public source or crossing into
the booking flow, which was not probed.

| | |
|---|---:|
| showtimes with a price on the listing we read | **1,043 of 5,079** |
| showtimes without | 4,030 |
| providers publishing at least one listing price | 27 of 32 |
| unpriced showtimes contributed by Finnkino | 2,333 |
| unpriced showtimes contributed by BioRex | 1,364 |

The provider count flatters it, and that is the correction worth keeping: 27 of 32 sounds
like near-coverage and is not, because the two largest chains are among the five that
publish nothing. A count of *providers* was the wrong denominator and had been quoted that
way in conversation; showtimes are the honest one.

An earlier draft of this entry went further and said cinemas do publish prices on the page
the "buy tickets" button opens. That was not measured. Booking pages were deliberately not
inspected, so nothing here can say what is or is not on them, and the claim is removed
rather than softened.

**The booking flow stays out of bounds and unprobed.** The rule is not conditional:
"booking, payment and administrative endpoints are never called and are not inventoried".
This app links visitors to those pages -- every showtime stub does, by design -- which is
a different act from fetching them on a schedule. A second reason stands on its own even
where the first did not apply: prices per showtime rather than per listing would mean
roughly 4,000 extra fetches at the current cadence, mostly against the small ticketing
platforms these cinemas share, and reading one listing per site is what this project's
traffic claims are built on.

What remains is the gap as measured and one avenue that has not been looked at: a
visitor-facing price page, where a cinema publishes one, is ordinary content and *could*
give per-ticket-type pricing rather than per-showtime. Whether any cinema has one, and
what it would contain, is unknown here.

### Finnkino publishes no prices outside the booking flow (2026-09-01)
Two backlog entries wanted this -- "prices alkaen" under App and "Finnkino prices via the
ticket-types endpoint" under Pipeline -- and they were the same endpoint counted twice.
What was missing was a source for the largest chain.

An earlier draft of this entry said the client half was already done, and that the price
cell carried the ticket-type breakdown in a `title`. Both were wrong, and writing them
down is what found a live bug -- see "[parseFloat only reads a leading
number](#parsefloat-only-reads-a-leading-number-so-23-of-orions-29-prices-vanished-2026-09-01)".
The `title` claim came from misreading an entry about *Cinema Orion's own page markup*,
which is where that tooltip lives; this app renders the price as a bare `<span>`.

There is not one, on the public API.

**The programme response carries no prices.** This is the request the adapter already
makes every run, so reading it again cost nothing new. A showtime object is
`areaCategories, attributeIds, eventId, filmAdvanceBookingRuleId, filmId, id,
isAllocatedSeating, isSoldOut, requires3dGlasses, restrictions, schedule, screenId,
seatLayoutId, siteId`, and its `schedule` is `businessDate, endsAt, filmEndsAt,
filmStartsAt, inSeatItemDelivery, startsAt`. Scanning the whole response -- showtimes and
every `relatedData` collection -- for any key containing price, amount, cost, ticket, fee,
tariff or currency returns **zero** matches, against 15 real showtimes.

**The obvious ticket-type read paths are not there.** Per-showtime, per-site and a bare
collection under the same API all answer 404. Not inventoried further than that, and the
four attempts are the whole of it.

**So the only route left is the seat-selection flow**, and that is where this stops. The
access rule in CLAUDE.md is not "avoid booking endpoints if awkward": they are never
called and never inventoried. A price that only exists once a visitor has started buying
a ticket is inside that flow by definition. This is blocked by the repo's own rule rather
than by difficulty, which is a better reason to stop than a technical one and needs
writing down as such, because a future reader will otherwise re-probe it.

**What is still open.** If Finnkino publishes a visitor-facing price page, that would be
ordinary content rather than a booking endpoint and reading it would be within the rule.
It *could* give per-cinema, per-ticket-type pricing rather than per-showtime, which is a
weaker thing than the chains with listing prices publish. Not probed, and not confirmed to
exist; the entry stays open on that possibility alone.

Request volume for the probe: one `/sites`, two programme reads and four 404s, plus a
token fetch per run. Nothing was written to the repo -- the finding is this paragraph, and
the raw responses were read and discarded.

### Seven backlog items closed without building them (2026-09-01)
The backlog had run to 13 and several entries had been sitting there long enough to look
like commitments. A pass over them closed seven, and none of the seven needed code. Four
were already built under other names, one was already passing, and two were decided
against. What is left is 7.

Each claim was checked against the source before it was written down here, because
"already covered" is the easiest thing in a backlog to believe without looking.

**Genre / format chips -- dropped.** The typed search already matches them. `haystack()`
folds `genres`, `method` (2D, IMAX, Anniskelu), the rating and the age limit into the
per-show string, and adds the TMDB genre names in Finnish and English on top. The entry
argued chips were about discovery rather than filtering -- showing what is available
tonight without guessing a word -- which is a real difference and still not worth a
second route to the same set on a mobile filter row already carrying five controls.

**Sort toggle and a past-showtimes option -- dropped, and the reason is narrower than
"it already exists".** "Ajat" is not the "Leffat" list re-sorted. `renderMovies` groups by
`eventId` and sorts films by title; `renderTimes` sorts `state.shows` by start and prints
one row per screening, so a film with four screenings appears four times. Those are
different lists at different granularity, and a title-versus-first-showtime toggle over
the film list is a thing this app does not have.

It is dropped anyway, because what the toggle was for -- browsing by time rather than by
film -- is what "Ajat" already does. The past-showtimes half is separately answered, and
the two views answer it differently on purpose: `renderMovies` shows only `ahead` while a
film still has a future screening and puts the rest behind a "Menneet näytökset" toggle,
falling back to the full list once `ahead` is empty so a finished film does not vanish;
`renderTimes` leaves past rows where they are, at 45% opacity with `pointer-events:none`.

**Tile / grid view -- dropped.** The question this app answers is when and where a film
plays, and a poster-first tile either hides that or reprints the card that is already
there. The open questions recorded against this item -- scan-by-poster versus time,
showtimes on the tile or behind a tap, auto-width or a manual toggle -- never resolved
because no arrangement avoided both.

**Multi-cinema merged view -- fulfilled.** "Kaikki Helsinki (12)" is this feature for the
case with evidence behind it. Letting a visitor assemble an arbitrary set of cinemas is a
different feature, and it should wait for somebody asking for it.

**Favourites float to top -- done.** `venueRows()` pushes the starred venue, or a starred
combined city, as the first row under its own `vOwn` heading before any city group.
`tests/test_venue_picker.py` asserts the order rather than the membership, because Enter
picks the first row.

**18 px title links -- dropped, and this halves an item rather than closing one.** They
clear 2.5.8's spacing exception by about a pixel, so they pass. The accessibility entry
covered two findings under one marker; the favourite star at 3.25:1 is still open, where
whether 1.4.3 or 1.4.11 governs a text-rendered icon is unsettled.

**A data branch -- decided against**, with the numbers first because the churn is real:
195 of the last 30 days' commits are the pipeline's own, and `.git` is 49 MB against
25 MB of `data/`, 21 MB of it posters. What is missing is a problem. Nothing has broken
because of it, and the fix would be structural: GitHub Pages serves a branch, this repo
has no build step on purpose, and the client reads `data/*.json` from the same origin as
the page. Moving the data off `main` breaks that, and the three ways out are each worse
than the churn -- `raw.githubusercontent.com` is forbidden by a hard rule after its CDN
served a two-commit-stale file, a Pages build that assembles two branches puts the
traffic path behind Actions scheduling, and splitting off only logs and posters reworks
`check_runs.py` and `logs.yml` for a smaller win. Branching does not shrink history in
any case: the blobs stay unless `main` is rewritten, and a rewrite has cost this repo
once already. Reopen it if the repository size starts costing something measurable.

### Two rejected in the same pass
**Denser cards: rejected on measurement.** The proposal was `.movie{gap:14px;
padding:16px 0}` against the current `18px`/`20px`. `.movie` is `display:flex` in a row,
so **`gap` is the column gap and does nothing vertically** -- measured, median card 214 px
and document height 10937 px identical with and without it; it only widens the text
column by 4 px. The whole vertical effect is the padding: card 214 -> 206, document
10937 -> 10577, 3.3 per cent. That changes the number of fully visible cards at **none**
of 320/375/390/430/1280, and spends 20 per cent of the separation between films to do it.
Compressing the product to save 8 px is the wrong direction when 58 px of chrome was
available for free.

**Result count: rejected.** No placement is free. Every option puts a new row directly
above the list at the exact moment the reader is looking at filtered results, and the
count largely restates what the list already shows, since the number of cards *is* the
film count. The closest call of the three: the showtime half of it is genuinely not
visible without scrolling. Not enough to earn permanent code and conditional chrome in a
view whose stated purpose is to get out of the list's way.

### "Did a run happen" is a different question from "did it fail" (2026-09-01)
`check_runs.py` reads every committed `run*.log` and fails on a non-zero or missing
`exit=`. It has caught real outages. It cannot catch the one failure that produces no log
at all: a run that never starts. The laptop asleep, launchd unloaded, the wrapper edited
into silence -- a log reading `exit=0` four days ago passes that check happily, and the
first symptom is the stale banner appearing for whoever opens the site. The gap was
already written down under it, deliberately; this closes the half of it that can live
here.

`scripts/check_staleness.py` reads `data/areas.json` and exits non-zero when it is older
than eight hours, cannot be parsed, or carries a timestamp that cannot be trusted.

**`data/areas.json`, and only since this morning.** It is written by the local half,
which carries 17 of 74 venues and the largest chain in the app. Until `3189906` it was
written *before* the seven Finnkino date requests, so its age answered "when did a run
last get as far as asking for the site list" -- a run that then published nothing still
stamped it fresh. It is now written with the schedule files, so the age means "when did a
complete publish last happen". Building this monitor a day earlier would have shipped one
that lied, which is the argument for doing these two in this order rather than either
alone.

**Eight hours, strictly greater**, because that is `STALE_H` in `index.html` and the
health line already uses it. A monitor firing at a different age would be a second,
invisible definition of stale. A test reads the number out of `index.html` rather than
copying it, so the two cannot drift apart quietly.

**A future timestamp fails rather than reading as very fresh.** The writer stamps
`datetime.now(timezone.utc)`; the reader is a different machine, so a few minutes of drift
is ordinary and tolerated. Past that, one of the clocks is wrong and the age is not
evidence of anything -- and it is the dangerous direction, because a badly future stamp
keeps the file looking current for as long as the skew lasts, which silences the monitor
instead of tripping it.

A file that cannot be read is reported as unreadable and never as an age. "0.0 h old" for
a file that failed to parse would be the healthiest-looking line the tool can print.

**The limit is validated, because two spellings of it made the check unfailable.**
`--hours inf` and `--hours nan` both exited 0 and reported the data fresh for ever: every
comparison against them is false. That is worse than having no monitor, because there is
one in the file map and in the wrapper's crontab and it never says anything. `nan` is the
quieter of the two -- `inf` at least reads as odd in a log line. A negative limit exited 1
and reported the data stale, which is the wrong direction as well: it is a typo, and
answering it with "the pipeline has stopped" sends somebody to look at a pipeline that is
fine. Both now exit **2**, argparse's code for a wrong invocation, so a caller can tell
its own mistake from a verdict about the data. Zero stays valid and is how the tests reach
the stale branch without waiting.

**The streams are separable, which is not the same as quiet.** The verdict goes to stdout
and every failure to stderr, so the wrapper can run `2>&1 >/dev/null` and keep only the
complaints. An earlier draft of this said stderr made a cron "stay quiet while things
work", which is wrong -- cron mails whatever a job writes to either stream. Discarding
stdout is the wrapper's decision and this script cannot make it.

**No command-line test reads the committed file at all, and getting there took two
tries.** The first version ran the script with no arguments against `data/areas.json` and
asserted success, which passes only while that file is under eight hours old: an unrelated
code push would have turned `Checks` red because a laptop had not published that morning,
the monitor reaching into the very CI it exists to stay out of.

The second version kept one test on the committed file with `--hours 0`, reasoning that
any committed file is older than an instant so the answer would be the same at any age.
It is not. A timestamp up to five minutes ahead is deliberately accepted and clamped to
`0.0 h old`, and `0.0 > 0` is false -- so a publisher clock a few minutes fast makes that
invocation report *fresh* and the test red while the script is answering correctly.
Reproduced by stamping the committed file two minutes ahead. The five-minute tolerance is
read against a clock too, so putting it there moved the dependency rather than removing
it.

The default path is now exercised the only way that is actually deterministic: run the
script with no arguments from a temporary working directory holding a `data/areas.json`
the test wrote, once fresh and once twenty hours old. Confirmed by stamping the committed
file at +2 minutes, -20 hours and -400 hours in turn -- the suite is green at all three,
which it was not before.

**The split is the point.** This repo supplies a verdict: a pure function of a file and a
clock, which is why 28 tests can hold it. When it runs, where it reads the file from, and
who hears about it are a schedule, an endpoint and a notification route -- machine-specific
every one, and this repo is public. They stay in the wrapper. Nothing here is a workflow,
an HTTP call, a secret or a scheduler, and the backlog item stays open until the ping
exists.

Verified by breaking it fourteen ways: `>=` instead of `>` at the threshold (1 red), the
age check removed (6), naive timestamps silently treated as UTC (1), the future check
disabled (1), the drift tolerance removed so ordinary skew pages someone (2), an
unreadable file reported as fresh (18), the `generated` type guard removed (4 errors), the
threshold moved off `STALE_H` (4), the default file changed (3), the limit taken on trust
(7), the finite check removed (4), a negative limit allowed (2), a bad invocation exiting
1 as though it were a verdict (4), and failures printed to stdout where a caller
discarding stdout would never see them (3).

### A page build that dies partway published half a generation (2026-09-01)
`build_pages.main()` wrote each page as it produced it. Every individual write is atomic
-- `write_if_changed` goes through `common.write_text_atomic` -- but the *set* was not,
and the set is what a reader sees. An exception anywhere in the render left the tree
holding some of that run's pages and some of the previous run's, and `biorex.yml` stages
`teatteri kaupunki en sitemap.xml` and pushes before it checks whether the build exited
non-zero. So the mixture was committed, pushed and served, and only then did the run turn
red.

Measured rather than argued, in a clone with the schedule perturbed and an exception
raised on the 41st render: **40 of 172 pages new, 132 from the previous build, all staged
for commit** alongside 73 changed data files. With the fix, the same injection stages 0
pages and the same 73 data files.

A partial update sounds harmless and this one is not. A city page is built from the
venues it merges and *after* them, and the sitemap after both, so a half-built run can
serve a city page whose showtimes disagree with the venue pages it links to, under a
sitemap describing neither. Nothing in the markup says it is inconsistent, and
`write_if_changed` means the stale half carries no signal either -- it is byte-identical
to a page that was correct yesterday.

**Batched instead of gated in the workflow.** The pages are collected as `(path, text)`
and written in one loop at the end, so a build that raises writes nothing at all. That
puts the fix where the invariant is, and it costs `biorex.yml` no change -- which matters,
because that file has an unmerged branch against it. It also keeps the workflow's existing
behaviour correct rather than fighting it: a failed build now stages no page changes, so
the run's fresh schedule data still publishes, which is the whole reason data is committed
before the failure gate.

Holding the set costs 4.5 MB across 173 files, measured, in a process that already has
every showtime in memory.

**The residual window is the flush itself** and it is not closed. The loop compares and
writes and does no work of its own that can fail, so only the disk stops it halfway --
which leaves the same mixture as before. That is pinned by a test asserting the error
propagates, because the one response that would make it worse is catching it and letting
the run report success: then the mixture publishes with a green tick.

**Enrichment and poster mirroring were deliberately left alone.** Both tolerate many
per-item failures by design, and a page missing some ratings or showing a placeholder
tile is optional degradation -- it is a correct page with less on it. A page set from two
different generations is not. Gating publication on `enrichfail` or `mirrorfail` would
trade a slightly thinner page for a stale one, and there is no evidence yet that the trade
is worth making.

Verified by breaking it four ways: written-as-produced again (6 red), flushed before the
city pass (2), flushed before the redirects (2), and the flush wrapped in a `try` that
swallows the error (1). The first attempt at the "where the failure lands" test used a
hard-coded 140, which *looks* late and is still inside the venue pass -- so the
flush-before-the-city-pass half fix passed it. The boundary is now derived from the venue
count, which is the only reason that mutation is red.

### A cancelled cloud run cost two venues every poster (2026-08-30)
Kino Engel and Kino Akseli rendered placeholder tiles for every film, at every screen
size, for hours. Three things had to line up.

**The local half publishes posters it cannot mirror.** `mirror_posters.py` runs only in
the cloud workflow, so Engel and Akseli ship the cinema's own URLs -- `johku.com/...`,
`kinoakseli.fi/...` -- and depend on a later cloud run to rewrite them into
`data/posters/`. Finnkino does not have this problem because `fetch_data.py` mirrors its
own posters in `download_poster`. That asymmetry is the root of it: 38 of 38 Engel
showtimes and 12 of 12 Akseli were remote, and every cloud provider was clean.

**`cancel-in-progress: true` threw away the run that fixes it.** A manual run of the
local script dispatched the workflow while a scheduled one was in flight, so the
in-flight run was cancelled mid-mirror. Nothing retries. Measured across the last 14
local runs, the normal window between publishing a remote URL and the cloud rewriting it
is a **2.7 minute median, 6.9 max**; a cancellation stretches it to the next cron, up to
four hours.

**Since v64 the client refuses a remote poster** rather than leaking the reader's IP to
someone else's host, which is correct and is exactly the case `safeAssetUrl` was written
for -- recorded then as "latent rather than live, which is precisely why it needed a test
rather than an inspection". It is no longer latent. The fallback tile is the right
behaviour; the data was wrong.

Two changes, one for the cause and one so the next variant is not silent:

- `cancel-in-progress: false`. Queueing keeps the serialisation the setting was added for
  -- two runs must not race on the same data files -- while letting the queued run
  actually finish. Four crons and four local dispatches a day means at most two in
  flight, so nothing piles up.
- `build_pages.py` names it. It runs straight after `mirror_posters`, already drops a
  non-local poster from the markup, and said nothing about it, so a reader saw tiles and
  the log looked clean. It now prints the hosts and the count. Verified against the real
  broken data before the recovery: `78 poster references were still remote ... johku.com
  x58, kinoakseli.fi x20`, and silent once the next cloud run had mirrored them.

The state self-heals on any completed cloud run, which is what happened here: 4 posters
downloaded, 0 remote references left. The fix is about not losing the run, and about
noticing when it is lost.

### The same asymmetry, one layer up: enrichment (2026-08-30)
Posters fixed, and the very next look at Kino Engel showed no score rings. Same shape:
`enrich_tmdb.py` runs only in the cloud, Finnkino has its own TMDB pass inside
`fetch_data.py`, and Engel and Kino Akseli have neither. Measured across the local run
that had just landed: **38 of 38 Engel showtimes and 12 of 12 Akseli went from a full set
to zero**, against 38/38 `tmdbId`, 35 ratings and 35 trailers in the cloud commit before
it.

Five fields, and `gids` is the one that matters most -- it drives the genre names the
client renders and the id half of the kids filter, so this was never only a missing
badge. `tmdbId` also feeds cross-chain merging; the damage there was small today only
because none of the 14 films showing at two or more Helsinki chains happened to be at
Engel.

**Running `enrich_tmdb` on the local half was the obvious fix and is the wrong one.** It
writes three shared files -- `tmdb-titles.json`, `films-extra.json`, `tmdb-genres.json` --
that the cloud pass also writes, and the wrapper pushes through `git pull --rebase`. A
content conflict in a single-line JSON cache cannot auto-merge, would fail all three push
attempts and abort the run. Trading a three-minute missing rating for a broken push is a
bad trade.

**The actual fix is to stop `run.py` dropping them.** A run rewrites a venue file
wholesale from what the adapter returned, so anything only the TMDB pass knows is lost.
`run_site` now reads the previous file first and carries `tmdbId`, `tmdb`, `votes`, `tr`
and `gids` forward by title -- the same key the TMDB pass itself uses, and the right one,
since these are properties of the film rather than the screening.

- **A floor, never an override.** `setdefault` leaves anything the adapter supplied
  alone, and the next enrichment pass overwrites all of it with fresh figures.
- It helps in the cloud too, where `run.py` also runs before enrichment: if the TMDB pass
  ever fails, the previous values stand instead of vanishing.
- It fixes the general trap this file already records -- *running `run.py` locally for a
  cloud provider and committing strips enrichment*, which once cost 1201 showtimes their
  `tmdbId` -- rather than only the two local providers.

Verified on the real cloud-committed file: 16 titles carry all five fields, none missing
`gids`, and the stripped file yields nothing, as it should. Four tests, all confirmed to
fail when broken -- removing the carry-forward errors two, and turning `setdefault` into
an assignment fails the one that guards the adapter's own values. The first version
shadowed the venue loop variable and the tests caught it on the first run.

**Closing the asymmetry: the local half can run the mirror too.** `mirror_posters.py`
needs no filter to do it. It only rewrites references that are still remote, and by the
time the local run happens every cloud provider's poster is already local, so pointing it
at the whole `data/` directory rewrites Engel and Akseli and touches nothing else.
Verified: with a remote URL planted on a Kino Akseli show it rewrote that one reference
in one file and left the other thirty alone.

It does need **Pillow**, and that is not optional. Measured rather than assumed: Kino
Akseli publishes the distributor's key art at 1984x2835, **872 kB for a single poster**,
against 57 kB once downscaled to 342 px -- 25 times larger, into a repo that is 11 MB of
posters in total. Engel's are gentler at 62-127 kB against 35-46 kB. Mirroring verbatim
is not a shortcut around the dependency.

`mirror_posters` now checks for Pillow once, up front, instead of letting every download
raise `ImportError` inside its own try. Without the check a machine with no Pillow
reports "185 failed" and reads like the network is down; it now prints one line naming
the real cause and the install command.

**That line first exited 0, and that was the wrong half of the decision** (corrected
2026-08-30, same day). Exiting 0 made "mirrored everything" and "could not mirror
anything" the same answer to a caller, and the second state is invisible everywhere
downstream: nothing is rewritten, every reference stays remote, the client refuses a
remote poster on purpose since v64, and those films show placeholder tiles. The one step
positioned to notice was the one reporting success. In the cloud that is worse than it
sounds, because Pillow is `pip install`ed inside the job -- it is missing only when that
install broke, and the workflow would have gone green over it.

Three states now, and the middle one is the point:

    OK (0)           ran; posters that failed to download are logged and left hot-linked
    CANNOT_RUN (3)   cannot downscale at all, so nothing was attempted and nothing changed
    1                an uncaught traceback, which is what the interpreter already exits with

3 rather than 1 because 1 already means the script crashed, and 2 is the conventional
usage error. A poster that fails to download stays exit 0 and is *not* folded into this:
kinoakseli.fi challenges datacenter IPs and fails every cloud run by design, so making a
download failure fatal would hand a third party the ability to fail the build.

**The guard checks by using Pillow, not by importing it.** An import check leaves the same
hole one layer in: `from PIL import Image` succeeds on an install whose imaging library is
incomplete -- a wheel built against a libjpeg that is no longer there, a half-finished
reinstall -- and then every poster raises inside its own try, is counted as a download
failure, and the run exits 0 with "185 failed". So `pillow_problem()` does a four-by-six
round trip through the exact calls `download` makes: open a paletted image, convert,
resize with LANCZOS, save as JPEG at the real quality settings. It returns the reason
rather than a boolean, because the two causes need different fixes and telling someone who
has Pillow installed to install Pillow is worse than saying nothing.

**No `--optional` flag, and that is an argument about where tolerance belongs.** The
obvious reading is that a non-zero exit would stop the local run publishing showtimes. It
does not, and neither caller needed changing: the cloud workflow commits data and logs in
the step *before* the gate that reads `mirrorfail`, and the local wrapper collects the
code into `fail` and carries on through commit, push and dispatch, failing only at the
very end. So the showtimes go out either way. The only thing exit 0 bought was hiding the
degradation, and a flag would have given that silence a name. The guard is also the first
statement in `main()`, so a run that cannot mirror leaves exactly what the fetch wrote --
which is what makes publishing over it safe rather than merely permitted.

Covered by `tests/test_mirror_posters.py`. The Pillow-absent cases block the import
through `sys.meta_path` rather than stubbing `have_pillow`, because a version that dropped
the up-front check and let each download raise `ImportError` would still satisfy a stubbed
predicate. Requirement five lives in the caller, so two of the tests read
`biorex.yml` directly: the mirror step must still record `$?` into `mirrorfail` and the
gate must still compare it to 0, since under `set +e` a non-zero exit changes nothing
without both halves. Verified by breaking it eleven ways, including returning 0 again,
setting `CANNOT_RUN = 1`, removing the guard entirely, moving it below the first `mkdir`,
making a download failure fatal, deleting the workflow gate, reverting the guard to an
import check, and collapsing the two reasons into one message.

The local wrapper prints `posters: DEGRADED` for exit 3 and `posters: FAILED` for
anything else, and sets `fail=1` either way -- a run that mirrored no poster must not
finish clean, but the two send you to different places.

Note for running them: the cases that need a real Pillow skip on the system interpreter,
which does not have it. The cloud installs it into the job and the local wrapper runs the
script from its own venv; use that interpreter to see all nine.

**That venv's path was written out here, and has been removed** (2026-08-30). CLAUDE.md
forbids machine-specific detail in this repo and names paths first among them. A
home-relative path carries no username, but it is still specific to one machine, and the
directory it named is where the token retrieval lives, which the same rule lists
separately. It was also unusable by anyone who read it, whereas "the venv that has Pillow"
can be acted on anywhere. `tests/test_mirror_posters.py` carried the same path inside a
runnable command and now carries a placeholder.

### Finnkino drops the odd character to "?" (2026-08-30)
The Vaiana live-action synopsis published "Catherine Laga?aia" and "Auli?i Cravalho".
Both names carry an okina (U+02BB).

**It is their payload, not this pipeline**, and the string proves it on its own: `®`,
`“ ”` and every `ä` in the same sentence arrive intact, so the transport is not lossy.
Neither candidate mechanism can even produce a "?" -- `json.loads` raises on malformed
UTF-8 rather than substituting, and the one decode in `fetch_data.py` uses
`errors="replace"`, which yields U+FFFD. Worth checking in that order next time: the
question "is this ours or theirs" was settled by three characters in the text we already
had, without a single request.

**A "?" cannot be decoded back.** It could stand for an apostrophe, an okina, a real
question mark, or anything else the CMS could not encode. Guessing per-character would
have been easy here, because the names are recognisable, and wrong in general.

So the repair transcribes rather than guesses. Several chains run the distributor's blurb
verbatim, and `films-extra.json` already held the same 823-character sentence with the
okina intact -- differing at exactly the two positions where Finnkino has "?".
`synmerge.repair_from_twin` uses a twin only when it is the same length and differs
*only* where this text has "?", so the result is a string we already hold rather than an
invention. A twin that disagrees anywhere else is a different synopsis and is left alone;
a genuine "Mitä?" is never touched, because no twin will differ there.

- Covered by `tests/test_synopsis_repair.py`, and the cases that refuse to act are the
  ones worth having: a twin that differs elsewhere, a twin that is also broken, a
  different-length twin, no twin, and a real question mark. Verified by removing each
  guard and watching the matching test go red.
- The lookup goes through `synmerge.norm()`, the same key `films-extra.json` is written
  with. Matching on the raw title silently never hits, which is what removing it shows.
- `data/films.json` was repaired in place in the same commit, so the fix is live rather
  than waiting on the next local run. `fetch_data.py` writes the same value from then on.
- **This needs a local run to be exercised in the pipeline.** `fetch_data.py` cannot run
  from a runner -- Finnkino answers Cloudflare 403 to datacenter IPs -- so the call site
  is compile-checked here and the logic is unit-tested, but the integration only runs at
  home. `[films] N character(s) restored from another chain's copy` in `run.log` is the
  line that confirms it.
- Two other intra-word "?" in the data are not this and are left alone: `watch?v=` in 39
  YouTube URLs, and one missing space after a real question mark in a provider's own
  prose ("tapahtunut?Will Gluck"). Adding that space would be editing their sentence,
  which is a different thing from restoring a character we can prove was there.

### IndexNow, and what it is actually worth here (2026-08-31)
`scripts/indexnow.py` plus `.github/workflows/indexnow.yml` tell IndexNow which generated
pages a push changed. The key is `9510fcf2085e43b89ff8b86a67f75362.txt` at the site root.

**Worth being honest about the ceiling: Google has never adopted IndexNow.** It is Bing,
Yandex, Seznam, Naver and Yep, which on a Finnish cinema site is the tail of the market
and not the head. Nothing about the implementation changes that, and nothing larger should
be built around it.

What makes it a fair fit anyway is that showtimes are perishable and this repo knows
exactly which pages moved -- the one thing the protocol asks for and most sites cannot
supply. Measured across twelve runs, the change set is bimodal rather than "everything,
always": quiet runs rewrite 0-23 pages, and the big ones (100-151) are day rollovers or
new venues landing. `write_if_changed` is what makes that distinction, and it already
existed.

- **The URL list comes from the commit, not the generator.** `build_pages.py` takes no
  network at all and is deterministic; putting a third-party POST inside it would trade
  that for nothing, since git already records which page files changed. It also keeps the
  submission out of `biorex.yml`, which has an unmerged branch against it.
- **Every status letter is a notification, removals included.** `A`/`M` submit the page,
  `D` submits the URL that is gone so the engine can drop it, `R` submits *both* sides so
  the old entry retires and the new one is found. Nothing reads the file: a deleted page
  cannot be read, and what a page now contains is a reason to announce it, not to stay
  quiet.
- **The first version filtered out `noindex` pages and that was backwards.** IndexNow is
  for added, updated, deleted and moved URLs -- a redirect or a 404 is exactly what an
  engine needs told, since otherwise it serves the old entry until it happens to recrawl.
  The filter suppressed precisely the notifications worth sending, and the test written
  for it "proved" that the commit adding four redirects should submit nothing. It now
  submits all four. A test can confirm the wrong rule as comfortably as the right one.
- **The key is a public ownership token, not a secret credential.** It is served openly at
  the root so the protocol can confirm who controls the domain, which is why committing
  it is correct. Possession cannot modify the site or authenticate another host, but it
  would let someone submit same-host notifications and generate crawl noise -- so it is
  not a secret and not nothing either. Its one invariant, that the file contains its own
  name, is what the far end checks, so it is checked here first.
- **`on: push` alone would have made this silent.** A push made with `GITHUB_TOKEN` does
  not trigger a workflow -- GitHub suppresses it so workflows cannot recurse -- and the
  routine `Update cloud provider data` commits are made exactly that way. Those are also
  the commits where the theatre and city pages actually change, so the trigger would have
  fired for hand commits and for nothing else: most of the feature, quietly missing, with
  no error anywhere. The fix is a second trigger, `workflow_run` on "Fetch cloud
  providers", rather than a PAT (a long-lived credential for a job that needs none) or an
  edit to the frozen fetch workflow.
- **The data commit has to be found, not handed over, and a lower time bound is not
  enough to find it.** `workflow_run.head_sha` is where the triggering run *started*, and
  a queued run starts from a base that has since moved, so the range it names can span an
  earlier run's data commit too. The first attempt took the newest bot commit after the
  run started, and that has a race with teeth: run A publishes commit A and finishes, run
  B publishes commit B, and only then does A's notification job get CPU. Both commits are
  newer than A's start, so A is handed B's commit -- A is never announced, B is announced
  twice, and an A that published nothing at all is credited with B's work. The commit must
  fall inside **the run's own window**, `run_started_at <= committed <= updated_at`, and
  the newest match inside that interval is the right one.
- **Never gated on `conclusion`.** The fetch workflow commits and pushes *before* its
  provider-failure gate, so a run can publish live pages and still finish red -- those
  URLs need announcing exactly as much as a green run's. Whether a commit exists is the
  only question worth asking, and looking for it answers it.
- **Branch guards on both doors.** `push: branches: [main]`, and for the other door
  `github.event.workflow_run.head_branch == 'main'`, written as an event check so it does
  not evaluate to null on a push and skip the job. A page committed on a branch is not
  live, and announcing a URL that 404s is worse than announcing nothing.
- `ref: main` on the checkout is **not** required -- on a workflow_run event `GITHUB_SHA`
  is already the last commit on the default branch, which an earlier version of this note
  had wrong. It stays because the job's correctness depends on which history it reads,
  and that is worth stating rather than inheriting.
- **10,000 URLs is the protocol's ceiling for one POST**, so the list is batched at that
  size. This site is two orders of magnitude below it and the batching will not fire for
  years; it exists so the limit is explicit rather than discovered as a 422 on the day
  someone regenerates every page.
- **A push is not one commit.** The range is the push event's own `before`..`after`;
  `HEAD^..HEAD` would silently drop every page change in every earlier commit of the same
  push, which looks identical to nothing having happened. An all-zero `before` means the
  ref was created by that push, and falls back to the tip's parent rather than diffing
  the empty tree, which would announce every page on the site. `fetch-depth: 0` for the
  same reason: a clone deep enough for `HEAD^` is not deep enough for `before`.
- **Response handling.** 200 and 202 are success -- 202 is the normal answer while a new
  key is still being validated, and treating it as failure would make the very first
  submission red. 400/403/422 are this repo's mistake and are not retried, because
  retrying repeats it. 429, 5xx and a dead socket are transient and get a bounded three
  attempts, honouring `Retry-After` when it is sane and capping it at 60 s so a stranger
  cannot stall the job. Exhausting the retries exits non-zero: this workflow cannot block
  publication, so a submission that keeps failing should say so rather than stay green.
- Covered by `tests/test_indexnow.py`, verified by breaking each guard. One of them --
  that the key file must contain its own name -- initially had no test and was only
  proved by hand; the test was added rather than the manual check being counted.

### Provider text could close the JSON-LD element (2026-08-31)
`ld_json()` serialised provider titles, theatre names and booking URLs with a plain
`json.dumps` and the page embedded that inside `<script type="application/ld+json">`.
Valid JSON is not enough in that position: the HTML parser ends a script element at the
first literal `</script>` **regardless of the type attribute**, so a title containing
one would have closed the element mid-document and opened a live script context on a
generated page. Found by an external review, not by an incident -- no current provider
ships such a title -- but the property that mattered was already broken: this was the
one sink where upstream text crossed into markup without context-specific escaping,
while every other interpolation goes through `esc()` or `safeUrl()`.

- **The fix is alternative JSON spelling, not sanitisation.** `&`, `<`, `>`, U+2028 and
  U+2029 are replaced with their `\uXXXX` escapes after serialisation, so a consumer
  parses the identical value. That matters here more than usual: the raw title is the
  key for `normTitle()`, `films-extra.json` and `tmdb-aliases.json`, so nothing may be
  altered or dropped, only respelt.
- **U+2028/U+2029 ride along** because `ensure_ascii=False` emits them raw and they are
  legal in JSON but not in JavaScript source. No JS engine executes this block, but a
  scraper that pastes it into one would break, and the escape costs nothing.
- **A global replace is safe** because `<`, `>` and `&` can only occur inside JSON
  string values -- the structural characters are `{}[],:"` and digits.
- Covered by `tests/test_ld_json.py`, including the whole-document property that a page
  built from a hostile title contains exactly one `</script>`. Verified by breaking the
  escape loop: three of the four tests go red. The fourth -- escaping is lossless --
  deliberately stays green on that break: it asserts the escaped output parses back to
  the original strings, which also holds for unescaped output.

### Where a run's time actually goes, and what could be taken back (2026-08-31)
Measured off one cloud run's committed logs rather than guessed: **eTiketti is about 85%
of it.** 185 requests against 9 for Nexxo, 25 for BioRex, 6 for Gilda and 1 for Orion. At
`sleep=1.2` after each film page that is roughly **3.5 minutes of deliberate sleeping**,
and everything else in the run is noise beside it.

The distinction worth keeping straight before anyone "optimises" this:

- **Per-host pacing is the design.** 1.2 s between two requests to the *same* cinema is
  the courtesy the whole access story rests on, and it is not negotiable for speed.
- **Serialising across hosts is not.** Reading kinopirtti.fi while biograni.fi is mid-fetch
  adds nothing to either -- they are unrelated third parties who cannot tell. Nothing
  chose that behaviour; it is how the loop was written when the module had two sites, and
  it now has fifteen.

So the available win is a pool **over sites**, keeping the sleep **within** each site:
eTiketti's wall clock would go from the sum of fifteen sites to the slowest single one,
roughly 3.5 min to ~20 s, with per-host load unchanged. No workflow edit needed.

**"Over sites" is wrong, and the next entry is what landed instead.** Two Nexxo hosts
serve two sites each, so a pool keyed on the site doubles the request rate at those two
cinemas -- the one thing this entry says is not negotiable. The unit is the host. The
site count above is also stale: eTiketti is seventeen sites as of 2026-09-01, not
fifteen.

Not free, and these are the reasons it is a design item rather than a small patch:

- **`common._stats` and `_throttle` are module-level dicts** mutated on every request and
  not thread-safe. Those counters are what the committed logs use to show how the
  pipeline fetched -- losing counts would quietly corrupt the evidence, which is worse
  than being slow.
- **Log interleaving.** `[provider] Venue: N showtimes` reads top to bottom today; a pool
  shuffles it. The committed logs are the verification surface for every run, so output
  would need buffering per site before printing.
- **The HTTP validator cache** writes per-URL files, and concurrent writes want checking
  against `write_text_atomic` rather than assuming.

One avenue is already closed and should not be re-tried: **conditional GETs do not help
here.** The same log reads `185 not stored (origin said no-store)` -- the eTiketti origins
forbid caching, so there is nothing to revalidate against.

Worth being honest about the payoff. At ~5 minutes, four to eight times a day, this is not
hurting anyone. What it buys is a faster verification loop when changing an adapter, and a
smaller window in which a mid-run failure can land. Do it deliberately or not at all.

### A run reads unrelated hosts at once (2026-09-01)
Done as the entry above proposed, with one correction to its design and one hazard it
did not name.

**The pool is keyed on the host.** Measured against the live `SITES` on 2026-09-01:
eTiketti is 17 sites on 17 distinct hosts, 25 venues -- there a pool over sites and a pool
over hosts are the same thing, and a *cloud* run reads 16 of them, since Joutsan Kino is
routed local. Nexxo is 8 sites on **6** hosts, 13 venues, because
kinoaurora.fi serves both kinoaurora and kinometso and kinohirvi.fi serves both kinohirvi
and biosade. Keyed on the site, those two pairs would be read concurrently against one
cinema's server at twice the rate their adapter paces for, which is the courtesy the whole
access story rests on. `run.py::host_groups` therefore groups by
`urlsplit(site["base"]).netloc` and gives each group one thread, so the sleep inside
`fetch_site` still describes what a host experiences.

`base` and not `site`: Bio Säde's showtimes come from kinohirvi.fi while its ticket links
go to biosade.fi, so the visitor-facing host is not the one being paced. A site carrying
no `base` at all keeps its host inside the adapter, out of reach; those share one group
and are read one after the other. Treating an unknown host as its own would put two
requests at one server at once; treating two servers as one costs seconds.

The hazards, and what each turned out to be worth:

- **Output is buffered per site and replayed in SITES order.** Sites finish out of
  order, so a pool prints `[provider] Venue: N showtimes` in an unreadable order. Each
  site's output is collected and replayed when its turn comes, *both* streams into one
  list, so the merge the workflow does (`> run-$m.log 2>&1`) sees them in the order they
  were written. That fixes something already broken: Python line-buffers stderr and
  block-buffers a redirected stdout, so the committed `run-nexxo.log` opens with
  kinometso's empty-venue notice -- a line printed by the eighth site of eight. The
  committed logs read chronologically from this change on, so the next run's log shows
  that as a diff.
- **`common`'s counters are locked.** The lock fixes nothing that was measured going
  wrong: on CPython 3.14 with the GIL, eight threads and 1.6 million `_stats["miss"] += 1`
  lose exactly zero, and the Retry-After decision's read of `waited` and its charge
  against it are separated by no call and no jump. It is there because that is an
  implementation accident rather than a language guarantee, and it is false on a
  free-threaded build, which 3.14 ships and which nothing here pins against. It also lets
  the Retry-After ceiling be one decision instead of three reads: the seconds are reserved
  before the sleep, so parallel hosts cannot each pass the same remaining budget. The
  tests pin the totals, which is what the committed log offers as evidence.
- **`_write_slot` writes a per-thread temp name.** The slot is a hash of the URL, so two
  threads asking the same URL would have written the same `<hash>.tmp`, one truncating the
  other and both renaming the result over the slot. The loser is a corrupt cache entry
  served as a cached body on the next run. Unlikely across different sites; the fix is
  the temp name.
- **`synmerge.merge()` is the hazard the entry above missed.** It is a read-modify-write of
  the shared `data/films-extra.json` and `run_site` calls it per site, so two sites merging
  at once each write back what they read and the second silently drops the first's
  synopses. Serialised inside `merge()` rather than hoisted out of the pooled section and
  merged once after the join, because merging in place keeps `[label] synopses merged: N`
  inside that site's own block in the log, and the merge costs milliseconds against a
  site's minutes. One bounded consequence: the order *new* keys land in now follows which
  site finished first. Keys already in the file keep their place -- `setdefault` does not
  move them -- so this is a handful of new films appearing in a different order among
  themselves on the run that first sees them, and nothing at all afterwards.
- **The lock was not enough, and a review caught it.** It stops a lost write and decides
  nothing about *whose* text lands when two sites publish different `_syn` for the same
  normalised title -- two chains showing one film, each with its own blurb. Fill-if-empty
  then means "whichever host answered first", which with a pool is a property of the
  network. Probed 2026-09-01 with one slow site and one fast one over the same data:
  `workers=1` published the first site's synopsis, `workers=2` published the second's.
  The winner is now the earlier site in SITES order, which is what the sequential loop
  produced and is the same at every pool size. `run_site` passes its index to
  `synmerge.merge`, which keeps a per-run map of who claimed each slot; an earlier site
  may take back a slot a later one filled **during this run**, and text that was in the
  file before the run began is never touched -- the provider's own synopsis still beats
  TMDB's. `synmerge.reset()` clears the map between modules, so a second module's site 0
  cannot outrank the first module's site 1. Values are identical at any pool size; the
  key-order consequence above is what remains, and it carries no meaning.

Everything else `run_site` writes was already single-writer, checked rather than assumed:
across all eight adapters the 57 venue ids and 31 provider ids are each unique, so
`area-{id}.json` and `venues-{provider}.json` have exactly one writer per run.

**The pool is 8.** The number bounds this end and not any cinema: per-host load is the
host grouping's job, and what a pool size bounds is open sockets and response bodies in
flight, at most `MAX_HOSTS * MAX_BODY` = 160 MB against a runner's 16 GB. 8 is twice the
four vCPUs an ubuntu-latest runner has, covers Nexxo's six groups outright and takes
eTiketti's 16 cloud sites in two waves. "As many as there are sites" was rejected as a
default because it raises the ceiling every time a cinema is added, with nobody deciding
to. `KINO_MAX_HOSTS` overrides it, in the style of `KINO_PAGE_BUDGET`, and 1 is the
sequential path -- which a test uses to show that path still writes the same files and
prints the same summary line.

**One pooled run, 2026-09-01, and the sample is one.** The "Fetch cloud providers" step,
which runs all six cloud modules one after another, completed in **186 s** against a
**562 s median across eight sequential runs**: 3.0x faster, 376 s saved. Those eight span
479-626 s, so the observed speed-up sits somewhere in **roughly 2.6-3.4x** depending on
which sequential run it is measured against. That range is the honest figure until more
pooled runs land; a single sample cannot separate the change from an ordinary good run,
and the workloads are not controlled either -- the pooled run made 225 eTiketti requests
against the previous run's 224.

Step durations are job metadata from the Actions API. That is not a reading of the Actions
logs and does not touch the rule about committed logs, which is about what a run *did*:
that half was read from `run-etiketti.log` and `run-nexxo.log` as always.

Two things this measurement does **not** establish. It does not measure eTiketti's own
duration -- the step covers all six modules, so "eTiketti went from 3.5 min to X" cannot
be read off it, and the comparison against the prediction above is a comparison of
inferred absolute savings, not of that one module's time. And the localhost benchmark run
beforehand -- 17 servers at eTiketti's shape, a tenth of the real pacing, 24.16 s at
`workers=1` against 4.29 s at 8 -- is directionally consistent with what production did
and is not validation of it. It measured the arithmetic on loopback with no upstream in
the path.

The committed logs say the rest of it held. `run-etiketti.log` has 16 provider blocks in
SITES order with no site's lines inside another's, and `run-nexxo.log` 8; the counters are
unchanged for the same work (Nexxo byte-identical at 10 requests, 12 venues, 165 showtimes,
1 pending, 0 failures; eTiketti 225 requests against 224, one film page more than the run
before it). Every provider exited 0 and `check_runs.py` passes. And the reordering landed:
`run-nexxo.log` used to open with kinometso's empty-venue notice, printed by the eighth
site of eight, and now opens with kinoset's first line while that notice sits at line 33
inside kinometso's own block.

Covered by `tests/test_run_pool.py`, 22 tests against real localhost servers rather than a
mocked fetch, because overlap in time is the property under test. Each was verified by
breaking the code under it: keying the pool on the site instead of the host (four go red),
letting a base-less site be assumed independent, dropping a request from the counters,
charging the last retry for a sleep it never takes, printing from the worker instead of
buffering (three go red), replaying without flushing between the streams, yielding only
after the pool joins, letting a worker's exception escape (which hangs the run rather than
failing it), removing the synmerge lock,
hard-coding the pool size past the environment, and draining the queue on teardown
instead of cancelling it. Seventeen checks, all red on the break and green on the
restore.

Checked once against the real thing rather than only against localhost: one `run.py nexxo`
from an ordinary connection, into a scratch directory, over the six hosts this change is
actually about. Same 12 venues, 158 showtimes, 10 requests, one pending venue and zero
failures as the committed log, same site order -- and the one difference is the one
predicted above, Tikkakoski's stderr notice moving out of line 1 and into kinometso's own
block. No second run was made to time it: repeatedly reading someone's cinema to measure a
pool is exactly what the access story forbids, and the wall-clock figure belongs to the
cloud log.

**A worker that ends is not a provider that failed, and it is not a run that carries on
either.** Two wrong answers in a row here, both caught by review. The first caught
`BaseException` per site and handed it back as that site's error, turning a `SystemExit`
out of adapter code into `[provider] FAILED: 3` -- a line that says a cinema could not be
fetched, about a cinema nobody asked. The second reported it as `not read` instead, which
stopped blaming the provider and still suppressed the exception: the run exited 1 and
published, where a sequential run would have ended on the `SystemExit` itself.

Suppression was never a choice anyone made. A worker's exception goes onto a future, and
nothing here reads futures -- the pool is drained through per-site events, so the
exception simply vanished. So it is recorded and re-raised by the reader thread, which is
the thread a sequential run would have raised it on, and the generator's `finally` has
cancelled what was queued and put `sys.stdout` and `sys.stderr` back before it leaves.
Ordinary failures are still caught per site with `except Exception`: one cinema refusing
must not take the rest of its host with it.

The two `finally` blocks now do one job, which is to stop the reader waiting on a site
that will never report. The inner one releases a site once it has an outcome; the outer
one releases everything still held and runs *after* `fatal` is recorded, so the reader
sees the exception before it can reach an empty slot. Nothing is ever reported as
abandoned, so `HostAbandoned` and the `not read` cause `check_runs.py` had learned are
both gone again -- there is no non-fatal path left that needs them.

One thing threads cannot give back: `shutdown(wait=True)` still waits for the hosts
already in flight, so the `SystemExit` arrives after they finish rather than at once. A
sequential run had nothing in flight to wait for.

Five tests, all break-verified: swallowing the exception, a reader that never checks for
one, catching `BaseException` per site again, an outer block that releases nothing (which
hangs, so that test runs on a watchdog), and an ordinary failure treated as fatal.

One thing the pool has that the sequential loop could not: **a run being torn down stops
reading hosts it has not reached yet.** The executor is shut down with
`cancel_futures=True`, so a Ctrl-C, a closed laptop or a caller that stops reading drops
every host still queued. Hosts already in flight are waited for, because a thread part-way
through writing a venue file has to finish and `wait=True` is what makes the atomic write
mean anything. Nothing is cancelled on the normal path, where every group has run by the
time the drain ends.

**What Nexxo was doing on the day this landed, recorded before it can be misread.** The
last cloud run before this branch rebased -- 8fcdc47, still the sequential code -- came
back `exit=1` with four sites refused: `403` from kinoset.fi and kinohirvi.fi
(`Server: openresty`) and from kino-olympia.fi (`Server: Apache`). Six venues kept their
previous data and the run went red. A manual `run.py nexxo` from an ordinary connection a
few hours earlier had read all six hosts cleanly.

Two things that establishes, and no more. The refusal came from the origin layer rather
than from a Cloudflare edge: three origin `Server` strings and no CF-Ray on any of them.
And it predates the pool -- a line of it was not on `main` when this happened -- which
matters because the next Nexxo 403 will arrive after a change that reads hosts
concurrently and will look like its cause.

What it does *not* establish is which origin-side policy refused. Application rate
limiting, a WAF rule and a policy on the address the runner called from are all
consistent with these headers, and the ordinary-connection comparison separates none of
them: an address-based rule and a rate limit both let a laptop through hours earlier.
The rule in "A refusal has to say which layer refused" reads a missing CF-Ray as
application rate limiting; that step distinguishes edge from origin, which it does
correctly here, and it does not distinguish one origin policy from another. Left as an
observation rather than a diagnosis, because the next run is the only thing that can
narrow it.

**A second observation, 2026-09-05, narrows it toward a per-hour limit.** The same three
hosts -- kinoset.fi and kinohirvi.fi (`Server: openresty`), kino-olympia.fi (`Server:
Apache`) -- refused with origin-layer 403 again, in a cloud run dispatched by hand at 23:56
UTC, the **third run within 41 minutes** (23:15 cron-adjacent, 23:42 after a local run,
23:56 manual). Every other run that day read them, including two that followed the previous
one by 20 and 26 minutes. Six venues kept their previous data, `run-nexxo.log` went `exit=1`
and the dispatched run failed on the provider gate. Two data points, both a manual dispatch
stacked on runs already made, both refused by exactly these hosts and nothing else. Rule
for the person at the keyboard until a third point says otherwise: **do not dispatch a
cloud run within an hour of one that already ran**; a code change that needs a run can
wait for the next cron or the next local run's own dispatch.

Not changed: `fetch_site` and its sleep, the workflow, and the site list. The local half
runs the same `run.py`, so it picks this up on its next run with no wrapper edit -- and
nothing else: its three modules have one site each on that half, so they are one host
group apiece and read exactly as they did, apart from the log order. Where this actually
does anything is the cloud half, and there only for Nexxo (6 groups) and eTiketti (16);
the other four cloud modules are a single site.

### Two cloud runs cannot both rebase their data (2026-08-31)
A cloud run failed with `could not push after 3 attempts`, having fetched everything
correctly: all six providers `exit=0`, enrichment, posters and pages all fine, the commit
made. It died rebasing that commit onto a `main` that had moved, with a `CONFLICT` on
about eighty generated JSON files.

**A queued run always starts from a stale base, by design.** `actions/checkout` defaults
to `github.sha`, which is resolved when the run is *created*, not when it starts. The
`kino-data` concurrency group correctly queues a second run rather than cancelling it --
that part works and should stay -- but the queued run then checks out the commit from
when it was queued, sits behind a nine-minute sibling, and wakes up on a base two commits
old. The checkout line says so outright: `git fetch --depth=1 origin +7f9494d...`.

**Rebasing generated data was never going to work.** These files are whole-file snapshots
of a fetch; a content merge of two independent snapshots is meaningless, so any overlap
conflicts on every file that moved. Both runs hold a complete and equally fresh copy, so
there is nothing to merge and nothing lost by choosing one.

**And the retry loop could not retry.** A conflicted rebase leaves the tree unmerged, so
attempts two and three died instantly on `Pulling is not possible because you have
unmerged files`. Three attempts were one attempt, and had been since the loop was
written -- it could never help with the failure it exists for.

Fixed with two lines, both verified against a reproduction rather than reasoned about: a
scratch repo with two clones committing different snapshots of the same file over one
base reproduces `pushed=0` exactly, and the fix pushes on the first attempt.

- `git rebase --abort 2>/dev/null || true` at the top of each attempt, so a wedged tree is
  cleared and the retries are real. Tested by wedging a tree deliberately -- one `UU` file
  and a rebase in progress -- and watching the loop recover.
- `git pull --rebase -X theirs`, where "theirs" during a rebase is the commit being
  replayed: this run's data. Verified that the snapshot which lands is the later run's.

**`-X theirs` was wrong and was removed the same day.** It resolves *every* conflict in
favour of this run's snapshot, which is only safe while the other side is an equivalent
cloud snapshot. When `main` moves because a person changed the generator, a provider or a
generated page, the policy overwrites that newer work with output from stale code -- and
says nothing, which is a worse failure than the red run it was added to prevent.
Demonstrated rather than argued: with a human fix to a generated file pushed mid-run,
`-X theirs` pushes successfully and the fix is gone from `main`; without it the run fails
and the fix survives.

The cause was the stale base, so that is where it is now fixed: the checkout says
`ref: main`, and a queued job therefore fetches the branch when it *starts* rather than
resolving `github.sha` from when it was created. A run that is not stale has almost
nothing to conflict about. If `main` still moves underneath one, the job fails and is
looked at instead of picking a side on its own. `git rebase --abort` stays, because it is
what makes the retries real, and `cancel-in-progress: false` stays for the reason it was
added.

Checked against a reproduction, five ways: a stale event SHA starts the job on the old
commit while `ref: main` starts it on the current tip; a non-conflicting concurrent human
commit rebases and pushes cleanly with both changes intact; a conflicting one fails with
the human change still on `main`; a tree left wedged by an earlier conflict is cleared by
the abort and the retry then pushes; and the commit step still precedes the
provider-failure gate, so a run that publishes pages and then finishes red still
publishes them.

Nothing was lost on the day: the sibling run published `8534b3c` and its data was as
fresh. The cost was a red run and, worth noting, **a failure that left no trace in the
repo** -- every committed log read `exit=0`, so `scripts/check_runs.py` had nothing to
find and a person had to notice the red badge. A run that dies before committing is
outside what reading committed logs can ever catch.

### The local half can now announce a failure (2026-08-30)
The cloud half has always announced its own: a provider that exits non-zero turns the
Actions run red and somebody sees it. Both of today's outages surfaced that way -- Joutsan
Kino's 403 and Savon Kinot's move off Vista, the second of which was noticed by a person
looking at a red run, not by anything in here.

The local half had nothing. It runs on a machine outside this repo, writes `exit=1` into
a provider's log, pushes it and carries on. Nothing is red anywhere, and the first symptom
is the health line going amber eight hours later, if someone happens to be on the site.
**Twenty of seventy venues ride on that half, seventeen of them Finnkino** -- so "no
signal" covered the largest provider in the app.

`scripts/check_runs.py` reads every committed `run*.log` and exits non-zero if any of them
did not end `exit=0`. `.github/workflows/logs.yml` runs it on any push that touches a log.

- **The commit is the transport, and that is the whole trick.** Both halves already push
  their logs here. Reading them on push gives the local half the same signal the cloud
  half gets for free, without touching the wrapper -- which lives outside this repo,
  cannot be tested from inside it, and is the one part of the pipeline no test covers.
  It also needed no change to `biorex.yml`, which has an unmerged branch against it.
- **A log with no `exit=` line fails too.** Every writer appends one, so its absence means
  the run died before it could or the file was truncated. Treating that as clean is how a
  half-written log passes for a healthy one.
- **The last `exit=` wins, not the first and not the final line.** Taking the first would
  report a run that recovered as failed; reading the final line would call a log
  unreadable the moment anything is printed after it, which reports a healthy run as
  broken. Both directions train people to ignore the check, which is the failure the
  deleted `fetch.yml` already caused by being permanently red.
- **A stale log counts.** `run-vista.log` sat at `exit=1` for hours today because its
  module had been retired and nothing overwrote it. That is exactly the state this should
  be loud about, and it was found by hand instead.
- Covered by `tests/test_check_runs.py`, verified by breaking each guard. Two of the four
  breaks initially went green against a test that could not tell the difference -- the
  test was rewritten until it could, which is the same lesson as the `not venues` clause
  earlier today.
- Not covered, deliberately: **staleness**. A log that says `exit=0` four days ago is a
  different problem, and the external ping on `data/areas.json` age is still open. This
  answers "did the last run fail", not "did a run happen".

### Savon Kinot names the venue inside its own room (2026-09-01)
Joensuu showed **`TAPIO | TAPIO 4`** beside a venue label that already said Tapio, on the
generated pages and in the app alike. Both print `aud` verbatim, and for the other sixteen
eTiketti sites that is right -- `aud` is the room as printed on the ticket. Savon Kinot is
the one that reports the venue and the room joined by a pipe, with the venue repeated in
the room half.

Measured before deciding anything: **127 of Savon Kinot's 157 showtimes carry a piped
`aud`**, across 11 distinct values and six venues. Every one of the 11:

| raw | venue | rendered |
|---|---|---|
| `TAPIO \| TAPIO 1..4` | Tapio Joensuu | `Sali Tapio 1..4` |
| `MAXIM \| MAXIM 1..3` | Maxim Varkaus | `Sali Maxim 1..3` |
| `KUVALIPAS \| KUVALIPAS` | Kuvalipas Iisalmi | *(empty)* |
| `KUVALINNA` | Kuvalinna Savonlinna | *(empty)* |
| `KILLA` | Killa Savonlinna | *(empty)* |
| `KINO-HOVI` | Kino-Hovi Kitee | *(empty)* |

**Empty for the single-screen houses is this family's own convention, not a decision taken
here.** Eight other eTiketti cinemas already publish `aud` as `""` -- Bio Grand, Bio
Grani, Bio Vuoksi, Ihme Kompleksi, Joutsan Kino, Kino Iiris, Kino Juha, K-Kino -- because
a room that is only the venue again says nothing the venue label has not said. Killa,
Kino-Hovi, Kuvalinna and Kuvalipas are all one screen, and three of them were already
sending the bare venue name with no pipe at all.

**The name stays with the number.** `Sali Tapio 4` rather than `Sali 4`, because a city
page lists four cinemas and a bare "Sali 4" identifies none of them. The casing comes from
the registry's `short`, so nothing in the parser has to decide how a Finnish name is
capitalised.

**Not a rule for eTiketti.** Leffabuumi pipes too -- `KINOLINNA | SALI 1`, 63 of its 78
showtimes -- and means something else by it: the right half is a real room name and the
left is which of its three buildings. Flattening that would leave rooms in different
houses all called SALI 1. So the normaliser is opt-in per site, `aud_repeats_venue`, set
on exactly one entry, and a test asserts the list of opted-in sites is exactly
`["savonkinot"]`. Fixed at the parser rather than in `index.html` or `build_pages.py`:
both consumers read the same field, and malformed presentation data should not reach
either of them.

An unrecognised room is returned unchanged rather than dropped, so a shape nobody
anticipated arrives on the page looking odd instead of disappearing.

**Operationally pending.** `run.py` takes a module, not a site, so refreshing Savon Kinot
alone would mean fetching all seventeen eTiketti hosts -- not a narrow refresh, and it
would fold sixteen providers' data churn into a parser fix. So no data was regenerated:
the committed `data/area-sk-*.json` still holds `TAPIO | TAPIO 4`, and the live site keeps
showing it until **the next cloud run replaces those files** -- `biorex.yml`, cron
02:30/06:30/10:30/14:30 UTC plus one dispatched after each local run. The parser change is
proved by 15 tests against the 11 real values; the data catching up is a scheduled event,
not something this commit did.

Verified by breaking it eight ways: the normaliser taken out of the emit (1 red), the flag
taken off the site (2), the flag added to Leffabuumi as well (3), the single-screen room
not emptied (1), the unpiped venue name not emptied (4), the number rewrite dropped (4),
the prefix built from the raw hall instead of `short`, which reproduces `Sali TAPIO 4` (9),
and an unrecognised room silently dropped (2).

**And a trap found on the way, which is its own defect and is not fixed here.** Adding this
test file with a plain `import etiketti` at the top turned three unrelated tests in
`test_empty_programme.py` red. The cause: provider modules do `from common import
EmptyProgramme`, which captures the class object at import time, and
`tests/test_common_fetch.py` calls `importlib.reload(common)` to get fresh throttle
counters -- which builds a *new* EmptyProgramme on the same module. A provider module
imported before that reload keeps the old class, so `assertRaises(common.EmptyProgramme)`
no longer catches what `fetch_site` raises, and `run.py`'s own handler stops recognising
it either, which is the third failure: a genuinely empty programme exits 1 instead of 0.

So the suite's result depends on **when a provider module is first imported**, and the
next test file that imports one at module level will hit this again. Worked around here by
importing inside a function, which is what the neighbouring test already does and is the
reason the suite was green before. The real fix is at the reload boundary and belongs in
its own change; this entry is where the next person finds out why.

### Savon Kinot left Vista for eTiketti (2026-08-30)
The cloud run went `exit=1` on `vista`: `HTTP Error 404` from `www.savonkinot.fi`. Not a
datacenter block and not a transient fault -- `/xml/TheatreAreas/`, `/xml/ScheduleDates/`
and `/xml/Events/` all answer **404 from an ordinary connection too**, while the site
itself serves 200. Fingerprinting the homepage found `etiketti.app` and
`/elokuvat/{id}/{slug}` links: they have migrated platforms.

So the fix was a `SITES` entry, not a parser. `etiketti.py` reads all six cinemas as they
are -- 17 films, 54 screenings, verified against the live site before the change and
again through `run.py` after it.

- **The venue ids are the ones `vista.py` used**, deliberately and byte-for-byte:
  `sk-tapio`, `sk-killa`, `sk-kuvalinna`, `sk-kuvalipas`, `sk-maxim`, `sk-kinohovi`. They
  key the saved home cinema in `localStorage` and every `/teatteri/` URL and JSON-LD
  address, so a rename would have silently wiped every Savon Kinot user's starred cinema
  and 404'd twelve indexed pages. Nothing about a platform migration requires new ids,
  and the diff was checked field by field rather than assumed.
- **This deployment is the Leffabuumi shape**: the *town* is the place and the cinema is
  in the room field, `JOENSUU | TAPIO | TAPIO 3`. `match` runs against the two joined, so
  it needed no adapter change. Tapio's four rooms and Maxim's three are rooms, not
  venues -- swept every film to be sure a seventh cinema was not hiding in one of them.
- **`vista.py` keeps its parser and loses its sites.** `SITES = []` rather than deleting
  the module: it works, several non-Finnish chains run the platform, and the endpoint
  shapes in its docstring are the research that identified it. `registry.modules()` no
  longer names it, so nothing runs it and the workflow loses a job step without being
  edited. `run.py vista` now finds no sites and exits 0, which is the routing change from
  earlier today doing its job.
- Worth reading next to the "Vista sweep -- tried and failed" entry above, which
  concluded Savon Kinot "looks like the only Finnish Vista deployment leaving the XML
  services open". That is now zero. A platform inventory is a snapshot, and this one
  lasted three days.
- **The failure surfaced the way it was designed to**: one provider red, everything else
  green and published, and the committed log naming the host and the status code. That is
  the whole argument for not letting a run be permanently red.
- **`run-vista.log` was deleted with the sites.** A retired module stops being run, so
  nothing overwrites its log, and the last thing it ever wrote was the 404 that retired
  it -- a file sitting at `exit=1` forever, in the one place a sweep for failures looks.
  A log is an artifact of a step that runs; when the step goes, the log goes with it.

### The Nexxo sweep: six cinemas, and two hosts that are not what they look like (2026-08-30)
Six more cinemas against the adapter that already served Kinoset. No new parser: 25
chains to 31, 64 venues to 70. Measured into a throwaway directory before committing --
**9 venues, 102 showtimes, 0 failures** across the module, Kinoset included.

Two of the ten hosts in the earlier probe are not separate cinemas, and both would have
published wrong data:

- **`ksek.fi` and `kinoaurora.fi` are one deployment.** Both answer locationid 1 with the
  same 33 showtimes and locationid 2 with the same 13, compared row by row and identical.
  The earlier entry listed them as two live hosts with 40 shows each, which double-counted
  one operator; adding both would have published every showtime twice under two chain
  names, in the same city, with two accents. **A distinct domain is not a distinct
  cinema**, and the cheap check is to compare the payloads rather than the host list.
- **`kinohirvi.fi` serves Bio Säde on locationid 4**, in Mänttä, 80 km from Kino Hirvi in
  Äänekoski. `biosade.fi` -- one of the four hosts recorded as answering with zero shows --
  is that cinema's own domain, serving an empty programme while its schedule is published
  on someone else's host. So "the site is empty" and "the cinema has no programme" are not
  the same statement either. Kino Hirvi and Bio Säde are two registry entries reading one
  host, because the picker has to name each cinema and they are in different towns.

Both are the same mistake in different clothes: **the host list was treated as the venue
list.** Ids were discovered by asking the endpoint, never assumed, which is how the id-4
cinema turned up at all.

- **Orange was the intuitive accent for a cinema called Aurora and measures 4.7 dE00
  against Finnkino's**, in Jyväskylä, where they share a city. Indigo instead, at 63.7.
  That is the second time in one day the obvious colour was the one the script rejected.
- **`book="reserve"` for all six**, as for Kinoset: Nexxo publishes no per-show booking
  URL, so a showtime opens the programme page filtered to that location.
- **`common.EmptyProgramme` is raised here too**, and this is the adapter it was written
  for: `biojukola.fi`, `biosalo.fi` and `biostara.fi` answer `public_api.php` with valid
  JSON and no shows at any id, permanently. The guard is that *every* locationid answered
  -- if a request failed we do not know what the site holds, so that stays a failure.
  None of the three is added: a site that has never published a show is not evidence the
  parser works.

**Deferred, and it is real coverage: Kino Metso.** `kinoaurora.fi` locationid 2 is a
touring operation whose `roomTitle` values are *towns* -- Muurame, Petäjävesi, Riihivuori,
Vaajakoski -- not screens, 13 showtimes across them. The adapter maps one locationid to
one venue, so taking it as it stands would file four towns' screenings under a single
venue in a single city, which is worse than not having them. Doing it properly needs the
room-splitting `match` that `etiketti.py` already has, plus a decision on whether
Riihivuori is a venue and whether Vaajakoski should read as Jyväskylä. Worth doing; not
worth guessing at the end of a sweep. **Done 2026-08-31 -- see "Kino Metso: five towns
on one locationid" below.**

### Kino Metso: five towns on one locationid (2026-08-31)
KSEK's touring cinema, added as four venues that share `kinoaurora.fi` locationid 2. A
venue entry now takes a `rooms` list of roomIds it owns; `fetch_site` fetches each
locationid once and parses it per venue, so four venues cost one request. 13 showtimes
in the 21-day window on the day it landed.

- **Its real home is ksek.fi, not kinoaurora.fi.** `ksek.fi/kino-metso/{town}/` exists
  per town and each page filters the plugin by the same roomId the API reports --
  verified 200 with showlist markup for every town before anything was written into
  `SITES` (the rule the dead-link fix earned). So the site entry carries `site`
  (ksek.fi, where a person goes) beside `base` (kinoaurora.fi, where the API lives),
  and a venue with a `page` links straight to its own town's page with no query.
- **Matching is on `roomId`, never `roomTitle`**: the ids are what KSEK's own pages
  filter on (Muurame 2, Petäjävesi 4, Tikkakoski 11, Vaajakoski 12, Riihivuori 21,
  Hankasalmi 19), and a title is one wording change from silently dropping a town.
- **Riihivuori folds into Muurame.** It is a resort hill in Muurame municipality and
  KSEK's own site gives it no page; the room name stays visible in `aud`, so a
  Riihivuori screening still says where it is.
- **Vaajakoski and Tikkakoski read as Jyväskylä** -- they are districts of it, so they
  join the combined city view beside Finnkino and Kino Aurora, which is where a
  Jyväskylä reader would look for them.
- **Hankasalmi and Laukaa are not added**: pages exist, programme does not, and a venue
  that has never published a show proves nothing about the parser. Rows no venue owns
  are printed loudly -- `unclaimed room {id} "{title}": N showtime(s) not published` --
  which is also how a new town announces itself: Tikkakoski appeared between two probes
  of the same endpoint.
- **Accent `#227D63`**, measured with `accent_check.py --candidate` against Muurame,
  Petäjävesi and Jyväskylä: worst same-city deutan pair 26.9 dE00 (against Finnkino and
  Kino Aurora in Jyväskylä), L* 46.9. Eight candidates measured; the intuitive olive of
  a forest bird scored 6.3 and lost, again.
- Covered by `tests/test_nexxo_rooms.py`, each guard verified by breaking it: the room
  filter, id-not-title matching, the per-venue page link and the unclaimed counter all
  go red. Two test traps surfaced on the way. The empty-programme tests patched
  `fetch_venue`, which the one-fetch-per-locationid change no longer calls -- the
  monkeypatch silently stopped intercepting and the tests spent minutes backing off
  against a fake host; they now patch `fetch_payload`, the seam that exists. And
  `test_common_fetch`'s `importlib.reload(common)` rebinds `EmptyProgramme` in place,
  so an adapter that from-imports the class at discovery time raises an object the
  reloaded test no longer recognises -- nexxo now references it through the module,
  which is identical in production and one identity under reload.

### The Nexxo sweep shipped six dead ticket links (2026-08-31)
A reader reported it from Järvelä: the show was real, the ticket link 404'd. The sweep
above measured the *data* -- 9 venues, 102 showtimes, ids asked from the endpoint -- and
copied Kinoset's `programme: "/ohjelmisto/"` onto every site without fetching it once.
Only Kinoset has that page. Every other site 404'd on it, so every showtime link for six
of the seven Nexxo providers was dead from the day they landed. The API endpoint is the
platform's and identical everywhere; the visitor-facing page is each site's WordPress
and named whatever its owner chose.

The paths, each verified live for the plugin's `nexxo_showlist`/`nexxo_reservations`
markup before being written down: Kino Aurora and Kino Olympia `/naytokset/`, Kino
Marilyn `/esitysajat/`, Järvelän Kino `/naytoslista/`, Kino Hirvi and Bio Säde the
front page.

- **Bio Säde needed a second base.** The sweep entry recorded biosade.fi as "serving an
  empty programme", and its *API* does answer empty at every id -- but its front page
  renders the location-4 schedule by calling kinohirvi.fi's API from the browser. So
  the SITES entry now carries `site` (where a person is sent, biosade.fi) beside `base`
  (where the API lives, kinohirvi.fi). A host list still is not a venue list, and it is
  not a landing-page list either.
- **The check that was missing costs one request per site**: fetch the built URL,
  expect 200 and the showlist markup. Do it before trusting any new `SITES` entry; no
  offline test can hold this, because the path is right until a webmaster renames a
  page.
- The data files carry the old URLs until a cloud run rewrites them, so the fix was
  followed by a dispatch rather than a wait for the cron.

### A quiet week is not a broken parser (2026-08-30)
"A whole site parsing zero showtimes fails the run" is what catches a parse that broke
silently and would otherwise leave old data ageing with nothing to say so. It also meant
a cinema with nothing on this week turned the whole run red, and after the eTiketti sweep
that stopped being hypothetical: **eight sites here are a single small venue**, K-Kino
publishing 3 showtimes and Kino Saimaa 2. Joutsan Kino had just demonstrated the shape of
it -- one site red, `exit=1`, everything else green and published.

The line is drawn where an adapter knows something `run.py` cannot: **what the listing
said**. `common.EmptyProgramme` may be raised only after a listing was fetched and parsed
successfully and held no films. A listing that still lists films while the parse yields
no showtimes is a broken parser wearing the same clothes, and keeps failing.

- **No per-site "allow empty" flag, deliberately.** The obvious design is a boolean on
  the `SITES` entry. It would switch the check off permanently for the one site most
  likely to need it, which is the hole this was meant to close rather than widen. The
  question is answered per run, from what the cinema published that day.
- **An empty site still writes no `venues-{provider}.json`.** Nothing is stamped fresh
  for a site that produced nothing, so the health line ages honestly rather than going
  green on an empty answer. A cinema that is quiet for a fortnight therefore still turns
  amber -- a soft signal that wants a look, instead of a hard failure that stops a run
  which had nothing else wrong with it.
- **Previously published data is kept.** The discriminator can be wrong: a site that
  changes its markup so film links stop matching looks exactly like one with nothing on.
  Keeping the last good file is what makes being wrong survivable, and it is asserted.
- The log line is deliberately noisy -- `[provider] no programme published: ...` -- and
  the run summary counts them. A cinema empty for weeks is worth chasing even though no
  run went red over it.
- Covered by `tests/test_empty_programme.py`. The tests that matter are the ones that
  keep something failing: a listing with films and no showtimes, and a fetch error.
  Verified by breaking each guard.
- **One break did not go red, and that was worth knowing.** Removing `not venues` from
  the exit condition changed nothing, because an all-empty site is already counted by
  `if not v: failures += 1` earlier in `main`. What that clause actually guards now is
  the case site-level routing created -- a module with no sites for this half -- which
  had no test until the break said so. `run.py biorex --half local` has nothing to do
  and must exit 0, not fail.
- Only `etiketti` raises it so far. Nexxo is where it lands next: four of its hosts
  answer `public_api.php` with valid JSON and zero shows, which is this case exactly, and
  they should not be added before the adapter can say so.

### Routing is per site, not per module (2026-08-30)
`where` on a registry entry used to decide which half fetched a whole *adapter*. One
cinema that can only be read from an ordinary connection therefore dragged its entire
platform with it: marking a single eTiketti provider local would have put all sixteen
sites in both halves, two writers racing on the same `data/venues-*.json`. That is why
Joutsan Kino was deleted rather than moved, and deleting it was the wrong answer -- an
infrastructure limit turned into a cinema the app stopped listing, when the parser and
the site were both fine.

`run.py` now filters `SITES` by each site's provider `where`, so a module can be split
across the two halves.

- **The half is derived, not passed, and that is the point.** The cloud workflow calls
  `run.py <module>` with a bare name; requiring a flag would have meant editing
  `biorex.yml`, which has an unmerged branch against it. Actions always sets
  `GITHUB_ACTIONS` and nothing else here does, so the workflow keeps working untouched
  and simply stops fetching the site it could never reach.
- **Off Actions the default is `all`, not `local`.** `run.py etiketti` on a laptop is how
  an adapter gets exercised; defaulting to the local half would have fetched one site of
  sixteen and looked exactly like a broken parser. The local *wrapper* has to say
  `--where local`, which is also what keeps one writer per provider file.
- **A site whose provider has no registry entry is kept in both halves.** Dropping it
  would turn a misconfiguration into a cinema that silently stops being fetched;
  `tests/test_registry_sites.py` is what reports it.
- Two properties are asserted against the live registry in `tests/test_run_routing.py`,
  because a fixture cannot go stale in the way that matters: the halves are **disjoint**,
  so no provider file has two writers, and they are **complete**, so routing cannot drop
  a cinema the way the module-level scheme just did. Verified by breaking each guard.
- **The argument parse was wrong and only running it showed that.** `run.py etiketti
  --half local` took `local` for a module name, tried to import it, logged
  `[local] unusable: No module named 'local'`, counted a failure and printed the word in
  the summary. A flag's value is not a positional argument. `module_names()` now knows
  that and is tested; the earlier version passed every test that existed at the time.
- **The wrapper needs one line for this to run.** `where="local"` only routes a site --
  something still has to call the local half for the eTiketti module. If the wrapper
  invokes bare module names it never reaches `etiketti`, and Joutsan Kino publishes
  nothing while the registry declares it, which is the health line's "unavailable" state.
  `run.py --where local` covers every local site in one call, which is why that form
  exists.

Joutsan Kino was fetched from an ordinary connection and its data committed alongside
this change, so the restored chain publishes immediately rather than waiting on the
wrapper. Its two posters stay hot-linked until a cloud run mirrors them -- `mirror_posters`
works from committed data regardless of which half fetched it -- so those films render
placeholder tiles until then, which `build_pages` warns about by name.

### Measuring when cinemas publish (2026-08-30)
The polling slots should follow the providers' publication rhythm and nobody knows what it
is. `scripts/poll_windows.py` reads only committed data -- no network -- and walks every
pair of consecutive data commits, reporting when new schedule data first became visible.

**It exists because its first three runs disagreed with each other.** Over one unchanged
history it reported 125 arrivals, then 20, then 4; the entire difference was its own bugs.
A number that moves 30x under its author is not evidence, and the slots were going to be
set from it. All four are now fixtures in `tests/test_poll_windows.py`:

- **ISO strings are not comparable across offsets.** The local half commits `+03:00` and
  the runner commits `+00:00`, so `"...T17:20:00+03:00" > "...T15:16:40+00:00"` is true
  lexically and false in real time -- 17:20 EEST is 14:20 UTC, an hour *before* that
  commit. Sixteen Gilda "arrivals" came out of two byte-identical files. Starts are epoch
  seconds now.
- **The weekday was the committer's, not the cinema's.** A cloud commit at 23:30 UTC is
  02:30 the next day in Helsinki, filed under the wrong day -- and the weekday is the whole
  output. Everything is normalised to `Europe/Helsinki`.
- **An adapter commit usually touches no data file**, so checking the data commit alone
  missed every one. The Orion parser landing between two cloud runs read as Orion
  publishing 27 screenings. The check is now over the whole range since the previous
  observation.
- **A venue whose file is momentarily empty names no provider**, because the provider id
  lives on the shows; it dropped out of the provider's state and stopped `seen` advancing,
  so the next window was measured against a stale observation. Venues are attributed
  globally now -- which then silently stopped first-population being flagged, since the
  venue was no longer *missing*, so that is tracked explicitly.

**First-seen titles are the weakest signal and are deliberately secondary.** A cinema
opening next week's dates for films already showing publishes real news and introduces no
title at all. The primary measure is future screenings added between consecutive
observations, keyed `venue + title + start + aud`, plus horizon extension.

**Every row is an observation window, never a publication time.** It reports
`(previous observation, this one]` in full, because the event is only known to fall
somewhere inside it. That window can never be narrower than the polling interval it is
meant to inform, which is the ceiling on what this can ever say -- read the weekday long
before the hour.

As of 2026-08-30 it reports **9 organic arrivals over 4.4 days**, which is far too few to
set anything by. The history has to accumulate first; the data is committed anyway, so it
costs nothing to wait.

### Finnkino publishes weekly, Tuesday ~15:00 -- their own statement (2026-09-01)

Finnkino's site: the new programme, covering Friday through the following Thursday, goes
on sale no later than about 15:00 on Tuesdays; a holiday early in the week can push it,
usually by one day; special cases sell earlier. Their words, not a measurement -- but the
committed data on the morning of Tue 2026-09-01, before that day's drop, matched it
exactly and explains a number that otherwise reads as a broken fetch:

    Finnkino, most venues      horizon 2026-09-03    2 days out
    Finnkino 1101 / 1100       horizon 09-06 / 09-07 the "special cases" selling early
    twelve non-Finnkino venues horizon 2026-09-30    29 days out
    eTiketti tail              out to 2026-12-20

The previous drop (Tue 08-25) covered Fri 08-28 -> Thu 09-03, and 09-03 is precisely
where the horizon sat. **A 2-day Finnkino horizon next to a 29-day small-cinema horizon
is not the pipeline under-fetching; it is Finnkino not having sold the weekend yet.**
The prediction this makes is falsifiable within hours: after ~15:00 on a normal Tuesday
the Finnkino horizons should jump a week (09-03 -> 09-10 on this one). If a Tuesday
passes without the jump, either the week is holiday-shifted or the statement has gone
stale and needs re-reading at the source.

Two things this changes about reading the measurements above:

- **For the weekly drop, read the showtime-count signal, not horizon.** `horizon` is the
  furthest future start, so a single advance-sale screening drags it -- it moved 09-01 ->
  09-02 -> 09-03 -> 09-05 on consecutive days while the weekly model was sitting still.
- **The Tuesday drop is the single highest-value data event of the week**, and with four
  local slots a day it can sit unfetched for hours: a Tuesday-afternoon visitor asking
  about the weekend is told it is not published when it is. That argues for a local slot
  shortly after 15:00 Helsinki on Tuesdays (and Wednesdays, per the holiday caveat) --
  **deliberately not done yet.** One chain's policy page plus one observed Tuesday is a
  sample of one, and the rule here is that slots come from measurement: revisit after
  poll_windows has two or three clean Tuesdays in view. Finnkino is local-only, so any
  new slot lands in the out-of-repo wrapper, not in anything this repo's tests can hold.

Deliberately **not** surfaced in the UI: turning "ohjelmistoa ei ole vielä julkaistu"
into "weekend showtimes appear Tuesday at 15" would promise one chain's policy on behalf
of all 32, the policy shifts on holidays and breaks on special cases by Finnkino's own
telling, and nothing in the pipeline would notice the policy page changing. A promise
the app cannot verify is worse than no promise.

## Access and ethics

- Every provider is read through the same public interface its own site uses, on a
  schedule no visitor can influence, and every showtime links back to the cinema's own
  page. **The traffic-independence is guaranteed; the cadence is not.** The client reads
  static JSON from this origin and never calls a cinema, so no amount of browsing produces
  a single request -- that holds by construction, and it is the part worth promising.
  The count holds by nothing. Normal configured cadence is four runs a day for the local
  three, and for the cloud eight a four-times-daily cron *plus* one run after every local
  run, since `dispatch_cloud.sh` fires the same workflow and the `concurrency` group
  queues rather than merges -- usually up to eight. It is not a bound in either direction:
  `workflow_dispatch` stays callable by hand or by API and can push it higher, and
  scheduled execution is best-effort and may be delayed or missed, which can put it lower.
  This said "four times a day regardless of traffic" until 2026-08-30, which was true of
  the local half and had never been true of the cloud half. Two corrections went into the
  replacement before it landed: the first draft printed "four to eight a day" as if it
  were enforced, when nothing caps a manual dispatch, and it claimed GitHub "skips runs"
  on evidence that only showed missing *data commits* -- and a run that changes no data
  makes no commit, which this same document records elsewhere. A promise to a cinema has
  to be one the configuration keeps, and a measurement has to be of the thing claimed.
- Datacenter-IP blocks are a deliberate access control. Reading a site from an ordinary
  browser on an ordinary connection is fine; residential proxies, fingerprint spoofing and
  probing third-party auth with credentials that were never issued are not, and none of
  those are used here.
- Booking, payment and administrative endpoints are never called, and this file does not
  inventory them.
- **Never commit a raw probe dump** (learned the hard way 2026-08-27). A dump of a third
  party's page carries whatever they ship to visitors: `probe/rv-films.html` contained
  rivieracinemas.fi's Google Maps JS key, which tripped GitHub secret scanning on this
  repo. That key is public by design — Maps JS keys are visible in every visitor's page
  source and are protected by HTTP-referrer restriction rather than secrecy — so there was
  nothing to rotate, and it was never ours to revoke. Mirroring someone else's credential
  into a public repo under your own name is still bad hygiene, and an alert queue full of
  other people's keys teaches you to ignore alerts. Probe, read the answer, write the
  *finding* here, commit nothing raw. `.gitignore` now blocks `probe/` and `probe-*`.
- If a cinema would rather not be included, the adapter comes out: one registry entry.
- **What the visitor's browser gives away is our problem too**, and the README used to
  claim "nothing leaves the device" and "no third-party requests". Neither was true: the
  typeface comes from Google Fonts on every load, and 1523 of 4279 posters (36%, counted
  2026-08-28) are hot-linked from the cinemas' own CDNs and `image.tmdb.org`, so those
  hosts see a visitor's IP. `referrerpolicy="no-referrer"` on every `<img>` keeps the page
  URL out of it, which is the one part that was already right. The README now states this
  plainly instead. Closing it means self-hosting the font and the remaining posters, the
  way MX posters are already mirrored into `data/posters/`. Until that is done, the
  README states the problem instead of hiding it.

### Posters are mirrored (2026-08-29)
`scripts/providers/mirror_posters.py` runs after enrichment and before `build_pages`,
downloads every hot-linked poster into `data/posters/` and rewrites the `img` reference
on each show and in `films-extra.json`. Half of the third-party-request problem the
README documents is now closed; the Google Fonts request is not.

- **The count was wrong by an order of magnitude, in our favour.** "1523 of 4279 posters"
  counted *references*, not files: one film's poster is repeated across every showtime it
  has. Measured on 2026-08-29 the data holds **194 distinct remote URLs** (147 on shows,
  the rest TMDB addresses reachable only through `films-extra.json`) against 3494
  references. So this was a ~5 MB job and had been written down as a ~35 MB one. Same
  lesson as the city count: measure against the data before writing a number.
- **Everything is downscaled to 342 px wide.** The sources are not comparable: TMDB serves
  w342 at ~25 kB, MyCloudCinema publishes only 1080, and Nexxo and Kino Akseli serve the
  distributor's key art at 1984x2835. Mirroring verbatim would have put tens of megabytes
  of image into a 4 MB repo to render a tile about 130 px wide on a phone. 342 is what
  TMDB already serves and what the client renders from. Pillow is installed in the
  workflow for this and for nothing else.
- **Named by `sha1(url)[:16]`.** Seven hosts with no id namespace in common; the URL is
  the only thing that identifies a poster across all of them. The existing MX mirror keys
  on the release id and keeps its own naming.
- **A failure is logged and left hot-linked.** `tries=2` keeps a permanent failure cheap.
  Nothing here is allowed to fail the build: a third party's uptime must not be able to
  stop the pipeline publishing showtimes.
- **Kino Akseli's posters mirror fine from a runner**, which I predicted they would not.
  The datacenter-IP challenge is on `kinoakseli.fi`'s pages, and its
  `wp-content/uploads/` path served all six to Actions without complaint. Worth
  remembering generally: "the site blocks datacenter IPs" is a claim about the endpoint
  that was tested, not about the host.
- **Nexxo publishes filenames containing spaces**, and urllib rejects those as control
  characters instead of encoding them, so one poster failed the first live run. `fetch`
  now goes through `request_url()`, which percent-encodes path and query. The cache key
  stays the **published** URL, since that is what the reference in the JSON says; keying
  on the encoded form would rename every poster the day the encoder changes.
- Knock-on effect worth expecting once: `build_pages` renders same-origin posters only, so
  the first run after this rewrites nearly every page as the `<img>` tags appear.
- Open: nothing prunes a poster once its film stops screening, so the directory grows by
  roughly the number of new releases forever. At ~20 new films a week that is a few MB a
  year, which is worth a sweep eventually and not worth state now.
- **Mirroring collided with `robots.txt`** (caught 2026-08-29, same day). `/data/` is
  disallowed because it is the app's machine payload and crawling it only spends budget.
  The moment posters moved there, every `<img>` and every JSON-LD `image` on the
  generated pages pointed at a path Googlebot may not fetch, and an unfetchable image is
  exactly what made `workPresented` invalid in the first place. `Allow: /data/posters/`
  now overrides it, since the longer rule wins. Moving an asset onto this origin is not
  finished until the crawler can still reach it.

### The webfont is self-hosted (2026-08-29)
`fonts/archivo-latin.woff2` (90 kB) and `fonts/archivo-latin-ext.woff2` (86 kB), with the
`@font-face` rules inlined in `index.html`. Google Fonts saw every visitor's IP on every
load and was the last third-party request on this origin. **The README's "no third-party
requests" claim is now true**, which it has not been at any earlier point it was written.

- The same two subsets Google serves a modern browser, with **their unicode-ranges kept
  verbatim**, so latin-ext is still only fetched by a page that needs it. Dropping the
  ranges and shipping one file would have made every visitor download 86 kB of accented
  Latin they never render.
- Only **latin** is preloaded. It covers Finnish and Swedish; preloading both would pull
  the subset most visitors never use.
- The subsets came from a throwaway workflow, since the sandbox cannot reach
  fonts.gstatic.com and Google serves woff2 only to a browser user-agent. Workflow deleted
  in the same commit that used its output, the same rule as any other probe.
- Licence in `fonts/OFL.txt`, from **Omnibus-Type/Archivo**, the upstream author.
  `googlefonts/archivo` has no OFL.txt at that path and the first attempt committed a
  14-byte "404: Not Found" as a licence file. Check the size of anything fetched blind.
- **A font is not a poster.** No pruning question here: two files, replaced only if the
  family changes.
