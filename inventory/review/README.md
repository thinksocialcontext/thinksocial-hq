# Review

One CSV per invoice with every line the tool would not trust: low confidence, no client, more than one possible client, a missing SKU or a bad quantity. A person checks each line against the invoice image, writes the decision in `note`, and moves the file into `review/done/`. A corrected line becomes a new extracted invoice (for example `INV-1001-r1`), never an edit to the master sheet.
