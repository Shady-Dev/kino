"""Kino Engel (Sofiankatu 4, Helsinki) — front-page scrape. Stdlib only.

kinoengel.fi answers **HTTP 202 with an `SG-Captcha: challenge` header** to a datacenter
address, so this runs from the Mac alongside Finnkino and Kino Akseli. The challenge is
on IP reputation, not on the request shape, so there is nothing to spoof and nothing that
would make it work from Actions.

The site has an open WordPress REST API and it looked for a moment like the whole
adapter: `wp/v2/elokuva` exists and exposes `acf`. It is empty on every film, and the
endpoint returns 899 posts across 9 pages, so it is the archive rather than the
programme. The schedule only exists in the rendered page. REST is still worth a second
pass later for the cinema's own Finnish synopsis and a full-size poster; see the note at
the bottom.

Two things about this site that shape the parser:

- **Rows carry their own date**, "La 29.08." next to "klo 17:30", so the `<h2>` day
  headings and the date `<select>` above them are both redundant. Parsing the rows alone
  means the heading markup can change without breaking this.
- **A strand is a separate `elokuva` post.** `autofiktio` (3303) and `kesakino-autofiktio`
  (3295) are two records for one film, and 23 of the first 100 posts are `kesakino-`. So
  the slug cannot be the `eventId`: it would split one film into two cards in one venue,
  each with its own poster lookup and its own TMDB miss. The id is the slug with the
  strand prefix removed, which is exactly the plain post's slug, so both halves land on
  one card.

**KesäKino is a room, not a strand.** It is the outdoor screen, so it goes in `aud` where
the client renders it on the showtime stub, next to "Sali 1" and "LUXE 4". Routing it
through `strands.py` would put it in `method` as a pill beside Anniskelu and SenioriKino,
which frames a place as a programme category. `kesäkino` stays in `EVENT_PREFIXES`
regardless, because `enrich_tmdb.clean()` needs it off the TMDB search string; this
adapter simply strips it first, so `run.py`'s central pass finds nothing left to split.
`BARNSÖNDAGAR:` and `BARNFESTIVAL:` are real strands and are left for that pass.
"""
import datetime
import html as html_mod
import re
import sys
import time
from zoneinfo import ZoneInfo

from common import capped, fetch

BASE = "https://kinoengel.fi"
URL = BASE + "/"
FI = ZoneInfo("Europe/Helsinki")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

VENUE = {"id": "engel-helsinki", "provider": "engel", "providerId": "1",
         "name": "Kino Engel", "short": "Kino Engel", "city": "Helsinki"}

SITES = [{"provider": "engel", "label": "Kino Engel", "venues": [VENUE]}]

# The outdoor screen. Slug prefix is the reliable signal; the visible title carries
# "KESÄKINO:" too, but the slug is ascii-folded and cannot be affected by a typo.
OUTDOOR_SLUG = "kesakino-"
OUTDOOR_AUD = "KesäKino"

# Attribute quoting is mixed on this page: WordPress emits double quotes, the Johku
# schedule widget emits single. Every attribute regex here has to accept both, which
# cost a live run to find: `<img src='...'>` matched nothing and every poster came back
# empty while the parse otherwise looked healthy.
Q = r'["\']'
ANCHOR_RE = re.compile(r'<a\b[^>]*href=["\'](?:https?://kinoengel\.fi)?(/elokuva/([^"\'/]+)/?)["\'][^>]*>'
                       r'(.*?)</a>', re.S | re.I)
DATE_RE = re.compile(r'(?:Ma|Ti|Ke|To|Pe|La|Su)\s*(\d{1,2})\.(\d{1,2})\.')
TIME_RE = re.compile(r'klo\s*(\d{1,2})[:.](\d{2})')
IMG_RE = re.compile(r'<img\b[^>]*>', re.I)
SRCSET_RE = re.compile(r'srcset=["\']([^"\']+)["\']')
SRC_RE = re.compile(r'\b(?:data-src|src)=["\']([^"\']+)["\']')
TAGS_RE = re.compile(r"<[^>]+>")
# A premiere card writes the weekday out in full and leaves the time span empty.
COMING_RE = re.compile(r'(?:Maanantai|Tiistai|Keskiviikko|Torstai|Perjantai|Lauantai|'
                       r'Sunnuntai)\s*(\d{1,2})\.(\d{1,2})\.')
