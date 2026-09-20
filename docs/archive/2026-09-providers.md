# Archive: per-provider decisions, to 2026-09-14

Dated decision records moved out of `IDEAS.md` on 2026-09-15, so that file can be a short
index of open work rather than a 4,937-line history. Each entry is the record as it was
written, heading unchanged, so a reference that used to name a heading in `IDEAS.md`
resolves here against the same text. Everything here is closed: built, reversed, or
decided against, and the entry says which.

One section per provider or sweep: what was probed, what the adapter decided, the accent
and its measurement, and the first cloud run that settled `where`. What each ticketing
platform publishes is in [docs/research/ticketing-platforms.md](../research/ticketing-platforms.md);
the generic pipeline rules are in [2026-09-pipeline.md](2026-09-pipeline.md).

Active and deferred work is in [IDEAS.md](../../IDEAS.md). The accepted working rules are
in [CLAUDE.md](../../CLAUDE.md), the visual contract in [DESIGN.md](../../DESIGN.md), and
the investigations these decisions rest on under [docs/research/](../research/).

---

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

### Kino Akseli (probed 2026-08-26)
Single screen, Nummela, WordPress + Elementor, showtimes server-rendered in the page.
**Datacenter IPs are challenged, so this one runs locally.**
- Parse: iterate `<h2 class="elementor-heading-title"><a href=".../elokuva-...">`, then the
  nearest following `Näytösajat` paragraph; genres/age/price sit in the paragraph *before*
- `Pe 28.08. klo 19:00` has no year — infer by keeping the date within roughly
  [today-45d, today+320d], otherwise January rolls over wrong
- `(dub.)` = Finnish audio; films showing `Näytösajat –` have no showtimes, skip them
- Gives price and genres; no runtime, auditorium or booking URL; ~3-day horizon

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

### Riviera published the listing URL for every screening (2026-09-13)
All 94 showtimes carried `https://www.rivieracinemas.fi/elokuvat/`, the venue's listing page.
`parse` took the first `href` in the row and kept it only when it started with `http`, and the
ajax listing carries no `href` at all, so every screening fell back.

What it does carry, measured 2026-09-13: 94 items, 90 with `<button class="... show_tickets"
data-movieid="{id}">` in the action cell and 4 with a `disabled` button that has neither the
class nor the id. The theme's `app.8dae36.js` sets the ticket iframe to
`https://tickets.rivieracinemas.fi/websales/show/{data-movieid}` on that click, so the id is
the screening and that URL is where a visitor lands.

The film-page route is the same screening by another address:
`/Event/31766/?show=982926#tickets` and websales show 982926 are both the 14.9. 18:00 Odyssey
in Kallio. The film id it needs is in neither the listing markup nor the ajax payload, and
`movie-sitemap.xml` lists the Event URLs without titles, so building it would cost a film-page
fetch per film per run. The adapter publishes the button's URL instead, which costs nothing
beyond the one request it already makes.

`show_url()` reads the action cell only: an anchor wins if the theme ever ships one, resolved
with `urljoin` and unescaped so a relative href keeps its query and fragment; otherwise the
button's id against the site's `tickets` prefix; otherwise the listing. Scoping to the cell is
what stops a linked film title from answering for the screening, which is the shape the old
rule read. A sold-out row keeps the listing, because a `disabled` button carries no id and
there is nothing to sell.

Live run 2026-09-13: 94 showtimes, 90 with a websales URL, 4 sold-out rows on the listing. Two
opened in a browser and read against the parse: 982926 is The Odyssey, Ma 14.9. 18:00, Kallio
Sali 1; 983265 is Practical Magic: Lumotut sisaret, Ma 14.9. 17:00, Punavuori Sali 1. Nothing
was selected or bought, and the pipeline calls no booking endpoint: it reads the same listing
it always did and writes a link.

`tests/test_riviera_links.py`, 7 tests. Five mutations red, and all seven fail against the
parser they replace.

### Riviera prices come from the screening's ticket page (2026-09-13)
The `filter_movies` payload has no price field (94 rows, 2026-09-13). The public page a
showtime already links to, `tickets.rivieracinemas.fi/websales/show/{id}`, prints
`table.showPrices-table` with one row per ticket category; the ordinary seat is
"Sohvapaikka tai Nojatuolipaikka" (20,00 € on 982926, 22,00 € on 984518). Only that row
is the price: a restricted category first, the cheapest amount or the first euro on the
page never is, and no row or two rows with different amounts leaves the price "" (never
zero). Format is eTiketti's ("20€", "12.5€"), so the app and the pages render it as is.

Request policy (`scripts/providers/prices.py`, shared since the same day): one GET per
screening id after the schedule is parsed, sequential, 1 s apart, at most 40 pages a run
(`KINO_PRICE_MAX`), three consecutive failures end the pass. `data/prices-riviera.json`
holds `{id: {price, at}}`, pruned to the ids on the listing, rewritten only when it
changed; an id is re-read after 48 h (`KINO_PRICE_TTL_H`). Tradeoff: a price change reaches the site within two days,
and 90 screenings with an id (of 94 listed, 2026-09-13) cost about six pages a run in
steady state; a first fill takes three runs. Exercised once from an ordinary connection
with the ceiling at 6: six pages, six prices, 18 € to 49 €, zero failures. The page sends `Cache-Control: no-store` and a session cookie, so the HTTP
validator cache does not apply and no cookie is kept. A failed page is not cached and
the showtime is published without a price; the schedule cannot fail on this step.
Sold-out rows keep the listing URL and are not asked. `tests/test_riviera_prices.py`, 17
tests through fetch_site(); the shared loop is pinned in `tests/test_prices.py` (12
mutations red). First cloud run 2026-09-12 23:18 UTC: 90 screenings with an id of 94, 40
read, 40 priced, 0 failed, 50 deferred.

### Regina and Korjaamo prices come from their ticket pages too (2026-09-13)
Reported missing by the user on three venues where the browser shows a price.
- Kino Regina: KAVI's shop page a showtime links to lists categories as rows with a
  `<label>` and a schema.org `Offer`; "Peruslippu" is the ordinary ticket (10,00 € on the
  two probed screenings; KAVI-klubilaisten lippu and Lapsi are not). Regina is on the
  local half, so the wrapper's machine reads these pages, 137 screenings at 40 a run.
  `regina.ordinary_price`, `tests/test_regina_prices.py`, three mutations red. Exercised
  once with the ceiling at 3: two priced at 10 €, one page with no buybox (sales closed).
- Korjaamo Kino: Vista's websales "Select tickets" page lists `ticket-list__item`
  rows; categories are per screening with no fixed ordinary name ("HelAFF" on a festival
  screening), so restricted categories are dropped by name (wheelchair, concessions,
  members) and the rest must agree on one amount. `vista.ordinary_price`, the site's
  `tickets` prefix, `tests/test_vista_prices.py`, five mutations red. Exercised once from an
  ordinary connection with the ceiling at 3: two screenings, 13 € both.
- Kino Engel: the price rows are drawn by Johku's widget from an API that needs the
  widget's key; the 2026-08-29 decision above stands. Options left to the user: render the
  film page in a headless browser on the local half, or ask the cinema or Johku for a feed.
  Headless render measured 2026-09-13 on one film page from an ordinary connection: 6 s
  to a settled DOM, and the widget's own table carried date, time, hall and price per
  screening (Autofiktio, four screenings, all Engel 1, 12,50 €), the times matching the
  committed rows exactly. It would need Chrome on the local machine, about 15 pages a
  run at roughly 6 s each, and the adapter would have to keep four fields and never the
  page, which carries the widget's key. Deferred by the user the same day: no more
  polling on the local half for now. `price` and `aud` stay empty for Engel.

### The Cinemahouse batch and the marker fix, verified on the first cloud run (2026-09-14)
First cloud run including `cinemahouse`, dispatched by the local wrapper at 20:37 UTC on
`52d8268b`, data at `712ebc7e`. `run-cinemahouse.log` reads `exit=0`: 3 venues, 253
showtimes, 0 failures, so the provisional `where="cloud"` holds. The run itself went red on
`run-nexxo.log`, `jarvelankino locationid 1 FAILED: <urlopen error timed out>`, which kept
its previous file; unrelated to this batch and the shape IDEAS already records as carrying
no mechanism.
Posters: all 253 were mirrored, but by the **local** half, not the cloud one. Its
`mirror_posters.py` step runs over the whole of `data/`, so it swept the new provider too:
`47 downloaded` in that log is exactly the film count, 21 + 19 + 7. The tree is 4044 poster
references, 0 off-origin, 1023 files. The README paragraph claiming 253 were waiting for a
cloud run was wrong on both halves and is corrected.
Marker fix, partially exercised. Every key that was new or held a wrong id was re-judged and
every id matches the ones read off /movie/{id} by hand: Presidentin kyyditys 1412214, Lapin
sota 1450460, Pirjo i Sverige 1729175, Rakkautta ja virtahepoja 1450473, Kerro kaikille
1304530, Hetki ennen valoa 1015881, Matka Piemonteen 1545391 by alias, and Avengers
Endgame Re-release (encore) from a weak 24428, The Avengers 2012, to an exact 1769545.
Not yet exercised: every `Kojootti vs. ACME` language-marker spelling. Those entries were
stamped `c: 2026-09-14` by the 17:13 UTC run, which predates the fix, and came out of this
run byte-identical because the pass skips a title already checked today. They take the
daily retry on the first run after midnight UTC. Same timing the 2026-09-13 entry above
records; not a defect in the fix, and nothing to change.

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
- **The feed lists a film twice (2026-09-07).** Read live it returned 39 film records for
  33 distinct `movie_id`s: six films arrived as two copies differing in exactly one field,
  `premiere`, each carrying the same `show_times`. Both parsed, so 44 of 183 rows were
  duplicates and the app drew each as its own stub: "Presidentin kyyditys" showed twice at
  14:40 in Gilda 3 on 12 September, and the committed data held 43 byte-identical rows.
  The `show_times` list inside a film has no repeats, so the duplication is at the film
  level, and nothing here reads `premiere`, which makes the copies interchangeable. The
  key is the screening rather than the record -- venue, start, film and auditorium -- so
  it holds whatever shape the feed arrives in, and `parse` prints how many rows it
  dropped. Every component of that key is tested: dropping the
  venue collapses one film playing both houses at one time, dropping the start collapses a
  matinee into an evening show, dropping the auditorium collapses two screens, and
  dropping the film id collapses two films whose screen names `_aud` blanked.

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
- Ticket URLs come from the markup, never built, but resolved against the site before
  they are stored. On 2026-08-27 every row pointed at `orion.kinola.ee/web/screening/{uuid}`
  and the festival box-office case was unexercised against the live page; the site moved to
  site-relative `/checkout/{uuid}` by 2026-09-06, which is the entry below. Both shapes and
  the box-office case are now covered by fixture in `tests/test_orion.py`.
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

### Cinema Orion's ticket links became site-relative, and reached the reader as ours (2026-09-06)
The site moved from absolute `orion.kinola.ee/web/screening/{uuid}` links to site-relative
`/checkout/{uuid}` ones. `orion.py` stored the row's href verbatim, so the bare path went
into the data and out to the two surfaces, which failed differently:

- The app rendered `href="/checkout/{uuid}"`. `safeUrl` allows a URL with no scheme,
  because it only rejects a scheme that is not http or https, so the browser resolved the
  path against leffavuoro.fi and all 14 showtimes pointed at a 404 on this origin. Checked
  with `curl` against our own host; cinemaorion.fi's checkout was never called.
- The static pages dropped the link instead. `build_pages.py:656` renders a URL that does
  not start with `http` as a `<span>` rather than an `<a>`, and line 735 leaves `url` and
  the price offer out of the JSON-LD, so the Orion page shipped 14 unlinked showtimes and
  no offers rather than 14 wrong links.

Fix: `_ticket()` resolves the href with `urljoin` against `URL`, which leaves an absolute
link alone. That matters here rather than being a detail of urljoin: festival rows link to
the festival's own box office (Espoo Ciné to boxoffice.espoocine.fi) and must not be
dragged onto cinemaorion.fi. A row with no link still falls back to the programme page.

Orion was the only provider storing a relative URL, measured across the 36 providers whose
shows carry a `provider` field (Finnkino's do not): every other ticket host matched or
ended with its registry host. After the refetch all 14 are absolute on cinemaorion.fi with
the uuids unchanged, and the four regenerated pages carry 11 ticket links where they
carried none.

`tests/test_orion.py`, 6 tests, five mutations red. The general one is
`test_every_stored_url_is_absolute_http`: a URL with no scheme and no host is a link to
this origin whatever it was meant to be, and that is the assertion that would have caught
the change on the day the site made it. A sixth mutation was discarded rather than
recorded as a break: `urljoin(URL, "")` already returns `URL`, so removing the explicit
fallback is an equivalent rewrite.

Left alone on purpose, because it is a client decision rather than a parser one: `safeUrl`
still accepts a scheme-less URL, so the next provider that publishes a bare path repeats
this. Deciding whether the client should reject one, or resolve it against the provider
host, is a separate change.

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
The six rounds of probing and where they stopped are in
[docs/research/ticketing-platforms.md](../research/ticketing-platforms.md). What it
cost here stands: `price` and `aud` stay empty for Engel, a showtime opens the film
page, and dates whose times exist only behind the widget stay missing.

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

### Cine Kerava and Sipoo use the eTiketti adapter (2026-09-07)
`kiertue.cine.fi` was requested by a user. Its `/elokuvat/ohjelmistossa` listing and film
pages render the eTiketti template `etiketti.py` already parses, so this is a `SITES`
entry and no new parser. Read on 2026-09-07: 7 films on the listing, 4 screenings for Cine
Keuda-Talo in Kerava and 6 for Cine Nikkilä in Sipoo, each with a `/salikartta?id=` link, a
price, a rating, a language and seat availability. One ticket URL answered 200.

The place lines are `KERAVA | CINE KEUDA-TALO` and `SIPOO | CINE NIKKILÄ`. `PLACE_RE`
splits them into place `KERAVA` and `aud` `CINE KEUDA-TALO`, so the room field repeats the
cinema. The site opts into `normalise_aud` and both venues publish `aud` as "". Matching
runs against the raw place and room joined, so the venue selects before the field is
emptied.

Cine is the second site to set the flag. The gating tests in `tests/test_etiketti_aud.py`
ran over Savon Kinot alone through an `sk_site()` helper. They now run over
`optedin_sites()`, checking every opted-in site for a venue `short` and for a room field
holding only the venue name. Five mutations red.

Kerava joins Keski-Uusimaa. Its longest hop stays Hyvinkää to Nummela, so `km` is
unchanged at 45. Sipoo joins Itä-Uusimaa and widens it: the longest hop becomes Sipoo to
Loviisa, an estimated 65 km, the widest of any area here and above the roughly 60 km the
cut was argued from. Kept because Sipoo's nearest cinema city is Porvoo, at about a quarter
of that distance. The figure is an estimate, like the others in `REGIONS`, and is not
published.

`CITY_SV` gains `Kerava: Kervo` and `Sipoo: Sibbo`, both established Swedish names. That
edits `index.html`, so `sw.js` goes to v128.

`tests/test_regions.py` required every `REGIONS` city to appear in committed
`data/venues-*.json`. Kerava and Sipoo cannot until the cloud workflow writes
`data/venues-cine.json`. A city is now backed by the data or by an adapter that names it. A
second test bounds that: a region city missing from the data must belong to a provider with
no venue file at all, so a cinema dropped from a provider that has one still fails.

The accent is Cine's `#FE4719`, L\* 57.7. Kerava and Sipoo have no other provider.

Cine Mäntsälä is excluded. `mantsala.cine.fi` runs MyCloudCinema: its root carries the
vendor signature, and `/elokuvat/ohjelmistossa` answers 200 with a 2958-byte page holding
no `movie-list` container and no film links, which the eTiketti parser would read as an
empty programme and fail on. It needs an adapter for that platform.

Kiertuenäytökset is excluded. `kiertue.cine.fi/teatterit/kiertue` renders zero screening
items, zero date classes and zero booking links.

### Elokuvateatteri Star, Oulu (2026-09-07)
Requested by a user. `lippu.elokuvateatteristar.fi` serves the same
`/elokuvat/ohjelmistossa` listing and film pages, on Kotka's template: `klo` times, `Lippu`
prices, `Vapaat paikat` seat counts and a `place | room` line, with posters on
`cdn.etiketti.app/star/`. A full read returned 24 films and 133 screenings for one venue,
each with an auditorium, a price and a `/salikartta` link, 128 with a rating and 108 with a
language. A second read an hour later returned 134, so the count is a reading rather than a
property of the site. One ticket URL answered 200.

The public site is `elokuvateatteristar.fi` and the programme and ticket links are on the
`lippu.` subdomain. `host` is the public domain, which the footer credits. `base` is
`https://lippu.elokuvateatteristar.fi`, which the adapter reads and `run.py` paces on: the
pacing key is `urlsplit(base).netloc`, so the public domain there would name a host the run
never touches.

The room field holds `SALI 1` through `SALI 5`, five rooms in one building, so
`aud_repeats_venue` stays off.

Accent `#2563EB`: 50.0 normal, 73.7 Viénot and 65.1 Machado against Finnkino Plaza, Oulu's
other chain, at L\* 46.1, and unique in the registry. Two colours were measured and
rejected. `#003CFC` is Kino Tapiola's hex, which `tests/test_tapiola.py` pins as unique, so
reusing it turns that test red; its figures against Finnkino, 52.7 / 80.4 / 71.6 at
L\* 38.3, are the ones the Tapiola entry above records. Star's brand red `#AF0310`, from
`/customers/star/css/style.min.css`, is unique and clears the rule at 19.6 / 18.6 / 18.7
but sits at L\* 36.4, under the band the 3 px borders stay legible in.

Star gives Oulu a second cinema and a combined city row. It does not give Oulu an area: an
area needs two cinema cities.

Cloud routing was provisional until the first committed run, and the run settled it the
other way. See "Cine and Star answer an ordinary connection and 403 a runner".

### Cine and Star answer an ordinary connection and 403 a runner (2026-09-08)
Both were registered `where="cloud"`, since nothing in a read from an ordinary connection
suggested otherwise. The first cloud run after they landed failed both:

    [http] 403 from kiertue.cine.fi, gave up after 3 attempt(s) -- Server: cloudflare
    [http] 403 from lippu.elokuvateatteristar.fi, gave up after 3 attempt(s) -- cloudflare

CF-Ray present, no Retry-After, edge datacenter DFW. The same two URLs answered 200 from
an ordinary connection minutes later, and had answered 200 on 2026-09-07 when the adapters
were written. That is Savon Kinot's signature exactly, so both move to `where="local"`.

`run.py` filters SITES by half, so the etiketti module now reads four sites locally and
sixteen on Actions. The wrapper needs no new block: etiketti already runs a local half for
Savon Kinot and Joutsan Kino, and it stages `data` wholesale.

The run committed its data and still exited 1, which is the intended behaviour: a provider
that parses nothing fails the run rather than letting old data age quietly. The other
sixteen eTiketti sites wrote 715 showtimes across 19 venues in the same run.

`tests/test_run_routing.py` pins the local list, so a site moving between halves stays a
decision rather than a side effect.

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
05:19 and 13:44 UTC), each recovering on the next run. A probe from that runner at 13:44 got
the same 167-byte shell for the homepage (centralus, HTTP 202), so SiteGround refuses the
address for the whole host and an in-run retry cannot help. Failures came from northcentralus,
westcentralus and centralus; passes from westus and westus3.
Nothing selects a region on hosted runners. `where="local"` on the registry entry
routes the module to the local half. The wrapper outside the repo got its block, its own
`run-regina.log` and its `git add` entry on 2026-09-06, placed before the poster step like
Joutsan Kino's so the run mirrors the posters it brings in: 15 of the venue's 20 showtimes
carry one. No `--half` flag, because the module has one site, that site is local, and off a
runner `half_of` defaults to `all`, which selects the same site.

