# Kiki Control Room on an older Windows computer

**Stage:** low-overhead local prototype on the `prototype/free-calendar-telegram-relay` branch. This is not a configured always-on service or finished voice assistant.

## Recommended arrangement

An older Windows PC runs the core app, local scheduler, and SQLite database. The browser displays the animated Kiki dashboard. Telegram (optional) carries remote check-ins and replies to a phone. The Google Apps Script calendar worker (optional) watches shared Google calendars and sends event reminders, and later can be expanded to permit approved writes. A local Ollama model or an eligible ChatGPT integration can be connected as a separate reasoning process. None is required to make reminders happen.

Kiki-Mind remains canonical for authored personal history and developmental evidence. The SQLite file in Control Room is a **separate operational ledger** of tasks and reminder state, not autobiographical memory.

## Start it on Windows

You need Python 3.10 or newer installed on the older computer. Download or clone this repository, check out the current prototype branch, then double-click `start-kiki-windows.cmd` in the repository root. The launcher detects the Python launcher and installs the small `tzdata` timezone support library once if Windows does not already have it. The runtime itself requires no other third-party packages.

When the terminal says Kiki is ready, open **http://localhost:8765** in a browser on that computer. Add a task and mark it complete. Stop the server with Ctrl+C. Restart it and confirm your task still appears. The SQLite database persists in `%USERPROFILE%\.kiki\control-room.sqlite3`; back it up like an ordinary personal data file. Do not store a live SQLite database in Google Drive's synchronized folder.

For automatic launch, use Windows Task Scheduler. Create a task named **Kiki Control Room**, choose **At log on** or configure an appropriate startup task, and point the action at the full path of `start-kiki-windows.cmd` with the repository root as the working directory. Disable any setting that stops the task simply because the computer becomes idle. Confirm the task actually starts after a reboot. A machine that is asleep, shut down, disconnected, or stuck before sign-in cannot provide reliable outbound Telegram notifications; the existing cloud Apps Script option can act as a fallback.

## Optional: direct Telegram notifications

Create a bot through Telegram's official **@BotFather** and start a private chat with that bot. Identify your numeric chat ID. Telegram bot tokens must never appear in the public repository, documentation, browser JavaScript, screenshots, or GitHub Actions secrets unless needed for a private deployment.

Set **KIKI_TELEGRAM_TOKEN** and **KIKI_TELEGRAM_CHAT_ID** in the Windows user environment, then restart Kiki. The runtime polls Telegram and only accepts commands originating from that one chat. Available commands are `/start`, `/help`, `/add some task`, `/status`, `/done 1`, `/snooze 15`, `/pause`, and `/resume`. No AI model is needed for these deterministic behaviors.

**Only one application may call Telegram's getUpdates for the same bot token.** If the local Kiki service owns Telegram polling, do not also run the original Apps Script Telegram-command mode. If Apps Script is kept for calendar event reminders, set its private Script Property `KIKI_CALENDAR_ONLY=true`. That disables its Telegram polling, morning checks, and follow-up messages while preserving outgoing calendar reminders. Both systems can send notifications, but the local daemon is the only receiver of commands.

Daily check-ins use America/Chicago time, beginning at the first tick between 9 and 11 a.m. Follow-ups are bounded and stop when you acknowledge, complete a task, or pause. Quiet hours are 10 p.m. through 8 a.m. Time and schedules are adjustable in the source for this prototype. Google Apps Script timers are approximate. The local Python scheduler checks every five seconds while the machine is running.

## Calendar connectivity

The existing `runtime/apps_script/Code.gs` provides a no-subscription method to read calendars already shared with the Kiki account. With `KIKI_CALENDAR_ONLY=true`, it sends reminders for upcoming events through Telegram without becoming a second task and command runtime. The full setup is in [FREE_RUNTIME_SETUP.md](FREE_RUNTIME_SETUP.md).

This is **not yet two-way calendar editing from the local dashboard**. The original Apps Script `/block` confirmation flow works only when Apps Script itself receives Telegram commands, so that flow is disabled in calendar-only mode. Do not expect local `/block` to work until a separate calendar-write bridge is implemented. Existing shared Google calendars still work as read-only event notification sources. The next integration must add explicit user-approved writes, conflict checks, and reconciliation to the local SQLite state.

## Phone and installability

The dashboard includes a web manifest, offline UI shell, and responsive layout suitable for installation as a progressive web app. Desktop browsers can open it on `localhost`. However, the server listens only on **127.0.0.1** to avoid exposing the SQLite-backed task API to your local network or the public internet.

To use the same browser interface on an iPhone, a **private HTTPS proxy** is needed. Tailscale Serve on the PC, with the iPhone joined to the same tailnet, is a reasonable later option. Do not directly port-forward Kiki's HTTP port or expose it to the public internet, and do not change the binding to `0.0.0.0` without designing authentication and authorization first. Telegram works on the phone immediately once configured, without any exposed inbound port.

Speech input, speech synthesis, automatic email triage, cross-device browser login, calendar editing from the dashboard, and model-based chat are *future integrations*. This release demonstrates persistence and initiation, rather than claiming those features.

## Test

The local code is checked using `python -m unittest discover -s tests -p "test_local_runtime.py" -v`. CI runs on Windows and Linux across two Python versions. Relay tests separately verify Apps Script logic through a simulated harness.

When the task scheduler and Telegram are enabled on the actual Windows PC, the operational acceptance test is simple: Kiki messages you at the morning check-in, follows up once if you ignore it, stops after `/status` or `/pause`, and remembers a task through a system reboot.
