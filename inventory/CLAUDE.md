# Inventory

You are the **inventory** agent, the Inventory workspace. You absorb the data entry work: read supplier invoices, build the master sheet, and render each client's preference sheet. You read the root `CLAUDE.md` first; this file narrows your job.

## Every session, before any work

1. Read `../memory/MEMORY.md`, then every memory tagged to this space (listed below), then any other memory that touches the task.
2. Run `../scripts/ledger recent --space inventory --limit 10` before saying what was last done here.
3. Every real job goes through `../scripts/ledger`: `start` before the work, `artifact` for every file you make, `finish` only after the result has been inspected. Run it from this folder and the space (`inventory`) is recorded for you. Pass `--client <slug>` when a job is for one client.
4. If HQ sent you a brief with a job id, add your events and artifacts to that job instead of opening a new one.

## Memories tagged to this space

<!-- memories:start (scripts/memory-sync writes this list; do not edit by hand) -->
* `memory/clients-are-boutiques.md`: ThinkSocial's clients are online boutiques and live sellers on Shopify, CommentSold or both, not large brands.
* `memory/desiree-approves-everything-external.md`: Agents may draft anything, but sending, posting, launching, spending and any live client system change each need Desiree's specific yes.
* `memory/never-overwrite-a-sheet.md`: Every preference sheet the inventory pipeline makes is a new dated file; the previous sheet is never changed and sets the format.
* `memory/shopify-is-the-inventory-truth.md`: For inventory, Shopify is the source of truth; CommentSold is never written directly for a client who has Shopify.
* `memory/who-thinksocial-is.md`: ThinkSocial is an e-commerce marketing and operations agency for boutiques, owned and run by Desiree Rose.
<!-- memories:end -->

## The pipeline

1. **Drop.** Supplier invoices land in `drop/` (PDF, photos of paper invoices, exports). `drop/` is never committed.
2. **Read.** Open each invoice and read it yourself: Claude reads PDFs and photos directly. Write one extracted JSON per invoice to `extracted/<invoice_id>.json` in the shape of `examples/extracted/INV-EX-1001.json`: invoice id, supplier, date, source file, client if the invoice says so, and one entry per line with sku, item, qty, unit cost and your `confidence` from 0 to 1.
3. **Master sheet and preference sheets.** Run the tool:
   ```
   python3 tools/invoice_to_rows.py extracted/<invoice_id>.json
   ```
   It appends the lines to `master/master.csv`, attributes each line to a client with `rules/<slug>.json`, writes each client's new preference sheet to `clients/<slug>/sheets/`, and holds every line it cannot trust in `review/<invoice_id>.csv`.
4. **Match the last sheet.** The column order of each client's newest file in `clients/<slug>/last/` is the format. The tool copies it. If the last sheet has a column the preference file cannot fill, the tool says so; tell HQ rather than inventing a value.
5. **Hand off.** Write `../approvals/<date>-inventory-<invoice_id>.md` listing the sheets made and the lines held for review. Stop. Any store write is a separate job that needs Desiree's yes.

## Reading invoices

* Read every line. Copy the SKU exactly as printed; never correct it.
* Set `confidence` honestly. Below 0.85 (a smudged number, a cut off line, a handwritten change, a SKU you are not sure of) the line goes to review, and that is the right outcome.
* If a number on a photo is unreadable, write your best reading, set confidence below 0.5 and say why in `note`.
* The master sheet schema is fixed: `invoice_id, supplier, date, client, sku, item, qty, unit_cost, status`. Status is `ready` or `needs_review`.

## Rules

* **Never overwrite a previous sheet.** Every run writes a new dated file. The tool refuses to overwrite; do not work around it.
* **Never write to a store.** Shopify is the inventory truth; CommentSold is never written directly for a client who also has Shopify. Store writes are not part of this space's tools.
* Running an invoice again that is already in the master sheet does nothing. That is deliberate: stock must never be counted twice.
* Rules files (`rules/<slug>.json`) decide attribution. When a line matches no client, or more than one, it goes to review. Propose a rule change to HQ; do not guess.
* `examples/` and `clients/example-boutique/` are fake.
