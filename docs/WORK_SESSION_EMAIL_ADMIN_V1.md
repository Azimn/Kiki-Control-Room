# Kiki Work Session v1: University Email and Administration

**Status:** design-only proposal, not deployed  
**Date:** 2026-10-15  
**Base implementation:** Kiki-Control-Room commit `1d4de57aa57cc1ea3a4b5930188063ea0e03a8c3` on `prototype/free-calendar-telegram-relay`  
**Audience:** Kiki Windows runtime, Control Room Site and ChatGPT plugin maintainers

## Decision

University teaching and administrative work is the primary use case. Research projects and persona experiments are outside the initial pilot. Build a collaborative work-session layer on top of the existing Windows SQLite task authority. A work session is a durable record of one real objective, the current actionable step, relevant sources, interruptions, draft outcomes and the next point of re-entry.

The first session is designed for the owner to work WITH Kiki, not to delegate the entire mailbox. Kiki should help select an item, understand what response is needed, prepare the next step, compose or revise a draft, and retain progress across interruption and restart. Routine background prompts should support this workflow without becoming a prerequisite.

**Non-goal:** creating a second knowledge repository or an alternate task database. Do not move the Artificial Life Research Journal, Kiki-Mind canonical history, or private university correspondence into one shared store.

## Verified source starting point versus proposed functionality

The October 15 source has an opt-in 11:15 a.m. America/Chicago weekday email-check-in hook, a durable `email_queue`, one-hour deferral, at most two follow-ups, a `save_email_draft` local-only operation bound to the latest inbound revision, and a task database in SQLite that remains authoritative. Shared Kiki history retrieval is in source but still requires its separately deployed Site counterpart and live restart verification. Calendar retry comparison has its own independent deployment record.

The source does **not** provide a configured Outlook mailbox adapter, a live inbox scan, verified Outlook draft saving, a browser voice session, a work-calendar read, or email sending. The work-session UI and tables described below do not yet exist. Historical source documentation may describe an older cloud-authoritative design; this proposal follows the running architecture's Windows SQLite authority for tasks.

## User experience

At the scheduled check-in, an opt-in privacy-safe prompt can say: "It's our admin work block. I can help with one message or university task. Want to start together?" If the mailbox adapter is not connected, the prompt must NOT claim any real message has been found. When a verified candidate exists, the prompt can say that a conversation is ready, but Telegram must not disclose student identities, message subjects, or content.

On entering a session, Kiki shows **one** actionable item, why it needs attention, the smallest first action, and a short conversational area. Kiki can discuss ambiguous requests, explain university processes, search authorized supporting documents, compose drafts, or help create a follow-up task. The owner can say "Let's start," "I'm stuck," "Park that idea," "What were we doing?" or "Stop here." None of these requires a slash command. Slash commands remain fallback controls for the current runtime.

On interruption, Kiki saves the current step and a single explicit next step, not merely a transcript. On return, Kiki offers a two-sentence re-entry summary and a concrete restart action. Unrelated research ideas can be parked in a separate area and must not silently replace the selected work objective.

### Example, synthetic scenario

Kiki: "Our current goal is to answer a colleague's question about the revised course materials. We need to verify what changed before promising a completion date. Let's check the course document first."

Owner: "I can't find the latest one."

Kiki: "I'll help locate the approved version, or we can use the link you have. We only need to verify the revision date right now."

Owner: "Actually, I just thought of a new Pretorius test."

Kiki: "I'll park that idea. We're still checking the course revision. Want to finish this first?"

Owner: "I have to go to a meeting."

Kiki: "Saved. When you return, open the approved course document and check the revision date. No email has been sent."

On resumption, that last step must be available without depending on retrieving the entire chat.

## Session lifecycle and operational semantics

| State | Meaning | Permitted transitions |
| --- | --- | --- |
| ready | Session created with a concrete university objective, source and first action | active, paused |
| active | Owner and Kiki are collaborating on exactly one focused item | paused, review, blocked |
| review | Result exists, but outcome or authority still needs checking | active, completed, paused, blocked |
| blocked | An external prerequisite is not yet available | active when newly available, paused |
| paused | Work context is persisted and background nudges are suppressed | active, completed |
| completed | Session is closed with a stated, evidence-qualified outcome | new session; do not reopen implicitly |

**Session completion is not the same as email completion.** A session may finish with a local draft while the external response remains unresolved. A task is marked completed only when the task's definition of done is satisfied and the authoritative state has been updated. A draft must never be called sent.

