"""Pajakkakino, Kuhmo. Stdlib only.

The front page is an Instagram feed; the programme is the site's WordPress posts, one per
film, read in one request (issue #10, read 2026-10-21):

    /wp-json/wp/v2/posts?per_page=100&_fields=id,link,title,content

What shapes the parser:

- **A film post has a facts line and an `ESITYKSET:` list.** The facts line is
  "Draama, sota, kotimainen I 2h 35min I 23.10.2026 I AUDIO suomi", the "I" separators in
  `<strong>`. A post with no list, or no runtime before it, is not read: on 2026-10-21 that
  was one event post whose prose held a 15:30 burger slot beside its 18:00 documentary,
  and nothing in its markup tells the two apart. It is counted in the log.
- **A row is a weekday and a date, then "KLO" and one or more clocks**: "LA 24.10. KLO
  15:00", "LA 24.10 KLO 13:00" without the second dot, "TO 29.10. KLO 16:30 & 18:30" for
  two screenings. A date line with nothing after it takes its clocks from the next line,
  "TI 27.10." then "KLO 14:00 & 18:00". No date carries a year, so `common.resolve_year`
  places it on the weekday.
- **Film and non-film stay apart.** Text after the clocks is a note, and a row with one is
  left out unless the note says the film starts: "MA 26.10. KLO 16:30 alkaen lukupiiri" is
  a reading circle and "MA 26.10. KLO 18:00 elokuva alkaa" is the screening.
- **A cancelled row is struck through** (`<del>`) and followed by "PERUTTU!", and is left
  out. So is a row whose clock is not set yet, "SU 1.11 KLO ? ilmoitetaan myöhemmin".
- **The rating** is the `ikaraja_{n|s}` image, or the sentence "kielletty alle N" or
  "sallittu kaikenikäisille" where a post has no image.
- **No poster of the site's own is published** (maintainer, 2026-10-21), so a poster comes
  only from a trusted TMDB match. Tickets are reserved by phone, WhatsApp or a form that is
  never requested, and paid at the cinema, so `book` is door.

Zero rows fails the site: the posts carry no sentence saying there is nothing on.
"""
import datetime
import html as html_mod
import json
import re
import sys
from zoneinfo import ZoneInfo

from common import bot_check, check_shows, get_text, resolve_year, served, weekday_index
from etiketti import strict_codes

FI = ZoneInfo("Europe/Helsinki")

SITES = [
    {"provider": "pajakkakino", "label": "Pajakkakino", "base": "https://www.pajakkakino.fi",
     "listing": "/wp-json/wp/v2/posts?per_page=100&_fields=id,link,title,content",
     "venues": [{"id": "pajakkakino-kuhmo", "name": "Pajakkakino", "short": "Pajakkakino",
                 "city": "Kuhmo"}]},
]

WINDOW = (30, 120)
LIST_RE = re.compile(r"ESITYKSET\s*:", re.I)
INLINE_RE = re.compile(r"</?(?:strong|b|em|i|u|span|a|font)\b[^>]*>", re.I)
TAG_RE = re.compile(r"<[^>]+>")
DEL_RE = re.compile(r"<del\b[^>]*>(.*?)</del>", re.S | re.I)
STRUCK, STRUCK_END = "\x01", "\x02"
RUNTIME_RE = re.compile(r"\b(\d{1,2})\s*h\s*(\d{1,2})\s*min\b", re.I)
DATE_RE = re.compile(r"^(ma|ti|ke|to|pe|la|su)\s+(\d{1,2})\.(\d{1,2})\.?(?:\s+(.*))?$", re.I)
KLO_RE = re.compile(r"^klo\.?\s*", re.I)
CLOCK_RE = re.compile(r"^(\d{1,2})[:.](\d{2})\s*(?:(?:&|ja|,)\s*)?", re.I)
STARTS_RE = re.compile(r"^elokuva alkaa\.?!?$", re.I)
RATING_IMG_RE = re.compile(r"ikaraja_(\d{1,2}|s)\.(?:png|svg|jpe?g)", re.I)
RATING_TEXT_RE = re.compile(r"kielletty alle (\d{1,2})\s*v", re.I)
AUDIO_RE = re.compile(r"\bAUDIO\s+(.+?)(?:\s+TEKSTIT\s+(.+?))?\s*$", re.I)


def lines(fragment):
    """Rendered post HTML -> its text lines, a struck-through part marked as such."""
    s = DEL_RE.sub(lambda m: STRUCK + m.group(1) + STRUCK_END, fragment or "")
    s = INLINE_RE.sub(" ", s)
    s = html_mod.unescape(TAG_RE.sub("\n", s))
    return [re.sub(r"[ \t ​]+", " ", x).strip() for x in s.split("\n") if x.strip()]


def facts_of(head):
    """The facts line before the list -> (minutes, genres, lang)."""
    for line in head:
        m = RUNTIME_RE.search(line)
        if not m:
            continue
        parts = [p.strip() for p in re.split(r"\s+I\s+", line)]
        genres = ", ".join(g.strip().capitalize() for g in parts[0].split(",")
                           if g.strip() and not re.search(r"\d", parts[0]))
        lang = []
        for p in parts:
            a = AUDIO_RE.search(p)
            if a:
                lang += [f"{c}-A" for c in strict_codes(a.group(1))]
                lang += [f"{c}-S" for c in strict_codes(a.group(2) or "")]
        return str(int(m.group(1)) * 60 + int(m.group(2))), genres, ", ".join(lang)
    return "", "", ""


