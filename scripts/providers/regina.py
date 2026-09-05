"""Kino Regina (Keskustakirjasto Oodi, Helsinki), KAVI's cinema. Stdlib only.

kinoregina.fi is a WordPress site with its own theme, `kinoregina2`, and every showtime
list on it is drawn by the theme's own PHP endpoints. The one the programme page calls,
`getShowtimesMoviesV2.php`, takes a start date in a POST body and returns the whole
published window from that date as server-rendered HTML: a day header, then one block per
screening with the time, the film's title and numeric id, an ISO-like start with the year
("05-09-2026 14:00") and a per-show ticket link into KAVI's shop. A start date in the past
is clamped to today, and a date past the window returns an empty shell. One request per
run covers the programme (5.9. to 17.9. on the day this was written).

Read from a GitHub runner on 2026-09-05 with a throwaway workflow: the listing GET, this
POST and a film page all answered 200 with no challenge header, so the site runs on the
cloud half from the first day, not provisionally.

What shapes the parser:

- **The film id is the key.** Every row links `/elokuva/{id}`, the same id the film page
  and the listing use, so `eventId` is that number and no title arithmetic is needed. The
  site writes titles in capitals ("PIUKAT PAIKAT"); they are published as written, because
  the title is the key the synopsis cache and the cross-chain merge normalise, and the
  merge lowercases anyway.
- **"Myynti on päättynyt." is not sold out.** A row turns `grey` with that note once online
  sales close for the screening; the seats may be free at the door, so `soldOut` stays
  false and the row stays a showtime.
- **The film page carries the rest**: the age limit as an image whose alt reads "Ikäraja:
  K12", the runtime ("162 min"), the subtitle line ("suom. tekstit/svensk text", "English
  subtitles", "ei tekstitystä"), the cinema's series under Teemat, the print under
  Kopiotieto ("35 mm", "70 mm", "DCP") and the synopsis under Kuvaus. Teemat becomes a
  strand tag only when it is a concise named series; Kopiotieto only when it names a film
  gauge; Lisätieto is screening-specific and never part of the synopsis.
- **No images from the site.** The stills are 16:9, the film page's `og:image` too, so
  posters come from TMDB.

An empty first window is asked for once more and then fails the venue, keeping the
previous file. It is never read as a confirmed empty programme. The first version took
the listing page's `shows-coming` count as the evidence and published an empty venue on
2026-09-05 at 16:57 UTC, when a runner got a window with no screenings *and* a listing
with no `shows-coming` while the same two requests from an ordinary connection returned
21 rows and 17 marked films. The site runs on SiteGround (`sg-f-cache` in its headers),
whose reputation challenge answers a datacenter address with a small HTTP 202 shell that
`fetch` accepts as success; that is what emptied Kino Engel from runners, and it is the
only reading of two contentless answers in one minute. A page that is not the page has no
`shows-coming` either, so absence of a class is not evidence of anything. A challenge
shell is now recognised and named in the log; an empty answer is retried once and then
fails; and whether this venue must move to the local half is decided by the run logs.
"""
import datetime
import html as html_mod
import re
import sys
import time
from zoneinfo import ZoneInfo

from common import capped, fetch

BASE = "https://kinoregina.fi"
SCHEDULE = BASE + "/wp-content/themes/kinoregina2/assets/functions/getShowtimesMoviesV2.php"
LISTING = BASE + "/ohjelmisto/elokuvat/"
FI = ZoneInfo("Europe/Helsinki")
UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"
HEADERS = {"user-agent": UA, "accept-language": "fi-FI,fi;q=0.9"}

VENUE = {"id": "regina-helsinki", "provider": "regina", "providerId": "1",
         "name": "Kino Regina", "short": "Kino Regina", "city": "Helsinki"}

SITES = [{"provider": "regina", "label": "Kino Regina", "base": BASE, "venues": [VENUE]}]

# No EMPTY_VENUES_CONFIRMED here, on purpose: see the module docstring.

BLOCK_RE = re.compile(r'<div class="movie pr col-12 ([a-z]*)">(.*?)(?=<div class="movie pr col-12 |$)', re.S)
FILM_RE = re.compile(r'<a href="(?:https?://kinoregina\.fi)?/elokuva/(\d+)/?"[^>]*class="title[^"]*"[^>]*>(.*?)</a>', re.S | re.I)
START_RE = re.compile(r'class="start">\s*(\d{2})-(\d{2})-(\d{4})\s+(\d{1,2}):(\d{2})\s*<', re.I)
TICKET_RE = re.compile(r'href="(https://kauppa\.kavi\.fi/[^"]+)"', re.I)
TAGS_RE = re.compile(r"<[^>]+>")

# Film page: the detail grid, the age-limit image, the synopsis section.
GRID_RE = re.compile(r'<div class="col-4 col-md-2"><b><span>(.*?)</span></b></div>\s*'
                     r'<div class="col-8 col-md-4">(.*?)</div>', re.S | re.I)
