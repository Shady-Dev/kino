#!/usr/bin/env python3
"""Pre-render one indexable page per venue and per multi-venue city, in fi and en.

Why pre-render at all: the app is a single JS-rendered URL, so the whole site was one
entry in a search index no matter how much markup went in `<head>`. Structured data does
not create pages. These do, from the same committed JSON the app reads, so there is one
source of truth and no second fetcher.

    /teatteri/{slug}/           fi, one venue        /en/theatre/{slug}/
    /kaupunki/{slug}/           fi, a whole city     /en/city/{slug}/
    /sitemap.xml                every page, both languages

City pages exist only where a city has more than one venue, which is the same rule the
app uses for its combined view: five cities today (Espoo, Helsinki, Kotka, Savonlinna,
Tampere). A city page for a one-venue city would be the venue page at a second URL, and
duplicate content at two URLs is worse than one good one. Single-venue cities are covered
by putting the city in the venue page's title, h1 and JSON-LD address instead.

Deliberate constraints:

- **No third-party requests.** Inline CSS, the same self-hosted Archivo the app uses
  (`/fonts/`, one same-origin request), and only same-origin posters (`data/posters/...`)
  are rendered; a poster hot-linked from a cinema CDN is skipped rather than made to leak
  a visitor's IP on a page they arrived at from Google. See the Privacy section of the
  README.
- **No JavaScript that renders content.** The page is what the crawler sees and what the
  visitor sees. The one script is the theme: the app stores its toggle in
  `localStorage["kino-theme"]`, and a landing page that ignored it opened dark beside a
  light app on the same origin. Before first paint the page reads that key exactly as
  the app does and sets `data-theme`; without it the theme follows the OS. The toggle
  button writes the same key, so a choice made on either page carries to the other, and
  it is hidden when the script did not run.
- **The card is the app's card.** Film facts -- rating, runtime, genres, score -- fold
  from the day's screenings by first non-empty value, never from the first screening
  alone. Language sits on the card once when every screening shares it and on
  the individual screening when they differ (`lang_parts` is the app's `langTxt`,
  `price_label` its `priceLabel`, each pinned against the client). The showtime keeps
  time, the cinema on a city page, and the room verbatim. The app's own tag folding for
  format tags (`stubTags`) is not ported.
- **A page is rewritten only when its bytes change.** Four runs a day across ~100 pages
  would otherwise commit megabytes of near-identical HTML forever. Quiet venues change
  once a week.
- **No timestamp in the page body**, for the same reason: `generated` moves every run and
  would defeat the comparison above. Freshness belongs in the app, which the page links.
- **No `aggregateRating` in the markup.** The ratings are TMDB's, and presenting another
  party's ratings as the page's own is against Google's structured-data guidelines. The
  rating is shown as text, credited, and left out of the JSON-LD.
"""
import html
import json
import re
import sys
import unicodedata
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "providers"))

import common                                    # noqa: E402
from synmerge import norm                        # noqa: E402

ROOT = HERE.parent
DATA = ROOT / "data"
FI = ZoneInfo("Europe/Helsinki")
SITE = "https://leffavuoro.fi"
# The route a cinema uses to ask a question or to be taken out. The pipeline's
# User-Agent points every provider at this site, so these pages have to answer too --
# a search result is as likely a first landing as the app itself. Constant, so
# write_if_changed keeps working.
CONTACT = "leffavuoro@gmail.com"

# Posters that reached the page generator still pointing at somebody else's host. Every
# provider's images are supposed to be rewritten into data/posters/ by mirror_posters,
# which runs immediately before this. A non-zero count here means that did not happen for
# some venue, and the reader sees a placeholder tile instead of a poster -- silently,
# because the page renders fine without it.
#
# Live cause, 2026-08-30: the local half publishes Kino Engel and Kino Akseli posters as
# the cinema's own URLs and only the cloud run rewrites them, so a cancelled cloud run
# left two venues with no posters at all until the next cron. The workflow no longer
# cancels; this line is here so the next way it happens is not silent too.
_unmirrored_hosts = {}


def _unmirrored(img):
    if img.startswith("http") or img.startswith("//"):
        host = img.split("/")[2] if "//" in img else img
        _unmirrored_hosts[host] = _unmirrored_hosts.get(host, 0) + 1
    return ""
DAYS = 4          # today plus three: enough to answer "what is on", small enough to commit
CITY_DAYS = 2     # a ten-venue city at seven days was a 1.2 MB page
LD_DAYS = 2       # markup for today and tomorrow only, see ld_json()


# ---------------------------------------------------------------- strings

