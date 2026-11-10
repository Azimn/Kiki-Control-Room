# Kiki on Slack

The native Dodaios connector and the optional Socket Mode listener have different identities. Native actions use the signed-in Slack account. Socket Mode replies use the Kiki app's bot user and the existing Windows Control Room conversation worker.

## Native Dodaios Slack

On the Windows host inspected for issue 21, the loopback health endpoint reported Dodaios **4.1.2**. Its checkout was on `feature/kiki-browser-reliability` at `79830721f` with local changes. The live Plugins and Skills registries listed Slack and `plugin-slack`. Marketplace reported Slack as connected and the Agent Chat catalog advertised the `slack` tool as available. MCP listed the existing Kiki continuity connection. These are registry observations. The selected Kiki session's tool invocation, OAuth workspace, and provider access still need an authorized smoke test.

1. In **Dodaios > Plugins > Slack**, check which workspace the connection targets. For an approved workspace without a connection, select **Connect** and complete the Slack authorization in your browser. Review the requested scopes and identity before consenting. The shipped OAuth flow uses the project's `token.personaljarvis.ai` broker. Obtain institutional approval before connecting any restricted workspace.
2. Open the intended existing Kiki session and check that its tools include `slack`. Use an approved test channel and synthetic messages only. In Run Inspector, verify actual `search_messages`, `read_history`, and `read_thread` calls and their provider results. Use the parent message timestamp for `read_thread`.
3. Ask Kiki to post one synthetic line to that test conversation. First deny the confirmation and verify no provider send or worker handoff occurred. Then request a new send and confirm the exact account, destination, thread, and text. Record provider acceptance and independently read the message back. Native `post_message` uses Dodaios's `ask` tier.
4. Optionally import `skills/kiki-slack` into the existing Kiki session after reviewing it. The skill grants no capabilities. [Dodaios Slack usage card](https://github.com/Dodaios/Dodaios/blob/main/dodaios/marketplace/usage_cards/slack.md)

## Owner setup for the Kiki bot

1. Create one Slack developer app named **Kiki** for the approved test workspace. Enable **Socket Mode** and **App Home > Messages Tab**, including permission to send messages from that tab. Generate one app-level token with `connections:write`.
2. Add bot scopes `chat:write`, `im:history`, and `app_mentions:read`. Enable Event Subscriptions for only `message.im` and `app_mention`. Have the workspace owner or admin approve and install it to obtain the bot token. Use an isolated test DM first. Invite the bot to a test channel and add its ID to the allowlist only if testing mentions. Avoid shared channels and public endpoints. [Slack Socket Mode setup](https://docs.slack.dev/tools/python-slack-sdk/socket-mode/) · [Slack app mentions](https://docs.slack.dev/reference/events/app_mention/)
3. Copy `integrations/slack/slack.example.json` to a private directory outside Git and synced folders. Restrict the directory, SQLite files, and backups to the Windows account operating Kiki. Set the approved workspace, app, bot, bot user, human user, and conversation IDs. Use the app console for the app ID and Slack's `auth.test` response for the workspace, bot user, and bot IDs. The listener validates these three fields on startup. Start with only the owner's user ID and one test DM. [Slack auth.test](https://docs.slack.dev/reference/methods/auth.test/)
4. Inject `KIKI_SLACK_APP_TOKEN` (`xapp-`) and `KIKI_SLACK_BOT_TOKEN` (`xoxb-`) into the listener process from an OS-protected secret store or private launcher. Inject the same randomly generated 32+ character `KIKI_SLACK_BRIDGE_KEY` into both the listener and Control Room. Keep token values out of chat, Git, shell history, screenshots, log output, and browser code.

## Windows launch and status

Use a separate environment from Dodaios. Run from the repository root in PowerShell.

```powershell
$venv = Join-Path $env:LOCALAPPDATA 'KikiSlackVenv'
$private = Join-Path $env:LOCALAPPDATA 'KikiSlack'
py -3 -m venv $venv
& "$venv\Scripts\python.exe" -m pip install -r integrations/slack/requirements.txt tzdata
& "$venv\Scripts\python.exe" -m integrations.slack.kiki_slack_bot --config "$private\slack.json" --dry-run
```

Dry-run validates the config without reading tokens, opening a connection, or sending. For live operation, have the owner update the **existing** Control Room process to this branch, with its existing DB, model configuration and Telegram ownership. This branch uses the existing configured Jan worker. If it is unavailable, the adapter keeps the event queued and reports the latest runtime status through localhost health. Confirm the Jan backend is local and authorized for the test content before starting.

In a separate process with the injected secrets, start one listener explicitly.

```powershell
& "$venv\Scripts\python.exe" -m integrations.slack.kiki_slack_bot --config "$private\slack.json" --run
Invoke-RestMethod http://127.0.0.1:8766/health
```

Run the health command from a second shell. The listener acquires port 8766 exclusively before connecting. It backs off on initial connection failure and delegates active socket reconnection to the Slack SDK. Use Ctrl+C to stop the listener. For unattended operation, use one opt-in Windows scheduled task under the owner account, with the repository as working directory, the same private launcher, and **Do not start a new instance**. Keep the Telegram listener under its existing manager. Use the localhost health endpoint for status and leave it unforwarded.

## Optional direct Dodaios DM

If the Windows host already runs Dodaios with Kiki's local Ollama model, the
listener can route one owner's Slack DM to a dedicated tool-free Dodaios side
conversation. Create the side conversation with the same local provider and
model as the existing Kiki session, and add a private configuration entry
`"dodaios_chat": {"session": "<existing side chat id>", "model": "<exact local model>"}`.
Use exactly one owner and one DM in the allowlists. The adapter verifies the
side-chat surface and configured Ollama model against the local API on every
poll. The session should be reserved for this DM. Slack remains a user message
and any reported tool use prevents a reply.

Dodaios owns this conversation's text and native reply. The Slack spool stores
the delivery receipt and native turn reference. This mode does not start the
Control Room worker or send to its task queue. The regular Control Room path
above remains available when that runtime is configured. A direct Dodaios DM
has its own thread history in Dodaios. The local test does not establish
cross-surface memory continuity or live Slack delivery.

## Optional single peer exchange

For two separately installed Slack bots, use one private test channel and one
owner-selected thread. If the operator adds the `groups:history` scope and
`message.groups` subscription to Kiki, Kiki can accept an explicitly addressed
request from one verified peer bot. Set the private `peer_exchange` entry with
`app_id`, `bot_id`, `bot_user_id`, `channel`, `thread_ts`, and `dodaios_session`.
Use the peer's actual Slack bot identity and a different tool-free Dodaios side
session from the owner's DM. The message must start with the Kiki bot mention
inside that exact private thread. Kiki replies once in the thread and ignores
the peer's subsequent messages there. Normal DMs and other bots stay separate.
The peer must read the reply using its own authorized Slack integration.

## Data, approvals and receipts

- The private transport spool deduplicates by Slack team and event ID before acknowledgement. The Control Room's existing SQLite conversation table independently deduplicates the same event and records source `slack`, app, bot, user, channel, timestamp and thread. Completed Slack turns are excluded from hosted sync and other model surfaces. The local receipt reports `remote_text: unavailable`. The current hosted route has no verified Slack receipt contract, so the adapter sends neither content nor metadata to it.
- Only the same Slack participant and conversation contribute to the model's Slack recall. It receives no task list or other-surface dialogue in the Slack prompt. The Slack reply path can only commit conversational text. Route other-channel messages, reminders, and task requests through existing approval workflows.
- The configured allowlists authorize conversational replies to approved DMs and mentions. The adapter can send only to the originating DM or thread. It cannot search Slack or initiate posts. Provider acceptance is recorded separately from readback. For an ambiguous send or crash after sending started, the adapter holds the receipt as `uncertain` and does not retry blindly. Have an authorized operator inspect the original thread before deciding what to do. A 429 retains the queue item and honors `Retry-After`.
- The transport clears terminal bodies and retains IDs to suppress replay. Windows Control Room retains the local turn under its SQLite retention policy. Use only approved synthetic content during acceptance. To show Slack text on the existing same-owner local dashboard, set `KIKI_SLACK_LOCAL_HISTORY=1` in Control Room. The setting is off by default. Use the direct loopback dashboard and keep it unforwarded.

## Live acceptance

- Verify the workspace and bot identity, establish the Socket Mode connection and confirm localhost health. Record the health result without credentials.
- Send a unique synthetic fact from the allowlisted user and DM, then verify one `slack`-sourced local turn and one bot reply. Read the fact on the explicitly enabled local dashboard or another authorized surface and record where it was observed. Check that another thread cannot recall it. Hosted continuity requires separate authorization and an actual hosted receipt.
- Repeat with an approved channel mention, then with a mention inside an existing thread. Verify same-thread delivery. Use a denied sender or channel and confirm there is no reply.
- Stop the listener, restart it, and verify a redelivered event leaves one logical turn and one accepted reply. Separately stop the Control Room worker and verify queued status and recovery. Record provider acceptance and manual readback separately.
- Run the native confirmation and denial checks above. Record the workspace policy approval and synthetic test receipts. The draft implementation was tested using synthetic Slack events and provider responses.
