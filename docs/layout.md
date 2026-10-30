# The layout: workspaces, folders, memory and the ledger

Every space of the agency has one herdr workspace, and that workspace is rooted at the space's own folder. The workspace name matches the folder, so what you see in herdr is what you see on disk. `scripts/hq start` builds this layout, and `./setup.sh` creates every folder below on day one.

| herdr workspace / tab | Folder | Agent | What it writes |
| --- | --- | --- | --- |
| HQ | `./` (repository root) | `hq` | `work/briefs/`, the ledger in `work/`, `approvals/`, `reports/`, `memory/` |
| Clients | `clients/` | `clients` | `clients/INDEX.md`, each `clients/<slug>/` (profile, kb, inbox agent prompt, reports, approvals, notes) |
| Inventory | `inventory/` | `inventory` | `inventory/extracted/`, `inventory/master/`, `inventory/review/`, `inventory/clients/<slug>/sheets/` |
| Team | `team/` | `team` | `team/roster.csv`, `team/sops/`, `team/qa/`, `team/checkins/` |
| Growth | `growth/` | `growth` | `growth/pipeline.md`, `growth/proposals/`, `growth/outreach/` (drafts, never sent) |
| Growth / Research | `growth/research/` | `growth-research` | `growth/research/` (findings with sources, read only research) |
| Ops | `ops/` | `ops` | `ops/tools.md`, `ops/vault-policy.md`, `ops/contracts/`, `ops/billing.csv` |

On tmux there are no workspaces, so each agent gets one window with the agent's name, started in the folder above.

## How each space is tied to memory and the ledger

* **Memory.** Every folder in the table has a `CLAUDE.md` that tells its agent to read `memory/MEMORY.md` at the start of every session, and lists the memories tagged to that space (`space:` in a memory's frontmatter). Client folders list the memories tagged to that client (`client:`). `scripts/memory-sync` writes those lists; `/remember` runs it.
* **Ledger.** The same `CLAUDE.md` tells the agent to record every job through `scripts/ledger`: `start` before work, `artifact` for each file, `finish` after inspection. Run from a space's folder, the ledger records that space and folder on the job, and the client slug when the folder is inside `clients/<slug>/` or `inventory/clients/<slug>/`.
* **Dashboard.** Each space's dashboard page ends with the jobs recorded in that space. Each client page shows that client's jobs, the same view as `scripts/ledger view --client <slug>`.
* **Tests.** `tests/test_spaces.py` checks that every row above has a folder that setup creates, a `CLAUDE.md` that names `memory/MEMORY.md` and `scripts/ledger`, a herdr workspace or tab in `scripts/hq` with the same label, a ledger space with the same folder, and that a job written from the folder shows on its dashboard page.

## The tree

```
thinksocial-hq/           HQ workspace, agent hq
├── CLAUDE.md             HQ's job description and the rules for everyone
├── memory/               long term facts and rules, tagged by space and client (private)
├── work/
│   └── briefs/           one brief per job, plus the ledger (private)
├── approvals/            decisions waiting on Desiree
├── reports/              the weekly agency report (private)
├── clients/              Clients workspace, agent clients
│   ├── _template/        the shape of a client folder
│   └── example-boutique/ a fake client, to show the shape
├── inventory/            Inventory workspace, agent inventory
│   ├── drop/             supplier invoices land here (private)
│   ├── extracted/        one JSON per invoice read (private)
│   ├── master/           the master sheet (private)
│   ├── review/           lines held for a person (private)
│   │   └── done/
│   ├── clients/          per client preference, last sheet, new sheets
│   ├── rules/            per client attribution rules
│   └── tools/            invoice_to_rows.py
├── team/                 Team workspace, agent team
│   ├── sops/             training and procedures
│   ├── qa/               spot checks
│   └── checkins/         the weekly VA check in (private)
├── growth/               Growth workspace, agent growth
│   ├── research/         Growth workspace, Research tab, agent growth-research
│   ├── proposals/        one folder per prospect package (private)
│   ├── outreach/         drafts, never sent (private)
│   └── docs/             how a prospect package is built
└── ops/                  Ops workspace, agent ops
    └── contracts/        outlines and checklists
```

## Why Research is a tab, not a workspace

Research and new business are one space with two jobs. The `growth` agent turns findings into sample ads and proposals; the `growth-research` agent finds those facts with sources and writes them to `growth/research/`. Keeping both in the Growth workspace means whoever reads Growth sees the whole pipeline in one place, and the research agent, which is read only, cannot wander into proposals by accident.
