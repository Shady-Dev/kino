# Ticketing platforms: what each one publishes and how it is read

Research notes, moved out of `IDEAS.md` on 2026-09-14 so that file can stay an index of
open work. Open items live in `IDEAS.md`, the dated decision records in
`docs/archive/2026-09-providers.md`, and accepted working rules in `CLAUDE.md`. Nothing
here is a rule.

Every reading below was taken as an ordinary visitor, through the same public interface
the cinema's own site uses. Booking, payment and administrative endpoints are not called
and are not inventoried; see "Access and ethics" in `CLAUDE.md`.

Each topic separates what was observed from what was concluded, because several
conclusions here were wrong the first time and the observations were not.

---

## BioRex

**Findings** (biorex.fi, probed 2026-08-26)

WordPress with `admin-ajax`. No auth, no nonce, no Cloudflare block. Twelve requests per
run, since `date=-1` returns every date at once.

```
GET  https://biorex.fi/elokuvat/                      # session cookie
POST https://biorex.fi/teatterin-valinta/   location={venueId}
POST https://biorex.fi/wp-admin/admin-ajax.php?lang=fi
     action=br_movies_handler&genre=-1&date=-1&format=-1&language=-1&activeType=showtimes
```

- The response is `{"posts": "<html>"}`: HTML inside JSON.
- **The cookie step is required.** Without it the answer is BioRex Verkatehdas rather
  than an error, so a missing session is wrong data, not a failure.
- `?cinema_id=` in page URLs is decorative; the cookie decides the venue.
- `f_cinemas={slug}` handles the within-city sub-filter (`all` / `helsinki` / `redi`).
- Each `.showtime-item` carries a `data-click-data-layer` JSON attribute with `movieId,
  movieName, showId, showCinemaId, showCinemaName, showDate, showTime, showDateTime`
  (ISO, +03:00) and `showWeekday`. That attribute is the data; text scraping is not.
- Also in the item: `.showtime-item__place__value` ("BioRex Tripla, Sali 6"),
  `.showtime-item__movie-rating` ("(K-16)"), `.showtime-item__format` (`["EN","FI&SV"]`,
  audio then subtitles), `icon-puhekieli` for a Finnish dub, a poster `data-srcset`
  (1080w variant on `web.biorex.mycloudcinema.com`) and a booking href through
  `biorex.fi/secure-redirect/`.
- Venue ids: 13 Helsinki Tripla, 14 Helsinki Redi, 1 Hämeenlinna, 9 Hyvinkää, 7 Kajaani,
  4 Pietarsaari, 10 Porvoo, 8 Riihimäki, 2 Rovaniemi, 12 Seinäjoki, 3 Tornio, 5 Vaasa.
- Dates are sparse (27–31.8, 1–3.9, then 5.9, 9.9, 11–13.9, 30.9): special events, not a
  rolling window. Read the `#dayselect` options rather than generating dates.
- Missing against Finnkino: runtime, genres, synopsis, sold-out state. TMDB covers
  rating, trailer and poster through `movieName`; runtime needs the film page.

**Inferences and open questions**

- `<input type="date">` cannot disable individual days, so dimming the sparse dates would
  need a custom picker. Deferred, and still unbuilt.
- Whether the sparse pattern is scheduling policy or a publishing lag was never
  established, and nothing here tests it.

**Status and next step**

Live as `scripts/providers/biorex.py`, twelve venues, cloud half. **Correction, checked
2026-09-14:** this note used to say the HTML-in-JSON is parsed "with BeautifulSoup". It is
not, and never was in the committed adapter. `biorex.py` parses with stdlib `re`
(`ITEM_RE`, `DL_RE`, `HREF_RE`), and `bs4` appears nowhere in the repository. See
`tooling-evaluation.md` for the measurement behind keeping it that way. No next step.

---

## Nexxo Scope

**Findings** (kinoset.fi, probed 2026-08-26; ten hosts swept 2026-08-29)

A WordPress plugin with a clean JSON API, so adding a cinema on it is a `SITES` entry
rather than a parser.

```
GET {base}/wp-content/plugins/nexxo-scope/public_api.php
    ?action=exportdailyshows&locationid=N&days=21&lang=fi&upcoming=0
-> {"shows": {"YYYY-MM-DD": [ {...} ]}}
```

