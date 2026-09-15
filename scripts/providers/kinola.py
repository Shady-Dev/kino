"""Kino Kilta (Turku) and Kino Laika (Karkkila), both on Kinola. Stdlib only.

Kinola is the platform behind Cinema Orion's ticketing too, and `orion.py` reads its third
front-end template, a `table.kinola-day`. Neither site here renders that table, so
`orion.parse` returns zero on both: this is a separate module with a handler per template
rather than two `SITES` entries. `orion.py` is unchanged.

**Konepaja has no `SITES` entry.** `kinokonepaja.fi` renders the Kinola filters and a
"tulossa" grid of film pages, and its screening list reads "Ei tulevia tapahtumia."
Re-read 2026-09-15, which is the check the build requirements asked for; the 2026-09-14
finding stands. It is a real tenant publishing no screening, the same position as Kino
Kaustinen, and it gets an entry when it lists one.

## The publication policy

Adopted 2026-09-15; the decision is in `docs/archive/2026-09-providers.md` under "Kinola:
the publication policy, adopted" and the evidence in `docs/research/kinola.md`. Concerts
and films are one WordPress `film` post type with nothing structural separating them, and
Laika's own filter lists its concerts under "Kaikki elokuvat". So:

- a screening publishes only when its film page carries **labelled film metadata**;
- everything else is omitted, and the count is logged;
- an override decides before the classifier runs, in either direction.

**Three states, and only one of them a runtime decision.** `film` and `unresolved` are what
the classifier can reach on its own. `non-film` is reachable **only** through a scoped,
evidence-backed exclusion, because these pages carry no structural signal for a live act
and reading a word out of a title or a synopsis is what the policy forbids. So the measured
report says "confirmed non-film" of an exclusion and nothing else: the classifier never
identifies a gig by itself, and this module does not pretend otherwise.

**The precedence.** An exclusion beats generic metadata. A billed live act whose page fills
`Ohjaus` or `Lajityyppi` would otherwise publish, and that is exactly the case an exclusion
exists for, so the override is consulted before the labels are looked at rather than after.

**Revalidation, at run time and for every entry.** Each override is scored against the page
as it stands now: `active` when it changes the classifier's verdict, `redundant` when the
classifier already reaches the same outcome, and `evidence-unavailable` when the event is
not in the listing or its page was not read. The third is not the second: a film that has
left the programme proves nothing about whether its override is still needed.

**An age classification and a runtime are not film evidence.** This is the trap the policy
was corrected for: Laika's billed live acts carry both. *Arppa* reads "130 min K-18" and
*Livemusavisa* "120 min K-18", with no director and no genre. Only the labelled director
and genre fields separate a film from a gig here, so only those are read as evidence.

Measured 2026-09-15 over 65 distinct film pages: 53 carry a director or a genre label and
12 carry neither. Eleven of the twelve are billed live acts (Arppa, Tuure Kilpeläinen,
Mariska, Knipi, Antti Autio, Livemusavisa, Ykspihlajan Kino-Orkesteri, Valimo/Bico/These
Boots, Dave Lindholm & Pepe Ahlqvist, 50 vuotta rokkia Karkkilasta, a festival bus trip)
and one is a genuine film, *A Fox Under a Pink Moon*, whose page names its director in
prose but fills no field. That one is the override list's first and only entry.

## The two listing templates

Both wrap each screening in a block whose class is exactly `kinola-event`, so the blocks
are found by that token and sliced between occurrences rather than by matching tags.

    kilta   <li class="kinola-event"> .time "20:00", .date "TI 15.9.2026",
            a.kinola-event-title -> /film/{slug}/, .movie-subtitle (a strand, not a
            subtitle), .duration-info "106 min", a.kinola-event-tickets-link
    laika   <div class="kinola-event"> img.kinola-event-poster,
            a.kinola-event-title -> /film/{slug}/, .kinola-event-venue,
            .kinola-event-date "16/09/2026 14:00", a.kinola-event-tickets-link or
            span.kinola-event-tickets-link-sold-out

**Both dates carry their year**, so nothing infers one and `common.resolve_year` is not
used. Kilta writes `D.M.YYYY` after a weekday abbreviation, Laika `DD/MM/YYYY HH:MM`.

**A sold-out row keeps its screening.** Laika drops the checkout anchor and renders
`<span class="kinola-event-tickets-link-sold-out">Loppuunmyyty</span>` instead, so the
destination falls back to the film page's own href, read from the listing and never built,
with `soldOut` true. Dropping those rows would hide four of Laika's screenings.

## The two film-page templates

    kilta   <dl class='info'> of <dt>Label</dt><dd>Value</dd>: Valmistumisvuosi, Maat,
            Ensi-ilta, Ohjaaja, Pääosissa, Lajityyppi, Kieli, Kesto
    laika   <strong>Label</strong> <br> value <br><br>: Ohjaus, Kieli, Tekstitys, with
            the runtime and the classification as bare text above them

One reader handles both, because the classifier has to be template-independent: a label
is a `<dt>`/`<dd>` pair or a `<strong>` followed by text, and both land in one dict.

- **Kilta's rating is an `alt` attribute**, `alt='Ikäraja: K-12'`, and the `alt` is what is
  read. The image beside it is `age-7.svg` on a K-12 film, so the file name is not the
  rating. "sallittu kaikille" maps to `S`.
- **Laika's rating and runtime are bare text** in the block above the first paragraph, so
  they are read from that bounded region and nowhere else.
- The same film can be rated differently by the two cinemas: *Hetki ennen valoa* is K-12 on
  Kilta and K-7 on Laika. Each publishes what its own page says, and `enrich_tmdb` reports
  the disagreement rather than either overwriting the other.
- Kilta's poster is the page's `og:image`; Laika's comes from the listing row.
- `LANG` is imported from `gilda.py`, which already maps the Finnish language names these
  pages use, so a code cannot drift between two readers of the same vocabulary.

## Requests

One listing per site, then one film page per distinct film: 41 for Kilta and 24 for Laika
when measured. Those pages carry the classification, so they decide what publishes, and
`common.budget_or_raise` applies rather than `capped`: trimming the loop would drop
screenings instead of costing metadata.
"""
import datetime
import html as html_mod
import json
import pathlib
import re
import sys
import time
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from common import EmptyProgramme, budget_or_raise, fetch
from gilda import LANG

FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"

OVERRIDE_FILE = pathlib.Path(__file__).resolve().parent / "kinola-overrides.json"

SITES = [
    {"provider": "kinokilta", "label": "Kino Kilta", "base": "https://www.kinokilta.fi",
     "listing": "/naytokset/", "template": "kilta",
     "venues": [{"id": "kilta-turku", "name": "Kino Kilta", "short": "Kino Kilta",
                 "city": "Turku"}]},
    {"provider": "kinolaika", "label": "Kino Laika", "base": "https://www.kinolaika.fi",
     "listing": "/ohjelmisto/", "template": "laika",
     "venues": [{"id": "laika-karkkila", "name": "Kino Laika", "short": "Kino Laika",
                 "city": "Karkkila"}]},
]

# The label whose presence is film evidence. Not the runtime and not the classification:
# see the module docstring, Laika's live acts carry both.
FILM_LABELS = ("ohjaaja", "ohjaus", "lajityyppi")

# The policy's three states. NON_FILM is never a runtime verdict; it is what an
# evidence-backed exclusion asserts.
FILM, NON_FILM, UNRESOLVED = "film", "non-film", "unresolved"
# How an override stands against the page as it is now.
ACTIVE, REDUNDANT, UNAVAILABLE = "active", "redundant", "evidence-unavailable"