AGE_RE = re.compile(r'alt="Ikäraja:\s*(K\s*-?\s*\d+|S|T)"', re.I)
KESTO_RE = re.compile(r"(\d+)\s*min", re.I)
KUVAUS_RE = re.compile(r'<a name="kuvaus"></a>.*?<div class="col-12 single-movie-main-content-area">(.*?)</div>',
                       re.S | re.I)
PARA_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
GAUGE_RE = re.compile(r"\b(8|16|35|70)\s*mm\b", re.I)

# A Teemat value is a strand tag when it is a concise named series: short, no subtitle
# after a colon, and not the cinema's generic scheduling words. "PAUL THOMAS ANDERSON"
# and "KESÄJAZZIT" qualify; "JATKOAIKA KESÄ 2026" and "KURITTOMAT SUKUPOLVET: NUORISOA
# SUOMALAISESSA ELOKUVASSA" do not.
SERIES_MAX_LEN = 26
SERIES_MAX_WORDS = 4
GENERIC_SERIES = ("jatkoaika", "ohjelmisto", "elokuvat", "uutuudet", "teemat",
                  "kesä", "syksy", "talvi", "kevät")


def _txt(s):
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub(" ", s or ""))).strip()


def _para(s):
    """Paragraph text with inline markup removed without leaving a gap."""
    s = re.sub(r"<br\s*/?>", " ", s or "", flags=re.I)
    return re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub("", s))).strip()


def parse_schedule(page):
    """The POST response -> [show]. Rows without a film link (events) are skipped."""
    shows, seen = [], set()
    for m in BLOCK_RE.finditer(page):
        block = m.group(2)
        f = FILM_RE.search(block)
        s = START_RE.search(block)
        if not (f and s):
            continue
        fid, title = f.group(1), _txt(f.group(2))
        if not title:
            continue
        day, month, year, hh, mm = (int(x) for x in s.groups())
        try:
            start = datetime.datetime(year, month, day, hh, mm, tzinfo=FI).isoformat()
        except ValueError:
            continue
        if (fid, start) in seen:
            continue
        seen.add((fid, start))
        t = TICKET_RE.search(block)
        shows.append({
            "eventId": fid,
            "title": title,
            "original": "",
            "len": "",
            "rating": "",
            "genres": "",
            "method": "",
            "theatre": VENUE["name"],
            "aud": "",
            "start": start,
            # The show's own KAVI ticket page; the film page when a row carries none.
            "url": t.group(1) if t else f"{BASE}/elokuva/{fid}/",
            "img": "",
            "lang": "",
            "soldOut": False,
            "price": "",
            "provider": "regina",
            "venue": VENUE["id"],
        })
    shows.sort(key=lambda s: s["start"])
    return shows


# ---------------------------------------------------------------- film pages

def _subs(text):
    """"suom. tekstit/svensk text" -> ["FI-S", "SV-S"]; "ei tekstitystä" -> []."""
    low = (text or "").lower()
    out = []
    for key, code in (("suom", "FI"), ("svensk", "SV"), ("ruots", "SV"), ("engl", "EN")):
        if key in low and f"{code}-S" not in out:
            out.append(f"{code}-S")
    return out


def series_tag(value):
    """A Teemat value as a strand tag, or "" when it is generic or not concise."""
    v = _txt(value)
    if not v or ":" in v or len(v) > SERIES_MAX_LEN or len(v.split()) > SERIES_MAX_WORDS:
        return ""
    if v.lower().split()[0] in GENERIC_SERIES:
        return ""
    return v


def gauge_tag(value):
    """"35 mm" -> "35 mm"; "DCP" and any prose -> ""."""
    m = GAUGE_RE.search(_txt(value))
    return f"{m.group(1)} mm" if m else ""


def details(page):
    """Film-page metadata. Returns {} for anything the page does not carry."""
    d = {}
    grid = {}
    for label, cell in GRID_RE.findall(page):
        grid[_txt(label).lower()] = cell
    m = AGE_RE.search(page)
    if m:
        tok = re.sub(r"\s|-", "", m.group(1).upper())
        d["rating"] = "S" if tok in ("S", "T") else f"K-{tok[1:]}"
    kesto = KESTO_RE.search(_txt(grid.get("kesto", "")))
    if kesto:
        d["len"] = kesto.group(1)
    subs = _subs(_txt(grid.get("tekstitys", "")))
    if subs:
        d["lang"] = ", ".join(subs)
    tags = []
    for a in re.findall(r"<a\b[^>]*>(.*?)</a>", grid.get("teemat", ""), re.S | re.I):
        tag = series_tag(a)
        if tag and tag not in tags:
            tags.append(tag)
    gauge = gauge_tag(grid.get("kopiotieto", ""))
    if gauge:
        tags.append(gauge)
    if tags:
        d["method"] = " · ".join(tags)
    k = KUVAUS_RE.search(page)
    if k:
        # Only Kuvaus, never Lisätieto: the lead paragraphs up to the "***" rule that
        # separates the synopsis from the programme essay below it.
        paras = []
        for p in PARA_RE.findall(k.group(1)):
            text = _para(p)
            if re.fullmatch(r"\*{2,}", text):
                break
            if text:
                paras.append(text)
        text = " ".join(paras)
        if len(text) > 40:
            d["_syn"] = text
    return d


