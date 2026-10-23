"""The Kino Tervakoski reader: the programme page's REST twin, one paragraph per slot.

The fixtures are the page's shapes read on 2026-10-24 (issue #14), cut to what each rule
needs, with two films and two slots wherever there is a loop.

What they exist to prove:

- **Only a slot linking to a film section is a film.** The private event in the same list,
  a slot with no link, is left out and counted.
- **Only the programme is read**: a clock in a film section's text below it is not a slot.
- **Every slot shape seen is read**: "klo" in lower case and "kesto, 1t 57 min".
"""
import contextlib
import datetime
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import registry
import run
import tervakoski as T

SITE = T.SITES[0]
VENUE = SITE["venues"][0]["id"]
LISTING = SITE["base"] + SITE["listing"]
PAGE = SITE["site"]
TODAY = datetime.date(2026, 10, 24)


def p(inner):
    return f'<p class="wp-block-paragraph">{inner}</p>\n\n'


def day(label):
    return p(f"<strong>{label}</strong>")


def slot(clock, anchor, label, rest, klo="Klo"):
    return p(f'{klo} {clock} &#8211; <a href="#{anchor}" data-type="internal">{label}</a>{rest}')


def section(anchor, title, body="<p>Kesto 1 t 41 min</p><p>Lippu 10,00 €</p>"):
    return f'<h2 class="wp-block-heading" id="{anchor}">{title}</h2>\n{body}\n'


def content(*parts, sections=True):
    out = "".join(parts)
    if sections:
        out += (section("h-lapin-sota", "Lapin sota") + section("h-pirjo-i-sverige", "Pirjo i Sverige")
                + section("h-wild-horse-nine", "Wild Horse Nine")
                + section("h-pikku-kummitus", "Pikku kummitus Lapanen keppostelee",
                          body=p("Klo 12.00 – kassa avautuu")))
    return out


LIVE = content(
    day("Keskiviikko 28.10."),
    p("Klo 17.00 &#8211; <strong>Yksityistilaisuus</strong>"),
    slot("19.30", "h-lapin-sota", "Lapin sota (K16)",
         ", kotimainen, draama, sota, kesto 2 t 38 min, lippu 10,00 €"),
    day("Torstai 29.10."),
    slot("17.00", "h-pirjo-i-sverige", "Pirjo i Sverige (S),",
         " kotimainen, komedia, koko perheen elokuva, kesto 1 t 28 min, lippu 10,00 €"),
    slot("18.45", "h-pikku-kummitus", "Pikku kummitus Lapanen keppostelee (S),",
         " <strong>SUOMEKSI PUHUTTU</strong>, perhe-elokuva, animaatio, kesto 1 t 3 min, "
         "lippu 9,00 €"),
    day("Perjantai 6.11."),
    slot("19.15", "h-wild-horse-nine", "Wild Horse Nine (K16)", ", kesto, 1t 57 min, lippu 10,00 €",
         klo="klo"),
)


