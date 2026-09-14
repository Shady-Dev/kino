# Which providers publish which languages

Moved out of `IDEAS.md` on 2026-09-15. Probed 2026-08-29 by counting films on each
provider's own Swedish path, not by counting HTTP 200s: a soft-404 answers 200 with zero
film links.

**Status.** Swedish is the third UI language and has been since 2026-08-29. Swedish
*titles* are not built: `title` is the merge key, so they would cost BioRex a second fetch
per venue and a new per-show field. Finnish is the fallback title, not English, because the
Finnish distributor title is what the ticket prints.

**Open.** Two things. The Swedish interface strings are drafted rather than translated and
still want a native Finland-Swedish reader, the contact line most of all. And the language
codes are normalised at the adapters and the client but the committed data has not been
re-measured since: the item stays open in [IDEAS.md](../../IDEAS.md) until no
`data/area-*.json` carries `TU`, `MA` or `XX`, at which point `CODE_ALIAS`, `NO_SUBTITLES`
and `LN_EXTRA` in `build_pages.py` go with their tests. Next step: grep the committed area
files after the next local run.

---

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
