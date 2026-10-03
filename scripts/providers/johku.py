"""Four cinemas whose whole site is a Johku storefront. Stdlib only.

Bio Marilyn (Lapua), Vihdin Kino (Vihti), Bio Forum (Tammisaari) and Kinokulma (Oulainen).

**Not Kino Engel or Kino Tapiola.** Those are the cinema's own site with a Johku widget
embedded in it, and the widget's show list needs its API key, which is the line "Access and
ethics" draws. A storefront renders the programme server-side. Probed 2026-09-18; the
evidence is in docs/research/ticketing-platforms.md.

One request per site for the listing, then one film page per distinct product.

The listing, inside `<div class="showgroup">` under a `<h3 class="daytitle">`:

    <a href="/fi_FI/{category}/{slug}" class="js-grid-item js-grid-show" data-product="1038">
      <span class="showrating rating-icon rating-12">K-12</span>
      <h3 class="grid-content-title" data-name="...">...</h3>
      <span class="showlocation" data-location="Bio Marilyn">Bio Marilyn</span>
      <span class="showtime" data-showtime="2026-09-19T14:30:00.000Z">klo 17.30</span>
      <span class="showduration">1 h 27 min</span>

What shapes the parser:

- **`data-showtime` is a UTC instant and the clock beside it is the same moment in
  Helsinki.** Both are read, and a row where they disagree fails the site. All 71 rows
  across the four sites agreed when this was written, and a dropped offset is the fault
  that would otherwise publish every screening three hours out. `cinemantsala.py` records
  the same trap in a feed that drops the `Z`.
- **A grid item inside a day group with no `data-showtime` is a coming-soon entry**, which
  the storefront files under a release date. Bio Marilyn had 14 of them and the other three
  none. They are counted and left out, because there is no time to publish.
- **`data-location` is declared per venue.** A row naming a hall the site does not list
  fails rather than landing under the wrong venue.
- **No price is published.** The grid carries none, the film page carries none, and the
  tariff pages state bands ("Normaali elokuva 13-15 €"). `price` stays empty.
- **The artwork is a landscape banner**, 2048x1365 and 2048x857 on the two measured, so
  `img` stays empty and the TMDB pass supplies a portrait poster.
- **No sold-out state is rendered on a row.** "Loppuunmyyty" appears once per page, inside
  the storefront's own string table.
- **The synopsis carries a language.** Tammisaari publishes Swedish beside Finnish, and the
  slot in films-extra.json is keyed by normalised title and read by every chain showing the
  film. `common.syn_language` places the text and withholds it when nothing is settled.

**A storefront also sells hall hire.** Read 2026-09-18, the day groups held one
("Salivaraus"), and it is the only kind of row left out. The storefront separates it
structurally: every film and event sits under a programme category
(`/fi_FI/nyt-ohjelmistossa/`, `/fi_FI/tulossa/`, `/fi_FI/{slug}`) while hall hire sits
under the generic `/fi_FI/products/`. That path is the rule here, and no word in a title is
read.

**Thin metadata never withholds a screening.** A film page that answers nothing, or
carries no director and no genre, costs the row its synopsis and its genres and nothing
else. The maintainer's instruction of 2026-09-18: a small film that publishes little about
itself still belongs on the site. The Kinola classifier is not applied here, and the
difference is that this listing carries no live-act problem of the kind Karkkila has.

**Zero rows fails the site.** No tenant was seen with an empty programme, so there is no
positive evidence of what one renders and nothing here may claim it is empty:
`common.EmptyProgramme` exists for the case where that evidence is in hand.

**The listing is read only once the server has rendered it whole.** From 2026-10-01 the
front page comes back, from any connection, either whole, or as the first days followed by
skeleton cards, or as a skeleton alone, and the page's script fills the rest through an
`X-ApiKey` call this adapter does not make. The page holds one `js-shows` block per
programme category, and the placeholder is `aria-busy="true"` inside one: Bio Marilyn's
"nyt-ohjelmistossa" block came back whole beside a skeleton "tulossa" one, 9 screenings of
14. A page with a placeholder in any block is read again, up to `LISTING_TRIES` times, and a
site that never renders whole fails with its previous files standing: a short listing would
publish part of the programme as all of it, and a skeleton is not an empty one.
"""
import datetime
import html as html_mod
import http.client
import re
import sys
import time
import urllib.request
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from common import capped, check_shows, fetch, make_opener, syn_language
from etiketti import lang_codes, strict_codes

FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

SITES = [
    {"provider": "biomarilyn", "label": "Bio Marilyn",
     "base": "https://www.biomarilyn.com", "listing": "/",
     "venues": [{"id": "biomarilyn-lapua", "name": "Bio Marilyn", "short": "Bio Marilyn",
                 "city": "Lapua", "loc": "Bio Marilyn"}]},
    {"provider": "vihdinkino", "label": "Vihdin Kino",
     "base": "https://vihdinkino.fi", "listing": "/",
     "venues": [{"id": "vihdinkino-vihti", "name": "Vihdin Kino", "short": "Vihdin Kino",
                 "city": "Vihti", "loc": "Vihdin Kino"}]},
    {"provider": "bioforum", "label": "Bio Forum",
     "base": "https://bioforum.fi", "listing": "/",
     "venues": [{"id": "bioforum-tammisaari", "name": "Bio Forum", "short": "Bio Forum",
                 "city": "Tammisaari", "loc": "Bio Forum"}]},
    {"provider": "kinokulma", "label": "Kinokulma",
     "base": "https://kinokulma.fi", "listing": "/",
     "venues": [{"id": "kinokulma-oulainen", "name": "Kinokulma", "short": "Kinokulma",
                 "city": "Oulainen", "loc": "Kulmasali"}]},
    # Added 2026-09-20, the sixth storefront. `kinohannikainen` on cdn.johku.com behind
    # the cinema's own domain, and the root renders the same `showgroup`/`daytitle`/
    # `js-grid-show` listing as the other five: read that day, eight rows over five day
    # groups, every one `data-location="Hannikaisen sali"`.
    {"provider": "kinohannikainen", "label": "Kino Hannikainen",
     "base": "https://www.kinohannikainen.net", "listing": "/",
     "venues": [{"id": "kinohannikainen-nurmes", "name": "Kino Hannikainen",
                 "short": "Kino Hannikainen", "city": "Nurmes",
                 "loc": "Hannikaisen sali"}]},
    # Added 2026-09-20, the seventh, and the one storefront read from johku.com itself:
    # the cinema has no storefront domain of its own and virtasali.fi links here. Read
    # that day, four rows over two day groups, `data-location="Virta-sali"`.
    {"provider": "kinovirta", "label": "Kino Virta",
     "base": "https://kinovirta.johku.com", "listing": "/",
     "venues": [{"id": "kinovirta-kalajoki", "name": "Kino Virta",
                 "short": "Kino Virta", "city": "Kalajoki", "loc": "Virta-sali"}]},
]

GROUP_RE = re.compile(r'(?<![-\w])class=["\'][^"\']*(?<![-\w])showgroup(?![-\w])')
ITEM_RE = re.compile(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*'
                     r'(?<![-\w])js-grid-show(?![-\w])[^"\']*["\'][^>]*'
                     r'data-product=["\'](\d+)["\'][^>]*>(.*?)</a>', re.S | re.I)
SHOWTIME_RE = re.compile(r'data-showtime=["\']([^"\']+)["\'][^>]*>\s*(?:klo\s*)?'
                         r'(\d{1,2})[.:](\d{2})', re.I)
BARE_TIME_RE = re.compile(r'data-showtime=["\']([^"\']+)["\']')
NAME_RE = re.compile(r'data-name=(["\'])(.*?)\1', re.S)   # to the opening quote
LOC_RE = re.compile(r'data-location=["\']([^"\']*)["\']')
RATING_RE = re.compile(r'(?<![-\w])rating-([0-9]{1,2}|s)(?![-\w])', re.I)
DURATION_RE = re.compile(r'class=["\'][^"\']*(?<![-\w])showduration(?![-\w])[^"\']*["\'][^>]*>'
                         r'(.*?)</span>', re.S | re.I)
