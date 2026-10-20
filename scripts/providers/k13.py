"""Kino K13, the Finnish Film Foundation's screen on Katajanokka, Helsinki. Stdlib only.

The listing is the cinema's own page:

    /kinok13/

The only other request is the organiser page a Kinokka evening links to, on the host the
site names in `reads`.

The programme is server-rendered inside `<section id=ohjelmisto>`, under the heading
"Avoimet yleisonaytokset", as free prose rather than a list. Checked for a structured
source first and there is none: `ses.fi` is WordPress but publishes no screening route,
and the section's paragraphs are where the programme lives.

What shapes the parser, measured on the live page 2026-09-21:

- **A line carrying a weekday, a date and a clock is a row.**
  `ma 5.10. klo 18: LUVATTU MAA (Ziemia obiecana) 1974, 179 min.` is a screening.
- **A Kinokka evening gives a date and a title and no clock**, `25.10.2026 Kinokka: Joyland`.
  The organiser page it links, `kaupunginosat.fi/skatta/ohjelmisto/`, lists its upcoming
  dates and states `Esitykset alkavat 16:00.` (read 2026-10-20). The evening is published
  at that clock only when that page lists its date, names no other film for it and states
  one start time. Otherwise it is counted in the log and left out.
- **A festival heading is not a screening.** `5.-9.10.2026 Puolan elokuvaviikot` and
  `6.-8.11.2026 Serbian elokuvapaivat` are date ranges introducing a block. They are read
  as block boundaries, never as rows.
- **Free admission is a property of the block, not of the page.** "Naytoksiin on vapaa
  paasy." sits under a festival heading and applies to the rows beneath it until the next
  heading. `price` is "Vapaa paasy" for those and empty elsewhere, which is what the page
  settles and no more.
- **A timed row prints no year.** `common.resolve_year` places each row from its weekday.
  The heading above prints one, and it is deliberately not read: the weekday is the
  stronger check and it is on the row itself. A Kinokka evening prints its own year.
- **The trailing sentence is the rating.** `Sallittu yli 16-vuotiaille.` is K-16 and
  `Sallittu kaikenikaisille` is S. A row without one leaves `rating` empty, as
  `STUDIO MUNKA, 3 lyhytelokuvaa.` does. A Kinokka evening states it on the lines below.
- **A Kinokka evening's director line gives the film's year**, `Ohjaaja: Saim Sadiq, 2022,
  Pakistan.`, published as `year`. Without it the TMDB search picks a 1929 short of that
  name for Joyland, measured 2026-10-20.
- **A parenthesised title is the original**, `(Ziemia obiecana)`, and the runtime is
  `179 min`. Neither is invented when the row omits it.
- **The showtime links to the cinema's own page.** No screening has a ticket page, and
  `url` is the programme section itself.

**Zero rows fails the site.** The page publishes no sentence saying there is no programme,
so a zero-row parse is a broken read rather than evidence of an empty one, and
`common.EmptyProgramme` needs that evidence.

**`book="list"`.** There is no per-screening booking URL and nothing is sold online: a
showtime opens the programme, which is the mode Gilda already uses.
"""
import datetime
import html as html_mod
import re
import sys
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from common import budget_or_raise, check_shows, get_text, resolve_year, weekday_index

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "k13", "label": "Kino K13",
     "base": "https://www.ses.fi",
     "listing": "/kinok13/",
     "anchor": "#ohjelmisto",
     "reads": ("kaupunginosat.fi",),
     "venues": [{"id": "k13-helsinki", "name": "Kino K13", "short": "Kino K13",
                 "city": "Helsinki"}]},
]

# `resolve_year`'s (behind, ahead). The live section reached 83 days out, a December
# Kinokka evening, so this is headroom rather than a fit.
WINDOW = (30, 180)

SECTION_RE = re.compile(r'<section[^>]*\bid=["\']?ohjelmisto\b["\']?[^>]*>(.*?)</section>',
                        re.S | re.I)
