# Kiki on AIRI 0.10.2: laptop setup

This build keeps Ollama inference on the laptop and records dialogue in the existing Kiki Control Room history. It does not require an OpenAI API key, Jan on the work PC, or a public laptop server. Python 3.10 or later and the already installed Ollama and AIRI are required. The optional screen feature additionally needs an installed Ollama vision model. A text-only model cannot describe screenshots.

## Start the laptop bridge

Download this branch as a ZIP or open its checkout. Extract the ZIP before starting. Double-click `start-kiki-airi-windows.cmd`. On the first launch it creates a dedicated Python environment and installs Pillow, websockets and timezone data from PyPI. Keep the terminal open while using Kiki. The bridge opens its private local controls in the browser at port 8766. Another process already using that port will prevent startup; the launcher will show the failure.

## Pair the existing shared history

Open https://kiki-control-room.cherrylarch3.chatgpt.site and sign in. In Preferences, the AIRI laptop companion section has a “Pair my laptop” control. Download the pairing JSON and import it using the local bridge’s “Connect your history” file field. The bridge validates the connection before accepting it. Delete the downloaded pairing file afterward: it contains private device and service access credentials. The working configuration stays under `%LOCALAPPDATA%\KikiCompanion`, outside the repository. Revoke the device from Site Preferences if necessary. Revocation prevents further history reads and writes through that device token.

The local delivery database is an outbox and context cache. It is not task authority or a replacement shared history. Do not delete it while replies are waiting to synchronize. A different pairing is refused while unsynchronized replies exist. A completed reply can be heard while its cloud delivery is pending, so inspect the status when offline.

## Choose the local conversation model

In the bridge controls select an installed Ollama model. In AIRI, use its OpenAI Compatible conversation provider. Set the base URL to `http://127.0.0.1:8766/v1/`, select model `kiki-local`, and paste the bridge’s local API key using the “Copy local API key” control. This authenticates only the local bridge; it does not invoke OpenAI. Save and test the provider, then make it AIRI’s active conversation provider. Leave AIRI’s speech and avatar selections as desired. The bridge buffers the full Ollama response and sends it in an OpenAI-compatible SSE response; speech begins after generation rather than streaming the first token immediately.

## Connect proactive conversation

In AIRI Settings, Connection, keep the gateway at `ws://localhost:6121/ws` and “Expose on network” at “This device”. Copy the masked gateway Auth Token into the local bridge’s password field and save. Do not put the Kiki Site URL into AIRI’s WebSocket address field. The local controls must report gateway ready and that AIRI has used this bridge before automatic check-ins are eligible.

Check-ins are enabled by default within 9 AM to 9 PM America/Chicago. They require an unlocked, recently active Windows desktop and a connected AIRI stage, wait at least 30 minutes since dialogue/output, stop after two unanswered invitations, and have a daily limit of six. They use the current shared objective if active or offer ordinary company when no work session is active. A paused shared work session blocks them. Local pause/snooze controls stop new screen captures and proactive check-ins. Restart recovery preserves unanswered limits, queued receipts, cached context and shared session; startup also gives a fresh quiet interval before another check-in. Sleep, lock and idle time suppress new invitations. Natural voice interruption and actual playback timing are AIRI behaviors and require live testing on the installed laptop.

## Add local screen understanding

Select a locally installed vision-capable Ollama model, enable the foreground-window screen option, and save. On each conversation or proactive reply, the bridge captures the foreground window only when the desktop is unlocked and recently active. A local vision request produces a short observational summary for the conversation model. Images stay in memory and go only to local Ollama; no image bytes are stored in the outbox or uploaded to the Site. Ordinary conversation may discuss visible content, so the resulting dialogue is still part of shared history. Password/private-window title exclusions are best effort, not a complete sensitive-data filter. Leave screen view off for content you do not want interpreted. Screen observations cannot execute actions.

## Save and resume our place

Use the local “Where we left off” controls or type `/focus objective | next small action`, `/next next action`, `/pause`, `/resume`, or `/done` in AIRI. These commands update the hosted, versioned work-session record. They do not change the PC task list, send email or book calendar appointments. The shared session appears in Site home and the ChatGPT plugin brief. Offline session edits report failure rather than silently overwriting newer shared state. Local `/pause` still takes effect if the shared service is offline.

## Verify the result

Begin with a harmless previously recorded Kiki detail. Confirm the reply uses relevant history, then check Shared history for the exact AIRI exchange and source. Save a work objective and next action, restart the bridge, and confirm resumption. Enable screen view on a nonsensitive test document and ask what is visible. During an active daytime session, wait for a check-in or temporarily use a shorter allowed interval through the authenticated settings endpoint. Confirm its input is recorded as an automatic Kiki initiative, not words Jay said. Pause and confirm no new captures or check-ins. Disconnect networking, converse locally, reconnect and refresh: each queued exchange should synchronize once. Revoke the test device and verify that it loses history access.

## Current acceptance boundary

Automated tests exercise the existing ledger and owner isolation, exact-once retry behavior, real HTTP proxy/provider/service transport with simulated upstreams, SSE compatibility, restart, pause, screen-byte routing, explicit session commands and v0.10.2 gateway messages. This environment cannot operate the Windows laptop. Actual AIRI speech playback, actual Ollama model quality/latency, foreground screen capture and a full laptop reboot remain live acceptance checks. No claim that those tests have passed should be made before running them.
