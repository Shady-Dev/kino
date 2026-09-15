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

| Provider | Price in the data | Where a price is stated | Cost to read it |
|---|---|---|---|
| Kino-Toijala, -Sampo, KinoMania, Elo | none | `?hinnat=N`, linked from the list view | one request per venue |
| Kino Kirkkonummi | none | `<div>Liput 14,50</div>` in each film's block | none, already fetched |
| Iso-Hannu | none | `LIPUT Ma-to 13,50 € Pe-su ja arkipyhä 14,50 €` on the front page | none, already fetched |
| Kino Manttu | none | `Kino Mantun liput: 11 € / 9 €` in the listing text | none, already fetched |
| Kino Kuvakukko | none | a `/liput/` page | one request |
| Bio-Kaari | none | a `/liput/` page, rules by film, day, length and 2D/3D | one request |
| Bio Savoy | none | **no ticket table found**; the amounts on the page are gift cards | unknown |
| Kino Kilta, Kino Laika | none | only behind the Kinola checkout | forbidden |
| Cine Mäntsälä | none | not located on the site | unknown |
| Julia, Kino Vaakuna | published | already read | — |

- **Kirkkonummi states a price per film, not per house**: 14,50 and 15,50 both appear on
  the page read 2026-09-16, so one house figure would be wrong for part of the programme.
  The block prints it either side of the screening list.
- **Iso-Hannu's rule is by weekday**: Mon–Thu 13,50 €, Fri–Sun and weekday public holidays
  14,50 €. The discounts beside it (student, pensioner, under-12, S-Etukortti Tuesdays at
  10,00 €) all require a card at the counter, so the ordinary ticket is the one figure that
  describes what a visitor pays without one.
- **Bio Savoy publishes gift-card denominations, not a tariff**: "13€ (barnfilmer) och 15€"
  is what a gift card may be bought for, and 135€ buys ten tickets. Reading a ticket price
  out of that is an inference, not a finding.
- **Bio-Kaari's page states rules rather than a table**: the price varies by film, by day,
  by running length and by 2D/3D. Not reducible to one amount per screening from the
  listing alone.

**Inferences and open questions**

- Kinola's price sits behind the checkout, which this repo does not call. Nothing to do.
- Cine Mäntsälä and Bio Savoy need a second look at pages not yet read; neither was found
  from the page the adapter already fetches.

**Status and next step**

Implemented 2026-09-16: TMB's four (from `?hinnat=`), Kino Kirkkonummi (per film) and
Iso-Hannu (the house tariff by weekday), the last two from pages already fetched and at no
extra request. Next: Kino Manttu, whose price is in the listing text the adapter already
reads; then decide whether Kuvakukko's and Bio-Kaari's `/liput/` pages are worth a request
each. Bio Savoy, Cine Mäntsälä and Kinola have no readable price and are not pending work.
