# Current work and next steps

Updated October 15, 2026. Source status is distinct from live deployment.

## Implemented in this repository

- Optional Jan interpreter with validated task mutations and durable receipts.
- Existing outbound PC/Site sync; SQLite remains task authority.
- Relevant older shared-history retrieval and incremental archive backfill.
  Hosted export patch is included; new retrieval is not yet live-verified.
- Signed calendar bridge with strict retry-content comparison, including insert
  collisions. Existing live version 3 was reported verified October 15; this
  update does not create events or redeploy the bridge.
- Persistent email candidate queue, deferred resurfacing, weekday 11:15 Central
  routine, bounded follow-ups, and local revision-bound drafts. Not activated.

## Product priority: personal companion and co-working

This roadmap now follows the [Kiki Companion vision](KIKI_COMPANION_VISION.md). The goal is not primarily autonomous email or grading. Kiki should be an engaging, recognizable assistant who helps the owner begin, stay with, and resume work through a voice-first relationship. This is a single-user personal tool, designed to be fun to develop and pleasant to use.

**Milestone C1: private Chrome companion shell.** Add an unpacked Manifest V3 side panel with the existing Kiki visual identity, a current task, and chat. Connect it to the already-running local Python/Jan service rather than creating a second Kiki process or second task database. Verify that conversation, pause, and task status match the current dashboard. Store distribution is not required.

**Milestone C2: durable co-working sessions.** Implement the [Work Sessions contract](WORK_SESSIONS.md) in the existing operational ledger. Kiki initiates a helpful next action, stays in the conversation, records completion, and remembers where to resume after a browser close, interruption, or restart. A notification that says only "open the dashboard" does not meet the goal.

**Milestone C3: live-feeling voice and presence.** Connect local speech input/output or another verified voice backend. Display the animated Kiki avatar with useful states such as greeting, listening, speaking, and waiting. Preserve personality from Kiki-Mind and maintain the same session and commitments in text, voice, Telegram, ChatGPT, and the Site.

**Milestone C4: first useful workday session.** Kiki brings forward one email or test-mailbox task, collaborates on a locally prepared draft, guides review, and maintains momentum across a short queue. A Playwright web adapter is an optional execution helper, not a prerequisite for companionship. See [Browser Companion v0.1](BROWSER_COMPANION_V01.md) and [Email Assistant](EMAIL_ASSISTANT.md).

**Milestone C5: capability expansion.** Add contextual browsing for Canvas, administrative forms, and research; evaluate Playwright MCP; consider Muse delegation with bounded task handoffs and verified results. Do not recreate Muse's broad agent infrastructure inside Kiki unless needed.

For C1 and C2, the acceptance demo is straightforward: the private sidebar loads; the owner can engage Kiki; Kiki introduces one next action without the user opening a separate task list; then after interruption Kiki accurately resumes it. Keep statuses honest: these milestones are planned, not currently running.

## Existing email automation track

## Browser-based email implementation details

1. Reuse Microsoft Playwright rather than writing a browser driver. Begin with
   a dedicated persistent local browser profile, signed into by the owner.
   Alternatives researched: Browser Use, Stagehand, and Playwright MCP.
2. Build a restricted adapter exposing find/read/save-draft operations. General
   browser clicking can send mail despite a local flag; draft-only requires
   enforcement and testing at the adapter boundary, including keyboard paths.
   No unrestricted browser tools should be exposed to Jan.
3. Prove read -> local draft -> verified mailbox draft on a synthetic/test
   mailbox. Test expired login, page changes, partial saves, and interrupted
   retries. No send/delete/archive actions. Email text is untrusted data.
4. Match priority contacts from actual mailbox evidence and distinguish direct
   student requests from Canvas announcements. Names alone are not verified
   addresses. Personal contact configuration belongs outside public source.
5. Connect the adapter to the existing queue and 11:15 weekday scheduler.
   Preserve deferred work; report failed scans distinctly from an empty queue.
6. Add one-conversation-at-a-time spoken drafting and review. Kiki initiates and
   brings the request forward; requiring the user to remember a dashboard is
   insufficient. Verify the voice integration rather than assuming availability.
7. Sending remains disabled during this phase. Any future send implementation
   requires approval of the specific recipient and final reply, plus verified
   provider outcome and uncertain-result reconciliation.

## Deployment and verification still needed

Publish the hosted context patch and restart the existing PC service after a
controlled rollout; verify old-topic retrieval using the real local model.
Retain one Telegram poller and outbound-only PC connectivity. Work-calendar
subscription freshness, observed calendar reminders, real reboot/sign-in
acceptance, and Outlook subscription refresh remain separate unverified items.

Project sources: https://github.com/microsoft/playwright,
https://github.com/browser-use/browser-use,
https://github.com/browserbase/stagehand,
https://github.com/microsoft/playwright-mcp.
