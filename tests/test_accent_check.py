"""accent_check: the colour maths, against published reference data.

The whole reason this script exists is that the previous accent numbers could not be
checked. A colour tool whose own arithmetic is unverified is the same failure one level
down, so the CIEDE2000 implementation is pinned to Sharma, Wu & Dalal's published pairs
here as well as in --selftest.
"""
import unittest

import _ctx                                                # noqa: F401
import accent_check as A


class Ciede2000Test(unittest.TestCase):
    def test_matches_sharma_reference_pairs(self):
        """Every pair, not the first one: the branches that get implementations wrong
        are the hue wrap and the RT rotation, and only some pairs reach them."""
        self.assertGreaterEqual(len(A.SHARMA), 10)
        for lab1, lab2, want in A.SHARMA:
            with self.subTest(pair=(lab1, lab2)):
                self.assertAlmostEqual(A.ciede2000(lab1, lab2), want, places=4)

    def test_a_colour_is_zero_from_itself(self):
        self.assertEqual(A.dE("#E4551F", "#E4551F"), (0.0, 0.0, 0.0))

    def test_grey_is_unmoved_by_either_dichromat_model(self):
        """The confusion line runs through the neutral axis, so a grey that shifts means
        the simulation is being applied in the wrong space."""
        for grey in ("#808080", "#333333", "#CCCCCC"):
            with self.subTest(grey=grey):
                labs = A.labs_for(grey)
                for i in (1, 2):
                    self.assertLess(A.ciede2000(labs[0], labs[i]), 1.0)

    def test_the_transfer_function_is_piecewise_not_gamma_22(self):
        """They differ most in the dark end, which is where several accents sit."""
        self.assertAlmostEqual(A.srgb_to_linear(0.02), 0.02 / 12.92, places=9)
        self.assertNotAlmostEqual(A.srgb_to_linear(0.02), 0.02 ** 2.2, places=4)


class SharedCityTest(unittest.TestCase):
    def test_pairs_come_from_the_data_not_a_hand_list(self):
        pairs = A.shared_city_pairs()
        self.assertTrue(pairs, "no same-city pairs found at all")
        for city, a, b in pairs:
            self.assertNotEqual(a, b)
            self.assertLess(a, b, "pairs should be ordered so they cannot duplicate")

    def test_a_candidate_is_measured_against_every_city_it_is_given(self):
        """--city took a comma-separated list and then broke after the first entry, so a
        candidate could be cleared in city A while colliding in city B. A validation tool
        that can approve falsely is worse than no tool.

        Two cities minimum, and the candidate has to appear in both, or the loop is
        never exercised."""
        base = {c for c, a, b in A.shared_city_pairs()}
        pairs = A.shared_city_pairs(extra=("candidate", ["Helsinki", "Tampere"]))
        cities = {c for c, a, b in pairs if "candidate" in (a, b)}
        self.assertIn("Helsinki", cities)
        self.assertIn("Tampere", cities,
                      "second city dropped: the candidate loop stops after the first")
        self.assertTrue(base.issubset({c for c, a, b in pairs}),
                        "adding a candidate lost an existing city's pairs")

    def test_a_bare_string_is_one_city_not_a_sequence_of_letters(self):
        """`for c in "Helsinki"` yields 'H', 'e', 'l' ... which would quietly measure
        the candidate against nothing at all."""
        pairs = A.shared_city_pairs(extra=("candidate", "Helsinki"))
        cities = {c for c, a, b in pairs if "candidate" in (a, b)}
        self.assertEqual(cities, {"Helsinki"})

    def test_a_candidate_in_a_one_chain_city_is_measured_against_that_one_chain(self):
        """Kokkola has a single cinema today, so a candidate landing there makes exactly
        one pair. Written after the first version of this test asserted zero pairs and
        was wrong: one existing chain plus a candidate is a pair, which is the whole
        point of asking."""
        pairs = [p for p in A.shared_city_pairs(extra=("candidate", ["Kokkola"]))
                 if p[0] == "Kokkola"]
        self.assertEqual(len(pairs), 1)
        self.assertIn("biorexkokkola", pairs[0])

    def test_a_candidate_in_a_town_with_no_cinema_is_unconstrained(self):
        """The same reasoning that lets Kino Akseli keep a gold 0.7 dE00 from Finnkino's
        orange: Nummela has one chain, so the two never appear together."""
        pairs = A.shared_city_pairs(extra=("candidate", ["Nowheresville"]))
        self.assertEqual([p for p in pairs if p[0] == "Nowheresville"], [])


if __name__ == "__main__":
    unittest.main()