HM_RE = re.compile(r'(\d{1,2})\s*h\s*(\d{1,3})\s*min\b', re.I)
MIN_RE = re.compile(r'(\d{1,3})\s*min\b', re.I)
INFO_RE = re.compile(r'class=["\'][^"\']*product-content-infolabel[^"\']*["\'][^>]*>'
                     r'(.*?)</div>\s*<div[^>]*class=["\'][^"\']*product-content-infovalue'
                     r'[^"\']*["\'][^>]*>(.*?)</div>', re.S | re.I)
DESC_RE = re.compile(r'class=["\'][^"\']*product-description__html[^"\']*["\'][^>]*>(.*?)</div>',
                     re.S | re.I)
PARA_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.S | re.I)
TAGS_RE = re.compile(r"<[^>]+>")

# The storefront's generic product path. A programme entry never uses it and the hall hire
# always does, which is what separates the two without reading a title.
PRODUCT_PATH = "/fi_FI/products/"

# A paragraph shorter than this is a release note ("Elokuvateattereissa 4.9.") rather than
# a synopsis. The same length kinola.py uses, for the same reason.
SYN_MIN = 120

# The language as a film page states it, in the three shapes read 2026-10-04 and nothing
# looser. Bio Marilyn's opera: labelled paragraphs, "Kieli : Alkuperäinen", "Tekstitys:
# Suomi". Bio Forum: "Elokuva on puhuttu englanniksi ja tekstitys on sekä suomeksi että
# ruotsiksi." Vihdin Kino: "Esitetään dubattuna versiona eli puhumme suomea." A phrase must
# end where the sentence does, so "ruotsiksi ja suomeksi tekstitettynä" reads as nothing.
# "ilman tekstitystä" is not read: no-subtitles (`XX-S`) is Kino Engel's alone so far.
LABEL_LINE_RE = re.compile(r"^(kieli|tekstitys)\s*:\s*(.+)$", re.I)
TRANSLATIVE = r"[a-zåäö]+ksi(?:\s*(?:,|ja|sekä|että)\s*[a-zåäö]+ksi)*"
SPOKEN_RE = re.compile(r"\bpuhuttu\s+(" + TRANSLATIVE + r")(?=\s*(?:[.,]|ja\s+(?:tekstitys|se)\b|$))",
                       re.I)
SUBTITLED_RE = re.compile(r"\btekstitys\s+on\s+(?:sekä\s+)?(" + TRANSLATIVE + r")(?=\s*(?:[.,]|$))",
                          re.I)
FINNISH_SPOKEN_RE = re.compile(r"\bpuhumme\s+suomea\b", re.I)


class _Response(http.client.HTTPResponse):
    """An HTTP response reader that skips interim 1xx responses.

    Cloudflare answers these storefronts with `103 Early Hints` before the real response.
    `http.client` skips `100 Continue` and nothing else, so urllib reports the 103 as the
    status and `common.fetch` raises on it, while curl reads through to the 200. Recorded
    as a probe detail in docs/research/ticketing-platforms.md on 2026-09-05 and hit again
    here.
    """

    def _read_status(self):
        while True:
            version, status, reason = super()._read_status()
            if status >= 200:
                return version, status, reason
            while True:                       # drain the interim response's own headers
                line = self.fp.readline(http.client._MAXLINE + 1)
                if line in (b"\r\n", b"\n", b""):
                    break


class _Connection(http.client.HTTPSConnection):
    response_class = _Response


class _Handler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_Connection, req, context=self._context)


# Through common.make_opener, so a redirect from https to http is refused here too.
OPENER = make_opener(_Handler())


class ListingRowError(RuntimeError):
    """A row the listing marks as a screening and this parser could not read.

    Skipping it would publish a schedule one screening short with nothing in the log to
    say so, so it fails the site and the previous files stand.
    """


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))
                  .replace("\xa0", " ")).strip()


def _minutes(text):
    """`1 h 27 min` or `87 min` -> "87". -> str, "" when neither shape is there."""
    m = HM_RE.search(text or "")
    if m:
        return str(int(m.group(1)) * 60 + int(m.group(2)))
    m = MIN_RE.search(text or "")
    return m.group(1) if m else ""