# Finnish city names inflect irregularly: Helsinki -> Helsingissä, Tampere -> Tampereella,
# Espoo -> Espoossa. Suffixing a case ending onto the nominative produces "Helsinkissä",
# which is exactly the tell that a page was generated by a script. Every string below
# therefore uses the city name in the nominative with a separator, which stays correct for
# any city a future provider brings.
L = {
    "fi": {
        "lang": "fi", "locale": "fi_FI",
        "venue_title": "{venue}, {city} \u2013 elokuvat ja n\u00e4yt\u00f6sajat",
        "city_title": "Elokuvat ja n\u00e4yt\u00f6sajat \u2013 {city}",
        "venue_h1": "{venue} \u2013 n\u00e4yt\u00f6sajat",
        "city_h1": "Elokuvat ja n\u00e4yt\u00f6sajat \u2013 {city}",
        "venue_desc": "{venue} ({city}): elokuvat, n\u00e4yt\u00f6sajat, ik\u00e4rajat ja liput "
                      "l\u00e4hip\u00e4iville.",
        "city_desc": "Kaikki elokuvateatterit ja n\u00e4yt\u00f6sajat \u2013 {city}: {venues}.",
        "venue_sub": "{city} \u00b7 {host}",
        "city_sub": "{n} teatteria",
        # One sentence per booking mode, from the registry's `book` field. The old copy
        # promised a ticket page for every cinema, which was wrong for Kino Akseli (no
        # links at all) and for Nexxo (the programme page, not a ticket).
        "intro_buy": "Katso l\u00e4hip\u00e4ivien n\u00e4yt\u00f6sajat. N\u00e4yt\u00f6sajasta p\u00e4\u00e4set "
                     "lipunmyyntiin sivustolla {host}.",
        "intro_reserve": "Katso l\u00e4hip\u00e4ivien n\u00e4yt\u00f6sajat. N\u00e4yt\u00f6sajasta p\u00e4\u00e4set "
                         "paikkavaraukseen sivustolla {host}.",
        "intro_list": "Katso l\u00e4hip\u00e4ivien n\u00e4yt\u00f6sajat. N\u00e4yt\u00f6sajasta p\u00e4\u00e4set "
                      "teatterin ohjelmistoon sivustolla {host}.",
        "intro_door": "Katso l\u00e4hip\u00e4ivien n\u00e4yt\u00f6sajat. Liput myyd\u00e4\u00e4n ovelta.",
        # Screenings included in a general admission ticket (Heureka): the time opens the
        # ticket shop and reserves no seat.
        "intro_admission": "Katso l\u00e4hip\u00e4ivien n\u00e4yt\u00f6sajat. Esitykset sis\u00e4ltyv\u00e4t "
                           "p\u00e4\u00e4sylippuun, jonka voit ostaa sivustolta {host}.",
        # Appended when every screening on the page shares a screening-level age limit;
        # the pages render no per-stub age chip. See age_note().
        "age_note": "Ik\u00e4raja {n} vuotta.",
        # A city mixes booking modes, so this promises only what every venue has.
        "city_intro": "Katso {n} teatterin n\u00e4yt\u00f6sajat l\u00e4hip\u00e4iville. N\u00e4yt\u00f6sajasta "
                      "p\u00e4\u00e4set teatterin lippu- tai ohjelmistosivulle, kun linkki on "
                      "saatavilla.",
        "cta": "Avaa koko ohjelmisto",
        "today": "T\u00e4n\u00e4\u00e4n", "tomorrow": "Huomenna",
        "days": ["Ma", "Ti", "Ke", "To", "Pe", "La", "Su"],
        "no_shows": "Ei julkaistuja n\u00e4yt\u00f6ksi\u00e4 l\u00e4hip\u00e4iville.",
        "mins": "min", "tmdb": "TMDB",
        "venues_h": "Teatterit \u2013 {city}",
        "city_link": "Kaikki teatterit \u2013 {city}",
        "subs": "tekstitys: {}", "lang_nav": "Kieli",
        "theme": "Vaihda teemaa", "a_theme": "Vaihda vaalean ja tumman teeman v\u00e4lill\u00e4",
        "from": "alkaen", "votes": "\u00e4\u00e4nt\u00e4",
        "sources": "N\u00e4yt\u00f6stiedot: kyseisen teatterin oma ohjelmisto. Arvosanat ja "
                   "kuvaukset: TMDB. Henkil\u00f6kohtainen harrastusprojekti, ei "
                   "sidoksissa teattereihin.",
        "contact": "Elokuvateattereille: yhteydenotot ja poistopyynn\u00f6t",
        "source": "L\u00e4hdekoodi",
    },
    "en": {
        "lang": "en", "locale": "en_GB",
        "venue_title": "{venue}, {city} \u2013 films and showtimes",
        "city_title": "Films and showtimes \u2013 {city}",
        "venue_h1": "{venue} \u2013 showtimes",
        "city_h1": "Films and showtimes \u2013 {city}",
        "venue_desc": "{venue} ({city}): films, times, age limits and tickets for the "
                      "next few days.",
        "city_desc": "Every cinema and showtime in one list \u2013 {city}: {venues}.",
        "venue_sub": "{city} \u00b7 {host}",
        "city_sub": "{n} cinemas",
        "intro_buy": "See showtimes for the next few days. Choose a time to buy tickets "
                     "on {host}.",
        "intro_reserve": "See showtimes for the next few days. Choose a time to reserve "
                         "seats on {host}.",
        "intro_list": "See showtimes for the next few days. Choose a time to open the "
                      "cinema programme on {host}.",
        "intro_door": "See showtimes for the next few days. Tickets are sold at the door.",
        "intro_admission": "See showtimes for the next few days. Screenings are included in "
                           "the admission ticket, sold on {host}.",
        "age_note": "Age limit {n} years.",
        "city_intro": "See showtimes from {n} cinemas for the next few days. Choose a time "
                      "to open the cinema\u2019s ticket or programme page, where available.",
        "cta": "See the full programme",
        "today": "Today", "tomorrow": "Tomorrow",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "no_shows": "No showtimes published for the next few days.",
        "mins": "min", "tmdb": "TMDB",
        "venues_h": "Cinemas \u2013 {city}",
        "city_link": "All cinemas \u2013 {city}",
        "subs": "{} subtitles", "lang_nav": "Language",
        "theme": "Switch theme", "a_theme": "Switch between light and dark theme",
        "from": "from", "votes": "votes",
        "sources": "Showtimes: each cinema's own schedule. Ratings and descriptions: "
                   "TMDB. A personal hobby project, unaffiliated with the cinemas.",
        "contact": "For cinemas: enquiries and removal requests",
        "source": "Source",
    },
}

# The booking verb comes from the registry; a mode this table does not know reads as a
# ticket page, which is what every provider but two actually offers.
def venue_intro(t, book, host):
    return t.get("intro_" + (book or "buy"), t["intro_buy"]).format(host=host)


def age_note(t, shows):
    """One sentence when every screening on the page shares a screening-level age limit.

    `age` is the room's limit, separate from the film's classification: K-18 on some
    Finnkino rows, K-5 on every Heureka row. The app puts it on each stub; these pages
    render no chip, so the venue-wide case is said once in the intro. A mixed page says
    nothing. -> "" when there is nothing to say.
    """
    ages = {(s.get("age") or "").strip() for s in shows}
    if len(ages) != 1:
        return ""
    n = re.sub(r"\D", "", ages.pop())
    return t["age_note"].format(n=n) if n else ""


# The client's language-name tables, copied for fi and en. `tests/test_landing_pages.py`
# reads the client's `LN` out of index.html and asserts these are identical, so the two
# cannot drift apart without a test saying so. Keys are ISO 639-1 codes.
LN = {
    "fi": {"FI": "suomi", "EN": "englanti", "SV": "ruotsi", "ES": "espanja", "DE": "saksa",
           "FR": "ranska", "IT": "italia", "RU": "ven\u00e4j\u00e4", "ET": "viro", "DA": "tanska",
           "NO": "norja", "IS": "islanti", "NL": "hollanti", "PL": "puola", "PT": "portugali",
           "UK": "ukraina", "AR": "arabia", "JA": "japani", "ZH": "kiina", "KO": "korea",
           "HI": "hindi", "TR": "turkki", "KA": "georgia", "TA": "tamili", "LT": "liettua",
           "ML": "malajalam"},
    "en": {"FI": "Finnish", "EN": "English", "SV": "Swedish", "ES": "Spanish", "DE": "German",
           "FR": "French", "IT": "Italian", "RU": "Russian", "ET": "Estonian", "DA": "Danish",
           "NO": "Norwegian", "IS": "Icelandic", "NL": "Dutch", "PL": "Polish",
           "PT": "Portuguese", "UK": "Ukrainian", "AR": "Arabic", "JA": "Japanese",
           "ZH": "Chinese", "KO": "Korean", "HI": "Hindi", "TR": "Turkish", "KA": "Georgian",
           "TA": "Tamil", "LT": "Lithuanian", "ML": "Malayalam"},
}
# Codes the committed data carried on 2026-09-02 that the client's table did not, each a
# defect somewhere else and named here so a page never showed a raw code meanwhile. The
# fixes landed the same day -- fetch_data.lang_tag maps TU and MA, nexxo._lang drops XX,
# LT and ML are in the client's LN and mirrored above -- but the committed data turns over
# only as the adapters run again, Finnkino from an ordinary connection, so these stay
# exactly as they are until a re-measure of data/area-*.json finds no TU, MA or XX:
#   TU, MA -- Finnkino's own vocabulary for Turkish and Malayalam ("Keltaiset kirjeet",
#             "I'm Game"), read as TR and ML here.
#   XX     -- Nexxo's "no subtitles" on dubbed films. Not a language: the subtitle role
#             is simply absent, so it renders nothing.
#   LT, ML -- now in LN above, which is consulted first; kept so the set goes in one step.
# A code in none of these tables still renders, as itself, so a new one is visible on
# the page rather than lost. `tests/test_landing_pages.py` asserts every code in the
# committed data is covered, and `tests/test_lang_normalization.py` pins this set.
CODE_ALIAS = {"TU": "TR", "MA": "ML"}
NO_SUBTITLES = {"XX"}
LN_EXTRA = {"fi": {"LT": "liettua", "ML": "malajalam"},
            "en": {"LT": "Lithuanian", "ML": "Malayalam"}}
