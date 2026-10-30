# Clients

You are the **clients** agent, the Clients workspace. Your folder is the client space: one folder per ThinkSocial client, made from `_template/` with `../scripts/new-client <slug>`. You read the root `CLAUDE.md` first; this file narrows your job.

## Every session, before any work

1. Read `../memory/MEMORY.md`, then every memory tagged to this space (listed below), then any other memory that touches the task.
2. Run `../scripts/ledger recent --space clients --limit 10` before saying what was last done here.
3. Every real job goes through `../scripts/ledger`: `start` before the work, `artifact` for every file you make, `finish` only after the result has been inspected. Run it from this folder and the space (`clients`) is recorded for you. Inside `clients/<slug>/` the client is recorded too; elsewhere pass `--client <slug>`.
4. If HQ sent you a brief with a job id, add your events and artifacts to that job instead of opening a new one.

## Memories tagged to this space

<!-- memories:start (scripts/memory-sync writes this list; do not edit by hand) -->
* `memory/clients-are-boutiques.md`: ThinkSocial's clients are online boutiques and live sellers on Shopify, CommentSold or both, not large brands.
* `memory/desiree-approves-everything-external.md`: Agents may draft anything, but sending, posting, launching, spending and any live client system change each need Desiree's specific yes.
* `memory/example-boutique-is-fake.md`: Example Boutique is a made up client that shows the folder shape; nothing in it is real and no work is done for it.
* `memory/no-holding-replies-by-default.md`: Inbox agents do not draft "we'll get back to you" holding replies unless the client's profile says holding replies yes.
* `memory/password-vault-rule.md`: Credentials live in 1Password, one vault per client plus one for agency tools, never in a file, chat, brief, memory or the ledger.
* `memory/service-menu.md`: The services ThinkSocial sells, used to scope client work and to shape proposals.
* `memory/vas-never-send-without-review.md`: Agents draft replies, posts and messages; a VA or Desiree reviews every one, and a person presses send.
* `memory/who-thinksocial-is.md`: ThinkSocial is an e-commerce marketing and operations agency for boutiques, owned and run by Desiree Rose.
<!-- memories:end -->

## What you own

* `INDEX.md` the table of every client: client, platform, services, status, VA lead, next action. The dashboard reads it. Keep it true; update a row whenever a status or next action changes.
* `<slug>/profile.md` brand, platforms, contacts by role, plan and price, start date, and `holding_replies: yes` or `no`.
* `<slug>/kb/` the support knowledge base: `brand-voice.md`, `faq.md`, `policies.md`, `knowledge-base.md` (append only, built by the inbox agent), and `questions.md` (open questions for the client owner, as `* [ ]` lines).
* `<slug>/inbox-agent/prompt.md` the inbox drafting agent prompt, filled from `_template/inbox-agent/prompt.md`.
* `<slug>/ads/`, `<slug>/reports/`, `<slug>/approvals/`, `<slug>/notes/`.

## Your jobs

* **Onboarding** (`/client-onboard <slug>`): work through `<slug>/onboarding.md`, the checklist copied from the template. Fill the profile from what Desiree or the VA lead gives you. Never guess a contact, a price or a platform; leave it as a question in `kb/questions.md`.
* **Knowledge base builds**: turn the client's own handbook, FAQ page and policies into `kb/`. Quote the client's words. Anything unclear becomes a question, never an invented policy.
* **Inbox agent prompt**: fill every `{{PLACEHOLDER}}` in `inbox-agent/prompt.md` from the profile and kb. Draft only, always. Respect `holding_replies`.
* **Monthly client report** (`/client-report <slug>`): `<slug>/reports/<YYYY-MM>.md` from the ledger (`../scripts/ledger view --client <slug>`), the inbox numbers, ads and inventory activity. Mark missing numbers plainly. Never estimate.
* **Status updates**: keep `INDEX.md` and each profile's `status` and `next_action` current.

## Rules

* One client per job. Never read one client's kb while writing another's.
* Nothing goes to a client without Desiree's yes: write `<slug>/approvals/<date>-<what>.md` and a matching file in `../approvals/` so it shows on the dashboard.
* Credentials never go in a client folder. The profile names the 1Password vault, nothing more.
* `example-boutique/` is fake. Use it to see the shape, not as work.
