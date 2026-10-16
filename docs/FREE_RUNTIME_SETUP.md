# Zero-fee Kiki relay: setup and operating contract

**Status:** source implemented and simulated, but not connected to a real Google account or Telegram bot. Do not treat this as a deployed service.

## What runs where

GitHub stores the source and can publish the static visual interface. A private Google Apps Script, running under a dedicated Kiki Google account or another account you control, runs a five-minute clock trigger. It reads calendars to which that account has access, stores a small queue of tasks in Script Properties, and uses a private Telegram bot to send a daily check-in, event alerts, and follow-ups. No home computer, LLM API key, or paid hosting service is required for this stage. Kiki-Mind's canonical memory remains separate, preferably local and never published to GitHub.

This is a **scheduled assistant relay**, not a reasoning model or a general mailbox reader. It deliberately works without ChatGPT or Ollama, and can later invoke a locally running Kiki reasoning service when available.

Google Drive is optional file storage. GitHub Actions and GitHub Pages alone cannot provide an interactive 24-hour messaging process. Apps Script supplies that missing scheduled execution.

## Set up

Create or select the Google account that will operate the Kiki relay. Share the relevant calendars to this account using the permissions you intend to grant. The script can only view what this account can access. For new focus blocks, select a specific writable calendar, ideally a separate **Kiki Blocks** calendar that also appears in your normal calendar applications. Calendar subscriptions using ICS may be read-only and do not imply write privileges. Never embed calendar IDs, bot tokens, or event data in the public repository.

Create a private bot in Telegram through **@BotFather**, save its API token, open the bot chat, and press Start. In the Google account, visit [Google Apps Script](https://script.google.com/), create a standalone project named **Kiki Relay**, and paste the full contents of `runtime/apps_script/Code.gs` into the project editor. In project settings, set timezone to **America/Chicago**.

Open **Project Settings > Script Properties** and add `TELEGRAM_BOT_TOKEN` with the private bot token. Run `discoverKikiChatId` once in the Apps Script editor, grant the required permissions, and read **Executions > Logs** for the `TELEGRAM_CHAT_ID`. Add that number as a script property.

Add `READ_CALENDAR_IDS` as comma-separated Google Calendar IDs for the calendars Kiki should monitor. This property is optional if you want Telegram check-ins without calendar alerts. For explicit calendar time blocks, set `WRITE_CALENDAR_ID` to a calendar Kiki can edit. Set `KIKI_TIMEZONE=America/Chicago`. Leave `SHOW_CALENDAR_TITLES` unset or `false` for privacy-preserving generic alerts; set it to `true` only if you want event titles in Telegram notifications.

Run `testKikiConnection` in the editor. It sends a one-off Telegram message and logs whether each configured calendar is accessible. Then run `installKikiRelay` to install the five-minute trigger. The function removes old Kiki triggers before installing the new one, to prevent duplicate scheduled checks. Leave this project private, because editors can access its Script Properties.

## Using Kiki

On the configured Telegram chat, send `/help` to see commands. `/add Read committee memo` queues a task; `/status` shows open tasks; `/done 1` completes task number 1. `/snooze 15` postpones the current check-in; `/pause` disables proactive alerts; `/resume` restarts them.

For calendar writing, `/block 2026-10-15 10:00 30 Review studio schedule` creates a proposal only. Nothing is added until you reply `/confirm`. The assistant rechecks the calendars for conflicting events before creating the time block; `/cancel` discards the proposal. The time is interpreted in the configured timezone. Invalid, expired, or overlapping blocks are rejected.

The morning check-in happens on the first five-minute tick during the 9:00 to 10:59 a.m. window. There is a 15-minute first follow-up, then a 30-minute follow-up, followed by hourly follow-ups up to six in total. Sending a recognized command such as `/status` clears the check-in reminder; `/snooze` reactivates it for a specified interval. Quiet hours are 10 p.m. through 7:59 a.m., and `/pause` stops all proactive messages. A direct text conversation without a slash command is not interpreted in this version.

New calendar events within the next 15 minutes prompt a once-only notice, subject to five-minute scheduling granularity. Titles are not sent by default. Kiki does not change any existing events and does not automatically email anyone.

## Limits and next integrations

Google Apps Script time triggers are not strict real-time guarantees. The script is subject to per-execution limits and daily quotas. The compact prototype stores state in a single Script Property and deliberately errors before exceeding roughly 8 KB, beneath Google's 9 KB per-property limit. This is adequate for proving a small workflow, not a production archive of hundreds of tasks. Move task and receipt storage to SQLite locally, or to an appropriate private database, before scaling. Google Sheet storage is another free option.

Telegram is the transport; text commands work without a model. Voice-message transcription, arbitrary natural-language instruction following, a browser-based conversational UI, Outlook email triage, and calls are **not implemented** in this stage. For a desktop model-backed runtime, use Kiki-Mind with Ollama and/or the supported locally hosted Sign in with ChatGPT flow. ChatGPT plan usage is eligibility- and capacity-limited and is not general unlimited remote API access.

The approved calendar-sharing policy is assumed. Actual write access must still be verified for the chosen account and destination calendar. The Telegram bot must remain private. Do not log or publish protected message content. Keep production credentials out of GitHub and avoid placing sensitive event descriptions into the Telegram notification channel.

## Why this is different from another forgotten organizer

Once installed, the relay initiates contact independently. Tasks do not depend on opening GitHub, ChatGPT, or a dashboard. However, the first real acceptance test is operational: a morning check-in arrives, a missed check-in is followed up, and one time block is created only after approval. Once that holds for several days, connect the more advanced Kiki interface and local memory mechanisms.
