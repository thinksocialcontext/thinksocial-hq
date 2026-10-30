---
name: example-boutique-is-fake
description: Example Boutique is a made up client that shows the folder shape; nothing in it is real and no work is done for it.
type: reference
space: clients
client: example-boutique
---

`clients/example-boutique/` and `inventory/clients/example-boutique/` are fake. The names, emails, numbers and invoices in them are invented.

**Why:** a fake client shows the shape of a real one without putting any real client's data in the repository.

**How to apply:** copy its shape with `scripts/new-client <slug>`, never its content. Do not run inbox agents or reports for it except as a test.

Related: [[clients-are-boutiques]]
