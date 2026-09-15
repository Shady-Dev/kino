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
- **Not yet published.** No run has fetched it, so `data/venues-isohannu.json` does not
  exist and the committed pages still count 86 venues. The first cloud run adds Rauma as
  the 58th city, takes the pages to 99 per language and the sitemap to 199.
