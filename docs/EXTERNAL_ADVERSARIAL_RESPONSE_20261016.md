# External adversarial review response and companion release gate

Date: 2026-10-16
Status: Partial implementation in GitHub review mirror. Not a live deployment acceptance report.

## What this change actually repairs

The hosted Site review mirror no longer pretends that saving a message creates an AI reply or that the avatar is processing inference. The composer is presented as a shared message journal, and the focus action is identified as a browser-local timer. Genuine two-way generation on the Site is still absent. The Site must not advertise itself as a speaking companion until its model round trip is demonstrated.

The MCP service now exposes owner-scoped read-only task projections, work-session state (if the compatible shared table is installed), and channel last-contact evidence. A recent interaction receipt is labeled historical, not proof of a live device connection. The hosted task table and the PC SQLite replica are returned separately. No cross-database mutation is inferred from a task title match.

The Site's mobile layout now puts the actionable work card before the decorative portrait, preserves the visual identity, and increases several undersized utility labels. When a compatible D1 work-session projection is available, the current objective, next action, status, and last update are visible.

## State ownership and replication boundary

The online D1 interaction ledger is the authority for source-attributed receipts and conversation turns. Kiki-Mind remains the independent authority for authored persona identity and admitted autobiographical memory. The Windows local SQLite runtime remains authoritative for local operational tasks. A replicated D1 desktop snapshot is evidence of the last reported PC state, not an independent task authority. The AIRI integration uses the D1 companion_sessions table with revision checking as the current shared work-session record; client-side timers, text drafts and portrait states never override it.

The legacy hosted D1 tasks table remains writable and distinct. It must not be used to complete a PC task without a confirmed two-way sync receipt. The UI now warns about this limitation. A future reconciler needs stable operation IDs, exact owner mapping, acknowledgement, replay protection, and a deterministic stale-revision failure. Treat reconciling the old hosted tasks store as a migration, not a silent assumption.

## Outstanding release gates

**Conversational loop:** An authenticated Site request must trigger an actual model response in the same thread and display it in the Site, with deterministic retry handling and appropriate latency/error states. AIRI's local Ollama and gateway conversation loop is a separate integration, not proof of this Site requirement. Browser speech recognition and speech synthesis are dictation/playback until an interruption-capable end-to-end loop is tested.

**Durable co-working slice:** Demonstrate a five-minute synthetic administrative email session offered by Kiki, accepted or declined, collaboratively revised, paused mid-draft and resumed on a second client after a process restart. Compare the persisted objective, draft revision, next action and verified outcome against the pre-interruption state. Mere retrieval of a transcript is insufficient. A prepared draft is not a sent email. Outgoing mail must retain human approval and provider send receipts.

**Proactivity:** AIRI's current check-in scheduler has eligibility, cooldown, quiet hours and unanswered-invitation protections. Live Windows installation, voice, gateway delivery, foreground capture and reboot recovery are still unverified. Record initiated versus user-initiated sessions, offers ignored, first useful action, number of user decisions, context repetition and actual verified outcomes.

**Health telemetry:** Operational projection APIs currently expose historical last activity. A genuinely live indicator requires a freshness-bounded heartbeat or active probe plus an independently successful capability test. Do not convert last receipt timestamps into green 'connected' labels.

**Deployment provenance:** The Sites-managed checkout is not reproducible from the GitHub mirror alone. Every Site release must record exact source revision, Site version, schema/migration version, tests executed and a restore exercise. Do not merge a review mirror and claim that doing so deployed the private hosted Site.

**Data protection:** Portable history export remains plaintext and must be treated as sensitive. Before institutional email integration, complete independently encrypted backup and verified restoration, retention/deletion design, owner authentication boundary verification, and an isolation test ensuring student or institutional content never enters personal Kiki history by default.

## Regression acceptance

The hosted tests exercise owner isolation, the difference between Site tasks and PC replica, work-session table absence, revision reading, and historical-contact-only status. These tests are source-level checks, not a browser or live deployment acceptance. The website's presence and voice need accessibility and user-device tests, including keyboard navigation, reduced motion, small viewports, interruption, empty states and failure responses.

The architectural priority remains a demonstrated initiation, conversation, interruption and recovery loop, before further avatar or integration expansion.
