---
description: Read every unprocessed invoice in inventory/drop, build the master sheet and preference sheets, hold doubtful lines
---

You are HQ. Brief the **inventory** agent (`work/briefs/<date>-inventory-run.md`):

* Goal: every invoice in `inventory/drop/` that is not yet in `inventory/master/processed.csv` is read and turned into sheets.
* Steps: follow `inventory/CLAUDE.md`. Read each invoice, write `inventory/extracted/<invoice_id>.json` with an honest confidence per line, run `python3 tools/invoice_to_rows.py extracted/<invoice_id>.json`, read every warning.
* Output: new sheets in `inventory/clients/<slug>/sheets/`, held lines in `inventory/review/`, one approval file `approvals/<date>-inventory-run.md` listing both.
* Boundaries: never overwrite a sheet, never edit the master sheet by hand, never write to a store.
* Stop: every dropped invoice is processed or listed as unreadable.

Ledger start with `--space inventory`, prompt, wait. Then open two sheets and one review file yourself, compare a few lines with the invoice image, record artifacts and finish. Tell Desiree how many invoices, lines ready, lines held, and which clients got sheets.