TAGS_RE = re.compile(r"<[^>]+>")
# `ma 5.10. klo 18:` and `to 8.10 klo 18:`, with the minutes optional.
ROW_RE = re.compile(r"^(ma|ti|ke|to|pe|la|su)\s+(\d{1,2})\.(\d{1,2})\.?\s*klo\s*"
                    r"(\d{1,2})(?:[.:](\d{2}))?\s*[:\-–]\s*(.+)$", re.I)
# A block heading: one date or a range, always with a year. The range form opens a
# festival. A single date with no clock is a Kinokka evening.
HEAD_RE = re.compile(r"^\d{1,2}\.(?:\s*[–-]\s*\d{1,2}\.)?\d{1,2}\.\d{4}\b")
FREE_RE = re.compile(r"vapaa\s+p[aä]{1,2}sy", re.I)
RATING_RE = re.compile(r"sallittu\s+(?:yli\s+(\d{1,2})[\s-]*vuotiaille|kaikenik[aä]isille)",
                       re.I)
LEN_RE = re.compile(r"\b(\d{1,3})\s*min\b", re.I)
ORIGINAL_RE = re.compile(r"\(([^()]{2,60})\)")
# Where a visitor sees a new line. Other tags are dropped, which keeps a title in `<i>` on
# its date's line.
BREAK_RE = re.compile(r"<(?:br|/?(?:p|div|h[1-6]|li|ul|ol|section|blockquote))\b[^>]*>",
                      re.I)
HREF_RE = re.compile(r"""<a\b[^>]*?\bhref=["']([^"']+)["']""", re.I)
DATED_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})\b\s*(?:Kinokka\s*:\s*)?(.*)$", re.I)
# The organiser page: `Tuleva ohjelmisto`, a year line, then `25.10 Joyland, ohjaaja: ...`.
UPCOMING_RE = re.compile(r"<h([1-6])\b[^>]*>\s*Tuleva ohjelmisto\s*</h\1>", re.I)
YEAR_RE = re.compile(r"^((?:19|20)\d{2})$")
LISTED_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.?(?:\s+(.*))?$")
STARTS_RE = re.compile(r"\b(?:esitykset|näytökset)\s+alkavat\s+(?:klo\s*)?"
                       r"(\d{1,2})[.:](\d{2})\b", re.I)
DIRECTED_RE = re.compile(r"^Ohjaaja\b.*?\b((?:19|20)\d{2})\b", re.I)


def paragraphs(markup):
    """Markup -> its visible lines in order, each as (text, [href, ...])."""
    out = []
    for chunk in BREAK_RE.split(markup):
        text = re.sub(r"\s+", " ", html_mod.unescape(TAGS_RE.sub("", chunk))).strip()
        if text:
            out.append((text, [html_mod.unescape(h) for h in HREF_RE.findall(chunk)]))
    return out


def lines_of(page):
    """The programme section -> its visible lines, as `paragraphs` gives them."""
    m = SECTION_RE.search(page)
    return paragraphs(m.group(1)) if m else []


def rating_of(rest):
    """`Sallittu yli 16-vuotiaille.` -> "K-16", `kaikenikaisille` -> "S", else ""."""
    m = RATING_RE.search(rest or "")
    if not m:
        return ""
    return f"K-{int(m.group(1))}" if m.group(1) else "S"


def title_of(rest):
    """The text after the clock -> (title, original).

    The title runs to the first bracket, comma or release year, which is where this page
    stops naming the film and starts describing it.
    """
    body = (rest or "").strip()
    cut = len(body)
    for pat in (r"\s*\(", r"\s*,", r"\s+(?:19|20)\d{2}\b"):
        m = re.search(pat, body)
        if m:
            cut = min(cut, m.start())
    title = body[:cut].strip(" .:-–")
    o = ORIGINAL_RE.search(body)
    original = o.group(1).strip() if o else ""
    if original.lower().startswith("sallittu") or LEN_RE.fullmatch(original or ""):
        original = ""
    return title, original


