# Kiki Browser Companion v0.1: Implementation Plan

Status: Proposed development milestone, October 15, 2026. No extension code is implied by this document.

## Goal

Ship a private, locally installed Chrome/Edge companion that makes Kiki present alongside an ordinary workday browser window. The first valuable outcome is conversational co-working on a single task, not autonomous browsing.

## Reuse first

The prototype already supplies a PWA dashboard at web/index.html, an offline shell, a Python loopback server at localhost:8765, an operational SQLite ledger, conversation hooks for local Jan, scheduler logic, and Site/Telegram connectivity. Preserve these components. Do not fork task ownership or copy Kiki-Mind into the browser.

A Chrome extension is a separate Manifest V3 package, not a renamed PWA manifest. Its primary surface will be chrome.sidePanel. Developer Mode with "Load unpacked" is enough for private installation; no Chrome Web Store publication is required.

## Proposed components

Extension shell: manifest.json, a background service worker, a narrow sidepanel page, bundled styles/assets, and optional active-tab context scripts. The side panel should show Kiki's portrait, a short conversational exchange, the current commitment, a simple next-action control, and pause/resume. Adapt the dashboard visual language, but design for a narrow column rather than squeezing the full dashboard into it.

Local bridge: a small permissioned communication path to the existing loopback runtime. The existing dashboard uses same-origin /api endpoints, whereas an extension runs under chrome-extension:// and requires explicit cross-origin handling. Do not embed local secrets in the extension. Keep the server's task data and session state authoritative.

Context adapter: initially only user-invoked access to the active tab's title, URL, and selected text where permitted. Later add site-specific adapters for Outlook and Canvas. A context snapshot is evidence for the current task, not a command channel.

Conversation adapter: reuse the existing Jan conversation route and conversation history. Keep model-specific inference independent of the extension so the user can change models without losing Kiki's identity.

Voice adapter: use a local or otherwise chosen speech input/output process attached to the Windows runtime. The extension can show mic/listening/speaking state and control a live session. Browser-native voice is a candidate fallback, not an assumed always-on engine.

Playwright adapter: optional later tool for navigating sites and assisting with web workflows. Do not block the sidebar milestone on automated clicking. Microsoft Playwright MCP and its browser extension are candidates for evaluation.

## Interaction contract

When Chrome starts and Kiki is already running, the sidebar reconnects to the current work session. Opening or closing Chrome does not create or destroy the session. Kiki can initiate through the existing desktop/Telegram pathways while the browser is closed.

The companion stays lightweight: one active action, the essential context, Kiki's voice/text, and a clear resume point. The owner can dismiss, pause, defer, or explicitly end a work session.

The avatar should react to meaningful states such as greeting, listening, speaking, thinking, celebrating a completed action, and quietly waiting. Use the existing Kiki art as the first visual source. An elaborate character animation pipeline is not a v0.1 dependency.

## Build sequence

Phase A: create the unpacked Manifest V3 extension with sidePanel and an on-demand button. Reuse the Kiki look and confirm manual load and basic sizing in personal Chrome.

Phase B: connect the sidebar to read-only local /api/state and show service availability, current task, and known conversation data. Use existing authentication/bridge rules; verify offline and restart reconnection.

Phase C: allow conversation, acknowledgment, pause, snooze, and a task-completion action using current runtime routes. Prove that status updates immediately appear in the main dashboard and survive reload.

Phase D: integrate a persistent work-session record and a morning or due-task initiation handoff. Keep the existing email schedule, task scheduler, and single Telegram poller intact. Reopening the sidebar should resume, not restart, a session.

Phase E: add push-to-talk or another reliable local voice interaction, then spoken drafting/review of one real or synthetic task. Text remains a fallback.

Phase F: add permitted active-page context and, separately, a Playwright experiment. Validate Outlook co-working before attempting more general automated workflows.

Phase G: optionally add Muse task delegation through a durable handoff, only after Kiki's core work-session loop functions on its own.

## First demonstration

With the local Kiki runtime running, the owner loads the unpacked extension and opens the sidebar. Kiki appears with a current commitment. The owner can talk or type, discuss the next action, pause the session, close and reopen Chrome, and resume without repeating context. Completion updates the existing ledger once, not a parallel extension database.

Then test Kiki-initiated reentry after interruption. A notification saying only "open the dashboard" does not count.

## Acceptance criteria

A private unpacked extension loads without store distribution. No duplicate task authority exists. Status and messages agree with the local dashboard. A task survives Chrome closure and runtime restart. A work session can be resumed at its last known step. Pause and deferral behave correctly. The same recognizable Kiki identity is used across modalities. Browser automation, voice, and Muse are declared incomplete until separately demonstrated.

## Implementation notes

Start with the existing Windows runtime and installed personal Chrome. Prefer built-in Chrome APIs and Playwright's existing tooling instead of writing a browser automation framework. Avoid a new hosted platform, subscription, or second scheduler for this milestone.

The product intent and behavior are in [Kiki as a Companion](KIKI_COMPANION_VISION.md). Session transitions and acceptance details are in [Work Sessions](WORK_SESSIONS.md).
