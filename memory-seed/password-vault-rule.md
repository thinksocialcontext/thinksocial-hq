---
name: password-vault-rule
description: Credentials live in 1Password, one vault per client plus one for agency tools, never in a file, chat, brief, memory or the ledger.
type: feedback
space: ops, clients
---

Every login, API key and token lives in 1Password. Each client has its own vault; agency tools have one shared vault. Each item carries a note: who may use it and for what. Agents never ask for, print, copy or store a credential. The ledger refuses text that looks like one.

**Why:** with dozens of clients and VAs, one leaked store login is one client's business exposed.

**How to apply:** when a task needs access, write what access is needed in the approval file and let Desiree or the ops lead grant it. Never paste a key into `.env` on a shared machine. See `ops/vault-policy.md`.

Related: [[desiree-approves-everything-external]]
