# Kiki on OpenClaw: reusable runtime package

Status: Prepared workspace profile, not installed on Jay's computer. Branch: `feature/kiki-openclaw-runtime-evaluation`.

## Why OpenClaw

OpenClaw provides a maintained agent loop, Windows Hub, background gateway, messaging channels, native automations/heartbeats, local-model support, device nodes, tool permissions, and optional computer interaction. We should use those capabilities rather than implement another computer-use agent, Telegram bot, voice driver, browser tool, or reminder scheduler from scratch.

Kiki's existing shared-history site and desktop SQLite are retained. Installing OpenClaw does not migrate conversations or task authority. OpenClaw's local conversation memory is a view/cache, not permission to rewrite Kiki-Mind or Kiki Control Room. The bridge that reads authenticated Kiki shared history and commits operational receipts is a separate, required, tested integration. Until then, describe this as a separate execution prototype, not a unified Kiki.

## First Windows deployment, performed by a local agent or operator

Use the maintained [official Windows guide](https://docs.openclaw.ai/platforms/windows) and [Windows Hub](https://docs.openclaw.ai/install) rather than instructions copied from older OpenClaw versions. A dedicated normal Windows user or isolated VM is preferable during evaluation. Install the official release, complete onboarding, verify `openclaw gateway status`, and open the Control UI. Existing Jan/Ollama or LM Studio can supply model inference, but actual tool calls must pass before choosing a local model for autonomous execution.

Back up the existing OpenClaw workspace, if one exists, before introducing any of the files in `workspace/`. Inspect differences; do not blindly replace a populated SOUL.md, MEMORY.md, or AGENTS.md. Use the Control UI under Settings > Agents > Files or a reversible local file copy to place the Kiki workspace profile in the intended agent's configured workspace. These public templates contain no account tokens. Actual workspace memory and model credentials must stay private.

Configure native heartbeats at an appropriate owner-confirmed cadence, with active hours and a resolvable owner DM destination. Use the current OpenClaw heartbeat documentation: the runtime's scheduled heartbeat is managed through native automations, not a handwritten infinite loop. The old HEARTBEAT.md scratch mechanism is not the current primary scheduler. Set command permissions to an approval-gated mode such as `ask` or `auto`; never turn on `full` to compensate for a failing demonstration.

## Telegram migration gate

The existing Kiki local Telegram poller already works and shares history. Two long pollers cannot safely own the same bot. Initially do not attach the existing Telegram bot token to OpenClaw. Verify the gateway privately through its local Control UI. Only after proving that the Kiki history interface and action receipts work should the old poller be paused, outstanding messages reconciled, Telegram ownership assigned to OpenClaw, and a single test message round trip verified. Restore the previous poller if migration fails. Do not paste bot tokens into GitHub or ChatGPT.

## Shared-history integration contract

The adapter must authenticate to the existing Kiki shared-history service using its supported provider protocol. It should read events incrementally by sequence and original source; prepare and commit user/assistant turns through the existing APIs when available; publish action proposals and execution outcomes to the desktop task owner; and reconcile duplicate event IDs and restarts. If the existing MCP endpoint is not exposed externally, build only the narrow bridge needed to expose it. Do not start a replacement memory database.

An OpenClaw decision to send a reminder is not proof that it was delivered. Store stable action IDs and outcomes in Kiki Control Room, preserve origin channel, and distinguish QUEUED from VERIFIED. University data and credentials must never traverse the public shared-history service.

## Minimal live acceptance

The first release is one safe synthetic interaction. OpenClaw initiates a scheduled Telegram check-in without Jay prompting it in ChatGPT. Jay replies. The transcript is retrieved in ChatGPT Kiki with correct provenance. Kiki remembers the next step after restarting the gateway. A test calendar action is created exactly once and independently verified. A separate local agent task writes one disposable sandbox file, with a recorded tool receipt. Kiki accurately says which operations ran and which did not. Only then promote OpenClaw to primary executive worker.

## Other repos

AliceMod (upstream pmbstyle/Alice) is an excellent optional Windows voice/avatar front end, especially for wake word, VAD, camera/screenshot understanding, and Chrome context. Avoid running its own autonomous scheduling, history authority, or duplicate Gmail/calendar rules alongside OpenClaw. Its local mode is described upstream as experimental. Rho is an alternative Linux/macOS/Android heartbeat and memory runtime built on Pi; it is a useful autonomous-behavior donor and a possible deployment choice on Calibos's Linux machine, not something to stack onto Windows OpenClaw by default. ClawPhone documents OpenClaw running in Android Termux with device access, valuable if a spare isolated Android device becomes available. chatbotAIML is a Program AB AIML bot with persistent sessions, but lacks the modern desktop action infrastructure required here. Gomoku's direct relevance was not established from available repository metadata, and it is not a dependency for the executive-assistant runtime.

## Launch posture

The practical hierarchy is: Kiki user-facing coordinator; OpenClaw as replaceable execution host; Kiki Control Room for operational history and task reconciliation; Kiki-Mind for identity; Alice or AIRI later as optional presentation; Calibos/Muse as independently operated delegated collaborator. Only migrate or replace a layer after a real end-to-end test proves improvement in executive burden. This work deliberately avoids creating a new standalone chatbot.
