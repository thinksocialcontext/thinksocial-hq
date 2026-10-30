---
description: Onboard a client: make the space if needed, then the clients agent works the checklist
argument-hint: "<slug> [client name]"
---

You are HQ. Input: $ARGUMENTS

1. If `clients/<slug>/` does not exist, run `scripts/new-client <slug> --name "<client name>"` (ask Desiree for the name and whether they want holding replies; default no).
2. Write a brief to `work/briefs/<date>-onboard-<slug>.md` for the **clients** agent: goal (work `clients/<slug>/onboarding.md` as far as the files and Desiree's notes allow), context (the profile, whatever handbook, FAQ or site links Desiree gave), output (profile filled, `kb/` built from the client's own words, `inbox-agent/prompt.md` filled, open questions in `kb/questions.md`, `clients/INDEX.md` row correct), boundaries (no contact with the client, no live system, no invented policy or contact), stop condition (every box ticked or turned into a question).
3. `scripts/ledger start --space clients --client <slug> ...`, then `scripts/hq prompt clients` with the brief path and job id.
4. Ask **team** to confirm a VA lead and backup in `team/roster.csv`, and **ops** to list the 1Password vault the client needs (a request, never a credential).
5. When done: record artifacts, read the profile, kb and prompt yourself, finish the record, and tell Desiree what is left and which questions need the client owner.
