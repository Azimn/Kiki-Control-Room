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

## Next: browser-based email assistance

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