Before the wrapper had run, what was verified was local and partial: `zsh -n` accepts the
wrapper, and `run.py regina` from an ordinary connection returned 20 showtimes over 8 dates
and exit 0, which covers the adapter and the routing but not the block as the wrapper runs
it.

**Recovered on the local run of 2026-09-06 23:11 UTC** (`85281746`). `run-regina.log` ends
`exit=0` with 17 showtimes over 7 dates, `data/area-regina-helsinki.json` is in the same
commit with `generated` at 23:11:19Z against 11:14:51Z before it, and the four parts that
had never executed all did: `tee` wrote the run's output, the `pipestatus` read produced
the appended `exit=` line, and the `git add` entry staged the log and the data together.
The drop from 20 showtimes to 17 is the programme moving as a day passed, not a loss.

`Check run logs` went red on that same push, which was the ordinary case rather than a new
fault: the tree still carried the cloud `run-nexxo.log` from 17:11, and a local push is
checked against every committed log including the cloud half's. Bot pushes do not trigger
that workflow, so the red clears on the next cloud run rather than on a rerun. It did:
`19f97e8a` has nexxo at `exit=0` and all 18 committed run logs ending `exit=0`.

### Cinemahouse: three cinemas on one WordPress plugin (2026-09-14)
Bug: Kino Piispanristi (Kaarina), Kino Lumo (Salo) and Laitilan Kino (Laitila) were unread.
All three run the `cinema-reservations` plugin under a cinemahouse-child theme, Laitila on
an older build with the same markup, so one adapter serves them.
Fix: `cinemahouse.py`, one front page per site. `cr-screening-row` carries the date, time,
room, price, free seats and `/varaa/?screening_id=N`; `cr-movie-tile` carries the poster,
age limit, runtime, genres and the film page, joined on the normalised title; one film page
per film for the cinema's own synopsis, `common.capped`. A row has no year, so `_iso` takes
the nearest. `eventId` is the normalised title with the strand off, since ENNAKKONAYTOS is
its own post. Dedup is on the screening id, which is unique inside a site and collides
across them. `EmptyProgramme` only when the filter select offers no day and there is no
tile and no row, and the film parse reads no part of that day list; a page still listing a
film or a day and parsing to zero fails. `book="reserve"`: /varaa/ takes a name, an email
and a phone and ends in "Vahvista varaus", with no payment step anywhere. Accents are
unconstrained (no shared city or region); against Finnkino 51.2 / 35.2 / 47.6 dE00 on the
weakest model, 18.2 and up between the three. Laitila's own JSON-LD stamps a 13:00 Helsinki
screening `+00:00`, so the rendered clock is the time source. First run 175 / 71 / 7
showtimes, 0 failures, three screenings a site read back against the pages by hand.
Tests: `tests/test_cinemahouse.py`, 43 tests, 29 mutations red; the `test_show_contract`
sample, 4 mutations red.
Accepted: eight titles survive `enrich_tmdb.clean` uncleaned (Laitila's seven "(Kahvi ja
Kino)" and "Kojootti vs. ACME ENGLANNIKSI") and will not match TMDB; posters stay remote
until the first cloud run mirrors them; an emptied programme keeps its last screenings,
since `EmptyProgramme` writes nothing.

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
**Superseded in part on 2026-09-20**, see the next entry: house-made title cards replace
the initials tiles. Everything here about *Heureka's own* artwork still binds, and written
permission is still the only route to publishing any of it.

### House title cards supersede the generated-artwork decline (2026-09-20)
The entry above declined "generated artwork" among the substitutes. The maintainer
superseded that on 2026-09-20, naming IDEAS.md as the file to change. The old record is
left standing and this one sits beside it, because its reasoning about Heureka's artwork
is untouched.

What ships. Three of the four planetarium films draw one of Leffavuoro's own title cards
instead of a two-letter initials tile: Asteroid Quest, Metsän sydän and The Stellars -
Tähtijengi, together 178 of the 248 showtimes the site was drawing without a poster.
Recombination has a real TMDB poster (1157677) and is untouched.

What a card is. `scripts/make_cards.py` draws an abstract background from a seed and sets
the published title over it in Archivo, at 342x513 -- the 2:3 and the width
`mirror_posters` already uses. Nothing is downloaded, nothing is a model's output and
nothing derives from anyone's artwork: the image is geometry, gradients and noise this
repository computes, which is why it is ours to publish. They are editorial illustrations
and the documents say so in those words. None of them may be called a poster.

The safeguards are the decision, not its decoration:
- **Abstract only.** No representational figure, character, logo or lettering in the art
  layer, and nothing in a named artist's or studio's manner. A theme enters as a palette
  and a motif, never as a depiction of the film.
- **Deterministic.** The bytes are a pure function of the title and a fixed seed, and
  `make_cards.py --check` fails when a committed file differs from what the script draws.
- **Keyed on the published title character for character**, in `heureka.py` and nowhere
  else, so no other provider picks a card up by publishing the same title and a title
  that moves on gets no card rather than the wrong one.
- **`isrc` is not set**, so `enrich_tmdb` treats a card as the cinema's own and never
  replaces it. The same rule makes a real poster, if permission ever arrives, a deletion
  from the map and nothing more.

Where they live: `data/posters/`, prefixed `card-`, not a directory of their own. The
client loads an image only from `data/posters/` (`ASSET_DIR`) and `build_pages.py` drops
any reference outside it. A card in `data/cards/` was silently refused by one guard and
dropped by the other, which is how that was found, before it shipped rather than after.

Measured. White type over the scrim is 17.9:1 at worst across the three, against WCAG
AAA's 7:1. Verified in Chromium at 375 px, where the app draws a card at exactly 72x104,
and at 1200 px, where it draws 92x132; the generated venue page draws 92x132 at both.

Tests: the adapter map agrees with the generator's own list, every mapped file exists and
is 342x513, an unmapped title keeps an empty `img`, and no show carries `isrc`. Six
mutations. One survived the first dimension test -- mapping a title to a different
existing 342x513 image -- and produced the map-agrees-with-generator test.

### A sibling cinema in the navigation still withholds the confirmation (2026-09-14)
Cine's navigation names Cine Mäntsälä and Kiertuenäytökset, neither registered here
(Mäntsälä is a separate deployment). A row for either clears `complete` and withholds
Nikkilä's empty confirmation, so the venue would read "Päivitys viivästynyt" again while
the row is there. The committed local run of 2026-09-13 read Cine complete: 12 rows for
Keuda-Talo, none unclaimed.
Rejected: excusing a row whose place the navigation names. The navigation names the site's
own theatres, so a `match` rotted off a *registered* venue drops that venue's rows onto a
navigation-named place too, and excusing those would publish a venue that is showing films
as confirmed empty. That is the one failure this flag may not have; withholding fails the
other way, and the venue keeps its real data while it does.
Fix: the read names the unclaimed place and its row count in the log, so a withheld
confirmation is visible in the committed run log instead of being silent.
Tests: the unregistered-place case asserts the place is named and that the navigation
naming it does not excuse the row. Three mutations.

### Kino Juha publishes two spaces on one listing (2026-09-14)
Bug: the site prints the place as "KINO JUHA" or "VIP-SALI" and only the first was
registered, so every VIP-SALI row matched no venue and was dropped. Measured 2026-09-14:
13 screenings over 9 film pages, 7 published and 6 lost, ever since the site was added on
2026-08-30. The unclaimed-place log line added the same day is what surfaced it, in the
cloud run committed at 3495cf8c.
Rejected: letting those rows claim Kino Juha as a hall of it. Both salikartta pages, read
as a visitor, print the address under the place: Keskustie 7 for KINO JUHA, Pratikankuja 3
for VIP-SALI, both Nurmijärvi, both HTTP 200. A hall fallback would have published 6
screenings at the wrong building, and the calendar LOCATION with them.
Fix: a second venue `kj-vipsali`, match `vip-sali`. The accent is the provider's, so there
was nothing to measure; label and page slug stay distinct from the main hall's.
Tests: the 13 split 7 and 6 with no shared ticket id, one screening listed under two films
is published once, a third place stays unclaimed. Five mutations. The cloud run of 23:13
published both venues, 7 and 6; the README is 83 venues and 191 sitemap URLs from there.

### The eTiketti navigation prints the town with the cinema (2026-09-14)
Bug: `identified_venues` compared the whole anchor text to `match`, and the comment above
it claimed every eTiketti site renders the navigation. Measured 2026-09-14, one listing
read per host: 6 of the 20 carry `/teatterit/` anchors at all, and the whole-text
comparison identified 6 of the 29 registered venues. Leffabuumi prints "Mikkeli Kinolinna",
"Mikkeli Ritz" and "Puumala Kino Saimaa" against matches `kinolinna`, `ritz` and `kino
saimaa`: 0 of 3. Kinotar prints "Kinotar 123" against `kinotar`.
Fix: `match` is looked for inside the anchor text, the rule the screening rows already
use, which takes the count to 10 of 29 and to all 10 venues of the six hosts that render a
navigation. `VENUE_LINK_RE` also tolerates other attributes on the anchor; no host carried
one on the day, so that half buys nothing now and stops a silent regression later. The
other 19 venues stay unconfirmable and keep their previous file, which is the safe side.
Tests: an anchor with a class, "Mikkeli Ritz" identifying `ritz`, a link outside
`/teatterit/` identifying nothing. Four mutations.

### A drifted screening pattern could confirm every eTiketti venue empty (2026-09-14)
Bug: `complete` was cleared by a failed fetch and by an unregistered place, never by a
film page that fetched and parsed to nothing. With TIME_RE off the template every venue
ends the read rowless and `EMPTY_VENUES_CONFIRMED` publishes a fresh empty file for each
one the navigation names: Cine reproduced as (0 live, 0 showtimes, both pending),
`area-cine-keuda.json` overwritten with `shows: []`, exit 0. CLAUDE.md's case, a listing
that lists films while the parse yields nothing, has to keep failing.
Fix: `parse_movie` counts the blocks it could read no time out of, and a page with blocks
and no row clears `complete`, so that site confirms no venue empty. The read is
disqualified rather than raised on as nexxo does: one odd block among readable ones is not
a template move, and the venues that did parse still publish. No live venue and nothing
confirmed empty is already a run.py failure.
Tests: a Keuda page with the clock gone from both blocks vouches for nothing, keeps both
previous files and writes no provider file; a mixed page still confirms. The fixtures and
the stub now come from `test_etiketti_templates`. Seven mutations.

### eTiketti confirms an empty venue from its own navigation (2026-09-13)
Bug: Cine Nikkilä's programme ended with the 16:45 screening on 13.9. The 20:12 local run
found no row for it, took the keep-previous branch, and the provider read "Päivitys
viivästynyt" on a 14:10 stamp while Keuda-Talo was fresh. The stamp never advances on
that branch, so the label would have stayed until Nikkilä's next programme. Same shape as
Kino Metso's Muurame (2026-09-04); eTiketti did not set `EMPTY_VENUES_CONFIRMED`.
Fix: it does now, on evidence from the read itself: the listing's theatre navigation
(`/teatterit/<slug>` anchors) names the venue with its `match` text, every film page was
fetched, and every screening row matched a registered venue. A skipped page, a row for
an unregistered place (a rename looks like that) or a venue the navigation lacks leaves it
out of the result, and run.py keeps the previous file as before. Anchors only: the
footer's "Esitysjaksot Keravalla ja Nikkilässä" names the town, not the venue.
Tests: `tests/test_etiketti_empty_venue.py`, Kotka-template fixtures for Cine: confirmed
empty beside Keuda-Talo's rows; a failed page, an unregistered place or a missing anchor
each keep the previous file through run.py; prose alone identifies nothing. Live read
2026-09-13: Keuda-Talo 12 rows, all matched, Nikkilä none. Seven mutations.

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

### An eTiketti audio-version label is not part of the film title (2026-09-14)

Bug: Bio Rex Kokkola published "Kojootti vs. ACME ENG" beside the plain title and
Kinopirtti "Kojootti vs. ACME DUB" and "... SUB". The search string is the published
title, so all three went to TMDB with the label attached and returned 0 results, while the
plain title matches 1204680 exactly. 10 showtimes, unmatched since the film opened.
Measured before choosing the layer: the language is already extracted separately here.
Kinopirtti's DUB row carries `lang` FI-A and method "Puhuttu suomeksi", its SUB row
EN-A, FI-S, SV-S and "Puhuttu englanniksi"; Kokkola's ENG row carries FI-S against the
plain title's FI-A. The label is a second copy of what the page already states.
Fix: `etiketti.strip_version_suffix()`, not `enrich_tmdb.clean()`. The shared cleaner would
have to strip these words for every provider, and ENG, SUB and DUB can end a real title.
Four conditions, all required: one of exactly three labels, published in capitals,
something left after it, and a language row on the page to corroborate it. A page stating
no language keeps its title, because there the label is the only record of the version.
Rejected: adding the bare tokens to `TRAIL_NOISE`, which would eat "King of Dub".
Tests: `test_etiketti_templates.VersionSuffixTest`, 7 tests, four mutations red, one of
them pinned on the function because `parse_movie` cannot reach the empty-result guard.
Published 2026-09-14 on the 23:18 UTC cloud run: no ENG, SUB or DUB title is left in the
data and all 10 showtimes carry 1204680.


### Iso-Hannu, Rauma: the batch's one cinema out of nine candidates (2026-09-15)

