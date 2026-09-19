# When the runner is challenged and an ordinary connection is not

Why a cloud run can fail on many unrelated cinemas at once while the same sites answer a
laptop minutes later, and what the pipeline does about it. Nothing here is a rule; the
decision it records is the maintainer's, taken 2026-09-19: **accepted as a known failure
mode, not routed local, no adapter change, no retry on a challenge body, no header
change.**

**Its own file rather than a section of
[ticketing-platforms.md](ticketing-platforms.md).** That file is organised per platform,
one section each for BioRex, Nexxo, eTiketti, Vista, Johku and the sweeps, and answers
"what does this platform publish". This answers "what did the runner get", spans seven
modules over five platforms and eighteen hosts, and belongs to none of them. Filed under a
platform it would be unfindable from any of the other six.

## Findings

**Two runs, the same nine red logs.** Measured 2026-09-19 from the committed logs at the
two commits those runs produced, `15ada2243` and `1ac89b049`, not from the Actions UI.
Both are `workflow_dispatch` of `biorex.yml`:

| run | started | commit | red logs |
|---|---|---|---|
| 35404792959 | 2026-09-18T23:12:48Z | `15ada2243` | cinemahouse, kinotour, kirkkonummi, lieksa, navetta, nexxo, tmb, vpk, cloud |
| 35443942404 | 2026-09-19T12:48:58Z | `1ac89b049` | the same nine |

`run-cloud.log` is the run's own tally, so eight modules failed and the ninth log is the
aggregate.

**What the failing hosts served, quoted from the logs.** The logs keep the response's byte
count and its `<title>` only; the body is never kept and never committed, which
CLAUDE.md's "Never commit a raw probe dump" requires. Nine hosts answered with a page of
about 12 kB titled `One moment, please...`. At `1ac89b049`:

| host | bytes | module |
|---|---:|---|
| www.kinopiispanristi.fi | 12089 | cinemahouse |
| www.kinolumo.fi | 12092 | cinemahouse |
| kinokirkkonummi.fi | 12095 | kirkkonummi |
| kino-mania.info | 12120 | tmb |
| elokuvat-elo.info | 12122 | tmb |
| www.lieksanelokuvat.net | 12134 | lieksa |
| kinosampo.info | 12201 | tmb |
| toijalan-kino.info | 12205 | tmb |
| www.pyhasalmenvpk.fi | 12257 | vpk |

The same nine at `15ada2243` ran 12051 to 12182 B, so the page differs slightly run to run
and is about 12.1 kB either time.

**Three more hosts answered 403, and only those three carry a `Server` header in a log.**
From `run-nexxo.log`, identical at both commits:

    [http] 403 from kinoset.fi, gave up after 3 attempt(s) -- Server: openresty/1.31.1.1
    [http] 403 from kinohirvi.fi, gave up after 3 attempt(s) -- Server: openresty/1.31.1.1
    [http] 403 from kino-olympia.fi, gave up after 3 attempt(s) -- Server: Apache

`kinohirvi.fi` serves both Kino Hirvi and Bio Säde, which is why four Nexxo providers
failed on three hosts.

**Two hosts failed with no evidence in the log of what they received.**
`www.navettakino.fi` and `www.kinotour.fi` failed on their own markers
(`the page renders no 'Tulevan viikonlopun näytökset' heading`, `no screening row in the
table`) and neither message passes the response through `common.served()`, so those two
logs say the marker was missing and nothing more. They are counted red here and are not
counted as challenged.

**Fourteen of the eighteen hosts the nine modules attempted were red.** A record and the
first NS record as `dig` returned them from an ordinary connection on 2026-09-19. These
are lookups, not page reads; no page was fetched for this table.

| host | run | A | first NS |
|---|---|---|---|
| kinokirkkonummi.fi | red | 152.115.36.105 | ns2.intendit.se |
| kino-olympia.fi | red | 157.180.98.77 | ns3.suncomet.fi |
| www.kinotour.fi | red | 31.217.192.36 | ns1.hostingpalvelu.fi |
| www.laitilankino.fi | **green** | 31.217.192.103 | ns2.hostingpalvelu.fi |
| www.kinolumo.fi | red | 31.217.193.150 | ns2.hostingpalvelu.fi |
| www.kinopiispanristi.fi | red | 31.217.193.150 | ns2.hostingpalvelu.fi |
| kinoaurora.fi | **green** | 5.44.244.43 | cns1.cloudpit.de |
| www.lieksanelokuvat.net | red | 5.44.244.228 | ns2.int2000.net |
| jarvelankino.fi | **green** | 5.44.245.76 | ns3.zoner.fi |
| www.navettakino.fi | red | 77.240.19.23 | dns1.louhi.net |
| elokuvat-elo.info | red | 77.240.19.48 | y.ns.joker.com |
| kino-mania.info | red | 77.240.19.48 | y.ns.joker.com |
| kinosampo.info | red | 77.240.19.48 | x.ns.joker.com |
| toijalan-kino.info | red | 77.240.19.48 | z.ns.joker.com |
| kinohirvi.fi | red | 77.240.19.57 | dns3.louhi.fi |
| www.pyhasalmenvpk.fi | red | 77.240.19.61 | dns3.louhi.fi |
| kinoset.fi | red | 80.69.174.12 | dns1.louhi.net |
| kinomarilyn.fi | **green** | 95.216.140.247 | ns2.dvn.fi |

