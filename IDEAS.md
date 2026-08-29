# Kino — Improvement Ideas

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
- [x] TMDB **posters** for providers that publish none, written onto each show by the
      pipeline so the client needed no change
- [x] Chain key in combined views doubles as a **quick filter**, and it is **additive**:
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
- [x] Language meta reads **"englanti · tekstit suomi/ruotsi"**: the audio language bare,
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
  own log, and `set -e` resumes only afterwards. So a Kino Akseli failure **cannot**
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
- Scheduled locally four times a day. **There is no cloud fallback, deliberately.**
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
| Finnkino | 17 | short-lived token | Local (blocks datacenter IPs) | full, seats |
| BioRex | 12 | none | Actions | no runtime/genres/seats |
| Kinoset (Nexxo) | 3 | none | Actions | prices, duration, genres |
| Kotkan Leffat (eTiketti) | 2 | none | Actions | prices, duration, **seats** |
| Riviera | 2 | none | Actions | seats, duration, 24-date horizon |
| Savon Kinot (Vista) | 6 | none | Actions | fullest feed: original title, ISO langs, posters, deep links |
| Cinema Orion | 1 | none | Actions | ticket-type prices, own Finnish blurbs; no seats, runtimes or age limits |
| Gilda (MyCloudCinema) | 2 | none | Actions | posters, own synopses, formats; no seats or deep links |
| Kino Akseli | 1 | none | Local (blocks datacenter IPs) | prices, no booking links |

Ratings and trailers come from the shared TMDB enrichment pass, so only Finnkino and
Kotkan Leffat still differ in what the source itself provides (seat availability).

46 venues / 31 cities across nine providers. Each provider writes `data/area-{venueId}.json` in one shape
(`{generated, dates, horizon, shows[]}`) plus `data/venues-{provider}.json`
(`{id, name, short, city}`). Finnkino still uses `data/areas.json` with numeric ids.
Adding a provider to the frontend is now **nothing**: a registry entry generates
`data/providers.json`, and the client derives every label, host, accent and footer verb
from it.

Conventions worth keeping:
- **An age limit can belong to the screening, not the film.** A licensed bar auditorium
  admits 18+ whatever the film is rated: BioRex sells K-12 films into `Anniskelu`
  screenings, and at Seinäjoki states it in the room name itself ("2 REX (K-18)"). So
  `age` is a per-show field, separate from `rating`, set from an explicit `(K-nn)` in the
  auditorium name first and inferred from the Anniskelu tag otherwise. The client renders
  it on the **showtime stub**, which is the thing you tap to book, and suppresses it when
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
  colour is no longer load-bearing. Keeping it on then has value: a palette only becomes
  learnable if it is always present, and the app looks better for it. The **legend** keeps
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
  appears on S-rated films too, so the 18+ marking belongs to the **screening** and is
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
  from a BioRex one. The old palette had three warm chains in Helsinki: Finnkino vs Gilda
  measured ΔE 25.9, and Finnkino vs BioRex measured **5.0 under deuteranopia** — the same
  colour, in Helsinki, Espoo and Tampere. So BioRex left its own gold for blue and Gilda
  left brick red for magenta, and Kino Akseli took the vacated gold: it is a single-screen
  house in Nummela and never appears in a combined city view, so it cannot clash there.
  Worst same-city pair is now ΔE 46.9 normal, 28.0 deutan; global minimum 32.1. Kotka's
  colourblind figure fell slightly (28.7 -> 24.8) because crimson sits near orange for a
  deuteranope; pushing Kotkan Leffat to pink would fix that pair and collide with Gilda's
  magenta everywhere else, and Kotka only ever shows two chains. Nine chains cannot all be
  mutually distinct under colourblind vision while staying this side of neon, so the target
  is per-city separation, not global. `scripts/providers/registry.py` carries the numbers.
- A failed venue writes **no file**, keeping previous data rather than publishing empty
- Verify the response belongs to the venue you asked for (see the BioRex cookie note)

