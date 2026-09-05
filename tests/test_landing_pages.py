"""The generated landing pages, as a reader and a crawler receive them (2026-09-02).

The pages under /teatteri/, /kaupunki/, /en/theatre/ and /en/city/ were redesigned to
belong to the same product as the app: wordmark, one CTA into the app carrying both the
venue and the language, ticket-shaped showtimes, the app's tokens in both themes. These
tests read the pages the real `main()` writes from the repo's own committed data, the way
`test_build_pages_atomic` does, plus a few synthetic shows for the label rule.

What they pin is the requested behaviour and nothing that merely mirrors the mockup:

- the four page families exist in the counts the sitemap advertises, and the four legacy
  redirects are byte-identical to the committed ones;
- every canonical page points at itself and carries its hreflang pair;
- one CTA per page, in the page's language, whose `area` and `lang` are what the
  client's `startupArea()`/`startupLang()` read;
- a theatre page never repeats the cinema inside a showtime; a city page always names it;
  the room is verbatim; empty parts leave no separator behind;
- the intro promises only what the registry's `book` mode offers;
- the language codes render as words, from a table identical to the client's, and no
  raw code is left on any page built from the committed data;
- the FI · SV · EN selector marks the page's language and links the other two;
- the theme is the app's: the stored `kino-theme` wins before first paint, the OS decides
  otherwise, the toggle writes the same key, and no script renders content;
- the card is the app's: film facts fold first-non-empty across the day's screenings,
  language sits on the card when shared and on the screening when it differs, the price
  sits on its own screening's stub and never on the card,
  the score is the app's ring with an accessible label, prices are labelled the way the
  client labels them, and a city page stacks its stubs the way the combined view does;
- regeneration is deterministic and nothing volatile reaches a page.
"""
import contextlib
import html
import io
import json
import pathlib
import ast
import random
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import date

import _ctx
import build_pages as bp


ROOT = _ctx.ROOT
REAL_DATA = ROOT / "data"
REDIRECTS = 4


