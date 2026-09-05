"""Korjaamo Kino through the Vista adapter: the schedule, the unknown rating, the bare hall.

The fixtures are cut from korjaamokino.fi's own `/xml/Schedule/` and `/xml/Events/`
answers of 2026-09-05, trimmed to three shows and one show from a theatre the site does
not list. The parser is the one Savon Kinot ran on; what Korjaamo added is the "Ei
tiedossa" rating, an auditorium called only "Sali", a festival in EventSeries and a
language the name table did not know.
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
import strands
import vista

ROOT = _ctx.ROOT
BASE = "https://korjaamokino.fi"


def show(sid, eid, title, start_local, start_utc, rating, label, series="", theatre="1045",
         aud="Sali", spoken=("suomi", "fi"), subs=(), length="88", genres="Dokumentti"):
    def lang(tag, name, iso):
        return (f"<{tag}><Name>{name}</Name><NameInLanguage>{name}</NameInLanguage>"
                f"<ISOTwoLetterCode>{iso}</ISOTwoLetterCode></{tag}>")
    sub_xml = "".join(lang(f"SubtitleLanguage{n}", name, iso)
                      for n, (name, iso) in enumerate(subs, 1))
    return f"""
    <Show>
      <ID>{sid}</ID>
      <dttmShowStart>{start_local}</dttmShowStart>
      <dttmShowStartUTC>{start_utc}</dttmShowStartUTC>
      <EventID>{eid}</EventID>
      <Title>{title}</Title>
      <OriginalTitle>{title}</OriginalTitle>
      <ProductionYear>2026</ProductionYear>
      <LengthInMinutes>{length}</LengthInMinutes>
      <Rating>{rating}</Rating>
      <RatingLabel>{label}</RatingLabel>
      <EventType>Movie</EventType>
      <Genres>{genres}</Genres>
      <TheatreID>{theatre}</TheatreID>
      <Theatre>Korjaamo Kino</Theatre>
      <TheatreAuditorium>{aud}</TheatreAuditorium>
      <PresentationMethod>2D</PresentationMethod>
      <EventSeries>{series}</EventSeries>
      <ShowURL>http://korjaamokino.fi/websales/show/{sid}</ShowURL>
      <EventURL>https://korjaamokino.fi/event/{eid}</EventURL>
      {lang("SpokenLanguage", *spoken)}
      {sub_xml}
      <Images />
    </Show>"""


SCHEDULE = f"""<?xml version="1.0" encoding="utf-8"?>
<Schedule xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <PubDate>2026-09-05T00:00:00+00:00</PubDate>
  <Shows>{show("168058", "5202", "Päivien lumo", "2026-09-07T15:00:00", "2026-09-07T12:00:00Z",
                "Sallittu", "S")}
    {show("168094", "5193", "HelAFF: Fez Summer 55", "2026-09-10T17:30:00", "2026-09-10T14:30:00Z",
          "Ei tiedossa", "", series="HelAFF", spoken=("useita kieliä", ""),
          subs=(("englanti", "en"), ("arabia", "")), length="115", genres="Draama")}
    {show("168059", "5204", "Presidentin Kyyditys", "2026-09-07T17:15:00", "2026-09-07T14:15:00Z",
          "K-12", "K-12", subs=(("ruotsi", "sv"),), length="87", genres="Komedia, Draama")}
    {show("168999", "5999", "Not Ours", "2026-09-07T20:00:00", "2026-09-07T17:00:00Z",
          "K-16", "K-16", theatre="9999", aud="Joensuu, Tapio 4")}
  </Shows>
</Schedule>
"""

EVENTS = """<?xml version="1.0" encoding="utf-8"?>
<Events xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Event>
    <ID>5202</ID>
    <Title>Päivien lumo</Title>
    <ShortSynopsis>Lyhyt.</ShortSynopsis>
    <Synopsis>&lt;p&gt;Dokumentti kolmesta kesästä, jotka muuttivat kaiken.&lt;/p&gt;</Synopsis>
  </Event>
  <Event>
    <ID>5193</ID>
    <Title>HelAFF: Fez Summer 55</Title>
    <Synopsis>Fez, kesä 1955.</Synopsis>
  </Event>