- `upcoming=1` returns the coming-soon list with `startDate: null`; use `upcoming=0`.
- Fields: `movieTitle, startTime, klo, roomTitle, ageLimit, duration, genre,
  priceIncludingTax, posterurl, showId, code_language, code_subtitles, showTypeTitle`.
- Posters need the prefix `{base}/wp-content/plugins/nexxo-scope/banners/`.
- `code_subtitles` can be multi ("FI-SE") and splits to `FI-S, SE-S`; `OV` means
  unspecified. `code_external_title` is a distributor code, not a title.
- No per-show booking URL, so a showtime opens the programme page filtered to the
  location. That is why every Nexxo provider is registered `book="reserve"`.
- Kinoset ids: 1 Huittinen (Kino 1-2), 2 Loimaa (Kinema), 3 Sastamala (Bio). Their film
  week runs Friday to Thursday and is published on Tuesdays.
- The same API also exposes write actions. Not used, not probed.
- **A host is not a venue.** `ksek.fi` and `kinoaurora.fi` are one deployment with
  identical payloads at locationid 1 and 2; adding both would have published every
  showtime twice under two chain names in one city. `kinohirvi.fi` serves Bio Säde on
  locationid 4, in Mänttä, about 80 km from Kino Hirvi, while `biosade.fi` serves an
  empty programme. Ids were discovered by asking the endpoint, not by reading host lists.

**Inferences and open questions**

- Three hosts have answered 403 under load (`Server: LiteSpeed`, `openresty`, `Apache`,
  no CF-Ray), which reads as the origin rather than an edge. Whether closely spaced runs
  cause it is an open question that would need probing a third party's server to settle,
  so it stays an observation. See "A run reads unrelated hosts at once" in
  `docs/archive/2026-09-pipeline.md`.

**Status and next step**

Live as `scripts/providers/nexxo.py`, eight providers on six hosts, cloud half. No next
step; a further Nexxo cinema is a `SITES` entry.

---

## eTiketti

**Findings** (kotkanleffat.fi, probed 2026-08-26; second template 2026-09-02)

The API host `{customer}.etiketti.app/api/yleiset/...` sits behind Cloudflare, so the
adapter reads the cinema's own server-rendered pages instead.

```
/elokuvat/ohjelmistossa      -> movie links /elokuvat/{id}/{slug}
/elokuvat/{id}/{slug}        -> every screening for that film
```

Per screening, inside `<div class="item ... date-D.M.YYYY">`:

- the `date-27.8.2026` class carries the full date including the year; the time comes
  from `klo HH.MM`;
- `TRIO 123 | VIP-SALI`, but **Kinopalatsi screenings have no room and no `|`**, so the
  room has to be optional in the pattern. Requiring it silently dropped 17 showtimes.
- `Lippu 18,00€` and `Vapaat paikat 13/22` give the price and a real sold-out state.
- The booking link is `/salikartta?id=NNNN`.

Film level: `<h1>` title, `ikarajat/fi-16.svg` for the rating, `Kesto: 2 h 53 min` for
minutes, `Kieli:` / `Tekstitys:` for language tags, `<img class="poster-img">` for the
poster. About one listing plus fifteen film pages per run, paced 1.2 s apart.

**A second template exists.** Cinema Niagara renders screenings as `<div\n class="item
tampere date-3.9.2026">` with `<div class="time"><span>16.15`, `<div class="show-price">
13,00€`, `Paikkoja vapaana: 126/127`, tags in `movie-specs` and no place line, where Kotka
prints `KE 2.9. klo 20.00`, `TRIO 123 | SALI 2`, `Lippu 15,00€`, `Vapaat paikat 27/35`.
Labels carry no colon and genres sit under a label reading `genre`. `/?shows=all` renders
every screening twice, in a desktop and a mobile wrapper, which is why a screening is
keyed on its `/salikartta?id=` href.

**Only six of the twenty hosts render a theatre navigation** (measured 2026-09-14, one
listing per host), and the `match` text has to be looked for *inside* an anchor rather
than compared to the whole of it: Leffabuumi prints "Mikkeli Kinolinna" against the match
`kinolinna`.

**Inferences and open questions**

- Counting film links on a listing proved less than it reads as: Cinema Niagara served the
  listing and rendered its screenings in a template the parser of the day read as zero.