NOISE_RE = re.compile(r"Osta liput|Lue lisää[\s›»>]*|Varaa|Liput"
                      r"|klo\s*\d{1,2}[:.]\d{2}"
                      r"|(?:Maanantai|Tiistai|Keskiviikko|Torstai|Perjantai|Lauantai"
                      r"|Sunnuntai|Ma|Ti|Ke|To|Pe|La|Su)\s*\d{1,2}\.\d{1,2}\.", re.I)
# Prefixes this adapter takes off the title itself. Kesäkino because it becomes `aud`;
# the rest stay for strands.apply in run.py.
SELF_PREFIX = ("kesäkino", "kesakino")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s))).strip()


def _biggest(srcset):
    best, bw = "", -1
    for part in srcset.split(","):
        bits = part.strip().split()
        if len(bits) == 2 and bits[1].endswith("w"):
            try:
                w = int(bits[1][:-1])
            except ValueError:
                continue
            if w > bw:
                best, bw = bits[0], w
    return best


def _poster(block):
    m = IMG_RE.search(block)
    if not m:
        return ""
    tag = m.group(0)
    ss = SRCSET_RE.search(tag)
    if ss:
        big = _biggest(ss.group(1))
        if big:
            return big
    src = SRC_RE.search(tag)
    url = src.group(1) if src else ""
    # Elementor ships a transparent placeholder in `src` when it lazy-loads.
    return "" if url.startswith("data:") else url


def _iso(day, month, hh, mm, today=None):
    """The rows carry no year, same as Kino Akseli. Pick the one nearest today."""
    today = today or datetime.datetime.now(FI).date()
    for year in (today.year, today.year + 1, today.year - 1):
        try:
            d = datetime.date(year, month, day)
        except ValueError:
            continue
        if -45 <= (d - today).days <= 320:
            return datetime.datetime(year, month, day, hh, mm, tzinfo=FI).isoformat()
    return ""


def _title(block):
    """Everything in the row that is not the date, the time or the button."""
    return re.sub(r"\s+", " ", NOISE_RE.sub(" ", _txt(block))).strip(" -–·|")


def _strip_outdoor(title):
    low = title.lower()
    for pre in SELF_PREFIX:
        if low.startswith(pre + ":"):
            rest = title[len(pre) + 1:].strip(" -–:")
            if rest:
                return rest
    return title


def parse(page, today=None):
    shows = []
    coming = []
    for m in ANCHOR_RE.finditer(page):
        href, slug, block = m.group(1), m.group(2), m.group(3)
        d = DATE_RE.search(block)
        t = TIME_RE.search(block)
        if not (d and t):
            # The page renders the programme twice. The timed listing gives
            # "Pe 05.09." + "klo 21:30" + "Osta liput" and is what this parser wants.
            # A second listing repeats the same screenings with the weekday written out
            # ("Perjantai 02.10.") and an **empty time span**, so those rows cannot be
            # placed in a time-ordered day list and are skipped.
            #
            # Do not read the timeless rows as premieres: on the first live run 44 of
            # the 46 were films that carry a time in the other listing. Only the dates
            # that appear *nowhere* with a time are worth reporting, and on 2026-08-29
            # that was 11.09. and 02.10. Those two are in the date picker, so their
            # times are presumably fetched when the reader picks the date. Reported
            # rather than chased, because a wrong count here would be worse than a
            # missing one and nothing about it is verifiable from this page alone.
            cd = COMING_RE.search(block)
            if cd:
                coming.append((f"{int(cd.group(2)):02d}-{int(cd.group(1)):02d}",
                               _title(block)[:40]))
            continue
        start = _iso(int(d.group(1)), int(d.group(2)),
                     int(t.group(1)), int(t.group(2)), today)
        if not start:
            continue
        outdoor = slug.lower().startswith(OUTDOOR_SLUG)
        title = _title(block)
        if outdoor:
            title = _strip_outdoor(title)
        if not title:
            continue
        shows.append({
            # Never the raw slug: kesakino-autofiktio and autofiktio are one film.
            "eventId": slug[len(OUTDOOR_SLUG):] if outdoor else slug,
            "title": title,
            "original": "",
            "len": "",
            "rating": "",
            "genres": "",
            "method": "",
            "theatre": VENUE["name"],
            "aud": OUTDOOR_AUD if outdoor else "",
            "start": start,
            "url": BASE + href if href.startswith("/") else href,
            "img": _poster(block),
            "lang": "",
            "soldOut": False,
            "price": "",
            "provider": "engel",
            "venue": VENUE["id"],
        })
    # One anchor can appear twice on a page (a carousel and the day list), so drop
    # exact repeats of the same film at the same minute rather than double-counting.
    seen, out = set(), []
    for s in shows:
        k = (s["eventId"], s["start"], s["aud"])
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    out.sort(key=lambda s: s["start"])
    # Only the dates no timed row covers. Everything else is the second listing
    # repeating a screening this parse already has.
    have = {s["start"][5:10] for s in out}
    orphan = sorted({(md, t) for md, t in coming if md not in have})
    if orphan:
        dates = sorted({md for md, _ in orphan})
        print(f"[engel] {len(dates)} date(s) listed with no time anywhere, skipped: "
              + ", ".join(dates) + " -- "
              + " | ".join(t for _, t in orphan))
    return out


