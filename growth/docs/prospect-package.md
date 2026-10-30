# The prospect package

When Desiree drops a prospect's store link, Growth builds one package. Nothing in it goes to the prospect until Desiree says yes.

1. **Ledger.** `scripts/ledger start --space growth --title "Prospect package: <name>"` from `growth/`.
2. **Pipeline.** Add or move the row in `pipeline.md` to `researching`.
3. **Research** (the Research tab, read only). Brief `growth-research` with an objective and a stop condition: what they sell and on which platforms (Shopify, CommentSold, both), what ads they run now, what their reviews and comments say in customers' own words, and two or three competitors. Output `growth/research/<date>-<slug>.md`, every finding with a source.
4. **F.O.C.U.S. rundown.** From the research, the customers' voice in five buckets: Frustration, Outcome, Constraint, Unspoken cost, Skepticism. Verbatim quotes with links. `proposals/<slug>/focus.md`.
5. **10 sample ads.** Stills built from the prospect's real product photos and their customers' words, one F.O.C.U.S. letter each, two per letter. A fresh pass checks every still for the right product, readable text and the right logo before anyone sees it. Labelled samples. `proposals/<slug>/ads/`.
6. **Proposal.** `proposals/<slug>/proposal.md`: what we saw, what we would do first, which services, the price Desiree sets. ThinkSocial's look (`memory/design-system-pointer.md`).
7. **Approval.** `approvals/<date>-proposal-<slug>.md`, pipeline stage `package ready`, ledger artifacts recorded, then stop.
