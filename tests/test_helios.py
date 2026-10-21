"""The Kino Helios reader: Linked Events by place, the whole house, three fields to filter.

The fixtures are the API's own event shape as read on 2026-10-21, cut to the fields the
reader touches. Two rows everywhere there is a loop.

What they exist to prove:

- **All three fields are needed to pick this cinema out.** The place held 21 film events
  over 90 days: 12 Kino Helios and 9 in other strands of the same house, `HopeaCine`,
  `Yleisön suosikit` and `Joululomaleffa`.
- **`start_time` is a UTC instant**, published as the same moment in Helsinki. A date alone
  or a clock with no offset is refused rather than published in a guessed zone.
- **The age limit is a suffix on the title.** It goes to `rating`, and the published title
  is the film's own, because the title is the key the combined city view merges on.
- **The language comes from the description**, with the rule the house's own event record
  was read with.
- **An empty result is not evidence of an empty programme**, because the API answers the
  whole house.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

import _ctx                                                # noqa: F401
import helios as H
import registry
import run


SITE = H.SITES[0]
VENUE = SITE["venues"][0]["id"]
URL = SITE["base"] + SITE["path"]
API = "https://api.hel.fi/linkedevents/v1"
TODAY = datetime.date(2026, 10, 21)
TICKET = "https://www.lippu.fi/event/kino-helios-esittaa-kino-helios-kerro-kaikille-malmitalo-22207030/"
FACTS = "<p>Ikäraja: 12 <br>Kesto: 112 min <br>Ensi-ilta: 09.10.2026 <br>Kieli: suomi <br>Tekstitys: suomi</p>"
BLURB = ("Kerro kaikille on voimaelokuva Amanda Aaltosesta, joka kieltäytyy alistumasta "
         "hänelle varattuun köyhän naisen ankeaan kohtaloon ja etsii huimapäisesti onneaan "
         "maailmalta.")


def utc(iso):
    """A Helsinki wall clock -> the API's `...Z` string."""
    dt = datetime.datetime.fromisoformat(iso).replace(tzinfo=H.FI)
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def event(name="Kerro kaikille (12) – Kino Helios", start="2026-10-21T18:00", id_="kulke:68849",
          place="tprek:8740", keywords=("kulke:205", "kulke:29", "kulke:42"), ticket=TICKET,
          price="9 €", facts=FACTS, blurb=BLURB, status="EventRescheduled", start_time=None,
          extra=None):
    return {
        "id": id_, "@id": f"{API}/event/{id_}/", "data_source": "kulke",
        "name": {"fi": name, "sv": name, "en": name},
        "location": {"@id": f"{API}/place/{place}/"},
        "keywords": [{"@id": f"{API}/keyword/{k}/"} for k in keywords],
        "start_time": utc(start) if start_time is None else start_time,
        "end_time": utc((datetime.datetime.fromisoformat(start)
                         + datetime.timedelta(minutes=112)).isoformat()),
        "event_status": status, "location_extra_info": extra, "in_language": [],
        "offers": [{"is_free": False, "offer_price_groups": [], "description": None,
                    "price": {"fi": price, "sv": price, "en": price},
                    "info_url": {"fi": ticket, "sv": ticket, "en": ticket}}],
        "short_description": {"fi": blurb, "sv": blurb, "en": blurb},
        "description": {"fi": f"<p>{blurb}</p>{facts}"},
        "images": [{"url": "http://www.malmitalo.fi/EventPic_792081.jpg",
                    "license": "event_only"}],
    }


def second(day="2026-10-22"):
    return event(name="Hetki ennen valoa (7) – Kino Helios", start=f"{day}T15:00",
                 id_="kulke:68851")


class FilterTest(unittest.TestCase):
    def rows(self, *events):
        return H.rows(SITE, list(events or (event(),)), TODAY)

    def test_every_matching_row_becomes_a_show(self):
        shows, report = self.rows(event(), second())
        self.assertEqual((report["rows"], report["mine"]), (2, 2))
        self.assertEqual([(s["title"], s["start"]) for s in shows], [
            ("Kerro kaikille", "2026-10-21T18:00:00+03:00"),
            ("Hetki ennen valoa", "2026-10-22T15:00:00+03:00"),
        ])

    def test_the_other_strands_of_the_house_never_publish(self):
        for name in ("HopeaCine: Presidentin kyyditys", "Yleisön suosikit: Sydäntalvi",
                     "Teräsleidit – kuin viimeistä päivää – Yleisön suosikit",
                     "Joululomaleffa: Tuhkimo (S)", "Kappale kauneinta Suomea – Doc Helios"):
            with self.subTest(name=name):
                shows, report = self.rows(event(name=name), event())
                self.assertEqual(report["mine"], 1)
                self.assertEqual([s["title"] for s in shows], ["Kerro kaikille"])

    def test_another_place_or_no_film_keyword_never_publishes(self):
        self.assertEqual(self.rows(event(place="tprek:7255"))[0], [])
        self.assertEqual(self.rows(event(keywords=("kulke:205", "kulke:42")))[0], [])


