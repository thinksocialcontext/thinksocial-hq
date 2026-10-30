# Master sheet

`master.csv` holds every invoice line ever read, one row per line:

| Column | Meaning |
| --- | --- |
| invoice_id | the supplier's invoice number |
| supplier | supplier name as printed |
| date | invoice date, YYYY-MM-DD |
| client | client slug, blank when nobody could be decided |
| sku | the vendor's SKU exactly as printed |
| item | item name as printed |
| qty | quantity received, a whole number |
| unit_cost | cost per unit, two decimals |
| status | `ready` (went into a client sheet) or `needs_review` (held in `review/`) |

`processed.csv` records each invoice once, with its source file and when it was read. Both files are appended to, never rewritten, and stay on this computer.
