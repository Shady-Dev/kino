"""`common.unread_marks`, the one count of screening lines an adapter did not read.

Seven adapters each counted dated lines their own way after the review of 2026-11-22
(M3). The maintainer asked that a fix hold for adapters not written yet, so the count is
one helper in `common.py` and the adapters call it.
"""
import unittest

import _ctx                                                # noqa: F401
import common


class UnreadMarksTest(unittest.TestCase):
    def test_each_date_beyond_the_rows_read_is_one(self):
        cases = [("La 19.9. ja Su 20.9. Klo 15:00", 1, 1),
                 ("Su 20.9. 19:00", 0, 1),
                 ("la 19.9. klo 17.15 su 20.9. klo 15 ma 21.9. 18.00", 1, 2),
                 ("Ke 23.9. Klo 13:00 | Liput 8€", 1, 0),
                 ("ma–ti 26.–27.10. 18:00", 0, 1)]
        for text, read, want in cases:
            with self.subTest(text=text):
                self.assertEqual(common.unread_marks(text, read), want)

    def test_a_clock_amount_or_more_rows_than_dates_is_no_mark(self):
        for text in ("klo 18.30", "klo 12.10", "9,50 €", "19.30", "Kesto 1 h 30 min", ""):
            with self.subTest(text=text):
                self.assertEqual(common.unread_marks(text), 0)
        self.assertEqual(common.unread_marks("su 20.9. klo 17", 3), 0)

    def test_clock_words_count_when_asked(self):
        para = "Tiistai 15.9. Klo 13: Elokuva A Klo 17.30 Elokuva B kello 19 C Kl 21 D"
        self.assertEqual(common.unread_marks(para, 1, by="clock"), 3)
        self.assertEqual(common.unread_marks("Klovnit", by="clock"), 0)

    def test_date_like_still_agrees(self):
        for text in ("To 26.11", "Torstaina 26,11", "klo 18.30", "19.30", "9,50 €"):
            with self.subTest(text=text):
                self.assertEqual(common.date_like(text), common.unread_marks(text) > 0)


if __name__ == "__main__":
    unittest.main()
