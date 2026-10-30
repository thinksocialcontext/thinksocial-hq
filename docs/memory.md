# How ThinkSocial HQ remembers

Agents forget everything when a session ends. The `memory/` folder is how they remember facts and rules between sessions, and how every agent shares them.

## The shape

* `memory/MEMORY.md` is the **index**. One line per memory: a link and a short summary. Every agent reads it at the start of every session.
* Every other file holds **one fact or one rule**. Small files are easy to find, update and trust.

```
---
name: no-holding-replies-by-default
description: One sentence that says what this memory is, specific enough to decide whether to open it.
type: feedback
space: clients, team
client:
---

The fact or the rule, in plain words. Dates for anything that changes.

**Why:** the reason it matters, or the event that taught it.

**How to apply:** when and how an agent should use it.

Related: [[vas-never-send-without-review]]
```

### Tags: space and client

* `space:` one or more of `hq`, `clients`, `inventory`, `team`, `growth`, `growth-research`, `ops`, separated by commas, or `all` for agency wide rules.
* `client:` a client slug, for a fact about one client only (their owner's preferences, a standing exception).

`scripts/memory-sync` writes, into each space's `CLAUDE.md`, the list of memories tagged to that space, and into each `clients/<slug>/CLAUDE.md` the memories tagged to that client. So an agent sees its own memories the moment it starts, and still reads the full index. `/remember` asks which space or client a new memory belongs to and runs the sync.

### The four types

| type | holds | example |
| --- | --- | --- |
| `user` | who Desiree is and how she likes to work | prefers a short summary first |
| `feedback` | a rule Desiree gave or a lesson from a mistake | no holding replies by default |
| `project` | facts about the agency or a client that change over time | the service menu |
| `reference` | where things are and how tools are set up | the design system pointer |

## When to save

Save a memory when Desiree states a preference or a rule, corrects an agent, a fact about the agency or a client changes, or a mistake costs time and has a clear lesson. Do not save one off task details (those go in the ledger), anything secret, customers' personal details, or guesses.

## How to save

Use `/remember <the fact>`, or by hand: search `memory/` first and update rather than duplicate; write the file with frontmatter and tags; add its line to `MEMORY.md`; run `scripts/memory-sync`. A wrong memory is worse than none, so fix or delete it the moment it is wrong.

## Where it lives

`./setup.sh` copies the starter memories from `memory-seed/` into `memory/`. After that, `memory/` belongs to the agency and is **not committed to git**, so client facts never end up in the repository.