- The nineteen hosts without a navigation cannot have an empty venue confirmed, so they
  keep the previous file. That is the safe side and is not a defect to chase.

**Status and next step**

Live as `scripts/providers/etiketti.py`, twenty providers and twenty-nine venues, four of
them on the local half. No next step.

---

## Vista, public XML services

**Findings** (savonkinot.fi 2026-08-27, korjaamokino.fi 2026-09-05)

Vista is the platform Finnkino also runs. A site that leaves its `/xml/` services open
needs no auth and is a `SITES` entry with a base URL and a venue list. Test a candidate
with `{base}/xml/TheatreAreas/`.

```
GET {base}/xml/TheatreAreas/                     -> ID + Name per area
GET {base}/xml/Schedule/?area={id}&nrOfDays=31   -> every Show in the window
GET {base}/xml/ScheduleDates/                    -> published date list
GET {base}/xml/Events/                           -> per-film synopsis, cast, credits
```

- No auth, no Cloudflare, datacenter addresses fine.
- `nrOfDays=31` is honoured, so one request per area covers the window. A one-day fetch is
  not enough: Kitee had 0 shows today and 7 in the window.
- Areas map to one or two theatres and each Show carries `TheatreID`, so venues split from
  the data.
- The richest field set of any provider: `OriginalTitle`, `LengthInMinutes`, `Genres`,
  `PresentationMethod`, four poster sizes, nested language elements with ISO codes and a
  per-show deep link in `ShowURL`. No seat counts.
- Shapes that need handling: `Rating` is `"K-7 (4)"` or `"Sallittu kaikenikäisille"`
  rather than a bare `"K-7"`, which a kids filter would silently miss; `dttmShowStartUTC`
  converts through `Europe/Helsinki`; `SubtitleLanguage2` can carry a `Name` with an empty
  ISO code; `TheatreAuditorium` is `"Joensuu, Tapio 4"`, so the city is stripped and a room
  repeating the venue is blanked; synopsis tag names vary between versions.