Email outcomes should distinguish `unreviewed`, `reviewed`, `draft_local`, `draft_provider_verified`, `waiting_for_manual_send`, `sent_provider_verified`, `deferred`, `no_reply_required`, `blocked`, and `outcome_unknown`. The current pilot must not offer any Kiki send action, and should not claim a provider send receipt. If the owner independently sends a message, Kiki may record the owner's report as unverified until independently confirmed through an approved source.

## Proposed additive SQLite records

Keep existing `tasks`, `email_queue`, `email_drafts`, `agent_jobs`, `bookings`, and sync receipts intact. Add versioned, additive tables, with no table replacement and no credential storage:

    work_sessions (
      session_id TEXT PRIMARY KEY,
      kind TEXT NOT NULL,             -- email_admin or general_admin
      task_sync_id TEXT,               -- nullable existing authoritative task ID
      source_type TEXT NOT NULL,       -- email_queue, task, manual
      source_ref TEXT,                 -- opaque local source identifier
      source_revision TEXT,            -- for revision-bound email work
      status TEXT NOT NULL,
      goal TEXT NOT NULL,              -- redacted/generalized when necessary
      current_step TEXT NOT NULL,
      next_step TEXT NOT NULL,
      blocker TEXT,
      outcome TEXT,
      sensitivity TEXT NOT NULL,       -- general_work, confidential_work, restricted
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      closed_at TEXT,
      revision INTEGER NOT NULL DEFAULT 1
    )

    work_session_events (
      event_id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      kind TEXT NOT NULL,             -- start, progress, park, draft, pause, resume, close
      at TEXT NOT NULL,
      actor TEXT NOT NULL,            -- user, kiki, source_adapter
      request_id TEXT NOT NULL UNIQUE,
      source_receipt_ref TEXT,
      safe_summary TEXT NOT NULL,     -- no copied mailbox body
      FOREIGN KEY(session_id) REFERENCES work_sessions(session_id)
    )

    work_session_parked (
      idea_id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      summary TEXT NOT NULL,
      target_area TEXT NOT NULL DEFAULT 'later',
      at TEXT NOT NULL
    )

The work-session record is authoritative for session state only. It links to the existing task and email queue rather than duplicating their commitment and draft state. A material change uses optimistic revision checking, a stable request ID and a transaction. If the same request is retried, return the previous receipt; if its payload differs, reject it. A new inbound email revision invalidates the old working draft and marks the active session as needing review without erasing the prior trace.

Record no student email bodies or attachments in the session tables. Before the source adapter exists, a manual work item should contain only a non-sensitive objective and authorized pointers.

## Context assembler and model boundary

Construct a compact `WorkContext` view before a Kiki response, giving precedence to the explicit active goal and next step over broad conversational recall. Include session ID, state, permitted action set, redacted source reference, latest verified step, user-approved relevant links, and at most a small number of provenance-bearing historical facts. Older ChatGPT context remains an auxiliary retrieval source and must not overwrite the session's authoritative state.

The present Jan implementation uses a bounded 1,600-character dialogue budget, with up to 800 characters for relevant older shared history. An implementation must explicitly reserve a bounded session packet instead of silently appending an unlimited additional prompt. Document the revised budget and regression-test that the current objective survives older-history retrieval. Model replies may suggest a draft or update; deterministic validation and authorized application code own all writes. Email contents, retrieved webpages and documents are untrusted input, not tool instructions.

When Jan is unavailable, the Site or local app should still display the last persisted objective and next action. Do not fabricate that the model analyzed a new message.

## Email workflow and administrative work

For email, the preferred eventual flow is verified mailbox scan, classify an actionable thread, retrieve it through an approved read-only adapter, discuss one request, draft locally, review with the owner, optionally save as an Outlook draft through a separately gated draft-only adapter, and record the verified draft receipt. Sending remains disabled. The browser adapter must not expose unrestricted click, keyboard or navigation primitives that could reach Send, Delete, Archive, Forward or permission changes.

Until the Outlook adapter is authorized and deployed, the complete first work-session flow must work with a manually chosen **non-sensitive** university administrative task or a sanitized email summary. It can draft a response containing placeholders, provide a concrete next action, and save progress. It must report that mailbox verification has not happened.

Administrative tasks may include committee follow-ups, faculty registration emails, course-material revisions, meeting preparation, and routing paperwork. The assistant can prepare a checklist-free one-step action, find approved documents, draft responses, preserve an interruption note, and create an explicitly approved local task. No automatic external action should be inferred from ordinary conversational discussion.