def enrich(shows, get=None):
    """One film page per film, folded onto every showtime of it."""
    get = get or (lambda u: fetch(u, cache=True, headers=HEADERS, tries=2, backoff=3,
                                  timeout=20).decode("utf-8", "replace"))
    by_film = {}
    for s in shows:
        by_film.setdefault(s["eventId"], []).append(s)
    ok = fail = 0
    for n, (fid, rows) in enumerate(capped(sorted(by_film.items()), "regina")):
        if n:
            time.sleep(0.5)
        url = f"{BASE}/elokuva/{fid}/"
        try:
            d = details(get(url))
        except Exception as e:
            fail += 1
            print(f"[regina] film page {fid} failed: {type(e).__name__}: {e}")
            continue
        if not d:
            fail += 1
            print(f"[regina] film page {fid}: nothing parsed")
            continue
        ok += 1
        for s in rows:
            for key, val in d.items():
                if val and not s.get(key):
                    s[key] = val
    print(f"[regina] film pages: {ok} parsed, {fail} with nothing usable, "
          f"{sum(1 for s in shows if s.get('rating'))}/{len(shows)} showtimes rated")
    return shows


def get_schedule(day):
    """One window of the schedule, from `day` (YYYY-MM-DD) onwards."""
    body = f"getShowtimesMovies={day}".encode("ascii")
    return fetch(SCHEDULE, data=body, cache=False,
                 headers={**HEADERS, "content-type": "application/x-www-form-urlencoded"},
                 timeout=40).decode("utf-8", "replace")


# Each answer covers about two weeks and ends with the page's "Lataa lisää" button,
# whose onclick names the day the next window starts. Followed until a window has no
# screenings, and no further than MAX_PAGES windows: the programme is published a few
# weeks ahead, so the second call is normally the empty one.
NEXT_RE = re.compile(r"loadNextTwoWeeks\('(\d{4}-\d{2}-\d{2})'")
MAX_PAGES = 4


def challenged(page):
    """SiteGround's captcha answers a refused address with a ~170-byte meta-refresh shell
    that names `sgcaptcha`; an honest empty window is a ~590-byte fragment with the
    load-more button. Either marker is enough on its own."""
    low = (page or "").lower()
    return "sgcaptcha" in low or "sg-captcha" in low or len(low.strip()) < 300


def fetch_schedule(today=None, get=None, sleep=1.0):
    """Every window from today -> [page html]. The first page is always fetched."""
    get = get or get_schedule
    day = (today or datetime.datetime.now(FI).date()).isoformat()
    pages = []
    for n in range(MAX_PAGES):
        if n:
            time.sleep(sleep)
        page = get(day)
        if challenged(page):
            raise RuntimeError(f"challenged: {len(page)} bytes for the window from {day}, "
                               f"the SiteGround shell rather than the schedule (a refused "
                               f"address; see the module docstring)")
        if n == 0 and not parse_schedule(page):
            # One empty first answer proves nothing: a runner got one at 16:57 UTC on
            # 2026-09-05 while the same POST from elsewhere listed 21 rows. Ask once more
            # before the caller fails the venue, and say what the empty answer looked
            # like, in counts, so the next such log can be read.
            print(f"[regina] first window from {day} has no screenings: {len(page)} bytes, "
                  f"{len(re.findall('day-header', page))} day headers, "
                  f"{'with' if NEXT_RE.search(page) else 'without'} the load-more button; "
                  f"asking once more")
            time.sleep(sleep * 3)
            page = get(day)
            if challenged(page):
                raise RuntimeError(f"challenged on the second try: {len(page)} bytes for "
                                   f"the window from {day}")
        pages.append(page)
        if not parse_schedule(page):
            break
        m = NEXT_RE.search(page)
        if not m or m.group(1) <= day:
            break
        day = m.group(1)
    print(f"[regina] schedule: {len(pages)} window(s), the last from {day}")
    return pages


def fetch_site(site=SITES[0]):
    """Runner contract: the schedule windows, one venue. An empty answer, asked twice, is
    a failure and not an empty programme; the previous file stays."""
    shows = parse_schedule("".join(fetch_schedule()))
    if not shows:
        raise RuntimeError("schedule answered twice with no screenings; nothing the site "
                           "publishes can confirm an empty programme, so the previous "
                           "file is kept")
    enrich(shows)
    return {VENUE["id"]: shows}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else ""
    data = (parse_schedule(open(src, encoding="utf-8", errors="replace").read()) if src
            else fetch_site()[VENUE["id"]])
    dates = sorted({s["start"][:10] for s in data})
    print(f"{len(data)} showtimes, {len({s['eventId'] for s in data})} films, {len(dates)} dates "
          f"({dates[0] if dates else '-'} .. {dates[-1] if dates else '-'})")
    for s in data:
        print(f"  {s['start'][:16]}  {s['title'][:34]:36} {s['rating']:5} {s['len']:4} "
              f"{s['lang']:14} {s['method'][:30]:32} {s['eventId']}")
