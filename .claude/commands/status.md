---
description: Read every agent, the ledger by space and the approvals, then report what needs Desiree
---

Read the live state; do not answer from memory.

1. `scripts/hq list`, then `scripts/hq read <agent> 60` for any agent that is working or blocked.
2. `scripts/ledger recent --limit 25` (each line shows its space and client).
3. Every file in `approvals/` whose status is `waiting`.
4. `python3 scripts/dashboard.py --once` for the space numbers: clients with open KB questions, invoices in `inventory/drop/` not yet read, lines held for review, roster coverage gaps, pipeline value by stage.

Report grouped by space (HQ, Clients, Inventory, Team, Growth, Ops), and inside each space in this order, one line each, naming the file or decision:

* Decisions waiting on Desiree
* Blocked work (quote the dialog's question; never answer it)
* Finished since the last report
* Important work still running
* Idle agents, only if useful

If nothing needs Desiree, say so in one sentence. No dashes.
