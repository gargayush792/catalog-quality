# catalog-quality

Take-home for the catalogue quality problem. Data is an ecommerce lifestyle slice: 120,000 products, 26 columns.

## The metric

It splits into the two parts of quality:

```
completeness = filled / applicable
correctness  = correct / filled
score        = completeness x correctness
```

```
Catalog Quality Score = correct values / applicable values
```

- **applicable**: attributes this product type is supposed to have. Example: A necklace cannot have a sleeve, and size should be present for shoes.
- **correct**: the value is filled, and title/other attributes on the same row don't disagree with it.

On this data:

```
92.56% completeness x 98.74% correctness = 91.40%
671,675 clean out of 734,874 applicable values
```

Most of the quality drop is because of missing values, and not wrong ones. Per attribute:

| attribute | score |
| --- | --- |
| brand | 99.98% |
| cms_vertical | 98.80% |
| ideal_for | 97.51% |
| pattern | 95.99% |
| size | 86.52% |
| color | 83.75% |
| outer_material | 79.44% |
| sleeve | 66.51% |

## Process

In the live round I tried two things:

1. Normalise the colour, then look for it in the description.
2. Check whether the title and the description are semantically similar.

For the take-home I moved the checks to the title. The description is empty for about 30% of rows (36,700). Where it does exist, it's mostly marketing text, and sometimes it describes a different product (one Bata men's shoe description says it is designed for women). The title is always filled and is closer to what the seller actually listed. I kept the colour normalisation from the first idea, but it is matched against the title and `color_code` instead of the description.

## Algorithm

For each product:

**1. Clean the title**

- Remove `brand` and `seller_entered_brand` from the title (case-insensitive, first match, only if the brand has 3+ characters). Otherwise "PRATHAM BLUE" reads as the colour blue, and "DAKU SHOES" as a shoe.
- For the product type check only: cut everything after "pair it with" / "team it with" / "wear it with".

**2. Decide which attributes apply, from `cms_vertical`**

These are keyword rules curated by hand, not learned from the data.

- All products: brand, ideal_for, color, cms_vertical
- Tops, dresses, kurtas, jackets, outfits: + pattern, size, sleeve
- Bottoms, sarees, innerwear: + pattern, size
- Footwear: + size, outer_material
- Jewellery, bags, watches, fabric: nothing extra

**3. Run the checks**

Each check returns support, contradict, invalid, or nothing (when the row has no second source).

- **ideal_for**: every word must be on a fixed audience list (men, women, boys, girls, baby, kids, unisex, couple, plus filler words like "and"/"for"), otherwise it's invalid. Compare with the `analytic_super_category` prefix: `Mens*` = men, `Women*` = women, `Kid*` = boys or girls. Then compare with Men/Women/Boys/Girls words in the title. Only direct opposites are flagged (men vs women, boys vs girls). "For girls" on a women's product is ignored. A title that names both men and women is ignored as keyword stuffing.
- **color and color_code**: map each to a colour family using a handwritten phrase list, longest phrase first (light blue / navy → blue, cream / off white → white, meroon → maroon, wht → white). There is no fuzzy matching. Compare against colours in the title, and against each other. Gold/silver/copper in the title can confirm a value but not contradict one, because on jewellery those words are usually the metal. "Multicolor" in the title doesn't deny a specific colour.
- **brand**: lowercase both brands and keep only a–z and 0–9. They count as the same brand if they're equal, or if the shorter one (3+ characters) appears inside the longer one. Otherwise that's a contradiction ("BG TEX" vs "BG TAX", "3SIX5" vs "Aayu"). If the title contains the brand, that counts as support.
- **cms_vertical**: match product nouns in the title, most specific first (t-shirt before shirt, earring before ring, "shirt stud" / "saree cover" before shirt / saree). `kids_` and `uniform_` variants are allowed. Two garment nouns, or the words set / combo / co-ord, allow the combo verticals.
- **sleeve, pattern, material**: only explicit opposites are flagged (half vs full sleeve, solid vs printed, cotton vs polyester). Embroidered vs printed is not a conflict, since one garment can be both.
- **pack_of**: must be a positive integer. Compare with "pack of N" in the title or `sales_package`, and with `contents_in_sales_package` when that number differs.
- **size**: there's no size chart in the data, so only placeholders like NA, or sentences, are marked invalid.

**4. One verdict per attribute, in this order**

1. empty → missing
2. any invalid → invalid
3. if the title contradicts the value, drop support from a sibling column (color_code, contents), because that is often the same entry copied twice
4. support and contradict together → contested
5. contradict → contradicted
6. support → supported
7. else → unverified

**5. Score**

- clean = supported + unverified
- defect = contradicted + invalid + contested
- score = clean / applicable

## Run

```bash
python3 -m unittest discover -s tests -q
python3 -m catalog_check "/path/to/catalog_slice_v1.csv" --out output
```

The outputs:

- `output/report.txt`: score and per-attribute breakdown
- `output/summary.json`: same numbers
- `output/review.csv`: every flagged value, with the rule and the reason

## Limitations and next steps

- The rules and the applicability map are handwritten from looking at this data. I haven't measured the precision of each rule. The next step is to label a few hundred products per vertical, which gives real accuracy and shows which rules can be trusted.
- The description isn't used. Where it's present, it can be added as a third source (the colour lookup from the live round), but as support or a tie-breaker, not as a contradiction on its own.
- Title–description similarity (embeddings) could catch descriptions that are about a different product. That's a separate "description quality" check.
- Images would be the actual ground truth for colour, pattern and sleeve.
- Attributes could be weighted by importance per vertical (colour and size matter more for apparel than for jewellery).
