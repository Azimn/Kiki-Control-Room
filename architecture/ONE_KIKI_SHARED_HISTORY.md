# One Kiki, multiple interfaces: shared history v0.1

Status: architecture contract and portable SQL migration. The hosted database, ChatGPT plugin, and multichannel event pipeline are **not yet deployed or integrated**. This contract is independent of the local-first prototype in PR #1, so the two branches should be integrated deliberately rather than replaced wholesale.

## Objective

Kiki should remain one continuing assistant across Telegram, the hosted website, ChatGPT, and her locally installed runtime. Every authorized interaction with Kiki must contribute to one shared, attributable interaction history. No front end may silently become an independent autobiographical or operational database.

Kiki Control Room owns the cross-channel receipt ledger, task coordination, and real-time delivery. Kiki-Mind retains separate epistemic authority over subject history and developmental evidence. An interaction receipt proves that a message was recorded with a stated source, not that every statement inside the message is true or that Kiki experienced it in the strong autobiographical sense.

## Authority boundary

The online service is the authoritative writer for interaction receipts and task state. A D1 database is a reasonable initial candidate because it accepts SQLite-compatible SQL and can be reached from scheduled Workers even when the home computer is off. The provided migration `architecture/migrations/001_shared_event_ledger.sql` defines the required append-only events, threads, turn receipts, source identity, deduplication, and replica cursors. It does not create a database or deploy a Worker.

Kiki-Mind's own canonical events and invariants must not be replaced by this ledger. A local Kiki-Mind bridge may project verified incoming receipts into its own formal evidence intake. It must not implicitly promote a Telegram claim, model-generated summary, or task completion to Kiki's literal autobiographical experience.

Only the authenticated online backend may commit canonical interaction events. Clients can propose requests and supply source identifiers, but they do not directly write databases. The local SQLite copy is a rebuildable, encrypted-at-rest replica for context and autonomous local processing. If the cloud connection disappears, the local runtime may queue drafts and requested actions with stable idempotency keys. It must display them as pending until the online backend accepts them. It may not silently diverge or claim uncommitted actions succeeded.

## ChatGPT is a first-class client

Use the official custom MCP plugin path, not browser DOM scraping, ChatGPT session cookies, or automatic extraction of unrelated ChatGPT conversation history. Current OpenAI plugin documentation supports authenticated MCP tool calls, including read and write tools, through a publicly reachable HTTPS endpoint or supported Secure MCP Tunnel. Private data and write tools require end-user authorization and per-request enforcement on the server.

The initial MCP tool surface should have these contracts:

| Tool | Purpose | Writes |
| --- | --- | --- |
| `kiki_get_brief` | Read the current summary, tasks, active commitments, and verified subject context. | No |
| `kiki_prepare_turn` | Persist the user's explicit Kiki-directed message once, return `turn_id` and provenance-scoped recall context. | Yes |
| `kiki_commit_turn` | Persist Kiki's proposed answer once for that `turn_id` and return the immutable committed text. | Yes |
| `kiki_get_tasks` | Read a bounded, authenticated task projection. | No |
| `kiki_propose_action` | Create an auditable calendar or message proposal without executing it. | Yes |
| `kiki_confirm_action` | Execute only after explicit, narrowly scoped user approval, with a safe duplicate check. | Yes |

`kiki_prepare_turn` and `kiki_commit_turn` form the explicit logging boundary. ChatGPT may generate a candidate response after receiving the context. The committed assistant text returned by `kiki_commit_turn` is what the ledger records. Prompt the model to present that exact committed reply to the user. The chat UI may nevertheless add surrounding text or fail to invoke a tool, so **never claim to have captured the complete native ChatGPT conversation verbatim**. Track a commit receipt and differentiate `generated_and_committed` from `displayed_in_host_unverified`.

Each write carries a backend-validated owner identity, a globally unique client retry key, thread and turn IDs, source channel, actor attribution, a minimal model/runtime declaration when available, and structured provenance. A repeated prepare/commit request with the same key must return the same receipt without creating another event. If the model produces no response, the prepared user turn remains pending and can be recovered or explicitly abandoned without invented dialogue.

Native ChatGPT can serve as the inference renderer **during conversations invoking the plugin**. This does not make a ChatGPT subscription a freely callable background inference service for scheduled Telegram messages. When no ChatGPT session is active and no local model is online, Kiki can still send deterministic reminders from cloud scheduling. For generative replies without a user-initiated ChatGPT session, Kiki needs a separately accessible model runtime or an eligible authorized inference integration.

