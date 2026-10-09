"""The checks are the assignment. These tests pin the decisions a reviewer will ask about."""

import unittest

from catalog_check.checks import check_row
from catalog_check.evaluate import resolve


def row(**kwargs: str) -> dict[str, str]:
    base = {
        "product_key": "P1",
        "title": "",
        "description": "",
        "analytic_super_category": "",
        "brand": "",
        "seller_entered_brand": "",
        "ideal_for": "",
        "color": "",
        "color_code": "",
        "sleeve": "",
        "pattern": "",
        "pack_of": "",
        "contents_in_sales_package": "",
        "sales_package": "",
        "cms_vertical": "",
        "material": "",
        "outer_material": "",
        "size": "",
    }
    base.update(kwargs)
    return base


def kinds(signals, attribute, rule=None):
    return [
        signal.kind
        for signal in signals
        if signal.attribute == attribute and (rule is None or signal.rule == rule)
    ]


class IdealForTests(unittest.TestCase):
    def test_taxonomy_disagreement_is_a_contradiction(self):
        signals = check_row(row(ideal_for="Men", analytic_super_category="WomenWesternGrowth", title="bazler Men Shapewear"))
        self.assertIn("contradict", kinds(signals, "ideal_for", "taxonomy_gender"))

    def test_boys_in_kids_is_support(self):
        signals = check_row(row(ideal_for="Boys", analytic_super_category="KidClothing", title="Cotton Tee"))
        self.assertIn("support", kinds(signals, "ideal_for", "taxonomy_gender"))

    def test_title_opposite_sex_contradicts(self):
        signals = check_row(
            row(
                ideal_for="Women",
                analytic_super_category="FashionWearables",
                brand="KRYSTALZ",
                title="KRYSTALZ Men Cuban Link Necklace",
            )
        )
        self.assertEqual(kinds(signals, "ideal_for", "title_gender"), ["contradict"])

    def test_women_versus_girls_in_the_title_is_not_evidence(self):
        signals = check_row(
            row(
                ideal_for="Women",
                analytic_super_category="FashionWearables",
                title="Pearl Hair Clip for Girls",
            )
        )
        self.assertEqual(kinds(signals, "ideal_for", "title_gender"), [])

    def test_brand_named_boy_is_not_an_audience(self):
        signals = check_row(
            row(
                ideal_for="Men",
                analytic_super_category="MensClothingTopwearUnbranded",
                brand="NB NICKY BOY",
                title="NB NICKY BOY Tshirt Pant Co-ords Set",
            )
        )
        self.assertEqual(kinds(signals, "ideal_for", "title_gender"), [])

    def test_product_copy_in_ideal_for_is_invalid(self):
        signals = check_row(row(ideal_for="Leather shoes formal dress or casual Synthetic footwear"))
        self.assertEqual(kinds(signals, "ideal_for"), ["invalid"])

    def test_taxonomy_and_title_disagreeing_is_contested(self):
        signals = check_row(
            row(
                ideal_for="Men",
                analytic_super_category="WomenWesternCore",
                title="clickwell Men Shrug",
                brand="clickwell",
            )
        )
        verdict = resolve("ideal_for", True, signals)
        self.assertEqual(verdict.verdict, "contested")


class ColorTests(unittest.TestCase):
    def test_title_color_disagrees(self):
        signals = check_row(row(color="Purple", title="Slim Saree Shapewear Petticoat Beige", color_code=""))
        self.assertIn("contradict", kinds(signals, "color", "title_color"))

    def test_one_of_several_title_colors_supports(self):
        signals = check_row(row(color="Navy", title="Men Flip Flops Navy, Grey", color_code=""))
        self.assertIn("support", kinds(signals, "color", "title_color"))
        self.assertNotIn("contradict", kinds(signals, "color"))

    def test_gold_in_the_title_is_not_a_color(self):
        signals = check_row(row(color="Grey", title="Gold Solid Men Track Suit", color_code=""))
        self.assertEqual(kinds(signals, "color", "title_color"), [])

    def test_shade_agrees_across_color_fields(self):
        signals = check_row(row(color="Blue", color_code="Dark Blue", title="Plain Shirt"))
        self.assertIn("support", kinds(signals, "color", "color_fields"))

    def test_color_fields_disagree(self):
        signals = check_row(row(color="Blue", color_code="Red", title="Plain Shirt"))
        self.assertIn("contradict", kinds(signals, "color", "color_fields"))

    def test_sibling_color_cannot_outvote_the_title(self):
        signals = check_row(row(color="Blue", color_code="Dark Blue", title="Red Cotton Shirt"))
        verdict = resolve("color", True, signals)
        self.assertEqual(verdict.verdict, "contradicted")

    def test_title_support_plus_color_code_conflict_is_contested(self):
        signals = check_row(row(color="Blue", color_code="Red", title="Blue Cotton Shirt"))
        verdict = resolve("color", True, signals)
        self.assertEqual(verdict.verdict, "contested")

    def test_abbreviated_color_code(self):
        signals = check_row(row(color="White", color_code="Wht & Blck", title="Shirt"))
        self.assertIn("support", kinds(signals, "color", "color_fields"))


