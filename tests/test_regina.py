"""Kino Regina: the theme's POST schedule, its two-week windows, and the film page.

Fixtures follow kinoregina.fi's own markup as read on 2026-09-05: a day header and one
`div.movie` block per screening with the start written with its year, a `grey` block with
"Myynti on päättynyt." once online sales close, the "Lataa lisää" button naming the next
window's first day, and a film page whose age limit is an image, whose Teemat cell links
the cinema's series and whose Kuvaus separates the synopsis from an essay with "***".
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import build_pages as bp
import registry
import run
import regina

ROOT = _ctx.ROOT
BASE = "https://kinoregina.fi"
SCHEDULE = regina.SCHEDULE
LISTING = regina.LISTING


def day_header(text):
    return f"""
      <div class="row">
        <div class="day-header pr col-12">
          <span class="day d-block">{text}</span>
        </div>
      </div>"""


def block(fid, title, start, state="green", info="", ticket=True, film_link=True):
    info_html = f'<div class="info">{info}</div>' if info else ""
    link = (f'<a href="{BASE}/elokuva/{fid}" class="title d-block d-md-inline-block">{title}</a>'
            if film_link else f'<a href="{BASE}/tapahtuma/{fid}" class="title d-block d-md-inline-block">{title}</a>')
    cart = (f'<a href="https://kauppa.kavi.fi/fi/events/pwdg/event_buybox/show/6a21c8{fid}" target="_blank" '
            f'class="add-to-cart cp pa" aria-label="Osta lippu: {title}" rel="noopener noreferrer">'
            f'<i class="fas fa-shopping-cart" aria-hidden="true"></i></a>') if ticket else ""
    return f"""
        <div class="row">
          <div class="movie pr col-12 {state}">
            {info_html}            <div class="row">
              <div class="content-container d-md-flex col-12">
                <div class="left-side d-md-flex">
                  <div class="img-container sixteen-nine cover d-none d-md-inline-block" style="background-image: url('{BASE}/wp-content/uploads/2021/09/still-300x163-optimized.jpg"></div>
                  <div class="movie-content d-flex d-md-block pr">
                    <span class="time d-block d-md-inline-block">{start[11:]}</span>
                    {link}<br class="d-none d-md-block"/>
                    <p class="d-none d-md-block">Lyhyt kuvaus...</p>
                  </div>
                </div>
                <div class="right-side d-block d-md-flex">
                  <div class="calendar-icon add-to-calendar cp pa addeventatc" role="button" aria-label="Lis&#228;&#228; kalenteriin">
                    <i class="far fa-calendar-alt"></i>
                    <span class="start">{start}</span>
                    <span class="timezone">Europe/Helsinki</span>
                    <span class="title">{title}</span>
                  </div>
                  {cart}
                </div>
              </div>
            </div>
          </div>
        </div>"""


def load_more(day):
    return f"""
  <div class="row">
    <div class="col-12 text-center" style="margin-top: 40px;">
      <button id="loadMoreMovies"
              onclick="loadNextTwoWeeks('{day}', this)"
              style="font-family: relative-bold, sans-serif;">
        <i class="fas fa-list" style="margin-right: 12px;"></i>Lataa lisää
      </button>
    </div>
  </div>
"""


WINDOW_1 = (
    day_header("Lauantai 5.9.")
    + block("202769", "SÁTÁNTANGÓ", "05-09-2026 14:00", state="grey", info="Myynti on päättynyt.")
    + day_header("Sunnuntai 6.9.")
    + block("1415167", "PERSEPOLIS", "06-09-2026 14:00")
    + block("105609", "PIUKAT PAIKAT", "06-09-2026 16:00")
    + block("105609", "PIUKAT PAIKAT", "06-09-2026 16:00")                  # listed twice
    + block("9001", "Keskustelutilaisuus", "06-09-2026 17:30", film_link=False)   # an event, not a film
    + block("1653971", "ONE BATTLE AFTER ANOTHER", "11-09-2026 20:30", ticket=False)
    + load_more("2026-09-21")
)
WINDOW_2 = (
    day_header("Maanantai 21.9.")
    + block("139011", "CARRIE", "21-09-2026 19:30")
    + load_more("2026-10-07")
)
WINDOW_EMPTY = load_more("2026-10-23")


def film_page(age_alt, kesto, tekstitys, teemat, kopiotieto, lisatieto, kuvaus):
    age = (f'<span><img src="{BASE}/wp-content/themes/kinoregina2/assets/img/K16.jpg" width="32" height="32" '
           f'alt="{age_alt}" /></span>') if age_alt else "<span></span>"
    teemat_html = "".join(f'<span><a href="{BASE}/teemat/{slug}">{name}</a></span>' for slug, name in teemat)
    lisatieto_row = (f'<div class="col-4 col-md-2"><b><span>Lisätieto</span></b></div>'
                     f'<div class="col-8 col-md-4"><span>{lisatieto}</span></div>') if lisatieto else ""
    return f"""<!doctype html><html><head><title>X - Kino Regina</title>