</Events>
"""

SITE = vista.SITES[0]
VENUE = SITE["venues"][0]


class RatingTest(unittest.TestCase):
    def test_not_known_is_no_rating(self):
        for v in ("Ei tiedossa", "ei tiedossa", "  Ei tiedossa ", "", None):
            with self.subTest(v=v):
                self.assertEqual(vista._rating(v), "")

    def test_the_savon_kinot_shapes_still_normalise(self):
        self.assertEqual(vista._rating("K-7 (4)"), "K-7")
        self.assertEqual(vista._rating("Sallittu kaikenikäisille"), "S")
        self.assertEqual(vista._rating("Sallittu"), "S")
        self.assertEqual(vista._rating("K-12"), "K-12")
        self.assertEqual(vista._rating("K16"), "K-16")


class AuditoriumTest(unittest.TestCase):
    def aud(self, raw):
        import xml.etree.ElementTree as ET
        return vista._aud(ET.fromstring(f"<Show><TheatreAuditorium>{raw}</TheatreAuditorium></Show>"),
                          VENUE)

    def test_a_bare_hall_is_no_room(self):
        self.assertEqual(self.aud("Sali"), "")
        self.assertEqual(self.aud("Korjaamo Kino, Sali"), "")
        self.assertEqual(self.aud("Korjaamo Kino"), "")

    def test_a_named_room_survives(self):
        self.assertEqual(self.aud("Joensuu, Tapio 4"), "Tapio 4")
        self.assertEqual(self.aud("Sali 2"), "Sali 2")


class ScheduleTest(unittest.TestCase):
    def setUp(self):
        self.by_venue = vista.parse_schedule(SCHEDULE, SITE, SITE["venues"])
        self.shows = {s["eventId"]: s for s in self.by_venue["korjaamo-helsinki"]}

    def test_only_the_listed_theatre_is_kept(self):
        self.assertEqual(set(self.by_venue), {"korjaamo-helsinki"})
        self.assertEqual(sorted(self.shows), ["5193", "5202", "5204"])

    def test_the_unknown_rating_is_blank_and_the_known_ones_are_kept(self):
        self.assertEqual({k: s["rating"] for k, s in self.shows.items()},
                         {"5202": "S", "5193": "", "5204": "K-12"})

    def test_start_is_the_utc_time_in_helsinki(self):
        self.assertEqual(self.shows["5202"]["start"], "2026-09-07T15:00:00+03:00")
        self.assertEqual(self.shows["5193"]["start"], "2026-09-10T17:30:00+03:00")

    def test_the_hall_is_blank_and_the_ticket_link_is_https(self):
        for s in self.shows.values():
            self.assertEqual(s["aud"], "")
            self.assertEqual(s["url"], f"https://korjaamokino.fi/websales/show/{s['url'].rsplit('/', 1)[1]}")
            self.assertEqual(s["theatre"], "Korjaamo Kino")
            self.assertEqual((s["img"], s["price"], s["soldOut"], s["provider"]),
                             ("", "", False, "korjaamo"))

    def test_the_festival_lands_in_method_with_the_client_separator(self):
        self.assertEqual(self.shows["5193"]["method"], "2D · HelAFF")
        self.assertEqual(self.shows["5202"]["method"], "2D")

    def test_languages(self):
        self.assertEqual(self.shows["5202"]["lang"], "FI-A")
        self.assertEqual(self.shows["5204"]["lang"], "FI-A, SV-S")
        # "useita kieliä" has no code and no tag; Arabic is mapped by its Finnish name.
        self.assertEqual(self.shows["5193"]["lang"], "EN-S, AR-S")

    def test_metadata(self):
        s = self.shows["5193"]
        self.assertEqual((s["title"], s["len"], s["genres"], s["original"]),
                         ("HelAFF: Fez Summer 55", "115", "Draama", "HelAFF: Fez Summer 55"))

    def test_synopses_strip_markup(self):
        self.assertEqual(vista.synopses(EVENTS),
                         {"5202": "Dokumentti kolmesta kesästä, jotka muuttivat kaiken.",
                          "5193": "Fez, kesä 1955."})
        self.assertEqual(vista.synopses("not xml"), {})


class StrandTest(unittest.TestCase):
    def test_the_festival_prefix_comes_off_a_feature(self):
        self.assertEqual(strands.split("HelAFF: Fez Summer 55"), ("Fez Summer 55", "HelAFF"))

    def test_a_short_programme_keeps_its_title(self):
        self.assertEqual(strands.split("HelAFF Short Films 1"), ("HelAFF Short Films 1", ""))

    def test_the_series_tag_is_not_doubled(self):
        s = {"title": "HelAFF: Fez Summer 55", "method": "2D · HelAFF"}
        self.assertTrue(strands.apply(s))
        self.assertEqual((s["title"], s["method"]), ("Fez Summer 55", "2D · HelAFF"))


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get, self._sleep = vista.get, vista.time.sleep
        self.addCleanup(lambda: setattr(vista, "get", self._get))
        self.addCleanup(lambda: setattr(vista.time, "sleep", self._sleep))
        vista.time.sleep = lambda s: None
        self.calls = []

    def serve(self, pages):
        def get(url, tries=3, timeout=40):
            self.calls.append(url)
            page = pages.get(url)
            if isinstance(page, Exception):
                raise page
            if page is None:
                raise RuntimeError(f"unexpected fetch {url}")
            return page
        vista.get = get

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["vista"])
        return code, out.getvalue() + err.getvalue()

    EVENTS_URL = f"{BASE}/xml/Events/"
    SCHEDULE_URL = f"{BASE}/xml/Schedule/?area=1007&nrOfDays=31"

    def test_a_full_run_publishes_the_venue(self):
        self.serve({self.EVENTS_URL: EVENTS, self.SCHEDULE_URL: SCHEDULE})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        area = json.loads((run.OUT / "area-korjaamo-helsinki.json").read_text())
        venues = json.loads((run.OUT / "venues-korjaamo.json").read_text())
        self.assertEqual([s["title"] for s in area["shows"]],
                         ["Päivien lumo", "Presidentin Kyyditys", "Fez Summer 55"])
        fez = area["shows"][2]
        self.assertEqual((fez["rating"], fez["method"], fez["aud"]), ("", "2D · HelAFF", ""))
        self.assertNotIn("_syn", area["shows"][0])
        self.assertEqual(area["dates"], ["2026-09-07", "2026-09-10"])
        self.assertEqual(venues["venues"], [{"id": "korjaamo-helsinki", "name": "Korjaamo Kino",
                                            "short": "Korjaamo Kino", "city": "Helsinki"}])
        self.assertEqual((venues["status"], venues["stale"], venues["pending"]), ("ok", [], []))
        self.assertEqual(self.calls, [self.EVENTS_URL, self.SCHEDULE_URL])
        self.assertIn("Korjaamo Kino: 3 showtimes, 2 dates", log)
        self.assertIn("0 failures", log)

    def test_a_refused_schedule_fails_the_site_and_keeps_the_previous_file(self):
        prev = {"generated": "2026-09-01T00:00:00+00:00", "dates": ["2026-09-01"],
                "horizon": "2026-09-01", "shows": [{"title": "Old", "start": "2026-09-01T12:00:00+03:00"}]}
        (run.OUT / "area-korjaamo-helsinki.json").write_text(json.dumps(prev))
        self.serve({self.EVENTS_URL: EVENTS, self.SCHEDULE_URL: RuntimeError("HTTP Error 403: Forbidden")})
        code, log = self.main()
        self.assertEqual(code, 1)
        self.assertIn("FAILED", log)
        self.assertEqual(json.loads((run.OUT / "area-korjaamo-helsinki.json").read_text()), prev)
        self.assertFalse((run.OUT / "venues-korjaamo.json").exists())

    def test_missing_events_cost_synopses_and_not_the_schedule(self):
        self.serve({self.EVENTS_URL: RuntimeError("HTTP Error 500"), self.SCHEDULE_URL: SCHEDULE})
        code, log = self.main()
        self.assertEqual(code, 0, log)
        area = json.loads((run.OUT / "area-korjaamo-helsinki.json").read_text())
        self.assertEqual(len(area["shows"]), 3)
        self.assertIn("Events unavailable", log)


class RegistryAndPagesTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("korjaamo")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Korjaamo Kino", "korjaamokino.fi", "buy", "vista", "cloud"))
        self.assertEqual(p["accent"], "#C07E7E")
        self.assertEqual(sum(1 for q in registry.PROVIDERS if q["accent"] == p["accent"]), 1)
        self.assertEqual((VENUE["id"], VENUE["name"], VENUE["short"], VENUE["city"],
                          VENUE["theatre"], VENUE["area"]),
                         ("korjaamo-helsinki", "Korjaamo Kino", "Korjaamo Kino", "Helsinki",
                          "1045", "1007"))
        self.assertEqual(SITE["base"], BASE)
        self.assertEqual(bp.label_of({**VENUE, "provider": "korjaamo"}, {"korjaamo": "Korjaamo Kino"}),
                         "Korjaamo Kino")            # the chain prefix collapses, no doubling

    def test_the_committed_page_follows_the_theatre_template(self):
        fi = (ROOT / "teatteri" / "korjaamo-kino-helsinki" / "index.html").read_text(encoding="utf-8")
        en = (ROOT / "en" / "theatre" / "korjaamo-kino-helsinki" / "index.html").read_text(encoding="utf-8")
        orion = (ROOT / "teatteri" / "cinema-orion-helsinki" / "index.html").read_text(encoding="utf-8")
        for page in (fi, en):
            self.assertIn('href="https://korjaamokino.fi/websales/show/', page)
            self.assertNotIn("Ei tiedossa", page)
        for marker in ('class="langseg"', 'class="cta"', '<h2 class="day">', '<p class="intro">',
                       'class="stub"', '<ul class="times">'):
            self.assertIn(marker, fi)
            self.assertIn(marker, orion)
        self.assertEqual(fi.count("<style"), orion.count("<style"))

    def test_the_helsinki_city_page_lists_the_cinema(self):
        city = (ROOT / "kaupunki" / "helsinki" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Korjaamo Kino", city)
        self.assertIn("chain-korjaamo", city)


if __name__ == "__main__":
    unittest.main()
