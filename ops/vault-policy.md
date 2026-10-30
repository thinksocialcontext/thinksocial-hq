# Password vault policy

ThinkSocial keeps every credential in **1Password**. This file is the policy; it never holds a credential.

## The shape

* **One vault per client,** named exactly like the client in `clients/INDEX.md`. It holds that client's store, inbox, ad account and app logins and API keys.
* **One shared vault, Agency tools,** for ThinkSocial's own accounts.
* Every item carries a note: who may use it, for what, and who granted it.

## Who gets what

* A VA gets access only to the vaults of the clients they work on (`team/roster.csv`), and only to the items their role needs.
* When a VA leaves or changes clients, ops removes access the same day and records it in `ops/access-log.md` (private).
* Agents never hold a credential. When an agent needs access, it says so in an approval file; a person grants it through a connector or a service account.

## Never

* Never put a password, token, API key, card number or bank detail in a file, a chat, a brief, a memory, a Slack message, an email or the ledger. The ledger refuses text that looks like one.
* Never share a login by copying it. Share the 1Password item.
* Never reuse a password across clients.

## When something leaks

Change the credential first, then tell Desiree, then write what happened in `ops/incidents.md` (private).
