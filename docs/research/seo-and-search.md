# Search Console: what the pages actually rank for

Moved out of `IDEAS.md` on 2026-09-15. One export so far, read on 2026-09-04 over the five
days 2026-08-29 to 09-02. The tables do not share a denominator, so a later export is
comparable only table by table over the same window.

**Status and next step.** Search visibility collapsed on 2026-10-03 and the cause is
unconfirmed. The read of 2026-10-20 below separates what was measured from the
spam-update hypothesis. No indexing change is proposed on this evidence. Next: the
maintainer's Security issues and URL Inspection reads, then a weekly comparison. The
"ohjelmisto" experiment waits, since a collapsed baseline measures nothing.

**Decided.** No city pages for one-cinema towns: they would compete with the theatre pages
that already rank. Crawl blocking and search-index removal are different things: on
2026-09-20 the first of the two changed, `Disallow: /status/?` closing the status page's
294 parameterised utility URLs to crawlers, and the second did not. That record, and the
snippet and structured-data work this rests on, are in
[docs/archive/2026-09-ops.md](../archive/2026-09-ops.md).

---

### Search Console baseline, 2026-08-29 to 2026-09-02 (read 2026-09-04)
First export, web search, five days. The tables do not share a denominator: chart, devices
and countries sum to 1776 impressions and 12 clicks (CTR 0.68 %); pages to 1951, since an
impression counts once per URL; queries to 1300, since rare queries are anonymised. A later
export is comparable only table by table over the same window.

Theatre pages carried about 92 % of page-level impressions; 74 of 170 canonical pages
appeared; small-town cinemas led (Leffabuumi Kinolinna and Kino Ritz 168 and 167
impressions at positions 5 to 7, Savon Kinot's four pages about 300 together) while
Finnkino pages sat at 12 to 20. Visible queries: the cinema's name (746), "elokuvat
<city>" (285), "<cinema> ohjelmisto" (248, two of three attributed clicks); none contained
"leffavuoro". Mobile position 8.4, desktop 23.6.

Decisions, 2026-09-04: no broad SEO change on five days of data; re-read after two to four
weeks. No city pages for one-cinema towns, which would compete with the theatre pages that
rank. The one experiment, when run: "ohjelmisto" in Finnish theatre-page titles and
descriptions on a subset against an unchanged control, measured over two to four weeks.
Desktop position and the absence of brand queries: watch.

### Search visibility collapse from 2026-10-03 (read 2026-10-20)

**Findings, Search Console.** Exports dated 2026-10-20, US Pacific days. From 2026-09-20 to
10-02 the site had 3352 impressions and 26 clicks a day at positions 7.2 to 7.9. From 10-03
to 10-17 it had 29 impressions a day, 1 click in total, at positions 12.8 to 31.5. Crawling
went on at about 119 requests a day, 99.46 % of them answered 200. The maintainer read
Manual actions and Removals that day and both were empty. Security issues has not been
read. A live URL Inspection of `/teatteri/kino-kirkkonummi-kirkkonummi/` reported the page
fetched and indexable. The live test does not show Google's selected canonical or the
indexing history.

**Findings, the site.** No commit in the window touches indexing. `robots.txt` last changed
on 2026-09-26. At `62d29c038` all 474 landing pages declare themselves canonical and carry
reciprocal hreflang with x-default, and the app's root carries none. Their scripts set the
theme and send one pageview, and nothing rewrites the content. Before the drop, Finnish
pages earned 88 % of impressions and 312 of 337 clicks, sv 5.7 % and 7, en 5.9 % and 16.
The sv and en theatre pages share a median 58 % of their non-synopsis words with the
Finnish page, mostly titles, times and prices. A synopsis is printed only in the page's
language, and 43 of the 141 Swedish theatre pages print none. 20 theatre pages show no
screening in their four-day window. 16 of them name the next date, and those cinemas have
published 1 to 13 screenings from it on. Alatalo Kiuruvesi has rows from 10-29, but its
last read is stale and the page says it could not be checked. Kino Metso Vaajakoski and
Alatalo Toholampi are empty by their adapters' reading. K13's read failed and its last rows
ended on 10-08. Since `a665c68a2` the same day it lists screenings from 10-25. Synopses are
TMDB's text or the cinemas' own, and the footer credited all of them to TMDB until the
footer fix of 2026-10-20.

**Findings, Google, 2026-10-20, one browser.** `site:` returned the Finnish, Swedish and
English Kirkkonummi pages and the Finnish Helsinki page, each under its own URL. Google's
stored copy of the Finnish Kirkkonummi page dates from 28.9. HTML is about 21 % of 5600
crawl requests over 51 days, about 23 HTML requests a day for 475 URLs. "leffavuoro" and
"leffavuoro kino kirkkonummi" returned no leffavuoro.fi result. The Search Status Dashboard
dates the September 2026 spam update from 2026-09-24 to 10-07/08.

**Inference.** The timing fits the spam update, and that is a hypothesis. An empty Manual
actions report does not rule out a technical, indexing, security or other ranking cause,
and `site:` does not show what share of the sitemap is indexed. Google's spam policies turn
on manipulation and little value to a reader. Automation, shared templates and a low
click share do not establish a violation on their own.

**Open questions.** Security issues. For `/`, the Finnish, Swedish and English Kirkkonummi
pages, the Finnish and Swedish Helsinki pages and Kino Metso Hankasalmi, the Google Index
view's page indexing state, Google-selected canonical and last crawl. The indexed count by
date in the Pages report around 10-03.

**Status and next step.** Withdrawn on review the same day: `noindex` for window-empty
pages, which would drop touring cinemas between visits, and `noindex` for every sv and en
page. No index removal is proposed on this evidence. Any later indexing change names its URL
set, a control set, the expected effect, the pre-drop impressions it puts at risk and a
rollback rule decided before it ships. Weekly, compare Search Console with the 2026-09-20
to 10-02 baseline by section, language, device and country, and for brand, "<cinema>
ohjelmisto" and "elokuvat <city>" queries. Changes that would serve readers are proposed
separately. The "coming later" list from 2026-10-18 shows the published titles behind a
window-empty page. The footer credit is corrected in its own commit.