LANG_RE = re.compile(r"^([A-Z]{2}(?:-[A-Z]{2})?)-(A|S)$")


def lang_parts(codes, lang):
    """`"EN-A, FI-S, SV-S"` -> `["englanti", "tekstitys suomi/ruotsi"]`, the app's
    `langTxt` rule: -A is the spoken language, -S a subtitle language, a compound
    `FI-SV-A` is two languages, duplicates collapse in source order, an absent role is
    omitted, and a name the tables lack stays visible as its code."""
    by = {"A": [], "S": []}
    for raw in (codes or "").split(","):
        c = raw.strip()
        if not c:
            continue
        m = LANG_RE.match(c)
        if not m:
            by["A"].append(c)          # not a tag this app knows: shown rather than lost
            continue
        for x in m.group(1).split("-"):
            x = CODE_ALIAS.get(x, x)
            if m.group(2) == "S" and x in NO_SUBTITLES:
                continue
            name = LN[lang].get(x) or LN_EXTRA[lang].get(x) or x
            if name not in by[m.group(2)]:
                by[m.group(2)].append(name)
    out = []
    if by["A"]:
        out.append("/".join(by["A"]))
    if by["S"]:
        out.append(L[lang]["subs"].format("/".join(by["S"])))
    return out


PRICE_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def price_label(rows, lang):
    """The app's `priceLabel`, for the same rows. The first number anywhere in the string
    is the price, sign included so "-5\u20ac" stays rejected; a floor is either two different
    amounts or a source that says so itself ("alkaen 10\u20ac"), tested on shape rather than
    on the word because the word is in the provider's language. `tests/test_landing_pages.py`
    runs the client's own harness cases through this and asserts the same answers."""
    floor, vals = False, []
    for r in rows:
        raw = str(r.get("price") or "").replace(",", ".")
        m = PRICE_NUM.search(raw)
        if not m:
            continue
        try:
            v = float(m.group(0))
        except ValueError:
            continue
        if v != v or v <= 0:
            continue
        if re.search(r"[^\d\s.,\u20ac$\u00a3]", raw.replace(m.group(0), "", 1)):
            floor = True
        vals.append(v)
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)

    def fmt(v):
        n = str(int(round(v))) if round(v * 100) % 100 == 0 else f"{v:.2f}"
        # Finnish typography, as in the client: "10,50 €" with a non-breaking space.
        return n.replace(".", ",") + "\u00a0\u20ac" if lang == "fi" else n + "\u20ac"

    return fmt(lo) if (lo == hi and not floor) else f"{L[lang]['from']} {fmt(lo)}"


VOTE_SOLID = 25     # the app's: a rating on fewer votes is dimmed, not hidden


def short_votes(n):
    return (f"{n / 1000:.1f}k" if n < 10000 else f"{n / 1000:.0f}k") if n >= 1000 else str(n)


def score_ring(tmdb, votes, t):
    """The app's ring, as static markup: arc for the glance, number for the value, vote
    count beside it. `role="img"` so the label is read as one thing: "TMDB 7.1/10 · 41
    ääntä". No `aggregateRating` in the JSON-LD, see the module docstring."""
    if not tmdb:
        return ""
    n = int(votes or 0)
    thin = " thin" if n and n < VOTE_SOLID else ""
    lbl = f"TMDB {tmdb}/10" + (f" \u00b7 {n} {t['votes']}" if n else "")
    return (f'<span class="ring{thin}" role="img" style="--v:{round(float(tmdb) * 10)}" '
            f'title="{esc(lbl)}" aria-label="{esc(lbl)}"><b>{esc(tmdb)}</b></span>'
            + (f'<span class="votes">{esc(short_votes(n))}</span>' if n else ""))


def first(shows, key):
    """A film fact folded across the day's screenings: the first non-empty value, so a
    chain that publishes no rating cannot blank the card when another one did."""
    for s in shows:
        if s.get(key):
            return s[key]
    return None


# The theme, before first paint. The same key and the same fallback as the app's
# `store`/`applyTheme`: a stored "dark" or "light" wins, otherwise the OS decides. Any
# other stored value is treated as absent rather than applied. Without this script the
# attribute is never set, the CSS falls back to `prefers-color-scheme`, and the toggle
# stays hidden, so a reader without JavaScript loses nothing they could use.
THEME_HEAD_JS = (
    "(function(){var k=null;try{k=localStorage.getItem('kino-theme')}catch(e){}"
    "var t=(k==='dark'||k==='light')?k:(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');"
    "document.documentElement.setAttribute('data-theme',t)})();"
)
# The toggle: the app's own handler, and theme-color follows the applied --bg so a
# translucent status bar draws the clock in the right colour. Both metas are rewritten
# because the no-script page carries one per scheme.
THEME_BODY_JS = (
    "(function(){var b=document.getElementById('themeToggle');if(!b)return;"
    "function paint(){var c=getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()||'#0D0E12';"
    "var m=document.querySelectorAll('meta[name=\\'theme-color\\']');"
    "for(var i=0;i<m.length;i++){m[i].removeAttribute('media');m[i].setAttribute('content',c)}}"
    "paint();"
    "b.onclick=function(){var next=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';"
    "document.documentElement.setAttribute('data-theme',next);"
    "try{localStorage.setItem('kino-theme',next)}catch(e){}paint()}})();"
)

