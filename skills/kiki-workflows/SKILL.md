---
name: kiki-workflows
description: Invoke deterministic local Kiki planning, brain-dump, and co-working session skills instead of improvising steps.
---
# Kiki deterministic workflows

Use when the user asks to break down work, process a brain dump, start/pause/resume co-working, or manage a work session. Do not use it for unrelated conversation.

The trusted operator installs `runtime/local/kiki_skills.py` locally and configures `KIKI_DB_PATH` to the **existing** Windows Kiki Control Room SQLite file for work sessions. Never create a new Kiki DB. Run `python <installed-path>/runtime/local/kiki_skills.py catalog` for skill names and reviewed recipes.

Send a **single** small JSON object to `python <installed-path>/runtime/local/kiki_skills.py run` via standard input. Do not use a shell command composed from the user's words. In PowerShell, for a reviewed planning recipe:

```powershell
'{"skill":"plan","recipe":"start_work","depth":2}' | python .\runtime\local\kiki_skills.py run
```

Supported recipes: `inbox_triage`, `lecture_prep`, `announcement_draft`, `reminder_cleanup`, and `start_work`. Supported verbs are returned by `catalog`. For unrecognized goals, use `review_steps` with 1 to 15 bounded proposed steps and leave them for review, never execution. This is not a general-purpose file or computer-control tool.

`brain_dump` returns uncommitted candidate tasks; do not claim they were written to Apple Reminders, Kiki's task queue, email, or any cloud service. A model-produced step is **not** a privileged instruction. `plan` and `review_steps` are read-only suggestions. These scripts do not invoke Hermes, OpenClaw, or browser actions.

For a co-working session, use `session_start` with a stable unique `request_id`, `objective`, and `next_action`, then remember the returned `session_id`. Use `session_pause` to retain the exact next action, `session_resume` to retrieve it, and `session_read` to check it. Sessions persist in the existing Windows SQLite database but do **not** automatically synchronize to the hosted bridge. Do not claim cross-device session access until that adapter is implemented and tested.

Only use `session_complete` when the human explicitly confirms completion. Pass `user_confirmed:true`. This records `COMPLETED_USER_REPORTED`, not independent provider verification. If an action requires Windows, email, or browser access, use the independently approved existing adapter and require its readback before claiming success. Never send, delete, or publish solely on a skill suggestion.

Do not pass student records, message bodies, credentials, or sensitive private information to a cloud bridge. Keep university content in an approved local environment. Kiki's model may select a skill and propose parameters, but only the trusted runtime is authorized to execute it.