Nine candidates were on the list. Eight are not cinemas this repo can or should add, and
the reasons are in [ticketing-platforms.md](../research/ticketing-platforms.md) under the
2026-09-15 batch: Bio Salo, Bio Stara and Bio Jukola still answer Nexxo with `{"shows":
[]}` at every locationid and `days=60`, current and upcoming alike; Kino Diana has closed
and points at Kino Piispanristi, already a provider; Kino Julia is a page in a cinema
history archive; Teatteri Union is WHS's stage, programming "visuaalista teatteria,
eläviä kuvia ja poikkitaiteellisia esityksiä"; Kino Kirkkonummi hand-authors its times in
Elementor widgets with no year, no room and no booking host; Eventio is confirmed as the
platform behind KAVI's shop, which is a shop rather than a listing. Kino Kaustinen is the
near miss and stays open: a real eTiketti tenant with its own id space, but it publishes
no screening, so there is no ticket destination to fetch and check.

Iso-Hannu is the one that became a provider, and the one parser in the batch: its site is
its own PHP and carries none of the platform fingerprints already read here.

- **The whole programme is one request.** `<div id="showtable">` on the front page holds a
  `<h3 class="showtable-title">` per day with the year in the date, then one
  `div.showtable-container` per hall. 66 screenings over 7 days and 3 halls when read,
  from 14 films. The film pages add runtime, age limit, genre, spoken language and a
  poster, one per film rather than per screening.
- **The row's anchor carries the film id** and that id is the film, not the run: it
  recurs across days and halls, so it is the `eventId` and no title normalisation is
  needed to fold a film's screenings together.
- **Hall is per container, not per day.** Parsing rows flat would file every screening
  under the day's first hall; `test_a_row_belongs_to_the_hall_whose_container_holds_it`
  pins it and the mutation that flattens it turns three tests red.
- **The ticket link is written `http://` on a host that answers `https://`** (checked
  2026-09-15, 200), so it is upgraded. `book="buy"`: the button reads "Osta liput".
- **The age limit is written `K12`.** Every other provider here publishes `K-12` and the
  committed data holds only `K-7`, `K-12`, `K-16`, `K-18` and `S`, and the stub prints
  `rating` verbatim, so it is normalised. Subtitles are not published at all, so `lang`
  carries the spoken language only and no `-S` role is invented.
- Accent `#FF4466`. Rauma is in no REGIONS area and holds no other chain, so it enters no
  shared view and `accent_check.py --search isohannu` says there is nothing to search.
  Measured anyway with the script's own dE: L* 58.4, inside the set's 38-60 band, 9.2
  dE00 from its nearest accent on the weakest of the three models. A sweep of the band
  against all 42 existing accents tops out at 9.2, so 14.4 is not reachable globally,
  which is why the rule binds shared views rather than the whole set.
- `where="cloud"`: www.isohannu.fi answers Apache with no Cloudflare and no challenge.
- Tests: `tests/test_isohannu.py`, 20 tests, plus a sample in `test_show_contract.py`.
  Eight mutations, all red, none void. The fixture carries two days and three halls
  because the parser walks them as nested loops and one of each would enter neither.
- **Published 2026-09-15** in `d216607b`: 66 showtimes over 7 dates, Rauma a new city.
  The run's own outcome is in "The thirteen venues published, and the run still failed".
  This line predicted 99 pages and 199 sitemap URLs on the assumption that Iso-Hannu
  published alone; thirteen venues landed in one run instead.

### TMB Cinema: four cinemas, one adapter, four new towns (2026-09-15)

Kino-Toijala (Akaa), Kino-Sampo (Valkeakoski), KinoMania (Pieksämäki) and Elokuvateatteri
Elo (Heinola), added as four providers on one module, `scripts/providers/tmb.py`. Four
towns that carried no cinema here before. The probe evidence is in
[ticketing-platforms.md](../research/ticketing-platforms.md) under the TMB section.

- **The question that had to be answered first was whether they are one site or four.**
  Their schedules coincide exactly, in two identical pairs, which is what a mirrored
  deployment looks like and is the trap `ksek.fi`/`kinoaurora.fi` set on 2026-08-30. They
  are four: the `?varaa=` booking id differs per host for the same film at the same
  minute, and Mania and Elo publish two halls where Toijala and Sampo publish none.
- **Four providers rather than one.** Each has its own brand and host, and `host` is the
  source line the footer shows; one "TMB Cinema" entry would name none of them and could
  carry only one of the four hosts.
- **The showtime links to `?ohjelmisto={id}`, the public film page, not to `?varaa=`.**
  The latter is the seat-reservation action, which this repo does not call, so a link
  there could never be checked before publishing: that is exactly how six Nexxo sites
  shipped dead ticket links on 2026-08-31. `book="reserve"` accordingly. All four
  destinations were fetched and answer 200 with the screening block.
- **No age limit is inferred.** The rating exists only as an image filename and the film
  page states it in no text. `ikaraja_2/_3/_4` were checked against this repo's own
  committed ratings for five films other providers carry and agree (K-7, K-12 twice, K-16
  twice). `ikaraja_1` occurs only on opera events, which nothing here rates, so it is
  unmapped and those rows publish no rating. The mutation that "completes" the table with
  S and K-18 turns a test red.
- A published weekday that contradicts its own date is skipped and counted. The date is
  complete without it, so the weekday's only job is to notice the template moving a field.
- Accents `#555588`, `#336633`, `#EE0055`, `#AA77AA`. All four towns hold no other chain
  and none is in a REGIONS area, so none of these enters a shared view and
  `accent_check.py --search` says there is nothing to search. Measured against the whole
  set anyway: each at least 6.3 dE00 from all 43 existing accents on the weakest of three
  models, and at least 18.4 from the other three added here. A sweep of the L* band tops
  out near that, which is why the 14.4 rule binds shared views and not the whole set.
- Tests: `tests/test_tmb.py`, 17 tests, plus a sample in `test_show_contract.py` built on
  the two-screen fixture because the single-screen one never enters the auditorium branch.
  Eight mutations, all red, none void.
- Measured live before committing: 23 screenings at Toijala and Sampo, 32 at Mania and
  Elo, 7 and 8 films, 12 dates each out to 2026-11-07, and the contract check passes for
  all four.
- **Published 2026-09-15** in `d216607b`: Kino-Toijala 22 and Kino-Sampo 22 showtimes,
  KinoMania 29 and Elo 29, each over 12 dates to 2026-11-07. `logs/run-tmb.log` reads
  `exit=0` and `4 venues, 102 showtimes`. Four new towns.

### Julia 1&2, Hyvinkää, and the identity the last batch got wrong (2026-09-15)

The 2026-09-15 candidate batch closed a name called "Julia" as a defunct Turku cinema,
having read `turunleffat.biokuva.fi/elokuvateatteri/julia/`: a local cinema-history page
about a 1980s Eerikinkatu build. The reading of that page was right and the identity was
wrong. The candidate is **Julia 1&2 in Hyvinkää**, Hämeenkatu 34, an operating two-hall
cinema on its own WordPress, and it is added here. The earlier entry is left as written
and carries a dated correction pointing at this one.

What made the error possible is worth naming, because the same shape closed two other
candidates that day: a name was matched against a search result rather than against a
town and an operator. Confirming the town first would have separated the two Julias in
one request.

- `/ohjelmisto/` is the whole programme in one request. The films are listed twice, once
  in an index with no screenings and once in the programme proper, so the parser anchors
  on the film block and requires a screening row; anchoring on the title would have
  published dateless shows.
- **The year is two digits**, `15.09.26`, read as 2000+YY. It is published rather than
  missing, so nothing is inferred from the clock. The mutation that substitutes today's
  year scored **VOID** at first, because the fixture year and the year the suite runs in
  were both 2026 and agree; the test now carries rows in 2027 and 2029 and the mutation
  is red. The same pass found the dedupe untested for the same reason, no fixture
  repeated a row, and that is covered now too.
- Price, age limit, runtime, genres and a poster all come from the film block. `Ikäraja:
  7` becomes `K-7` and an unreadable value yields no rating rather than a guess.
- **`book="door"`.** There is no online booking: the cinema sells at the door and takes
  reservations by phone, and `/liput/` sells gift tickets only. The showtime links to the
  film's own page. No ticket host was invented.
- Accent `#12664E`. This one is genuinely constrained, unlike the TMB four: Hyvinkää
  already holds BioRex and Keski-Uusimaa holds BioRex, Cine, Kino Akseli, Kino Juha and
  Studio 123 Järvenpää. The first colour tried, `#00AA88`, measured **1.7** on the weakest
  model and was rejected by `accent_check.py --search julia`, which is what that tool is
  for; `#12664E` measures 20.0 and every one of Julia's six shared-view pairs clears the
  14.4 floor. `tests/test_accent_check.py` pinned the shared-view pair total at 139 and it
  is now 145; the twelve pairs below the floor are unchanged, which is the number that
  matters.
- Tests: `tests/test_julia.py`, 17 tests, plus a contract sample. Eight mutations, all
  red, none void after the two VOIDs above were closed.
- Measured live before committing: 4 screenings, 2 films, 2 dates, both halls, price
  `14€ / 12€`, ratings K-7 and K-12, runtimes 87 and 87 (the cinema's own figures; TMB's
  pages independently give 87 for both films).
- **Published 2026-09-15** in `d216607b`: 4 showtimes over 2 dates. Hyvinkää was already
  covered by Kino Akseli, so it gained a combined city page rather than a new town, which
  is half of why `index.html` needed its chooser resynchronised.

### Bio-Kaari, Forssa: a MyCloudCinema cinema that still needed its own parser (2026-09-15)

Forssa had no cinema here. Added as `scripts/providers/biokaari.py`, one provider, one
venue. Evidence in [ticketing-platforms.md](../research/ticketing-platforms.md).

- **The platform fingerprint was a lead and not an adapter.** Posters from
  `mcswebsites.blob.core.windows.net` and tickets from `.../websales/` make this
  MyCloudCinema, which BioRex and Gilda also run on, and all three render it differently:
  HTML-in-JSON through `admin-ajax`, MyCloudCinema's own document, and here a bespoke
  WordPress plugin. Checking for an existing adapter was right and reusing one would not
  have worked.
- **The date is the day container's id**, `id="15092026"`, and the film rows repeat
  verbatim across the ten containers. A parser reading rows without their container would
  publish one day's times on every day; the mutation that does exactly that turns four
  tests red. That every one of the 15 screenings read had its own `websales/show/{id}` is
  what confirms the association is right rather than merely plausible.
- The release year in the title becomes the optional `year` field instead of staying in
  `title`, which is the TMDB and merge key.
- `Ikäraja: K7/4` becomes `K-7`: the 4 is how many years the limit may flex under the
  kuvaohjelmalaki, not part of the classification.
- The ticket link is read from the page and upgraded to the https its host redirects to.
  It is never constructed from a copied path, and the sales page is never fetched.
- Accent `#DD1100`, unconstrained: Forssa holds no other chain and is in no REGIONS area.
  Measured at 6.2 dE00 from its nearest on the weakest model, near the best available with
  48 accents already in the band.
- Tests: `tests/test_biokaari.py`, 18 tests, plus a contract sample. Eight mutations, all
  red, none void.
- Measured live before committing: 15 screenings, 3 films, 10 dates, 15 distinct ticket
  ids, and the film pages filling rating, runtime and genre for all 15.
- **Published 2026-09-15** in `d216607b`: 15 showtimes over 10 dates to 2026-09-24.

### Kino Vaakuna, Lohja, and a shared rule for pages that publish no year (2026-09-15)

Lohja had no cinema here. Added as `scripts/providers/vaakuna.py`, and with it
`common.resolve_year`, because three of the candidates assessed that day publish a day and
a month and no year at all.

- **The rule is nearest occurrence, ties to the future**, over last year, this year and
  next. "Next occurrence" is the rule that suggests itself and it is wrong in the case
  that matters: on 2 January a page still showing `28.12.` means five days ago, and a
  forward-only rule puts it eleven months out where nothing filters it. Nearest handles
  both directions and bounds every answer to about six months either side of today. A day
  and month naming no real date in the window is skipped, never moved.
- **The tie-break is live code**, which was not obvious: a twelve-year sweep finds 195
  exact ties, all at 183 days across a leap year. The first test for it used 181 against
  184 days, which is not a tie at all, and the mutation flipping the tie-break scored
  **VOID** against it. The test now uses 2027-08-31 against `01.03.`, a real tie, and the
  mutation is red.
- The age limit is an image whose filename is the number, `icon/16.png`, so it is read
  rather than inferred. One film carried `icon/.png` and publishes no rating, which is
  what the site does too.
- `book="reserve"`: "Varaa liput" opens the film's own page and reservations are by phone
  and email. No purchase link and no auditorium were invented.
- Accent `#CC4477`, unconstrained: Lohja holds no other chain and is in no REGIONS area.
- Tests: `tests/test_vaakuna.py`, 19 tests including `resolve_year` on its own, plus a
  contract sample whose `today` is pinned so it cannot drift with the calendar. Ten
  mutations, all red, none void after the tie case was fixed.
- Measured live before committing: 19 screenings, 8 films, 8 dates, prices and runtimes on
  all of them and ratings on all but the one the site does not rate.
- **Published 2026-09-15** in `d216607b`: 30 showtimes over 10 dates to 2026-09-24, inside
  the +0..+9 span the `(30, 60)` window was measured at.

### Kuvakukko and Kino Manttu: two venues on one page (2026-09-15)

Kuopio's two municipal cinemas, added as one provider with two venues,
`scripts/providers/kuvakukko.py`. Nilsiä is a new town; Kuopio already had Finnkino.

- **The two `<h2>` headings are the venue boundary.** Without them Nilsiä's weekend is
  filed under Kuopio and nothing downstream catches it; the mutation that ignores the
  boundary turns three tests red.
- **A day paragraph must open with a weekday and a date.** Addresses, price lists and
  closure notices use the same element. The anchoring is enforced twice, by `^` in the
  pattern and by `re.match`, which is why the mutation attacking it scored **VOID** twice
  before it was written to defeat both: neither edit alone changes any output. The test
  that pins it is a closure notice carrying a weekday, a date and something shaped exactly
  like a screening row.
- **Manttu's schedule is routinely already past**, because it plays every other weekend:
  11.–13.9. against Kuvakukko's 15.–24.9. on the day read. The weekday places those rows
  in the past, which is correct, and the client filters them. A forward-only year rule
  would have moved the whole weekend a year ahead.
- Rows linking to a third party (isak.fi, hyvätkuvat.fi) publish this cinema's own
  programme page instead.
- Titles keep their strand prefix. **"Hopeatähti-sarja" is not in
  `strands.EVENT_PREFIXES`**, so that one title will not match TMDB. Adding it is a change
  to a shared list every provider reads and is left as its own decision.
- `book="door"` for both venues; the page states there is no advance sale at either.
- Accent `#7A3FB8`, constrained by Finnkino in Kuopio and measuring 46.9 against it on the
  weakest model, far above the 14.4 floor. The pinned shared-view pair total in
  `tests/test_accent_check.py` moves 145 to 146; the twelve below the floor are unchanged.
- Tests: `tests/test_kuvakukko.py`, 18 tests, plus a contract sample. Nine mutations, all
  red, none void once the anchoring mutation was written to break both guards.
- Measured live before committing: 36 screenings at Kuvakukko over 9 dates, 9 at Manttu
  over 3, and the contract check passes for both.
- **Published 2026-09-15** in `d216607b`: Kuvakukko 36 showtimes over 9 dates, Manttu 9
  over 3. Manttu's are 2026-09-11 to 09-13, all in the past, which is the fortnightly
  weekend this entry recorded as already over and which the window's 30 days behind
  deliberately admit. Kuopio was already covered by Finnkino, so it gained a combined
  city page.

### Kino Kirkkonummi, and reversing a deferral made on maintenance grounds (2026-09-15)

Deferred earlier the same day as "parseable only by reading page-builder markup that
carries no contract", and implemented on a second look. The deferral was a judgement about
how much upkeep the parser would need, not a finding that it could not be written, and the
page does not bear it out: the screenings are server-rendered in a consistent shape and
there are three to five a week. Kirkkonummi is a new town.

- **Everything on the page is published twice**, desktop and mobile: 21 headings and 46
  list items for 6 films, 11 real screenings. Deduplicated on (film, start). The mutation
  that removes it doubles the programme and turns two tests red.
- **A row is a screening only if it reads `D.M. Weekday kloHH.MM`.** The same element
  carries cast, directors, notes, an address and a phone number.
- **"Tulossa 25.9. alkaen" is a release date and is excluded three times over**: the row
  must begin with the date, carry a weekday, and carry a time. Measured each relaxation
  separately: any one alone still excludes it, and only relaxing all three admits it. That
  is why the mutation aimed at it scored **VOID** twice before it was written to defeat the
  pattern anchor and the `re.match` call together. The same over-determination showed up in
  `kuvakukko.py` an hour earlier, and it is worth knowing that `re.match` plus a `^` cannot
  be broken by editing either one.
- The year comes from the weekday, as everywhere else in this batch.
- **`book="list"`**: the site is a single page with no per-film page and no booking host,
  so a showtime opens the programme page. That is what the mode is for, and it is the
  honest label when tickets are reserved by phone. The page names two seat counts and never
  says which screening uses which, so no auditorium is invented.