- Finnkino's own host answers a plain client a Cloudflare challenge (403, `cf-mitigated:
  challenge`, probed 2026-09-13) and is read through OCAPI with a token instead. Its
  `/xml/` was never probed past the challenge.

**Inferences and open questions**

- Cinamon and other non-Finnish Vista users are untested.

**Status and next step**

Live as `scripts/providers/vista.py`, one site: Korjaamo Kino. Savon Kinot left Vista for
eTiketti on 2026-08-30. Next step, if anyone wants it: probe a non-Finnish Vista customer.

---

## Johku

**Findings** (kinoengel.fi 2026-08-29, four known Johku cinemas 2026-09-05)

Johku is the shop behind the button, not a listing template. Each cinema renders its
programme with its own site builder, so there is no shared parser to write.

The Engel chase, six rounds of probing, and why it stopped: the film page renders a table
with the year, the auditorium, the per-screening price and a booking button, cleanly
classed (`_kj_showtime_*`), and none of it is in the 81 kB the server sends. The path was
`johku.com/kinoengel/allproducts.json` 403 (wrong path); `widget-module.js` publishes the
shop id and locale; `settings/public.json`, `storefrontsettings.json` and
`widgets/{id}.json` are public; `categories/2/allproducts.json?details=true` is 200 with
781 products but carries only the next show per product; per-product detail is empty, 404
or 403; the `rs-johku-wordpress` loader hands off to an authenticated widget call. The show
list is reachable only with the widget's `X-ApiKey`, which is the line "Access and ethics"
draws.

The sweep of the four known sites, read 2026-09-05:

- **Kino Tapiola** (Espoo): its own WordPress theme. Johku is the basket embed and a
  per-film schedule widget drawn client-side. The programme is server-rendered on
  `/elokuvat/`, one `div.movie-list-movie` per screening with the date and year. The slug
  is per run (`autofiktio-4`, `-5`, `-6`), so the `eventId` cannot be the slug. No age
  rating on the film page, no `og:image`, no per-show booking URL.
- **Kulttuurimylly** (Helsinki): Squarespace, programme only inside `<johku-widget>`
  filled by `johku.com/widget.js`. The storefront is a Nuxt app whose `__NUXT_DATA__`
  carries `showschedule-*` keys, empty on the day because public screenings resume in
  autumn 2026.
- **KuvaTähti** (Kuvala, Kauttuan Kuva): the storefront sits behind Cloudflare and loads
  showtimes client-side through `/api/auth/widget-session` and `X-ApiKey`, the route
  declined above. Both venues listed nothing during a maintenance break.
- **Virtasali** (Kalajoki): WordPress, no Johku, a municipal culture hall with 0 of 12
  events in `category-elokuvat`. Dropped.

Two probe details worth keeping: Cloudflare answers the storefront with an HTTP 103 Early
Hints interim response, which `urllib` reports as the final status while curl reads
through it; and `?k=elokuvat` needs quoting in zsh.

The same 2026-09-05 pass found **Korjaamo Kino is a Vista site** with the public services
open, and **Kino Regina** runs a WordPress theme whose own `getShowtimesMoviesV2.php`
returns the day list as server-rendered HTML.

**Inferences and open questions**

- The two wrong assumptions that cost round trips: that the first 403 meant a closed API,
  and that `widget-module.js` rendered the table. Find the code that builds the URL before
  trying URLs.
- Kulttuurimylly is worth re-reading when its programme resumes: if the `showschedule-*`
  array fills, the storefront HTML is the read.
- A headless render of one Engel film page was measured on 2026-09-13: 6 s to a settled
  DOM, and the widget's own table carried date, time, hall and price per screening, the
  times matching the committed rows exactly. It would need Chrome on the local machine and
  about fifteen pages a run.

**Inferences the data settled against us**

Johku looked like a platform win and is not one. Three integrations, three HTML shapes.

**Status and next step**

Kino Tapiola got its own parser on 2026-09-05 (`scripts/providers/tapiola.py`). Kino Engel
is read from its front page and keeps `price` and `aud` empty; the headless-render option
was deferred by the maintainer the same day, with no more polling on the local half for
now. KuvaTähti and Kulttuurimylly stay unread. Next step: none open.

---

## The 2026-09-15 candidate batch: nine names, one cinema

**Findings** (each host read once as a visitor, 2026-09-15)

The nine candidates `IDEAS.md` carried. Classified by fingerprinting the host and then
verifying against the endpoint an adapter would need, never on the fingerprint alone.

- **Bio Salo, Bio Stara, Bio Jukola** run `nexxo-scope` and answer `public_api.php` with
  `{"shows": []}` at every locationid 1-5, `days=60`, `upcoming=0` and `upcoming=1` alike.
  Their sites render no `/ohjelmisto` and no clock time anywhere; the only programme-ish
  link is `/tilausnaytokset/`, which is group hire. The 2026-08-30 reading that they are
  permanently empty therefore still held sixteen days later. Each also carries a Johku
  fingerprint the 2026-08-30 note did not record, so the shop is Johku while the
  (empty) programme is Nexxo.
- **Kino Kaustinen** is a real eTiketti tenant: `etiketti.app` on the page, the
  `/elokuvat/ohjelmistossa` listing served, `/salikartta?id=` answering with eTiketti's
  own "Linkki vanhentunut" and a "Powered by eTiketti" footer. Its id space is its own,
  not Bio Rex Kokkola's: `/elokuvat/3216` is "The Odyssey" on biorex.org and a 404 here,
  and 3168 is a different film on each, so the two would not double-publish. **It has no
  screenings.** The listing renders "Ei ohjelmistoa saatavilla", the front page
  "Ohjelmistossamme ei ole näytöksiä tällä hetkellä", and `etiketti._classify_no_films`
  run against the live listing raises `EmptyProgramme`, which is the sanctioned path. Its
  `/ohjelmisto` page states a Monday update adding the next Fri-Thu week; none was
  published for the week this was read. `/elokuvat/tulossa` does list coming films, so
  the cinema is alive rather than closed.
- **Iso-Hannu**, Rauma, is on none of the platforms here and got the batch's one parser.
  See `scripts/providers/isohannu.py`.
- **Kino Kirkkonummi** is WordPress with Elementor. Its showtimes are hand-authored
  `elementor-icon-list` text ("20.9. Sunnuntai klo18.00"): no year, no room, no booking
  host among its outbound links, and no semantic class around the time. Parseable only by
  reading page-builder markup that carries no contract.
- **Teatteri Union** is WHS's stage, not a cinema. Its own words: a programme of
  "visuaalista teatteria, eläviä kuvia ja poikkitaiteellisia esityksiä". The four events
  on `/esitys/` when read were concerts and performances, one of them titled
  *elokuvaton*. `/ohjelmisto/` renders nothing server-side.
- **"Julia" was the wrong cinema.** This entry read `turunleffat.biokuva.fi`, a local
  cinema-history archive, and closed the candidate as a defunct Turku house. The page is
  genuine and the reading of it was right; the identity was not. The operating cinema is
  **Julia 1&2 in Hyvinkää**, `juliaelokuvat.fi`, and it was added on 2026-09-15. Corrected
  the same day. The lesson is the one already in this file's inferences and it was not
  applied here: a name on a candidate list is not a cinema, and matching a name against a
  search result is not identifying it. Confirm town and operator before classifying.
- **Kino Diana** has closed. `kinodiana.fi` is 2.4 kB whose entire visible text is "Kino
  Diana www.kinopiispanristi.fi www.kinodiana.fi". Its audience moved to Kino
  Piispanristi and Kino Lumo, both already providers here.
- **Eventio** powers `kauppa.kavi.fi`, evidenced on the page itself rather than by a
  string match: a `powered-by-eventio.png` badge linking to `https://www.eventio.fi/`.
  That is a shop rather than a listing, and shops are not inventoried here; Kino Regina,
  the cinema behind it, is already read from its own WordPress.
  **The vendor has split, which is why its site looks wrong for the product.** eventio.fi
  is Eventio Group Oy and now sells bingo and fundraising; its own front page states it
  sold the ticketing software business ("lipunmyyntiohjelmiston liiketoimintansa") to
  Eventio Oy to concentrate on "bingo- ja arpaliiketoimintaan". The badge still points at
  the seller. So the vendor site carries no customer list worth reading, and reading it as
  "a fundraising company, not a ticketing platform" is the wrong conclusion: it was both,
  and the ticketing half moved.
  **Not established:** whether the platform has other Finnish cinema customers. No sweep
  was run, and eventio.fi is no longer where one would look. That is what a next probe
  would need, and it is the only reason Eventio is not closed.