EVENT_RE = re.compile(r'class=["\']kinola-event["\']')
TITLE_RE = re.compile(r'<a[^>]*class=["\']kinola-event-title["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                      re.S | re.I)
SLUG_RE = re.compile(r'/film/([^/?#"\']+)', re.I)
TICKET_RE = re.compile(r'<a[^>]*class=["\'][^"\']*kinola-event-tickets-link[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
                       re.S | re.I)
SOLD_OUT_RE = re.compile(r'kinola-event-tickets-link-sold-out', re.I)
DIV_CLASS_RE = r'<div[^>]*class=["\'][^"\']*\b%s\b[^"\']*["\'][^>]*>(.*?)</div>'
SPAN_CLASS_RE = r'<span[^>]*class=["\'][^"\']*\b%s\b[^"\']*["\'][^>]*>(.*?)</span>'
POSTER_RE = re.compile(r'<img[^>]*class=["\'][^"\']*kinola-event-poster[^"\']*["\'][^>]*>', re.I)
SRC_RE = re.compile(r'(?:data-)?src=["\']([^"\']+)["\']', re.I)
KILTA_DATE_RE = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{4})')
KILTA_TIME_RE = re.compile(r'(\d{1,2})[:.](\d{2})')
LAIKA_DATE_RE = re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2})[:.](\d{2})')
MIN_RE = re.compile(r'(\d{1,3})\s*min\b', re.I)
DT_DD_RE = re.compile(r'<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', re.S | re.I)
STRONG_RE = re.compile(r'<strong[^>]*>\s*([A-Za-zÄÖÅäöå]{3,20})\s*</strong>\s*(?:<br\s*/?>)?'
                       r'(.*?)(?=<strong|<br\s*/?>\s*<br|<p[\s>]|</div>|$)', re.S | re.I)
KILTA_RATING_RE = re.compile(r'alt=["\']Ikäraja:\s*([^"\']+)["\']', re.I)
LAIKA_RATING_RE = re.compile(r'\bK-?(\d{1,2})\b|(?<![A-Za-zÄÖÅäöå])(S)(?![A-Za-zÄÖÅäöå])')
OG_IMAGE_RE = re.compile(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']'
                         r'|<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', re.I)
SYN_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.S | re.I)
TAGS_RE = re.compile(r"<[^>]+>")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))
                  .replace("\xa0", " ")).strip()


def _one(pattern, cls, block):
    m = re.search(pattern % cls, block, re.S | re.I)
    return _txt(m.group(1)) if m else ""


def blocks(page):
    """-> [html] one per screening, sliced between `class="kinola-event"` occurrences.

    The class token is matched exactly: `kinola-event-title`, `-date`, `-venue` and
    `-tickets-link` all contain it as a prefix, so a substring match would cut a block
    into pieces at its own children.
    """
    starts = [page.rfind("<", 0, m.start()) for m in EVENT_RE.finditer(page)]
    starts = [i for i in starts if i >= 0]
    out = []
    for n, i in enumerate(starts):
        out.append(page[i:starts[n + 1] if n + 1 < len(starts) else len(page)])
    return out


def _title_and_slug(block, base):
    m = TITLE_RE.search(block)
    if not m:
        return "", "", ""
    href, inner = html_mod.unescape(m.group(1)), m.group(2)
    sm = SLUG_RE.search(href)
    return _txt(inner), (sm.group(1) if sm else ""), urljoin(base, href)


def _destination(block, base, film_url):
    """The checkout href the row emits, or the film page when the row is sold out.

    Never constructed: a sold-out Laika row has no anchor at all, and building a checkout
    URL from a copied path is what shipped six dead Nexxo links.
    """
    m = TICKET_RE.search(block)
    if m and not SOLD_OUT_RE.search(m.group(0)):
        return urljoin(base, html_mod.unescape(m.group(1))), False
    return film_url, bool(SOLD_OUT_RE.search(block))


def events_kilta(page, site):
    """-> [{slug, title, film_url, start, url, soldOut, method, len}]"""
    out = []
    for b in blocks(page):
        title, slug, film_url = _title_and_slug(b, site["base"])
        d = KILTA_DATE_RE.search(_one(DIV_CLASS_RE, "date", b))
        t = KILTA_TIME_RE.search(_one(DIV_CLASS_RE, "time", b))
        if not (title and d and t):
            continue
        try:
            start = datetime.datetime(int(d.group(3)), int(d.group(2)), int(d.group(1)),
                                      int(t.group(1)), int(t.group(2)), tzinfo=FI)
        except ValueError:
            continue
        url, sold = _destination(b, site["base"], film_url)
        dur = MIN_RE.search(_one(DIV_CLASS_RE, "duration-info", b))
        out.append({"slug": slug, "title": title, "film_url": film_url,
                    "start": start.isoformat(), "url": url, "soldOut": sold,
                    "method": _one(DIV_CLASS_RE, "movie-subtitle", b),
                    "len": dur.group(1) if dur else "", "img": ""})
    return out