### Combined city view (done)
- Dropdown gets `city:{name}` entries for cities with 2+ venues: Helsinki (11, five chains),
  Espoo (2), Tampere (2), Kotka (2).
- `loadCity()` fetches each venue file in parallel and folds them into one payload;
  `dates`/`horizon` are the union, `generated` the **oldest** so the stale banner reflects
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
- Dates are **sparse** (e.g. 27–31.8, 1–3.9, then 5.9, 9.9, 11–13.9, 30.9) — special
  events, not a rolling window. Scrape `#dayselect` options rather than generating dates.
  `<input type="date">` cannot disable individual days, so dimming unavailable dates
  would need a custom picker — deferred until BioRex is actually in.

Other Finnish aggregators exist (leffajat.fi, kinoon.fi) — useful as prior art for which
chains exist and how they present multi-cinema. Take data from the chains' own sources.

### Nexxo Scope — a *platform*, not a site (probed 2026-08-26)
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
- `Pe 28.08. klo 19:00` has **no year** — infer by keeping the date within roughly
  [today-45d, today+320d], otherwise January rolls over wrong
- `(dub.)` = Finnish audio; films showing `Näytösajat –` have no showtimes, skip them
- Gives price and genres; no runtime, auditorium or booking URL; ~3-day horizon

### eTiketti — a platform (probed 2026-08-26)
Kotkan Leffat runs **eTiketti** (etiketti.app). The API host
`{customer}.etiketti.app/api/yleiset/...` is **behind Cloudflare**, so the adapter reads
the cinema's own server-rendered pages instead. Another eTiketti cinema = a `SITES` entry
in `scripts/providers/etiketti.py`.

```
/elokuvat/ohjelmistossa      -> movie links /elokuvat/{id}/{slug}
/elokuvat/{id}/{slug}        -> every screening for that film
```

Per screening, inside `<div class="item ... date-D.M.YYYY">`:
- `date-27.8.2026` class carries the **full date including year**; time from `klo HH.MM`
- `TRIO 123 | VIP-SALI` — but **Kinopalatsi screenings have no room and no `|`**, so the
  room must be optional in the regex (this silently dropped 17 showtimes first time)
- `Lippu 18,00€` and `Vapaat paikat 13/22` -> price and real sold-out state
- Booking link `/salikartta?id=NNNN`
Film-level: `<h1>` title, `ikarajat/fi-16.svg` -> rating, `Kesto: 2 h 53 min` -> minutes,
`Kieli:` / `Tekstitys:` -> language tags, `<img class="poster-img">` -> poster.
Roughly 1 listing + ~15 movie pages per run, paced 1.2 s apart.
Kotka venues: Kinopalatsi (no rooms, ~236 seats), Trio 123 (SALI 1/2, VIP-SALI).

### Synopses and enrichment
`scripts/providers/enrich_tmdb.py` runs **last** in the cloud workflow and **merges** into
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
  matches. The **ids were right the whole time**; TMDB has registered Finnish titles and
  had matched them. The cost of the mistake was not a wrong film but a missing one:
  a weak entry gets no `tmdbId` and no `gids`, so 29 films were excluded from cross-chain
  merging and from genre-based filtering for no reason.
  `language` localizes the response, it does not widen which titles are searched, so this
  is presentation rather than matching — the fix is one query parameter, not 29 aliases.
  **Verify before writing aliases**: a "weak match" line is a claim about the comparison,
  not about the film.
### The score ring (2026-08-27)
The score is a ring: arc length for the glance, the number inside for the value, and the
**vote count beside it**, because 7.1 from 41 votes and 7.1 from 15 000 are not the same
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
- **Name merging stays load-bearing.** Merging by `tmdbId` only helps films where *both*
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
  search returned **nothing**, not when it returned the wrong thing. It now retries
  whenever the year produced no exact match, and never applies a year to an alias search
  string in the first place.
