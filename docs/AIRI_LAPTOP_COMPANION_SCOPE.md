# AIRI laptop companion: first integration scope

Jay's direction, October 15, 2026: executive-function support and companionship take priority. Every tool does not need to work in every interface. ChatGPT is also installed and can handle work requiring its connected tools. AIRI is installed on the laptop with local Ollama; the older work PC separately hosts Jan. Do not route laptop conversation generation through Jan merely to obtain continuity.

## Verified installation target

The supplied Windows executable Properties screenshot reports file and product version 0.10.2.0. The matching upstream v0.10.2 source has tree SHA 6d61699d10df19e2bb239d37fb162ba4ff85497e. This establishes the target version, not proof of a working Kiki integration.

The v0.10.2 MCP configuration schema supports local stdio servers using command, args, env, cwd and enabled fields. It does not include the remote URL/header server configuration found on the newer upstream main branch. The earlier description of direct remote MCP support applies to newer source, not this installed version. A locally launched adapter can still communicate outward to an authenticated hosted service.

Source: https://github.com/moeru-ai/airi/blob/v0.10.2/apps/stage-tamagotchi/src/shared/mcp-config.ts

The same version supports an OpenAI-compatible conversation provider with a custom base URL. This permits a local conversation adapter to forward generation to the laptop's Ollama service while adding history and recording the exact reply. It does not require using OpenAI inference. Authentication and protocol compatibility require implementation and testing.

Source: https://github.com/moeru-ai/airi/blob/v0.10.2/packages/stage-ui/src/libs/providers/providers/openai-compatible/index.ts

## Minimum useful experience

Kiki maintains her familiar voice and conversation context, brings forward one manageable next action, and retains a stopping point after interruption. The laptop remains usable for local conversation when the work PC is unavailable. Shared history requires an internet connection; any offline delivery must be explicitly marked pending until acknowledged.

Retrieve relevant hosted history before generation and commit the exact final exchange afterward. Keep source provenance and stable retry IDs. These steps should be enforced by the adapter, rather than left to discretionary model tool calls. Reuse the existing shared ledger; do not create a competing history store. An operational next-step record is separate from narrative conversation receipts and must retain its authoritative owner.

The adapter needs its own authorized device authentication. The present Site MCP route relies on authenticated ChatGPT identity and is not directly callable by AIRI merely by pasting the URL. The existing desktop sync also binds one task-owning device, so do not reuse its credential as a second independent SQLite authority.

## Division of work

AIRI on the laptop provides conversational company, voice and avatar, and the stronger local model where hardware permits. The hosted Site preserves shared conversation evidence. The work PC retains its existing task authority and scheduler. ChatGPT remains available for tasks needing its connected capabilities. A handoff records objective, last verified outcome and next action; merely having ChatGPT installed does not make automatic app-to-app delegation available.

Calendar, email, browser automation and full tool parity do not block the first integration. A laptop companion may prepare work and hand it off without claiming an action was executed. Proactive initiation, automatic receipt capture and interruption recovery must be tested separately from ordinary chat.

## Acceptance demonstration

Discuss a detail previously recorded through ChatGPT; verify AIRI receives the relevant source-attributed context. Work on one task using laptop Ollama, record the stopping point, close and reopen the interface, then resume accurately. Verify the exact AIRI exchange is present in hosted history once. With the work PC unavailable, conversation should still work; unsupported actions should be stated as unavailable or pending. No runtime deployment or laptop configuration was performed by this scope update.