DIV_RE = re.compile(r"<div\b|</div\s*>", re.I)


def _element(page, start):
    """The `<div>` beginning at `start` and everything it contains. -> html.

    Counted rather than sliced to the next sibling: the last day group on the page is
    followed by the coming-soon shelf, which renders the same item markup, and a slice to
    the end of the document swallowed it.
    """
    depth = 0
    for m in DIV_RE.finditer(page, start):
        depth += 1 if m.group(0).lower().startswith("<div") else -1
        if depth == 0:
            return page[start:m.end()]
    return page[start:]


def groups(page):
    """-> [html] one per day group.

    Only what a day group holds is a screening. A grid outside one is the coming-soon
    shelf or a product listing, and reading those as screenings would publish a film with
    no time under whatever date happened to be nearby.
    """
    starts = [page.rfind("<", 0, m.start()) for m in GROUP_RE.finditer(page)]
    return [_element(page, i) for i in starts if i >= 0]


# The listing blocks, one per programme category, and the loading placeholder inside one
# (read 2026-10-03).
SHOWS_RE = re.compile(r'<div\b[^>]*class=["\'][^"\']*(?<![-\w])js-shows(?![-\w])')
LOADING_RE = re.compile(r'aria-busy=["\']true["\']'
                        r'|(?<![-\w])(?:product-list-skeleton|sk-product-card)(?![-\w])')
# Reads of one listing before the site fails, and the pause between them. Measured
# 2026-10-03: Bio Forum whole on 8 of 9 reads, Vihdin Kino and Kino Virta about half the
# time, Bio Marilyn on 1 of 19, Kinokulma and Kino Hannikainen on none of 17.
LISTING_TRIES = 5
LISTING_WAIT = 5.0


def listing_state(page):
    """-> "rendered", "loading" or "missing": whether the page has `js-shows` blocks and
    every one of them is free of the loading placeholder."""
    blocks = [_element(page, m.start()) for m in SHOWS_RE.finditer(page)]
    if not blocks:
        return "missing"
    return "loading" if any(LOADING_RE.search(b) for b in blocks) else "rendered"


def read_listing(url):
    """-> (page, reads) once the listing is rendered whole. Raises after `LISTING_TRIES`
    reads that were not: neither a loading nor a missing listing is an empty programme."""
    states = []
    for n in range(LISTING_TRIES):
        if n:
            time.sleep(LISTING_WAIT)
        page = get(url)
        state = listing_state(page)
        if state == "rendered":
            return page, n + 1
        states.append(state)
    raise RuntimeError(
        f"{url}: the listing was not rendered whole on any of {LISTING_TRIES} reads "
        f"({', '.join(states)}). A loading or missing listing is not an empty programme, "
        f"so the previous files stand")


def _rating(block):
    m = RATING_RE.search(block)
    if not m:
        return ""
    v = m.group(1).lower()
    return "S" if v == "s" else f"K-{int(v)}"


def rows(site, page):
    """-> ([row], skipped). `skipped` is the coming-soon entries, counted by title.

    A row is (product, title, loc, start, url, rating, len). Everything else comes from
    the film page.
    """
    out, skipped = [], []
    venues = {v["loc"]: v for v in site["venues"]}
    n = 0
    for group in groups(page):
        for href, product, block in ITEM_RE.findall(group):
            n += 1
            title = _txt(NAME_RE.search(block).group(2)) if NAME_RE.search(block) else ""
            if not title:
                raise ListingRowError(
                    f"{site['provider']}: grid item {n} of the listing has no title")
            if not BARE_TIME_RE.search(block):
                skipped.append(title)
                continue
            loc = _txt(LOC_RE.search(block).group(1)) if LOC_RE.search(block) else ""
            if loc not in venues:
                raise ListingRowError(
                    f"{site['provider']}: grid item {n} names the hall {loc!r}, which this "
                    f"site does not list. Publishing it would file a screening under "
                    f"another venue or drop it without a word")
            out.append({
                "product": product,
                "title": title,
                "venue": venues[loc]["id"],
                "start": _start(site, n, title, block),
                "url": urljoin(site["base"], html_mod.unescape(href)),
                "rating": _rating(block),
                "len": _minutes(DURATION_RE.search(block).group(1)
                                if DURATION_RE.search(block) else ""),
            })
    return out, skipped


