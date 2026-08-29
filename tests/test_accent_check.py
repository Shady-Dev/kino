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


if __name__ == "__main__":
    unittest.main()