Two rows are the ones worth keeping. **`www.laitilankino.fi` was green on 31.217.192.103
while `www.kinotour.fi` was red on 31.217.192.36 and two more were red on
31.217.193.150**, all four on one /23 behind one hosting company's nameservers, in the same
run. And **`kinoaurora.fi` was green on 5.44.244.43 while `www.lieksanelokuvat.net` was red
on 5.44.244.228**, adjacent addresses under different nameserver operators. So the split is
not per hosting company and not per address range.

**The gap to the previous run was not short.** Both from one read of the `biorex.yml` run
list: 35404792959 started **38 min 36 s** after 35402123826, and 35443942404 started
**95 min 17 s** after 35439529910. The rule this repository already carries, that a
dispatch should leave an hour after the previous cloud run, is therefore not what these
two failures test: the second waited well over an hour and failed anyway, and the run
95 minutes before it succeeded.

**The rate, over the 50 most recent `biorex.yml` runs**, 2026-09-13T07:34:17Z to
2026-09-19T12:48:58Z, out of 282 in the workflow's history: **8 concluded `failure`** and
one more was `cancelled`. Ids: 34868488107, 34894004566, 34983009141, 34999969305,
35070394363, 35126793232, 35404792959, 35443942404. Only the last two were read
log-by-log for this section, so 8 in 50 is the rate at which a run fails, not the rate at
which it fails **this way**, which is not established here.

**What a failure costs, and it is not bad data.** `run.publish_site` compares each venue's
parse against the file already on disk: a venue that returns nothing while a previous file
exists is appended to `stale`, the previous file is kept untouched, and the provider file
is written with `status: partial` and the stale venue ids named. Confirmed in the committed
`data/venues-kinoset.json` at `1ac89b049`: `status partial`, `stale
['ks-huittinen', 'ks-loimaa', 'ks-sastamala']`. So a challenged run publishes older data,
says which venues are older and how old, and publishes nothing wrong. A module whose parse
yields zero rows against a listing that does list films still fails the run, which is the
behaviour that turned these logs red rather than letting them pass quietly.

## Inferences, marked as such

- **A shared bot filter with a centrally distributed IP reputation list would explain the
  shape.** Unrelated hosting companies, unrelated nameserver operators and two different
  origin servers (`openresty/1.31.1.1` and `Apache`) refused one runner address inside one
  minute, while a neighbour on the same /23 answered. A per-host configuration change at
  fourteen sites simultaneously is the alternative and is much less likely. **Not
  verified**, and it cannot be verified from here: the response body is never kept, and an
  ordinary connection cannot reproduce a datacenter challenge.
- **The hostname pattern does not identify the product.** No log line and no header the
  logs keep names a vendor, and `One moment, please...` is used by more than one. This
  file deliberately names none.
- **That the sites were up is established; that the runner was challenged is not, for
  every host.** Nine hosts are evidenced by the title and byte count their log quotes.
  Three are evidenced by a 403 with a `Server` header. Two, Navettakino and Kinotour, are
  inferred from failing in the same run as the others and from nothing else.

## Status and next step

Accepted 2026-09-19 at the measured rate, as a known failure mode of reading the public web
from a datacenter address. No adapter changes, no retry on a challenge body, no header
change, and nothing routed local on it: CLAUDE.md's rule that a datacenter read is not
evidence a site is unreachable is what makes this a failure of the reading side rather than
a property of the cinema.

**Next step: none**, unless the rate rises. What counts as a rise is the maintainer's
decision and is deliberately not a number chosen here; the figure to re-measure against is
the 8-in-50 above, taken the same way, one read of the run list.

**Not proposed, and it should not be:** keeping the challenge page in the log to identify
the filter. A challenge page is a third party's content and CLAUDE.md forbids committing a
raw dump. The title and the byte count are what the logs keep and are enough to recognise
the state.