def _start(site, n, title, block):
    """The row's UTC instant as Helsinki local time. -> ISO 8601 with offset.

    The rendered clock is checked against it where the row prints one. They agreed on all
    71 rows read on 2026-09-18, and a disagreement means the storefront changed what
    `data-showtime` carries, which would otherwise ship every screening at the wrong hour.
    """
    m = BARE_TIME_RE.search(block)
    try:
        when = datetime.datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    except ValueError as e:
        raise ListingRowError(
            f"{site['provider']}: grid item {n} for {title!r} has an unreadable "
            f"data-showtime {m.group(1)!r}") from e
    if when.tzinfo is None:
        raise ListingRowError(
            f"{site['provider']}: grid item {n} for {title!r} has a data-showtime with no "
            f"offset ({m.group(1)!r}), so the hour it means is not established")
    local = when.astimezone(FI)
    shown = SHOWTIME_RE.search(block)
    if shown and (local.hour, local.minute) != (int(shown.group(2)), int(shown.group(3))):
        raise ListingRowError(
            f"{site['provider']}: grid item {n} for {title!r} prints "
            f"{shown.group(2)}.{shown.group(3)} beside an instant that is "
            f"{local:%H.%M} in Helsinki")
    return local.isoformat()


def _translative(phrase):
    """"englanniksi ja ruotsiksi" -> ["EN", "SV"]; [] unless every word names one language."""
    out = []
    for word in re.findall(r"[a-zåäö]+ksi", (phrase or "").lower()):
        codes = lang_codes(word)
        if len(codes) != 1:
            return []
        if codes[0] not in out:
            out.append(codes[0])
    return out


def film_lang(paras):
    """A film page's description paragraphs -> "EN-A, FI-S, SV-S", "" when none states it."""
    audio, subs = [], []
    for t in paras:
        m = LABEL_LINE_RE.match(t)
        if m:
            (audio if m.group(1).lower() == "kieli" else subs).extend(strict_codes(m.group(2)))
            continue
        spoken, subtitled = SPOKEN_RE.search(t), SUBTITLED_RE.search(t)
        audio += _translative(spoken.group(1)) if spoken else []
        subs += _translative(subtitled.group(1)) if subtitled else []
        if FINNISH_SPOKEN_RE.search(t):
            audio.append("FI")
    parts = [f"{c}-A" for c in dict.fromkeys(audio)] + [f"{c}-S" for c in dict.fromkeys(subs)]
    return ", ".join(parts)


def film_facts(page):
    """One film page -> {len, genres, original, syn, lang}."""
    info = {_txt(k).lower(): _txt(v) for k, v in INFO_RE.findall(page)}
    syn = ""
    body = DESC_RE.search(page)
    paras = [_txt(p) for p in PARA_RE.findall(body.group(1))] if body else []
    for t in paras:
        if len(t) >= SYN_MIN:
            syn = t
            break
    return {"len": _minutes(info.get("kesto", "")),
            "genres": info.get("luokittelu", ""),
            "original": info.get("alkuperäinen nimi", ""),
            "syn": syn, "lang": film_lang(paras)}


