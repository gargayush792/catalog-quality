# catalog-quality

Take-home for the catalogue quality problem. Data is an ecommerce lifestyle slice: 120,000 products, 26 columns.

## The metric

It splits into the two parts of quality:

```
completeness = filled / applicable
correctness  = correct / filled
score        = completeness x correctness
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

Processes product catalog entries row-by-row to verify structured metadata against titles and package details.

---

### Step 1: Clean the Title

* **Remove Brand Names:** Drop `brand` and `seller_entered_brand` (case-insensitive, first match, length $\ge$ 3 chars) to avoid false matches (e.g., *"PRATHAM BLUE"* $\rightarrow$ color blue; *"DAKU SHOES"* $\rightarrow$ footwear).
* **Truncate Cross-Sell Text:** Drop text after *"pair it with"*, *"team it with"*, or *"wear it with"* so complementary items aren't misidentified as the main product.

---

### Step 2: Select Applicable Attributes (`cms_vertical`)

Rule-based assignment by vertical:

* **All Products:** `brand`, `ideal_for`, `color`, `cms_vertical`
* **Tops, Dresses, Kurtas, Jackets, Outfits:** + `pattern`, `size`, `sleeve`
* **Bottoms, Sarees, Innerwear:** + `pattern`, `size`
* **Footwear:** + `size`, `outer_material`
* **Jewellery, Bags, Watches, Fabric:** Base attributes only

---

### Step 3: Execute Attribute Checks

Each check yields **`support`**, **`contradict`**, **`invalid`**, or **`nothing`** (no secondary source).

1. **`ideal_for`:** Words must be on the audience whitelist (*men, women, boys, girls, baby, kids, unisex, couple* + filler words like *and/for*); otherwise **`invalid`**. Compare against `analytic_super_category` prefix (`Mens*`, `Women*`, `Kid*`) and title keywords. Only direct opposites flag a conflict (*men* vs *women*, *boys* vs *girls*). Both genders in a title are ignored as keyword stuffing.
2. **`color` / `color_code`:** Map phrases to base colors using longest-phrase-first matching (*light blue* $\rightarrow$ *blue*, *meroon* $\rightarrow$ *maroon*). No fuzzy matching. Compare mapped colors across title and metadata. *Gold/silver/copper* in titles can confirm but never contradict (jewellery metals). *"Multicolor"* in title never contradicts.
3. **`brand`:** Lowercase and strip non-alphanumeric chars (`a-z`, `0-9`). Match if identical or if the shorter string ($\ge$ 3 chars) is inside the longer one. Otherwise flag as **`contradict`**. Title matches count as **`support`**.
4. **`cms_vertical`:** Scan title for product nouns, matching most specific first (*t-shirt* before *shirt*, *earring* before *ring*). Allow `kids_`/`uniform_` prefixes. Two garment nouns or terms like *set/combo/co-ord* map to combo verticals.
5. **`sleeve` / `pattern` / `material`:** Flag direct binary opposites only (*half* vs *full sleeve*, *solid* vs *printed*, *cotton* vs *polyester*). Overlapping attributes (*embroidered* + *printed*) are allowed.
6. **`pack_of`:** Must be a positive integer. Compare with title *"pack of N"*, `sales_package`, and `contents_in_sales_package`.
7. **`size`:** Flag placeholders (*NA*, sentences) as **`invalid`** (no size chart available).

---

### Step 4: Attribute Verdict Priority

Assign a single verdict using strict precedence:

$$\begin{aligned} 1.&\quad \text{Empty value} &\longrightarrow\quad &\mathbf{missing} \\ 2.&\quad \text{Any invalid check} &\longrightarrow\quad &\mathbf{invalid} \\ 3.&\quad \text{Title contradicts value} &\longrightarrow\quad &\text{Drop support from sibling fields (\textit{color\_code}, \textit{contents})} \\ 4.&\quad \text{Support AND contradict} &\longrightarrow\quad &\mathbf{contested} \\ 5.&\quad \text{Contradict only} &\longrightarrow\quad &\mathbf{contradicted} \\ 6.&\quad \text{Support only} &\longrightarrow\quad &\mathbf{supported} \\ 7.&\quad \text{Otherwise} &\longrightarrow\quad &\mathbf{unverified} \end{aligned}$$

---

### Step 5: Scoring

$$\text{clean} = \text{supported} + \text{unverified}$$

$$\text{defect} = \text{contradicted} + \text{invalid} + \text{contested}$$

$$\text{Score} = \frac{\text{clean}}{\text{applicable attributes}}$$

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
