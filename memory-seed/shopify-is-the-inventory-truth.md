---
name: shopify-is-the-inventory-truth
description: For inventory, Shopify is the source of truth; CommentSold is never written directly for a client who has Shopify.
type: project
space: inventory
---

For a client on Shopify and CommentSold, received stock is written to Shopify only, at the My Ship Manager default location, and My Ship Manager carries it into CommentSold. Writing CommentSold as well can double the stock. A client on CommentSold alone gets a work order sheet a person types in. Three silent zeros look like out of stock in CommentSold: a product with no description, a negative quantity, or stock at a non default Shopify location.

**Why:** two writers for one number is how stock doubles or vanishes.

**How to apply:** the inventory agent prepares sheets; any store write is a separate, approved step. Check for the three silent zeros when a sheet is reviewed.

Related: [[never-overwrite-a-sheet]] [[clients-are-boutiques]]
