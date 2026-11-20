# AIRI shared Kiki integration plan

The target is AIRI 0.10.2 on Jay's laptop, using laptop Ollama. The existing Site D1 ledger remains the authoritative conversation history. Work-PC SQLite remains task authority. This integration adds a hosted work-session record, not a replacement task database. It does not route laptop replies through Jan.

## Implementation sequence

First, add authenticated laptop device enrollment to the existing signed-in Site, revocable device tokens, and an owner-scoped companion API. Reuse the existing event ledger, preserve exact reply text and distinguish human dialogue from assistant-initiated events. Provide recent and lexical historical context and a versioned shared objective, next action and pause state.

Second, add a local OpenAI-compatible proxy for AIRI. It retrieves history before generation, invokes laptop Ollama, records the exact final exchange, and returns the reply. A private local SQLite delivery queue holds unsynchronized receipts only; it never supersedes hosted history. Failed delivery is retried without generating a different reply. Restart and uncertain transport retries retain operation IDs. Model metadata identifies Ollama and the configured model without claiming ChatGPT or Jan generated the text.

Third, add opt-in local screenshot understanding through a configured local vision model. Frames are held in memory, never written or sent to the hosted ledger. A visible local control page exposes capture/pause status. Sensitive application exclusions and OS lock/idle checks gate capture. Screen content is untrusted observational context, never authorization for actions.

Fourth, add an AIRI 0.10.2 gateway client for scheduled check-ins. Use authenticated module announce and input:text/contextUpdates from the upstream protocol. Quiet hours, active-user checks, a cooldown, maximum unanswered invitations, and pause/snooze gates prevent repeated interruption. The bridge must be selected as AIRI's chat provider, and gateway connection must be ready before scheduling. Automatic inputs are recorded as system initiatives, never as words Jay said. Work sessions and natural conversation have equal standing; no invented action completion.

Finally, run adversarial checks for cross-account reads, revoked devices, duplicate delivery, concurrent requests, restart, offline operation, prompt injection boundaries, false provenance, screen pause, and scheduler flooding. Fix observed defects before publishing. Validate local HTTP proxy transport against simulated Ollama and hosted-service endpoints, and validate the hosted API against its test database. After deployment, check the existing authenticated plugin brief. Synthetic live conversation receipts, Windows capture, installed AIRI playback and actual Ollama latency require laptop acceptance and are reported separately.

## Completion evidence

A complete source build includes the hosted API, enrollment UI, Windows launcher and configuration wizard, local history-aware Ollama proxy, screen capture/vision adapter, gateway-driven proactive scheduler, pause/resume controls, documented setup and reproducible tests. Passing automated tests is not proof that the laptop installation has been run. Full live acceptance requires an old recorded fact retrieved in AIRI, exact dialogue appearing once in the Site, restart recovery, a screen-aware exchange, a proactive spoken check-in, silence after pausing and recovery from a network outage.
