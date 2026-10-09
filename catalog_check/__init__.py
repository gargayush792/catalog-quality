"""Correctness checks for an ecommerce catalogue slice.

Completeness asks whether a cell is filled. Correctness asks whether a filled
value is true of the product. This slice has no ground truth, so a value is
not marked correct just because it is present.

Each check looks for a second source on the same row: the analytics taxonomy,
another attribute, or a phrase in the title. The description is not used. It
is empty on about a third of rows, and when it is present it is marketing
copy that sometimes describes a different product than the title.

A sibling column (color against color_code, pack_of against contents) can confirm a value when the title is silent. It cannot outvote the title, because the two columns are often the same entry typed twice.

A filled value ends in one bucket:

- supported: a second source agrees, and none disagrees
- contradicted: a second source disagrees, and none agrees
- contested: one source agrees and another disagrees
- invalid: the value is not a possible value for that attribute
- unverified: nothing else on the row speaks to it

Unverified is not correct. Contested is a review item, not a silent pass.
"""

__version__ = "1.0.0"