<meta property="og:image" content="http://kinoregina.fi/wp-content/uploads/2026/06/still-optimized.jpg"></head><body>
<div class="main-content col-12 col-lg-9 col-xl-6" id="main-content"><div class="row"><div class="col-12"><h1>X (2025)</h1></div></div>
<a name="lisatiedot"></a><div class="row"><div class="col-12"><div class="row">
<div class="col-4 col-md-2"><b><span>Ohjaaja</span></b></div><div class="col-8 col-md-4"><span>Joku Ohjaaja</span></div>
<div class="col-4 col-md-2"><b><span>Maa</span></b></div><div class="col-8 col-md-4"><span>Yhdysvallat</span></div>
<div class="col-4 col-md-2"><b><span>Tekstitys</span></b></div><div class="col-8 col-md-4"><span>{tekstitys}</span></div>
<div class="col-4 col-md-2"><b><span>Kesto</span></b></div><div class="col-8 col-md-4"><span>{kesto}</span></div>
<div class="col-4 col-md-2"><b><span>Teemat</span></b></div><div class="col-8 col-md-4">{teemat_html}</div>
<div class="col-4 col-md-2"><b><span>Kopiotieto</span></b></div><div class="col-8 col-md-4"><span>{kopiotieto}</span></div>
{lisatieto_row}
<div class="col-4 col-md-2"><b><span>Ikäraja</span></b></div><div class="col-8 col-md-4">{age}</div>
</div></div></div>
<a name="kuvaus"></a><div class="row"> <!--<style> .single-movie-main-content-area p:first-child {{ font-size: 17px; }} </style>--><div class="col-12 single-movie-main-content-area">{kuvaus}</div></div>
<a name="naytosajat"></a><div class="row"><div class="col-12"><h2>Näytökset</h2></div></div>
</div></body></html>"""


ONE_BATTLE = film_page(
    "Ikäraja: K12", "162 min", "ei tekstitystä",
    [("paul-thomas-anderson", "PAUL THOMAS ANDERSON"), ("jatkoaika-kesa-2026", "JATKOAIKA KESÄ 2026")],
    "70 mm", "Thomas Pynchonin romaanista",
    "<p>Loistokkaalta 70 mm:n kopiolta nähtävä <em>One Battle After Another</em> (2025) on harvinaista ison "
    "kankaan poliittista toimintaelokuvaa.</p><p>***</p><p>Paul Thomas Anderson kuuluu yhdysvaltalaisen "
    "nykyelokuvan arvostetuimpiin auteur-ohjaajiin.</p>")
PERSEPOLIS = film_page(
    "Ikäraja: K16", "97 min", "suom. tekstit/svenska texter",
    [("koko-perheelle-frankofonia-sarjakuvan-kesa", "KOKO PERHEELLE: FRANKOFONIA-SARJAKUVAN KESÄ"),
     ("kesajazzit", "KESÄJAZZIT"), ("kesajazzit", "KESÄJAZZIT")],
    "35 mm", "15 min väliaika",
    "<p>Iranista Itävaltaan emigroituneen sarjakuvataiteilijan elämään perustuva teos on vaikuttava, "
    "klassisen animaation keinoin kerrottu tarina.</p>")
PLAIN = film_page("", "120 min", "English subtitles", [], "DCP", "",
                  "<p>Kaksi chicagolaista jazzmuusikkoa todistaa vahingossa mafian verilöylyn ja pakenee.</p>")

SITE = regina.SITES[0]
VENUE = SITE["venues"][0]


class ScheduleTest(unittest.TestCase):
    def setUp(self):
        self.shows = regina.parse_schedule(WINDOW_1)
        self.by_id = {}
        for s in self.shows:
            self.by_id.setdefault(s["eventId"], []).append(s)

    def test_rows_become_showtimes_keyed_on_the_film_id(self):
        self.assertEqual([(s["eventId"], s["start"]) for s in self.shows],
                         [("202769", "2026-09-05T14:00:00+03:00"), ("1415167", "2026-09-06T14:00:00+03:00"),
                          ("105609", "2026-09-06T16:00:00+03:00"), ("1653971", "2026-09-11T20:30:00+03:00")])

    def test_a_closed_sale_is_a_showtime_and_not_sold_out(self):
        s = self.by_id["202769"][0]
        self.assertEqual((s["title"], s["soldOut"]), ("SÁTÁNTANGÓ", False))
        self.assertTrue(s["url"].startswith("https://kauppa.kavi.fi/fi/events/pwdg/event_buybox/show/"))

    def test_the_ticket_link_is_the_shows_own_and_the_film_page_is_the_fallback(self):
        self.assertEqual(self.by_id["1415167"][0]["url"],
                         "https://kauppa.kavi.fi/fi/events/pwdg/event_buybox/show/6a21c81415167")
        self.assertEqual(self.by_id["1653971"][0]["url"], f"{BASE}/elokuva/1653971/")

    def test_an_event_without_a_film_link_and_a_repeated_row_are_dropped(self):
        self.assertNotIn("9001", self.by_id)
        self.assertEqual(len(self.by_id["105609"]), 1)

    def test_the_show_shape(self):
        s = self.by_id["1415167"][0]
        self.assertEqual((s["title"], s["img"], s["price"], s["aud"], s["rating"], s["method"], s["lang"],
                          s["provider"], s["venue"], s["theatre"]),
                         ("PERSEPOLIS", "", "", "", "", "", "", "regina", "regina-helsinki", "Kino Regina"))

    def test_an_empty_window_parses_to_nothing(self):
        self.assertEqual(regina.parse_schedule(WINDOW_EMPTY), [])


class WindowTest(unittest.TestCase):
    def fetch(self, answers):
        calls = []

        def get(day):
            calls.append(day)
            return answers[day]
        pages = regina.fetch_schedule(today=__import__("datetime").date(2026, 9, 5), get=get, sleep=0)
        return calls, pages

    def test_windows_are_followed_until_one_is_empty(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            calls, pages = self.fetch({"2026-09-05": WINDOW_1, "2026-09-21": WINDOW_2, "2026-10-07": WINDOW_EMPTY})
        self.assertEqual(calls, ["2026-09-05", "2026-09-21", "2026-10-07"])
        self.assertEqual(len(pages), 3)
        shows = regina.parse_schedule("".join(pages))
        self.assertEqual([s["eventId"] for s in shows], ["202769", "1415167", "105609", "1653971", "139011"])
        self.assertIn("3 window(s), the last from 2026-10-07", out.getvalue())

    def test_a_window_without_a_next_day_ends_the_walk(self):
        with contextlib.redirect_stdout(io.StringIO()):
            calls, pages = self.fetch({"2026-09-05": WINDOW_1.replace("loadNextTwoWeeks('2026-09-21', this)", "")})
        self.assertEqual(calls, ["2026-09-05"])

    def test_a_next_day_that_does_not_advance_ends_the_walk(self):
        with contextlib.redirect_stdout(io.StringIO()):
            calls, _ = self.fetch({"2026-09-05": WINDOW_1.replace("'2026-09-21'", "'2026-09-05'")})
        self.assertEqual(calls, ["2026-09-05"])

    def test_the_walk_is_bounded(self):
        # A server that always offers another window is cut off at MAX_PAGES.
        pages_seen = []

        def get(day):
            pages_seen.append(day)
            nxt = f"2026-12-{len(pages_seen):02d}"
            return WINDOW_2.replace("'2026-10-07'", f"'{nxt}'")
        with contextlib.redirect_stdout(io.StringIO()):
            pages = regina.fetch_schedule(today=__import__("datetime").date(2026, 9, 5), get=get, sleep=0)
        self.assertEqual(len(pages), 4)                      # the literal bound, not the constant


class DetailsTest(unittest.TestCase):
    def test_rating_runtime_series_gauge_and_synopsis(self):
        d = regina.details(ONE_BATTLE)
        self.assertEqual((d["rating"], d["len"], d["method"]), ("K-12", "162", "PAUL THOMAS ANDERSON · 70 mm"))
        self.assertNotIn("lang", d)                                   # "ei tekstitystä"
        self.assertEqual(d["_syn"], "Loistokkaalta 70 mm:n kopiolta nähtävä One Battle After Another (2025) "
                                    "on harvinaista ison kankaan poliittista toimintaelokuvaa.")
        self.assertNotIn("auteur", d["_syn"])                         # the essay after *** is not the synopsis
        self.assertNotIn("Pynchon", d["_syn"])                        # Lisätieto is never appended

    def test_subtitles_series_filter_and_dedupe(self):
        d = regina.details(PERSEPOLIS)
        self.assertEqual((d["rating"], d["len"], d["lang"], d["method"]), ("K-16", "97", "FI-S, SV-S", "KESÄJAZZIT · 35 mm"))

    def test_no_rating_english_subtitles_and_dcp_dropped(self):
        d = regina.details(PLAIN)
        self.assertNotIn("rating", d)
        self.assertEqual(d["lang"], "EN-S")
        self.assertNotIn("method", d)

    def test_the_series_rule(self):
        self.assertEqual(regina.series_tag("PAUL THOMAS ANDERSON"), "PAUL THOMAS ANDERSON")
        self.assertEqual(regina.series_tag("TARR &amp; KRASZNAHORKAI"), "TARR & KRASZNAHORKAI")
        self.assertEqual(regina.series_tag("JATKOAIKA KESÄ 2026"), "")
        self.assertEqual(regina.series_tag("KURITTOMAT SUKUPOLVET: NUORISOA SUOMALAISESSA ELOKUVASSA"), "")
        self.assertEqual(regina.series_tag("50 VUOTTA SITTEN: ELOKUVAVUOSI 1976"), "")
        self.assertEqual(regina.series_tag("MARILYN MONROE 100 VUOTTA"), "MARILYN MONROE 100 VUOTTA")
        self.assertEqual(regina.series_tag("KESÄ"), "")
        # Each rule on its own: too long with few words, a colon in a short value.
        self.assertEqual(regina.series_tag("ELOKUVAHISTORIAN SUURET MESTARITEOKSET"), "")
        self.assertEqual(regina.series_tag("TEEMA: KESÄ"), "")

    def test_the_gauge_rule(self):
        for raw, want in (("35 mm", "35 mm"), ("70mm", "70 mm"), ("16 mm", "16 mm"), ("8 mm", "8 mm"),
                          ("DCP", ""), ("Digitaalinen kopio, 4K-restauroitu", ""), ("", "")):
            with self.subTest(raw=raw):
                self.assertEqual(regina.gauge_tag(raw), want)

    def test_the_age_alt_shapes(self):
        for alt, want in (("Ikäraja: K12", "K-12"), ("Ikäraja: K7", "K-7"), ("Ikäraja: K-18", "K-18"),
                          ("Ikäraja: S", "S"), ("Ikäraja: T", "S")):
            with self.subTest(alt=alt):
                self.assertEqual(regina.details(film_page(alt, "90 min", "", [], "", "", ""))["rating"], want)

    def test_nothing_on_the_page_is_nothing(self):
        self.assertEqual(regina.details("<html><body>Huolto</body></html>"), {})


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._fetch, self._sleep = regina.fetch, regina.time.sleep
        self.addCleanup(lambda: setattr(regina, "fetch", self._fetch))
        self.addCleanup(lambda: setattr(regina.time, "sleep", self._sleep))
        regina.time.sleep = lambda s: None
        self.calls = []

    def serve(self, answers):
        """answers: {url or (url, post body): html or Exception}."""
        def fetch(url, data=None, **kw):
            key = (url, data.decode("ascii")) if data else url
            self.calls.append(key)
            page = answers.get(key)
            if isinstance(page, Exception):
                raise page
            if page is None:
                raise RuntimeError(f"unexpected fetch {key}")
            return page.encode("utf-8")
        regina.fetch = fetch

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["regina"])
        return code, out.getvalue() + err.getvalue()

    def today(self):
        import datetime
        return datetime.datetime.now(regina.FI).date().isoformat()

    def films(self):
        return {f"{BASE}/elokuva/202769/": PLAIN, f"{BASE}/elokuva/1415167/": PERSEPOLIS,
                f"{BASE}/elokuva/105609/": PLAIN, f"{BASE}/elokuva/1653971/": ONE_BATTLE,
                f"{BASE}/elokuva/139011/": PLAIN}

    def test_a_full_run_publishes_the_venue_across_two_windows(self):
        self.serve({(SCHEDULE, f"getShowtimesMovies={self.today()}"): WINDOW_1,
                    (SCHEDULE, "getShowtimesMovies=2026-09-21"): WINDOW_2,
                    (SCHEDULE, "getShowtimesMovies=2026-10-07"): WINDOW_EMPTY, **self.films()})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        area = json.loads((run.OUT / "area-regina-helsinki.json").read_text())
        venues = json.loads((run.OUT / "venues-regina.json").read_text())
        self.assertEqual([s["eventId"] for s in area["shows"]], ["202769", "1415167", "105609", "1653971", "139011"])
        one = area["shows"][3]
        self.assertEqual((one["rating"], one["len"], one["method"], one["url"]),
                         ("K-12", "162", "PAUL THOMAS ANDERSON · 70 mm", f"{BASE}/elokuva/1653971/"))
        self.assertNotIn("_syn", area["shows"][0])
        self.assertEqual(venues["venues"], [{"id": "regina-helsinki", "name": "Kino Regina",
                                            "short": "Kino Regina", "city": "Helsinki"}])
        self.assertEqual((venues["status"], venues["pending"]), ("ok", []))
        self.assertEqual(self.calls[:3], [(SCHEDULE, f"getShowtimesMovies={self.today()}"),
                                          (SCHEDULE, "getShowtimesMovies=2026-09-21"),
                                          (SCHEDULE, "getShowtimesMovies=2026-10-07")])
        self.assertEqual(len(self.calls), 8)                 # three windows and five film pages
        self.assertIn("Kino Regina: 5 showtimes, 4 dates", log)
        self.assertIn("0 failures", log)

    PREV = {"generated": "2026-09-01T00:00:00+00:00", "dates": ["2026-09-01"],
            "horizon": "2026-09-01", "shows": [{"title": "Old", "start": "2026-09-01T12:00:00+03:00"}]}

    def serve_sequence(self, first_answers, rest):
        """The same POST answered differently on successive calls: `first_answers` in
        order for today's window, then `rest` for anything else."""
        queue = list(first_answers)

        def fetch(url, data=None, **kw):
            key = (url, data.decode("ascii")) if data else url
            self.calls.append(key)
            if key == (SCHEDULE, f"getShowtimesMovies={self.today()}") and queue:
                return queue.pop(0).encode("utf-8")
            page = rest.get(key)
            if isinstance(page, Exception):
                raise page
            if page is None:
                raise RuntimeError(f"unexpected fetch {key}")
            return page.encode("utf-8")
        regina.fetch = fetch

    def test_an_empty_first_window_is_asked_once_more_and_then_published(self):
        """2026-09-05, 16:57 UTC: one empty answer from a runner while the site listed 21
        rows to everyone else. One retry covers a single such answer."""
        self.serve_sequence([WINDOW_EMPTY, WINDOW_1],
                            {(SCHEDULE, "getShowtimesMovies=2026-09-21"): WINDOW_EMPTY, **self.films()})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        area = json.loads((run.OUT / "area-regina-helsinki.json").read_text())
        self.assertEqual(len(area["shows"]), 4)
        self.assertEqual(self.calls[:3], [(SCHEDULE, f"getShowtimesMovies={self.today()}")] * 2
                         + [(SCHEDULE, "getShowtimesMovies=2026-09-21")])
        self.assertIn("has no screenings: ", log)
        self.assertIn("asking once more", log)

    def test_an_empty_schedule_twice_fails_the_site_and_keeps_the_previous_file(self):
        (run.OUT / "area-regina-helsinki.json").write_text(json.dumps(self.PREV))
        self.serve_sequence([WINDOW_EMPTY, WINDOW_EMPTY], {})
        code, log = self.main()
        self.assertEqual(code, 1)
        self.assertIn("FAILED", log)
        self.assertIn("answered twice with no screenings", log)
        self.assertEqual(json.loads((run.OUT / "area-regina-helsinki.json").read_text()), self.PREV)
        self.assertFalse((run.OUT / "venues-regina.json").exists())
        self.assertNotIn(LISTING, self.calls)              # the listing is no evidence and is not read

    def test_a_challenge_shell_is_named_and_fails_the_site(self):
        (run.OUT / "area-regina-helsinki.json").write_text(json.dumps(self.PREV))
        shell = ('<html><head><meta http-equiv="refresh" content="0;url=/.well-known/sgcaptcha/?r=%2F">'
                 '</head><body></body></html>')
        self.serve_sequence([shell], {})
        code, log = self.main()
        self.assertEqual(code, 1)
        self.assertIn("challenged", log)
        self.assertEqual(len(self.calls), 1)               # no retry against a challenge
        self.assertEqual(json.loads((run.OUT / "area-regina-helsinki.json").read_text()), self.PREV)
        self.assertFalse(hasattr(regina, "EMPTY_VENUES_CONFIRMED"))

    def test_a_refused_schedule_fails_the_site(self):
        self.serve({(SCHEDULE, f"getShowtimesMovies={self.today()}"): RuntimeError("HTTP Error 403: Forbidden")})
        code, log = self.main()
        self.assertEqual(code, 1)
        self.assertIn("FAILED", log)

    def test_a_failing_film_page_costs_that_film_its_metadata_only(self):
        films = self.films()
        films[f"{BASE}/elokuva/1653971/"] = RuntimeError("HTTP Error 500")
        self.serve({(SCHEDULE, f"getShowtimesMovies={self.today()}"): WINDOW_1,
                    (SCHEDULE, "getShowtimesMovies=2026-09-21"): WINDOW_EMPTY, **films})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        area = json.loads((run.OUT / "area-regina-helsinki.json").read_text())
        by_id = {s["eventId"]: s for s in area["shows"]}
        self.assertEqual(by_id["1653971"]["len"], "")
        self.assertEqual(by_id["1415167"]["len"], "97")
        self.assertIn("film page 1653971 failed", log)


class RegistryAndPagesTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("regina")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Kino Regina", "kinoregina.fi", "buy", "regina", "cloud"))
        self.assertEqual(p["accent"], "#8A4854")
        self.assertEqual(sum(1 for q in registry.PROVIDERS if q["accent"] == p["accent"]), 1)
        self.assertEqual((VENUE["id"], VENUE["name"], VENUE["short"], VENUE["city"]),
                         ("regina-helsinki", "Kino Regina", "Kino Regina", "Helsinki"))
        self.assertEqual(SITE["base"], BASE)
        self.assertEqual(bp.label_of({**VENUE, "provider": "regina"}, {"regina": "Kino Regina"}), "Kino Regina")

    def test_the_committed_page_follows_the_theatre_template(self):
        fi = (ROOT / "teatteri" / "kino-regina-helsinki" / "index.html").read_text(encoding="utf-8")
        en = (ROOT / "en" / "theatre" / "kino-regina-helsinki" / "index.html").read_text(encoding="utf-8")
        orion = (ROOT / "teatteri" / "cinema-orion-helsinki" / "index.html").read_text(encoding="utf-8")
        for page in (fi, en):
            self.assertIn('href="https://kauppa.kavi.fi/fi/events/pwdg/event_buybox/show/', page)
        for marker in ('class="langseg"', 'class="cta"', '<h2 class="day">', '<p class="intro">',
                       'class="stub"', '<ul class="times">'):
            self.assertIn(marker, fi)
            self.assertIn(marker, orion)
        self.assertEqual(fi.count("<style"), orion.count("<style"))

    def test_the_helsinki_city_page_lists_the_cinema(self):
        city = (ROOT / "kaupunki" / "helsinki" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Kino Regina", city)
        self.assertIn("chain-regina", city)
        self.assertIn("14 teatteria", city)


if __name__ == "__main__":
    unittest.main()
