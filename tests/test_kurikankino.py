"""The Kurikan Kino reader: one front page, one `li.elokuva-thumb` per film.

The fixtures are the markup as read on 2026-10-21 (issue #8), cut to the smallest shape
that still exercises a rule, with two cards and two times wherever there is a loop.

What they exist to prove:

- **The stamp is the local clock written as UTC**, so a row's year comes from it and the
  row stands only where the stamp and the printed day, weekday and clock agree.
- **Every time is printed twice**, in the card and in its mobile copy, and is one row.
- **A coming-soon card and the gift card tile are not films**, and no poster of the site's
  own is published.
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import kurikankino as K
import registry
import run

SITE = K.SITES[0]
BASE = SITE["base"]
VENUE = SITE["venues"][0]["id"]
LISTING = BASE + SITE["listing"]
WD = ("ma", "ti", "ke", "to", "pe", "la", "su")


def stamp(d, clock):
    """The site's stamp: the local clock's fields encoded as a UTC instant."""
    h, m = (int(x) for x in clock.split(":"))
    return int(datetime.datetime(d.year, d.month, d.day, h, m,
                                 tzinfo=datetime.timezone.utc).timestamp())


def span(d, clock, printed=None):
    shown = printed or f"{WD[d.weekday()]} {d.day}.{d.month}. {clock}"
    return f'<span esitysaika="{stamp(d, clock)}" class="elokuva-aika"> {shown} </span>'


def card(slug="kerro-kaikille", title="Kerro Kaikille", age="12", times=(), price="14 €",
         hours="1", mins="52"):
    """One film card in the order the live page renders it, the times printed twice."""
    spans = " ".join(span(*t) for t in times)
    return (f'<li class="elokuva-thumb"> <a class="elokuva-linkki" '
            f'href="{BASE}/elokuvat/{slug}/"> <div class="elokuva-thumb-content" '
            f'style="background-image: url({BASE}/wordpress/wp-content/uploads/x-565x424.jpg"> '
            f'<div class="elokuva-ajat-ja-hinta"> <div class="elokuva-ajat"> {spans} </div> '
            f'<div class="hinta-ja-kesto"> <span class="kesto"> <strong>{hours}</strong> h '
            f'<strong>{mins}</strong> min </span> <span class="hinta">{price}</span> </div> '
            f'</div> <div class="elokuva-nimi"> {title}<span class="ikaraja ikaraja-{age}"> '
            f'{age.upper()}</span> </div> </div> <div class="elokuva-ajat mobiili '
            f'hide-for-large-up"> {spans} </div> </a> </li>')


COMING = (f'<li class="elokuva-thumb"> <a href="{BASE}/elokuvat/yon-lapsi/"> '
          f'<div class="elokuva-thumb-content"> <div class="elokuva-nimi">Yön Lapsi'
          f'<span class="elokuva-tulossa-vk"> vk 45</span></div> </div> </a> </li>')
GIFT = (f'<li class="elokuva-thumb"> <a class="elokuva-linkki" href="{BASE}/lahjakortit/"> '
        f'<div class="elokuva-thumb-content"> <div class="elokuva-nimi joulu">Lahjakortit'
        f'</div> </div> </a> </li>')


def page(*cards):
    return '<html><body><ul class="elokuvat">' + "".join(cards) + "</ul></body></html>"


OCT21, OCT22, OCT26 = (datetime.date(2026, 10, d) for d in (21, 22, 26))
LIVE = page(card(times=((OCT21, "20:00"), (OCT22, "20:00"))),
            card("pikku-kummitus-lapanen-keppostelee", "Pikku Kummitus Lapanen Keppostelee",
                 "s", ((OCT21, "18:00"), (OCT26, "17:30")), "13 €", "1", "5"),
            COMING, GIFT)


class CardTest(unittest.TestCase):

    def test_each_distinct_time_of_every_film_card_is_one_row(self):
        shows, report = K.rows(SITE, LIVE)
        self.assertEqual([(s["start"], s["title"]) for s in shows],
                         [("2026-10-21T18:00:00+03:00", "Pikku Kummitus Lapanen Keppostelee"),
                          ("2026-10-21T20:00:00+03:00", "Kerro Kaikille"),
                          ("2026-10-22T20:00:00+03:00", "Kerro Kaikille"),
                          # Summer time ends in Finland on 25.10.
                          ("2026-10-26T17:30:00+02:00", "Pikku Kummitus Lapanen Keppostelee")])
        self.assertEqual((report["films"], report["coming"]), (2, 1))

    def test_the_fields_a_row_carries(self):
        shows, _ = K.rows(SITE, LIVE)
        first, second = shows[1], shows[0]
        self.assertEqual((first["rating"], first["len"], first["price"], first["eventId"],
                          first["url"], first["img"]),
                         ("K-12", "112", "14€", "kerro-kaikille",
                          f"{BASE}/elokuvat/kerro-kaikille/", ""))
        self.assertEqual((second["rating"], second["len"], second["price"]), ("S", "65", "13€"))

    def test_a_stamp_that_disagrees_with_the_print_is_left_out(self):
        bad = card(times=((OCT21, "20:00"), (OCT22, "20:00", "ke 22.10. 20:00")))
        shows, report = K.rows(SITE, page(bad))
        self.assertEqual([s["start"][:16] for s in shows], ["2026-10-21T20:00"])
        self.assertEqual(report["disagree"], 1)

    def test_a_price_with_a_condition_publishes_none(self):
        shows, report = K.rows(SITE, page(card(times=((OCT21, "20:00"),),
                                               price="14 € / 10 € lapset")))
        self.assertEqual(shows[0]["price"], "")
        self.assertEqual(report["no_price"], 1)


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get = K.get_text
        self.addCleanup(lambda: setattr(K, "get_text", self._get))
        self.calls = []

    def serve(self, body):
        def get_text(url, **kw):
            self.calls.append(url)
            if isinstance(body, Exception):
                raise body
            return body
        K.get_text = get_text

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["kurikankino", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def soon(self, days):
        """run.main reads the real clock, so a fixture dated in September would go stale."""
        return datetime.datetime.now(K.FI).date() + datetime.timedelta(days=days)

    def kept(self):
        doc = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
               "horizon": "2026-10-20",
               "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(doc), encoding="utf-8")

    def after(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))

    def test_the_site_publishes_from_one_request(self):
        self.serve(page(card(times=((self.soon(1), "19:00"), (self.soon(2), "19:00"))),
                        card("lapin-sota", "Lapin Sota", "16",
                             ((self.soon(2), "14:00"),), "15 €", "2", "35"), COMING))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls, [LISTING])
        self.assertEqual(sorted({s["title"] for s in self.after()["shows"]}),
                         ["Kerro Kaikille", "Lapin Sota"])

    def test_a_page_with_no_timed_card_fails_and_keeps_the_previous_file(self):
        self.kept()
        self.serve(page(COMING, GIFT))
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no film card with a screening time", log)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")

    def test_a_refused_request_keeps_the_previous_file(self):
        self.kept()
        self.serve(RuntimeError("503 refused"))
        code, _ = self.main()
        self.assertNotEqual(code, 0)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        p = registry.by_id("kurikankino")
        self.assertEqual((p["label"], p["host"], p["book"], p["module"], p["where"]),
                         ("Kurikan Kino", "kurikankino.com", "door", "kurikankino", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS
                             if q["accent"] == p["accent"]), 1)

    def test_the_site_names_the_host_it_is_read_from(self):
        self.assertEqual(SITE["base"], "https://www.kurikankino.com")
        self.assertNotIn("reads", SITE)


if __name__ == "__main__":
    unittest.main()