**Inferences and open questions**

- A name on a candidate list is not a cinema. Three of these nine were a closed cinema, a
  history page and a theatre company, and no amount of adapter work would have changed
  that. Classify before estimating.
- An empty platform API is not proof of an empty cinema: Bio Säde's schedule lives on
  another host. Here the sites' own pages agreed with their APIs, which is what settled it.
- Whether Kaustinen's silence is a seasonal break or a longer pause is not established.
  Nothing here tests it, and its own pages say only what is quoted above.

**Status and next step**

Iso-Hannu is live. Kino Kaustinen is one `SITES` entry away and is held only by having no
screening to verify a ticket destination against, which is the rule six dead Nexxo links
bought. Next step: re-read `kinokaustinen.fi/elokuvat/ohjelmistossa` on a later Monday and
add it when it lists a film.

---

## TMB Cinema: four cinemas on one template (2026-09-15)

**Findings** (all four sites read as a visitor, 2026-09-15)

TMB Cinema Oy runs Kino-Toijala (Akaa), Kino-Sampo (Valkeakoski), KinoMania (Pieksämäki)
and Elokuvateatteri Elo (Heinola). Four sites, one template, footer "Mediapalvelu W3D".

- **Not an existing platform.** `/elokuvat/ohjelmistossa` answers 200 with zero film links
  on all four, so they are not eTiketti tenants despite carrying
  `cdn.etiketti.app/studio123/...` image URLs: those are syndicated opera posters, which
  is a fingerprint of a shared poster source and not of a tenancy. Counting the films, not
  the 200s, again.
- **Four cinemas, not one mirrored four times.** This had to be settled first, because the
  schedules coincide: Toijala and Sampo published an identical set of 23 screenings, and
  Mania and Elo an identical set of 32. The booking id separates them. For the same film
  at the same minute `?varaa=` is 21001 at Toijala, 21006 at Sampo, 21012 at Elo and 21015
  at Mania: four rows in the operator's system. The screen counts differ too, which a
  mirror could not do: Mania and Elo print `, sali 1` / `, sali 2`, the other two print no
  auditorium.
