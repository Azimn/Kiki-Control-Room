# Shared task protocol v1 (draft implementation)

This change extends Azimn/Kiki-Control-Room. It does not establish another agent,
task database, Telegram listener, or Google OAuth connection. It addresses #13's
corrected comment and #11/#8. The supplied shared_queue.py was reference material,
not a replacement schema or an unauthenticated server deployment.

## Authority and transport

Windows `~/.kiki/control-room.sqlite3`, existing `tasks` rows, remains the only task
authority. Stable IDs remain `tasks.sync_id` (`task-<UUID>`). Additive `queue_json`
holds the richer task contract; `queue_events`, `queue_requests`, `queue_runtimes`
and `queue_nonces` hold audit, deduplication, health and signature replay records.
Legacy tasks retain their IDs and original completion semantics. Legacy completion
cannot complete a queue-managed task. Old completed tasks are not retroactively
called VERIFIED. No task-owner migration is performed.

D1 `desktop_actions` is a durable **command inbox**, not an executable task queue.
`desktop_sync.snapshot_json.shared_queue` is a confirmed SQLite projection. An
accepted hosted request says `pending`, not QUEUED or executed. The existing
outbound desktop sync (15-second cadence) commits it on Windows and publishes
the authoritative result and snapshot on a subsequent exchange. Offline requests
wait. D1 cannot grant a lease. Shared-history interaction receipts and shared
work-session revisions retain their existing authority; Kiki-Mind is untouched.

## Hosted website and ChatGPT contract

Existing origin: `https://kiki-control-room.cherrylarch3.chatgpt.site`.
These additions are source changes until a deployment receipt is recorded.

- `GET /api/shared-queue`: authenticated Site identity; only a paired owner's
  snapshot, recent command results, runtime TTLs, and task evidence. Returns 403
  when the caller has no owner pairing. No user ID parameter or owner spoofing.
- `POST /api/shared-queue`: authenticated Site identity, same-origin `Origin`,
  JSON, at most 12 KB, at most 30 accepted commands per owner per minute. Supports
  `create` and `update`. Returns a durable request acknowledgement, not execution.
- `POST /mcp`, `tools/list`: adds `kiki_create_task({request_id, task})` and
  `kiki_get_tasks({})`. Existing four conversation/history tools remain. ChatGPT
  creation is a proposal with `authorization: pending`, attributed to `chatgpt`.
  Existing `kiki_get_brief` also includes `shared_queue` after Windows sync.
- Existing `POST /api/desktop-sync` retains Sites service authentication plus
  `X-Kiki-Sync-Key`. The same paired desktop/device/monotonic snapshot sequence is
  used. No extra cloud task writer, scheduler, or poller is introduced.

Hosted example (browser uses its signed-in Site session):

```json
{
  "op": "create",
  "request_id": "request-stable-0001",
  "task": {
    "intent": "Write a harmless Kiki test file",
    "next_step": "Write KIKI_OK in the approved sandbox and read it back",
    "origin": {"source": "control_room_web", "thread": "synthetic-thread"},
    "required_capabilities": ["local.file.write"],
    "prerequisites": [],
    "privacy": "synthetic",
    "authorization": "pending",
    "status": "AWAITING_APPROVAL",
    "priority": 0,
    "deadline": null,
    "timezone": "America/Chicago",
    "idempotency_key": "synthetic-file-0001",
    "effect": "sandbox_file",
    "payload": {"content": "KIKI_OK"}
  }
}
```

For the ChatGPT tool, omit `op`, use `origin.source: chatgpt`, and retain pending
authorization. Successful hosted acknowledgement:

```json
{"request_id":"request-stable-0001","status":"pending","authority":"windows_sqlite","message":"Request saved; waiting for Windows commit."}
```

Relay request IDs are owner-prefixed (`<owner>:<request_id>`) in D1 and SQLite.
The SQLite-created stable task ID arrives in `requests[].result.result.id` and
`tasks[].id` after commit. Reuse the exact command and request ID on network
failure. Changed content with the same key is rejected. Do not create a cloud task
while waiting for that acknowledgement. The create idempotency key also dedupes
across different HTTP request IDs and rejects changed task content.

## Windows runtime API

`POST http://127.0.0.1:8765/api/shared-queue`, JSON only. This is a new authenticated
route on the **existing loopback server**, not a public Python listener. Do not
expose it with a tunnel or change its bind address. The existing legacy endpoints
have not been promoted into an authenticated remote API.