- Accent `#BB6688`. The first colour tried, `#1E7A3C`, measured 4.4 dE00 from Bio Grani on
  the weakest model; Kirkkonummi shares no view with it, so nothing bound the choice, but
  a near-clone of an existing chain colour is still a bad one. `#BB6688` is 6.1 from its
  nearest, which is close to the best available with 51 accents already in the band.
- Tests: `tests/test_kirkkonummi.py`, 17 tests, plus a contract sample. Eight mutations,
  all red, none void.
- Measured live before committing: 11 screenings, 5 films, 8 dates, the release-only film
  correctly absent.
- **Published 2026-09-15** in `d216607b`: 11 showtimes over 7 dates to 2026-09-24.

### Bio Savoy, Mariehamn: Åland, and a source that infers nothing (2026-09-15)

Added as `scripts/providers/biosavoy.py`, one provider, one venue. Åland was uncovered.
Evidence in [ticketing-platforms.md](../research/ticketing-platforms.md).

- **The only source added this week that needs no inference.** Every row carries a full ISO
  instant with its offset in a `content` attribute, put there by Drupal's date field, so
  there is no year to resolve, no weekday to verify and no timezone to assume.
  `common.resolve_year` is not used here. A row whose datetime carries no offset is skipped
  rather than given an assumed zone.
- **Two halls come from the block titles**, `Filmvisningar - Sal 1` and `- Sal 2`, and not
  from anything on the row. A third block on the page, `Dela`, carries the same class and
  only its title tells it apart, so a row inside it must not become a screening; the test
  puts one there to prove it.
- **The site is http only and the published URLs are http.** Port 443 is refused on both
  `biosavoy.ax` and `www.biosavoy.ax`, and `http://biosavoy.ax/` redirects to
  `http://www.biosavoy.ax/`. Publishing https would hand the reader a link that cannot
  connect; `safeUrl()` accepts http and no rule here forbids it. The mutation that
  "upgrades" the scheme turns a test red. If this is ever to change it changes at the
  cinema.
- The site publishes no poster, age limit or runtime, so there is nothing site-specific to
  mirror and the ordinary TMDB and `mirror_posters.py` passes cover artwork.
- `book="door"`: bookings by telephone only, and only until the day before.
- **The city is keyed `Mariehamn`**, its only official name: Åland's sole official language
  is Swedish. Every other city key here is Finnish because `CITY_SV` in `index.html`
  translates them, and that table cannot gain an entry without editing a file this project
  keeps frozen, so a Finnish exonym would show untranslated in the Swedish interface.
- Accent `#7766FF`, unconstrained. The first choice, `#0C6B8F`, measured 2.2 dE00 from
  Kino-Toijala and was rejected on that alone.
- Tests: `tests/test_biosavoy.py`, 16 tests, plus a contract sample. Eight mutations, all
  red, none void once the share-block mutation was aimed at `HALL_RE` itself.
- Measured live before committing: 12 screenings, 10 films, 3 dates, both halls, and the
  destination fetched at 200 over http.
- **Published 2026-09-15** in `d216607b`: 43 showtimes over 10 dates to 2026-09-24, both
  halls, every URL http as recorded. Åland is covered.

### Cine Mäntsälä: MyCloudCinema read through the visitor's own requests (2026-09-15)

Added as `scripts/providers/cinemantsala.py`, one provider, one venue in Mäntsälä. The
investigation that unblocked it, including what was tried first and why it was wrong, is in
[ticketing-platforms.md](../research/ticketing-platforms.md).

- **The JSON-LD feed the page injects is the wrong source, twice over.**
  `/webservices/structured_data/get` carries today only, 4 of the 37 screenings a visitor
  reaches that week, and it drops the `Z` off a UTC instant, so reading its naive
  `startDate` as a local time publishes every showtime three hours early. This was settled
  by comparing the feed with `getShowTimes` for the same day: identical rows, identical
  `show_time_id` values, one day's worth.
- **Not a `SITES` entry on `gilda.py`, which reads the same platform.** Gilda has a
  WordPress facade that returns the whole programme in one response; this site serves
  MyCloudCinema's own `/webservices/show_times/` endpoints, one date window at a time. The
  row shape *is* shared, so `FORMATS` and `LANG` are imported from that module and a test
  asserts the identity, but the fetch has nothing in common. Third time this week that a
  platform fingerprint turned out to be a lead rather than an adapter.
- **`number_of_days` is a cap of 7, not a request.** Asked for 7, 14 and 120 from
  2026-09-15 the endpoint returned the same 37 rows over six days, while a window from
  2026-12-01 did reach 12-05. So `getShowDates` is walked and covered with as few seven-day
  windows as it takes: 17 dates to 2026-12-22 took nine requests. Windows can overlap and a
  repeated `show_time_id` is one screening.
- **`show_date` is a UTC instant, not a date.** Local midnight arrives as the preceding
  `21:00:00.000Z` through 2026-10-19 and `22:00:00.000Z` from 2026-11-02, tracking the
  2026-10-25 DST change, so it is converted and never sliced. That mapping was checked
  three ways against the programme: the first window's business date, `getShowTimes` on
  2026-10-06, and the window from 2026-12-01. `business_date` on a screening row is the
  *local* date stamped `T00:00:00.000Z`, a second convention in one payload, and nothing
  reads it.
- **A failed window fails the site.** These requests carry the schedule, so
  `common.budget_or_raise`'s rule applies and half a programme is worse than none. A
  window count over 30 is refused for the same reason: the count comes from the cinema's
  own date list and nothing else bounds it.
- **An empty date list is `EmptyProgramme`; dates with no screening is not.** The dates are
  derived from the screenings, so a list of them beside an empty parse is the contradiction
  CLAUDE.md names as the broken case, and it fails.
- **The ticket link is read, not constructed.** The rendered programme emits one
  `#/book/{id}` anchor per screening, and the 37 ids it emitted were exactly the 37
  `show_time_id` values the window returned, as sets; the 2026-12-15 date route emitted
  exactly the two this adapter publishes for that day. `#/book/13394` loaded once resolves
  to the seat-selection page for that screening, which is how the destination was verified;
  the booking flow is never called by the adapter.
- Vocabulary, from 48 rows: `rating_name` is Finnish (`K7`, "Sallittu kaikenikäisille",
  "Ikäraja tulossa!", "Luokittelematon"), `subtitle_lang` is a phrase rather than a code
  ("Suomeksi ja ruotsiksi", "Ei"), and `title_extension` is the strand field, which
  `strands.py` says belongs in `method`. Because the strand arrives in its own field,
  nothing comes off the title and `EVENT_PREFIXES` is untouched.
- `movie_audio_style_name` is "Original language" or "Dubbed" and is **not** published: all
  five dubbed rows are Finnish-language children's films whose `audio_lang` is already
  `FI`, so `lang` states it and a pill would repeat it.
- Posters are `/media/posters/{movie_id}/{width}/{movie_poster}` and only widths 216 and
  1080 exist; 300, 500, 720, 1024 and 2048 answer 404. 1080 is published, same as Gilda.
- **Separate from the `cine` entry**, which is kiertue.cine.fi in Kerava and Sipoo: its own
  host, its own operator, its own platform, and cloud where Cine is local. Same shape as
  BioRex against Bio Rex Kokkola, so the label spells the town out.
- Accent `#5B21B6`. `accent_check.py --search cinemantsala` reports it unconstrained:
  Mäntsälä holds no other provider and sits in no `REGIONS` area. Chosen against the one
  area Mäntsälä would join if the areas were extended, Keski-Uusimaa, where of twelve
  measured candidates it had the largest worst pair at 27.2 normal / 13.4 Viénot / 13.2
  Machado. Nothing reaches 14.4 there, the area already holding twelve sub-threshold pairs
  of its own, so the bar is unreachable in a view this colour does not currently enter and
  no existing minimum moves.
- Tests: `tests/test_cinemantsala.py`, 60 tests, plus a contract sample. 24 mutations, all
  24 red after two were void: a naive `show_date` fixture that a Helsinki machine resolved
  to the same date as the good row, and a sort fixture that arrived already sorted. Both
  fixtures were rewritten rather than the assertions.
- Measured live before committing: 17 dates, 9 windows, 50 screenings to 2026-12-22, both
  screens, `check_shows` clean, 50 distinct booking URLs, and offsets `+03:00` and `+02:00`
  both present in one run, which is the DST conversion exercised by real data.
- **Published 2026-09-15** in `d216607b`: 50 showtimes over 17 dates to 2026-12-22, both
  screens, offsets `+03:00` and `+02:00` both present. Nine windows, no duplicate
  dropped, so the greedy cover met each date exactly once on this programme.

### The thirteen venues published, and the run still failed (2026-09-15)

One record for the run that published the whole week's additions, because the nine entries
above each predicted its own increment and all thirteen venues landed together.

**The run.** Cloud run `34983009141`, created 14:38:29Z on revision `437aa533`, data
committed as `d216607b` at 14:48 UTC, 344 files. Its event was `workflow_dispatch`, from
the wrapper outside this repo after its own push, not the schedule: of the four cron slots
that day only 07:55 fired, and that one predated every provider added here.

**It failed, and that is the record.** `build_pages.py` returned 3 at the final gate
because `index.html`'s generated city-links block was two links short of the city pages
the same run had just created: Hyvinkää and Kuopio became multi-venue cities. That is the
designed handoff rather than a fault, since the workflow stages `data logs teatteri
kaupunki en sitemap.xml` and never `index.html`, which carries a service-worker bump. The
pages themselves were written and committed first, 127 of them, so the failure is the
notification and not a lost publish. Do not read this run as a success.

**Everything else was green**, from the committed logs and not the Actions logs: nine new
module logs at `exit=0` with `0 failures`, `0 stale`, `0 unverified` and `0 pending` each,
`run-enrich.log` `exit=0`, `run-posters.log` `exit=0` with 70 posters downloaded and none
failed.

| verified after the run | |
|---|---|
| showtimes across the thirteen | 366 |
| provider, venue, theatre and city metadata | matches the registry on all thirteen |
| ticket destinations sampled, one per venue | 13 of 13 answer 200 |
| rated / with a poster | 338 / 325 |
| off-origin poster references, whole repo | 0 |
| theatre pages, fi and en, each once in the sitemap | 13 of 13 |
| new combined city pages | Hyvinkää and Kuopio, fi and en |
| declared and committed | 54 providers, 99 venues, 68 cities, both |
| pages per language / sitemap URLs | 113 / 227 |

**Two things the publish exposed.** `index.html`'s chooser, fixed in `9b94e89b` under an
explicit narrow exception to the freeze on that file. And the snippet test's h1
comparison, which compared escaped markup with unescaped text and so went red on the first
venue name carrying an `&`, Julia 1&2; fixed in `80bc1c76`, page unchanged because
`&amp;` was already right.

**One judgement published as read.** Cine Mäntsälä lists *Practical Magic* as K-12 on three
dates and K-18 on its "Leffa & viini-näytös". That is the cinema's own per-screening value,
a licensed-screening door policy, and `enrich_tmdb` names it as a rating disagreement
rather than overwriting either.

### Kinola: the publication policy, adopted (2026-09-15)

Kilta and Laika publish concerts and films through one WordPress `film` post type, with no
taxonomy, tag, JSON-LD, `og:type`, REST type or filter separating them, and Laika's own
filter lists its concerts under "Kaikki elokuvat". The film page is the only evidence
there is. Whether to publish a row that page cannot resolve had been open since
2026-09-14 and blocked the adapter. The findings are in
[docs/research/kinola.md](../research/kinola.md) and are unchanged by this record.

**Adopted.** Accuracy over coverage:

- Publish positively identified films, concert films included.
- Omit explicitly identified live events **and** unresolved entries. Both omit, so the
  only classification that has to be right is "this is a film".
- Never classify from a keyword in the title or synopsis alone, in either direction.
- Support evidence-backed force-include and force-exclude overrides, applied **before**
  the default classifier.
- Explicit event-level evidence of a live act prevents automatic inclusion even where
  generic metadata is present.

**The cost, accepted rather than discovered later.** A sparsely described film is missing
until an override is verified for it. How much is missing is not yet known: the sample
counted pages and rows but never the screenings behind an unresolved page, so measuring
omissions in both unique events and screening counts is a requirement of the build.

**Three corrections this decision makes to the proposal it accepted.** Recorded because
each was wrong in a way that reads plausible, which is how the first two got written down.

1. **An age classification is not film evidence.** The rule drafted on 2026-09-14 listed
   "a classification" as a sufficient structured signal. Live events carry one: the seven
   sampled Laika non-films read "Not rated" or K-18. The same file's first fixture is *A
   Fox Under a Pink Moon*, 76 min, K-16, `Tekstitys` only, called unresolved. A rule
   cannot count K-16 as film evidence and call that page unresolved in the same document.
2. **The classifier itself carries risk.** The predicate rests on seven sampled non-films,
   which supports a hypothesis and guarantees nothing about pages not yet written. The
   presence of a field such as `Lajityyppi` is therefore not automatically sufficient, and
   the exact predicate is an implementation detail to validate against the fixtures and
   the current pages rather than a value settled here.
3. **An override has to be able to change the decision.** The guard proposed alongside the
   policy would have rejected any override whose page already classifies, which would
   forbid exactly the force-exclude the policy needs: an event is worth an override
   *because* the default wrongly includes it. The guard identifies a **redundant**
   override, one that does not change the default decision. An event that has left the
   programme or a page that cannot be read does not by itself prove redundancy.

**What this does and does not unblock.** The decision is closed; the adapter is not
started, and nothing here is implemented. The requirements it has to satisfy are recorded
in the research file under "Build requirements": override scope and provenance, the
omission measurement, sold-out rows keeping the film-page href read from the source, the
four fixtures plus conflicting metadata and both override directions, one adapter for
Kilta and Laika with a handler per template, and `orion.py` left alone. Konepaja stays
out: it listed no event on 2026-09-14 and that reading is dated, so it is re-read before
it is carried forward, the same way Kino Kaustinen waits.

### Kino Kilta and Kino Laika: the Kinola adapter, under the adopted policy (2026-09-15)

Added as `scripts/providers/kinola.py`, two providers on one adapter with a handler per
template, plus `scripts/providers/kinola-overrides.json`. The policy it implements was
adopted earlier the same day; that record is "Kinola: the publication policy, adopted" and
the findings are in [kinola.md](../research/kinola.md). `orion.py` reads the third Kinola
template and is unchanged, which a test asserts by feeding it this module's markup and
expecting zero rows.

- **Konepaja is still out, re-read 2026-09-15.** `kinokonepaja.fi` renders the Kinola
  filters and a "tulossa" grid of 44 film-page links, so a count of `kinola-event`
  occurrences looks like a programme; its screening list says "Ei tulevia tapahtumia."
  The dated 2026-09-14 finding therefore stands rather than being carried forward on
  trust, and the site gets an entry when it lists a screening, as Kino Kaustinen will.
- **The classifier is the labelled director or genre field, and nothing else.** Validated
  against 65 distinct film pages that day: 53 carry `Ohjaaja`, `Ohjaus` or `Lajityyppi`
  and publish; 12 carry none. Eleven of the twelve are billed live acts and one is a
  genuine film.
- **A runtime and an age classification are not evidence, and this is not theory.**
  *Arppa* reads "130 min K-18" and *Livemusavisa* "120 min K-18", both with no director
  and no genre. Either field counted as evidence would publish every gig in Karkkila as a
  film. The correction the policy made on paper is the one the data demanded.
- **One override, in the include direction:** *A Fox Under a Pink Moon* at Laika. Its page
  fills no field but names the film in prose, "Esitettävänä elokuvana on Mehrdad Oskouen
  dokumenttielokuva A Fox Under A Pink Moon (2025)", with 76 min and K-16 beside it.
  Identity and source verified before the entry was written, as the requirements asked.
  Overrides are scoped to a provider plus the site's own `/film/{slug}/` identifier, carry
  action, reason, evidence and a verification date, and are applied before the classifier.
- **The redundancy guard is on the decision, not the page.** An `include` whose page
  already classifies is redundant; an `exclude` whose page classifies is not, and that is
  the case the first draft of the guard would have rejected. Both directions are pinned by
  tests.
- **What the policy omits, measured** on 2026-09-15 as the requirements asked, in unique
  films and in screenings: Kilta 58 screenings over 41 films with nothing omitted; Laika
  47 over 24, of which 35 publish, 11 films over 12 screenings left unresolved and none
  force-excluded. 93 of 105 screenings publish; the 12 withheld are 11.4% of the listing
  and every one of them a live act.
- **Sold-out screenings are kept**, with the film page's own href in place of the checkout
  anchor Laika drops. All four sold-out rows that day were live acts, so no sold-out film
  publishes yet and only a fixture reaches the case. A second fixture covers the sold-out
  class appearing on the anchor rather than on a span, which neither site does today.
