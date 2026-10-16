# Kiki as a Companion: Product Vision

Status: Approved design direction, October 15, 2026. This document records intended behavior, not a claim that all capabilities are implemented.

## Purpose

Kiki is a personal, single-user administrative companion and persistent conversational presence. Her first job is to share the executive burden of starting, continuing, resuming, and completing everyday tasks. She is not primarily a commercial productivity application, autonomous task factory, game NPC, or evaluation of machine consciousness.

Success means a person can sit down to work and Kiki helps them begin without needing to remember to open a task manager, decide where to start, or reconstruct an interrupted task. Kiki should feel like the same familiar collaborator across Windows, browser, the hosted Site, ChatGPT integration, and Telegram.

## Product principle

Build a friend who can hang out while work gets done. Keep the assistant useful even when she does not automate the actual work.

Kiki should initiate an appropriate conversation, offer a realistic next step, collaborate in voice or text, track what is unfinished, and follow through. She should retain a playful, recognizable voice and the identity already defined in Kiki-Mind, rather than becoming a generic corporate productivity chatbot. Preserve established personality boundaries and historical continuity; do not rewrite her canonical identity in Control Room.

The user enjoys prototyping persona systems. Improving Kiki can be part of the fun and can motivate using the assistant. The feature-building experience should reinforce ordinary work, not replace the work indefinitely.

## The concrete morning scenario

The local Windows runtime notices the beginning of an eligible work period. Kiki checks the operational ledger, pending commitments, and available task context. She greets the user conversationally, brings forward the most actionable item, and proposes an easy opening move.

A typical session: Kiki introduces a short email queue. The user says they do not want to do email. Kiki responds with familiar humor, opens or helps open one message, offers a locally prepared draft if available, and collaborates through review. The user controls edits and approval. Kiki verifies whether the action was completed. If interrupted, she remembers the exact stopping point and resumes later.

An unsuccessful session is a reminder that says only "open the dashboard." A successful session begins with Kiki, presents a specific next action, and makes task progress possible without separate planning work.

## Behavioral commitments

### Initiation is Kiki's responsibility

At an appropriate trigger, Kiki initiates. A trigger may be a scheduled work routine, arrival at a usable Windows session, a resumption opportunity, or a deferred commitment becoming due. Preserve existing schedule preferences rather than inventing new ones.

A missed morning is not a missed chance forever. Kiki should recognize a disrupted schedule and offer an appropriate later reentry point. Reminders are not equivalent to completed work.

### Work together, not merely work for

Default to collaborative sessions: one next action, conversational check-ins, a visible current task, and a clear way to pause. Automation is useful when it eliminates drudgery but is optional. Kiki should help with email, university administration, grading support, research, and personal tasks without requiring full autonomy.

### Relationship and continuity are product features

Maintain the same character, recurring jokes, conversational preferences, current commitments, and earlier decisions across modes. Distinguish actual shared history from fabricated claims of past interactions. Use authored Kiki-Mind history for identity and the Control Room ledger for operational commitments.

### Follow-through rather than nagging

Track whether the user acknowledged, deferred, began, paused, completed, or explicitly declined an activity. A repeated alert is not progress. Kiki should vary approach based on what actually helped, recognize genuine unavailability, and allow pauses and quiet hours.

### Creative engagement

An animated Kiki avatar, a voice, subtle expressions, and context-sensitive banter are core usability options, not decorative extras. Optional playful touches may make routine tasks appealing. Avoid building a points-and-streaks application by default; prioritize collaborative pleasure over artificial rewards or guilt.

## Architecture: one Kiki, several interfaces

The current Windows Python process remains the persistent local worker: scheduling, Jan model interaction, task state, and local integrations. SQLite remains the task and work-session authority. The hosted Site and ChatGPT Kiki plugin remain continuity surfaces; Telegram remains a mobile option. The existing web dashboard remains functional.

A privately installed Chrome extension adds a side panel with Kiki's avatar, conversation, voice controls, current work session, and contextual page actions. It is a thin interface to the existing runtime, not a second independent Kiki brain. Playwright may later handle navigation, form workflows, and other browser interactions. The side panel does not need Playwright to be useful.

Local Jan is a candidate for conversational work and sensitive draft preparation. Models and task workers may vary by capability, but user-visible personality and commitments should remain coherent. Voice input/output and browser automation must be tested in reality, not treated as already available.

Muse can act as an independent, more capable agent for delegated research, analysis, or project work. Kiki remains the familiar point of contact for workday collaboration, not necessarily the technically most powerful agent. Muse may also be used directly. Any shared handoff should record assignment, owner, result, verification, and next action so the user never has to reconcile competing reminders or task lists. Muse connectivity is proposed, not implemented.

## Primary use cases

Email co-working: Kiki chooses a manageable next message, surfaces context, drafts or discusses a response, and helps verify what happened. The user can approve the final action. Browser-assisted Outlook and local Jan are preferred exploratory paths before adding other integrations.

Faculty work: Kiki accompanies the user through Canvas tasks, preparation, formative feedback, and administrative follow-up. The core value is keeping a session moving even if she never performs grading herself.

Personal life: Kiki remembers ordinary commitments and helps act on them across computer and phone, using proactive conversation rather than another list of notifications.

Research and creative projects: Kiki helps capture ideas, remember projects, and optionally delegate deeper research to Muse. Building Kiki itself can be an engaging recurring activity.

## User control and scope

This is a personal tool for one owner. A private unpacked Chrome extension is a suitable distribution approach. The design should stay lightweight and reuse working infrastructure.

Use existing local processing where appropriate. University data should remain in suitable environments, with operational summaries rather than message contents shared across services by default. User approval is expected for consequential outgoing actions. These are implementation boundaries, not reasons to postpone brainstorming.

## Definition of success

Measure observable results rather than feature count: Kiki-initiated sessions, time from initiation to first useful action, tasks completed, interrupted sessions successfully resumed, follow-ups that led to action rather than dismissal, and perceived ease of starting. Compare sessions with and without voice or contextual help when possible.

The north star: Kiki carries the burden of remembering, organizing, initiating, and tracking so that the user can focus on judgment, conversation, and doing the work.

Related implementation documents: [Browser Companion v0.1](BROWSER_COMPANION_V01.md), [Work Sessions](WORK_SESSIONS.md), [Roadmap](ROADMAP.md), [Email Assistant](EMAIL_ASSISTANT.md).