def parse(site, listing, pages):
    """-> ({venue_id: [show]}, report). `pages` is {product: film page html}.

    `report` carries what was left out and why: `skipped` the coming-soon entries,
    `hire` the hall-hire rows, and `unplaced` the synopses no language could be settled
    for. A row with no film page read publishes without its genres and synopsis.
    """
    listed, skipped = rows(site, listing)
    facts = {p: film_facts(h) for p, h in pages.items()}
    per_venue = {v["id"]: [] for v in site["venues"]}
    unplaced, hire, hire_shows = set(), set(), 0
    for r in listed:
        if PRODUCT_PATH in r["url"]:
            hire.add(r["title"])
            hire_shows += 1
            continue
        f = facts.get(r["product"]) or {"len": "", "genres": "", "original": "", "syn": "",
                                        "lang": ""}
        venue = next(v for v in site["venues"] if v["id"] == r["venue"])
        show = {
            "eventId": r["product"],
            "title": r["title"],
            "original": f["original"],
            "len": r["len"] or f["len"],
            "rating": r["rating"],
            "genres": f["genres"],
            "method": "",
            "theatre": venue["name"],
            "aud": "",
            "start": r["start"],
            "url": r["url"],
            "img": "",
            "lang": f["lang"],
            "soldOut": False,
            "price": "",
            "provider": site["provider"],
            "venue": r["venue"],
        }
        if f["syn"]:
            lang = syn_language(f["syn"])
            if lang:
                show["_syn"] = {lang: f["syn"]}
            else:
                unplaced.add(r["title"])
        per_venue[r["venue"]].append(show)
    for shows in per_venue.values():
        shows.sort(key=lambda s: s["start"])
    return per_venue, {"skipped": skipped, "hire": hire, "hire_shows": hire_shows,
                       "unplaced": unplaced}


def get(url, tries=3, timeout=30):
    return fetch(url, cache=True, opener=OPENER,
                 headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"},
                 tries=tries, timeout=timeout).decode("utf-8", "replace")


def fetch_site(site, sleep=1.2):
    """Runner contract: the listing, then one film page per distinct product."""
    listing_url = site["base"].rstrip("/") + site["listing"]
    listing, reads = read_listing(listing_url)
    if reads > 1:
        print(f"[{site['provider']}] the listing rendered whole on read {reads} of "
              f"{LISTING_TRIES}")
    listed, _ = rows(site, listing)
    if not listed:
        raise RuntimeError(
            f"{listing_url}: no screening in any day group. No tenant of this platform has "
            f"been seen with an empty programme, so there is no evidence of one to read "
            f"this as, and the previous files stand")
    pid = site["provider"]
    pages = {}
    # The hall-hire rows are dropped before the film pages are chosen: their product page
    # is never read, so the request is not made at all.
    wanted = sorted({(r["product"], r["url"]) for r in listed
                     if PRODUCT_PATH not in r["url"]})
    for n, r in enumerate(capped(wanted, pid)):
        if n:
            time.sleep(sleep)
        product, url = r
        try:
            pages[product] = get(url)
        except Exception as e:
            print(f"[{pid}] film page {url.rsplit('/', 1)[-1]} failed ({e}); the screening "
                  f"publishes without its synopsis and genres")
    per_venue, report = parse(site, listing, pages)
    check_shows(per_venue, pid, {v["id"] for v in site["venues"]})
    print(f"[{pid}] {len(listed)} screening(s) in day groups, {len(pages)} film page(s) read")
    if report["skipped"]:
        print(f"[{pid}] {len(report['skipped'])} coming-soon entry/entries with no time, "
              f"left out: {', '.join(sorted(set(report['skipped']))[:8])}")
    if report["hire"]:
        print(f"[{pid}] {len(report['hire'])} hall-hire title(s) over "
              f"{report['hire_shows']} row(s) left out: "
              f"{', '.join(sorted(report['hire'])[:8])}")
    if report["unplaced"]:
        print(f"[{pid}] {len(report['unplaced'])} synopsis/synopses withheld, no language "
              f"settled: {', '.join(sorted(report['unplaced'])[:8])}")
    if not any(per_venue.values()):
        raise RuntimeError(
            f"{listing_url} holds {len(listed)} screening(s) in its day groups and none "
            f"published. That is a template failure rather than a cinema with nothing on")
    for v in site["venues"]:
        shows = per_venue[v["id"]]
        days = sorted({s["start"][:10] for s in shows})
        print(f"[{pid}] {v['name']}: {len(shows)} showtimes, {len(days)} dates")
    return per_venue


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "biomarilyn"
    site = next(s for s in SITES if s["provider"] == which)
    for vid, shows in fetch_site(site).items():
        print(f"{vid}: {len(shows)} showtimes")
        for s in shows[:5]:
            print(f"   {s['start'][:16]}  {s['title'][:34]:36} {s['rating']:5} "
                  f"{s['len']:4} {s['genres'][:20]:22} {s['url'][-28:]}")
