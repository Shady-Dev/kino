# Where a ticket price can be read, and where it cannot

Moved out of `IDEAS.md` on 2026-09-15. Findings from reading each provider as an ordinary
visitor, with the date each was read. The access rule they are all measured against:
booking, payment and administrative endpoints are never called and not inventoried.

**Status.** The shared step is `scripts/providers/prices.py`: one GET per screening id
against the public ticket page a showtime already links to, sequential, 1 s apart, at most
40 pages a run, re-read after 48 h. Riviera, Kino Regina and Korjaamo Kino use it. Coverage
was 907 of 3773 showtimes priced when last measured on 2026-09-13.

**Open.** The one route not looked at is a visitor-facing *price page*, which would be
ordinary content rather than a booking endpoint. Next step: check whether Finnkino or
BioRex publishes one before treating either as blocked.

**Decided against.** Kino Engel's prices sit behind the Johku widget's API key; a headless
render was measured at about 6 s a page and deferred by the maintainer on 2026-09-13.
Inferring a screening's price from a site's footer house rates, as Kino Tapiola would
need, is an inference and is not published.

---

### BioRex, Gilda and Tapiola publish no per-screening price (probed 2026-09-13)
Asked whether the shared ticket-page price step (`prices.py`) could cover the three
unpriced non-Finnkino providers. Read as a visitor from an ordinary connection, one page or
payload each, nothing kept:
- **BioRex**: the admin-ajax listing's `data-click-data-layer` carries event, movie,
  cinema, show id and time only (82 objects, no price field). The showtime link lands on
  `webshop.biorex.fi/fi/#/book/{id}`, a 3.9 kB single-page shell whose prices come from
  the booking flow, which is never called.
- **Gilda**: the booking API's `show_times[].tickets` is `[]` on all 81 screenings; the
  film page prints no amount but "0,00 €". Prices appear only inside MyCloudCinema's
  purchase flow.
- **Kino Tapiola**: the screening page's ticket box carries no amount; the only prices on
  the site are the footer's house rates, "Liput 12,50 / 11,50 €", which are not a
  screening's price and would be an inference to publish.
So the step applies to none of them today. Coverage stays 907 of 3773 showtimes priced;
Finnkino (booking flow only), Heureka (admission) and Engel (Johku widget, deferred) are
the other zeros.

### Listing data leaves four fifths of showtimes unpriced (2026-09-01)
| | |
|---|---:|
| showtimes with a price on the listing we read | **1,043 of 5,079** |
| showtimes without | 4,030 |
| providers publishing at least one listing price | 27 of 32 |
| unpriced showtimes contributed by Finnkino | 2,333 |
| unpriced showtimes contributed by BioRex | 1,364 |

The provider count flatters it: the two largest chains are among the five that publish
nothing, so showtimes are the denominator. An earlier draft claimed cinemas publish prices
on the booking page; that was not measured, booking pages were not inspected, and the claim
is removed.

The booking flow stays out of bounds: booking, payment and administrative endpoints are
never called and not inventoried, and per-showtime prices would mean about 4,000 extra
fetches at the current cadence against small ticketing platforms. Not looked at: a
visitor-facing price page, which would be ordinary content and could give per-ticket-type
pricing.

