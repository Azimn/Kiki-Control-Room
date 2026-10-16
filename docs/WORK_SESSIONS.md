# Kiki Work Sessions: Behavioral and State Contract

Status: Design specification, October 15, 2026. Not yet a claim of runtime implementation.

## Definition

A work session is a durable shared commitment between the owner and Kiki. It stores what they are trying to accomplish, the next tiny action, what has already happened, and when to revisit it. Its job is to reduce the burden of initiating and resuming real-world work, not to enforce continuous productivity.

A task is something that needs doing. A work session is the conversational process of doing it together. A scheduled reminder is an opportunity to initiate or resume the session, not proof that the task advanced.

## Minimum session record

Keep a stable session_id; owner identity; linked task_id or thread reference; human-readable objective; current next action; state; creation and update timestamps; optional planned revisit; last verified action; last conversation pointer; origin modality; and an interruption/resume marker.

Use the current SQLite runtime as authority. The extension, dashboard, Telegram, and hosted Site display or relay session summaries; they do not independently decide that work is complete. Store a compact event history with unique operation IDs so reconnects do not double-complete actions.

## State model

Proposed states are OFFERED, ACTIVE, PAUSED, DEFERRED, BLOCKED, AWAITING_APPROVAL, COMPLETED, and DECLINED. A session can enter OFFERED through a morning routine, pending commitment, or explicit request. It becomes ACTIVE when the user accepts or starts. Interruption causes PAUSED or DEFERRED with a retained next action. Completion requires a verified outcome or an explicit user decision when verification is not available.

BLOCKED records what is missing. AWAITING_APPROVAL means the assistant prepared an action but is waiting for human judgment. DECLINED is a legitimate end state, not a failure to trigger more reminders. A completed session can spawn a separate follow-up commitment if needed.

## Initiation and recovery

Use the existing scheduler and Kiki's ongoing Windows presence. A regular morning is one possible trigger, but not the only one. On missed windows, try a later appropriate opportunity instead of dropping the commitment. Respect a work session currently underway and avoid overlapping invitations.

Kiki should make a concrete opening offer rather than demand that the user inspect a backlog. Example: "I've got the student question ready. Want to talk through the answer together?" If declined or deferred, record that choice and honor it.

When a session is interrupted, record the last completed step and the next action. After resumption Kiki should say what remains, not retell the entire plan. If browser state was lost, say so and offer to reopen the relevant page.

## Co-working loop

Kiki proposes one manageable action, brings forward any relevant context, collaborates conversationally, confirms the next outcome, and either proposes another action or marks a stopping point. Different tasks can use different helpers: local Jan for language, Playwright for a web action, or Muse for bounded background research. Completion evidence belongs in the session ledger.

Natural humor and banter are desirable where appropriate. The user remains able to change priorities, ask for a break, or switch to a creative Kiki prototype session. The system should recognize a spontaneous useful detour versus a lost commitment and retain the unfinished work accordingly.

## Voice and persona

Prefer live-feeling, turn-taking spoken conversation where the user can interrupt, pause, and redirect naturally. Preserve the already established Kiki persona and context across voice and text. Kiki's visible avatar can show listening, speaking, working, and waiting, but should not make inaccurate claims about her underlying cognition.

A spoken reply does not itself constitute a completed task; the system records the actual next step and any verified action separately. When voice is unavailable, continue the same session through text rather than starting a different Kiki.

## First vertical slice: email

The initial practical session is a short inbox review. Kiki initiates; presents one candidate message or a synthetic test equivalent; helps formulate a reply using Jan if available; shows the draft for user revision; and records whether it was prepared, deferred, or actually sent. Existing email candidate and revision-bound draft mechanisms should be reused.

No automatic send is required for the first slice. The v0.1 goal is getting started, collaboratively working one message, and resuming the remaining queue later. Verified sending, if added, requires its own provider outcome.

## Optional delegation contract

Muse may be more capable at complex research or autonomous execution. Kiki can assign a bounded job with a job ID, expected output, and response destination. Muse reports completion, evidence, or blockage. Kiki remains responsible for incorporating the result into the current session and preserving the user's continuity. No second competing personal reminder stream is created.

## Test plan

Test a session that starts unprompted at an agreed schedule; one that is manually initiated; a session interrupted mid-draft; a browser closed and reopened; a runtime restart; a missed scheduled window; explicit pause and decline; a duplicate event; and a helper failure. Confirm the pending next action survives and that Kiki does not announce completion without evidence.

Record metrics that matter: initiation success, time to first action, number of user-side steps before work begins, completion, resumption, and user-reported ease of starting. Avoid vanity metrics such as total reminders sent.

Related: [Product vision](KIKI_COMPANION_VISION.md), [Browser Companion v0.1](BROWSER_COMPANION_V01.md), [Email Assistant](EMAIL_ASSISTANT.md).
