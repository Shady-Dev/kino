"""Kino Marilyn, Loviisa, read from eTiketti since 2026-10-30.

The site prints the place line "KINO MARILYN | SALI", or "| AULA" for the foyer, on
`data-dates` items whose `data-locations` is the town. Before the move it was a Nexxo site,
and its provider and venue ids key saved venues and page URLs.
"""
import io
import unittest
from contextlib import redirect_stdout

import _ctx                                                # noqa: F401
import build_pages as bp
import nexxo
import registry
from test_etiketti_templates import Stubbed, dated_film, dated_item, listing, site as site_of


def site():
    return site_of("kinomarilyn")


def item(date, clock, room, price, sid, place="KINO MARILYN"):
    return dated_item("loviisa", date, clock, f"{place} | {room}", price, "189/189", sid)


SENSE = dated_film(item("30.10.2026", "13.30", "SALI", "13,00", 53444),
                   item("1.11.2026", "14.30", "SALI", "13,00", 53445))
QUIZ = dated_film(item("5.11.2026", "19.30", "AULA", "0,00", 53413))
PAGES = {"/elokuvat/23/jarki-ja-tunteet": SENSE, "/elokuvat/10/baaripahkina": QUIZ}


class MarilynTest(Stubbed):

    def read(self, pages=PAGES):
        buf = io.StringIO()
        with redirect_stdout(buf):
            out = self.stub(dict(pages, **{"/elokuvat/ohjelmistossa": listing(*pages)})
                            ).fetch_site(site(), sleep=0)
        return out, buf.getvalue()

    def test_the_ids_and_client_fields_are_the_nexxo_ones(self):
        p = registry.by_id("kinomarilyn")
        self.assertEqual((p["module"], p["label"], p["host"], p["accent"], p["accentDark"]),
                         ("etiketti", "Kino Marilyn", "kinomarilyn.fi", "#1A6E4A", "#297833"))
        self.assertEqual(site()["venues"], [{"id": "ma-loviisa", "match": "kino marilyn",
                                             "name": "Kino Marilyn", "short": "Kino Marilyn",
                                             "city": "Loviisa"}])
        self.assertEqual(site()["base"], "https://www.kinomarilyn.fi")

    def test_only_etiketti_reads_it(self):
        self.assertNotIn("kinomarilyn", [s["provider"] for s in nexxo.SITES])
        self.assertNotIn("kinomarilyn.fi",
                         " ".join(s.get("base", "") + s.get("site", "") for s in nexxo.SITES))

    def test_rows_carry_the_screening_s_own_ticket_link(self):
        out, _ = self.read()
        rows = out["ma-loviisa"]
        self.assertEqual([(r["start"], r["aud"], r["price"], r["url"]) for r in rows], [
            ("2026-10-30T13:30:00+02:00", "SALI", "13€",
             "https://www.kinomarilyn.fi/salikartta?id=53444"),
            ("2026-11-01T14:30:00+02:00", "SALI", "13€",
             "https://www.kinomarilyn.fi/salikartta?id=53445"),
            ("2026-11-05T19:30:00+02:00", "AULA", "0€",
             "https://www.kinomarilyn.fi/salikartta?id=53413"),
        ])
        self.assertEqual({(r["provider"], r["venue"], r["theatre"]) for r in rows},
                         {("kinomarilyn", "ma-loviisa", "Kino Marilyn")})

    def test_another_place_in_loviisa_is_not_taken_as_marilyn(self):
        pages = dict(PAGES, **{"/elokuvat/40/konsertti": dated_film(
            item("7.11.2026", "19.00", "SALI", "20,00", 53500, place="KULTTUURITALO"))})
        out, log = self.read(pages)
        self.assertEqual(len(out["ma-loviisa"]), 3)
        self.assertNotIn("53500", " ".join(r["url"] for r in out["ma-loviisa"]))
        self.assertIn("'KULTTUURITALO' (1 row(s)", log)

    def test_the_page_slug_is_unchanged(self):
        d = dict(site()["venues"][0], provider="kinomarilyn")
        label = bp.label_of(d, {"kinomarilyn": "Kino Marilyn"})
        self.assertEqual(bp.slug(f"{label} {d['city']}"), "kino-marilyn-loviisa")


if __name__ == "__main__":
    unittest.main()
