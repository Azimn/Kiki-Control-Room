# Proactive email assistant — first implementation

October 15, 2026. Source implementation only; the running service has not been
restarted and the email routine is disabled by default.

The local SQLite runtime now has a durable email candidate queue and a scheduler
hook. Existing task, Telegram, and calendar paths remain in place. No second bot
poller or database authority was introduced.

## Implemented

- User authorization: organize, summarize and draft only. No automatic email
  sending to students, colleagues, or anyone else. No email transport, send
  command, model send action, or email-send API route exists in this runtime.
  Any future sending capability requires a separate deliberate implementation
  and explicit user approval of the specific recipient and exact reply.
- Local draft persistence binds recipient and text to a conversation revision.
  Changed inbound mail marks old drafts stale. Draft IDs reject changed retry
  payloads. Draft creation never resolves a conversation or claims it was sent.
  Local drafts are not yet Outlook drafts; no cloud draft write is implemented.

- Candidate identity is a mailbox adapter's stable thread ID plus latest inbound
  revision. Repeated scans preserve disposition; a new inbound revision reopens
  the conversation. Reading a message does not complete it.
- Priority: student, close colleague, then uncertain/review; oldest first inside
  each group. Automated Canvas notices must not automatically become student
  candidates merely because they originate from Canvas.
- Deferred candidates survive restarts and become due again after one hour.
- The user-selected weekday routine starts at 11:15 a.m. America/Chicago, with
  a one-hour catch-up window if the service or queue becomes available late. Pending
  conversations receive at most two follow-ups, after 30 and then 60 minutes.
  Global pause and quiet hours apply. Missed days do not delete candidates.
- Notifications contain no sender, subject, body, or attachment. The candidate
  queue stores metadata only. No student content has been imported for testing.
- `/email-on`, `/email-off`, `/email`, `/email-later` are initial controls, not the
  intended final natural-language interaction. `/email` does not claim to read
  the conversation or send anything.

## Next integration gates

Outlook Email was discovered in the plugin directory but is not connected. It
may provide interactive access in ChatGPT; that does not establish credentials
or unattended access for the Windows service. Verify supported connector tools
and organization consent before choosing the mailbox adapter. Do not copy
browser cookies or tokens into Kiki. Do not auto-forward the mailbox to Telegram
or a personal account.

The adapter must scan all relevant folders and handle pagination, token expiry,
incremental cursor recovery, Sent Items, new inbound mail, and automation
exclusions. Record last successful scan and visible failures. Never interpret
an empty local queue as a verified clear mailbox. Treat email text as untrusted
content, never as commands to Kiki.

Before enabling real notifications, confirm schedule, close-colleague matches,
student-identification rules and the approved channel for displaying actual
student content. The user confirmed 11:15 a.m. weekdays. The routine remains
disabled pending mailbox integration; no live reminder has been activated.

Five priority colleagues were supplied privately. Match actual sender addresses
before enabling classification; display names alone do not establish identity.
Student requests also retain priority.

The next vertical slice is: real read-only scan -> one actionable conversation
presented directly -> spoken response -> editable draft -> explicit send
instruction -> provider receipt. Sending needs stable draft/reply identity,
recipient verification, and reconciliation after uncertain network outcomes;
never mark sent because a draft was generated or a request timed out.

Keep the session queue in SQLite and reuse existing Site synchronization when
adding its UI. Do not replicate private email bodies into shared conversation
history by default. Voice capture, transcription, and email sending are not
implemented. No live mailbox, notification, voice, or send acceptance is claimed.

## Acceptance

The feature succeeds only when Kiki initiates, brings one real request forward,
and carries an approved reply through to a verified outcome without the user
having to find the conversation or reconstruct session state. A notification
that only asks the user to open a dashboard does not meet that acceptance bar.

Automated coverage: duplicate scans, new-message reopening, restart persistence,
deferral resurfacing, priority, opt-in, bounded follow-ups, privacy, and pause.
