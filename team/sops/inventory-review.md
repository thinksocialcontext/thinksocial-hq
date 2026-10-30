# Checking held invoice lines

The inventory agent holds any line it does not trust in `inventory/review/<invoice>.csv`. Nobody near the product checks the count, so this check is the only one.

1. Open the review file and the original invoice from `inventory/drop/` side by side.
2. For each line, compare the SKU, item and quantity with the invoice. Read the `reason` column.
3. Write your decision in `note`: confirmed, corrected to N, or not on this invoice.
4. Move the file to `inventory/review/done/` and tell the inventory agent. A corrected line is re read as a new extracted invoice; the master sheet is never edited by hand.
