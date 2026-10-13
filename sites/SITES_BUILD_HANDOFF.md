# Kiki Control Room: ChatGPT Sites build handoff

**Status:** implementation handoff, not a published Site. This project is staged in `feature/sites-mcp-integration`; the shared-history contract and SQL migration are inherited from `design/unified-history-chatgpt-mcp`. The PC runtime is being developed separately in PR #1. Reconcile the branches before production use.

## Build target

Create a private, visually polished, mobile-friendly **ChatGPT Site** named **Kiki Control Room**, including a Site-hosted MCP server and plugin. Kiki is the same assistant across Telegram, ChatGPT, the website, and her local computer. Each interface reads from and writes to the **same authoritative interaction ledger**. Never create an unrelated Site-only memory store.

Use `architecture/migrations/001_shared_event_ledger.sql` as the starting database schema. The portable tool logic in `sites/kiki-tools.mjs` defines the behavior for four initial MCP tools, tested with `tests/sites-tools.test.mjs`. Adapt this logic to the Site's supported server/data layer and auth system, rather than assuming a Node library can be pasted directly into the hosted Site runtime.

## Visual character direction

The user supplied a visual reference in the source ChatGPT conversation: a feminine Art Deco gold android, reflective golden face and articulated torso, blonde short sculpted curls, dark bronze mechanical details, elegant 1920s/1930s retrofuturism. **Use the actual image as the hero portrait** with its original composition, not an unrelated purple-haired illustration or a generic cartoon human. Get permission to store and publish the reference as a Site asset before sharing externally.

Use a professional visual interface with a warm gold, deep plum/charcoal, and subtle champagne palette. Include a compact left navigation, a primary voice and conversation panel, a single active task card, a small upcoming commitments area, and an always-visible connection indicator. Animate the character subtly (mouth or eye states, glow, idle movement), keep reduced-motion accessible, and avoid claiming accurate real-time lip synchronization.

Display one actionable task at a time, with 'Start together', 'Snooze', 'Done', and 'Talk to Kiki'. Do not fabricate connected calendar entries, inbox counts, or memories. Where backend capabilities are absent, show a clear unconnected state and demo examples explicitly marked as synthetic.

Use browser speech synthesis to prefer an available feminine-sounding English voice. SpeechSynthesisVoice metadata does not reliably identify gender on every OS. Provide an explicit accessible voice picker and remember its preference only as UI state. Do not silently upload microphone data; obtain user permission for any cloud transcription.

## Persistent storage and authority

There must be exactly one authoritative interaction ledger with server-side authenticated read/write access, and a separate Kiki-Mind canonical continuity boundary. The online database must not be a replica competing with the PC's SQLite. The PC caches data and can queue offline actions, which are pending until the online service accepts them. Kiki-Mind remains the authority for its own subject-level historical evidence.

Every conversation event has a source channel, thread, turn, timestamp, stable ID, and provenance. Telegram, ChatGPT and Site-origin interactions use the same owner identity after secure account mapping. No browser client chooses `owner_id`, `actor_id`, or a trusted source label. Cross-account access is forbidden. No authentication token or privileged API URL goes in client JS or the public repository.

The Site should either use the intended canonical cloud database or an authenticated adapter to it. **Do not add a second independent Site storage database** merely because one is available in the Sites UI. If the Site creates its own D1 binding, designate that D1 as the single authoritative backend and have the future Telegram/PC services use it.

## ChatGPT-facing tools

Expose the behaviors implemented in `sites/kiki-tools.mjs` with these initial tool names and strict read/write descriptions:

`kiki_get_brief`: read a bounded provenance-preserving recent event summary and pending turn count.

`kiki_get_history`: read events for one authorized thread, paginated and source-attributed.

`kiki_prepare_turn`: accept explicit user speech/text directed to Kiki, with a stable retry key, and commit the original user message exactly once.

`kiki_commit_turn`: commit the exact intended Kiki reply to a prepared turn, idempotently. Return the committed text for display. A recorded committed response is **not proof** that the native ChatGPT interface rendered it exactly.

Require user authorization before writes, and do not assume unrelated native ChatGPT messages are retrievable. The plugin should not claim background ChatGPT inference or capture messages from conversations that never invoked Kiki's tools.

A future release can add `kiki_get_tasks`, `kiki_create_task`, `kiki_propose_calendar_action`, and `kiki_confirm_calendar_action` after a coherent task projection and scoped approval flow exist. Do not expose unimplemented capabilities as working tools.

## Site build and publishing workflow

Start from ChatGPT **Work** on web or Work/Codex on desktop, and ask to create a ChatGPT Site using this handoff, the original Kiki image, and the repository's Sites branch. Add the MCP tools to the Site through the supported Sites workflow. The Site owner must publish to create the associated plugin and then install/connect it in ChatGPT.

Keep the Site private during development. Test the plugin's tool list, user authorization, read-only retrieval and write approvals in ChatGPT. If the Site is updated, republish so the plugin receives new tools. There is currently no claim in this repository that the Site has been created, published or connected.

Official documentation:
https://help.openai.com/en/articles/20001339-creating-and-using-chatgpt-sites
https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites

## Acceptance sequence

Create a private synthetic conversation through the Site. Verify that the same conversation is retrieved through its MCP plugin in ChatGPT, including source and timestamps. Send a second message through ChatGPT using `kiki_prepare_turn` and `kiki_commit_turn`, then reload the Site and verify the exchange exists exactly once. Retry the same request key: no duplicate event. Attempt a different authenticated owner: access must fail. Shut down the old PC: the Site and plugin must still read/write the authoritative history. Reconnect the PC after its sync adapter is implemented and verify it catches up from the shared ledger.

Do not mark cross-source continuity complete until a live Telegram integration uses that same backend. Do not mark backups complete until an encrypted export has been restored and checked against the event order.

## Operational limit

ChatGPT Sites has beta quotas and availability restrictions that may change. A published Site's MCP plugin is an authenticated conversation interface, not an automatic subscription-powered inference server for Telegram. For unattended reminders or autonomous model interactions, use an explicit cloud scheduler and a separately available model or rules-based workflow. The local computer remains optional for richer processing when online.