- **`fetch_data.py` needs candidate queries too** (2026-08-27). Two failures found in one
  local run: OCAPI's `originalTitle` is **empty** for some releases, so `q` arrived as
  "Autot (uudelleenjulkaisu)" and matched nothing at all; and "Mutiny - Lavastettu
  syylliseksi" matched *Mutiny* only weakly, so no `tmdbId` was written and the row could
  not merge with BioRex's "Mutiny" even though the pipeline had found the right film.
  `_queries()` now yields the de-noised title, the raw title, then the head before a
  **dash**. Never before a colon: that would search "Mission" for "Mission: Impossible -
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
Finnish. Both TMDB passes now keep the **genre ids** already present in the `/movie/{id}`
response they fetch for the synopsis — no extra requests in the cloud pass, one detail
call per film in `fetch_data.py`, cached after. Ids land on each show as `gids`;
`data/tmdb-genres.json` holds the id -> name map for `fi` and `en`, two requests per run.

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
  first non-empty field across the **filtered** set and the chains disagree: Finnkino
  publishes "Dokumentti, Kotimainen " (trailing space and all) for "Laula minulle Arja",
  Gilda "Dokumentti". With the filter on, Finnkino's subtitled screenings drop out and the
  card re-folded from Gilda. `tmdb`, `tr`, `img`, `len`, `genres`, `rating` and `original`
  now fold from the unfiltered set, and genres take the **longest** string rather than the
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
  slide through behind it. Day headings are **not** sticky: the legend wraps to two lines
  on narrow screens, so their offset would have to be measured at runtime rather than set
  in CSS, and a guessed value overlaps at some widths.
- **The times list needs the venue too** (2026-08-27). The film cards labelled the venue
  and tinted by chain in a combined view; `renderTimes()` did neither, so "Ajat" on Kaikki
  Helsinki showed "Sali 14" — a room in one of five cinemas, uncoloured, under a chain
  legend it had no connection to. The stub is a fixed 158 px ticket whose label column is
  about 75 px, so putting "Kinopalatsi · Sali 14" in it truncates to "Kinopalat…" and
  loses both halves. So the venue goes on the **meta line**, which has the full row width,
  as a `.theatre-tag` (a class that already existed and was unused), and the stub keeps the
  room name and gains the chain tint. Single-venue views are unchanged: there the bare room
  name is correct, because the cinema is the thing you picked.