# ---------------------------------------------------------------- film pages
#
# The listing carries title, date, time and poster and nothing else. The film page at
# /elokuva/{slug}/ carries the rating, runtime, genres, languages, original title and
# the cinema's own Finnish synopsis, so one request per showing film fills in almost
# everything the listing drops. 17 films on the first run, paced.
#
# What the film page does **not** have is the showtime table. The rows visible in a
# browser (date with year, auditorium, per-screening price, a real booking link) are
# injected by johku.com/widget.js and appear nowhere in the 81 kB of HTML. Its read
# endpoints answer 403 without the key the widget is issued, and lifting that key is
# out of bounds under "Access and ethics". So price, `aud` and a per-show booking URL
# stay empty here, and the two timeless dates stay missing.

DETAIL_RE = re.compile(r'<label>\s*([^<]+?)\s*</label>\s*'
                       r'(?:<span>(.*?)</span>|<div class=["\']contentratings["\']>(.*?)</div>)',
                       re.S | re.I)
GENRE_RE = re.compile(r'class=["\']cmd-desription[^"\']*["\'][^>]*>.*?<h5[^>]*>(.*?)</h5>', re.S | re.I)
SYN_RE = re.compile(r'class=["\']cmd-desription[^"\']*["\'][^>]*>.*?</h5>\s*<p>(.*?)</p>\s*</div>', re.S | re.I)
RATING_CLASS_RE = re.compile(r'class=["\']rating\s+([^"\']+)["\']', re.I)
KESTO_RE = re.compile(r'(?:(\d+)\s*h)?\s*(\d+)\s*min', re.I)

# Finnish language names as this site writes them -> the tag set the client's LN map
# keys on. Swedish is SV, the ISO 639-1 language code, not SE, which is Sweden.
LANGS = {"suomi": "FI", "ruotsi": "SV", "englanti": "EN", "saksa": "DE", "ranska": "FR",
         "espanja": "ES", "italia": "IT", "venäjä": "RU", "viro": "ET", "tanska": "DA",
         "norja": "NO", "islanti": "IS", "japani": "JA", "kiina": "ZH", "korea": "KO"}


def _langs(spoken, subs):
    """"puhuttu kieli: englanti" + "Suomi-Ruotsi" -> "EN-A, FI-S, SE-S"."""
    out = []
    for name in re.split(r"[,/;-]| ja ", (spoken or "").split(":")[-1]):
        code = LANGS.get(name.strip().lower())
        if code and f"{code}-A" not in out:
            out.append(f"{code}-A")
    for name in re.split(r"[,/;-]| ja ", subs or ""):
        code = LANGS.get(name.strip().lower())
        if code and f"{code}-S" not in out:
            out.append(f"{code}-S")
    return ", ".join(out)


