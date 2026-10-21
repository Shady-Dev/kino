# Kuvakukko and Kino Manttu: the programme host

`scripts/providers/kuvakukko.py` reads both cinemas from one page on www.kuvakukko.fi,
and the tariff from `/liput/` on the same host. The page's shape as first probed on
2026-09-15 is in the adapter's docstring. This file holds what later probes of the host
found.

## The 404 of 2026-10-21

### Findings

Read 2026-10-21 between 16:17 and 16:45 UTC from an ordinary connection, unless marked.

- The listing `/ohjelmisto/kuvakukon-ja-kino-mantun-ohjelmisto/` and `/liput/` both
  answer 404. The body is a not-found page under the City of Kuopio's header ("Voe
  rähmä! Hakemaasi sivua ei löytynyt!"), served from Google Cloud Storage
  (`Server: UploadServer` and `x-goog-*` headers).
- `https://www.kuvakukko.fi/` answers 200 with the City of Kuopio's temporary site, a
  Gatsby build marked `noindex`. Its front page states that kuopio.fi is not working
  normally, that the outage is expected to last until Thursday morning 22.10.2026, and
  that the temporary site is a reduced version.
- www.kuvakukko.fi, kuvakukko.fi, www.kuopio.fi and kuopionseina.fi resolve to one
  address and serve that same temporary site. Its pages carry
  `Last-Modified: Wed, 21 Oct 2026 13:52:11 GMT`.
- Its "Vapaa-aika ja hyvinvointi" page lists Kino Kuvakukko with its street address and
  phone number, a link to www.kuvakukko.fi and a link to the cinema's Facebook page. It
  carries no programme. The four other pages in its navigation do not mention a cinema.
- The committed `logs/run-kuvakukko.log` places the change between two cloud runs. At
  `ed2dd2c1a`, from data generated 11:15:52 UTC, it reads 40 showtimes and `exit=0`. At
  `bb84a65a9`, the run committed at 15:31 UTC, it reads `HTTP Error 404` and `exit=1`.
- A web search on 2026-10-21 found no news report of the outage. The temporary site's
  own notice is the only source for its cause and expected end.

Read 2026-10-22:

- The same log at `ae75ff9be`, committed 17:19 UTC on 2026-10-21, still reads the 404.
  At `67148e0fd`, committed 23:21 UTC from data generated 23:16:06 UTC, it reads 37
  showtimes over both cinemas and `exit=0`. The three cloud commits after it, to
  `c745c37d3` at 11:20 UTC on 2026-10-22, read the same.
- At 12:39 UTC the listing answers 200 with both `esitysaikataulu` headings.

### Inferences

- The programme did not move to a new path. The city replaced its whole web estate,
  kuvakukko.fi included, with a temporary site at about 13:52 UTC, and the 404 was that
  site's not-found page. The same path answered again once the city's site returned.
- The outage ended between the cloud runs committed at 17:19 and 23:21 UTC on
  2026-10-21, before the morning the notice gave.
- No visitor-facing page read here carried the programme while the outage lasted. The
  cinema's Facebook page was not read.

### Status

Closed 2026-10-22 with no adapter change. `run.py` kept the previous files for
`kk-kuopio` (32 showtimes) and `kk-nilsia` (8), generated 11:15:52 UTC, until the
23:16 UTC fetch replaced them. By the rule in `staleNotice`, with `STALE_H` at 8 hours,
the client could name Kuvakukko as late from about 19:16 UTC until that data arrived.