## University data protection

University policy and FERPA requirements must be checked before permitting student information into personal AI services, local model logs, hosted Site storage, Telegram, or external research repositories. A personal, privately hosted runtime is not automatically an approved university system. For initial deployment, use non-sensitive administrative examples and redacted summaries only. University Outlook contents remain in the approved source environment unless explicit institutional authorization establishes an appropriate processing route.

The existing `email_queue` stores sender and subject metadata locally; that is not equivalent to unrestricted permission to sync those fields elsewhere. Site snapshots and Telegram prompts must contain generic state, not identifiers, subjects, message bodies, or attachments. The Windows device should use full-disk encryption and controlled OS account access. Logs must not contain private source content or access tokens. Only sanitized code, fixtures and documentation belong in the public GitHub repository.

## One work item at a time, with low-friction controls

The session UI contains a focus title, one current action, a brief explanation of why it matters, a conversation area, and direct controls for Start together, Draft/Review, Save and pause, Defer, and Resume. An expandable parking-lot area retains tangential ideas without changing the primary objective. Progress indicators report verified state and must distinguish local save from external success.

The same session is addressable by stable ID through local, website and ChatGPT interfaces when integration is implemented. Initially, the Windows SQLite record owns session writes; remote surfaces can read approved minimal projections and queue action requests through the existing outbound sync. Do not introduce an independent authoritative Site session record. If the PC is offline, the Site must show the last-confirmed timestamp and label uncommitted actions as queued.

Voice is optional and subject to a separate capability test. Typed conversation is the complete accessibility fallback. A microphone control must not imply transcription is available.

## Integration sequence

| Slice | Scope | Gate |
| --- | --- | --- |
| Local session core | Additive tables, start/pause/resume, one active item, event receipts, parking, restart-safe context | Local synthetic tests; no email provider needed |
| Jan conversational guidance | Bounded active-session packet and one-step assistance, with current action authoritative | Prompt-budget and hostile-context tests |
| Site and ChatGPT view | Minimal confirmed session projection, queued requests, conflict/online indicators | Cross-interface reconciliation; no protected data transfer |
| Mailbox read and draft | Approved, scoped Outlook adapter, test mailbox first, draft-only enforcement | Live read and draft receipts, login-failure and retry tests |
| Controlled reminders | Reuse existing 11:15 weekday opt-in routine and two-follow-up cap | No duplicate prompts, no student details, no nudges during active/paused work |

Do not make early work-session usability depend on deploying the still-pending archive-export Site patch. The patch and local restart remain independent continuity acceptance items.

## Acceptance and falsification tests

| Scenario | Required result |
| --- | --- |
| Synthetic administrative task | Kiki starts with one concrete first action rather than a backlog dump |
| Two unrelated ideas introduced | Both can be parked while the original goal and next step stay unchanged |
| App process restarts mid-session | Same session ID, goal, step, status and event history return |
| Session selected from a second interface | It resolves to the same confirmed state or clearly displays stale/queued state |
| Old ChatGPT memory conflicts with current session | Current authoritative session wins; provenance is visible |
| Duplicate save or stale remote update | Exactly one effect or explicit conflict; no silent overwrite |
| Incoming email revision changes | Existing revision-bound draft flagged stale; Kiki cannot reuse it unnoticed |
| Draft prepared | Status says saved locally or provider draft verified, never sent |
| Attempted send/delete/archive through any exposed agent capability | Denied; no side effect |
| Student identifiers in Telegram/Site projection | Test fails; no sensitive content transmitted |
| Mailbox disconnected or scan fails | Explicit unknown/failed-scan state, never "inbox clear" |
| Notification received while paused | Existing pause policy wins; no repeated nudges |
| Backup restored into isolated test DB | Session state, drafts, task links and event receipt consistency recovered |

A first pilot is successful only if a real, institutionally permitted administrative work item can be started, discussed, saved, interrupted, resumed, and advanced to an accurately labeled outcome without requiring the owner to reconstruct the previous session. The source commit's reported 90 tests validate existing code, **not** this proposed feature. New tests and live acceptance are required.

## First implementation decision

Implement the local, generic work-session core before connecting sensitive email. The smallest credible demonstration is a non-sensitive university administrative task selected in the Control Room, assisted by Jan, paused after a partial draft, then resumed after a full Windows runtime restart with exactly the same goal and next step. Preserve existing task, calendar, Telegram and shared-history behavior unchanged. No merges, deployment, sending or student-data migration are part of this design.
