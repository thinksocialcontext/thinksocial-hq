---
description: The weekly VA check in: coverage, hours, QA, escalations, questions for Desiree
---

You are HQ. Brief the **team** agent (`work/briefs/<date>-va-checkin.md`) to write `team/checkins/<date>.md` from:

* `team/roster.csv` and `clients/INDEX.md`: any client without a VA lead or backup, any VA over or under their hours. These go first.
* `team/qa/qa-log.csv` for the week: passes, fixes, patterns.
* `scripts/ledger recent --space team` and `--space clients` for escalations and finished work.
* Open questions to Desiree.

Ledger start with `--space team`, prompt, wait, read the file yourself, finish. It is a draft for Desiree or the VA director; no agent messages the team.