- Two date formats, both carrying their year, so `common.resolve_year` is not used:
  `TI 15.9.2026` on Kilta and `16/09/2026 14:00` on Laika. `+03:00` and `+02:00` both
  appear in one run.
- **Kilta's rating is the `alt` attribute and not the image beside it:** the site serves
  `age-7.svg` next to `alt='Ikäraja: K-12'`. Laika's is bare text above the first
  paragraph and is read from that bounded region, so a limit quoted in a synopsis is not
  mistaken for the film's own. The two cinemas rate the same film differently, *Hetki
  ennen valoa* being K-12 at Kilta and K-7 at Laika; each publishes its own page and
  `enrich_tmdb` reports the disagreement.
- `LANG` and the venue-blanking rule come from `gilda.py`; the block, row and cell
  patterns are this module's own, as the research file predicted.
- Accents: Kilta `#1D6F8B`, constrained by Finnkino in Turku and in Turun seutu and
  measured at 52.3 normal / 53.7 Viénot / 49.1 Machado. Laika `#9A3412`, which
  `accent_check.py --search` reports unconstrained, Karkkila holding no other provider and
  sitting in no `REGIONS` area. The set's twelve sub-threshold region pairs are unchanged;
  the pinned pair total moved 146 to 148 for the two Turku views Kilta enters.
- Tests: `tests/test_kinola.py`, 72 tests, plus a contract sample. 26 mutations, all 26
  red; seven were void first and every one was a real gap in a fixture rather than in the
  code: a live act with no labelled runtime, a sold-out marker never placed on an anchor,
  a rating decoy that sat after the real value instead of standing alone, an unbounded
  header that no fixture could distinguish, no repeated row, a film-page failure whose
  site had nothing else to publish, and a budget refusal that a cap would also have
  failed. The fixtures were rewritten, not the assertions.
- **Published 2026-09-15** in `87437a3f`: Kilta 57 showtimes over 28 dates to 2026-12-16,
  Laika 35 over 10. `logs/run-kinola.log` reads `exit=0`, `2 venues, 92 showtimes,
  0 failures`, and 67 requests with 42 cache entries written, so the next run revalidates
  rather than refetching those film pages.
  **The run itself failed**, at the city-link gate and not on any provider: Turku reached
  two venues, gained a city page, and left the chooser block in `index.html` one link
  short, so `build_pages.py` returned 3 after the data had already been committed. The
  chooser was synchronised in `56723020`. Venue publication, the gate failure and the
  repair are three separate facts and are recorded as three.
  From that run's own log rather than the earlier measurement: Kilta omitted nothing,
  Laika omitted 11 unresolved films over 12 screenings and no confirmed non-films, and the
  Fox override reported `active`. Counts after it: 56 providers, 101 venues, 69 cities,
  116 pages per language, 233 sitemap URLs.

**Completed the same day: the two safeguards the first pass only half-built.**

- **The precedence is implemented, not assumed.** `classify` consulted the override before
  the labels already, but nothing proved it mattered, because every exclusion fixture used
  a plain film page. A billed live act whose page fills `Ohjaus` and `Lajityyppi` publishes
  by default, and that is now a fixture: the classifier reaches `film` on it, the exclusion
  withholds it, and the test asserts both halves so the precedence cannot quietly invert.
  A concert film and a film whose synopsis mentions a concert are unaffected, since an
  exclusion is scoped to one page and no keyword is read.
- **Three states, and only two of them a runtime verdict.** `film` and `unresolved` are
  what the classifier can reach; `non-film` is reachable only through an evidence-backed
  exclusion. The run log now says "confirmed non-film by evidence-backed exclusion" of
  those and counts them apart from unresolved entries, because the two are different
  claims and only the first is a person's. The eleven live acts at Laika stay
  **unresolved**, not confirmed: no exclusion is needed for them, since the classifier
  omits them already, and recording one would be redundant by the definition below.
- **Revalidation moved out of the tests and into the run.** The first pass had a redundancy
  helper that lived in the test file and re-stated the rule it was checking, so it could
  only prove decision semantics against a fixed fixture. `override_state` now scores every
  entry in the file against the page as it stands: `active`, `redundant`, or
  `evidence-unavailable`, one log line each. An entry is scored even when its event has
  left the programme, which is how the third state is reached and why it is not the second:
  a film going off programme proves nothing about whether its override is still needed, so
  nothing is dropped on that basis.
- Measured live 2026-09-15 after the change: Laika's own entry reports `active`, and the
  omission line reads 0 confirmed non-films over 0 screenings against 11 unresolved over
  12.
- Tests: 82 in the file, up from 72. Ten further mutations, all red; one was void first
  because `parse` never separates a vanished event from an unread page, so the `listed`
  parameter was only reachable from a direct call and is now tested there.

**Two claims narrowed the same day, before either could be read as more than it is.**

- **Precedence is not detection.** A recorded, evidence-backed exclusion outranks director
  and genre metadata; that is built and tested. A *newly encountered* live act carrying
  that metadata and no entry publishes as a film and nothing in the adapter notices. The
  new fixture proves the precedence holds once an entry exists, not that conflicting
  live-event evidence is found automatically, and no test claims otherwise. A new case is
  caught by a person reading the run log, and the remedy is one more scoped entry. Not a
  title or synopsis keyword: the policy forbids it and it would misfile every concert film.
- **`redundant` is about the decision, not the evidence.** It says an entry changes no
  publication decision today. It does not say the evidence was wrong, and it is not
  grounds for deletion, because an exclusion earns its keep exactly when a cinema that
  fills no field now fills a misleading one later and the entry turns `active` again.
  Nothing removes an entry automatically and no test requires one removed to pass.

### Kinola's listing integrity: three ways a screening went missing quietly (2026-09-15)

All three were reproduced against `656cb7e2` by driving `run.main(["kinola"])` with the
listing served from fixtures, before anything was changed.

**1. A screening block that could not be parsed was skipped.** `events_kilta` and
`events_laika` both did `continue` on a missing field and again on a `ValueError` out of
`datetime`. The block was a screening on the page and the row was gone from the schedule
afterwards; the omission report could not name it either, because that report counts what
the *classification policy* withheld and a row that never parsed was never classified. One
good row beside one malformed one published a schedule one screening short, exit 0, 0
failures. With every row malformed the site parsed to zero rows, which `fetch_site` then
read as an empty programme: `no programme published`, exit 0, stale data preserved and
nothing red.

**2. Zero parsed rows was the whole evidence for an empty programme.** Unrelated HTML --
any page that is not this listing -- produced the same exit 0 and the same line, with the
previous `area-*.json` left ageing and not even a `venues-*.json` rewritten to mark the
provider partial. That is exactly the inference `common.EmptyProgramme` forbids in writing:
"my parser found nothing" is what a markup change upstream produces while the page is still
full of films.

**3. The row class was matched as a whole attribute.** `class="kinola-event"` and nothing
else, so `class="kinola-event featured"` was not a block at all: not parsed, not published,
not counted, and with every row like that the site read as a cinema with nothing on.

**The fixes, at the narrowest layer that owns each.**

- `EVENT_RE` matches `kinola-event` as a CSS class **token**, with lookarounds on both
  sides so it neither takes a prefix (`kinola-event-title` and the other four children, and
  `kinola-events`, the container) nor requires the attribute to hold nothing else.
- A block that cannot be read raises `ListingRowError`, a `RuntimeError`, so `run.py` fails
  that site the way it fails any parse error: the files are left as they were and the other
  cinema on the module still publishes. A row whose title anchor names no `/film/{slug}/`
  counts as unreadable too -- the film page carries the classification, so reporting such a
  row as `unresolved` would dress a parse failure up as a policy omission.
- `empty_programme_evidence` is the positive evidence, and every part of it is something
  the row parser does not read: the filter widget rendered, **no** `kinola-events`
  container, and `Ei tulevia tapahtumia.` *after* the widget. Short of all three the site
  fails. The sentence is scoped to the page after the widget so a cinema writing the same
  words in its own copy cannot silence a parse that broke underneath it, which is the trap
  `test_empty_programme.py` already records for eTiketti.

**The evidence, read as a visitor on 2026-09-15, one GET per site.** Kilta 57 blocks and
Laika 47, both inside a `kinola-events` container, neither carrying the sentence; Konepaja
zero blocks, no container at all, and the sentence in a bare `<div>` after the filter form.
All three render the filter widget. The table is in
[docs/research/kinola.md](../research/kinola.md).

**What this does not establish.** One tenant in the empty state is the whole sample. Whether
Kilta or Laika would render the container empty rather than omit it is unknown, so the rule
requires all three conditions and fails conservatively if only some hold. Every one of the
104 live blocks carries `kinola-event` alone, so the token fix is hardening and repairs
nothing observed live; the two parsing fixes repair behaviour that was reachable from any
markup change.

**What did not change.** The classification policy, the override file and its precedence,
the sold-out destination rule, `budget_or_raise`, and the 1.2 s pacing between film pages.
The existing "lists N screening(s) and none published" check is a *classification* failure
and stays where it was, separate from the parse failures above.

Tests: `tests/test_kinola.py` 104, up from 82. 15 mutations, all 15 red, none void; the
test that pinned the old skip (`a row with an unparseable date is skipped not fatal`) was
replaced rather than kept, which is the one behaviour this entry reverses deliberately.

### Three Kinola claims narrowed, and one withdrawn (2026-09-15, later)

Corrections to the two entries above. The entries themselves are left as they were written;
what follows is what each of them may be read as saying and what it may not.

**"42 cache entries written, so the next run revalidates rather than refetching those film
pages" is withdrawn.** The figure is real and comes from `logs/run-kinola.log`; the
inference does not follow from it. `42 cache entries written` counts what
`common._write_slot` wrote to `.http-cache` on the runner's own disk. Whether any of it
reaches the next run is a separate question about `actions/cache`, whose save step runs
after a successful job -- and the run that wrote those entries **failed**, at the city-link
gate. Nothing here establishes that the cache survived. Until something does, assume the
pages are refetched.

A later `[run] http:` line reading a non-zero `revalidated (304)` is weaker evidence than
it looks, and weaker than this first said: the counter is per module and per run, so it
proves *some* entry was reused, not that these 42 were. Comparing it against the film-page
count does not close the gap either -- that was the second answer here and it is no better,
because neither number identifies an entry. Only URL-level evidence would, and there is no
reason to build it: the forecast it would defend has been withdrawn, and what the cache
does is visible in the aggregate line on every run anyway.

**And revalidating would not save the time it was quoted for.** A conditional GET is still
a request: `common.fetch` sends `If-None-Match`, the origin answers 304, the round trip
happens. `kinola.fetch_site` sleeps 1.2 s between film pages either way, because the sleep
is pacing and not a download. So even perfect revalidation saves response bodies, not the
deliberate waiting, which is where the time is.

**"A newly encountered live act is caught by a person reading the run log" is wrong.** The
log names what the policy *withheld* -- `confirmed non-film`, `unresolved`, and the titles
of each -- and it counts what published. It never names a published title. An act wrongly
included therefore reads as an ordinary film in the log and gives a reader nothing to
chase; it is noticed on the site or in the data, by someone who knows the programme. The
standing limitation is unchanged and is if anything larger than it was written.

**"Closing that gap would mean reading a word out of a title or a synopsis" claims more
than was measured.** That keywords would misfile every concert film is established, and the
policy forbidding them stands. That keywords are the *only* route left is not: no other
structural signal was looked for -- a ticket type, a venue field, a programme list the
cinema publishes itself -- so nothing rules one out. The adopted policy does not change on
this; what changes is that the alternative is now open rather than closed.

Nothing here adds an override, changes the classifier, or relaxes the keyword rule.

### A price is published only where it is established (2026-09-16)

Three adapters gained a price that morning and two of them were wrong within hours. The
rule the maintainer stated, now in `CLAUDE.md` and on `common.Show`: an exact amount only
where its applicability to *that screening* is established, otherwise nothing. A note in a
docstring saying the figure is sometimes 0.50 or 2.50 out does not make it right, and the
reader does not read the docstring.

**TMB withdrawn entirely.** Its tariff is real and one request per venue away, but two
things sit between it and a screening and neither is readable: 2D and 3D differ by 2.50 with
no marker on any row, and the `+0.50` covers weekday public holidays as well as the weekend.
Together they leave no screening settled, weekend rows included. The price page fetch went
with the field -- there is no point asking a cinema for a page nothing publishes -- and what
the page holds is recorded in the module docstring and `docs/research/prices.md` so the
finding survives the withdrawal.

**Iso-Hannu narrowed to the part its tariff settles.** `Pe-su ja arkipyhä 14,50 €` fixes
Friday, Saturday and Sunday whatever else the day is, so those publish. `Ma-to 13,50 €`
does not fix a weekday, because the same line puts an *arkipyhä* on the dearer tariff, so
those publish nothing. Both amounts are still read, because a block stating one cannot say
which days it covers. Live at the time: 67 showtimes, 37 priced where it was 67.

**Kirkkonummi tightened on ambiguity rather than on the rule.** Its amount is attached to a
film rather than derived from a rule, which is why it survived: 14,50 and 15,50 both appear
on the page and each belongs to its own film. What changed is that a heading with two
*different* amounts under it now publishes neither, where it used to take the first. Nothing
in the markup delimits a film's block, so a stray `Liput NN,NN` attaches to the heading
above it; where that happens the association is what is in doubt, and taking the first
publishes the doubt. The same amount twice is not ambiguous, which is what the page's
duplicated programme produces for every real film.

**Corrected in the same pass:** "not located" was written as though it settled something for
Cine Mäntsälä and Bio Savoy. It does not. Only the page each adapter already fetches was
read; Cine Mäntsälä's MyCloudCinema `show_times/` payload was never inspected for a price
field and neither site's own ticket pages were looked for. They are unfinished research and
are recorded as such.

Tests: `test_tmb.py` 20, `test_isohannu.py` 29, `test_kirkkonummi.py` 27. Four mutations
across the three, all red: an ambiguous association publishing one of its amounts, Monday
to Thursday publishing the cheaper figure again, the weekend publishing the weekday figure,
and TMB publishing anything at all.

### Kuvakukko and Manttu publish their tariff, and four rows do not (2026-09-16)

The three price sources `docs/research/prices.md` still listed as unread were read that
day. Bio-Kaari's is closed. Kuvakukko's settles both its cinemas, and the maintainer's
instruction on it is the one implemented here: publish the venue's tariff where its
applicability is established, leave an externally sold or otherwise ambiguous screening
unpriced, do not infer applicability from an on-site link alone, honour an explicit
screening-specific price or exception, fetch the page once a run, and blank the amount
where the source is unavailable or ambiguous.

**Why this tariff settles a screening.** `/liput/` states
`Liput: 11,50 € / 9,50 €` under `Kino Kuvakukko liput` and `Liput: 11 € / 9 €` under
`Kino Manttu liput`, and makes neither figure depend on a day, a format, a running length
or a kind of film. There is no *arkipyhä* clause to check against a calendar, no 2D/3D
difference to find a marker for, and neither block prints the "hinnoitellaan erikseen"
escape Mäntsälä's page does. Nothing about the row is left to read, which is the test the
rule states.

**What established that `11 € / 9 €` is ordinary and concession.** The programme page the
adapter already fetches carries Manttu's line in full, with the parenthesis naming who the
second figure is for: students, pensioners, conscripts, the unemployed and under-12s. Two
statements on the cinema's own site, and the question `IDEAS.md` and the research file had
left open since 2026-09-15 is answered by the page itself, not by a reading convention.

**The two ways the tariff is taken back.**

- *An outside organiser's screening.* A series, a film club or a festival billed under its
  own name is sold by whoever runs it, and the house statement does not reach it. Both
  signals are read, the label on the row and a destination that leaves this site, because a
  label can link here and an outside sale can go unlabelled. On the day it was written the
  two agreed exactly: four Kuopio rows, `Hopeatähti-sarja: Laula minulle Arja`,
  `Hyvät Kuvat-kerho: Perfect Blue` and two `Vilimit-festivaali:` rows, each labelled and
  each linking to isak.fi or hyvätkuvat.fi.
- *A row stating its own amount*, which outranks the tariff because it is the more specific
  statement. No row does today. Two amounts on one row publish neither.

**An on-site link is not evidence that the tariff applies**, and the code does not treat
it as any. The house statement stands where neither signal is present, so
an unlinked ordinary row -- `Klo 15: Autofiktio (viimeinen näytös)`, printed without a page
because the film is ending -- is priced, and a series row that happens to have a page here
would not be.

Live at the time: Kuopio 32 of 36 rows at 11,50 €, Nilsiä 9 of 9 at 11 €.

**Published in `c796413c`, 05:16 UTC, and the committed data says the same thing.**
`logs/run-kuvakukko.log` reads `kk-kuopio: 36 showtimes, 9 dates, 32 priced (tariff 11.5€)`
and `kk-nilsia: 9 showtimes, 3 dates, 9 priced (tariff 11€)`, and `data/area-kk-kuopio.json`
carries 32 rows at `11.5€` against 4 blank while `data/area-kk-nilsia.json` carries 9 at
`11€`. The four blanks are the outside organisers' rows, unchanged from the reading above.
That is one run agreeing with one local parse of the same pages hours earlier. It says
nothing about a week of programmes.