Operator-provisioned `KIKI_QUEUE_CREDENTIALS` is a private JSON object keyed by
runtime ID. Each entry has a random `key` (32+ characters), a paired Site `owner`,
allowed operation `scopes`, a capability allowlist, and pinned `adapter_version`.
Never put this value in Git, a prompt, frontend storage, or a model context.
Credentials belong to executable adapters, not personas or model-generated text.

```json
{
  "runtime": "operator-provisioned-runtime-id",
  "timestamp": 1792380000,
  "nonce": "fresh-random-request-nonce",
  "command": {"op":"list","request_id":"stable-read-0001"},
  "signature": "hex-HMAC-SHA256"
}
```

Sign the entire envelope **excluding signature**. Canonical bytes are UTF-8 Python
`json.dumps(unsigned, sort_keys=True, separators=(',', ':'), allow_nan=False)`
(default `ensure_ascii=True`). Sign with HMAC-SHA256 using that runtime's key.
Timestamp is Unix seconds, accepted within 60 seconds; nonce is single-use,
retained for replay protection. Re-sign retries with a fresh nonce/timestamp but
keep `command.request_id` and command content unchanged. Limit: 60 valid signed
requests per runtime per minute. Keys select owner/scopes server-side; client
owner/capability claims do not grant authority.

Operations (all require `request_id` and their matching scope):

| op | additional fields | result |
|---|---|---|
| create | `task` | authoritative task with stable ID/version |
| list | none | owner tasks, events, runtimes, authority |
| read | `id` | same shape as list, one task |
| update | `id`, `version`, allowed `status`, optional `next_step`, `required_capabilities`, `authorization` | task; approval additionally needs `approve` scope |
| register | `tested_capabilities`, `adapter_version`, `probes`, `ttl` | health record; TTL 15–300 seconds |
| claim | optional `id` | `{task: task}` or `{task: null, reason: ...}` |
| heartbeat | `id`, `version`, `lease_token` | task with renewed lease and new version |
| finish | `id`, `version`, `lease_token`, `status`, `evidence` | task with outcome |

Claims use `BEGIN IMMEDIATE` on the existing database. One authorized eligible
task is selected by priority, aware deadline, then creation time. All required
capabilities and VERIFIED prerequisites must match. Queue pause prevents claims.
Lease fields: `runtime`, unpredictable `token`, Unix `until`; lease is 60 seconds.
Every claim increments `attempts` and `version`. Heartbeat and finish require the
current version, same runtime, live lease and token. Reload after a version
conflict. **Never execute a cached claim response without checking it is current.**

States: PROPOSED, NEEDS_DETAIL, QUEUED, CLAIMED, AWAITING_APPROVAL, BLOCKED, VERIFIED,
FAILED, CANCELLED. Missing capability detail prevents queueing. Approval is not
account connection; it authorizes only the described step. Expired claims become
BLOCKED with an interruption event. No automatic retry of uncertain effects,
including sends. A safety-denied task cannot be requeued through update. This
slice intentionally has no automatic reconciliation or override route for an
uncertain external effect; an action-specific verifier is required first.

Finish VERIFIED requires `evidence.provider_receipt` naming a durable READBACK
event emitted by an executable verifier for the same task, runtime and attempt.
A string such as “readback OK”, assistant utterance, arbitrary provider ID, or
conversation receipt cannot verify a task. BLOCKED/FAILED require a bounded
`evidence.reason`; platform denials additionally set `safety_denial: true`.

## Capability registration and adapters

Registration checks the operator's allowlist/version and a recent SQLite
TOOL_PROBE receipt written by executable adapter code. Arbitrary probe prose is
rejected. `queue_worker.py` probes actual file read/write or the private model
endpoint before registering; failed/offline probes do not create health.

Run one cycle from the existing permitted OpenClaw command policy:

```text
python runtime/local/queue_worker.py --runtime <provisioned-id> --sandbox <approved-existing-synthetic-directory>
```

It uses the existing DB by default; `--db` selects an isolated synthetic test DB.
It does not start a scheduler or Telegram poller. Only `local.file.write` is
provisioned for this mode. The destination is derived from the stable task ID,
uses exclusive create, flush/fsync and separate readback; an existing mismatch is
never overwritten. Paths and shell commands cannot be supplied by the task.

For Jan, omit `--sandbox` and provision only `local.draft.generate`. It probes the
existing private Jan transport and calls the model with no tools. Persisted draft
readback yields VERIFIED with `outcome: DRAFTED`; never SENT. Live Jan generation
and actual OpenClaw invocation remain separate deployment tests.

