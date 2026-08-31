"""Room-split venues on one Nexxo locationid: who owns which rows, and what gets loud.

Kino Metso is five towns published as rooms of kinoaurora.fi's locationid 2. A venue
entry with a `rooms` list owns the rows whose roomId is in it; rows nobody owns must
be announced in the log rather than silently unpublished, because that is how a new
town first appears -- Tikkakoski arrived between two probes of the same endpoint.
Matching is on roomId, not roomTitle: the id is what KSEK's own per-town pages filter
on, and a title is one wording change from silently dropping a town.
"""
import unittest

import _ctx                                                # noqa: F401
import nexxo


def row(room_id, room_title, title="Film", start="2026-09-02 18:00:00"):
    return {"movieId": "9", "movieTitle": title, "roomId": room_id,
            "roomTitle": room_title, "startDate": start[:10], "startTime": start,
            "duration": "90", "ageLimit": "7"}


PAYLOAD = {"shows": {"2026-09-02": [
    row(2, "Muurame", "Film A"),
    row(21, "Riihivuori", "Film B"),
    row(4, "Petäjävesi", "Film C"),
    row(12, "Vaajakoski", "Film D"),
    row(19, "Hankasalmi", "Film E"),
    row(19, "Hankasalmi", "Film F", "2026-09-03 18:00:00"),
]}}

SITE = {"provider": "kinometso", "base": "https://api.example",
        "site": "https://pages.example", "programme": "/kino-metso/", "venues": [
            {"id": "km-muurame", "locationid": "2", "rooms": ["2", "21"],
             "page": "/kino-metso/muurame/", "name": "Muurame",
             "short": "Muurame", "city": "Muurame"},
            {"id": "km-petajavesi", "locationid": "2", "rooms": ["4"],
             "page": "/kino-metso/petajavesi/", "name": "Petäjävesi",
             "short": "Petäjävesi", "city": "Petäjävesi"},
        ]}

PLAIN_VENUE = {"id": "x", "locationid": "1", "name": "Kino X",
               "short": "Kino X", "city": "X"}


class RoomSplitTest(unittest.TestCase):
    def test_a_roomed_venue_owns_exactly_its_rooms(self):
        shows = nexxo.parse(PAYLOAD, SITE, SITE["venues"][0])
        self.assertEqual(sorted(s["title"] for s in shows), ["Film A", "Film B"])
        shows = nexxo.parse(PAYLOAD, SITE, SITE["venues"][1])
        self.assertEqual([s["title"] for s in shows], ["Film C"])

    def test_matching_is_on_the_id_not_the_title(self):
        """A retitled room still lands with its venue; a same-titled row under a
        different id does not."""
        p = {"shows": {"d": [row(2, "Muuramesali", "Renamed"),
                             row(99, "Muurame", "Impostor")]}}
        shows = nexxo.parse(p, SITE, SITE["venues"][0])
        self.assertEqual([s["title"] for s in shows], ["Renamed"])

    def test_the_home_room_vanishes_from_aud_and_a_sibling_room_stays(self):
        """"Muurame" repeats the venue and says nothing; "Riihivuori" is a different
        place inside the same venue and the reader needs it."""
        shows = nexxo.parse(PAYLOAD, SITE, SITE["venues"][0])
        by_title = {s["title"]: s for s in shows}
        self.assertEqual(by_title["Film A"]["aud"], "")
        self.assertEqual(by_title["Film B"]["aud"], "Riihivuori")

    def test_a_venue_without_rooms_takes_everything(self):
        shows = nexxo.parse(PAYLOAD, SITE, PLAIN_VENUE)
        self.assertEqual(len(shows), 6)

    def test_a_venue_page_is_the_link_and_carries_no_location_query(self):
        shows = nexxo.parse(PAYLOAD, SITE, SITE["venues"][0])
        self.assertEqual(shows[0]["url"], "https://pages.example/kino-metso/muurame/")

    def test_a_pageless_venue_keeps_the_programme_link(self):
        shows = nexxo.parse(PAYLOAD, SITE, PLAIN_VENUE)
        self.assertEqual(shows[0]["url"], "https://pages.example/kino-metso/?location=1")


class UnclaimedRoomTest(unittest.TestCase):
    def test_rows_nobody_owns_are_counted_by_room(self):
        got = nexxo.unclaimed(PAYLOAD, SITE["venues"])
        self.assertEqual(got, {("19", "Hankasalmi"): 2, ("12", "Vaajakoski"): 1})

    def test_a_plain_site_reports_nothing(self):
        """One venue that takes everything leaves nothing to claim; the guard exists
        only where rooms partition a location."""
        self.assertEqual(nexxo.unclaimed(PAYLOAD, [PLAIN_VENUE]), {})

    def test_a_fully_claimed_payload_is_quiet(self):
        p = {"shows": {"d": [row(2, "Muurame"), row(4, "Petäjävesi")]}}
        self.assertEqual(nexxo.unclaimed(p, SITE["venues"]), {})


if __name__ == "__main__":
    unittest.main()
