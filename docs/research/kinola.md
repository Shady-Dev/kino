# Kinola: three templates, and telling a film from a concert

Research notes for an adapter that does not exist yet, moved out of `IDEAS.md` on
2026-09-14. Nothing here is built: there is no `scripts/providers/kinola.py`, re-checked
2026-09-15, and no registry entry for Kilta, Laika or Konepaja.

**The publication policy was decided on 2026-09-15** and the decision, with the reasoning
and the three corrections it made to the proposal below, is in
[docs/archive/2026-09-providers.md](../archive/2026-09-providers.md) under "Kinola: the
publication policy, adopted". This file keeps the findings it always held, and its
inferences are now either superseded by that record or carried forward as build
requirements. Findings are dated and unchanged; the policy is not a finding.

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

Unbuilt. The classification question that used to gate it was settled on 2026-09-15; what
is left is validation and then the adapter. Two template details carry forward as
requirements: Kilta and Laika are candidates for **one** adapter with a separate handler
per template, and the empty-programme reading for Konepaja is dated 2026-09-14 and has to
be re-read before it is relied on.

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

The rule this sample supports, stated conservatively so a wrong guess fails towards
publishing nothing rather than towards publishing a concert as a film. **Corrected
2026-09-15**, and the correction is part of the adopted policy:

- **Known film** only on structured film metadata, and **an age classification is not
  part of it.** The version of this list written on 2026-09-14 named "a classification"
  as sufficient, which contradicts both the finding above, where the non-films read
  "Not rated" or K-18, and the first fixture below, a film carrying K-16 that this file
  calls unresolved. A classification says a board rated something, not that the something
  is a film.
- **The predicate is a hypothesis, not a guarantee.** It rests on 7 sampled non-films.
  The presence of a field such as `Lajityyppi` is therefore not automatically sufficient,
  and which fields in which combination constitute film evidence is an implementation
  detail to validate against the fixtures and against the pages as they stand when the
  adapter is written.
- **Known non-film** only on an explicit event-level description of a live act: a
  performer billed as such, a gig, a quiz. **Never on a word**: a synopsis can say
  konsertti, and a concert film is still a screening. Explicit event-level evidence of a
  live act **prevents** automatic inclusion, even where generic metadata is present.
- **Unresolved** is everything else, and it stays unresolved. A log line records it; that
  does not make it a film.

**Decided 2026-09-15, no longer open:** unresolved rows are omitted, with evidence-backed
overrides in both directions. The record is in
[docs/archive/2026-09-providers.md](../archive/2026-09-providers.md). The cost accepted
with it is that a sparsely described film is missing until an override is verified for it.

**Status and next step**

Requirement, not implementation. Fixtures the adapter has to carry, chosen because each
one breaks a rule that reads plausible:

1. a film with no metadata: *A Fox Under a Pink Moon*, 76 min, K-16, `Tekstitys` only;
2. a concert film: *Oasis: Don't Look Back in Anger*, `Ohjaus` present;
3. a film whose synopsis mentions a concert;
4. a billed live concert: *Arppa*, "Akustisesti saleissa", no film metadata.

Only the fourth is a non-film.

**Status: policy adopted 2026-09-15, implementation not started.** Next action, in order:
validate the structured-metadata predicate and the three templates against the fixtures
and against the pages as they stand; measure what the policy omits; then write the adapter
only when that is asked for. The requirements below are what it has to satisfy and are
recorded rather than implemented.

---

## Build requirements

Recorded 2026-09-15 with the policy, and **not implemented**. These are what the adapter
has to satisfy, not a description of anything that exists.

**The classifier**

- Validate the structured-metadata predicate against the four fixtures and against the
  pages as they stand at the time of writing, rather than against the 2026-09-14 sample
  alone. An age classification is not film evidence. No single field is assumed
  sufficient in advance.
- Explicit event-level evidence of a live act prevents automatic inclusion even where
  generic metadata is present.
- Never classify from a keyword in the title or the synopsis alone, in either direction.

**Overrides**

- Two directions: force-include a film the predicate leaves unresolved, force-exclude an
  event the predicate wrongly includes. The second is the reason the mechanism cannot be
  one-sided.
- **Applied before the default classifier**, so an override decides rather than argues
  with it.
- Scoped to a provider and a stable event or page identifier, or a verified canonical
  URL. Never a loose title keyword, which would reintroduce the classification rule this
  policy forbids.
- Each entry carries its action, its reason, its evidence source and the date that
  evidence was verified.
- Revalidated against available evidence. A redundant override is one that does not
  change the default decision; the guard identifies those. An event that has left the
  programme, or a page that cannot be read, does **not** by itself prove an override
  redundant, so neither may be treated as grounds to drop one.
- *A Fox Under a Pink Moon* is a known candidate for an inclusion override if the
  validated predicate still leaves it unresolved. Its identity and its source page are
  verified before an entry is written, not assumed from this file.

**Measurement**

- Measure what the policy omits as **both** unique events and screening counts, split
  into explicit non-films and unresolved entries. The 2026-09-14 sample counted pages
  (37 Kilta, 23 Laika) and rows (56, 47) but never the screenings behind an unresolved
  page, so the cost of the policy is currently unknown.

**Rows and destinations**

- A sold-out film screening is preserved even though its checkout link is gone: Laika's
  sold-out rows carry none. The destination is the film page's own href **read from the
  source**, never constructed, with `soldOut: true` and whichever existing destination
  semantics that implies.

**Fixtures**

- Keep the four already listed. Add coverage during implementation for conflicting
  metadata, and for both override directions.

**What not to touch**

- `scripts/providers/orion.py` reads the third template and stays as it is. A change
  there would need its own justification, demonstrated by the implementation rather than
  assumed now.