class ProgrammeTest(unittest.TestCase):

    def rows(self, html):
        return T.rows(SITE, html, TODAY)

    def test_every_film_slot_is_a_row_and_the_private_event_is_not(self):
        shows, report = self.rows(LIVE)
        self.assertEqual([(s["start"], s["title"]) for s in shows],
                         [("2026-10-28T19:30:00+02:00", "Lapin sota"),
                          ("2026-10-29T17:00:00+02:00", "Pirjo i Sverige"),
                          ("2026-10-29T18:45:00+02:00", "Pikku kummitus Lapanen keppostelee"),
                          ("2026-11-06T19:15:00+02:00", "Wild Horse Nine")])
        self.assertEqual((report["films"], report["not_film"]), (4, 1))

    def test_the_fields_a_row_carries(self):
        shows, _ = self.rows(LIVE)
        lapin, pirjo, pikku, wild = shows
        self.assertEqual((lapin["rating"], lapin["len"], lapin["price"], lapin["genres"],
                          lapin["url"], lapin["eventId"], lapin["img"], lapin["lang"]),
                         ("K-16", "158", "10€", "Kotimainen, Draama, Sota",
                          PAGE + "#h-lapin-sota", "lapin-sota", "", ""))
        self.assertEqual((pirjo["rating"], pirjo["len"]), ("S", "88"))
        self.assertEqual((pikku["lang"], pikku["price"], pikku["genres"]),
                         ("FI-A", "9€", "Perhe-elokuva, Animaatio"))
        self.assertEqual((wild["len"], wild["rating"], wild["genres"]), ("117", "K-16", ""))

    def test_a_clock_in_a_film_section_is_not_a_slot(self):
        """The fixture's last section holds "Klo 12.00 – kassa avautuu" under a heading the
        programme links to; it is below the programme and never read."""
        shows, _ = self.rows(LIVE)
        self.assertNotIn("12:00", " ".join(s["start"] for s in shows))

    def test_a_link_to_no_section_still_reads_and_links_the_page(self):
        shows, _ = self.rows(content(day("Lauantai 24.10."),
                                     slot("18.00", "h-tuntematon", "Tuntematon (K12)",
                                          ", kesto 1 t 40 min, lippu 10,00 €"),
                                     slot("20.00", "h-lapin-sota", "Lapin sota (K16)",
                                          ", kesto 2 t 38 min, lippu 10,00 €")))
        self.assertEqual([s["url"] for s in shows], [PAGE, PAGE + "#h-lapin-sota"])

    def test_a_slot_before_any_day_is_left_out(self):
        shows, report = self.rows(content(
            slot("18.00", "h-lapin-sota", "Lapin sota (K16)", ", lippu 10,00 €"),
            day("Lauantai 24.10."),
            slot("20.00", "h-lapin-sota", "Lapin sota (K16)", ", lippu 10,00 €")))
        self.assertEqual([s["start"][:16] for s in shows], ["2026-10-24T20:00"])
        self.assertEqual(report["orphan"], 1)


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._get = T.get_text
        self.addCleanup(lambda: setattr(T, "get_text", self._get))
        self.calls = []

    def serve(self, body):
        def get_text(url, **kw):
            self.calls.append(url)
            return body
        T.get_text = get_text

    def main(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(["tervakoski", "--half", "all"])
        return code, out.getvalue() + err.getvalue()

    def day(self, days):
        """run.main reads the real clock, so a fixture dated in October would go stale."""
        d = datetime.datetime.now(T.FI).date() + datetime.timedelta(days=days)
        names = ("Maanantai", "Tiistai", "Keskiviikko", "Torstai", "Perjantai", "Lauantai",
                 "Sunnuntai")
        return day(f"{names[d.weekday()]} {d.day}.{d.month}.")

    def kept(self):
        doc = {"generated": "2026-10-20T00:00:00+00:00", "dates": ["2026-10-20"],
               "horizon": "2026-10-20",
               "shows": [{"title": "Yesterday", "start": "2026-10-20T17:00:00+03:00"}]}
        (run.OUT / f"area-{VENUE}.json").write_text(json.dumps(doc), encoding="utf-8")

    def after(self):
        return json.loads((run.OUT / f"area-{VENUE}.json").read_text(encoding="utf-8"))

    def test_the_site_publishes_from_one_request(self):
        self.serve(json.dumps({"id": 196, "content": {"rendered": content(
            self.day(1), slot("19.00", "h-lapin-sota", "Lapin sota (K16)", ", lippu 10,00 €"),
            self.day(2), slot("17.00", "h-pirjo-i-sverige", "Pirjo i Sverige (S)", ", lippu 10,00 €"),
            p("Klo 19.00 &#8211; Yksityistilaisuus"))}}))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(self.calls, [LISTING])
        self.assertEqual(sorted({s["title"] for s in self.after()["shows"]}),
                         ["Lapin sota", "Pirjo i Sverige"])
        self.assertIn("1 slot(s) with no film link", log)

    def test_a_programme_with_no_film_slot_fails_and_keeps_the_previous_file(self):
        self.kept()
        self.serve(json.dumps({"content": {"rendered": content(
            self.day(1), p("Klo 17.00 &#8211; Yksityistilaisuus"))}}))
        code, log = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn("no film slot", log)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")

    def test_an_answer_that_is_not_json_keeps_the_previous_file(self):
        self.kept()
        self.serve("<html><body>Just a moment...</body></html>")
        code, _ = self.main()
        self.assertNotEqual(code, 0)
        self.assertEqual(self.after()["shows"][0]["title"], "Yesterday")


class RegistryTest(unittest.TestCase):
    def test_the_registry_entry(self):
        r = registry.by_id("kinotervakoski")
        self.assertEqual((r["label"], r["host"], r["book"], r["module"], r["where"]),
                         ("Kino Tervakoski", "janakkala.fi", "door", "tervakoski", "cloud"))
        self.assertEqual(sum(1 for q in registry.PROVIDERS if q["accent"] == r["accent"]), 1)


if __name__ == "__main__":
    unittest.main()
