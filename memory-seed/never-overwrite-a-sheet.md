---
name: never-overwrite-a-sheet
description: Every preference sheet the inventory pipeline makes is a new dated file; the previous sheet is never changed and sets the format.
type: feedback
space: inventory
---

Each run writes a new file in `inventory/clients/<slug>/sheets/`. The last sheet a client received sits in `inventory/clients/<slug>/last/` and its column order is the format the new sheet must match, so the person opening it sees what they always see. A correction is a new sheet with a new name, never an edit to an old one.

**Why:** the old sheet is the record of what the client was told and what was typed into their store.

**How to apply:** `inventory/tools/invoice_to_rows.py` refuses to overwrite. Low confidence lines go to `inventory/review/` for a person, never into a sheet.

Related: [[shopify-is-the-inventory-truth]]