def advertised():
    """The figures README states: (pages per language, sitemap URLs). Read rather than
    retyped, so the sentence a reader sees is measured against the committed venues
    below. A venue added without README following fails here."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"(\d+) per language, (\d+) sitemap URLs", readme)
    return int(m.group(1)), int(m.group(2))

CTA_RE = re.compile(r'<a class="cta" href="([^"]+)">(.*?)</a>', re.S)
AUD_RE = re.compile(r'<span class="aud">(.*?)</span></span>', re.S)   # up to the stub's end
CANON_RE = re.compile(r'<link rel="canonical" href="([^"]+)">')
LANGSEG_RE = re.compile(r'<nav class="langseg"[^>]*>(.*?)</nav>', re.S)
RAW_CODE_RE = re.compile(r"\b[A-Z]{2}(?:-[A-Z]{2})?-[AS]\b")
HREFLANG_RE = re.compile(r'<link rel="alternate" hreflang="(fi|en)" href="([^"]+)">')
STUB_RE = re.compile(r'<li><(?:a|span) class="stub[^"]*"[^>]*>(.*?)</li>', re.S)


def text_of(html):
    return re.sub(r"<[^>]+>", "", html)


class GeneratedPagesTest(unittest.TestCase):
    """Build once from the committed data, then read what came out."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.tmp.name)
        (cls.root / "data").mkdir()
        for p in REAL_DATA.glob("*.json"):
            shutil.copy2(p, cls.root / "data" / p.name)
        cls.saved = (bp.ROOT, bp.DATA)
        bp.ROOT, bp.DATA = cls.root, cls.root / "data"
        bp._unmirrored_hosts.clear()
        cls.first_run = cls.run_main()
        cls.pages = {}
        for prefix in ("teatteri", "kaupunki", "en/theatre", "en/city"):
            for p in sorted((cls.root / prefix).glob("*/index.html")):
                cls.pages["/" + str(p.relative_to(cls.root).parent) + "/"] = \
                    p.read_text(encoding="utf-8")
        cls.canonical = {k: v for k, v in cls.pages.items() if "noindex" not in v}
        cls.redirects = {k: v for k, v in cls.pages.items() if "noindex" in v}
        cls.providers = {p["id"]: p for p in
                         json.loads((REAL_DATA / "providers.json").read_text())["providers"]}
        # The venue list the way main() sees it: city and label derived, slugs
        # de-duplicated the same way, so the tests address pages by the same names.
        chains = {k: p.get("label", k) for k, p in cls.providers.items()}
        cls.venues, seen = [], set()
        for v in bp.load_venues():
            v["city"] = bp.city_of(v)
            v["label"] = bp.label_of(v, chains)
            v["slug"] = bp.slug(f"{v['label']} {v['city']}")
            if v["slug"] in seen:
                v["slug"] = f"{v['slug']}-{bp.slug(v['id'])}"
            seen.add(v["slug"])
            cls.venues.append(v)
        # One theatre page per venue and one city page per city with more than one venue,
        # in each language. 75 venues and 10 such cities on 2026-09-02, which is 85.
        by_city = {}
        for v in cls.venues:
            by_city.setdefault(v["city"], []).append(v)
        cls.per_lang = len(cls.venues) + sum(1 for vs in by_city.values() if len(vs) > 1)

    @classmethod
    def tearDownClass(cls):
        bp.ROOT, bp.DATA = cls.saved
        cls.tmp.cleanup()

    @classmethod
    def run_main(cls):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            bp.main()
        return buf.getvalue()

    def page_for(self, prefix, needle):
        hits = [k for k in self.canonical if k.startswith(prefix) and needle in k]
        self.assertEqual(len(hits), 1, f"{needle!r} under {prefix}: {hits}")
        return hits[0], self.canonical[hits[0]]

    # -- the set ---------------------------------------------------------------------------

    def test_the_four_families_render_in_the_advertised_counts(self):
        by_prefix = {}
        for k in self.canonical:
            by_prefix[k.split("/")[1] if not k.startswith("/en/") else "en/" + k.split("/")[2]] = \
                by_prefix.get(k.split("/")[1] if not k.startswith("/en/") else "en/" + k.split("/")[2], 0) + 1
        fi = by_prefix["teatteri"] + by_prefix["kaupunki"]
        en = by_prefix["en/theatre"] + by_prefix["en/city"]
        self.assertEqual((fi, en), (self.per_lang, self.per_lang))
        self.assertEqual(len(self.redirects), REDIRECTS)
        self.assertEqual(len(self.pages), 2 * self.per_lang + REDIRECTS)
        for family in ("teatteri", "kaupunki", "en/theatre", "en/city"):
            self.assertGreater(by_prefix[family], 0, family)

    def test_the_readme_advertises_the_measured_counts(self):
        """`85 per language, 171 sitemap URLs` has to be what the data produces. The
        number was carried over from an older document and wrong five times before the
        rule in CLAUDE.md was written; this makes the sixth impossible to commit."""
        per_lang, urls = advertised()
        self.assertEqual(per_lang, self.per_lang)
        self.assertEqual(urls, 2 * self.per_lang + 1)

    def test_the_sitemap_lists_exactly_the_canonical_pages(self):
        sm = (self.root / "sitemap.xml").read_text(encoding="utf-8")
        locs = set(re.findall(r"<loc>(.*?)</loc>", sm))
        self.assertEqual(locs, {bp.SITE + "/"} | {bp.SITE + k for k in self.canonical})
        self.assertEqual(len(locs), 2 * self.per_lang + 1)

    def test_the_legacy_redirects_are_untouched(self):
        for k, text in self.redirects.items():
            with self.subTest(path=k):
                committed = (ROOT / k.strip("/") / "index.html").read_text(encoding="utf-8")
                self.assertEqual(text, committed)
                self.assertNotIn('class="cta"', text)

    def test_every_canonical_page_points_at_itself_and_its_pair(self):
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                self.assertEqual(CANON_RE.search(text).group(1), bp.SITE + k)
                head = text.split("</head>")[0]
                pair = dict(HREFLANG_RE.findall(head))
                self.assertEqual(set(pair), {"fi", "en"})
                self.assertEqual(pair["fi" if not k.startswith("/en/") else "en"], bp.SITE + k)
                self.assertNotIn('hreflang="sv"', head)      # no Swedish canonical exists
                self.assertEqual(re.search(r'<html lang="(\w+)">', text).group(1),
                                 "en" if k.startswith("/en/") else "fi")

    # -- the language selector ---------------------------------------------------------------

    def test_the_selector_marks_this_language_and_links_the_other_two(self):
        """FI · SV · EN on every page: the page's own language is a non-link marked
        current, the other static language links to the pair page, and Swedish opens the
        app on this page's area in Swedish, since no Swedish landing page exists."""
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                segs = LANGSEG_RE.findall(text)
                self.assertEqual(len(segs), 1)
                seg = segs[0]
                items = re.findall(r"<(a|span)([^>]*)>(FI|SV|EN)</(?:a|span)>", seg)
                self.assertEqual([i[2] for i in items], ["FI", "SV", "EN"])
                cur = [i for i in items if 'aria-current="page"' in i[1]]
                self.assertEqual(len(cur), 1)
                self.assertEqual(cur[0][0], "span")
                own = "EN" if k.startswith("/en/") else "FI"
                self.assertEqual(cur[0][2], own)
                pair = dict(HREFLANG_RE.findall(text.split("</head>")[0]))
                other = "fi" if own == "EN" else "en"
                m = re.search(rf'<a href="([^"]+)" hreflang="{other}">{other.upper()}</a>', seg)
                self.assertIsNotNone(m, seg)
                self.assertEqual(bp.SITE + m.group(1), pair[other])
                sv = re.search(r'<a href="([^"]+)">SV</a>', seg)
                self.assertIsNotNone(sv, seg)
                area = html.unescape(CTA_RE.search(text).group(1)).split("area=")[1].split("&")[0]
                self.assertEqual(html.unescape(sv.group(1)), f"/?area={area}&lang=sv")
                self.assertNotIn("hreflang", sv.group(0))

    # -- the CTA ---------------------------------------------------------------------------

    def test_one_cta_per_page_in_the_pages_own_language(self):
        old = "Ajantasaiset ajat, suodattimet ja koko ohjelmisto"
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                ctas = CTA_RE.findall(text)
                self.assertEqual(len(ctas), 1)
                label = " ".join(text_of(ctas[0][1]).replace("\u2192", "").split())
                # One line, one label: the intro already says the app carries the days
                # ahead, so the button does not repeat it.
                if k.startswith("/en/"):
                    self.assertEqual(label, "See the full programme")
                else:
                    self.assertEqual(label, "Avaa koko ohjelmisto")
                for gone in (old, "nyt ja tulevina", "upcoming screenings", 'class="more"'):
                    self.assertNotIn(gone, text)

    def test_the_cta_carries_this_pages_venue_or_city_and_its_language(self):
        ids = {v["id"] for v in self.venues}
        by_slug = {v["slug"]: v["id"] for v in self.venues}
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                href = html.unescape(CTA_RE.search(text).group(1))
                m = re.fullmatch(r"/\?area=([^&]+)&lang=(fi|en)", href)
                self.assertIsNotNone(m, href)
                area = bp.urllib.parse.unquote(m.group(1))
                self.assertEqual(m.group(2), "en" if k.startswith("/en/") else "fi")
                if "/theatre/" in k or k.startswith("/teatteri/"):
                    self.assertIn(area, ids)
                    self.assertEqual(area, by_slug[k.rstrip("/").split("/")[-1]])
                else:
                    self.assertTrue(area.startswith("city:"), area)
                    self.assertEqual(bp.slug(area[5:]), k.rstrip("/").split("/")[-1])

    def test_the_parameters_are_the_ones_the_client_reads(self):
        """The link is only as good as the code at the other end. Both names are read out
        of index.html rather than assumed, so a rename on either side fails here."""
        client = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(".get('area')", client)
        self.assertIn(".get('lang')", client)
        self.assertIn("function startupLang(", client)
        for text in self.canonical.values():
            href = html.unescape(CTA_RE.search(text).group(1))
            self.assertTrue(href.startswith("/?area="), href)
            self.assertIn("&lang=", href)

    # -- the showtime label ----------------------------------------------------------------

    def test_a_theatre_page_never_repeats_its_own_cinema_in_a_showtime(self):
        """Data-driven over every venue: each room the data holds appears verbatim, and
        neither the venue's short name nor its label is prepended to it."""
        checked = 0
        for v in self.venues:
            # Only shows inside the page's own window count: a touring cinema can hold
            # shows in its file and none in the next four days, and that page is right
            # to carry no stubs.
            window = bp.group_by_day(bp.load_shows(v["id"]), bp.datetime.now(bp.FI).date())
            if not window:
                continue
            k = f"/teatteri/{v['slug']}/"
            text = self.canonical[k]
            stubs = [text_of(m) for m in STUB_RE.findall(text)]
            self.assertTrue(stubs, k)
            checked += 1
            for st in stubs:
                self.assertNotIn(f"{bp.short_of(v)} · ", st, (k, st))
                self.assertNotIn(f"{v['label']} · ", st, (k, st))
            # And the room does appear, verbatim, for every show in the window that has
            # one -- so the assertion above cannot pass on an empty label.
            for day in window.values():
                for shs in day.values():
                    for sh in shs:
                        if sh.get("aud"):
                            self.assertTrue(any(sh["aud"] in st for st in stubs),
                                            (k, sh["aud"]))
        self.assertGreater(checked, 50, "the committed data stopped carrying showtimes")

    def test_tapio_reads_sali_tapio_4_and_none_of_the_bad_forms(self):
        k, text = self.page_for("/teatteri/", "savon-kinot-tapio")
        body = text_of(text)
        self.assertIn("Sali Tapio", body)
        for bad in ("TAPIO | TAPIO", "Tapio Tapio", "Sali Sali", "Tapio · Sali"):
            self.assertNotIn(bad, body, bad)

    # -- language in words -------------------------------------------------------------------

    def test_no_raw_language_code_is_left_on_any_page(self):
        """The storage format stays in the JSON. Every -A/-S tag on every page built from
        the committed data has become words."""
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                for block in re.findall(r'<article class="film">(.*?)</article>', text, re.S):
                    self.assertIsNone(RAW_CODE_RE.search(text_of(block)), text_of(block)[:120])

    def test_every_code_in_the_committed_data_is_known(self):
        """The guarantee behind the test above, stated on the data rather than the output:
        each language code the adapters currently publish resolves to a name, an alias
        or the no-subtitles marker. A new code fails here first, by name."""
        seen = set()
        for p in (REAL_DATA).glob("area-*.json"):
            for s in json.loads(p.read_text(encoding="utf-8")).get("shows", []):
                for raw in (s.get("lang") or "").split(","):
                    c = raw.strip()
                    if not c:
                        continue
                    m = bp.LANG_RE.match(c)
                    self.assertIsNotNone(m, (p.name, c))
                    seen.update(m.group(1).split("-"))
        self.assertTrue(seen)
        known = set(bp.LN["fi"]) | set(bp.LN_EXTRA["fi"]) | set(bp.CODE_ALIAS) | bp.NO_SUBTITLES
        self.assertEqual(seen - known, set())
        # and the extras are exactly the ones this file documents, so a new one is a decision
        self.assertEqual(set(bp.CODE_ALIAS), {"TU", "MA"})
        self.assertEqual(bp.NO_SUBTITLES, {"XX"})
        self.assertEqual(set(bp.LN_EXTRA["fi"]), {"LT", "ML"})
        self.assertEqual(set(bp.LN_EXTRA["en"]), {"LT", "ML"})

    def test_the_name_tables_are_the_clients(self):
        """Read out of index.html rather than retyped: `LN.fi` and `LN.en` there must equal
        the generator's, key for key, so the two cannot drift apart quietly."""
        client = (ROOT / "index.html").read_text(encoding="utf-8")
        block = re.search(r"const LN = \{(.*?)\n  \};", client, re.S).group(1)
        tables = {}
        for lang in ("fi", "en"):
            body = re.search(rf"\b{lang}:\{{(.*?)\}}", block, re.S).group(1)
            tables[lang] = dict(re.findall(r"([A-Z]{2}):'([^']*)'", body))
        self.assertEqual(tables["fi"], bp.LN["fi"])
        self.assertEqual(tables["en"], bp.LN["en"])
        self.assertGreater(len(tables["fi"]), 20)

    def test_a_price_appears_only_inside_a_screening_stub(self):
        """Across every generated page: the euro sign occurs only inside a stub's price
        element, never in the card's metadata. The committed Tampere case of 2026-09-02
        is one instance; this holds for whatever the data says today."""
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                body = text.split("<main>")[1].split("</main>")[0]
                metas = re.findall(r'<div class="meta[12]">(.*?)</div>', body)
                self.assertFalse(any("\u20ac" in m for m in metas), k)
                # A synopsis is the cinema's prose and may quote a price ("9€/kpl" in a
                # senior-screening blurb); it is not a label and is left out of the check.
                stripped = re.sub(r'<p class="syn">.*?</p>', "", body, flags=re.S)
                stripped = re.sub(r'<span class="price">[^<]*</span>', "", stripped)
                self.assertNotIn("\u20ac", stripped, k)
                for li in re.findall(r"<li>(.*?)</li>", body, re.S):
                    self.assertLessEqual(li.count('class="price"'), 1)

    def test_a_city_page_stacks_its_stubs_and_a_theatre_page_does_not(self):
        """The app's combined view is a grid of stacked stubs; its single-venue view is a
        row of ticket stubs. A city page is the combined view."""
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                lists = re.findall(r'<ul class="times( grid)?">', text)
                if not lists:
                    continue          # nothing in the window; the count test covers it
                city = k.startswith("/kaupunki/") or k.startswith("/en/city/")
                self.assertEqual({bool(g) for g in lists}, {city})

    def test_the_price_label_is_the_clients(self):
        """The client's own harness cases, run through both implementations. The case
        table is read out of tests/price_label_harness.js and its answers come from node
        running the shipped priceLabel, so neither side is retyped here."""
        if shutil.which("node") is None:
            self.skipTest("node not installed")
        harness = ROOT / "tests" / "price_label_harness.js"
        out = subprocess.run(["node", str(harness)], capture_output=True, text=True,
                             cwd=str(ROOT), timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        expected = json.loads(out.stdout)
        src = harness.read_text(encoding="utf-8")
        cases = re.findall(r"^\s*\['(\w+)',\s*'(\w+)',\s*\[(.*?)\]\],?\s*$", src, re.M)
        self.assertGreater(len(cases), 15)
        checked = 0
        for name, lang, inner in cases:
            if lang not in ("fi", "en"):
                continue
            prices = ast.literal_eval("[" + inner.replace("null", "None").replace("undefined", "None") + "]")
            with self.subTest(case=name):
                self.assertEqual(bp.price_label([{"price": p} for p in prices], lang), expected[name])
                checked += 1
        self.assertGreater(checked, 12)
        for lang in ("fi", "en"):
            self.assertEqual(expected["__from"][lang], bp.L[lang]["from"])

    def test_a_city_page_names_the_cinema_on_every_showtime(self):
        for k, text in self.canonical.items():
            if not (k.startswith("/kaupunki/") or k.startswith("/en/city/")):
                continue
            with self.subTest(path=k):
                labels = {v["label"] for v in self.venues}
                stubs = STUB_RE.findall(text)
                self.assertTrue(stubs, k)
                for st in stubs:
                    m = re.search(r"<span class=v>(.*?)</span>", st)
                    self.assertIsNotNone(m, (k, text_of(st)))
                    self.assertIn(html.unescape(m.group(1)), labels, (k, text_of(st)))

    def test_no_stub_has_a_leading_trailing_or_doubled_separator(self):
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                for aud in AUD_RE.findall(text):
                    plain = text_of(aud)
                    self.assertFalse(plain.startswith("·") or plain.startswith(" ·"), plain)
                    self.assertFalse(plain.endswith("·") or plain.endswith("· "), plain)
                    self.assertNotIn("· ·", plain)
                    self.assertNotIn("··", plain)
                    self.assertNotRegex(aud, r"<span class=\w+></span>")

    # -- the copy --------------------------------------------------------------------------

    def test_the_intro_promises_what_the_booking_mode_offers(self):
        """Every venue page, against the registry's own `book` field."""
        for v in self.venues:
            k = f"/teatteri/{v['slug']}/"
            prov = self.providers[v["provider"]]
            for lang, path in ((("fi", k)), ("en", "/en/theatre" + k[len("/teatteri"):])):
                with self.subTest(path=path):
                    expected = bp.venue_intro(bp.L[lang], prov.get("book"), prov["host"])
                    self.assertIn(bp.esc(expected), self.canonical[path])

    def test_all_five_booking_modes_have_their_own_sentence(self):
        for lang in ("fi", "en"):
            seen = {bp.venue_intro(bp.L[lang], b, "x.fi")
                    for b in ("buy", "reserve", "list", "door", "admission")}
            self.assertEqual(len(seen), 5, lang)
            self.assertNotIn("x.fi", bp.venue_intro(bp.L[lang], "door", "x.fi"))
            for b in ("buy", "reserve", "list", "admission"):
                self.assertIn("x.fi", bp.venue_intro(bp.L[lang], b, "x.fi"))
            self.assertEqual(bp.venue_intro(bp.L[lang], None, "x.fi"),
                             bp.venue_intro(bp.L[lang], "buy", "x.fi"))

    def test_a_city_intro_does_not_promise_ticket_sales(self):
        for k, text in self.canonical.items():
            if not (k.startswith("/kaupunki/") or k.startswith("/en/city/")):
                continue
            with self.subTest(path=k):
                self.assertNotIn("sivustolla", text_of(text).split("<h2")[0])
                self.assertIn("kun linkki on saatavilla" if k.startswith("/kaupunki/")
                              else "where available", text)

    # -- stability -------------------------------------------------------------------------

    def test_regenerating_writes_nothing(self):
        out = self.run_main()
        self.assertIn(" 0 files written", out)

    def test_nothing_volatile_reaches_a_page(self):
        """Only a stamp with a time component is evidence. `films-extra.json` writes
        `generated` as a bare date, and every page with a screening that day carries the
        same date inside a JSON-LD `startDate`; on 2026-09-02 that failed 154 pages on a
        legitimate `2026-09-02T18:15:00+03:00`. It had passed only while the date-only
        stamp lagged a day behind the screenings on the page. A build timestamp that
        leaked would carry its time of day, and that is what is searched for."""
        stamps = set()
        for p in (self.root / "data").glob("*.json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            for key in ("generated", "oldest"):
                if isinstance(d, dict) and d.get(key) and "T" in d[key]:
                    stamps.add(d[key])
        self.assertTrue(stamps)
        self.assertTrue(all(len(st) >= len("2026-09-02T05:10") for st in stamps))
        for k, text in self.pages.items():
            with self.subTest(path=k):
                for st in stamps:
                    self.assertNotIn(st, text)
                body_scripts = re.findall(r"<script>(.*?)</script>", text.split("</head>")[1], re.S)
                if k in self.redirects:
                    self.assertEqual(body_scripts, [])
                else:
                    self.assertEqual(len(body_scripts), 1)
                    self.assertIn("kino-theme", body_scripts[0])

    # -- the theme ---------------------------------------------------------------------------

    def test_the_theme_is_read_before_first_paint_from_the_apps_key(self):
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                head = text.split("</head>")[0]
                scripts = re.findall(r"<script>(.*?)</script>", head, re.S)
                self.assertEqual(len(scripts), 1)
                js = scripts[0]
                self.assertIn("localStorage.getItem('kino-theme')", js)
                self.assertIn("prefers-color-scheme: dark", js)
                self.assertIn("setAttribute('data-theme'", js)
                # a stored value the app never writes is treated as absent, not applied
                self.assertIn("k==='dark'||k==='light'", js)
                self.assertLess(head.index("<script>"), head.index("<style>"))

    def test_the_stylesheet_honours_the_stored_theme_and_falls_back_to_the_os(self):
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                css = re.search(r"<style>(.*?)</style>", text, re.S).group(1)
                self.assertIn(":root[data-theme=dark]{--bg:#0D0E12", css)
                self.assertIn("@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0D0E12", css)
                self.assertIn("html:not([data-theme]) #themeToggle{display:none}", css)

    def test_the_toggle_is_the_apps_button_with_a_localised_name(self):
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                m = re.search(r'<button id="themeToggle" type="button" title="([^"]+)" aria-label="([^"]+)">', text)
                self.assertIsNotNone(m)
                if k.startswith("/en/"):
                    self.assertEqual(m.group(2), "Switch between light and dark theme")
                else:
                    self.assertEqual(m.group(2), "Vaihda vaalean ja tumman teeman välillä")
                body_js = re.findall(r"<script>(.*?)</script>", text.split("</head>")[1], re.S)[0]
                self.assertIn("localStorage.setItem('kino-theme',next)", body_js)
                self.assertIn("theme-color", body_js)

    def test_no_script_renders_content(self):
        """The rule the pages keep: what the crawler reads is what the visitor reads. The
        two scripts touch an attribute, a meta and a button, nothing else."""
        for k, text in self.canonical.items():
            with self.subTest(path=k):
                for js in re.findall(r"<script>(.*?)</script>", text, re.S):
                    for banned in ("innerHTML", "document.write", "createElement",
                                   "appendChild", "fetch(", "textContent"):
                        self.assertNotIn(banned, js)

    @unittest.skipIf(shutil.which("node") is None, "node not installed")
    def test_the_inline_scripts_parse(self):
        """The same check `scripts/check_inline_js.py` gives the app, against one page of
        each family; the scripts are constants, so one page each is every page."""
        for prefix in ("/teatteri/", "/kaupunki/", "/en/theatre/", "/en/city/"):
            k = next(p for p in self.canonical if p.startswith(prefix))
            for js in re.findall(r"<script>(.*?)</script>", self.canonical[k], re.S):
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                    f.write(js); name = f.name
                try:
                    r = subprocess.run(["node", "--check", name], capture_output=True, text=True)
                finally:
                    pathlib.Path(name).unlink()
                self.assertEqual(r.returncode, 0, (k, r.stderr))


class StubShapeTest(unittest.TestCase):
    """The label rule on synthetic shows, so it does not depend on what plays this week."""

    T = bp.L["fi"]

    @staticmethod
    def show(**kw):
        base = {"title": "Laula minulle Arja", "start": "2026-09-02T16:00:00+03:00",
                "theatre": "Tapio Joensuu", "aud": "Sali Tapio 4", "lang": "FI-S, SV-S",
                "url": "https://www.savonkinot.fi/salikartta?id=1", "venueLabel": "Savon Kinot Tapio",
                "venueProvider": "savonkinot"}
        base.update(kw)
        return base

    def aud_text(self, s, with_venue, lang="fi"):
        html = bp.film_block(s["title"], [s], {}, {}, lang, bp.L[lang], with_venue, set())
        m = AUD_RE.search(html)
        return text_of(m.group(1)) if m else None

    def block(self, shows, with_venue, lang="fi"):
        return bp.film_block(shows[0]["title"], shows, {}, {}, lang, bp.L[lang], with_venue, set())

    def meta2_text(self, html):
        m = re.search(r'<div class="meta2">(.*?)</div>', html)
        return [text_of(x) for x in re.findall(r"<span>(.*?)</span>", m.group(1))] if m else []

    def stub_texts(self, html):
        return [text_of(a) for a in re.findall(r'<span class="aud">(.*?)</span></span>', html)]

    def test_theatre_shape(self):
        s = self.show(lang="EN-A, FI-S, SV-S")
        self.assertEqual(self.aud_text(s, False), "Sali Tapio 4")
        self.assertIn("englanti · tekstitys suomi/ruotsi", self.meta2_text(self.block([s], False)))
        self.assertIn("English · Finnish/Swedish subtitles", self.meta2_text(self.block([s], False, "en")))

    def test_city_shape(self):
        s = self.show(lang="EN-A, FI-S, SV-S", venueLabel="Finnkino Tennispalatsi", aud="Sali 10")
        self.assertEqual(self.aud_text(s, True), "Finnkino Tennispalatsi · Sali 10")
        self.assertIn('<ul class="times grid">', self.block([s], True))
        self.assertIn('<ul class="times">', self.block([s], False))

    def test_shared_language_sits_on_the_card_once(self):
        shows = [self.show(start="2026-09-02T16:00:00+03:00", aud="Sali Tapio 4"),
                 self.show(start="2026-09-02T19:00:00+03:00", aud="Sali Tapio 1")]
        html = self.block(shows, False)
        self.assertEqual(self.meta2_text(html).count("tekstitys suomi/ruotsi"), 1)
        self.assertEqual(self.stub_texts(html), ["Sali Tapio 4", "Sali Tapio 1"])

    def test_a_differing_language_stays_on_its_screening(self):
        """Never the first screening's language for all of them: a dubbed 16:00 and a
        subtitled 19:00 each say their own, and the card says neither."""
        shows = [self.show(start="2026-09-02T16:00:00+03:00", aud="Sali Tapio 4", lang="FI-A"),
                 self.show(start="2026-09-02T19:00:00+03:00", aud="Sali Tapio 1", lang="EN-A, FI-S, SV-S")]
        html = self.block(shows, False)
        self.assertEqual(self.stub_texts(html),
                         ["Sali Tapio 4 · suomi", "Sali Tapio 1 · englanti · tekstitys suomi/ruotsi"])
        self.assertFalse(any("tekstitys" in m or m == "suomi" for m in self.meta2_text(html)))

    # -- price: the screening's, never the film's (2026-09-02) ----------------------------

    @staticmethod
    def stubs_of(html):
        return re.findall(r"<li>(.*?)</li>", html, re.S)

    def stub_prices(self, html):
        """One entry per stub: the price compartment's text, or None when it is blank.
        The compartment itself is always there (2026-09-02): it is part of the ticket."""
        out = []
        for li in self.stubs_of(html):
            m = re.search(r'<span class="price">(.*?)</span>', li)
            out.append(text_of(m.group(1)) or None if m else None)
        return out

    @staticmethod
    def card_text(html):
        m = re.search(r"<h3>.*?<ul class=", html, re.S)
        return text_of(m.group(0)) if m else ""

    def tampere(self):
        """The committed Autofiktio / Tampere case of 2026-09-02, field for field: Cinema
        Niagara 16:15 at 11€, Finnkino Plevna 17:30 and 20:15 with no published price."""
        base = dict(title="Autofiktio", lang="ES-A, FI-S, SV-S", rating="K-12", len="112",
                    genres="Draama, Komedia", gids=[18, 35], img="", tmdb=6.3, votes=123)
        return [dict(base, start="2026-09-02T16:15:00+03:00", price="11\u20ac", aud="",
                     venueLabel="Cinema Niagara", venueProvider="niagara",
                     url="https://cinemaniagara.fi/salikartta?id=54280"),
                dict(base, start="2026-09-02T17:30:00+03:00", price=None, aud="Sali 7",
                     venueLabel="Finnkino Plevna", venueProvider="finnkino",
                     url="https://www.finnkino.fi/websales/show/302341/"),
                dict(base, start="2026-09-02T20:15:00+03:00", price=None, aud="Sali 7",
                     venueLabel="Finnkino Plevna", venueProvider="finnkino",
                     url="https://www.finnkino.fi/websales/show/302342/")]

    def test_one_priced_screening_among_unpriced_ones_prices_only_itself(self):
        """The defect. price_label over the three skipped the unpriced two and put 11€ on
        the card as if Finnkino charged it."""
        html = self.block(self.tampere(), True)
        self.assertEqual(self.stub_prices(html), ["11\u20ac", None, None])
        self.assertNotIn("\u20ac", self.card_text(html))
        self.assertEqual(html.count("11\u20ac"), 1)
        niagara = next(li for li in self.stubs_of(html) if "Cinema Niagara" in li)
        self.assertIn('<span class="price">11\u20ac</span>', niagara)

    def test_different_prices_stay_with_their_screenings(self):
        shows = [self.show(start="2026-09-02T16:00:00+03:00", price="13\u20ac"),
                 self.show(start="2026-09-02T19:00:00+03:00", price="10\u20ac", aud="Sali Tapio 1")]
        html = self.block(shows, False)
        self.assertEqual(self.stub_prices(html), ["13\u20ac", "10\u20ac"])
        self.assertNotIn("\u20ac", self.card_text(html))
        self.assertNotIn("alkaen", html)

    def test_the_same_price_everywhere_is_still_each_screenings_own(self):
        shows = [self.show(start=f"2026-09-02T{h}:00:00+03:00", price="13\u20ac", aud=f"Sali {h}")
                 for h in ("14", "17", "20")]
        html = self.block(shows, False)
        self.assertEqual(self.stub_prices(html), ["13\u20ac"] * 3)
        self.assertNotIn("\u20ac", self.card_text(html))

    def test_no_prices_means_blank_compartments_and_no_value(self):
        """The compartment stays so the ticket keeps its silhouette; nothing is printed in
        it -- no euro, no dash, no zero, no word."""
        shows = [self.show(start="2026-09-02T16:00:00+03:00", price=None),
                 self.show(start="2026-09-02T19:00:00+03:00", price="", aud="Sali Tapio 1")]
        html = self.block(shows, False)
        self.assertNotIn("\u20ac", html)
        for li in self.stubs_of(html):
            self.assertTrue(li.endswith('<span class="price"></span></a>'), li)
            self.assertEqual(li.count('class="price"'), 1)
        self.assertEqual(self.stub_prices(html), [None, None])

    def test_a_providers_own_floor_survives_on_its_stub(self):
        s = self.show(price="alkaen 10\u20ac")
        self.assertEqual(self.stub_prices(self.block([s], False)), ["alkaen 10\u20ac"])
        self.assertEqual(self.stub_prices(self.block([s], False, "en")), ["from 10\u20ac"])
        self.assertNotIn("\u20ac", self.card_text(self.block([s], False)))

    def test_city_and_theatre_pages_both_attach_the_price_to_the_right_stub(self):
        for with_venue in (True, False):
            with self.subTest(with_venue=with_venue):
                html = self.block(self.tampere(), with_venue)
                lis = self.stubs_of(html)
                self.assertEqual(self.stub_prices(html), ["11\u20ac", None, None])
                self.assertIn("16:15", lis[0])
                self.assertNotIn("\u20ac", self.card_text(html))

    def test_a_hostile_price_string_cannot_reach_the_page(self):
        """price_label rebuilds the label from the number it finds, so markup in a
        provider's price string never survives it; the leftover letters make it a floor.
        The element is escaped on top of that, asserted at the source."""
        s = self.show(price="13\u20ac<b>x</b>")
        html = self.block([s], False)
        self.assertNotIn("<b>", html)
        self.assertEqual(self.stub_prices(html), ["alkaen 13\u20ac"])
        src = (ROOT / "scripts" / "build_pages.py").read_text(encoding="utf-8")
        self.assertIn('<span class="price">{esc(own_price)}</span>', src)

    def test_venue_room_and_links_are_what_they_were(self):
        html = self.block(self.tampere(), True)
        self.assertEqual(re.findall(r'href="([^"]+)"', html),
                         ["https://cinemaniagara.fi/salikartta?id=54280",
                          "https://www.finnkino.fi/websales/show/302341/",
                          "https://www.finnkino.fi/websales/show/302342/"])
        self.assertEqual(self.stub_texts(html),
                         ["Cinema Niagara", "Finnkino Plevna · Sali 7", "Finnkino Plevna · Sali 7"])
        self.assertIn('class="stub chain-niagara"', html)
        self.assertIn('class="stub chain-finnkino"', html)
        self.assertNotIn("sold", html.lower())

    def test_film_facts_fold_first_non_empty_not_first(self):
        shows = [self.show(start="2026-09-02T16:00:00+03:00", rating="", tmdb=None, votes=None),
                 self.show(start="2026-09-02T19:00:00+03:00", rating="K-12", tmdb=7.1, votes=41)]
        html = self.block(shows, False)
        self.assertIn('<span class="rating">K-12</span>', html)
        self.assertIn('aria-label="TMDB 7.1/10 · 41 ääntä"', html)

    def test_the_score_is_the_apps_ring_with_an_accessible_label(self):
        html = self.block([self.show(tmdb=7.1, votes=41)], False)
        self.assertIn('<span class="ring" role="img" style="--v:71" title="TMDB 7.1/10 · 41 ääntä" '
                      'aria-label="TMDB 7.1/10 · 41 ääntä"><b>7.1</b></span><span class="votes">41</span>', html)
        thin = self.block([self.show(tmdb=6.4, votes=12)], False, "en")
        self.assertIn('class="ring thin"', thin)
        self.assertIn("TMDB 6.4/10 · 12 votes", thin)
        self.assertIn(">1.2k<", self.block([self.show(tmdb=8.0, votes=1234)], False))
        self.assertNotIn("ring", self.block([self.show(tmdb=None)], False))
        self.assertIn('aria-label="TMDB 7.1/10"><b>7.1</b></span>', self.block([self.show(tmdb=7.1, votes=None)], False))

    def test_an_empty_room_leaves_no_separator(self):
        shows = [self.show(aud="", lang="FI-A"), self.show(aud="", lang="EN-A", start="2026-09-02T19:00:00+03:00")]
        self.assertEqual(self.stub_texts(self.block(shows, False)), ["suomi", "englanti"])
        self.assertEqual(self.stub_texts(self.block(shows, True)),
                         ["Savon Kinot Tapio · suomi", "Savon Kinot Tapio · englanti"])

    def test_nothing_but_the_time_leaves_no_details_cell(self):
        self.assertIsNone(self.aud_text(self.show(aud="", lang=""), False))

    def test_the_room_is_verbatim_including_leffabuumis_pipe(self):
        s = self.show(aud="KINOLINNA | SALI 1", lang="FI-A", venueLabel="Leffabuumi Kinolinna")
        self.assertEqual(self.aud_text(s, False), "KINOLINNA | SALI 1")
        self.assertEqual(self.aud_text(s, True), "Leffabuumi Kinolinna · KINOLINNA | SALI 1")

    def test_language_words_follow_the_apps_rule(self):
        cases = {
            # role words, and subtitles after the spoken language
            "EN-A, FI-S, SV-S": (["englanti", "tekstitys suomi/ruotsi"],
                                 ["English", "Finnish/Swedish subtitles"]),
            # a dubbed film: spoken language only
            "FI-A": (["suomi"], ["Finnish"]),
            # subtitles only
            "FI-S, SV-S": (["tekstitys suomi/ruotsi"], ["Finnish/Swedish subtitles"]),
            # duplicates collapse, source order kept
            "FI-A, FI-S, SV-S, FI-S": (["suomi", "tekstitys suomi/ruotsi"],
                                      ["Finnish", "Finnish/Swedish subtitles"]),
            # a compound tag is two languages
            "FI-S, FI-SV-A, SV-S": (["suomi/ruotsi", "tekstitys suomi/ruotsi"],
                                    ["Finnish/Swedish", "Finnish/Swedish subtitles"]),
            # Nexxo's no-subtitles marker is an absent role
            "FI-A, XX-S": (["suomi"], ["Finnish"]),
            "XX-S": ([], []),
            # Finnkino's own codes and the one ISO code the client lacks
            "TU-A, FI-S, SV-S": (["turkki", "tekstitys suomi/ruotsi"],
                                 ["Turkish", "Finnish/Swedish subtitles"]),
            "EN-S, MA-A": (["malajalam", "tekstitys englanti"], ["Malayalam", "English subtitles"]),
            "LT-A, FI-S": (["liettua", "tekstitys suomi"], ["Lithuanian", "Finnish subtitles"]),
            # a code nobody has mapped stays visible rather than vanishing
            "ZZ-A, FI-S": (["ZZ", "tekstitys suomi"], ["ZZ", "Finnish subtitles"]),
            "": ([], []),
        }
        for codes, (fi, en) in cases.items():
            with self.subTest(codes=codes):
                self.assertEqual(bp.lang_parts(codes, "fi"), fi)
                self.assertEqual(bp.lang_parts(codes, "en"), en)

    def test_the_time_is_the_clock_and_the_stub_is_a_link_when_there_is_a_url(self):
        html = bp.film_block("x", [self.show()], {}, {}, "fi", self.T, False, set())
        self.assertIn('<span class="time">16:00</span>', html)
        self.assertIn('<a class="stub" href="https://www.savonkinot.fi/salikartta?id=1" rel="nofollow noopener">', html)
        html = bp.film_block("x", [self.show(url="")], {}, {}, "fi", self.T, False, set())
        self.assertIn('<span class="stub">', html)
        self.assertNotIn("<a class=\"stub", html)

    def test_the_order_shows_arrive_in_does_not_change_the_page(self):
        shows = [self.show(start=f"2026-09-02T{h:02d}:00:00+03:00", aud=f"Sali Tapio {i%4+1}",
                           title=("A" if i % 2 else "B")) for i, h in enumerate(range(10, 22))]
        today = date(2026, 9, 2)
        def render(order):
            days = bp.group_by_day(order, today)
            seen = set()
            return "".join(bp.film_block(t_, sh, {}, {}, "fi", self.T, False, seen)
                           for iso in sorted(days)
                           for t_, sh in sorted(days[iso].items(),
                                                key=lambda kv: (kv[1][0]["start"], kv[0])))
        ref = render(list(shows))
        rnd = random.Random(7)
        for _ in range(5):
            order = list(shows); rnd.shuffle(order)
            self.assertEqual(render(order), ref)


if __name__ == "__main__":
    unittest.main()
