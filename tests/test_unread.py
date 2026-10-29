"""common.unread: what an adapter saw and did not place, named in the run log.

An item is its kind and whole context, and the display is cut after that. One site's items
stay in its block, the output is bounded, and no exit code changes.
"""
import contextlib
import io
import threading
import unittest

import _ctx                                                # noqa: F401
import common


def shown(label, kind, text, n=1):
    """One item's log line: site, kind, the digest of the whole context, the text."""
    return (f"[{label}] unread {kind} {common.unread_id(kind, text)}: {text}"
            + (f" (x{n})" if n > 1 else ""))


def lines_of(label, calls):
    """Run `calls` inside one site's scope. -> the lines the scope printed."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        with common.unread_scope(label):
            for kind, text in calls:
                common.unread(kind, text)
    common.take_unread(label)
    return buf.getvalue().splitlines()


class UnreadTest(unittest.TestCase):
    def test_each_item_is_named_with_its_site_and_kind(self):
        text = "Järki ja tunteet, To/Tors 5.11 Klo 17.00: X"
        got = lines_of("biopallas", [("line", text)])
        self.assertEqual(got, [shown("biopallas", "line", text)])
        self.assertRegex(got[0], r"^\[biopallas\] unread line [0-9a-f]{12}: Järki")

    def test_a_repeated_item_is_one_line_with_its_count(self):
        """Niagara renders every screening twice, a desktop and a mobile copy."""
        got = lines_of("niagara", [("date", "Film: data-dates [1, 2]")] * 2)
        self.assertEqual(got, [shown("niagara", "date", "Film: data-dates [1, 2]", 2)])

    def test_two_items_alike_in_their_first_characters_stay_two(self):
        """The whole context is the identity. Only the display is cut."""
        head = "x" * common.UNREAD_WIDTH
        got = lines_of("s", [("row", head + " first"), ("row", head + " second")])
        self.assertEqual(len(got), 2)
        self.assertEqual({line.split(": ", 1)[1] for line in got}, {head[:-3] + "..."})
        self.assertEqual(len({line.split(":", 1)[0] for line in got}), 2,
                         "only the digest tells them apart")
        for line in got:
            self.assertLessEqual(len(line), len("[s] unread row 0123456789ab: ")
                                 + common.UNREAD_WIDTH)

    def test_the_digest_is_the_same_in_every_process_and_covers_the_kind(self):
        """The digest has to match across runs. Python's hash() changes per process."""
        self.assertEqual(common.unread_id("row", "r"), "a67795ec3102")
        self.assertNotEqual(common.unread_id("row", "r"), common.unread_id("line", "r"))

    def test_output_is_bounded_and_the_rest_is_counted_by_kind(self):
        calls = ([("line", f"l{i}") for i in range(common.UNREAD_SHOWN)]
                 + [("place", "p1"), ("place", "p2"), ("row", "r1")])
        got = lines_of("s", calls)
        self.assertEqual(len(got), common.UNREAD_SHOWN + 1)
        self.assertEqual(got[-1], "[s] unread: 3 more item(s) not shown (place 2, row 1)")

    def test_kinds_print_in_a_fixed_order(self):
        got = lines_of("s", [("row", "r"), ("line", "l"), ("place", "p"), ("date", "d")])
        self.assertEqual([l.split(":")[0].rsplit(" ", 1)[0] for l in got],
                         ["[s] unread line", "[s] unread date", "[s] unread place",
                          "[s] unread row"])

    def test_whitespace_and_zero_width_characters_do_not_make_a_new_item(self):
        got = lines_of("s", [("row", "KERRO  KAIKILLE 3.11. TI ﻿ klo 15.00"),
                             ("row", "KERRO KAIKILLE 3.11. TI klo 15.00")])
        self.assertEqual(got, [shown("s", "row", "KERRO KAIKILLE 3.11. TI klo 15.00", 2)])

    def test_an_unknown_kind_is_refused(self):
        with common.unread_scope("s"), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                common.unread("note", "x")
        common.take_unread("s")

    def test_outside_a_site_it_goes_to_stderr_rather_than_nowhere(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            common.unread("line", "Halvjus på")
        self.assertEqual(err.getvalue(),
                         f"[unread] line {common.unread_id('line', 'Halvjus på')}: Halvjus på\n")

    def test_a_scope_that_raises_still_prints_what_it_saw(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(RuntimeError):
            with common.unread_scope("s"):
                common.unread("row", "r")
                raise RuntimeError("site failed")
        self.assertEqual(buf.getvalue(), shown("s", "row", "r") + "\n")
        self.assertEqual(common.take_unread("s"), 1)

    def test_the_count_is_the_latest_scope_s_and_is_taken_once(self):
        """A site read twice in one process does not add the reads together."""
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(2):
                with common.unread_scope("t"):
                    common.unread("row", "a")
                    common.unread("row", "a")
                    common.unread("row", "b")
        self.assertEqual(common.take_unread("t"), 2)
        self.assertEqual(common.take_unread("t"), 0)

    def test_two_sites_on_two_threads_keep_their_own_items(self):
        """The pool reads hosts at once, and each thread has its own scope."""
        go = threading.Barrier(2)
        out = {}

        def site(label):
            with common.unread_scope(label) as box:
                go.wait()
                for i in range(50):
                    common.unread("line", f"{label} {i}")
                go.wait()
                out[label] = dict(box)
            common.take_unread(label)

        with contextlib.redirect_stdout(io.StringIO()):
            threads = [threading.Thread(target=site, args=(n,)) for n in ("a", "b")]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        for label in ("a", "b"):
            self.assertEqual({text.split()[0] for _, text in out[label]}, {label})
            self.assertEqual(len(out[label]), 50)

    def test_a_nested_scope_gives_the_outer_one_back(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with common.unread_scope("outer") as outer:
                with common.unread_scope("inner"):
                    common.unread("row", "in")
                common.unread("row", "out")
        common.take_unread("outer")
        common.take_unread("inner")
        self.assertEqual(list(outer), [("row", "out")])


if __name__ == "__main__":
    unittest.main()
