"""Add to calendar: one screening as an .ics file (2026-09-13, v146).

`icsFor` and its helpers are sliced verbatim out of index.html by tests/ics_harness.js and
run on their own with the page's Helsinki formatters and safeUrl. Measured 2026-09-13:
35 of 3561 committed shows have no `len` (booked as 120 minutes, said so), 627 no `aud`
(no hall in LOCATION). The download plumbing and the second menu row are pinned on the
source; the download itself is verified by hand on the platforms IDEAS names.
"""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

import _ctx

HARNESS = pathlib.Path(__file__).resolve().parent / "ics_harness.js"
HTML = (_ctx.ROOT / "index.html").read_text(encoding="utf-8")


def unfold(text):
    return text.replace("\r\n ", "")


def prop(text, name):
    """The value of the (unfolded) property `name`, first occurrence inside VEVENT."""
    event = unfold(text).split("BEGIN:VEVENT", 1)[1]
    m = re.search(r"^" + re.escape(name) + r"[;:](.*?)\r\n", event, re.M)
    return m.group(1) if m else None


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class IcsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True,
                             cwd=str(_ctx.ROOT), timeout=60)
        if out.returncode:
            raise AssertionError(f"harness failed: {out.stderr}")
        cls.o = json.loads(out.stdout)

    def test_the_file_is_a_calendar_with_one_event_in_helsinki_time_and_crlf_ends(self):
        t = self.o["plain"]
        self.assertTrue(t.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"))
        self.assertTrue(t.endswith("END:VEVENT\r\nEND:VCALENDAR\r\n"))
        self.assertNotRegex(t, r"[^\r]\n", "every line end is CRLF")
        self.assertEqual(t.count("BEGIN:VEVENT"), 1)
        self.assertIn("BEGIN:VTIMEZONE\r\nTZID:Europe/Helsinki\r\n", t)
        self.assertIn("RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", t)
        self.assertIn("RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", t)
        self.assertEqual(prop(t, "DTSTART"), "TZID=Europe/Helsinki:20260915T163000")
        self.assertEqual(prop(t, "DTEND"), "TZID=Europe/Helsinki:20260915T175800")   # 16:30 + 88 min
        self.assertEqual(prop(t, "DTSTAMP"), "20260913T120000Z")

    def test_summary_is_the_title_verbatim_and_location_is_chain_venue_hall_city(self):
        t = self.o["plain"]
        self.assertEqual(prop(t, "SUMMARY"), "Ryhmä Hau: Dinoelokuva")
        self.assertEqual(prop(t, "LOCATION"), r"Finnkino Promenadi\, Sali 3\, Pori")
        self.assertEqual(prop(t, "URL"), "https://www.finnkino.fi/liput/valitse-paikat/?showtimeId=1004-5281")
        self.assertEqual(prop(t, "DESCRIPTION"), r"2D\nhttps://www.finnkino.fi/liput/valitse-paikat/?showtimeId=1004-5281")

    def test_no_hall_means_venue_and_city_only(self):
        self.assertEqual(prop(self.o["no_hall"], "LOCATION"), r"Kino Regina\, Helsinki")

    def test_a_missing_runtime_books_two_hours_and_says_so_in_the_language(self):
        for case, note in (("no_len_fi", "Kesto arvioitu"), ("no_len_sv", "Längd uppskattad"), ("no_len_en", "Runtime estimated")):
            t = self.o[case]
            self.assertEqual(prop(t, "DTEND"), "TZID=Europe/Helsinki:20260915T183000", case)
            self.assertTrue(prop(t, "DESCRIPTION").endswith(r"\n" + note), (case, prop(t, "DESCRIPTION")))
        self.assertNotIn("Kesto arvioitu", self.o["plain"])

    def test_text_values_escape_backslash_semicolon_comma_and_newline(self):
        t = self.o["punctuation"]
        self.assertEqual(prop(t, "SUMMARY"), r"Mission: Impossible\, Part\; Two\\Three")
        self.assertEqual(prop(t, "LOCATION"), r"BioRex Tripla\, Sali 3\, Helsinki")
        self.assertTrue(prop(t, "DESCRIPTION").startswith(r"IMAX\, dubattu\n"))

    def test_lines_fold_at_75_octets_without_splitting_a_character(self):
        t = self.o["long_title"]
        lines = t.split("\r\n")
        self.assertLessEqual(max(len(l.encode("utf-8")) for l in lines), 75)
        self.assertTrue(any(l.startswith(" ") for l in lines), "the long title was folded")
        self.assertEqual(prop(t, "SUMMARY"), " ".join(["Ääkkösiä"] * 12), "unfolding gives the title back")
        self.assertNotIn("�", t)

    def test_the_ticket_link_goes_through_safeurl(self):
        t = self.o["bad_url"]
        self.assertIsNone(prop(t, "URL"))
        self.assertNotIn("javascript:", t)
        self.assertEqual(prop(t, "DESCRIPTION"), "2D")

    def test_an_iso_start_in_winter_time_is_wall_time(self):
        t = self.o["iso_start"]
        self.assertEqual(prop(t, "DTSTART"), "TZID=Europe/Helsinki:20261101T180000")
        self.assertEqual(prop(t, "DTEND"), "TZID=Europe/Helsinki:20261101T192800")

    def test_the_uid_is_stable_across_calls_and_ours(self):
        a, b = prop(self.o["plain"], "UID"), prop(self.o["same_again"], "UID")
        self.assertEqual(a, b)
        self.assertEqual(a, "6c8421f5-34@leffavuoro.fi", "djb2 over venue|start|title, not a clock")
        self.assertNotEqual(a, prop(self.o["no_hall"], "UID"), "another venue is another event")


class CalendarPlumbingTest(unittest.TestCase):

    def test_the_second_menu_row_and_its_strings(self):
        self.assertIn('<button type="button" role="menuitem" class="mi" data-act="cal"><span>${esc(T.addCalendar)}</span></button>', HTML)
        self.assertIn("if(s && mi.dataset.act === 'cal') calendarScreening(s);", HTML)
        for lang, text in (("fi", "Lisää kalenteriin"), ("sv", "Lägg till i kalendern"), ("en", "Add to calendar")):
            self.assertIn(f"addCalendar:'{text}'", HTML, lang)

    def test_the_download_is_a_blob_on_a_download_anchor(self):
        fn = re.search(r"function calendarScreening\(s\)\{.*?\n  \}\n", HTML, re.S).group(0)
        self.assertIn("icsFor({ ...s, start: s.start }, venueFor(s), state.lang)", fn)
        self.assertIn("new Blob([ics], { type: 'text/calendar;charset=utf-8' })", fn)
        self.assertIn("a.download = `leffavuoro-${fiDate(s.start)}-", fn)
        self.assertIn("a.click();", fn)
        self.assertIn("URL.revokeObjectURL(href)", fn)

    def test_the_venue_behind_the_screening_is_labelled_and_placed_by_the_pickers_rules(self):
        fn = re.search(r"function venueFor\(s\)\{.*?\n  \}\n", HTML, re.S).group(0)
        self.assertIn("venueIndex[s.venue] || (venueIndex[state.area] || null)", fn)
        self.assertIn("label: labelOf(a), city: cityOf(a)", fn)
        self.assertIn("label: venueName(s), city: cityOf({ name: s.theatre })", fn)

    def test_the_service_worker_moved_with_the_page(self):
        sw = (_ctx.ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(int(re.search(r"leffavuoro-v(\d+)", sw).group(1)), 146)


if __name__ == "__main__":
    unittest.main()