- **`{base}/?lista=1` is the whole published programme**, one request per venue: a
  `<small>` with weekday, full date including the year, time and the optional hall, then
  the title in `<h2><a href="?ohjelmisto=N">`, then the age limit as an image filename.
  12 dates out to 2026-11-07 when read. Every row in this view is a timed screening; the
  coming-soon entries are in the default grid view and are not read.
- **The age limit is only an image.** The film page states it in no text at all.
  `ikaraja_2`, `_3` and `_4` were checked against this repo's own committed ratings for
  five films other providers also carry and agree: K-7, K-12 twice, K-16 twice.
  `ikaraja_1` appears only on opera events, which no provider here rates, so it is left
  unmapped. The sequence looks like S, K-7, K-12, K-16, but a classification is not
  something to infer from a filename's ordinal.
- **The film page carries a per-screening price and a runtime**, and this adapter reads
  neither. That would be one request per film per venue, about 68 a run against a third
  party, for fields the card does without. A deliberate omission rather than an oversight.

**Inferences and open questions**

- Whether the four ever diverge in programme is not established; on the day read they ran
  in two identical pairs. Nothing here depends on it, since each venue is read from its
  own host.
- `Leffa & Kaffe` is a labelled screening group on the film page and does not appear in
  the list view, so no strand label is published. Reading it would need the film pages.

**Status and next step**

Live as `scripts/providers/tmb.py`, four providers, four venues, cloud half. Committed
2026-09-15 and **not yet published**: no run has fetched them. Next step: verify from the
committed logs and show records after a scheduled run.

---

## Julia 1&2, Hyvinkää (2026-09-15)

**Findings** (juliaelokuvat.fi, read as a visitor 2026-09-15)

An operating two-hall cinema at Hämeenkatu 34, on its own WordPress. Not the Turku "Julia"
an earlier entry in this file closed; see the correction in the batch section above.

- `/ohjelmisto/` is the whole published programme in one request: one `div.elokuva` per
  film with the film-page link, the poster, a `<div id='bNNNN'>` of `<br>`-separated
  screenings and `<strong>`-labelled `Hinta`, `Ikäraja`, `Kesto` and `Genre`.
- **The films are listed twice.** An index above the programme repeats every title with a
  "Katso näytösajat tästä" link and no screening, so a parser anchored on the title alone
  would publish dateless rows. Anchoring on the film block and requiring a screening row
  handles it.
- **The year is two digits**, `15.09.26`. Published, not missing, so it is read as 2000+YY
  and nothing is taken from the clock. Two films ran 4 screenings over 2 dates when read.
- `Salit` states two halls, 110 and 57 seats; screenings carry `1. sali` / `2. sali`.
- **No online booking anywhere.** Tickets at the door, reservations by phone, and `/liput/`
  sells only gift tickets. So the showtime links to the film's own page and the registry
  entry is `book="door"`; no ticket host exists and none is invented.

**Inferences and open questions**

- The programme was two films deep on the day read. Whether it is always that short is not
  established and nothing here depends on it.

**Status and next step**

Live as `scripts/providers/julia.py`, one provider, one venue, cloud half. Committed
2026-09-15 and **not yet published**. Next step: verify from the committed logs and show
records after a scheduled run.

---

## Bio-Kaari, Forssa (2026-09-15)

**Findings** (bio-kaari.fi, read as a visitor 2026-09-15)

WordPress with a site-specific plugin, `wp-content/plugins/biokaari/`, that renders the
whole programme server-side.

- **MyCloudCinema, and that did not make it a `SITES` entry.** Posters come from
  `mcswebsites.blob.core.windows.net` and tickets from
  `bio-kaari.azurewebsites.net/websales/`, the platform BioRex and Gilda also run on.
  All three render it differently: BioRex is `admin-ajax` returning HTML inside JSON,
  Gilda is MyCloudCinema's own document, this is a bespoke WordPress plugin. Same
  conclusion this file already reached about Johku, on a different platform.
- **The date is the day container's id.** `<div class="searchResults" id="15092026">`, ten
  of them, all in the markup with the later ones `display:none`. The film rows repeat
  verbatim across days, so the container is the only thing that separates them: 15
  screenings over 10 days when read, each with its own `websales/show/{id}`, which is what
  confirms no day's times are being published on another.
