# Public programme APIs behind page-read cinemas

A recheck of the sources this project reads as HTML, looking for a public API that earlier
research missed. Read on 2026-10-24 with anonymous GET requests and the project's
User-Agent. Requests to one host were paced. No credentials or widget sessions were used,
and no booking, seat-map, payment or administrative route was requested. Raw responses
stayed outside the repository. This file records what was seen, and it names cinemas and
their public pages without listing API routes. Nothing here is a rule, and no adapter
changed because of it.

39 sites were attempted. 37 served their page and two did not. The pass covered sources
read as pages. Adapters that already read an API were left out, and eTiketti was sampled
on three tenants. A site with no API found here may still have one.

## Findings

### Kino Kirkkonummi publishes its programme as WordPress records

Source: [kinokirkkonummi.fi](https://kinokirkkonummi.fi/), its advertised WordPress REST
index and its public movie collection, read 2026-10-24.

- The movie collection answered 200 without authentication. It held six records on one
  page, and the response headers gave the same totals.
- Each record has a `meta_box` object with `titel`, `comingsoon`, `date_and_time_1` to
  `date_and_time_3`, a short description, `read_more` and a trailer link.
- All 12 non-empty date fields matched text on the front page after whitespace and entity
  normalisation. Ten carry a clock and two are coming-soon notices with a date and no
  clock. One field can hold several screenings.
- Four films had timed fields: Pikkuli ja Tähtipeura, Matka Piemonteen, Lapin Sota and
  Kerro Kaikille. The other two records were Late Lammas and Järki ja tunteet.
- The values are free text with no year, slash-separated dates and sometimes two clocks on
  one date. `read_more` is HTML that carries the runtime, rating and price as prose.

### Kino Tapiola publishes a screening archive

Sources: [kinotapiola.fi](https://www.kinotapiola.fi/), its
[programme page](https://www.kinotapiola.fi/elokuvat/) and the screening collection that
the site's alternative REST discovery advertises, read 2026-10-24.

- Discovery answered 200 anonymously. A three-record read reported 4,061 records in total,
  which is an archive going back well before the current programme.
- The useful object is the uppercase `ACF`. The lowercase `acf` was empty on every record
  sampled. `ACF` holds `johku_show_id`, `elokuva-relaatio`, `start_datetime`,
  `end_datetime`, `upcoming`, `language` and `subtitles`.
- One record was Dyyni: Osa kolme at `2026-12-16 17:15:00`, language `EN`, subtitles
  `FI-SE`. The times carry no UTC offset.
- Preview records can run from midnight to midnight with `upcoming: true`, for example
  Joulupukin salainen paja. They are not midnight screenings.
- The newest 100 records by id held ten previews and 22 screenings on or after 24 October.
  All 22 matched a row that `tapiola.parse` read from the programme page that day, on the
  normalised title and the local start minute. The page gave 28 timed rows.
- The six page rows outside that sample were Carmen, Pähkinänsärkijä, Götterdämmerung,
  Cosi fan Tutte, Joutsenlampi and Tosca, dated December 2026 to June 2027. Searching the
  collection for them returned nothing. A control search for Dyyni returned an invalid-page
  error, and the negative searches therefore prove nothing.

### Three Cinemahouse sites refuse their screening route

Sources: [kinopiispanristi.fi](https://www.kinopiispanristi.fi/),
[kinolumo.fi](https://www.kinolumo.fi/) and [laitilankino.fi](https://www.laitilankino.fi/),
read 2026-10-24.

All three advertise a GET screening collection in the cinema plugin's REST namespace, and
all three answered an anonymous request with 403, `cr_forbidden`. Piispanristi's movie
collection answered 200 with film descriptions and no screening fields. Its public filter
script does not fetch a programme.

### Film records with no programme

Read 2026-10-24.

- [Cinema Orion](https://cinemaorion.fi/): film records answered 200 with an empty `acf`. The
  advertised screening collection answered 200 with an empty list.
- [Kino Regina](https://kinoregina.fi/): two movie records answered 200 with rendered content
  and an empty `acf`.
- [Kino Engel](https://kinoengel.fi/): two film records answered 200 with empty content and
  an empty `acf`.
- [Kinotour](https://www.kinotour.fi/): a custom REST namespace exists and its discovery
  document lists no route that reads a programme.
- [Kino Kilta](https://www.kinokilta.fi/): the front page answered, and REST discovery was
  refused, with 401 on the alternative discovery URL.
- Kino Laika, Kino Myyri, Cinema Sheryl and Kino Konepaja: discovery showed no programme
  route. Laika's public Kinola script requests filter options and no timed programme.

### No API found

Read 2026-10-24. Each of these served its front page. Discovery and script reads were
selective, and a site in this list may still have an API.

- WordPress with no screening collection advertised: Kino Akseli, Navettakino, Matin-Tupa,
  Marita, Julia and Huvimylly. Navettakino left WordPress on 2026-11-01, see
  [ticketing-platforms.md](ticketing-platforms.md).
- No cinema schedule route found: Kuvakukko, Kino Hamina and Bio-Kaari.
- Kino K13's alternative REST discovery answered 403, and its API status is unknown.
- No programme API seen on the front page or in its sources: Iso-Hannu, Kino Vaakuna,
  Elävienkuvien teatteri, Lieksan Kino, Bio Pallas, and the four sites on one template,
  Kino-Toijala, Kino-Sampo, KinoMania and Elokuvateatteri Elo.
- Heureka's calendar page is what the adapter already reads. Its Shopify storefront is no
  evidence of a separate planetarium API.
- eTiketti, sampled on Kotkan Leffat, Cinema Niagara and Star: all three load the same
  version of the main public script, and the Kotka copy makes no programme request.

### Two sites that did not answer

Bio Savoy's HTTP front page answered 503 and HTTPS was refused. Alatalo's HTTP front page
could not be read and HTTPS timed out after 12 seconds. Neither result says anything about
an API. Bio Savoy moved to HTTPS on 2026-10-28, and Alatalo's TLS probes are in
[adapter-http.md](adapter-http.md).

## Inferences

- Kirkkonummi's records could replace the dependence on Elementor headings, the repeated
  mobile and desktop blocks and the icon-list order. The date fields are still free text,
  and the date, weekday and film-fact rules in the current adapter would still be needed.
  The records give no ticket link, and the programme link stays.
- Tapiola's collection is real structured screening data. Reading only the newest records
  would miss distant events entered earlier, and it is not shown to cover the whole
  programme. A film relation id is no evidence of a public film feed or of a ticket URL,
  and an interval between start and end is no evidence of a runtime.
- The BioRex and Johku API comparisons in [ticketing-platforms.md](ticketing-platforms.md)
  were not re-read in this pass, and their reasons for keeping the current readers stand.

## Open questions

- Does Tapiola's collection hold the far-future opera and ballet rows, and how can the
  archive be read in a bounded way?
- Are Tapiola's times local, and what do `start_datetime` and `end_datetime` mean on a
  preview record?

## Status and next step

Nothing is implemented, and no adapter, registry entry or published page changed. The
write-up was moved here on 2026-11-01 from a report kept outside the repository, and the
sites were not read again for it. Kirkkonummi is the first candidate. The next step there
is to build an API reader beside the page reader and compare their full output: title
keys, per-screening prices, several clocks on one date, coming-soon notices and posters.
Tapiola comes after the open questions above are answered. The three Cinemahouse sites
stay on `cinemahouse.py`.
