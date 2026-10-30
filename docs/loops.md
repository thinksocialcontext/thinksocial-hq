# The standing loops

A loop is a job that repeats on a rhythm with the same steps every time. Each one ends at a file and, when something would leave the building, at Desiree's approval. Never at sending.

| Loop | Rhythm | Command | Space and agent | Ends at |
| --- | --- | --- | --- | --- |
| Status | any time | `/status` | HQ | a report to Desiree, grouped by space |
| Client onboarding | each new client | `/client-onboard <slug>` | Clients, `clients` | profile, kb, inbox prompt, open questions |
| Client report | monthly | `/client-report <slug>` | Clients, `clients` | `clients/<slug>/reports/<YYYY-MM>.md` and an approval file |
| Inventory run | daily or when invoices land | `/inventory-run` | Inventory, `inventory` | sheets, review files, an approval file |
| Pipeline | weekly, or a store link | `/pipeline [link]` | Growth, `growth` and `growth-research` | pipeline next steps, or a prospect package |
| VA check in | weekly | `/va-checkin` | Team, `team` | `team/checkins/<date>.md` |
| Friday report | Friday | `/friday-report` | HQ | `reports/<date>-weekly.md` |
| Remember | any time | `/remember <fact>` | HQ | a tagged memory, synced into each space's `CLAUDE.md` |

Every loop opens a ledger job in its space before it starts and closes it after HQ has read the result.

## Making a loop run on a schedule

Start by hand until the steps are stable. Then a loop can be scheduled with cron on the WSL machine, for example every Friday at 3pm:

```
0 15 * * 5 cd ~/thinksocial-hq && scripts/hq prompt hq "/friday-report"
```

Only schedule loops that end at a file or an approval. Never schedule anything that sends, posts, spends or writes to a client system.