**Bio-Kaari is closed.** Its `/liput/` prices 2D at 14 €
`viikonloppuisin ja pyhinä` and 13 € on a weekday, 3D a euro dearer, children's films at
12 €, and adds `Korotettu lipunhinta normaalia pidempiin elokuviin. Korotus 1-2 €`. Four
conditions, none readable: *pyhinä* needs a calendar, the surcharge states neither a
threshold nor a single amount, "lasten elokuvat" is not defined anywhere machine-readable,
and the format is not published at all. Unlike Iso-Hannu's, the weekend does not survive
either, because the length surcharge and the children's rate can both land on a weekend
row. Its own pages carry no amount to fall back on: the weekly `Elokuvat, näytösajat ja
hinnat` posts publish the week as a JPG, and the `/tapahtuma/?event={id}` page the adapter
already fetches contains no `€` at all. The showtime link goes to the websales flow, which
is not called.

Tests: `tests/test_kuvakukko.py`, 35, of which 17 are new. Twelve mutations, all red:
two tariff statements under one heading publishing the first, a disclaimer being ignored,
one cinema named under two headings with the last winning, an organiser's label ignored, an
off-site destination ignored, an on-site link being *required* rather than an off-site one
being disqualifying, two amounts on a row taking the first, the tariff outranking the row,
the amount keeping its trailing zero, the tariff never reaching the show, a row's own text
running to the end of the day's paragraph, and a failed `/liput/` failing the site. The
last row-boundary mutation survived its first test. The test was at fault: it put the
amount on the earlier row, where an overrunning tail cannot be seen. The fixture puts it on
the later row now, which is the direction such a tail leaks.

### TMB reads the film page after all, for the runtime (2026-09-16)

The adapter shipped on 2026-09-15 with the film page deliberately unread, and the reason
written into its docstring: one request per distinct film per venue, about 68 a run against
a third party, to publish a runtime. The maintainer looked at Kino-Toijala on the site,
found the rows carrying no length, and asked for it. That makes the trade theirs, and the
entry above is superseded. Its cost figure was right; whether that cost was worth paying
was never mine to decide.

**The page gives three fields for that one request.** `Kesto`, `Kuvaus` and `Lajityyppi`,
all in one shape -- `<p class="info">Label: <b>value</b></p>` -- so the parser reads labels
instead of positions, so a field the operator adds or drops changes nothing. Measured on
two live pages 2026-09-16: `1 tuntia 27 minuuttia` -> 87 and `2 tuntia` -> 120, with genre
`kotimainen` and `fantasia`, and a Finnish synopsis on both. A text stating no duration
publishes no runtime instead of a `0`. That is Bio Savoy's `XXh 00min` lesson, applied
before it could happen here.

`film_facts_by_id` is Bio Savoy's shape: one page per **distinct** film, paced 1.2 s,
cached, and bounded by `common.capped` rather than `budget_or_raise`, because these pages
carry no screening. The list view is parsed before any of them is asked for, so a film page
that 500s costs that film its metadata and never a cinema its programme.

**What was also on that page, and is not published.** Each screening on it carries its own
`Hinta: 14.45€ / 12.45€ / 11.45€`, and the Saturday row reads 14.95 where the weekday reads
14.45. That is the operator stating what a given screening costs rather than a tariff
waiting to be applied, so it is not the thing withdrawn hours earlier the same day, and it
would satisfy the rule the withdrawal was made under. It is still a decision the maintainer
has not made, and reading the page for a runtime is not a way to make it quietly. A test
pins that `film_facts` returns the three metadata fields and no amount.

Tests: `tests/test_tmb.py`, 27, of which 7 are new plus a rewritten one. The test that
pinned "one request per venue and no more" pinned the decision this entry reverses, so it
is gone; what replaces it asserts the order and that a repeated film is fetched once. Seven
mutations, all red: a page per showtime instead of per film, the budget dropped, no
duration becoming a `0`, hours-only runtimes ignored, an empty synopsis published as a
`_syn`, a failing film page failing the site, and the runtime and genre fields swapped.

### TMB's price comes back, from the screening's own line (2026-09-16, later)

Withdrawn that morning, published again that evening, and the two are not the same claim.
What was withdrawn was the **tariff**: 14.45 € plus 0.50 at weekends, applied to rows whose
format nothing states and whose *arkipyhä* status no calendar here knows. What is published
now is the `Hinta:` line the film page prints under each screening, which the adapter began
fetching hours earlier for the runtime. The operator has applied its own tariff there, so
the two gaps that sank the first attempt are not questions any more: the Sunday row reads
14.95 € where the same film's Wednesday reads 14.45 €, and the maintainer confirmed the
+0.50 covers weekends and public holidays alike.

The first of the three figures is the ordinary admission, and that is read rather than
assumed: `?hinnat=2` prints Aikuinen 14.45, Eläkeläinen 12.45 and Lapsi 11.45 in that
order, and the film page prints those three numbers in that order. The other two need a
card at the counter. The tariff page is still fetched by nothing, and the price costs no
request that was not already being made.

Keyed by the screening's own minute, so neither page's ordering matters and a screening the
film page does not list stays unpriced. Two amounts under one screening publish neither:
only the next date delimits a block, so a row the parser cannot read would otherwise leave
its amount attached to the screening above it.

Tests: `tests/test_tmb.py`, 36. Eight mutations, all red: a concession published as the
price, two amounts for one minute keeping the last, a block holding two amounts taking the
first, a block running past the next screening, the price keyed by the day rather than the
minute, an unlisted screening taking some other row's amount, and the amount losing its
cents.

### Kino Myyri, and four Johku storefronts, published (2026-09-18)

Five cinemas in one push, `f360a09c`, verified on the runner by the dispatch that
committed `ca17dc58` at 18:17:30 UTC.

**Kino Myyri**, Vantaa, is a third tenant on `kinola.py`. Its row prints no year, so the
weekday selects it through `common.resolve_year` inside a 30/120 day window, and a row that
cannot be placed raises. Its ticket link is `/checkout/{uuid}`, a booking endpoint, so the
showtime opens the film page instead. 25 screenings listed, 23 published; the two left are
Yksityisnäytös and Yksityistilaisuus, which the site's own pages describe as the products
it books private events with. A dubbed print carried no labelled director or genre and is
included by an override entry rather than dropped.

**The four Johku storefronts** are Bio Marilyn (Lapua), Vihdin Kino (Vihti), Bio Forum
(Tammisaari) and Kinokulma (Oulainen), 66 showtimes over four new cities. The 2026-09-05
Johku entry concluded the show list needs the widget's API key; it was reading a WordPress
site with the widget embedded, and a cinema whose whole site is the storefront renders the
programme server-side. `data-showtime` is a UTC instant and the clock printed beside it is
read as well, so a row where the two disagree fails the site. A day group is sliced by
counting its own divs, because the coming-soon shelf that follows the last group renders
the same item markup. Cloudflare answers these hosts with 103 Early Hints, which
`http.client` reports as the final status, so the module reads through it with its own
response class. That worked on the runner as well: 39 full fetches, no refusal.

**What is left out, and what is not.** A grid item with no time is a coming-soon entry (14
at Bio Marilyn), and a row under `/fi_FI/products/` is hall hire (2 at Kinokulma). Nothing
else. A film page that answers nothing costs its row the genres and the synopsis and not
its place, on the maintainer's instruction of 2026-09-18, so opera, ballet, a memorial
screening and a stand-up show publish. Prices stay empty, because the tariff pages state
bands. Artwork stays empty for the four, because the storefront's images are landscape
banners, 2048x1365 and 2048x857 on the two measured; Kino Myyri's own 2:3 posters publish.

**A synopsis declares its language now that a site publishes more than one.**
`common.syn_language` scores disjoint function words across fi, sv and en, with a Finnish
route through case endings that opens only when Swedish and English score nothing. Three of
twelve Finnish blurbs at one cinema were refused without it. Four texts across the five
cinemas settle no language and are withheld rather than filed.

**Accents.** Kino Myyri is #807CFC: 14.6 dE00 against Bio Grand in Vantaa, and 10.1 against
Kino Engel in Pääkaupunkiseutu, where no colour in the L* band clears the floor against
twelve chains. Pairs below the floor went from 12 of 148 to 14 of 163 and the regional
minimum is unchanged at 4.5. Vihdin Kino is #AC7CD4, chosen against Keski-Uusimaa's six
chains although Vihti is in no region row, because Nummela is a locality of Vihti and is in
that row: 14.9 on the weakest model, 20.6 to normal vision.

Tests: `tests/test_kinola.py` 130, `tests/test_johku.py` 30, `tests/test_syn_language.py`
11, plus a Johku sample in `tests/test_show_contract.py`. 34 mutations, all red after three
VOIDs were investigated: one removed a redundant empty-input guard, two were covered by new
tests. `tests/test_landing_pages.py` now skips the film title in its euro check, as it
already skipped the synopsis, because Bio Marilyn names three screenings "(5€)" and a title
publishes verbatim.

### Ritz Vaasa and Tähti Kino, and Vihti joining Keski-Uusimaa (2026-09-18)

`tribe.py` reads The Events Calendar, a WordPress plugin whose REST route is public:
`{base}/?rest_route=/tribe/events/v1/events&per_page=50&start_date=...&categories={id}`.
Published in `d17d65da`, verified on the runner by the dispatch that committed `8ef45c0e`:
`run-tribe.log` exit=0, Ritz Vaasa 6 showtimes over 4 dates and Tähti Kino 3 over 1, the
same counts the local snapshot carried.

**A sweep sized the platform before any of it was built.** 148 of the Filmikamari
directory's 152 hosts, one request each, four aggregators dropped. Four answered the route
and two are cinemas: ritz.fi with 56 events under category `Kino` (id 19) and muhos.fi with
35 under `Elokuvat` (id 106). The category is declared per site by its numeric id, because
the display name moves with the site's language, and the parser checks that every event
came back carrying it, so a filter the server ignored fails the site instead of publishing
a council meeting.

What the two sites settle differently: Ritz publishes portrait film artwork (1500x2138,
1080x1592) and Muhos the same 768x470 calendar illustration on every film, so only Ritz
carries posters and the TMDB pass fills the rest. `cost_details.values` decides the price,
one value publishing and two being a band, which left 4 of Ritz's 6 priced and all 3 of
Muhos'.

**Iobio, Inkoo, is the third host and is not read.** Its films carry no category of their
own, sit in the generic `Tapahtumakalenteri` and `Evenemangskalender` rows, and are marked
only by an "IoBio:" prefix in the title, with each screening appearing once under each
language. Two screenings were listed when it was read. Both exceptions are ones this
repository has already written against: `johku.py` separates hall hire by a path because
"no word in a title is read", and the Kinola classifier decides on labelled evidence for
the same reason. A bilingual dedup has to pick a canonical row across two calendars, and
getting it wrong publishes twice in one direction and drops a screening in the other, with
nothing in a count to show either. It becomes an ordinary adapter the day Iobio publishes a
film category of its own or a single calendar.

**Vihti joined Keski-Uusimaa the same day.** The row already held Nummela, which is a
locality of Vihti municipality 10 km from Vihdin Kino, so a reader opening that row saw
Kino Akseli and not the other cinema in the same municipality. The longest hop in the area
is unchanged at Hyvinkää to Nummela, so `km` stays 45, and Vihdin Kino's accent clears the
floor in the row it now enters: 14.9 dE00 on the weakest model against BioRex and 26.0 to
normal vision, with none of its six new pairs below 14.4. The shared-view total went 164 to
170 and the count below the floor stayed 14.

Vihti is conventionally Länsi-Uusimaa, and a row of that name would also pick up Karkkila
and Tammisaari. These rows are commuting areas rather than maakunnat, so that is its own
decision with its own accent measurements, and it was not allowed to block this one.

**The `km` field was left at 45 and is not asserted to be right.** The first version of the
registry comment claimed the longest hop stays Hyvinkää to Nummela; a review asked for that
to be measured rather than repeated. Distances between the row's towns, measured 2026-09-18
through a public geocoder and router, in kilometres:

    pair                    road    straight
    Vihti - Kerava          73.8     42.7
    Nummela - Kerava        64.7     43.9
    Nummela - Järvenpää     63.5     45.2
    Vihti - Järvenpää       58.1     42.3
    Nummela - Hyvinkää      51.8     44.9
    Vihti - Hyvinkää        46.3     37.8
    Vihti - Nummela         11.8      9.8

So the claim was wrong twice over: the longest hop was not the pair named, under either
metric, and Vihti moves the road maximum from 64.7 to 73.8 while leaving the straight-line
maximum at Nummela to Järvenpää, 45.2.

**Which metric `km` stated was never settled, and the field was deleted instead.**
Itä-Uusimaa's 65 matches Sipoo to Loviisa by road (64.1; straight 53.3) and Kymenlaakso's
55 matches Kotka to Kouvola by road (56.6; straight 46.5), while Keski-Uusimaa's 45 matches
a straight line and not its road distance of 63.5. At least one of those readings was
wrong.

Re-measuring all fourteen was declined on 2026-09-18 because it buys nothing: nobody
consumes the field. `build_regions.py` never mentions it, `REGION_KEYS` leaves it out of
`data/regions.json`, `index.html` has no match for it and no test read it. It was a comment
written in dict syntax, and a number nobody consumes and nobody measures is a claim waiting
to go stale, which this repository has already paid for five times in its counts. So the
field is gone and the reasoning it annotated stays in prose: Sipoo still stretches its area
furthest and is still kept because the cinema city it is nearest to is Porvoo. The two
sentences that leaned on a figure lost the comparison rather than keeping an unsourced one.
A radius, if one is ever genuinely needed, gets measured once on one stated metric with the
source recorded.

Tests: `tests/test_tribe.py`, 21. Eleven mutations, all red: trusting the category filter,
reading only the first page, ignoring the UTC stamp, reading the local stamp as UTC,
publishing a band as a price, publishing any image as a poster, dropping the width floor,
publishing an all-day event, filing an unplaceable synopsis as Finnish, treating every
empty answer as an empty programme, and accepting a renamed category. A twelfth, a guard on
the `timezone` field, went VOID and the guard was deleted: a zone with another offset
already fails the stamp comparison.


### Kino Hamina, and the Helsinki feed that priced itself out (2026-09-18)

Moved out of `IDEAS.md` on 2026-09-19, with its heading, once the cinema had published and
the only open half had an entry of its own.

`hamina.py`: 14 screenings over 5 films on one page, one request, a new city. `book="door"`
because the page says "Ei ennakkovarauksia. Lipunmyynti alkaa n. 30min ennen elokuvan
alkamista!" in its own words, so a showtime opens the programme page and no ticket host is
invented. The film's `Liput:` line is that film's price and a screening line carrying
`| Liput 8€` overrides it for that showing; a range or an "alkaen" figure there settles
nothing. `OG` and `DUB` are the page's own legend and become `FI-S` and `FI-A`. A block
whose second paragraph holds no readable line is a film with nothing scheduled, counted
and left out, and a line the weekday cannot place raises rather than disappearing.

**Published 2026-09-18** in the run that committed `ade246db5`: `logs/run-hamina.log` reads
`exit=0`, `1 venues, 14 showtimes, 0 stale, 0 unverified, 0 pending, 0 failures`, 14
showtimes over 5 dates, one host attempted, `www.hamina.fi`.

**Kino Helios is not built, and the feed was assessed before deciding rather than after.**
One accent buys one venue: over 2026-09-18 to 12-31 the Kulke events service carried 725
events, 94 of them type 29 across seven houses, and only Malmitalo has a standing cinema
brand, 37 rows of which 26 are `Kino Helios` with a ticket link. The rest is festival
programming, a children's week and a three-row free-Monday series. Declined on the accent
rather than on the reading: no colour in the L* band clears the combined-city floor against
Helsinki's eight chains, 0 of 226,580 swept, best reachable 12.2. That would be the first
exception the city rule has ever taken, so it stays a policy question about a full city and
keeps its own `IDEAS.md` entry. Evidence:
[docs/research/ticketing-platforms.md](../research/ticketing-platforms.md).

### Kinotour, and the towns it visits that this repo does not list (2026-09-18)

Moved out of `IDEAS.md` on 2026-09-19, with its heading, once the runner had read it.

`kinotour.py`: one request to `kinotour.fi/varaa-liput-elokuvatapahtumiin/`, which renders
the whole programme as one Events Manager table, one row per screening. Three new cities,
Kyrö, Naantali and Lieto.