def rating_of(content, text_lines):
    m = RATING_IMG_RE.search(content)
    if m:
        return "S" if m.group(1).lower() == "s" else f"K-{int(m.group(1))}"
    body = " ".join(text_lines)
    t = RATING_TEXT_RE.search(body)
    if t:
        return f"K-{int(t.group(1))}"
    return "S" if re.search(r"sallittu kaikenik", body, re.I) else ""


def clocks(rest):
    """`KLO 16:30 & 18:30 note` -> ([(16, 30), (18, 30)], "note"), or None with no KLO."""
    k = KLO_RE.match(rest)
    if not k:
        return None
    s, out = rest[k.end():], []
    while True:
        c = CLOCK_RE.match(s)
        if not c:
            break
        out.append((int(c.group(1)), int(c.group(2))))
        s = s[c.end():]
    return out, s.strip()


def screenings(after, today, report):
    """The list's lines -> [(date, hour, minute)]. Skipped rows are counted in `report`."""
    out, pending, struck = [], None, False
    for line in after:
        here = struck or STRUCK in line or "PERUTTU" in line.upper()
        struck = (struck or STRUCK in line) and STRUCK_END not in line
        line = line.replace(STRUCK, " ").replace(STRUCK_END, " ").strip()
        d = DATE_RE.match(line)
        if d:
            day, month = int(d.group(2)), int(d.group(3))
            year = resolve_year(day, month, today, weekday_index(d.group(1)), WINDOW)
            pending = None
            if here:
                report["cancelled"] += 1
                continue
            if year is None:
                report["undated"] += 1
                continue
            date = datetime.date(year, month, day)
            if not d.group(4):
                pending = date
                continue
            got = clocks(d.group(4))
        elif pending and KLO_RE.match(line):
            date, got, pending = pending, clocks(line), None
            if here:
                report["cancelled"] += 1
                continue
        else:
            continue
        if not got or not got[0]:
            report["untimed"] += 1
            continue
        times, note = got
        if note and not STARTS_RE.match(note):
            report["noted"] += len(times)
            continue
        out += [(date, h, m) for h, m in times]
    return out


def rows(site, posts, today=None):
    """-> (shows, report). One row per screening of every film post."""
    today = today or datetime.datetime.now(FI).date()
    venue = site["venues"][0]
    out = []
    report = {"posts": 0, "films": 0, "not_film": 0, "cancelled": 0, "untimed": 0,
              "noted": 0, "undated": 0}
    for p in posts:
        report["posts"] += 1
        content = (p.get("content") or {}).get("rendered") or ""
        title = " ".join(lines((p.get("title") or {}).get("rendered") or ""))
        split = LIST_RE.search(content)
        head = lines(content[:split.start()]) if split else []
        minutes, genres, lang = facts_of(head)
        if not split or not minutes or not title:
            report["not_film"] += 1
            continue
        report["films"] += 1
        link = p.get("link") or ""
        slug = link.rstrip("/").rsplit("/", 1)[-1] or str(p.get("id") or "")
        rating = rating_of(content, lines(content))
        for date, h, m in screenings(lines(content[split.end():]), today, report):
            out.append({
                "eventId": slug, "title": title, "original": "", "len": minutes,
                "rating": rating, "genres": genres, "method": "", "theatre": venue["name"],
                "aud": "",
                "start": datetime.datetime(date.year, date.month, date.day, h, m,
                                           tzinfo=FI).isoformat(),
                "url": link, "img": "", "lang": lang, "soldOut": False, "price": "",
                "provider": site["provider"], "venue": venue["id"],
            })
    out.sort(key=lambda s: (s["start"], s["title"]))
    return out, report


def fetch_site(site, today=None):
    """Runner contract: one request for the posts."""
    pid = site["provider"]
    venue = site["venues"][0]
    url = site["base"].rstrip("/") + site["listing"]
    body = get_text(url)
    try:
        posts = json.loads(body)
    except ValueError:
        bot_check(body, url)
        raise RuntimeError(f"{url}: not a JSON list of posts ({served(body)})")
    if not isinstance(posts, list):
        raise RuntimeError(f"{url}: not a JSON list of posts ({served(body)})")
    shows, report = rows(site, posts, today)
    if not shows:
        raise RuntimeError(
            f"{url}: {report['posts']} post(s), {report['films']} with a screening list, "
            f"and no screening read. The posts carry no sentence saying there are none, so "
            f"there is no evidence of an empty programme to read this as and the previous "
            f"files stand")
    per_venue = {venue["id"]: shows}
    check_shows(per_venue, pid, {venue["id"]})
    days = sorted({s["start"][:10] for s in shows})
    print(f"[{pid}] {venue['name']}, {venue['city']}: {len(shows)} showtimes, "
          f"{len(days)} dates, {report['films']} film post(s) of {report['posts']}")
    for key, what in (("not_film", "post(s) with no screening list or no runtime, not read"),
                      ("noted", "row(s) whose note is not the film starting, left out"),
                      ("cancelled", "cancelled row(s), left out"),
                      ("untimed", "row(s) with no clock yet, left out"),
                      ("undated", "row(s) whose date no candidate year holds, left out")):
        if report[key]:
            print(f"[{pid}] {report[key]} {what}")
    return per_venue


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        with open(src, encoding="utf-8") as fh:
            shows, report = rows(SITES[0], json.load(fh))
        print(report)
    else:
        shows = fetch_site(SITES[0])[SITES[0]["venues"][0]["id"]]
    for s in shows:
        print(f"   {s['start'][:16]}  {s['title'][:40]:42} {s['rating']:5} {s['len']:4} "
              f"{s['lang']:12} {s['genres'][:30]}")
    sys.exit(0)