def details(page):
    """Film-page metadata. Returns {} for anything the page does not carry."""
    d = {}
    fields = {}
    for m in DETAIL_RE.finditer(page):
        label = _txt(m.group(1)).upper()
        if m.group(3) is not None:
            # IKÄRAJA. **The value is in the class, not in the text**: the markup is
            # <span class="rating K-12"><span>Ikäraja ei vielä tiedossa</span></span>,
            # so reading the text gives every film the same placeholder. The sibling
            # spans (seksi, paihteet, vakivalta, kauhu) are KAVI content descriptors,
            # which this app does not render, so only a K-nn or S token is kept.
            for cls in RATING_CLASS_RE.findall(m.group(3)):
                tok = cls.strip().split()[0]
                if re.fullmatch(r"K-\d+|S", tok):
                    d["rating"] = tok
                    break
        else:
            fields[label] = _txt(m.group(2) or "")

    if fields.get("ALKUPERÄINEN NIMI"):
        d["original"] = fields["ALKUPERÄINEN NIMI"]
    kesto = KESTO_RE.search(fields.get("KESTO", ""))
    if kesto:
        d["len"] = str(int(kesto.group(1) or 0) * 60 + int(kesto.group(2)))
    lang = _langs(fields.get("LISÄTIEDOT", "") or fields.get("KIELI", ""),
                  fields.get("TEKSTITYS", ""))
    if lang:
        d["lang"] = lang
    g = GENRE_RE.search(page)
    if g:
        # Published in caps ("KOMEDIA,DRAAMA"). Only a fallback for films TMDB misses,
        # since genres are rendered from `gids`, but a shouting fallback is still worse
        # than a readable one.
        names = [n.strip().capitalize() for n in _txt(g.group(1)).split(",") if n.strip()]
        if names:
            d["genres"] = ", ".join(names)
    syn = SYN_RE.search(page)
    if syn:
        text = _txt(syn.group(1))
        if len(text) > 40:
            # `_syn` is stripped by run.py after synmerge folds it into
            # films-extra.json; a synopsis repeated across every showtime would add
            # tens of kB to the venue file.
            d["_syn"] = text
    return d


def enrich(shows, get=None):
    """One film page per distinct film, folded onto its showtimes."""
    get = get or (lambda u: fetch(u, headers={"user-agent": UA,
                                              "accept-language": "fi-FI,fi;q=0.9"},
                                  tries=2, backoff=3, timeout=20
                                  ).decode("utf-8", "replace"))
    by_url = {}
    for s in shows:
        by_url.setdefault(s["url"], []).append(s)
    ok = fail = 0
    for n, (url, rows) in enumerate(capped(sorted(by_url.items()), 'engel')):
        if n:
            time.sleep(0.5)
        try:
            d = details(get(url))
        except Exception as e:
            fail += 1
            print(f"[engel] detail {url.rsplit('/', 2)[-2]}: {type(e).__name__}: {e}")
            continue
        if not d:
            fail += 1
            print(f"[engel] detail {url.rsplit('/', 2)[-2]}: nothing parsed")
            continue
        ok += 1
        for s in rows:
            for k, v in d.items():
                if v and not s.get(k):
                    s[k] = v
    print(f"[engel] film pages: {ok} parsed, {fail} with nothing usable, "
          f"{sum(1 for s in shows if s.get('rating'))}/{len(shows)} showtimes rated")
    return shows


def fetch_page():
    page = fetch(URL, headers={"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"},
                 timeout=30).decode("utf-8", "replace")
    if len(page) < 20000 or "sgcaptcha" in page:
        raise RuntimeError("challenged (needs a residential IP)")
    return enrich(parse(page))


def fetch_site(site=SITES[0]):
    """Runner contract: one page, one venue."""
    return {VENUE["id"]: fetch_page()}


# Next pass, deliberately not in this one: wp/v2/elokuva?slug[]=... with
# _embed=wp:featuredmedia gives the cinema's own Finnish synopsis (`content.rendered`,
# which synmerge prefers over TMDB) and a full-size poster, for the ~40 films actually
# showing rather than all 899. One request, keyed by the slugs this parse already has.

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = parse(open(src, encoding="utf-8", errors="replace").read()) if src else fetch_page()
    films = {s["eventId"] for s in data}
    outdoor = [s for s in data if s["aud"] == OUTDOOR_AUD]
    dates = sorted({s["start"][:10] for s in data})
    print(f"{len(data)} showtimes, {len(films)} films, {len(dates)} dates "
          f"({dates[0] if dates else '-'} .. {dates[-1] if dates else '-'}), "
          f"{len(outdoor)} KesäKino, {sum(1 for s in data if s['img'])} with a poster")
    for s in data:
        print(f"  {s['start'][:16]}  {s['title'][:38]:40} {s['aud']:9} {s['eventId'][:28]}")
