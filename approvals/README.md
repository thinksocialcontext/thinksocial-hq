# Approvals

Anything that needs Desiree's yes goes here as one Markdown file. The dashboard lists every file whose status is `waiting`.

```
---
title: Send the October report to Example Boutique
from: clients
kind: client report
client: example-boutique
asked: 2026-11-02
status: waiting
---

What: the monthly report, ready to send to the client owner.
Where to look: clients/example-boutique/reports/2026-10.md
Risk: none until sent. Desiree sends it, or says which VA may.
```

Desiree changes `status` to `approved` or `rejected` (or tells HQ, and HQ edits it). Agents act only on `approved`, and record the approval in the ledger.
