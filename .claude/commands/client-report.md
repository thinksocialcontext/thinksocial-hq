---
description: Write one client's monthly report from the ledger, inbox, ads and inventory activity
argument-hint: "<slug> [YYYY-MM, default last month]"
---

You are HQ. Input: $ARGUMENTS

1. `scripts/ledger view --client <slug>` for every job done for this client; keep the month's.
2. Brief the **clients** agent (`work/briefs/<date>-report-<slug>.md`): gather the month's inbox numbers (drafts made, sent, escalated) from whatever export Desiree or the VA lead dropped in `clients/<slug>/reports/`, ads results if they buy ads, inventory sheets made (`inventory/clients/<slug>/sheets/`) and lines held for review, KB questions opened and answered. Output `clients/<slug>/reports/<YYYY-MM>.md`: the month in three sentences, numbers, what we did, what is next, what we need from the owner. Mark missing numbers plainly; never estimate.
3. Ledger start with `--space clients --client <slug>`, prompt, wait, read the report yourself, finish.
4. Write `approvals/<date>-report-<slug>.md` so Desiree can review before it goes to the client. Never email it.