# The app's own tokens, both themes: a stored choice through `data-theme` first, the OS
# through `prefers-color-scheme` otherwise. Same Archivo files, same two unicode-range
# subsets, absolute paths because the pages live in subdirectories. The synopsis is
# clamped to three lines on a phone by CSS alone: the full text stays in the markup, so
# the crawler and the visitor read the same document.
CSS = """
@font-face{font-family:'Archivo';font-style:normal;font-weight:100 900;font-stretch:62% 125%;font-display:swap;src:url(/fonts/archivo-latin-ext.woff2) format('woff2');unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
@font-face{font-family:'Archivo';font-style:normal;font-weight:100 900;font-stretch:62% 125%;font-display:swap;src:url(/fonts/archivo-latin.woff2) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
:root{--bg:#F6F7F9;--surface:#FFFFFF;--ink:#16181D;--muted:#5C6470;--line:#E3E6EB;--accent:#B8860B;--accent-text:#8A6508;--chip-bg:#FFFFFF;--shadow:0 1px 3px rgba(22,24,29,.06)}
:root[data-theme=dark]{--bg:#0D0E12;--surface:#16181F;--ink:#EDEDEA;--muted:#8B93A1;--line:#262A33;--accent:#E8B84B;--accent-text:#E8B84B;--chip-bg:#1C1F28;--shadow:0 1px 3px rgba(0,0,0,.4)}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0D0E12;--surface:#16181F;--ink:#EDEDEA;--muted:#8B93A1;--line:#262A33;--accent:#E8B84B;--accent-text:#E8B84B;--chip-bg:#1C1F28;--shadow:0 1px 3px rgba(0,0,0,.4)}}
*{box-sizing:border-box;margin:0;padding:0}
html{color-scheme:light dark}
html[data-theme=dark]{color-scheme:dark}
html[data-theme=light]{color-scheme:light}
body{font:16px/1.5 'Archivo',system-ui,sans-serif;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased}
a{color:inherit}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.wrap{max-width:52rem;margin:0 auto;padding:0 20px 32px}
.bar{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--line)}
.bar .logo{margin-right:auto}
#themeToggle{border:1px solid var(--line);background:var(--surface);color:var(--ink);flex:0 0 44px;width:44px;height:44px;border-radius:50%;cursor:pointer;font-size:1rem;line-height:1;display:grid;place-items:center;transition:border-color .15s,transform .15s}
#themeToggle:hover{border-color:var(--accent);transform:rotate(15deg)}
#themeToggle:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
html:not([data-theme]) #themeToggle{display:none}
.logo{font-stretch:125%;font-weight:900;letter-spacing:.16em;text-transform:uppercase;font-size:1.05rem;text-decoration:none;white-space:nowrap}
.logo span{color:var(--accent)}
.langseg{display:flex;flex:0 0 auto;overflow:hidden;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
.langseg a,.langseg span{display:inline-flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;padding:0 10px;color:var(--muted);text-decoration:none;font-weight:800;font-size:.74rem;letter-spacing:.06em}
.langseg [aria-current]{background:var(--ink);color:var(--bg)}
.langseg a:hover{color:var(--ink)}
h1{font-size:1.5rem;font-weight:800;line-height:1.2;letter-spacing:-.01em;margin:22px 0 4px}
.sub{color:var(--muted);font-size:.9rem}
.intro{color:var(--muted);margin:12px 0 14px}
.cta{display:flex;align-items:center;justify-content:space-between;gap:16px;width:100%;min-height:48px;padding:0 16px;border-radius:10px;background:var(--ink);color:var(--bg);text-decoration:none;font-size:1rem;font-weight:800;line-height:1.3;white-space:nowrap;box-shadow:var(--shadow)}
.cta .arr{flex:0 0 auto}
.cta:hover{background:var(--accent-text);color:#fff}
:root[data-theme=dark] .cta:hover{background:var(--accent);color:var(--bg)}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]) .cta:hover{background:var(--accent);color:var(--bg)}}
.legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin:14px 0 0;font-size:.72rem;color:var(--muted)}
.legend .lg{padding-left:8px;border-left:3px solid var(--chain,var(--line))}
h2.day{position:sticky;top:0;z-index:1;background:var(--bg);font-size:.95rem;font-weight:800;padding:16px 0 8px;margin-top:10px;border-bottom:1px solid var(--line)}
.film{display:flex;gap:18px;padding:20px 0;border-bottom:1px solid var(--line)}
.poster{flex:0 0 92px;width:92px;height:132px;border-radius:8px;object-fit:cover;background:var(--surface);box-shadow:var(--shadow)}
.poster.blank{border:1px solid var(--line)}
.info{flex:1;min-width:0}
h3{font-size:1.15rem;font-weight:800;line-height:1.25;letter-spacing:-.01em}
.meta1{margin-top:7px;display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;font-size:.82rem}
.rating{display:inline-block;border:1px solid var(--line);border-radius:5px;padding:1px 7px;font-weight:700;font-size:.72rem;color:var(--ink);background:var(--surface)}
.ring{--v:0;position:relative;flex:0 0 auto;width:30px;height:30px;border-radius:50%;background:conic-gradient(var(--accent) calc(var(--v) * 3.6deg),var(--line) 0);display:grid;place-items:center}
.ring::before{content:"";position:absolute;inset:3px;border-radius:50%;background:var(--bg)}
.ring b{position:relative;font-size:.68rem;font-weight:800;color:var(--ink);line-height:1}
.ring.thin{opacity:.55}
.votes{color:var(--muted);font-size:.7rem;font-weight:600}
.meta2{margin-top:5px;color:var(--muted);font-size:.8rem;display:flex;flex-wrap:wrap;gap:4px 14px}
.syn{color:var(--muted);font-size:.88rem;line-height:1.45;margin-top:6px}
.times{list-style:none;margin-top:12px;display:flex;flex-wrap:wrap;gap:8px}
.times.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(240px,100%),1fr))}
.grid .stub{display:grid;grid-template-columns:64px minmax(0,1fr) auto;grid-template-areas:"time aud price";align-items:stretch;min-height:40px}
.grid .stub .time{grid-area:time;padding:0 10px 0 12px}
.grid .stub .aud{grid-area:aud;min-width:0;display:flex;flex-wrap:wrap;align-items:center;align-content:center;gap:2px 4px;padding:6px 8px 6px 10px;border-left:1px dashed var(--line);line-height:1.2;overflow-wrap:anywhere}
.grid .stub .aud .a{white-space:normal}
.grid .stub .price{grid-area:price;flex:none;width:auto;display:flex;align-items:center;padding:0 10px 0 4px;border-left:0;font-size:.72rem;color:var(--muted);white-space:nowrap}
.grid .stub .price:empty{display:none}
.grid .stub .price::before,.grid .stub .price::after{display:none}
.grid .stub .aud::before,.grid .stub .aud::after{content:"";position:absolute;left:-4px;width:8px;height:8px;border-radius:50%;background:var(--bg);border:1px solid var(--line)}
.grid .stub .aud::before{top:-5px}.grid .stub .aud::after{bottom:-5px}
.stub{display:flex;align-items:stretch;min-height:40px;background:var(--chip-bg);border:1px solid var(--line);border-radius:7px;box-shadow:var(--shadow);text-decoration:none;color:inherit;font-variant-numeric:tabular-nums;position:relative;overflow:hidden}
.stub[class*="chain-"]{border-left:3px solid var(--chain,var(--line))}
.stub .time{display:flex;align-items:center;padding:0 10px 0 12px;font-weight:800;font-size:.92rem;line-height:1.2;white-space:nowrap}
.stub .aud{display:flex;align-items:center;flex:1 1 auto;min-width:0;padding:6px 12px 6px 10px;font-size:.72rem;line-height:1.3;color:var(--muted);position:relative}
.stub .aud{flex-wrap:wrap;gap:0 4px}
.stub .aud .a{white-space:nowrap}
.stub .price{flex:0 0 56px;width:56px;box-sizing:border-box;align-self:stretch;display:flex;align-items:center;justify-content:center;padding:0 4px;border-left:1px dashed var(--line);text-align:center;white-space:normal;font-size:.78rem;font-weight:700;line-height:1.1;color:var(--ink);position:relative}
.stub .price::before,.stub .price::after{content:"";position:absolute;left:-4px;width:8px;height:8px;border-radius:50%;background:var(--bg);border:1px solid var(--line)}
.stub .price::before{top:-5px}.stub .price::after{bottom:-5px}
.stub:hover .price{color:var(--bg)}
.stub:hover{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.stub:hover .aud{color:var(--bg);opacity:.75}
.also{margin-top:24px}
.also h2{font-size:.95rem;font-weight:800;margin-bottom:10px}
.also ul{list-style:none;display:flex;flex-wrap:wrap;gap:8px}
.vchip{display:inline-flex;align-items:center;min-height:44px;padding:0 12px;border:1px solid var(--line);border-radius:7px;background:var(--surface);text-decoration:none;font-size:.85rem;font-weight:600;box-shadow:var(--shadow)}
.vchip[class*="chain-"]{border-left:3px solid var(--chain,var(--line))}
.vchip:hover{border-color:var(--muted)}
footer{margin-top:28px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:.78rem;display:flex;flex-direction:column;gap:6px}
footer a{color:inherit}
@media(min-width:561px){.cta{width:fit-content;padding:0 18px}}
@media(max-width:560px){.wrap{padding:0 14px 28px}.logo{font-size:.82rem;letter-spacing:.08em}h1{font-size:1.3rem}.poster{flex-basis:72px;width:72px;height:104px}h3{font-size:1.02rem}.syn{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;line-clamp:3;overflow:hidden}}
@media(max-width:360px){.bar{gap:8px}.logo{font-size:.6rem;letter-spacing:.02em}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
""".strip()