def events_laika(page, site):
    out = []
    for b in blocks(page):
        title, slug, film_url = _title_and_slug(b, site["base"])
        d = LAIKA_DATE_RE.search(_one(SPAN_CLASS_RE, "kinola-event-date", b))
        if not (title and d):
            continue
        try:
            start = datetime.datetime(int(d.group(3)), int(d.group(2)), int(d.group(1)),
                                      int(d.group(4)), int(d.group(5)), tzinfo=FI)
        except ValueError:
            continue
        url, sold = _destination(b, site["base"], film_url)
        pm = POSTER_RE.search(b)
        src = SRC_RE.search(pm.group(0)) if pm else None
        out.append({"slug": slug, "title": title, "film_url": film_url,
                    "start": start.isoformat(), "url": url, "soldOut": sold,
                    "method": "", "len": "",
                    "img": urljoin(site["base"], html_mod.unescape(src.group(1)))
                           if src else ""})
    return out


TEMPLATES = {"kilta": events_kilta, "laika": events_laika}


def labels(page):
    """-> {lowercased label: value} from either film-page template.

    Both shapes land in one dict so the classifier does not have to know which site it is
    reading: Kilta writes `<dt>Ohjaaja</dt><dd>Klaus Härö</dd>`, Laika writes
    `<strong>Ohjaus</strong> <br> Klaus Härö`.
    """
    out = {}
    for k, v in DT_DD_RE.findall(page):
        key, val = _txt(k).lower(), _txt(v)
        if key and val:
            out.setdefault(key, val)
    for k, v in STRONG_RE.findall(page):
        key, val = _txt(k).lower(), _txt(v)
        if key and val:
            out.setdefault(key, val)
    return out


def _head(page):
    """Laika's bare runtime and classification sit above the first paragraph. Bounded on
    purpose: a `K-12` or a `min` anywhere in a synopsis is not this film's own."""
    i = page.find("<strong>")
    j = page.find("<p", i if i >= 0 else 0)
    return _txt(page[i:j]) if 0 <= i < j else ""


def _rating(page, head):
    """Kilta's `alt` first, then Laika's bare token. "" when the page says nothing: the
    shared classification pass fills a blank from another chain showing the same film."""
    m = KILTA_RATING_RE.search(page)
    if m:
        v = _txt(m.group(1))
        if v.lower().startswith("sallittu"):
            return "S"
        d = re.search(r"(\d+)", v)
        return f"K-{d.group(1)}" if d else ""
    m = LAIKA_RATING_RE.search(head)
    if not m:
        return ""
    return "S" if m.group(2) else f"K-{m.group(1)}"


def _lang(facts):
    """-> "FI-A, SV-S" using Finnkino's tags, from the Finnish language names."""
    out = []
    for label, suffix in (("kieli", "-A"), ("tekstitys", "-S")):
        for part in re.split(r"[,/]|\bja\b", facts.get(label, "")):
            code = LANG.get(part.strip().lower(), "")
            if code and code + suffix not in out:
                out.append(code + suffix)
    return ", ".join(out)


def film_facts(page):
    """-> {labels, rating, len, genres, img, syn} for one film page."""
    facts = labels(page)
    head = _head(page)
    dur = MIN_RE.search(facts.get("kesto", "")) or MIN_RE.search(head)
    og = OG_IMAGE_RE.search(page)
    syn = ""
    for p in SYN_RE.findall(page):
        t = _txt(p)
        if len(t) > 120:
            syn = t
            break
    return {"labels": facts, "rating": _rating(page, head),
            "len": dur.group(1) if dur else "",
            "genres": facts.get("lajityyppi", ""),
            "img": (og.group(1) or og.group(2)) if og else "",
            "syn": syn, "lang": _lang(facts)}


