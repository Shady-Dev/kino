# Kinola: three templates, and telling a film from a concert

Research notes for an adapter that does not exist yet, moved out of `IDEAS.md` on
2026-09-14. Nothing here is a rule, and nothing here is built: there is no
`scripts/providers/kinola.py` (checked again 2026-09-14). One item in it, whether to
publish rows the page cannot resolve, is a maintainer decision and is flagged as such.

Kinola is the platform behind Cinema Orion's ticketing. `scripts/providers/orion.py` reads
one of its three front-end templates; the other two belong to cinemas that are not
registered here.

---

## The three templates

**Findings** (read as a visitor, 2026-09-14)

| Site | Markup | Count that day |
|---|---|---|
| cinemaorion.fi | `table.kinola-day` rows | read today by `orion.py` |
| kinokilta.fi/naytokset/ | 56 × `li.kinola-event` | `.date` "TI 15.9.2026", `.time`, `.movie-subtitle`, `.duration-info` |
| kinolaika.fi/ohjelmisto/ | 47 × `div.kinola-event` | one `.kinola-event-date` "16/09/2026 14:00", a `.kinola-event-venue`, 4 sold-out rows |
| kinokonepaja.fi | none | lists no event at all |

- `.movie-subtitle` on Kilta carries a strand, not a subtitle: "Kahvikino",
  "Anniskelunäytös K18".
- Laika's four sold-out rows carry no checkout link.
- Neither Kilta nor Laika renders `kinola-day`, so `orion.parse` returns zero on both.
  That is the whole reason this is a new module rather than two `SITES` entries.

**Inferences and open questions**

- Reusable from `orion.py`: `_iso`, `_slug`, `_price`, the `/checkout/<uuid>` link resolved
  with `urljoin`, and the runner contract. Not reusable: the block, row and cell patterns,
  which are bound to the table.
- The shape that fits is **one `kinola.py` with a template per site named in `SITES`**
  (`table`, `kilta`, `laika`), not a copy of `orion.py`. That is a design proposal, not a
  measurement.

**Status and next step**

Unbuilt. Next step is the adapter, and the classification question below has to be settled
by the maintainer before it ships.

---

## Films and other events

**Findings** (kinokilta.fi and kinolaika.fi, sampled 2026-09-14)

Concerts and films are **one WordPress `film` post type**. No taxonomy, tag, JSON-LD,
`og:type`, REST type or filter option separates them. Laika's own filter lists its
concerts under "Kaikki elokuvat". The film page is the only evidence there is.

- On 23 Laika pages: the 16 films carry `Ohjaus` and `Kieli`; the 7 concerts and events
  carry neither and read "Not rated" or K-18 with no director (Tuure Kilpeläinen, Arppa,
  Antti Autio, Knipi, Mariska, Livemusavisa, 50 vuotta rokkia).
- On Kilta: 37 pages, every one with `Ohjaus` or `Lajityyppi`.

**Inferences and open questions**

The rule the sample supports, stated conservatively so a wrong guess fails towards
publishing nothing rather than towards publishing a concert as a film:

- **Known film** only on structured film metadata (`Ohjaus` / `Ohjaaja`, `Kieli`,
  `Lajityyppi`, a classification) or another verified structured signal.
- **Known non-film** only on an explicit event-level description of a live act: a
  performer billed as such, a gig, a quiz. **Never on a word**: a synopsis can say
  konsertti, and a concert film is still a screening.
- **Unresolved** is everything else, and it stays unresolved. A log line records it; that
  does not make it a film.

**Open, and the maintainer's to decide before the adapter ships:** whether to publish
unresolved rows. Include them and some live events show as films; omit them and
thin-metadata films vanish. A per-title override list covers either choice.

**Status and next step**

Requirement, not implementation. Fixtures the adapter has to carry, chosen because each
one breaks a rule that reads plausible:

1. a film with no metadata: *A Fox Under a Pink Moon*, 76 min, K-16, `Tekstitys` only;
2. a concert film: *Oasis: Don't Look Back in Anger*, `Ohjaus` present;
3. a film whose synopsis mentions a concert;
4. a billed live concert: *Arppa*, "Akustisesti saleissa", no film metadata.

Only the fourth is a non-film. Next step: put the decision on unresolved rows to the
maintainer, then write the adapter.
