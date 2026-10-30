# The work ledger

The ledger is the shared record of every real job: who was asked, in which space, for which client, what the brief said, what happened, what was produced, and how it ended. Nobody has to scroll an agent's terminal to find out what happened yesterday.

* **Records:** `work/<date>-<title>-<id>.md`, one readable Markdown file per job.
* **Journal:** `work/.ledger/events.jsonl`, one line per change, append only.
* **State:** `work/.ledger/jobs/<id>.json`.

`work/` is not committed to git.

## Spaces and clients

Every job carries a **space** (the herdr workspace it belongs to: `hq`, `clients`, `inventory`, `team`, `growth`, `growth-research`, `ops`), the **folder** of that space, and a **client** slug when the job is for one client.

* Run `scripts/ledger start` from a space's folder and the space is filled in for you.
* Run it from inside `clients/<slug>/` or `inventory/clients/<slug>/` and the client is filled in too.
* From anywhere else (HQ in the root), pass `--space` and `--client`.
* `scripts/ledger spaces` prints every space and its folder.

## Commands

```
id=$(scripts/ledger start --key 2026-11-02-inventory-run --agent inventory --space inventory \
      --title "Read this week's invoices" --brief work/briefs/2026-11-02-inventory-run.md)
scripts/ledger event "$id" --state running --note "Reading four invoices."
scripts/ledger artifact "$id" inventory/clients/example-boutique/sheets/2026-10-26-INV-EX-1001.csv --note "sheet"
scripts/ledger event "$id" --state waiting_approval --note "Approval file written."
scripts/ledger finish "$id" --status done --outcome "Four invoices read, 31 lines ready, 2 held for review."

scripts/ledger recent --limit 10                     # everything, newest first
scripts/ledger recent --space inventory               # one space
scripts/ledger view --client example-boutique         # one client's jobs as a Markdown table
scripts/ledger show "$id"
```

States: `dispatched`, `running`, `blocked`, `waiting_approval`, then one of `done`, `failed`, `abandoned`.

## The rules

1. **What gets a record:** delegated work, research that reaches a conclusion, anything that makes files, anything that changes something outside. Quick questions and status checks do not.
2. **The dispatcher owns the record.** HQ opens it *before* prompting a specialist, puts the job id in the brief, records the artifacts and closes it *after* inspecting the result. A specialist may add events and artifacts, but correctness never depends on it remembering.
3. **Everything ends.** A crash, a rate limit, or a job Desiree cancels still gets `finish --status failed` or `abandoned` with the reason.
4. **One record per assignment,** including retries. A retry is an event, not a new job.
5. **`--key` makes `start` safe to repeat.** Use something stable like the date plus a slug. Running `start` twice with the same key returns the same job.
6. **No secrets.** The ledger refuses text that looks like a password, token or API key.
7. **Session start:** every agent runs `scripts/ledger recent --space <its space>` before saying what was last done there.