class BrandTests(unittest.TestCase):
    def test_case_and_contained_line_name_are_the_same_brand(self):
        signals = check_row(row(brand="Adrenex by Ecommerce", seller_entered_brand="Adrenex", title="Running Shoes"))
        self.assertEqual(kinds(signals, "brand", "seller_brand"), [])

    def test_different_brands_contradict(self):
        signals = check_row(row(brand="3SIX5", seller_entered_brand="Aayu", title="Cotton Kurta"))
        self.assertIn("contradict", kinds(signals, "brand", "seller_brand"))

    def test_title_confirms_brand(self):
        signals = check_row(row(brand="Bata", seller_entered_brand="Bata", title="Bata Men's Formal Monk Shoes"))
        self.assertIn("support", kinds(signals, "brand", "title_brand"))


class AttributeTests(unittest.TestCase):
    def test_sleeve_length_conflict(self):
        signals = check_row(row(sleeve="Half Sleeve", title="Full Sleeve Printed Girls Sweatshirt"))
        self.assertIn("contradict", kinds(signals, "sleeve", "title_sleeve"))

    def test_sleeve_style_is_not_a_length(self):
        signals = check_row(row(sleeve="Puff Sleeves", title="Full Sleeve Party Dress"))
        self.assertEqual(kinds(signals, "sleeve"), [])

    def test_solid_versus_printed(self):
        signals = check_row(row(pattern="Solid", title="Printed Men Round Neck White T-Shirt"))
        self.assertIn("contradict", kinds(signals, "pattern", "title_pattern"))

    def test_floral_print_supports_printed(self):
        signals = check_row(row(pattern="Floral Print", title="Printed Women Kurta"))
        self.assertIn("support", kinds(signals, "pattern", "title_pattern"))

    def test_embroidered_versus_printed_is_not_a_conflict(self):
        signals = check_row(row(pattern="Embroidered", title="Printed Kurta"))
        self.assertEqual(kinds(signals, "pattern"), [])

    def test_known_pattern_typo_still_matches(self):
        signals = check_row(row(pattern="Embriodered", title="Embroidered Anarkali Kurta"))
        self.assertIn("support", kinds(signals, "pattern", "title_pattern"))

    def test_pack_in_the_title_disagrees(self):
        signals = check_row(row(pack_of="1", title="Casual Shirts Pack of 2", sales_package=""))
        self.assertIn("contradict", kinds(signals, "pack_of", "pack_text"))

    def test_contents_disagreement_does_not_need_the_title(self):
        signals = check_row(row(pack_of="2", contents_in_sales_package="1", title="Casual Shirts"))
        self.assertIn("contradict", kinds(signals, "pack_of", "pack_contents"))

    def test_copied_contents_is_not_support(self):
        signals = check_row(row(pack_of="1", contents_in_sales_package="1", title="Casual Shirt"))
        self.assertEqual(kinds(signals, "pack_of"), [])

    def test_saree_filed_as_kurta(self):
        signals = check_row(row(cms_vertical="kurta", title="Women Printed Saree Light Blue"))
        self.assertIn("contradict", kinds(signals, "cms_vertical", "title_product_type"))

    def test_tshirt_is_not_read_as_shirt(self):
        signals = check_row(row(cms_vertical="t_shirt", title="Printed Men Round Neck White T-Shirt"))
        self.assertIn("support", kinds(signals, "cms_vertical"))
        self.assertNotIn("contradict", kinds(signals, "cms_vertical"))

    def test_combo_title_may_use_a_set_vertical(self):
        signals = check_row(row(cms_vertical="kids_apparel_combo", title="Girls Shirt Shorts Camisole"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_shoe_cream_is_not_a_shoe(self):
        signals = check_row(row(cms_vertical="shoe_care", title="White Shoe Cream Polish Leather Canvas"))
        self.assertEqual(kinds(signals, "cms_vertical"), [])

    def test_shirt_fabric_may_live_in_fabric(self):
        signals = check_row(row(cms_vertical="fabric", title="Polycotton Printed Shirt Fabric"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_shirt_dress_is_still_a_dress(self):
        signals = check_row(row(cms_vertical="dress", title="Women T Shirt Black Midi Length Dress"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_mini_short_dress_is_a_dress(self):
        signals = check_row(row(cms_vertical="dress", title="Women A-line White Mini/Short Dress"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_blouse_material_is_fabric(self):
        signals = check_row(row(cms_vertical="fabric", title="Organza Self Design Blouse Material"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_boxer_vertical(self):
        signals = check_row(row(cms_vertical="boxer", title="Striped Men Boxer"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_kids_variant_of_the_same_product(self):
        signals = check_row(row(cms_vertical="kids_panty", title="Panty For Girls Multicolor"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_pyjama_set_may_be_a_night_suit(self):
        signals = check_row(row(cms_vertical="night_suit", title="Women Self Design Black Shirt & Pyjama set"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_saree_cover_is_not_a_saree(self):
        signals = check_row(row(cms_vertical="garment_cover", title="Premium Saree Cover Storage Bag"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_brand_color_is_not_the_product_color(self):
        signals = check_row(
            row(color="Green", brand="PRATHAM BLUE", title="PRATHAM BLUE Women Kurta Palazzo Dupatta Set", color_code="")
        )
        self.assertNotIn("contradict", kinds(signals, "color"))

    def test_multicolor_title_does_not_deny_a_specific_color_code(self):
        signals = check_row(row(color="Multicolor", color_code="White", title="Men Checkered Casual Multicolor Shirt"))
        self.assertNotIn("contradict", kinds(signals, "color_code", "title_color"))

    def test_gold_in_the_title_confirms_a_gold_attribute(self):
        signals = check_row(row(color="Gold", title="Women Heels Gold", color_code="Maroon"))
        verdict = resolve("color", True, signals)
        self.assertEqual(verdict.verdict, "contested")

    def test_top_and_shorts_may_be_a_kids_combo(self):
        signals = check_row(row(cms_vertical="kids_apparel_combo", title="Baby Girls PartyFestive Top Shorts Pink"))
        self.assertIn("support", kinds(signals, "cms_vertical"))

    def test_styling_clause_is_ignored(self):
        signals = check_row(row(cms_vertical="t_shirt", title="Blue T-Shirt pair it with jeans"))
        self.assertIn("support", kinds(signals, "cms_vertical"))
        self.assertNotIn("contradict", kinds(signals, "cms_vertical"))

    def test_material_antonym(self):
        signals = check_row(row(material="Polyester", title="100% Pure Cotton T-Shirt"))
        self.assertIn("contradict", kinds(signals, "material", "title_material"))

    def test_generic_material_is_not_judged(self):
        signals = check_row(row(material="Fabric", title="Cotton Shirt"))
        self.assertEqual(kinds(signals, "material"), [])

    def test_size_placeholder_is_invalid_and_a_real_size_is_left_alone(self):
        self.assertEqual(kinds(check_row(row(size="NA")), "size"), ["invalid"])
        self.assertEqual(kinds(check_row(row(size="M")), "size"), [])
        self.assertEqual(kinds(check_row(row(size="5 - 6 Years")), "size"), [])

    def test_empty_color_is_not_a_correctness_finding(self):
        self.assertEqual(kinds(check_row(row(color="", title="Blue Shirt")), "color"), [])


if __name__ == "__main__":
    unittest.main()