- A film can hold several `<li>` rows on one day. The screening-row tags are upper case
  (`<P>`, `<DIV>`, `<A>`) where the rest of the markup is lower case.
- The title carries a release year, `(2026)`, taken as the optional `year` field rather
  than left in `title`, which is the TMDB and merge key.
- The ticket link is published as `http://` on a host that answers `https://` and
  redirects there. It is upgraded, and it is read from the page rather than constructed.
  The sales page itself is never fetched.
- The film page adds `Lajityyppi`, `Ikäraja: K7/4` (the 4 is the flexibility years, not
  part of the classification) and `Kesto: 1 h 27 min`. Three films when read, so the
  per-film pass is a few requests a run.

**Inferences and open questions**

- The weekly articles under `/elokuvat-naytosajat-ja-hinnat-DD-DD-M/` restate the same
  programme in prose with prices. The front page's day containers are the structured
  source and are what this adapter reads; whether the articles ever carry a screening the
  containers do not is not established, and nothing here depends on it.
- No price is published in the day containers, so `price` stays empty.

**Status and next step**

Live as `scripts/providers/biokaari.py`, one provider, one venue, cloud half. Committed
2026-09-15 and **not yet published**. Next step: verify from the committed logs and show
records after a scheduled run.

---

## Which platforms exist: the directory and domain sweeps

**Findings** (nytleffaan.fi, probed 2026-08-29; Vista domain sweeps 2026-08-27 and -29)

`nytleffaan.fi/elokuvateatterit/`, run by Suomen Filmikamari, lists every Finnish cinema:
225 entries across 152 hosts, each linking the cinema's own site. The page needs a browser
to render, which is why it sat unprobed for two days.

103 of the 152 hosts were swept, two requests each: the homepage for a platform
fingerprint and `/xml/TheatreAreas/`. **A signature in someone's HTML proves they are a
platform's customer, not that the platform answers us**, so every hit was verified against
the endpoint the adapter would need.

- eTiketti: 22 hosts carry `etiketti.app`; 16 serve the `/elokuvat/ohjelmistossa` listing.
- Nexxo: all 10 hosts carrying `nexxo-scope` answer `public_api.php`; six had live shows.
  Four return valid JSON with zero shows at every id.
- Johku: `kuvatahti.johku.com` is in the directory. The widget claims for kinotapiola.fi,
  kulttuurimylly.com and virtasali.fi were corrected on 2026-09-05 (see Johku above).
- MyCloudCinema: mantsala.cine.fi.

The **Vista domain sweep failed twice.** 45 guessed domains, then the real 103-host list:
zero hits beyond Savon Kinot. Azure blob enumeration on the shared asset host and a search
for the vendor's client list were also dead. Ten hosts answered 200 with their own HTML, a
soft-404 whose first bytes are not `<?xml`, so status alone would have reported ten false
hits. The sweep was blocked for two days on a presumed missing input, the domain list,
which turned out not to be what made it fail, and korjaamokino.fi, a real Vista site, was
not among the hosts probed at all.

**Inferences and open questions**

- Roughly 196 cinemas and 306 screens existed in Finland in 2009, and the tail clusters
  onto a few platforms. Platform adapters first; a bespoke parser only when a cinema is on
  none of them.
- Competitive picture: nytleffaan.fi is industry-run, gets exhibitor data and excludes
  event cinema and festivals; elokuviin.com includes festivals; kinossa.fi exists. "Suomen
  kattavin" is not a defensible claim against 225 directory entries and two services
  claiming full coverage.
- **Eventio** is a ticketing platform with cinema customers and was unprobed when this
  sweep was written. Kino Regina's film pages carry an Eventio `events.json` URL with the
  page's key, so KAVI's shop runs on it. Probed 2026-09-15; see the batch section above,
  which supersedes the next step this section used to set.

**Status and next step**

The eTiketti and Nexxo sweeps both landed (2026-08-30). The open candidate list lives in
`IDEAS.md` under "Provider coverage, and what is next", which is the status index. Eventio
was probed on 2026-09-15 and the finding is in the batch section above, so the next step
this section used to set is done. What is left here: a customer sweep for Eventio if
anyone wants one, and re-reading Kulttuurimylly when its programme resumes.
