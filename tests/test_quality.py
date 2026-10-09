"""The quality score is completeness times correctness, on applicable attributes only."""

import unittest

from catalog_check.evaluate import evaluate
from catalog_check.quality import applicable_attributes, score_counts


class ScoreTests(unittest.TestCase):
    def test_score_is_the_product_of_the_two_factors(self):
        folded = score_counts(applicable=10, clean=6, filled=8)
        self.assertEqual(folded["completeness"], 0.8)
        self.assertEqual(folded["correctness"], 0.75)
        self.assertAlmostEqual(folded["catalog_quality_score"], 0.8 * 0.75)

    def test_jewellery_is_not_missing_a_sleeve(self):
        self.assertNotIn("sleeve", applicable_attributes("earring"))
        self.assertNotIn("size", applicable_attributes("mangalsutra_tanmaniya"))

    def test_a_shoe_is_expected_to_have_a_size(self):
        self.assertIn("size", applicable_attributes("shoe"))
        self.assertIn("outer_material", applicable_attributes("kids_sandal"))

    def test_a_shirt_is_expected_to_have_a_sleeve(self):
        self.assertIn("sleeve", applicable_attributes("t_shirt"))
        self.assertNotIn("sleeve", applicable_attributes("jean"))

    def test_missing_and_disputed_values_move_different_factors(self):
        rows = [
            {
                "product_key": "clean",
                "title": "Bata Men Blue Shirt",
                "analytic_super_category": "MensClothingTopwearBranded",
                "brand": "Bata",
                "seller_entered_brand": "Bata",
                "ideal_for": "Men",
                "color": "Blue",
                "color_code": "Blue",
                "cms_vertical": "shirt",
                "pattern": "Solid",
                "size": "M",
                "sleeve": "Full Sleeve",
            },
            {
                "product_key": "gaps",
                "title": "Bata Men Blue Shirt",
                "analytic_super_category": "MensClothingTopwearBranded",
                "brand": "Bata",
                "seller_entered_brand": "Bata",
                "ideal_for": "",
                "color": "Red",
                "color_code": "",
                "cms_vertical": "shirt",
                "pattern": "Solid",
                "size": "M",
                "sleeve": "Full Sleeve",
            },
        ]
        result = evaluate(rows)
        # Two shirts, seven applicable attributes each.
        self.assertEqual(result.quality_applicable, 14)
        # First product is clean on all seven. Second is missing ideal_for and
        # the title says Blue while color is Red, so color is a defect.
        self.assertEqual(result.quality_clean, 12)
        self.assertEqual(result.quality_filled, 13)
        folded = score_counts(result.quality_applicable, result.quality_clean, result.quality_filled)
        self.assertAlmostEqual(folded["completeness"], 13 / 14)
        self.assertAlmostEqual(folded["correctness"], 12 / 13)
        self.assertAlmostEqual(folded["catalog_quality_score"], 12 / 14)


if __name__ == "__main__":
    unittest.main()