# ---------------------------------------------------------------- helpers

def slug(s):
    """URL slug. ä/ö/å are folded by hand first: NFKD does not decompose them in all
    Python builds, and a venue silently losing a letter changes its URL."""
    s = (s or "").lower()
    for a, b in (("ä", "a"), ("ö", "o"), ("å", "a"), ("é", "e"), ("ü", "u")):
        s = s.replace(a, b)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def esc(s):
    return html.escape(str(s or ""), quote=True)


def city_of(v):
    """Mirror of cityOf() in index.html: BioRex and friends ship `city`, Finnkino names
    carry it as the last word ("Plevna Tampere")."""
    if v.get("city"):
        return v["city"]
    w = (v.get("name") or "").strip().split()
    return w[-1] if len(w) > 1 else (v.get("name") or "")


def short_of(v):
    if v.get("short"):
        return v["short"]
    city, n = city_of(v), (v.get("name") or "").strip()
    return n[:-(len(city) + 1)].strip() if n.endswith(" " + city) else n


def label_of(v, chains):
    chain, short = chains.get(v["provider"], ""), short_of(v)
    return f"{chain} {short}" if chain and not short.startswith(chain) else short


def load_venues():
    out = []
    areas = json.loads((DATA / "areas.json").read_text())
    for a in areas.get("areas", []):
        out.append({**a, "provider": "finnkino"})
    for f in sorted(DATA.glob("venues-*.json")):
        d = json.loads(f.read_text())
        for v in d.get("venues", []):
            out.append({**v, "provider": d["provider"]})
    return out


def load_shows(vid):
    p = DATA / f"area-{vid}.json"
    if not p.exists():
        return []
    return json.loads(p.read_text()).get("shows", [])


def duration(minutes):
    try:
        n = int(minutes)
    except (TypeError, ValueError):
        return None
    return f"PT{n}M" if n > 0 else None


def genre_names(gids, genres, gmap, lang):
    """TMDB ids where we have them, the provider's own string otherwise. The chains
    disagree on spelling and their strings are Finnish even in English mode, so ids win
    when both exist."""
    if gids:
        names = [gmap.get(lang, {}).get(str(g)) for g in gids]
        names = [n for n in names if n]
        if names:
            return ", ".join(names)
    return (genres or "").strip().strip(",")


# ---------------------------------------------------------------- rendering

def group_by_day(shows, today, days=DAYS):
    """{iso date: {film title: [show, ...]}} for the next `days` days, times ascending."""
    window = {(today + timedelta(days=i)).isoformat() for i in range(days)}
    days = {}
    for s in sorted(shows, key=lambda x: x.get("start") or ""):
        start = s.get("start") or ""
        d = start[:10]
        if d not in window:
            continue
        days.setdefault(d, {}).setdefault(s.get("title") or "?", []).append(s)
    return days


def day_label(iso, today, t):
    d = date.fromisoformat(iso)
    if d == today:
        head = t["today"]
    elif d == today + timedelta(days=1):
        head = t["tomorrow"]
    else:
        head = t["days"][d.weekday()]
    return f"{head} {d.day}.{d.month}."


def clip(text, n=200):
    """Truncate on a word boundary with an ellipsis. Cutting mid-word looked like a bug
    and Google will re-truncate the snippet anyway."""
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    cut = text[:n]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > n * 0.6 else cut).rstrip(" ,.;:") + "\u2026"


def stub_parts(s, with_venue, lang, own_lang=False):
    """The showtime label, as (css class, text) pairs. The price is not a label part: it
    is its own element on the stub, see film_block.

    Theatre page: the room -- the page already names the cinema, and printing it again
    is how Joensuu read "Tapio · Sali Tapio 4". City page: the chain-prefixed cinema
    first, because a bare "Sali 6" identifies none of twelve. The room is the provider's
    value verbatim after the adapter's own normalisation; Leffabuumi's "KINOLINNA |
    SALI 1" means something and stays. Empty parts vanish, so no separator is ever
    leading, trailing or doubled.

    Language belongs to the card when every screening of the film that day shares it,
    the app's rule; `own_lang` puts it on this screening when they differ, so nothing a
    screening says differently is lost. The classes decide wrapping only: the cinema and
    the language phrases may break at their spaces, the room stays on one line.
    """
    parts = []
    if with_venue:
        parts.append(("v", s.get("venueLabel") or ""))
    parts.append(("a", s.get("aud") or ""))
    if own_lang:
        parts += [("l", x) for x in lang_parts(s.get("lang"), lang)]
    return [(c, t) for c, t in parts if t]


def _part(cls, text):
    """One label part. A language phrase joins names with "/", which Chrome will not break
    after on its own, so a six-language screening would clip in a 206 px column; a <wbr>
    after each slash is a break opportunity and no text."""
    body = esc(text).replace("/", "/<wbr>") if cls == "l" else esc(text)
    return f"<span class={cls}>{body}</span>"


