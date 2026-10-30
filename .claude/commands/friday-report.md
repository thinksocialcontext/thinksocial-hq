---
description: Write the weekly agency report across every space
---

You are HQ. Gather, do not guess:

* `scripts/ledger recent --limit 100`: what finished, failed or was abandoned, grouped by space.
* `clients/INDEX.md` and each profile: status changes, next actions, open KB questions.
* Inventory: invoices read this week, lines ready, lines held, sheets made (`python3 scripts/dashboard.py --once`, key `inventory`).
* `team/checkins/` newest file: coverage and QA.
* `growth/pipeline.md`: movement by stage, value.
* `ops/billing.csv`: anything overdue; `ops/tools.md`: renewals in the next 30 days.
* `approvals/`: anything still waiting.

Write `reports/<YYYY-MM-DD>-weekly.md`: the week in three sentences, then one short section per space, then decisions Desiree needs to make next week. Mark sample or missing data plainly. No dashes. Record it in the ledger (space hq) and tell Desiree where it is. Do not email it.
