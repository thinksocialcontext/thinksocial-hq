---
description: Save a fact or rule as a memory, tagged to a space or a client, and index it
argument-hint: "[the fact or rule]"
---

Follow `docs/memory.md`. Input: $ARGUMENTS

1. **Ask which space or client it belongs to** before writing, unless it is obvious from the words: one or more of `hq`, `clients`, `inventory`, `team`, `growth`, `growth-research`, `ops`; `all` for agency wide rules; or a client slug from `clients/INDEX.md`.
2. Search `memory/` for an existing memory on the same subject. Update it rather than adding a duplicate.
3. Otherwise create `memory/<short-kebab-name>.md` with the frontmatter (name, description, type, `space:` and, for one client, `client:`) and the body: the fact or rule, a **Why:** line, a **How to apply:** line, and `[[links]]` to related memories.
4. Add or update its one line in `memory/MEMORY.md`.
5. Run `scripts/memory-sync` so that space's (or client's) `CLAUDE.md` lists it.
6. Never store a password, token, a customer's personal details, or anything Desiree asked to keep out.
7. Tell Desiree in one sentence what you saved and where it is tagged.
