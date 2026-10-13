# Kiki Control Room

A visual and voice-first personal assistant project, built around Kiki's existing personality and a persistent, proactive task loop. The goal is to initiate helpful contact, remember commitments, guide work sessions, and reduce the need to open yet another organizational tool.

## Current prototype: free Telegram + calendar relay

The first backend candidate uses a dedicated Google Apps Script account as a scheduled runner, Telegram as the notification channel, and a Google calendar shared with that account. It can send morning check-ins and follow-ups, read upcoming calendar appointments, keep a small task queue, and create a calendar focus block only after explicit confirmation. It does **not** yet support conversational AI, voice messages, email triage, direct Outlook editing, or a connected browser UI.

Code: `runtime/apps_script/Code.gs`. Private account setup: [Zero-fee runtime instructions](docs/FREE_RUNTIME_SETUP.md). Verification: `node --test tests/relay.test.cjs`.

GitHub remains the development and static web-hosting home, **not** the always-on scheduler. Google Apps Script supplies scheduled execution without a paid hosting subscription. The runtime works without a billed LLM API. Google Drive can be used to store backups but is not required.

## Planned integration

The original animated Kiki Control Room visual prototype is the interface design reference. A subsequent stage will connect that interface to the reminder/task service, add a voice interaction path, and allow the Kiki-Mind canonical history engine to remain independently owned and locally stored. Local model processing through Ollama, and eligible ChatGPT plan use through Sign in with ChatGPT, are alternative reasoning backends rather than architectural dependencies.

Kiki-Mind is a separate repository: https://github.com/Azimn/Kiki-Mind

## Important limits

The relay is a **tested prototype**, not an activated bot. Activation requires the user's private Google Apps Script project, Telegram bot token, chat ID, and calendar sharing. Secrets and identifiable calendar contents must never be committed to this repository. The script currently retains only a small operational queue and does not constitute the canonical Kiki memory database.

The software's scheduled execution is best-effort within provider quotas. The initial research question is whether Kiki reliably initiates the day's first task and follows up when that task has not yet been started.
