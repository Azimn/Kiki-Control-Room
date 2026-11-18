# Jan as a Kiki runtime adapter

Jan uses the same Windows SQLite task IDs, state transitions, source pointers and
verified receipts as the Site and other adapters. There is no Jan task authority,
new scheduler, Telegram poller or secondary task history.

## Implemented changes

- `JanAgent.finish()` refuses queue-managed completion by title or local numeric
  ID. Its SQL completion fallback has `queue_json IS NULL`; only legacy tasks can
  use that path. Shared completion always requires queue verification.
- Once the existing desktop owner is paired, explicit `Add task: ...` requests
  create shared PROPOSED tasks. Explicit `Draft ...` requests queue only bounded
  `local.draft.generate` work. Draft authorization is not send authorization.
  These use the original agent-job ID as provenance and deduplication key. When
  owner pairing is absent, existing legacy behavior is preserved.
- Jan reads owner-scoped pending tasks, blockers, last verified outcomes/receipts
  and the originating job/thread pointer from the existing SQLite authority.
  The saved resume pointer survives process restart. There is no copied Jan list.
- The existing serial `JanAgent.run()` worker services one eligible draft during
  its existing idle cycle. No independently scheduled worker is installed.
- Draft generation uses Kiki's identity and bounded, attributed recent/relevant
  shared conversation context. Context is data, not tool instructions.
- A draft lease renews every 20 seconds during a bounded 180-second model call.
  Renewal failure prevents verification. Truncated/tool-call responses are
  rejected. Failure preserves a BLOCKED task, without automatic retry.
- Capability probing now tests **authenticated inference**. Jan's public
  loopback model list alone cannot prove permission to generate.
- A persisted/read-back draft records `VERIFIED` with `outcome: DRAFTED`, a stable
  task ID, revision, provider response ID, context digest and SQLite receipt.
  It never means SENT and cannot invoke mail/calendar tools.

The initial conversation interpreter remains deliberately bounded: generic
planning answers are suggestions, not executed work. Natural-language draft
submission currently uses the explicit `Draft ...` form. Broader intent parsing
must preserve the same source, approval and verification boundaries.

## Machine connection

The inspected environment is `MCC16-JR`; both the existing SQLite runtime and an
authenticated Jan inference service are reachable here. This does not establish
which machine should own the eventual cross-machine connection.

Jan accepts only these authority-side endpoints:

- `http://127.0.0.1:18766`: existing same-machine private model service.
- `http://127.0.0.1:18767`: an explicitly configured private SSH local forward.

For the second arrangement, the SQLite authority still runs the adapter. It
forwards only model requests over an existing approved SSH connection to the
secondary desktop's localhost-only Jan API. The secondary desktop receives no
SQLite database, task-owner credential, scheduler or independent queue.

Example **after** confirming the private host, account, existing authorization,
and known host fingerprint (do not bypass SSH host verification):

```text
ssh -N -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes -L 127.0.0.1:18767:127.0.0.1:18766 <approved-account>@<private-secondary-host>
```

Keep Jan bound to remote `127.0.0.1:18766`. Do not open a public port, use a
public tunnel, copy SQLite through a network share, or disable TLS/SSH checks.
The authority-side adapter still requires the existing Jan API key in private
configuration. Never place the key in the SSH command, Git, prompts or frontend.

Configure `KIKI_JAN_URL=http://127.0.0.1:18767` only after a real connection test.
The existing Windows runner must load this optional environment name before a
controlled restart. No cross-machine address or key has been invented or deployed.

## Backup, activation, rollback

Before activating the Windows change, create a fresh backup outside Git:

```text
python runtime/local/backup_authority.py --destination <private-new-backup.sqlite3>
```

The source is opened read-only; SQLite's backup API captures WAL safely. A second
connection verifies integrity and table counts; a SHA-256 and local verification
record are written. This is a verified local backup, **not an independently
encrypted backup**. Do not upload the resulting data or verification paths.

First reconcile the Site patch against production version 33. Preserve the Site
owner/viewer policy, source revision and existing single-desktop mapping. Then
stop only `Kiki Control Room`, verify its process/port stopped, and start that
same task with the reviewed code and owner configuration. Do not start another
Telegram consumer or replace `Kiki Local Model`.

Retain the old source revision and backup. On rollback stop the same task,
restore the prior code and restart it. Preserve newer DB receipts; never overwrite
them with a pre-execution backup. Stop new draft dispatch until reconciliation
if task state and external/provider state differ.

## Live evidence and remaining gates

Run opt-in live acceptance with only synthetic context:

```text
python tests/jan_live_acceptance.py --output <private-workspace-evidence-directory>
```

For the configured SSH local forward add `--model-url http://127.0.0.1:18767`.
The harness reads the existing private model key without displaying/storing it.
It uses an isolated synthetic DB, the actual Jan model, the same queue worker,
independent persisted-draft readback, and a fresh interpreter for resume checks.
It does not start services, send messages, or touch the production task DB.

Real local-model acceptance passed on October 19, 2026:

- Task `task-9450211d-e16f-4144-9218-40c0c26c4d2b`
- Readback `receipt-18bc9896-5397-47b5-bba1-9176ca56e7f5`
- Provider response `chatcmpl-b7InUl56fQ22HsQQRj7xC6enyTVKVfwa`
- Actual Jan request interpretation and actual authenticated draft inference
- Outcome `DRAFTED`; no outbox/send
- Same task/receipt and origin pointer verified after a cold Python restart

Still required: approved secondary-desktop transport and real cross-machine run;
Site v33 reconciliation/publication and hosted create/read acceptance; production
Windows activation and full Windows restart. A process restart is not OS reboot
evidence. PR #15 remains draft until those gates are resolved.

Site-source reconciliation is additionally pending an explicit approval request:
automatic approval review rejected passing the Site-issued short-lived repository
credential to the official source helper. No alternate credential-transfer path
was used. The private desktop address/approved SSH connection also remains to be
confirmed before a cross-machine run.