### Finnkino publishes no prices outside the booking flow (2026-09-01)
Two backlog entries wanted Finnkino prices and were the same endpoint counted twice. An
earlier draft said the client half was done and that the price cell carried a ticket-type
breakdown in a `title`; both were wrong (the `title` belongs to Cinema Orion's page markup),
and checking found the parseFloat bug above.

The programme response carries no prices: a showtime object is `areaCategories,
attributeIds, eventId, filmAdvanceBookingRuleId, filmId, id, isAllocatedSeating,
isSoldOut, requires3dGlasses, restrictions, schedule, screenId, seatLayoutId, siteId`, and
scanning the whole response for any key containing price, amount, cost, ticket, fee,
tariff or currency returns zero matches. Per-showtime, per-site and bare ticket-type paths
answer 404; four attempts, not inventoried further.

The only route left is the seat-selection flow, which the access rule forbids: blocked by
the repo's own rule, not by difficulty. Open on one possibility: a visitor-facing price
page, not probed. The probe was one `/sites`, two programme reads and four 404s; nothing
raw was written to the repo.

## The providers added 2026-09-14/15, surveyed for a price (2026-09-16)

**Findings.** Committed data at `0b4a167f`, then each site read as a visitor, once.

| Provider | Where a price is stated | Cost to read it |
|---|---|---|
| Kino-Toijala, -Sampo, KinoMania, Elo | `?hinnat=N`, linked from the list view | one request per venue |
| Kino Kirkkonummi | `<div>Liput 14,50</div>` in each film's block | none, already fetched |
| Iso-Hannu | `LIPUT Ma-to 13,50 € Pe-su ja arkipyhä 14,50 €` on the front page | none, already fetched |
| Kino Manttu | `Kino Mantun liput: 11 € / 9 €` in the listing text | none, already fetched |
| Kino Kuvakukko | a `/liput/` page | one request |
| Bio-Kaari | a `/liput/` page, rules by film, day, length and 2D/3D | one request |
| Bio Savoy | not located on the front page | not established |
| Kino Kilta, Kino Laika | only behind the Kinola checkout | forbidden |
| Cine Mäntsälä | not located; only the front page was read | not established |
| Julia, Kino Vaakuna | already read | — |

- **TMB states a tariff and no screening can be priced from it.** 2D and 3D differ by 2.50
  and the list view carries no 3D marker -- the three `3D` strings are the `<title>` and the
  "Mediapalvelu W3D" footer, none on a row -- so the format of every row is unknown. The
  `+0.50` covers Saturday, Sunday *and* weekday public holidays, so a weekday row is
  unknown too. Both gaps together leave no screening settled.
- **Kirkkonummi states a price per film**, not per house: 14,50 and 15,50 both appear. The
  block prints it either side of the screening list. This is the strongest of the three,
  because the amount is attached to the film rather than derived from a rule.
- **Iso-Hannu's tariff settles part of the week.** `Pe-su ja arkipyhä 14,50 €` fixes Friday,
  Saturday and Sunday whatever else the day is. `Ma-to 13,50 €` does not fix a weekday,
  because the same line puts an *arkipyhä* on the dearer tariff. The discounts beside it --
  student, pensioner, under-12, S-Etukortti Tuesdays at 10,00 € -- all need a card at the
  counter, so they describe no ordinary ticket.
- **Bio Savoy's front page shows gift-card denominations, not a tariff**: "13€ (barnfilmer)
  och 15€" is what a gift card may be bought for, and 135€ buys ten tickets. A ticket price
  read out of that would be an inference.
- **Bio-Kaari's page states rules rather than a table**: the price varies by film, by day,
  by running length and by 2D/3D.

**Inferences and open questions**

- Kinola's price sits behind the checkout, which this repo does not call. Closed.
- **Cine Mäntsälä and Bio Savoy are unfinished research, not closed questions.** Only the
  page each adapter already fetches was read. Cine Mäntsälä runs MyCloudCinema, whose
  `show_times/` payload the adapter reads and which was not inspected for a price field, and
  neither site's own `/liput/`-style pages were looked for. Nothing here says they have no
  price; it says nobody has looked.
- Whether a labelled house tariff should be published where a per-screening price cannot be
  is a product question. The `price` field is a per-screening claim, so that would be a
  different field.

**Status and next step**

The rule, stated by the maintainer 2026-09-16 and now in `CLAUDE.md` and on `common.Show`:
an exact price only where its applicability to that screening is established, otherwise
blank. Implemented the same day: Kino Kirkkonummi publishes its per-film amount and blanks
any film whose association is ambiguous; Iso-Hannu publishes Friday to Sunday and blanks
Monday to Thursday; TMB publishes nothing and no longer fetches the price page.

Next: read Cine Mäntsälä's `show_times/` payload and its site for a price, and Bio Savoy's
other pages, before either is called closed. Kino Manttu's amount is in the listing text
already fetched and is the cheapest remaining, but it is `11 € / 9 €` with no statement of
which ticket each is, so what it settles has to be established first.
