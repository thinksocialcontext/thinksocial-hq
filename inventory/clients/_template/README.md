# Inventory folder for one client

* `preference.json` the columns of this client's preference sheet and how they map to master sheet fields.
* `last/` the last preference sheet this client received (a CSV export of it). Its column order is the format every new sheet copies.
* `sheets/` new sheets made by `tools/invoice_to_rows.py`, one dated file per invoice. Never edited, never overwritten. Not committed.
