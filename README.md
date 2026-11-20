# Kiki Control Room

A low-resource, voice-first assistant project for Kiki. The operational goal is persistent, proactive follow-through: reach out, remember commitments, guide a single task, and continue even when the browser is closed.

## Companion-first product direction

Kiki's primary purpose is to be a familiar, proactive executive-function companion: start a work session, stay with the owner while working, remember interruptions, and follow through. A friendly voice, animated presence, and genuine co-working are central features; automation is optional. The user can enjoy improving Kiki while using her for real administrative and personal tasks.

The next design milestone is a privately installed Chrome companion panel that reuses the existing Windows runtime and shared continuity. Read the [product vision](docs/KIKI_COMPANION_VISION.md), [browser companion v0.1 plan](docs/BROWSER_COMPANION_V01.md), and [work-session contract](docs/WORK_SESSIONS.md). Muse may later handle delegated work, but Kiki remains the familiar workday collaborator.

## Working prototypes

**Local-first runtime (recommended for an older, mostly-on PC):** `runtime/local/kiki_local.py` uses Python 3.10+, SQLite, a background scheduler, and optional private Telegram messaging. `web/index.html` is a responsive animated dashboard with task management, a focus view, and pause/snooze controls. A web manifest and offline app shell support PWA installation under an eligible secure origin. The server stays on loopback by default to prevent accidental network exposure.

On Windows, use `start-kiki-windows.cmd`, then open **http://localhost:8765**. Instructions: [Local installation](docs/LOCAL_INSTALL.md).

**Cloud-free-calendar relay (optional companion or fallback):** `runtime/apps_script/Code.gs` can read Google calendars already shared with a dedicated Kiki Google account and send near-term appointment reminders via Telegram. Set the private Apps Script property `KIKI_CALENDAR_ONLY=true` when the local runtime owns Telegram commands. That prevents two competing update pollers or duplicate morning messages. Detailed setup: [Free runtime](docs/FREE_RUNTIME_SETUP.md).

The Python runtime includes optional local Jan conversation, outbound Site task/history synchronization, and signed calendar booking. Relevant older shared conversations can be retrieved into Jan's prompt after the hosted archive export is deployed. Email queue and local draft persistence are implemented; browser mailbox access, voice input, and email sending are not. See [current status and next steps](docs/ROADMAP.md).

## Architecture and boundaries

The operational SQLite database lives in the Windows user profile, **not in the public GitHub repository or a synchronized drive**. GitHub stores source and tests, not private task data or bot credentials. Kiki's true authored history and developmental evidence belong in the separate [Kiki-Mind](https://github.com/Azimn/Kiki-Mind) engine. We may later connect the two via a carefully typed evidence interface without allowing assistant reminders to become fabricated autobiographical events.

Local Ollama or an eligible user-authorized ChatGPT integration can later provide reasoning on demand; neither should be required for a timer or reminder to fire.

## Verification

Local Telegram calendar booking is implemented through the optional signed Apps Script bridge; see [Calendar booking setup](docs/CALENDAR_BOOKING.md). `/book` schedules directly on an explicit user command, while `/block` offers an optional preview. Deployment, calendar-writing authorization, and live acceptance are required before enabling it. The existing local server remains loopback-only.

Local server tests: `python -m unittest discover -s tests -p "test_local_runtime.py" -v`.
Apps Script simulated tests: `node --test tests/relay.test.cjs`.

CI tests the local runtime on Windows and Linux, Python 3.10 and 3.12. These are prototype acceptance tests, **not a claim that any real Google or Telegram accounts are already connected**.

## Intended next milestone

Build Kiki Browser Companion v0.1 as a private, locally installed Chrome side panel, backed by a durable, Kiki-initiated co-working session. Keep the existing local runtime, dashboard, and shared state as authorities. Prove that Kiki can greet, guide one real task, pause, and later resume it without requiring the owner to reconstruct the plan. Develop voice and browser-assisted email incrementally; sending remains disabled in the current prototype. See the [roadmap](docs/ROADMAP.md), [browser plan](docs/BROWSER_COMPANION_V01.md), [work-session contract](docs/WORK_SESSIONS.md), [email design](docs/EMAIL_ASSISTANT.md), and [shared context](docs/SHARED_CONTEXT.md).

## AIRI laptop companion

The laptop bridge connects AIRI 0.10.2 and local Ollama to the existing shared conversation ledger, with optional local screen understanding and paced proactive check-ins. It includes a shared work-session record, exact-reply delivery queue and pause controls. Start with [AIRI setup](docs/AIRI_SETUP.md), [implementation plan](docs/AIRI_IMPLEMENTATION_PLAN.md), and [adversarial review](docs/AIRI_GAN_REVIEW.md). Live laptop acceptance remains required.
