# Relevant shared history for Jan

The recent six-turn shared cache is supplemented by a private SQLite archive.
On each authenticated desktop exchange the PC supplies `context_after`. The
Site exports up to 100 committed owner-scoped turns in ascending assistant
event sequence. The PC validates and persists the page before advancing a
separate cursor. Retries do not duplicate turns; an empty page cannot jump the
cursor. Recent-context sequence never skips archive backfill.

Jan's worker passes the current request into `context(query)`. Matching words
rank archived exchanges, breaking ties by recency. Up to two matches use at
most 800 characters of the existing 1600-character formatted-dialogue budget;
remaining space holds recent dialogue. Retrieved turns retain their source,
timestamp and turn ID. Dialogue remains untrusted evidence, not instructions.

This is lexical retrieval, not semantic search or unrestricted ChatGPT access.
Only explicit Kiki turns recorded in the shared ledger are available. Exported
messages are capped at 600 characters; selected historical excerpts at 160.
Topics beyond those excerpts and synonym-only matches may be missed. The
current implementation scans the local archive; indexing is a later scaling
improvement. No email bodies are added to this archive by the email code.

## Hosted counterpart

The Site is maintained in a separate source tree based on
`f2945fe76ea9240c703dd802a744a0022de927b7`. The accompanying
`integrations/site-context.patch` contains the archive-export change and its
owner-isolation/pagination tests against that base. Apply it in that Site tree,
run `node --test tests/*.test.mjs`, and publish through the Site's existing
deployment workflow. This repository push does not deploy the Site or restart
Windows services. The previous deployed Site remains compatible but supplies
only the recent cache until this counterpart is published.

Acceptance: an old recorded ChatGPT fact, absent from recent jobs, must appear
with attribution in a real Jan inference request after backfill and restart.
Automated tests inspect the inference request; live model/deployment acceptance
of this new archive path is still pending.