- **A town this repository does not declare is counted and named, never dropped in silence
  and never a failure.** A touring operator visits a new town as a matter of course: its
  own `/locations/` list ran to Karkkila, Ikaalinen and Piispanristi as well as the three
  on the programme. Failing the site on one, the way `johku.py` fails on an undeclared
  hall, would turn the routine case into breakage, so the run log carries a line per run
  until someone adds the town to `SITES`. Same shape CLAUDE.md gives `reads`.
- **The venue is keyed on the town, not the hall.** `Kyrö kurkisali, Kyrö` is hall then
  town, and the hall is what changes while the tour keeps coming back.
- **Only a rating-shaped tail comes off the title**, because `Ryhmä Hau, Dinoelokuva, K7`
  is a title with a comma in it.
- **The time is the one with a colon.** The cell flattens to `su 27.09.2026 14:00`, and a
  dot-tolerant pattern read the 27.09 of the date as 27:09 and raised on the hour.
- `EMPTY_VENUES_CONFIRMED` is set: the table is the whole published programme, so a
  declared town it does not mention is known empty and gets a fresh empty file instead of
  ageing its last visit.

**Verified on the runner** in the dispatch that committed `f7b77ff71` at 21:33 UTC on
2026-09-18: `logs/run-kinotour.log` reads `exit=0`, `3 venues, 10 showtimes, 0 stale, 0
unverified, 0 pending, 0 with no programme, 0 failures`, one host attempted. Kyrö 3 over
1 date, Naantali 3 over 1, Lieto 4 over 2. **The undeclared-town path has not fired in
production yet**, and neither has the confirmed-empty one: every row that run named one of
the three declared towns. Both are covered by fixture only until a tour reaches a fourth.

### The four small cinemas, one commit each (2026-09-19)

Moved out of `IDEAS.md` on 2026-09-19, with its heading, once the four run logs had been
read and the enriched snapshot measured.

Four towns that carried no cinema here, one bespoke parser and one commit each, all four
accents measured together first: Marita `#849666`, Lieksan Kino `#2A5A9C`, Navettakino
`#E45CC0`, Pyhäsalmen VPK `#725466`, worst pair among them 18.9 dE00, all `book="door"`.
Built 2026-09-19.

- **Marita**, Outokumpu: 3 screenings, one request plus a film page per film; empty
  confirmed on the site's own "Ei tulevia näytösaikoja".
- **Lieksan Kino**: 7 screenings over 4 films, one request; zero rows fail, no capture of
  this template being empty.
- **Navettakino**: 2 screenings, a weekend list in prose over a shelf of blocks; an empty
  weekend is confirmed and a missing heading raises.
- **Pyhäsalmen VPK**: 6 screenings from the My Calendar REST route, category by id, price
  from the cinema's own page.

**What closed it.** The entry's next action was to read the four run logs, because the
local snapshot the adapters shipped with carried no TMDB field yet. All four logs read
`exit=0` with one venue, one host attempted and no failure: `run-marita.log` 3 showtimes
over 2 dates and 2 films with 2 film pages read, `run-lieksa.log` 7 over 3 dates and 4
films, `run-navetta.log` 2 over 1 date and 2 films, `run-vpk.log` 6 over 6 dates and 3
films priced 12 €. Measured in the committed `data/area-*.json` at `73a075acc`, every
showtime of all four now carries both a `tmdbId` and an `img`: Marita 3/3, Lieksan Kino
7/7, Navettakino 2/2, Pyhäsalmen VPK 6/6. Nothing in the four renders an initials tile.

Neither of the two paths that only a later programme can exercise has fired in production:
Marita's confirmed-empty answer and Navettakino's missing-heading raise are covered by
fixture only.

### Bio Pallas, Karjaa: a Wix page whose structure is its document order (2026-09-19)

biopallas.com, a 1923 funkis cinema in Karjaa, in the municipality of Raasepori. Probed as
a visitor on 2026-09-19: the apex 301s to www, www answers 200, `server: Pepyaka` behind
Fastly, no CF-Ray and no challenge on any of twelve requests.

- **The programme is the front page and there is no second request.** `<title>Ohjelmisto/
  Program</title>`, and `pages-sitemap.xml` lists three URLs in all, the root and two
  standing pages. No film page, so no synopsis and no runtime beyond the one line the row
  carries.
- **Server-rendered, checked rather than assumed.** Wix often keeps content in a payload,
  so all 60 `<script>` blocks were grepped for the day's titles and none carries one. The
  only `/_api/` strings are Wix platform infrastructure. The titles are in the markup and
  nowhere else, which is what makes the site buildable under the visitor's-public-interface
  rule.
- **Nothing keys on a component id.** The `comp-` prefix changes on every page edit, and
  the `__item-` ids repeat across days. What is stable is the order of the rich-text
  elements and the images, so a row is the block holding both a date and a `Klo` time, its
  title is the block before, its price the block after, its poster the last image before
  its title.
- **The coming-soon block is excluded by shape, not by its heading.** Its five entries
  carry a title and a bare date in separate blocks, with no time, so requiring the date and
  the time together drops them and a renamed heading cannot let them back in.
- **One amount settles a price.** Ten rows read `13€`, two matinees read `12€ med
  kaffeserv./kahvitarjoilulla`, which is one amount with a description of what it includes,
  and the touring concert reads `22/25€`, which is two with nothing on the row to choose
  between them and publishes none. The site states no house tariff at all.
- **The poster is checked for shape on every run.** The `<img>` carries no `src`;
  `<wow-image data-image-info>` holds escaped JSON whose `imageData.uri` names the file on
  static.wixstatic.com, with its own width and height beside it. Every poster measured
  across six readings is portrait and the page's one landscape image is its hero, outside
  every row.
- **`book="door"`,** in the site's own words: reservations by telephone and Facebook
  Messenger, and no film row carries a ticket URL. The one row that does is the 23.9
  concert, whose link goes to a third party's shop belonging to a separate organiser; it
  was not fetched and is not published, because this repo does not call a booking endpoint.
- **Zero rows fails the site.** Six readings over fourteen months all rendered a programme.
  The site does write a per-day closure block, in four different spellings across the
  captures, which is evidence about a day rather than about the programme, so it cannot
  carry an `EmptyProgramme` gate. A closed day is counted and named in the log.

**Accent `#546C78`.** Karjaa holds no other chain and sits in no REGIONS area, so nothing
binds it today. Fitted to the row a Lansi-Uusimaa extension would create, against Bio Forum
in the same municipality, Kino Laika, Kino Olympia, Kino Akseli, Vihdin Kino and Kino
Vaakuna: 18.6 dE00 on the weakest model, 21.1 to normal vision. 4.7 from its nearest accent
anywhere, Bio Säde and Laitilan Kino, which is as far as the L* 38 to 60 band reaches with
70 accents in it. The colours that scored better inside the row all sat on top of Kino
Tapiola.

**Verified against the cinema's own page**, not against the run log: thirteen screenings
over six days, the same four titles, the same times and the same prices the page prints,
and a poster on all thirteen. Twelve of the thirteen carry a `tmdbId` after enrichment; the
thirteenth is the concert, for which TMDB holds no record and none was forced.

**Routing settled cloud, 2026-09-19.** The first committed `logs/run-pallas.log`, from the
dispatch that commited `1ac89b049` at 12:52 UTC: `exit=0`, `1 venues, 13 showtimes, 0
stale, 0 unverified, 0 pending, 0 with no programme, 0 failures`, one host attempted,
1.8 s of fetching. No 403 and no challenge body, so the runner reads `www.biopallas.com`
as an ordinary visitor does and `where="cloud"` stands as written rather than as a guess.

Worth recording beside it: **that same run was challenged on twelve other domains.** Seven
modules failed together with a 12 kB interstitial titled "One moment, please..."
(cinemahouse, kirkkonummi, kinotour, lieksa, navetta, tmb, vpk) and Nexxo with plain 403s,
while Bio Pallas on the same run came back clean. Read from an ordinary connection minutes
later, all six hosts checked served their real pages. That is the reading side, the same
pattern `common.served()`'s docstring records from 2026-09-16, and it is why this entry
reports what the log says about *this* host rather than about the run.

### Elokuvateatteri Huvimylly, Raahe: a programme typed freehand (2026-09-19)

huvimylly.com, the cinema in the Tapahtumatalo hall in Raahe. The site names itself
Elokuvateatteri Huvimylly eight times on its own front page and in its `<title>`; "Bio
Huvimylly" is what the nytleffaan.fi directory calls it, and that directory separately
lists the same street address as "Raahesali", which is the hall rather than the operator.
The cinema's own name is the one published.

- **The route was chosen after checking for a screenings API and finding none.**
  `/wp-json/` lists no plugin namespace holding events, `/wp/v2/types` has only the core
  types plus `elementor_library`, and `/wp/v2/posts` is empty. The programme is typed by
  hand into one page, so the adapter reads
  `/wp-json/wp/v2/pages?slug=etusivu&_fields=id,modified_gmt,content`: the same markup as
  the front page at a tenth of the transfer, 4 kB against 45 kB, with `modified_gmt`
  besides. Neither the page nor the route carries an ETag or a Last-Modified, so there is
  no conditional request to make.
- **The rating marker is what closes a title, not the line break.** A title can run across
  two list items, and a free-text note sits in the same position; the captures carry both.
  So a `Klo` line carrying a marker is complete, a `Klo` line without one takes the next
  item only if that one carries a marker, and otherwise the row is left out. Guessing
  would publish `elokuvan jälkeen ilmainen pullakahvitarjoilu` as part of a film title,
  and the title is the key for `normTitle()`, `films-extra.json` and `tmdb-aliases.json`.
- **The marker is anchored to the end of the line, and that was a failing case rather than
  taste.** An unanchored pattern read the final `s` of `Koiramies-k7/4-` as an S rating and
  published the title as "Koiramie". Twelve marker shapes from the captures are read,
  including `-k 16/13` with no closing dash and `-k?`, which closes a title and states that
  the rating is unknown.
- **A line that cannot be placed is left out and counted, and the site fails when more fail
  than succeed.** The captures hold `Klo?`, a dotless `Klo 1900`, a placeholder row reading
  `elokuva avoin` and a row with no title at all. Raising on each was the first design and
  was rejected on the measurement: one capture carries four placeholder rows at once, so an
  operator's ordinary week would fail the whole site and age every other row with it. The
  guard that stays loud is the ratio: unplaceable lines outnumbering distinct start times
  means the template moved.
- **The anchoring on the heading pattern is load-bearing twice.** It rejects
  `Sunnuntaina  7.12024-`, where a year is typed straight onto the month, and it rejects
  `Paddington seikkailee 24.1 alkaen`, which without it would be read as a heading on the
  weekday "seikkailee" and would place a phantom screening. A lookahead that tried to do
  the same job could not be made to fail on its own and was removed.
- **The price is the standing line and it settles every row.** `Liput  vain 10-€` carries
  no weekday, hall, age or format condition and no row states a price of its own. It is
  parsed from that line each run rather than hardcoded, and a line naming two amounts
  publishes none. The gift tickets and the five-ticket book on another page are separate
  products and are not read.
- **No poster is published from this site.** The four images sit in their own list items
  with no alt text, no link and no title, and their order is not the rows' order: the
  2026-02-17 capture runs `vin`, `lm`, `humiseva-harju`, `kaija`, `otso` against rows
  Vinski 2, Kaija Koo, Luottomies, Humiseva Harju, Otso Karu. The filenames are
  hand-abbreviated, the counts disagree with the row counts in both directions across the
  captures, and two captures use a landscape still. The TMDB pass supplies them instead,
  and all four rows carry one.
- **The page's first item carries the operator's private email address.** It is read only
  for the price amount, and the parse carries no line's text out with it: the report counts
  what it could not use rather than keeping it, so there is no field a later change could
  print. `tests/test_contact_address.py` refuses any address in any tracked file.

**Accent `#CC60A0`.** Raahe holds no other chain and sits in no REGIONS area. Fitted to the
row a Pohjois-Pohjanmaa extension would create, against Elokuvateatteri Star and Finnkino in
Oulu, Bio Rex Kokkola and Pyhäsalmen VPK: 18.9 dE00 on the weakest model, 21.5 to normal
vision, and 4.8 from its nearest accent anywhere, Elokuvateatteri Elo. A fully saturated
magenta scored 19.5 and 5.7 and was passed over at saturation 0.94, the same call
Navettakino's entry records making at 0.60. Measured against Bio Pallas on the same pass,
the day's only other addition: 14.8 dE00 apart.

**Four titles, four aliases, and the reason each is one cinema's wording.** The cinema
writes a film's name the way it would say it, so none of these is a marker a shared cleaner
should strip: `Dome Karukosken Rakkautta ja virtahepoja` carries the director's name in the
genitive, which is what TMDB's own record names as the director; `Kerro se kaikille` is one
word longer than the `Kerro kaikille` five rows at other chains publish; `Pirjo` is the
short form of the `Pirjo i Sverige` Laitilan Kino publishes; and the 14.00 line reads
`Saapasjalkakissa` then `unohdettu saari`, where the cinema's own poster for that slot is
named unohdettu-saari and TMDB registers FI "Unohdettu saari" on 1465063.

**Local, and it cannot run yet.** The 403 to a non-residential address is the evidence, and
routing local on a 403 needs no runner evidence. What it does need is a block in the wrapper
outside this repository, which nothing in here can add: until it exists the venue ages after
the snapshot committed with the adapter.

### The Huvimylly wrapper block landed, and the entry closed (2026-09-19, later)

The preceding record ends "it cannot run yet". It can. The local half's wrapper outside
this repository gained a `huvimylly` block the same day, and the run it produced was
committed by `kino-local` in `f1803a9f2` at 15:48 +0300: `logs/run-huvimylly.log` reads
`exit=0`, 4 showtimes over 1 date, 4 films, all priced 10€, one host attempted
(`www.huvimylly.com`), one full fetch and no failures. `data/area-huvimylly-raahe.json`
carries those four rows. The venue no longer ages after its snapshot, so the `IDEAS.md`
entry "Elokuvateatteri Huvimylly waits on a wrapper block" is closed and removed there.

The counts were re-measured on the same tree before the entry came out, because closing a
provider item is where a carried-over count has gone wrong before: 71 providers, 118
venues, 84 cities from `build_pages.load_venues()` and `city_of()`, 118 `data/area-*.json`
files, 9 `where="local"` providers over 31 venues. All unchanged, so nothing in "Provider
coverage" was rewritten but the Huvimylly clause.

### Movie Company Alatalo: one page, five towns, and Huvimylly's own operator (2026-09-19)

moviecompanyalatalo.fi, a touring operator: Pudasjärvi Pohjantähti, Haapajärvi
Teatterisali, Kiuruvesi Kiurusali, Toholampi Toholampisali, Kemijärvi Kulttuurikeskus.
Five new cities. Read over the live page and eleven Wayback captures, 2023-03 to 2026-06.

- **The same person types huvimylly.com**, which carries the same contact address, so the
  line grammar is one grammar and `alatalo.py` imports `RATING_RE`, `TIME_RE`, `STRIP` and
  `WEEKDAY_WORD` from `huvimylly.py` rather than copying them. The precedent for an adapter
  importing another's tables is `from gilda import FORMATS, LANG`.
- **The grey background span on four of the five headings is not the marker.** Toholampi
  never carries it and Haapajärvi lost it in 2024-12, so a parser keyed on it would have
  filed two towns' screenings under the town above. The venue is keyed on the town name.
- **An unrecognised heading clears the venue.** Kinotour reads the town out of each row, so
  an undeclared one costs only its own rows; here the rows follow the heading, so the
  alternative is publishing them under the wrong town. The cost is false positives: `Suomen
  Ensi-ilta` took two rows in the 2023-12 capture, against seven that `Ylivieska
  Akustiikka` in the same capture would otherwise have misfiled under Kiuruvesi.
- **Only a place-name-shaped first word reaches the log**, one alphabetic word of 4 to 20
  characters with a capital initial. The page's header carries the operator's private
  address and mobile, and no line's text leaves the parse.