- **English titles have to resolve through `_eid`** (2026-08-27). `disp()` looked up
  `films.json` (keyed by Finnkino's `filmId`) with the show's `eventId`, which in a
  combined city view is the cross-chain merge key, so English mode silently showed the
  Finnish title for **every** film in every combined view. `showSheet()` already dug the
  real id out of `_eid`; `disp()` now does the same through `filmEntry()`, which also
  scans the group's showtimes so a merged row finds the Finnkino member. Falls back to the
  show's `original` title, which a few providers publish (Savon Kinot) and which beats a
  Finnish distributor title in English mode.
- **Never translate `s.title` itself.** It is the key for `mergeKey()`, for `normTitle()`
  -> `films-extra.json`, for the TMDB title cache and for `tmdb-aliases.json`. Rewriting
  it would unmerge rows, orphan synopses and invalidate every alias key at once. English
  titles are a render-time substitution and nothing else.
- Still Finnish in English mode, by omission rather than design: **genres** are the
  provider's own strings, stored verbatim, so `Toiminta, Jännitys` shows for every
  provider including Finnkino. Fixing it means storing TMDB's genre list per language in
  the enrichment cache and choosing at render time. Also the film list sorts on
  `title.localeCompare`, so English mode keeps Finnish alphabetical order.
- **Merge on the union of both signals, never on one or the other** (2026-08-27). Keying
  by `tmdbId` *when present* and by title otherwise **unmerged** a pair that had worked:
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
- Aliases are keyed by the title **as each chain publishes it**, so one film can need
  several keys: `autot re release` (BioRex) and `autot uudelleenjulkaisu` (Finnkino) both
  map to the search string `Cars`, because "Autot" alone matched *Cars 3* by popularity.
- The two TMDB passes are still separate (`fetch_data.py` keyed by Finnkino `filmId` and
  run locally, `enrich_tmdb.py` keyed by normalised title and run in the cloud). They now
  agree on the rules — exact-match preference, `TMDB_MIN_VOTES` = `MIN_VOTES` = 25, `n`
  and `x` in both caches — but they still fetch at different times, so the same film can
  briefly carry two `vote_average` values. Merging by id hides that, because the merged
  row takes one show's rating. A single shared pass is the real fix and is not written.

### Riviera (added 2026-08-27)
WordPress admin-ajax, no auth, **one request covers both venues**:
```
POST /wp/wp-admin/admin-ajax.php
     action=filter_movies&date=&movie=&area=1040&singlemovie=&initial=1
-> {"success":true,"data":{"movies":"<ul class=movielist>…</ul>"}}
```
- `area` (1040 all / 1024 Kallio / 1039 Punavuori) is **ignored** by their backend, so the
  adapter splits on the `location` field ("Kallio, Sali 1") instead.
- Per `<li class="movielist__item single-show">`: `.date` ("To 27.8.2026"), `.time`,
  `.location`, `.movielist__item__title`, `Varatut paikat: 50/50`, `Kesto: 1 h 48 min`.
- Sold out = all seats taken **or** the button carries `disabled`.
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
- `nrOfDays=31` is honoured, so **one request per area** covers the whole published window
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
  - `SubtitleLanguage2` can carry a `Name` with an **empty** `ISOTwoLetterCode`, so fall
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
    unrated **blank** rather than guessing.
  - `screen_name` for Lasipalatsi is "Bio Rex Lasipalatsi (K-18)" — a venue door policy,
    not a film rating. Strip it or every show there looks adults-only.
  - `subtitle_lang` arrives three ways in the same feed: Finnish words ("suomi, ruotsi"),
    codes ("FI", "SE"), and "-" for none. `audio_lang` is always a code.
  - `description` is HTML **with entities**; strip tags then `html.unescape`, or the sheet
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
  fact that this cinema is **not** part of the BioRex chain, which the app also carries.
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
- `descrption` is the site's spelling, and the span inside it is **never closed**, so it
  is cut at whatever tag comes next rather than at a `</span>`. The blurb goes to `_syn`
  (5 merged on the first good run). It mixes screening notes ("Ensi-iltaelokuva,
  klubialennus.", guest names) into the synopsis; synmerge only fills an empty slot, so
  that is accepted rather than split.
- Attribute quoting is loose: `title ="Film"` has a space before the `=`, and the price
  cell is `13&nbsp;€`. Attribute regexes allow `\s*=\s*`, and `\s` matches `&nbsp;`
  once unescaped.
- The `price` cell's `title` attribute carries the **full ticket-type breakdown**, so a
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
  slug and the blurb. **And it has no posters** (probed 2026-08-27): `featured_media` is
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

  Three assumptions that were **wrong** and cost a detour, recorded so nobody repeats them:
  - ELKE's **"Rajapinnat"** page is not an API page. It means *interfaces between old and
    new media*: an arts programme about VR and interactive works.
  - The **`naytokset`** post type exists and answers 200, but returns an **empty list**.
    Registered route, no records. A route listing is not data.
  - **Kinola is not a platform win.** `tickets.cinemaorion.fi` answers 403 to datacenter
    IPs and `orion.kinola.ee` exposes only a Filament/Livewire admin login, whose
    screening pages render seats and prices client-side. Nothing to adapt, and not
    somewhere to go poking.

### Probed, not yet added (2026-08-27)
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
    local wrapper runs, and `localfetch.sh` has to call `run.py kinoakseli engel`.
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

### The cinema-list lead: nytleffaan.fi (2026-08-27, not yet probed)
`nytleffaan.fi/elokuvateatterit/` is a directory of every Finnish cinema, run by Suomen
Filmikamari (the industry umbrella body), which is exactly the **list of domains** the
Vista sweep has been blocked on — guessing 45 produced zero hits, and KAVI and SES render
their lists client-side. Worth probing: if the page yields names with links, the sweep for
`/xml/TheatreAreas/` becomes trivial and several chains could arrive at once.

Also the competitive picture, since it comes up when deciding what to claim on the site:
- **nytleffaan.fi** — industry-run, gets exhibitor data rather than scraping, claims every
  cinema in Finland. It **excludes** special screenings: event cinema (theatre, opera,
  sport) and **festival screenings**.
- **elokuviin.com** — claims all cinemas large and small, and does include festivals.
- **kinossa.fi** — same aggregation idea.

So **"Suomen kattavin" is not a defensible claim**: 46 venues against roughly 180-200
cinemas nationally, and two services already claim full coverage. What is true and
checkable: nine chains merged into one city view, festival and strand screenings included
where those services drop them, seat availability and prices where a cinema publishes
them, no ads and no tracking. Say the count ("9 ketjua, 46 teatteria, 31 kaupunkia") and
let it grow.

### Vista sweep — tried and failed (2026-08-27)
Guessed 45 plausible Finnish cinema domains and probed each for `/xml/TheatreAreas/`.
**Zero hits** beyond Savon Kinot itself. Also dead: account-level Azure blob enumeration
on the shared asset host (`mcswebsites...?comp=list` -> 404, though a *known* container
lists fine), and searching for the platform vendor's client list.

The blocker is a real list of Finnish cinema **domains**. KAVI, SES and NytLeffaan have
the cinema list but render it client-side or publish names without sites. Get that list
once and the sweep becomes trivial; until then, do not guess domains.

### Next providers
- **Sweep for more Vista sites first.** This is now the highest-value lead: an open
  `/xml/TheatreAreas/` makes a chain pure config. Finnish candidates worth testing:
  Kinopalatsi/Bio Rex operators outside the chains, Tampere's Niagara, Cinamon (Estonian
  Vista user), and any site whose URLs look like `/event/{id}/title/{slug}/` or
  `/websales/show/{id}/`, which is the Vista front-end signature.
- **Korttelikinot** (Helsinki: Orion, Riviera, Korjaamo, Regina) — they cooperate, so there
  may be a shared listing. Not yet probed.
- Search Finnish cinema sites for the `nexxo-scope` plugin path to enumerate the ones that
  come free with the existing adapter.
- **Eventio** is a ticketing platform with cinema customers — another possible platform win.
- Search Finnish cinema sites for `etiketti.app` (as well as `nexxo-scope`) to enumerate
  cinemas the existing two platform adapters already cover.
- ~196 cinemas / 306 screens in Finland (2009), but the tail clusters onto a few platforms.
  Platform adapters first; bespoke sites only when a cinema is on none.

## Hosting

- GitHub Pages, free. Custom domain **leffavuoro.fi** (Nordweb, 12 €/yr, renews 12 €/yr).
- DNS at Nordweb: four apex A records `185.199.108-111.153`, `www` CNAME -> `leffavuoro.fi.`
- `CNAME` file in the repo root holds the domain; Pages + Enforce HTTPS on.
- `.fi` cannot be bought from Traficom directly — always through an approved registrar.
  Watch for registrars bundling parking/DNS services: the same domain quoted 12 €, 20 € and
  73 € depending on what was silently attached.
- Old `shady-dev.github.io/kino/` now redirects. A PWA installed from the old origin keeps
  its own service worker, so reinstall after the domain change.

## Refactor to do before adding more providers

Adding a **venue** to an existing platform is already one line. Adding a **platform** costs
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
- [x] The cloud workflow **loops** over `registry.py --cloud`. Failure flag goes to
      `$RUNNER_TEMP`, never into a commit; `git add data run-*.log` replaced the explicit
      list (`run.log`, Finnkino's, does not match that glob). Data is committed *before*
      the failure check, so one dead provider still publishes the rest. The enrich gate
      also reads its exit code from `$RUNNER_TEMP` (2026-08-28): it used to
      `grep -q "exit=0"` over run-enrich.log, a substring search on a file that also
      carries arbitrary film titles and TMDB error text — the same class of silently
      passing check that hid breakage for days once before. The `exit=` line stays in
      the committed log for humans; the machine reads the temp file.
- [x] `riviera.py` is **parameterised by base URL** (`base`, `ajax`, `listing`, `area` on
      the site dict). It did not end up buying Gilda, but it is the right shape anyway.
- [x] **Repertory titles**: `clean()` in enrich_tmdb strips a trailing "(YYYY)", bracketed
      format noise ("(dub)", "(re-release)", "(liveaction)", 2D/3D/IMAX/4K), a trailing
      ", suomeksi", and a known-list event prefix. Exact list, not a `^\w+:` pattern,
      which would strip "Dyyni" from "Dyyni: Osa kolme". Only the **search string** is
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
- [ ] A whole site parsing **zero** showtimes fails the run (a single empty venue only
      logs). Watch for a legitimately empty site tripping it.
- [ ] **Repertory titles defeat the TMDB search**: "Trainspotting (1996)",
      "Vauvakino: La La Land", "KESÄKINO: Autofiktio", "BARNSÖNDAGAR: ..." all miss.
      `queries()` in enrich_tmdb.py should strip a trailing "(YYYY)" and known prefixes,
      the same way `mergeKey()` does in the client. Matters more as arthouse venues
      are added: Riviera and Orion are in, and Orion's first run supplied the live
      no-match list that `EVENT_PREFIXES` was extended from. Remaining misses are titles
      with no TMDB entry at all (music playback nights, shorts programmes), which is a
      `tmdb-aliases.json` job at best.

## Open — pipeline
- [x] **TMDB cannot be searched by Finnish distributor title.** Probed 2026-08-27:
      "Maailman rikkain nainen" gives 0 hits and `&language=fi-FI` also gives 0, while the
      original "La femme la plus riche du monde" gives exactly 1. `language` localises the
      *response* only; it does not widen the match, which covers original + English +
      registered alternative titles. Escape hatch: `scripts/providers/tmdb-aliases.json`,
      keyed by `norm()` of the published title, valued either a TMDB id (skips the search)
      or a replacement search string. `run-enrich.log` now names every title that found
      nothing, which is the input to that file. Wikidata (P4947 = TMDB id, matched on the
      Finnish label) is the automated version if this outgrows a hand list.
- [ ] **MovieXchange API credentials** — the real fix. Server-side client_credentials,
      programmatic refresh, no browser and no residential IP, so the whole pipeline
      could move back to Actions. Request drafted at moviexchange.com/request-api-access/
      — check whether it was ever sent / chase the reply.
- [ ] Move the local fetch off the laptop onto an always-on box on the same network.
      Cloud VMs are not an option for the two providers that block datacenter IPs.
- [x] Finnkino ratings whitelisted to `S` and `K-n` (2026-08-28). The OCAPI
      classification text passed through raw when it did not start with a digit, and the
      live values include "Tulossa" and "-" (verified in committed data: 5 and 7
      showtimes), which rendered inside the age-limit chip and silently failed every
      `rating ===` comparison. Same bug class as the Vista "K-7 (4)" gotcha. Anything
      else now blanks; "coming soon" is premiere-chip material, not a rating.
- [ ] Finnkino prices via the ticket-types endpoint (Kinoset + Akseli already show prices)
- [ ] Commit run.log only on failure (less commit noise)
- [x] Finnkino no longer publishes an **empty** area file when a venue returns no shows: it
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
      real on the Mac: localfetch.sh writes into the checked-out repo and the next run's
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
- [ ] Refresh TMDB rating on trailer re-check (currently the cached rating carries over,
      since reusing the movie id skips the search call)
- [ ] README workflow badge
- [ ] Credential hygiene and rotation: tracked in local private notes

### Ensi-illat: a badge, not a section (2026-08-27)
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

## Open — app
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
- [ ] **"K-18" quick filter**, the counterpart to "Lapsille". Must show only screenings
      that are *certainly* 18+, which is **not** the same as anniskelu: plain `Anniskelu`
      marks a licensed auditorium and sits on S- and K-7-rated films (460 Finnkino
      showtimes carry it). The rule is `rating === 'K-18' || age === 'K-18'` — the film's
      own classification, or a screening limit a cinema states outright (Finnkino's
      `Annisk_K18`, BioRex rooms named "(K-18)"). Never inferred from the Anniskelu tag;
      see the anniskelu entry under Synopses and enrichment for why that inference was
      removed. Note the two are independent: an S-rated film in a K18 anniskelunäytös
      qualifies, and a K-18 film in an ordinary room qualifies.
- [x] **Punctuation and spacing do not count in search.** Both the query and the haystack
      are reduced to letters and digits only, with diacritics folded, so "spiderman",
      "spider man" and "spider-man" are one search and "katyrit" finds "Kätyrit". Nobody
      types a hyphen in the right place. The spaced form is kept alongside the collapsed
      one, so a two-word query still behaves normally.
- [x] The placeholder example is **drawn from the day on screen** — the film with the most
      showtimes, shortened at the colon, so "Spider-Man: Brand New Day" suggests
      "Spider-Man". Costs nothing, never goes stale, and beats a hardcoded title that ages
      out with one schedule. Falls back to a plain description when no film repeats.
- [x] Placeholder teaches by example — "Etsi esim. Dyyni tai komedia" / "Search e.g. Dune
      or comedy" — because a description of the capability ("nimellä tai lajilla") is both
      clumsy in Finnish and easier to skip than an example. The `aria-label` stays an
      explicit description; only the visible text is the example. Pick a **franchise**
      rather than a current release if it ever needs changing, so it does not age out with
      one schedule.
- [x] Search box matches **genres as well as titles**, in both languages at once, so
      "comedy" finds a film the Finnish UI calls Komedia. Matched through the same
      id -> name maps the cards render from, with the provider's genre string as fallback
      for films TMDB never matched. The per-show haystack is memoised and cleared when the
      genre maps arrive, or a search typed during that fetch would match titles only.
- [ ] Genre / format filter **chips** (IMAX, LUXE, 2D/3D, genre) — the typed search covers
      genre now, so chips are about discovery rather than filtering: they show what is
      *available* tonight without having to guess a word.
- [ ] Sort toggle: title ↔ first showtime; hide/dim past showtimes option
- [ ] Tile/grid view mode (open questions: scan-by-poster vs time; showtimes on tile vs
      behind tap; auto-width vs manual toggle)
- [ ] Multi-cinema merged view (e.g. all Helsinki)
- [ ] Favorites (starred float to top)
- [ ] Prices "alkaen" probe (ticket-types endpoint)
- [ ] Light-mode polish + accessibility pass

## Ops
- [x] Per-provider health line in the app (⚠ past 8 h, from each `venues-*.json` generated)
- [ ] Staleness monitor (external ping on data/areas.json age)
- [x] The cloud workflow fails loudly if any provider exits non-zero, and now also if the
      push does not land (the retry loop used to swallow that)
- [x] The local half drives everything: it fetches Finnkino and Kino Akseli, pushes, then
      dispatches the cloud workflow. **GitHub cron did not fire for either workflow across
      four scheduled slots**, a known GitHub weakness rather than a config error; cron
      stays enabled as a bonus.
- [x] Verify the dispatch actually fires. It is the last step, after the push has already
      succeeded, so when it broke the run still looked healthy and only the seven cloud
      providers went stale. A cloud run should appear within a minute of each local run.
- [x] A provider parsing **zero** showtimes is now caught in the cloud: `run.py` writes no
      file, logs the venue by name, and exits non-zero, which fails the workflow. Before
      this, an empty parse silently left old data ageing.
- [ ] The local half still only records it. `run-kinoakseli.log` gets `exit=1` and the run
      continues by design (so Finnkino still publishes), but nothing actively flags it.
- [ ] Consider data branch to keep main history clean

## Documentation state (2026-08-27, sixth pass)

- `README.md` covers: Leffavuoro, **nine providers / 46 venues**, the two-location
  pipeline with **no cloud fallback for Finnkino**, the data shape every provider writes
  (including `age`, `gids` and `tmdbId`, and why the last two are exact-match only), the
  three lists worth reading in `run-enrich.log`, and a step-by-step for adding a provider.
  It went a full day stale during the Orion work — check it whenever the provider count,
  the file list or the show shape changes.
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
- The cloud workflow is **cron + dispatch only** with `cancel-in-progress: true`. It used to
  trigger on pushes to `scripts/providers/**`, which meant an adapter commit spawned a run
  that raced a manual dispatch; both regenerate the same files, so the loser could not
  rebase and the run went red for no real reason.
- A retry loop whose last command is `sleep` exits 0 even when every attempt failed. Set an
  explicit flag and `exit 1`, or the step goes green having done nothing.
- Small hosts rate-limit: Kinoset started answering 403 after repeated hits in one hour.
- **Every frontend bug today came from a field that only Finnkino ever populated**:
  `soldOut` (only Finnkino and Kotka have seats), `s.fi` (Finnish synopsis missing ->
  rendered blank instead of falling back to English), and a hash regex `m=([\w-]+)` that
  silently truncated ids containing spaces. When adding a provider, check field-presence
  assumptions in the client, not just the parser.
- `location.hash = ''` counts as navigating to the top of the document and scrolled the
  list up when the sheet closed. Use `history.replaceState` to strip the fragment.
- A helper defined as `def rep(a,b,t)` that raises before the file write, followed by a
  push, commits the file **unchanged** — two no-op commits (`755a39f`, `eeaa4e5`) came from
  exactly that. Write the file before pushing, and check the edit count.
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
- Adapters carry a referer, three retries with backoff, and a pause between venues.
## Crawlers and search

- State as of 2026-08-29: pages generated and committed, sitemap submitted, Rich Results
  Test clean on a city page (371 valid, 0 invalid: 10 Local business, 10 Organisation, 351
  Films). Remaining warnings are all optional fields -- `priceRange`, `telephone` and
  `image` on MovieTheater, `director` and `dateCreated` on Movie. None are in the pipeline;
  the first three would be manual data entry across 46 venues and `director` would need a
  per-film TMDB credits call. Deliberately not chased: optional fields do not gate
  eligibility, and the number that decides whether any of this worked is how many of the
  103 URLs turn up in Search Console's Pages report.

- `<head>` carries a description, canonical, OpenGraph and Twitter tags; `robots.txt` and
  a generated `sitemap.xml` exist (2026-08-28).
- **Pre-rendered pages, decided and built 2026-08-28**, superseding the note that deferred
  them. Markup does not create pages and the app is one JS-rendered URL, so
  `scripts/build_pages.py` renders 51 pages per language from the committed JSON at the end
  of every run: 46 venues plus the five multi-venue cities. Same data, no second fetcher.
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
  date window shifts.
- **Finnish city names are never inflected by the generator.** Helsinki -> Helsingissä,
  Tampere -> Tampereella: suffixing a case ending onto the nominative yields "Helsinkissä",
  which is precisely how a reader spots a generated page. Every string uses the nominative
  with a separator, which stays correct for whatever city a future provider brings.
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

## Access and ethics

- Every provider is read through the same public interface its own site uses, four times a
  day regardless of traffic, and every showtime links back to the cinema's own page.
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
  way MX posters are already mirrored into `data/posters/`; until that is done, an
  accurate README beats a flattering one.

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
  now overrides it, since the longer rule wins. Worth generalising: moving an asset onto
  this origin is not finished until the crawler can still reach it.

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