def film_block(title, shows, extra, gmap, lang, t, with_venue, syn_seen):
    rating, length = first(shows, "rating"), first(shows, "len")
    genres = genre_names(first(shows, "gids"), first(shows, "genres"), gmap, lang)
    tmdb = first(shows, "tmdb")
    # Language shared by every screening of this film today -> on the card once.
    # Otherwise each screening says its own, and the card says nothing it cannot say for
    # all of them. Price never folds: `price_label(shows)` skipped unpriced screenings, so
    # Autofiktio in Tampere carried "11€" at film level from Cinema Niagara's 16:15 while
    # Finnkino's 17:30 and 20:15 published none (2026-09-02). A price is the ticket's --
    # provider, time, format and ticket type differ -- so each stub prints its own or
    # nothing, even when every stub happens to agree.
    langs = {s.get("lang") or "" for s in shows}
    shared_lang = lang_parts(next(iter(langs)), lang) if len(langs) == 1 else []
    own_lang = len(langs) > 1

    meta1 = [score_ring(tmdb, first(shows, "votes"), t)]
    if rating:
        meta1.append(f'<span class="rating">{esc(rating)}</span>')
    meta1 = [m for m in meta1 if m]
    meta2 = []
    if genres:
        meta2.append(f"<span>{esc(genres)}</span>")
    if length:
        meta2.append(f"<span>{esc(length)} {t['mins']}</span>")
    if shared_lang:
        meta2.append(f'<span>{esc(" \u00b7 ".join(shared_lang))}</span>')

    # A synopsis only on a film's first appearance: a four-day page repeats the same
    # title daily, and printing it each time both bloated the page and read like padding.
    fx = extra.get(norm(title)) or {}
    syn = ""
    if title not in syn_seen:
        syn = clip(((fx.get("s") or {}).get(lang) or ""))
        syn_seen.add(title)
    # Only same-origin posters: a hot-linked CDN poster would leak the visitor's IP. A
    # film with none keeps its column with a blank tile, so the text does not jump left.
    img = first(shows, "img") or ""
    if img.startswith("data/posters/"):
        poster = f'<img class="poster" src="/{esc(img)}" alt="" width="92" height="132" loading="lazy">'
    else:
        poster = _unmirrored(img) or '<div class="poster blank" aria-hidden="true"></div>'

    times = []
    for s in shows:
        clock = (s.get("start") or "")[11:16]
        parts = stub_parts(s, with_venue, lang, own_lang=own_lang)
        aud = (f'<span class="aud">{" \u00b7 ".join(_part(c, x) for c, x in parts)}</span>'
               if parts else "")
        # Always present: the compartment is part of the ticket's silhouette, blank when
        # the cinema publishes no price. The grid hides an empty one (`:empty`) so the
        # combined view keeps its shape.
        own_price = price_label([s], lang)
        price = f'<span class="price">{esc(own_price)}</span>'
        cls = f" chain-{esc(s['venueProvider'])}" if with_venue and s.get("venueProvider") else ""
        inner = f'<span class="time">{clock}</span>{aud}{price}'
        url = s.get("url") or ""
        times.append(f'<li><a class="stub{cls}" href="{esc(url)}" rel="nofollow noopener">{inner}</a></li>'
                     if url.startswith("http") else f'<li><span class="stub{cls}">{inner}</span></li>')

    # The app's combined view stacks time over place in a grid; its single-venue view
    # keeps the row stub. A city page is the combined view, a theatre page is not.
    grid = " grid" if with_venue else ""
    return (f'<article class="film">{poster}<div class="info"><h3>{esc(title)}</h3>'
            + (f'<div class="meta1">{"".join(meta1)}</div>' if meta1 else "")
            + (f'<div class="meta2">{"".join(meta2)}</div>' if meta2 else "")
            + (f'<p class="syn">{esc(syn)}</p>' if syn else "")
            + f'<ul class="times{grid}">{"".join(times)}</ul></div></article>')


def poster_url(s, extra):
    """Absolute poster URL for markup, or None.

    A URL in JSON-LD is read by the crawler, not fetched by the visitor's browser, so a
    cinema CDN or image.tmdb.org address here does not leak a reader's IP the way an
    <img> would. That is why markup can use posters the page itself refuses to render.
    """
    img = (s.get("img") or "").strip()
    if img.startswith("data/posters/"):
        return f"{SITE}/{img}"
    if img.startswith("http"):
        return img
    fx = extra.get(norm(s.get("title") or "")) or {}
    return fx.get("img") or None


def ld_json(days, today, city, extra):
    """ScreeningEvent per showtime, for today and tomorrow only.

    Three deliberate economies, all of which came out of a 1.2 MB Helsinki page:

    - **Only LD_DAYS of events.** Rich results are a near-term surface, and a crawler
      that revisits weekly would be reading stale markup for day six anyway.
    - **Theatres are `@id` nodes referenced by each event** rather than a nested address
      repeated per showtime. On a ten-venue city page that was most of the payload.
    - **No `availability`.** Sold-out state flips several times a day, so it would
      guarantee a rewrite of every popular page on every run while being stale in the
      index regardless. Price is stable enough to keep.

    No `aggregateRating`: the ratings are TMDB's, and presenting another party's ratings
    as the page's own is against Google's structured-data guidelines.
    """
    window = {(today + timedelta(days=i)).isoformat() for i in range(LD_DAYS)}
    theatres, events = {}, []
    for iso in sorted(d for d in days if d in window):
        for title, shows in days[iso].items():
            for s in shows:
                theatre = s.get("theatre") or ""
                tid = f"#venue-{slug(theatre)}"
                if tid not in theatres:
                    theatres[tid] = {
                        "@type": "MovieTheater", "@id": tid, "name": theatre,
                        "address": {"@type": "PostalAddress",
                                    "addressLocality": city, "addressCountry": "FI"},
                    }
                ev = {
                    "@type": "ScreeningEvent",
                    "name": title,
                    "startDate": s.get("start"),
                    "location": {"@id": tid},
                }
                # Google validates a nested Movie against its own Movie requirements, and
                # `image` is the one it treats as critical: without it the item is parsed,
                # rejected and reported as invalid. A Movie with no poster is no use to it
                # anyway, so the event keeps its name and drops the nested work rather
                # than shipping something that will only ever fail. One showtime in 3509
                # has no poster from any source.
                poster = poster_url(s, extra)
                if poster:
                    work = {"@type": "Movie", "name": title, "image": poster}
                    dur = duration(s.get("len"))
                    if dur:
                        work["duration"] = dur
                    if s.get("tmdbId"):
                        work["sameAs"] = \
                            f"https://www.themoviedb.org/movie/{s['tmdbId']}"
                    ev["workPresented"] = work
                if s.get("url", "").startswith("http"):
                    ev["url"] = s["url"]
                    if s.get("price"):
                        m = re.search(r"\d+([.,]\d+)?", str(s["price"]))
                        if m:
                            ev["offers"] = {"@type": "Offer", "url": s["url"],
                                            "price": m.group(0).replace(",", "."),
                                            "priceCurrency": "EUR"}
                events.append(ev)
    out = json.dumps({"@context": "https://schema.org",
                      "@graph": list(theatres.values()) + events},
                     ensure_ascii=False, separators=(",", ":"))
    # This string is embedded inside <script>, and the HTML parser ends a script
    # element at the first literal "</script>" regardless of its type attribute --
    # valid JSON is not enough here. Titles, venue names and URLs are provider text,
    # so a hostile or merely unlucky title could otherwise close the element and open
    # a live script context. \uXXXX escapes are equivalent JSON, so a consumer parses
    # the identical value. U+2028/U+2029 are legal in JSON but not in JS source, and
    # ensure_ascii=False would emit them raw.
    for ch, rep in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                    ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        out = out.replace(ch, rep)
    return out


def lang_switch(lang, path_fi, path_en, area, t):
    """FI · SV · EN, the app's own selector. The page's language is a plain span marked
    current; the other static language links to its page; Swedish has no static page
    yet, so it opens the app on this area in Swedish -- `lang=sv` is accepted by the same
    startupLang() the CTA relies on. No Swedish hreflang in <head>: there is no Swedish
    canonical to point at."""
    sv = "/?area=" + urllib.parse.quote(area) + "&lang=sv"
    def seg(code, href):
        if code == lang:
            return f'<span aria-current="page">{code.upper()}</span>'
        hl = f' hreflang="{code}"' if code != "sv" else ""
        return f'<a href="{esc(href)}"{hl}>{code.upper()}</a>'
    return (f'<nav class="langseg" aria-label="{esc(t["lang_nav"])}">'
            + seg("fi", path_fi) + seg("sv", sv) + seg("en", path_en) + "</nav>")


