---
name: no-holding-replies-by-default
description: Inbox agents do not draft "we'll get back to you" holding replies unless the client's profile says holding replies yes.
type: feedback
space: clients, team
---

A holding reply commits to nothing ("We have your message and a member of our team will get back to you shortly"). By default ThinkSocial does not use them: when the agent cannot answer, it leaves an internal note and the VA writes the real reply or escalates. A client who wants holding replies says so, and their `profile.md` records `holding_replies: yes`.

**Why:** a holding reply can read as a brush off, and it hides the fact that nobody has answered yet.

**How to apply:** read `holding_replies` in the client's profile before drafting. If it is missing, treat it as no.

Related: [[vas-never-send-without-review]]