def load_overrides(path=None):
    """-> {(provider, slug): entry}. Absent file is no overrides, not an error."""
    path = path or OVERRIDE_FILE
    try:
        doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    out = {}
    for row in doc.get("overrides", []):
        pid, slug, action = row.get("provider"), row.get("slug"), row.get("action")
        if pid and slug and action in ("include", "exclude"):
            out[(pid, slug)] = row
    return out


def default_state(facts):
    """-> FILM or UNRESOLVED: everything the classifier can say without help.

    Never NON_FILM. Nothing on these pages marks a live act structurally, so a runtime
    verdict of "this is not a film" would have to come from a word in a title or a
    synopsis, which the policy forbids.
    """
    return FILM if any(facts["labels"].get(k) for k in FILM_LABELS) else UNRESOLVED


def classify(provider, slug, facts, overrides):
    """-> (publish, state, default).

    `state` is the policy's verdict and `default` is what the classifier would have said
    alone, which is what makes revalidation possible at all.

    The override is consulted before the labels, which is the adopted precedence: explicit
    event-level evidence of a live act prevents automatic inclusion even where generic
    metadata is present. A billed gig whose page fills `Ohjaus` would publish otherwise.
    """
    d = default_state(facts)
    o = overrides.get((provider, slug))
    if o:
        return (True, FILM, d) if o["action"] == "include" else (False, NON_FILM, d)
    return d == FILM, d, d


def override_state(entry, default, listed, page_read):
    """-> ACTIVE, REDUNDANT or UNAVAILABLE for one override, against the page as it is.

    Redundancy is a statement about the decision: an `include` is redundant once the page
    classifies as a film on its own, and an `exclude` is redundant once it does not. An
    entry whose event is not in the listing, or whose page was not read, is neither active
    nor redundant: the evidence for it is simply unavailable this run, and dropping it on
    that basis would delete a still-needed override the first time a film went off
    programme.
    """
    if not listed or not page_read:
        return UNAVAILABLE
    if entry["action"] == "include":
        return REDUNDANT if default == FILM else ACTIVE
    return ACTIVE if default == FILM else REDUNDANT


def parse(site, listing, pages, overrides=None):
    """-> ({venue_id: [show]}, omissions). `pages` is {slug: film page html}.

    `omissions` counts what the policy left out, as unique films and as screenings, split
    by state: `non_film_*` is what an evidence-backed exclusion asserted, `unresolved_*`
    what the classifier could not resolve. The two are never merged, because only the
    first is a claim that something is not a film and only a person made it.

    `om["overrides"]` scores every entry against the pages this run read: active,
    redundant, or evidence-unavailable.
    """
    overrides = {} if overrides is None else overrides
    venue = site["venues"][0]
    rows = TEMPLATES[site["template"]](listing, site)
    facts_by_slug = {slug: film_facts(html) for slug, html in pages.items()}
    listed = {e["slug"] for e in rows if e["slug"]}
    shows, seen = [], set()
    om = {"non_film_films": set(), "non_film_shows": 0,
          "unresolved_films": set(), "unresolved_shows": 0, "overrides": {}}
    # Every entry for this provider, not only the ones the listing happens to hold, so an
    # override whose film has left the programme is reported rather than silently ignored.
    for (pid, slug), entry in sorted(overrides.items()):
        if pid != site["provider"]:
            continue
        facts = facts_by_slug.get(slug)
        om["overrides"][slug] = override_state(
            entry, default_state(facts) if facts else UNRESOLVED,
            slug in listed, facts is not None)
    for e in rows:
        slug = e["slug"] or ""
        facts = facts_by_slug.get(slug) or {"labels": {}, "rating": "", "len": "",
                                            "genres": "", "img": "", "syn": "",
                                            "lang": ""}
        publish, state, _ = classify(site["provider"], slug, facts, overrides)
        if not publish:
            if state == NON_FILM:
                om["non_film_films"].add(e["title"])
                om["non_film_shows"] += 1
            else:
                om["unresolved_films"].add(e["title"])
                om["unresolved_shows"] += 1
            continue
        key = (e["start"], slug or e["title"])
        if key in seen:
            continue
        seen.add(key)
        row = {
            "eventId": slug or e["title"].lower(),
            "title": e["title"],
            "original": "",
            "len": e["len"] or facts["len"],
            "rating": facts["rating"],
            "genres": facts["genres"],
            "method": e["method"],
            "theatre": venue["name"],
            "aud": "",
            "start": e["start"],
            "url": e["url"],
            "img": e["img"] or facts["img"],
            "lang": facts["lang"],
            "soldOut": e["soldOut"],
            "price": "",
            "provider": site["provider"],
            "venue": venue["id"],
        }
        if facts["syn"]:
            row["_syn"] = facts["syn"]
        shows.append(row)
    shows.sort(key=lambda s: s["start"])
    return {venue["id"]: shows}, om