class ClockTest(unittest.TestCase):
    def test_the_utc_instant_is_published_as_helsinki_local(self):
        s = H.rows(SITE, [event(start_time="2026-10-21T15:00:00Z")], TODAY)[0][0]
        self.assertEqual(s["start"], "2026-10-21T18:00:00+03:00")

    def test_a_winter_instant_keeps_its_own_offset(self):
        s = H.rows(SITE, [event(start_time="2026-10-28T13:00:00Z")], TODAY)[0][0]
        self.assertEqual(s["start"], "2026-10-28T15:00:00+02:00")

    def test_a_date_alone_or_a_clock_with_no_offset_is_counted_and_left_out(self):
        for value in ("2026-10-22", "2026-10-22T15:00:00", "soon", None):
            with self.subTest(value=value):
                bad = event(); bad["start_time"] = value
                shows, report = H.rows(SITE, [bad, second()], TODAY)
                self.assertEqual(([s["title"] for s in shows], report["unreadable"]),
                                 (["Hetki ennen valoa"], 1))


class FieldTest(unittest.TestCase):
    def one(self, **kw):
        (s,), _ = H.rows(SITE, [event(**kw)], TODAY)
        return s

    def test_the_age_suffix_becomes_the_rating_and_leaves_the_title(self):
        for title, want in (("Hetki ennen valoa (7)", ("Hetki ennen valoa", "K-7")),
                            ("Kerro kaikille (12)", ("Kerro kaikille", "K-12")),
                            ("Pirjo i Sverige (S)", ("Pirjo i Sverige", "S")),
                            ("Heart of the Beast", ("Heart of the Beast", ""))):
            with self.subTest(title=title):
                self.assertEqual(H.split_title(title), want)

    def test_a_title_that_is_only_a_bracket_is_left_alone(self):
        self.assertEqual(H.split_title("(12)"), ("(12)", ""))

    def test_the_title_merges_with_the_same_film_at_other_chains(self):
        """The combined city view keys on the title. A title carrying `(12)` or the
        strand's name would be a second film."""
        s = self.one()
        self.assertEqual((s["title"], s["rating"]), ("Kerro kaikille", "K-12"))

    def test_no_runtime_is_published_from_the_end_time_or_the_description(self):
        self.assertEqual(self.one()["len"], "")

    def test_the_offer_amount_is_not_published_as_the_price(self):
        """The house gave its tariff as "alkaen 9 EUR", a floor."""
        self.assertEqual(self.one(price="9 €")["price"], "")

    def test_the_description_names_the_audio_and_the_subtitles(self):
        self.assertEqual(self.one()["lang"], "FI-A, FI-S")
        tony = "<p>Kesto: 109 min <br>Kieli: englanti <br>Tekstitys: suomi, ruotsi</p>"
        self.assertEqual(self.one(facts=tony)["lang"], "EN-A, FI-S, SV-S")

    def test_a_dubbed_film_says_spoken_in_finnish(self):
        # Unohdettu saari, 2026-10-21.
        dub = "<p>Kesto: 109 min<br>Ensi-ilta: 09.10.2026<br>Kieli: puhuttu suomeksi</p>"
        self.assertEqual(self.one(facts=dub)["lang"], "FI-A")

    def test_what_the_description_does_not_state_plainly_is_left_out(self):
        for facts in ("<p>Kesto: 102 min</p>", "<p>Kieli: dari</p>", ""):
            with self.subTest(facts=facts):
                self.assertEqual(self.one(facts=facts)["lang"], "")

    def test_a_sold_out_name_sets_the_state_and_leaves_the_title(self):
        s = self.one(name="LOPPUUN MYYTY Kerro kaikille (12) – Kino Helios")
        self.assertEqual((s["title"], s["rating"], s["soldOut"]),
                         ("Kerro kaikille", "K-12", True))
        self.assertFalse(self.one()["soldOut"])

    def test_a_cancelled_or_postponed_row_is_counted_and_left_out(self):
        for kw in ({"name": "Kerro kaikille (12) PERUTTU – Kino Helios"},
                   {"status": "EventCancelled"}, {"status": "EventPostponed"}):
            with self.subTest(**kw):
                shows, report = H.rows(SITE, [event(**kw), second()], TODAY)
                self.assertEqual(([s["title"] for s in shows], report["cancelled"]),
                                 (["Hetki ennen valoa"], 1))

    def test_the_room_is_published_only_where_the_row_names_one(self):
        self.assertEqual(self.one()["aud"], "")
        self.assertEqual(self.one(extra={"fi": "Pieni sali"})["aud"], "Pieni sali")

    def test_a_finnish_blurb_is_declared_finnish(self):
        self.assertEqual(self.one()["_syn"], {"fi": BLURB})
        self.assertNotIn("_syn", self.one(blurb=""))

    def test_the_show_shape(self):
        s = self.one()
        self.assertEqual((s["provider"], s["venue"], s["method"], s["original"], s["genres"],
                          s["img"]), ("helios", VENUE, "", "", "", ""))
        self.assertEqual((s["theatre"], s["eventId"], s["url"]),
                         ("Kino Helios", "kulke:68849", TICKET))


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get, self._pause = H.get_text, H.PAUSE
        self.addCleanup(lambda: setattr(H, "get_text", self._get))
        self.addCleanup(lambda: setattr(H, "PAUSE", self._pause))
        H.PAUSE = 0
        self.calls = []
        # Dated from today, so the rows stay ahead of the run whenever the suite runs.
        self.today = datetime.datetime.now(H.FI).date()
        day = lambda n: (self.today + datetime.timedelta(days=n)).isoformat()
        self.rows = [event(start=f"{day(1)}T18:00"), second(day(2))]

    def serve(self, *pages):
        """Each page answers one request in turn; an exception is raised instead."""
        def get_text(url, **kw):
            self.calls.append(url)
            page = pages[len(self.calls) - 1]
            if isinstance(page, Exception):
                raise page
            return json.dumps(page)
        H.get_text = get_text

    def page(self, events, nxt=None):
        return {"meta": {"count": len(events), "next": nxt, "previous": None},
                "data": events}

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["helios", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def published(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))["shows"]

    def keep(self):
        kept = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
                "horizon": "2026-10-20",
                "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(kept), encoding="utf-8")

    def test_the_site_publishes_from_one_get_by_place_and_window(self):
        self.serve(self.page(self.rows + [event(name="HopeaCine: Lapin sota")]))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        (url,) = self.calls
        self.assertTrue(url.startswith(URL + "?"), url)
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        self.assertEqual(q, {"location": "tprek:8740", "start": self.today.isoformat(),
                             "end": (self.today + datetime.timedelta(days=H.HORIZON)).isoformat(),
                             "page_size": "100", "sort": "start_time"})
        self.assertEqual([(s["title"], s["lang"]) for s in self.published()],
                         [("Kerro kaikille", "FI-A, FI-S"), ("Hetki ennen valoa", "FI-A, FI-S")])

    def test_the_next_page_is_followed_and_asked_of_the_declared_host(self):
        nxt = "https://elsewhere.example/linkedevents/v1/event/?location=tprek%3A8740&page=2"
        self.serve(self.page(self.rows[:1], nxt), self.page(self.rows[1:]))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls[1], URL + "?location=tprek%3A8740&page=2")
        self.assertEqual(len(self.published()), 2)

    def test_a_place_past_the_page_cap_fails_and_keeps_the_previous_file(self):
        """The listing carries the schedule, so its front alone is not published."""
        self.keep()
        more = f"{URL}?page=2"
        self.serve(*[self.page(self.rows, more)] * H.MAX_PAGES)
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("more than", log)
        self.assertEqual(len(self.calls), H.MAX_PAGES)
        self.assertEqual(self.published()[0]["title"], "Yesterday")

    def test_a_payload_with_no_row_of_this_cinema_fails_and_keeps_the_previous_file(self):
        """The API answers the whole house, so this is not evidence of a dark week."""
        self.keep()
        self.serve(self.page([event(name="HopeaCine: Lapin sota"),
                              event(name="Yleisön suosikit: Sydäntalvi")]))
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no Kino Helios row", log)
        self.assertEqual(self.published()[0]["title"], "Yesterday")

    def test_a_refused_request_keeps_the_previous_file(self):
        self.keep()
        self.serve(RuntimeError("502 refused"))
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertEqual(self.published()[0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("helios")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Kino Helios", "malmitalo.fi", "buy", "helios", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == p["accent"]), 1)

    def test_the_site_names_the_host_it_is_read_from(self):
        self.assertEqual(SITE["base"], "https://api.hel.fi")
        self.assertNotIn("reads", SITE)

    def test_the_three_filter_fields_are_declared(self):
        self.assertEqual((SITE["place"], SITE["keyword"], SITE["strand"]),
                         ("tprek:8740", "kulke:29", "Kino Helios"))


if __name__ == "__main__":
    unittest.main()
