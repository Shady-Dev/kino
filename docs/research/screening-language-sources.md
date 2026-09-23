# Screening language: Riviera, Cinema Orion, Kino Helios

The three adapters publish `"lang": ""` for every screening (`riviera.py`, `orion.py`,
`helios.py`), so the app shows no audio or subtitle language for them. Read 2026-09-23
from an ordinary connection, as a visitor, with the adapters' own User-Agent. The open
item is in [IDEAS.md](../../IDEAS.md).

## Findings

- **Riviera, per screening.** The admin-ajax listing the adapter reads (111 kB) names no
  language. Each screening's ticket page on the ticket host, the page the price pass
  already fetches, carries both: `<p class="spokenLanguage">Kieli: <b>Suomi</b></p>` and
  `<p class="showSubtitles">Tekstitys : <b>Englanti</b></p>`. Values are capitalised
  Finnish language names. One page read (screening 982798, 200, 39.5 kB).
- **Cinema Orion, per film.** The front-page table the adapter reads names no language.
  Each film page linked from it, `/elokuvat/{slug}/` (18 on the day), has a definition
  table with `Kieli:` and `Tekstitys:` rows, lower-case Finnish names separated by
  commas. Three pages read: "englanti, portugali, ranska, japani" / "suomi";
  "espanja" / "suomi, ruotsi" (Autofiktio, matching Finnkino's `ES-A, FI-S, SV-S`);
  "suomi" / "ruotsi".
- **Kino Helios, nowhere this adapter can read.** The calendar service returned 22 Kino
  Helios events with 16 non-empty fields each, none of them a language, and no language
  wording in any description (one-sentence blurbs). All 22 ticket links go to one ticket
  shop, whose event page reset the connection for a plain client (HTTP/2 stream error
  after 0.1 s) on one attempt.

## Inferences

- Riviera's language can ride on the price pass: same page, same cache, no new request.
  At `FETCH_MAX` 40 pages a run and 84 screenings on the day, coverage would fill over
  about three runs, as prices do.
- Orion's is film-level, so one page per film (18 requests a run, paced) and the same
  value on every screening of that film. Orion is a single screen, so a per-screening
  difference would be unusual; unverified.
- Both publish Finnish names, not codes: mapping them back through the client's
  `LN.fi` table gives the codes `langTxt` already renders.
- Reaching the Helios ticket shop would need a browser fingerprint, which the project
  does not do. Helios stays without language unless its calendar service adds a field.

## Open questions

- Whether Riviera's two fields are ever absent or "-" on a page; one page read.
- Whether an Orion film page can list a language the client's `LN` table lacks.

## Implementation status

Nothing built. Next step: Riviera, extend the price pass's parse and cache to carry the
two fields and map them to codes; then Orion, one paced film-page read per film.