def slug_of(title):
    return re.sub(r"-{2,}", "-", re.sub(r"[^\w]+", "-", (title or "").lower(),
                                        flags=re.UNICODE)).strip("-")


def scan(page):
    """The section -> (timed, entries, report).

    `timed` holds each screening line's match with its block's free admission. `entries`
    holds each dated heading with no clock, with the lines and links of its block.
    """
    timed, entries = [], []
    report = {"lines": 0, "headings": 0, "no_time": 0, "unlisted": 0, "linked": 0,
              "undated": 0, "untitled": 0}
    free, entry = False, None
    for line, hrefs in lines_of(page):
        report["lines"] += 1
        if HEAD_RE.match(line):
            report["headings"] += 1
            free = bool(FREE_RE.search(line))
            entry = None
            if not ROW_RE.match(line):
                d = DATED_RE.match(line)
                if d and "klo" not in line.lower():
                    entry = {"date": d.group(1, 2, 3), "title": d.group(4).strip(" .:-–"),
                             "body": [], "hrefs": list(hrefs), "free": free}
                    entries.append(entry)
                continue
        if FREE_RE.search(line):
            free = True
        m = ROW_RE.match(line)
        if m:
            entry = None
            timed.append((m, free))
        elif entry is not None:
            entry["body"].append(line)
            entry["hrefs"].extend(hrefs)
            entry["free"] = free
    return timed, entries, report


def follow(site, page):
    """The pages that can give this page's Kinokka evenings a start time. -> [url].

    Only an entry's own link to a host the site declares in `reads` is followed.
    """
    hosts = {urlsplit(h if "//" in h else "//" + h).hostname for h in site.get("reads") or ()}
    out = []
    for e in scan(page)[1]:
        for href in e["hrefs"]:
            if urlsplit(href).hostname in hosts and href not in out:
                out.append(href)
    return out


def programme_of(page):
    """The organiser's upcoming block -> (clock, {date: the rest of its line}).

    `clock` is (hour, minute) when the block states one start time, else None.
    """
    m = UPCOMING_RE.search(page)
    if not m:
        return None, {}
    end = re.compile(rf"<h[1-{m.group(1)}]\b", re.I).search(page, m.end())
    year, listed, clocks = None, {}, set()
    for line, _ in paragraphs(page[m.end():end.start() if end else len(page)]):
        clocks.update((int(h), int(mi)) for h, mi in STARTS_RE.findall(line))
        if YEAR_RE.match(line):
            year = int(line)
            continue
        d = LISTED_RE.match(line)
        if d and year:
            try:
                date = datetime.date(year, int(d.group(2)), int(d.group(1)))
            except ValueError:
                continue
            listed[date] = d.group(3) or ""
    return (next(iter(clocks)) if len(clocks) == 1 else None), listed


def words(text):
    return " ".join(re.findall(r"\w+", (text or "").casefold()))


def settle(entry, programmes):
    """A Kinokka evening -> (start, "") from the first linked page that lists it and states
    one start time, else (None, the report key naming why not)."""
    if not entry["title"]:
        return None, "untitled"
    day, month, year = (int(x) for x in entry["date"])
    try:
        date = datetime.date(year, month, day)
    except ValueError:
        return None, "undated"
    why = "no_time"
    for href in entry["hrefs"]:
        clock, listed = programmes.get(href, (None, {}))
        if clock is None:
            continue
        named, title = words(listed.get(date)), words(entry["title"])
        if date not in listed or (named and named != title and
                                  not named.startswith(title + " ")):
            why = "unlisted"
            continue
        return datetime.datetime(year, month, day, *clock, tzinfo=FI), ""
    return None, why