Voice access through a Kiki website and browser speech APIs is separate from native ChatGPT Voice. Custom MCP availability during a native Live Voice session must be tested rather than assumed.

### Coordinating ChatGPT's other tools

When available in the user's ChatGPT session, ChatGPT may combine Kiki's MCP tools with independently authorized calendar, email, GitHub, or other app tools. Kiki's MCP server must not impersonate those connectors or assume it can read data that has not been explicitly provided through the host. For example, ChatGPT can obtain a permitted email from the mail connector, ask Kiki for relevant communication context, draft the reply, and submit the *proposed* draft or action outcome as an attributed Kiki event. The exact content, source, and user approval status must be preserved. Never mark an external email as sent merely because ChatGPT drafted it.

This is a key reason to keep the ChatGPT interface first-class: it provides a capable user-invoked reasoning environment and access to separately approved tools, while Kiki's own durable backend provides continuity before and after the session.

## Multi-interface conversation continuity

Telegram receives a private message, authenticates the configured chat, records it through the shared backend, and retrieves context for the reply. The web interface reads the same conversation log and task projections. The ChatGPT plugin reads the same authenticated context and adds explicitly routed ChatGPT exchanges. Kiki on the old computer streams newly committed events by sequence number and submits evidence or pending operations through the cloud service.

An authorized Kiki interaction from any channel becomes visible to the others after the service commits it, subject to normal delivery delays. Preserve each channel's native thread ID while linking it to the canonical user and subject identity. A channel switch should begin with a bounded, provenance-aware summary and selectively recalled earlier exchanges, not blindly inject a lifetime of raw history into every prompt.

A user's ordinary conversation with ChatGPT, outside Kiki's tools, is not a Kiki interaction. It must not be ingested automatically or presented as Kiki's experience.

## Scheduling and failure behavior

Cloud scheduling owns reminders and commitments that must fire even when the home computer is off. It emits delivery attempts with deduplication keys. The local daemon can contribute richer reasoning and computer interaction but must not create duplicate reminders using a competing scheduler. Telegram should have exactly one inbound update receiver (webhook or long poll), though authorized senders may share an outbound transport with coordinated idempotency.

If the cloud is unavailable, a hosted website should report the connection problem rather than present stale state as current. The local app can offer clearly labeled offline tasks and queue proposed events. On reconnection, the service checks keys and ownership, returns accepted event sequence numbers, and rejects conflicting mutations for explicit reconciliation. Every database migration must be reversible where feasible and preceded by a verified backup.

## Confidentiality and backups

Use OAuth 2.1 for the private MCP plugin with user identity checked server side, HTTPS transport, restricted scopes, rate limits, and confirmed write authorization. Never publish message bodies, tokens, calendar credentials, or task data to GitHub. Do not rely on a secret embedded in website JavaScript. Avoid accepting a source channel label or owner ID as proof of identity.

An online D1 database is **not its own independent backup**. Export encrypted, integrity-checked snapshots and immutable event ranges to a second storage provider, and keep a regularly verified local copy. Document and test restoration on an isolated environment. Make deletion and retention controls explicit so old messages can be purged by an authorized administrator while maintaining audit evidence that deletion was requested. Append-only refers to application writes, not an excuse to prevent legitimate retention or erasure operations.

## Decisive acceptance test

From Telegram, send Kiki a unique arbitrary fact and receive an acknowledged receipt. Turn off the old computer. Use Kiki through the hosted website and then a connected ChatGPT MCP plugin to request that fact. Both must retrieve the same evidence, correctly attributed to Telegram, without inventing a Kiki first-person memory. Send a new message through the ChatGPT plugin using `kiki_prepare_turn` and `kiki_commit_turn`; it must appear in Telegram and on the website with its ChatGPT source. Restart the local computer and confirm it catches up from the last event sequence number. Retry the same write twice and verify only one committed event exists. Restore an encrypted backup to a clean test database and verify checksums and the same event order.

If any channel loses the fact, creates a divergent record, claims to log a native ChatGPT reply it did not commit, or fails the offline-reconnect test, shared-history integration is not complete.

The relevant model-access choice is secondary. A single, source-accurate history and reliable proactive task service come first.
