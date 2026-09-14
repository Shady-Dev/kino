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