ChatGPT-only capabilities are not provisioned locally. There is no supported
local invocation of ChatGPT connectors. This slice does **not** expose remote
ChatGPT claim/finish tools or an external-provider verifier. A legitimately
connected ChatGPT session needs an approved runtime adapter and provider-specific
verification before it can execute those tasks; until then they remain pending
with no eligible runtime. Do not route a safety denial to another runtime.

## Inventory, risks, rollout, rollback

Inspected: issue #13 plus corrected architecture comment, #11, #8; actual hosted
source version 31 (`672b5bbad477d793df269fb9a3664a0f7d7f0b6d`); live Kiki connector
brief; SQLite schema; loopback API; existing Windows startup tasks and sync code.
The initial local checkout was `1d4de57`; fast-forwarded its existing prototype
branch to `c00c628` before feature work. The running Windows DB had 5 legacy tasks
and no queue metadata. The running process predates some checked-out schema
additions. Windows startup uses existing scheduled-kiki.py and pythonw.exe.

Risks/gates: the hosted source mirror and local runtime branches differ; source
patch must be applied against the documented Site baseline. Owner pairing must
remain one device/one owner. No D1 task migration is authorized. Additive metadata
does not invent provenance/verification for old tasks. Full audit is retained in
SQLite; snapshot size remains bounded by the existing 500 KB sync contract, so
large histories need pagination before scale-up. Independently encrypted backup
and restore are not established by this change. Real OS reboot and notification
delivery to a person are not proved by process restart or D1 receipt creation.

Before Windows activation: retain a source archive at c00c628 and a SQLite backup
using `sqlite3.Connection.backup` (WAL-safe). Stop **only** the existing Kiki Control
Room startup task, confirm port 8765 closes, then start that same task. Do not
start a second daemon or alter Telegram ownership. Preserve the existing local
model startup task. Provision only the bounded worker credential separately.

Rollback: stop the same Control Room task, restore the prior code from the source
archive or switch back to the original branch, and restart the same task. Additive
tables/column may remain; old code ignores them. Freeze new queue commands during
rollback, since old code cannot execute them. Do not restore an old DB over newer
execution receipts. If DB restore is needed, first preserve the newer DB and
reconcile external effects manually. Hosted rollback is Site version 31; keep the
same owner/viewer access policy and project ID. No token rotation is needed.

## Verification status

Commands from the repository root (Python must have tzdata on Windows):

```text
python -m unittest discover -s tests -p "test_*.py" -v
python tests/queue_http_acceptance.py <private-workspace-evidence-directory>
```

Hosted source, Node 22.13+:

```text
node --test tests/*.test.mjs
node scripts/run-framework.mjs build
```

66 Python tests passed, including claim races on two connections, duplicate and
conflicting submissions, stale versions/leases, offline runtimes, safety denial,
forged/replayed signatures, model-prose capability rejection, cross-owner reads,
legacy completion bypass, relay retries, draft-only Jan contract, and restart.
54 hosted tests cover the relay/projection, retry, isolation and TTL plus existing
session/history/follow-up behavior. Build passed before final documentation sync;
final build/test output belongs in the PR/deployment report.

Actual synthetic HTTP/file/cold-interpreter test:
`task-4246d735-4fc9-4349-839a-78697ce45bda`, readback receipt
`receipt-e6231ea7-bdf7-421b-ac17-9f6637e17d6c`, artifact SHA-256
`0ef4e9a95143a7f5f88d4338d1887856e6851c4f8168ef5ef9d24226ab731dcb`.
This is an acceptance harness invocation, **not** an OpenClaw or ChatGPT receipt.

Acceptance A–E are not yet fully passed. Gates are live Site/Windows rollout,
ChatGPT plugin tool refresh/approval and harmless task creation, real OpenClaw
command-policy invocation, live Jan draft generation, independent cross-surface
receipt read, gateway restart, and an actual Windows reboot. No calendar/mail
action is used in these tests. The existing poller and deferred local Google OAuth
remain unchanged. Do not claim end-to-end operation from these tests.

Concurrent deployment discovered before publication: Site version 33 is based on
`ceec58d0ee79f17539b4ab5640251a70162db254` (version 32 was `6e8719b`). The included
Site patch targets version 31 and must be rebased/checked against version 33 before
publication. This feature has not overwritten that deployment. Coordinate the
single owner/device mapping and transport contract here before either side
activates a new task integration. Windows activation has also not been performed.