def get(url, tries=3, timeout=30):
    return fetch(url, cache=True,
                 headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"},
                 tries=tries, timeout=timeout).decode("utf-8", "replace")


def fetch_site(site, sleep=1.2):
    """Runner contract: one listing, then one film page per distinct film.

    A listing with no screening block is `EmptyProgramme`: the Kinola template renders the
    filters either way, so an empty event list is the cinema saying it has nothing on. A
    listing that holds blocks while nothing publishes is **not**, because the film pages
    then decided it, which is the policy working rather than a failure.
    """
    listing = get(site["base"].rstrip("/") + site["listing"])
    rows = TEMPLATES[site["template"]](listing, site)
    if not rows:
        raise EmptyProgramme(f"{site['base']}{site['listing']} lists no screening")
    slugs = budget_or_raise(sorted({e["slug"] for e in rows if e["slug"]}),
                            site["provider"])
    pages = {}
    for n, slug in enumerate(slugs):
        if n:
            time.sleep(sleep)
        url = next(e["film_url"] for e in rows if e["slug"] == slug)
        try:
            pages[slug] = get(url)
        except Exception as e:
            raise RuntimeError(
                f"{url}: {e}. The film page carries the classification, so a missing one "
                f"would silently omit that film's screenings") from e
    per_venue, om = parse(site, listing, pages, load_overrides())
    shows = per_venue[site["venues"][0]["id"]]
    pid = site["provider"]
    print(f"[{pid}] {len(rows)} screening(s) listed, {len(slugs)} film page(s) read")
    # The two omission classes are reported apart on purpose. "Confirmed non-film" says a
    # person excluded it on recorded evidence; "unresolved" says the classifier could not
    # tell, which is not the same claim and must not be dressed up as one.
    print(f"[{pid}] omitted {len(om['non_film_films'])} confirmed non-film(s) by "
          f"evidence-backed exclusion over {om['non_film_shows']} screening(s), and "
          f"{len(om['unresolved_films'])} unresolved over {om['unresolved_shows']}")
    if om["non_film_films"]:
        print(f"[{pid}] confirmed non-film: "
              f"{', '.join(sorted(om['non_film_films'])[:12])}")
    if om["unresolved_films"]:
        print(f"[{pid}] unresolved: {', '.join(sorted(om['unresolved_films'])[:12])}")
    for slug, state in sorted(om["overrides"].items()):
        print(f"[{pid}] override {slug}: {state}")
    if not shows:
        raise RuntimeError(
            f"{site['base']}{site['listing']} lists {len(rows)} screening(s) and none "
            f"published. The listing is not empty, so this is a template or "
            f"classification failure rather than a cinema with nothing on")
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {site['venues'][0]['name']}: {len(shows)} showtimes, {len(days)} dates")
    return per_venue


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "kinokilta"
    site = next(s for s in SITES if s["provider"] == which)
    for vid, shows in fetch_site(site).items():
        print(f"{vid}: {len(shows)} showtimes")
        for s in shows[:5]:
            print(f"   {s['start'][:16]}  {s['title'][:30]:32} {s['rating']:5} "
                  f"{s['len']:4} {s['lang']:14} {s['method'][:22]:24} sold={s['soldOut']}")