def rows(site, page, today=None, linked=None):
    """-> (shows, report). One row per timed screening line, and one per Kinokka evening a
    linked page settles. `linked` maps a URL the section carries to that page's markup."""
    today = today or datetime.datetime.now(FI).date()
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"] + site["anchor"]
    timed, entries, report = scan(page)
    out = []

    def show(title, original, length, rating, start, free):
        return {
            "eventId": slug_of(title),
            "title": title,
            "original": original,
            "len": length,
            "rating": rating,
            "genres": "",
            "method": "",
            "theatre": venue["name"],
            "aud": "",
            "start": start.isoformat(),
            "url": url,
            "img": "",
            "lang": "",
            "soldOut": False,
            "price": "Vapaa pääsy" if free else "",
            "provider": site["provider"],
            "venue": venue["id"],
        }

    for m, free in timed:
        day, month = int(m.group(2)), int(m.group(3))
        year = resolve_year(day, month, today, weekday_index(m.group(1)), WINDOW)
        if year is None:
            report["undated"] += 1
            continue
        title, original = title_of(m.group(6))
        if not title:
            report["untitled"] += 1
            continue
        rest = m.group(6)
        length = LEN_RE.search(rest)
        out.append(show(title, original, length.group(1) if length else "", rating_of(rest),
                        datetime.datetime(year, month, day, int(m.group(4)),
                                          int(m.group(5) or 0), tzinfo=FI), free))
    programmes = {u: programme_of(p) for u, p in (linked or {}).items()}
    for e in entries:
        start, why = settle(e, programmes)
        if start is None:
            report[why] += 1
            continue
        report["linked"] += 1
        row = show(e["title"], "", "", rating_of(" ".join(e["body"])), start, e["free"])
        made = next((d.group(1) for d in map(DIRECTED_RE.match, e["body"]) if d), "")
        if made:
            row["year"] = made
        out.append(row)
    out.sort(key=lambda s: (s["start"], s["title"]))
    return out, report


def fetch_site(site, today=None, sleep=1.2):
    """Runner contract: the programme page, then each page its Kinokka evenings link."""
    pid, venue = site["provider"], site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    page = get_text(url)
    linked = {}
    for n, link in enumerate(budget_or_raise(follow(site, page), pid)):
        if n:
            time.sleep(sleep)
        try:
            linked[link] = get_text(link)
        except Exception as e:
            raise RuntimeError(f"{link}: {e}. The previous files stand, because this page "
                               f"states the start time of the Kinokka evenings that link "
                               f"it") from e
    shows, report = rows(site, page, today, linked)
    if not shows:
        raise RuntimeError(
            f"{url}: no screening line with a weekday, a date and a clock, and no dated "
            f"entry that a linked page settles. This site publishes no sentence saying "
            f"there are none, and a parse with no rows is no evidence of an empty "
            f"programme. The previous files stand")
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {report['headings']} block heading(s)")
    for link, body in linked.items():
        clock, listed = programme_of(body)
        stated = (f"start time {clock[0]:02d}:{clock[1]:02d}" if clock
                  else "no single start time")
        print(f"[{pid}] {link}: {stated}, {len(listed)} upcoming date(s)")
    for key, note in (("linked", "dated entry(ies) given a start time by the page they link"),
                      ("no_time", "dated entry(ies) with no clock and no linked page stating "
                                  "one, which this parser will not invent"),
                      ("unlisted", "dated entry(ies) whose linked page does not list that "
                                   "date for that film, left out"),
                      ("undated", "line(s) whose date no candidate year holds, left out"),
                      ("untitled", "line(s) with a date and no title, left out")):
        if report[key]:
            print(f"[{pid}] {report[key]} {note}")
    return per_venue


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        with open(src, encoding="utf-8", errors="replace") as fh:
            shows, report = rows(SITES[0], fh.read())
        print(report)
    else:
        shows = fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]
    for s in shows:
        print(f"   {s['start'][:16]}  {s['title'][:30]:32} {s['rating']:5} {s['len']:4} "
              f"{s['price']:12} {s['original'][:20]}")
    sys.exit(0)