- **Four widenings over `huvimylly.py`**, each against a line this page carries: a bare
  `k?` closes a title (2 of the live page's 13 rows), a leading time with a marker and no
  `Klo` is a row, `Kl` reads as `Klo`, and a year may be glued on with a dot. The guard
  that refuses `7.12024` still holds. A fifth difference is a softening: a row with no date
  heading is counted rather than raised, because the 2024-08 capture heads Pudasjärvi
  `Maanantaina 9.` with the month left off and raising would cost four other towns.
- **Empty has positive evidence and is seasonal.** 2025-08 lists all five towns under
  `ELOKUVAT JATKUU SYYSKUUSSA`; 2025-04 lists all five with nothing under them. Town
  headings and no `Klo` line raises `common.EmptyProgramme`; no town heading at all fails.
- **http only.** 443 refused the connection on 2026-09-19 and the apex has no A record.
  The only `http://` base in the repository. Ticket link is the page: cash at the door.
- **No poster**: the images are hand-named, sit outside the rows and match no capture's
  order. TMDB supplies them, and two aliases were needed for the operator's own typos,
  `Saapasajalkakissa` and `Kero se kaikille`, each verified off `/movie/{id}`.

**Accent `#6C9678`.** None of the five towns holds another chain or sits in a REGIONS area,
so it enters no shared view today and was fitted to the rows an extension would create:
Pohjois-Pohjanmaa 14.8 dE00 on the weakest model, Ylä-Savo 19.7, Keski-Pohjanmaa 21.6,
Lappi 34.6. Binding pair Tähti Kino at 14.8; Huvimylly itself 16.9 away. 4.1 from its
nearest accent anywhere, Korjaamo Kino, against a median nearest-neighbour distance of 2.8
across the 71 existing accents, 45 of which sit below 4.1. Nothing in the L* 38-60 band
clears 14.4 in all four rows and reaches 5.0 anywhere.

**First run, from an ordinary connection:** 13 showtimes in 4 town headings, Toholampi
confirmed empty, all priced 10 €, 2 placeholder lines left out. Every row carries a TMDB id
and a mirrored poster. `where="cloud"` on the 2026-09-18 sweep, which read this host from a
non-residential address; the runner log settles it the way Bio Pallas's did.

### Cinema Sheryl, Espoo: the fourth Kinola tenant, in two languages (2026-09-19)

sheryl.fi, a student-run cinema in the Marsio building on the Aalto campus in Otaniemi.
First of the five from the nytleffaan diff. An existing platform, so a `SITES` entry and a
template rather than a parser.

- **`listing: "/"`.** Its `/ohjelmisto/` answers 404 and the front page is where the
  `kinola-event` blocks are, 71 of them when read.
- **The listing localises and the film page does not.** With the Finnish header
  `common.TEXT_HEADERS` always sends, the rows read `su, 20.09 15:00`; with no
  accept-language at all they read `Sun, 20.09 15:00`. The first probe of this site used
  curl without the header and saw English, the first real fetch saw Finnish and failed on
  it, and that is how the negotiation was found. The pattern reads both: it costs one
  alternation, and a site that answers in two languages can answer in either.
  `_sheryl_weekday` tries `common.weekday_index` first, which places `su` and `ti`
  whichever language they came from, and the English map covers the other five.
- **The film page is in English whatever the listing said**: `<strong>Director</strong>`,
  `Cast`, `Language`, `Subtitles`, in Laika's shape. `FILM_LABELS` was Finnish only, so
  every one of the ten screenings classified `unresolved` and the site published nothing.
  Adding `director` and `genre` is the same evidence in another language, not a widening
  of the policy: `default_state` still never returns `non-film`.
- **`_events_no_year` is now shared with Myyri** rather than copied a fourth time. Both
  print no year and let the weekday select it; only the date pattern and the weekday
  language differ.
- **The ticket link is `/checkout/{uuid}`**, the same booking endpoint Myyri has, so the
  showtime opens the film page. `Access and ethics` keeps this repo out of it.
- Not read: `_lang` maps Finnish language names, and this tenant writes `Cantonese` and
  `English`, so its rows carry no language tag. The synopsis is English and `syn_language`
  files it there; one of the five film pages settled no language and was withheld.

**Accent `#9E60C2`.** Espoo already held Finnkino and Kino Tapiola: 42.0 and 19.8 dE00 on
the weakest of the three models, both clear of the 14.4 floor. Pääkaupunkiseutu is the
crowded row where 14.4 is reachable for nothing -- its own minimum is 4.479, Bio Grand
against BioRex -- so the binding rule there is not lowering it, and this sits 8.19 from its
nearest in that row. Four of its fifteen new region pairs fall below the floor, which takes
the repository count from 14 of 170 to 18 of 185, for the reason Kino Myyri's entry already
records. 5.5 from its nearest accent anywhere, Savon Kinot, which shares no view with
Espoo. L* 51.3, saturation 0.51.

**First run, from an ordinary connection:** 10 showtimes over 4 dates, 5 film pages read, 0
unresolved, 0 failures. Checked against the cinema's own front page the same minute: the
same ten rows, same titles, same times, a mirrored poster and a TMDB id on every one.
`where="local"` on the instruction of the day, to be revisited if a committed runner log
proves otherwise; the three other Kinola tenants stay cloud and routing is per site.

### Haapamäen Elokuvat: the fifth Johku storefront (2026-09-19)

haapamaenelokuvat.fi, the village cinema in Haapamäki, run by volunteers for the HPP
sports club, 120 seats. Second of the five from the nytleffaan diff and the cheapest of
them: an existing platform, an existing parser, one `SITES` entry and one registry line.

- **The storefront is `hpmenelokuvat` on cdn.johku.com** and the listing is the same
  `showgroup` / `daytitle` / `js-grid-show` markup the other four serve, eight day groups
  when read. Nothing in `johku.py` changed.
- **`loc` is `Sali 1`**, the hall the rows carry in `data-location`.
- **The town is Haapamäki, not Keuruu.** The cinema names itself after the village and
  publishes that address; Keuruu is the municipality it belongs to and is not what a
  reader looking for this cinema types. Same call Kinotour's entry records for Kyrö.
- **No price**, like the other four: the Johku widget takes its amounts from an API that
  needs the widget's key, which is the Kino Engel deferral.

**Accent `#E644FE`.** Haapamäki holds no other chain and sits in no REGIONS area. Fitted
to the row a Keski-Suomi extension would create, against Finnkino and Kino Aurora in
Jyväskylä, Kino Metso across its three towns, Kino Hirvi in Äänekoski and Kinotar 123 in
Jämsä: 18.4 dE00 on the weakest of the three models. 4.9 from its nearest accent anywhere,
Kino Piispanristi in Kaarina, which shares no view with it. L* 60.0, saturation 0.73;
everything that scored better in the row sat above 0.95, which is the saturation
Elokuvateatteri Huvimylly's entry records passing over.

**First run, from an ordinary connection:** 11 showtimes over 8 dates, 5 film pages read, 0
failures, first try. Checked against the cinema's own front page the same minute: the same
rows, same dates, same times, same hall.

**The test harness needed pinning, not the adapter.** `tests/test_johku.py` ran
`run.main(["johku"])` with no half, which is "all" on a laptop and "cloud" on Actions; with
four cloud sites and one local that is five sites here and four there, and the film-page
count would have differed between them. It now passes `--half all` explicitly, which is
the trap CLAUDE.md records under "Pipeline changes".

### Forssan Elävienkuvien teatteri: a listing of films, a page of screenings each (2026-09-19)

elavienkuvienteatteri.fi, Finland's oldest operating countryside cinema, 1906, 77 seats.
Third of the five from the nytleffaan diff and the only one of them that runs on no
platform: its own Foxy CMS, server-rendered, so a plain fetch is the whole of it.
`scripts/providers/elavienkuvien.py`, one listing request plus one film page per film.

- **The sub-navigation shares the film links' path space.** `ohjelmisto/` holds
  `erikoisnaytokset/`, `esityskalenteri/` and `mykkaelokuvafestivaalit/` beside the twelve
  films. The listing is sliced to `movielifts` and the rows are read from `lift` blocks, so
  the three nav pages are never fetched; matching the path across the document would have
  fetched them and published whatever they parsed to.
- **The poster is the listing's, not the film page's.** Both exist and only one is a
  poster: measured that day, `{slug}-list.jpg` on the listing is 316x474 portrait and
  `{slug}.jpg` on the film page is an 835x369 banner. Publishing the film page's would put
  a cropped landscape still where every other chain has a poster.
- **An unscoped image search took the age-limit icon.** A lift with no poster fell through
  to `agelimit_12.png` in the same block, which would have published an icon as a poster.
  Caught by the test written for the missing-poster case, not by reading the code.
- **The screening line carries its own year**, `su 20.9.2026 klo 17:00`, so nothing is
  inferred and the printed weekday is not read at all.
- **A date with no clock time is left out and counted.** Six of the thirty on the day this
  was written: `pe 2.10.2026` and nothing after it, a film announced for a day before its
  time is set. Raising on one would cost the other eleven films their schedule every time
  the cinema announces a date early; inventing a midnight would publish a screening that
  does not exist. eTiketti's reader makes the same call.
- **The rating is the age image's file name and nothing else**: `agelimit_12.png`, no alt,
  no title, no text beside it. `kinola.py` records the opposite case, where Kilta's file
  name disagreed with its own alt; here there is no second source on the page, so it is
  corroborated against other chains instead and every value matched. `agelimit_notset` is
  the site's own "no rating" and produces none.
- **Two amounts and no price.** Every row ends `13€ / 11€`, adult and reduced, and the row
  settles neither.

**Accent `#2E8C92`.** Forssa already held Bio-Kaari, so this creates the combined city view
and its accent must clear the floor in it: 39.5 dE00 apart on the weakest of the three
models. Forssa is in no REGIONS area, so that is the only view it enters, which takes the
repository count from 185 pairs to 186 with none added below the floor. 5.9 from its
nearest accent anywhere, Studio 123 Järvenpää, with Savon Kinot the nearest teal at 6.1 and
sharing no view with it. L* 53.4, saturation 0.68.

**First run, from an ordinary connection:** 12 films listed, 24 screenings over 12 dates, 6
rows left out for having no clock time, 0 failures. Every row carries a TMDB id and a
mirrored poster. Checked against the cinema's own film pages: Hetki ennen valoa on 22.9 at
17:30 and 24.9 at 17:30, and Lapin Sota's lone `pe 23.10.2026` correctly withheld.

## Kino Hannikainen, Nurmes (2026-09-20)

Built as the sixth Johku storefront: one `SITES` entry against `johku.py`, no parser.
`www.kinohannikainen.net` is the storefront on the cinema's own domain, and its root
renders the same `showgroup`/`daytitle`/`js-grid-show` listing as the other five. Read
2026-09-20: eight rows over five day groups, every one `data-location="Hannikaisen sali"`,
the 250-seat auditorium in Nurmes-talo named after the composer Pekka Juhani Hannikainen.
First fetch published 8 showtimes over 5 dates with no failures.

Accent `#1188DD`. Nurmes holds no other chain and no `REGIONS` area holds Nurmes, so the
accent enters no shared view and the 14.4 floor binds nothing. 4.2 dE00 from its nearest
accent anywhere, Kino Piispanristi in Kaarina; L* 55.0, saturation 0.92.

`base` is the cinema's host rather than `johku.com`, which keeps its pacing group its own;
a test pins that.

Tests: `KinoHannikainenTest` in `tests/test_johku.py`, 2 tests, plus the updated base list
and film-page count the new site moves. **Four mutations red, shared with the Kino Virta
entry below**, because the two sites are pinned by the same assertions: swapping either
site's declared hall reddens the hall test, and moving either site's `base` on or off
`johku.com` reddens both the pacing-group test and the platform-domain test. The four are
not four per entry; they are four across the pair.

## Kino Virta, Kalajoki (2026-09-20)

Built as the seventh Johku storefront. The cinema has no storefront domain of its own:
`virtasali.fi` is the municipal hall's WordPress page and every ticket button on it points
at `kinovirta.johku.com`, which is what a showtime links to and what this reads. Read
2026-09-20: four rows over two day groups, all `data-location="Virta-sali"`. The cinema
names itself Kino Virta; Virta-sali is the hall, in Kauppa- ja kulttuurikeskus Merta.
First fetch published 4 showtimes over 2 dates with no failures.

**The 2026-09-05 sweep recorded this site as "no Johku" and was wrong.** That pass read
the page for an embedded Johku *widget*, which it has none of; the storefront was one link
away on a different host. The research file is corrected rather than rewritten, because
the mistake is the reusable part: an embedded widget and a storefront are different
things, and only one of them is visible in the page's own markup.

This is the only site read from `johku.com` itself, so its pacing group is the platform
host. A second site there would share it, which is correct and has to be deliberate rather
than a copied `base`; a test pins that it is the only one.

Accent `#CC1188`. Kalajoki holds no other chain and no `REGIONS` area holds it. 4.1 dE00
from its nearest accent anywhere, Gilda; L* 45.7, saturation 0.92.

Tests: `KinoVirtaTest` in `tests/test_johku.py`, 2 tests. **The same four mutations the
Kino Hannikainen entry records**, not four more: `tests/test_johku.py` went to 34 tests
covering both new sites, and two of the four mutations redden a test in each entry.

## Elokuvateatteri Matin-Tupa, Ylistaro (2026-09-20)

On none of the platforms, so its own parser. Founded 1941. The programme is a
server-rendered Toolset view on the cinema's own WordPress, one `<div class="col-sm-6">`
per film. A structured source was looked for first and there is none: `/wp-json/` lists
340 routes and no namespace holding screenings, `/wp/v2/types` has the core types plus
Kadence and Toolset furniture and no film type, `/wp/v2/posts` is a news feed whose newest
entry is from August, and the `kategoria` taxonomy has `ohjelmistossa` at count 0.

One request to `/ohjelmistossa/`, one row per `Esitysajat:` line. First fetch published 13
showtimes over 7 dates across 4 films.

What the design rests on:

- **No date carries a year**, and the weekday is abbreviated to two letters, so
  `common.resolve_year` places it with `common.weekday_index` selecting on the weekday.
- **A price publishes only when the `Liput:` value is one bare amount.** Three films read
  `14 €` or `13 €`; the fourth read `14,00 €. Kts. lisätiedot`, a Neulekino evening sold
  with a 3,80 € serving and a members' discount the row does not state, so its rows publish
  no price. Documenting that the figure is sometimes conditional is not a substitute.
- **The poster is the cinema's own `alignleft` image and its dimensions are in the
  filename**, because Toolset's resizer writes them there: 235x336 and 236x336 on the live
  page. A landscape file is refused and the TMDB pass supplies a poster instead. Five were
  mirrored on the first run.
- **The rating is the KAVI icon's filename**, `ikaraja_12`, because the page prints no
  rating text.

**Ylistaro, not Seinäjoki.** Ylistaro has belonged to Seinäjoki since 2009, and the cinema
gives Ylistaro as its own address. Filing it under Seinäjoki would also put this accent in
that city view beside BioRex at 8.3 dE00 on the weakest of the three models, below the 14.4
floor. Nilsiä under Kuopio and Haapamäki under Keuruu are the same call already made.

Accent `#448855`; 4.1 dE00 from its nearest accent anywhere, Bio Grani; L* 51.3,
saturation 0.50. `book="door"`: the box office opens 30 minutes before the day's first
screening and reservations are taken by telephone and email, and the site sells nothing
online.

Tests: `tests/test_matintupa.py`, 21 tests, plus `sample_matintupa` in
`tests/test_show_contract.py`. Eight mutations red, none void: a landscape file accepted as
a poster, the price pattern unanchored, the weekday dropped from `resolve_year`, the window
dropped, the hours ignored in the runtime, the rating blanked, an empty parse published
instead of failing, and `soldOut` published as a string against the show contract.

## Kino Kuusamotalo, Kuusamo (2026-09-20)

On none of the platforms, so its own parser, over `/wp-json/wp/v2/posts`. 520 seats in the
Oulankasali hall of the town's culture house, run by its own operator on its own site.
`kuusamotalo.fi` is the culture house and only links to the cinema: its programme block is
a Flockler embed and it names no film. First fetch published 8 showtimes over 6 dates from
2 film posts of 5.

What the design rests on:

- **`Esitysajat:` is what makes a post a film, not its category.** Both notices on the site
  sit in `nykyinen-ohjelmisto` beside the films, and one of them in `tuleva-ohjelmisto` as
  well. They carry no `Esitysajat:` line, are counted and named in the log, and are left
  out.
- **No date carries a year** and the weekday is two letters, so `common.resolve_year`
  places it. **The clock may omit its minutes**: `klo 15` and `klo 13.30` both appear.
- **A dated line with no clock publishes nothing.** `Pirjo i Sverige` read that day was
  `Pe 9.10. alkaen.` and carried no `Esitysajat:` line at all. Reading an hour out of such
  a line would be inventing one.
- **No poster is published from this site.** The featured images are the cinema's own
  uploads at 160 px wide, 160x228 and 160x240 on the two films read, against the 342 px
  `mirror_posters` downscales to and the client renders from. Nothing is upscaled, so
  mirroring one would serve a blurred half-width image where the TMDB pass supplies a full
  one.

Accent `#AA8844`; 4.6 dE00 from its nearest accent anywhere, KinoMania in Pieksämäki;
L* 58.6, saturation 0.60. Kuusamo holds no other chain and no `REGIONS` area holds it.
`book="door"`: the site sells nothing online and the desk opens an hour before the
screening.

Tests: `tests/test_kuusamotalo.py`, 22 tests, plus `sample_kuusamotalo` in
`tests/test_show_contract.py`. Eight mutations red, none void: the category read instead of
the `Esitysajat:` marker, the clock's minutes made mandatory, the dateless coming-soon line
left uncounted, the price pattern unanchored, a synopsis published with no language
settled, a non-list answer accepted, the window dropped, and a row published under an
undeclared venue id against the show contract.