def page(*, lang, path_fi, path_en, title, desc, h1, sub, intro, days, today, t,
         extra, gmap, city, with_venue, legend, also, og_image, app_href, area, chain_css):
    body, syn_seen = [], set()
    if not days:
        body.append(f'<p class="intro">{esc(t["no_shows"])}</p>')
    for iso in sorted(days):
        body.append(f'<h2 class="day">{esc(day_label(iso, today, t))}</h2>')
        for title_, shows in sorted(days[iso].items(),
                                    key=lambda kv: (kv[1][0].get("start") or "", kv[0])):
            body.append(film_block(title_, shows, extra, gmap, lang, t,
                                   with_venue=with_venue, syn_seen=syn_seen))
    self_path = path_fi if lang == "fi" else path_en
    # One link, one line. The intro already says the app carries the days ahead, so the
    # button says only what it does; a two-line version read as a hero panel and pushed
    # the first showtime 16 px further down a phone.
    cta = (f'<a class="cta" href="{esc(app_href)}"><span>{esc(t["cta"])}</span>'
           f'<span class="arr" aria-hidden="true">\u2192</span></a>')
    return f"""<!DOCTYPE html>
<html lang="{t['lang']}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#F6F7F9">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0D0E12">
<script>{THEME_HEAD_JS}</script>
<link rel="canonical" href="{SITE}{self_path}">
<link rel="alternate" hreflang="fi" href="{SITE}{path_fi}">
<link rel="alternate" hreflang="en" href="{SITE}{path_en}">
<link rel="alternate" hreflang="x-default" href="{SITE}{path_fi}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Leffavuoro">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{SITE}{self_path}">
<meta property="og:image" content="{SITE}{og_image}">
<meta property="og:locale" content="{t['locale']}">
<link rel="icon" href="/icon-192.png">
<link rel="preload" href="/fonts/archivo-latin.woff2" as="font" type="font/woff2" crossorigin>
<style>{CSS}
{chain_css}</style>
<script type="application/ld+json">{ld_json(days, today, city, extra)}</script>
</head>
<body>
<div class="wrap">
<header class="bar"><a class="logo" href="/">Leffavuoro<span>.</span></a>{lang_switch(lang, path_fi, path_en, area, t)}<button id="themeToggle" type="button" title="{esc(t['theme'])}" aria-label="{esc(t['a_theme'])}">\u25d0</button></header>
<main>
<h1>{esc(h1)}</h1>
<p class="sub">{esc(sub)}</p>
<p class="intro">{esc(intro)}</p>
{cta}
{legend}
{''.join(body)}
{also}
</main>
<footer><div>{esc(t['sources'])}</div><div>{esc(t['contact'])} \u00b7 <a href="mailto:{CONTACT}">{CONTACT}</a></div><div>{esc(t['source'])}: <a href="https://github.com/Shady-Dev/kino" rel="noopener">github.com/Shady-Dev/kino</a> \u00b7 AGPL-3.0</div></footer>
</div>
<script>{THEME_BODY_JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------- main

# Venue slugs that were public before a naming fix, and the venue id each now belongs to.
#
# A slug is built from the chain label and the city, so correcting a label moves the URL.
# Studio 123's two venues rendered their name twice ("Studio 123 Kouvola Studio 123")
# until 2026-08-30, and the fix silently retired four indexed paths -- bookmarks, links
# and anything Google had already crawled would 404. The pages are regenerated as
# redirects instead of being deleted.
#
# Deliberately a fixed table rather than a general aliasing framework: it is four entries
# for one mistake, and a mechanism that rewrites URLs on every label edit would make it
# easy to keep moving them. Add here only when a live URL has actually changed.
LEGACY_VENUE_SLUGS = {
    "studio-123-jarvenpaa-studio-123-jarvenpaa": "s3-jarvenpaa",
    "studio-123-kouvola-studio-123-kouvola": "s3-kouvola",
}


def redirect_page(lang, to_path, label):
    """A minimal page that sends a reader to the URL this one became.

    Not a copy of the venue page: duplicating the content under both URLs is what
    `canonical` exists to prevent, and the schedule would then age in two places. The
    meta refresh moves a browser, the canonical and `noindex` tell a crawler which URL is
    real, and the anchor is what someone lands on if neither runs. `follow` rather than
    `nofollow`, so the link is what carries the old URL's standing to the new one.

    Nothing volatile in it, so `write_if_changed` keeps returning "kept" and these four
    files stop appearing in diffs.
    """
    t = ("Sivu on siirtynyt" if lang == "fi" else "This page has moved")
    go = ("Siirry teatterin sivulle" if lang == "fi" else "Go to the cinema's page")
    return (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{esc(t)}: {esc(label)}</title>\n'
            f'<link rel="canonical" href="{SITE}{to_path}">\n'
            f'<meta name="robots" content="noindex,follow">\n'
            f'<meta http-equiv="refresh" content="0;url={to_path}">\n'
            f'</head>\n<body>\n'
            f'<h1>{esc(t)}</h1>\n'
            f'<p><a href="{to_path}">{esc(go)}: {esc(label)}</a></p>\n'
            f'</body>\n</html>\n')


def write_if_changed(path, text, stats):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        stats["kept"] += 1
        return
    common.write_text_atomic(path, text)
    stats["written"] += 1


def main() -> int:
    providers = {p["id"]: p for p in
                 json.loads((DATA / "providers.json").read_text())["providers"]}
    chains = {k: v.get("label", k) for k, v in providers.items()}
    gmap = json.loads((DATA / "tmdb-genres.json").read_text())
    extra = json.loads((DATA / "films-extra.json").read_text()).get("films", {})
    today = datetime.now(FI).date()

    venues = load_venues()
    for v in venues:
        v["city"] = city_of(v)
        v["label"] = label_of(v, chains)
        v["slug"] = slug(f"{v['label']} {v['city']}")

    seen = {}
    for v in venues:                     # a collision would silently drop a venue's page
        if v["slug"] in seen:
            v["slug"] = f"{v['slug']}-{slug(v['id'])}"
        seen[v["slug"]] = v["id"]

    by_city = {}
    for v in venues:
        by_city.setdefault(v["city"], []).append(v)
    multi = {c: vs for c, vs in by_city.items() if len(vs) > 1}

    stats = {"written": 0, "kept": 0}
    # (path, text) for every page this run produces. Nothing reaches the tree until the
    # whole set is built -- see the flush at the bottom of this function.
    pages = []
    urls = []

    def stage(path, text):
        pages.append((path, text))

    def paths_venue(v):
        return f"/teatteri/{v['slug']}/", f"/en/theatre/{v['slug']}/"

    def paths_city(c):
        s = slug(c)
        return f"/kaupunki/{s}/", f"/en/city/{s}/"

    # ---- venue pages
    for v in venues:
        shows = load_shows(v["id"])
        days = group_by_day(shows, today)
        p_fi, p_en = paths_venue(v)
        first_poster = next((s["img"] for iso in sorted(days)
                             for sh in days[iso].values() for s in sh
                             if (s.get("img") or "").startswith("data/posters/")), None)
        og = f"/{first_poster}" if first_poster else "/icon-512.png"
        prov = providers.get(v["provider"], {})
        for lang in ("fi", "en"):
            t = L[lang]
            also = ""
            if v["city"] in multi:
                cp = paths_city(v["city"])[0 if lang == "fi" else 1]
                also = (f'<nav class="also"><ul><li><a class="vchip" href="{esc(cp)}">'
                        f'{esc(t["city_link"].format(city=v["city"]))}</a></li></ul></nav>')
            text = page(
                lang=lang, path_fi=p_fi, path_en=p_en,
                title=t["venue_title"].format(venue=v["label"], city=v["city"]),
                desc=t["venue_desc"].format(venue=v["label"], city=v["city"]),
                h1=t["venue_h1"].format(venue=v["label"]),
                sub=t["venue_sub"].format(city=v["city"], host=prov.get("host", "")),
                intro=" ".join(x for x in (
                    venue_intro(t, prov.get("book"), prov.get("host", "")),
                    age_note(t, [s for d in days.values() for sh in d.values() for s in sh]))
                    if x),
                days=days, today=today, t=t, extra=extra, gmap=gmap, city=v["city"],
                with_venue=False, legend="", also=also, og_image=og,
                # Deep link, so a reader arriving from search opens on this venue in this
                # language instead of whatever the app last had selected. Both halves are
                # decided by startupArea()/startupLang() in index.html.
                app_href="/?area=" + urllib.parse.quote(v["id"]) + "&lang=" + lang,
                area=v["id"], chain_css="")
            out = ROOT / (p_fi if lang == "fi" else p_en).strip("/") / "index.html"
            stage(out, text)
        urls += [p_fi, p_en]

    # ---- redirects for venue URLs that were public under an older slug. Written after
    # the venue pages so the destination exists, and deliberately not added to `urls`:
    # the sitemap advertises canonical URLs only.
    by_id = {v["id"]: v for v in venues}
    for old_slug, vid in LEGACY_VENUE_SLUGS.items():
        v = by_id.get(vid)
        if v is None or v["slug"] == old_slug:
            continue          # venue gone, or the slug is current again -- nothing to do
        for lang, prefix, dest in (("fi", "teatteri", paths_venue(v)[0]),
                                   ("en", "en/theatre", paths_venue(v)[1])):
            out = ROOT / prefix / old_slug / "index.html"
            stage(out, redirect_page(lang, dest, v["label"]))

    # ---- city pages, only where the app offers a combined view
    for c, vs in multi.items():
        merged = []
        for v in vs:
            for s in load_shows(v["id"]):
                # The chain-prefixed label, not the bare short: "Tripla" and "Kamppi" are
                # shopping centres and "Kallio" a district. Same rule as the app's
                # combined view.
                merged.append({**s, "venueLabel": v["label"], "venueProvider": v["provider"]})
        days = group_by_day(merged, today, CITY_DAYS)
        p_fi, p_en = paths_city(c)
        names = ", ".join(sorted(v["label"] for v in vs))
        first_poster = next((s["img"] for iso in sorted(days)
                             for sh in days[iso].values() for s in sh
                             if (s.get("img") or "").startswith("data/posters/")), None)
        og = f"/{first_poster}" if first_poster else "/icon-512.png"
        # One 3 px rule per chain on the stubs and on the venue links, and a legend that
        # names each colour. Never colour alone: every stub also names its cinema.
        chain_ids = sorted({v["provider"] for v in vs}, key=lambda k: chains.get(k, k))
        chain_css = "".join(f".chain-{esc(k)}{{--chain:{esc(providers[k]['accent'])}}}"
                            for k in chain_ids if providers.get(k, {}).get("accent"))
        legend = ('<p class="legend">' + "".join(
            f'<span class="lg chain-{esc(k)}">{esc(chains.get(k, k))}</span>' for k in chain_ids)
            + "</p>")
        for lang in ("fi", "en"):
            t = L[lang]
            chips = "".join(
                f'<li><a class="vchip chain-{esc(v["provider"])}" '
                f'href="{esc(paths_venue(v)[0 if lang == "fi" else 1])}">{esc(v["label"])}</a></li>'
                for v in sorted(vs, key=lambda x: x["label"]))
            also = (f'<nav class="also"><h2>{esc(t["venues_h"].format(city=c))}</h2>'
                    f"<ul>{chips}</ul></nav>")
            text = page(
                lang=lang, path_fi=p_fi, path_en=p_en,
                title=t["city_title"].format(city=c),
                desc=t["city_desc"].format(city=c, venues=names),
                h1=t["city_h1"].format(city=c),
                sub=t["city_sub"].format(n=len(vs)),
                intro=t["city_intro"].format(n=len(vs)),
                days=days, today=today, t=t, extra=extra, gmap=gmap, city=c,
                with_venue=True, legend=legend, also=also, og_image=og,
                app_href="/?area=" + urllib.parse.quote("city:" + c) + "&lang=" + lang,
                area="city:" + c, chain_css=chain_css)
            out = ROOT / (p_fi if lang == "fi" else p_en).strip("/") / "index.html"
            stage(out, text)
        urls += [p_fi, p_en]

    # ---- sitemap
    lastmod = today.isoformat()
    entries = "\n".join(
        f"  <url><loc>{SITE}{u}</loc><lastmod>{lastmod}</lastmod></url>"
        for u in ["/"] + sorted(urls))
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{entries}\n</urlset>\n")
    stage(ROOT / "sitemap.xml", sm)

    # Everything above only decided what the pages say. This is where they land.
    #
    # The build used to write each page as it produced it, so an exception partway
    # through left the tree holding some of this run's pages and some of the last run's
    # -- and the cloud workflow stages `teatteri kaupunki en sitemap.xml` and pushes
    # before it checks whether the build exited non-zero, so the mixture was published
    # and only then did the run turn red. Measured against real data by raising on the
    # 41st write: 40 of 172 pages new, 132 from the previous build, all committed.
    #
    # The mixture is worse than a partial update sounds. A city page is built from the
    # venues it merges and after them, and the sitemap after both, so a half-built run
    # can serve a city page whose showtimes disagree with the venue pages it links to,
    # under a sitemap describing neither. Nothing on the page says it is inconsistent.
    #
    # Holding the whole set costs 4.5 MB across 173 files, measured, in a process that
    # already has every showtime in memory. The loop does no work that can raise on its
    # own -- it compares and writes -- so a build that fails now writes nothing at all.
    # The previous complete page set stays exactly where it was, and because the failed
    # build stages no page changes, the run's fresh schedule data still publishes.
    for path, text in pages:
        write_if_changed(path, text, stats)

    print(f"[pages] {len(venues)} venues, {len(multi)} multi-venue cities "
          f"({', '.join(sorted(multi))})")
    if _unmirrored_hosts:
        total = sum(_unmirrored_hosts.values())
        where = ", ".join(f"{h} x{n}" for h, n in sorted(_unmirrored_hosts.items()))
        print(f"[pages] WARNING: {total} poster references were still remote and were "
              f"dropped from the markup, so those films render a placeholder tile: "
              f"{where}. mirror_posters should have rewritten these; check whether the "
              f"cloud run before this one completed.")

    print(f"[pages] {len(urls) + 1} urls in sitemap, "
          f"{stats['written']} files written, {stats['kept']} unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
