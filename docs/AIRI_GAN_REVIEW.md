# AIRI companion adversarial build review

Review mode: builder implementation followed by a separate adversarial inspection pass and regression fixes. This was not an external human review or an independent model assessment. Date: October 16, 2026, America/Chicago.

## Findings repaired

The initial proactive marker lookup could classify a later human message as an automatic initiative while AIRI retained earlier context. It now requires the check-in input shape, recognizes a registered nonce, and permits a consumed nonce only for a byte-equivalent request retry. It searches newest initiatives first and retains recovery across slow generation rather than expiring a valid marker mid-retry.

The first pairing implementation could reuse cached context when credentials were replaced. Pairing now refuses replacement while replies remain unsynchronized, rotates the local thread and clears cached owner context after a verified replacement. Request fingerprints include the paired device identity.

A final failed-first-pairing check exposed an unsafe rollback path for an initially unpaired laptop. Credentials are now verified before any persistent configuration changes, with an HTTP regression test proving that failed verification leaves no candidate credential behind. The Windows launcher also retries dependency installation on subsequent launches after an interrupted setup.

Initial Windows ctypes calls relied on default 32-bit handle return types. Explicit pointer signatures now cover desktop and foreground-window handles. Runtime Windows capture remains unverified in this Linux build environment.

Initial AIRI receipts were visible to plugin history but absent from the PC’s conversation-turn join. Receipts now include the same conversation-turn linkage used by existing clients. Automatic initiatives use a system actor and a distinct event kind/source. PC context explicitly labels these as automatic Kiki initiatives, not words Jay said.

The previously documented archive-export patch had not been applied in the deployed Site source. It is included in this build, with owner isolation and cursor pagination tests, so relevant older history can backfill to the PC without changing task authority.

Local pause initially stayed on after its time window expired. The capture gate now evaluates the deadline. Pause commands are handled before any screenshot request. Explicit work-session commands save through version checking and do not claim success on failed shared writes.

TypeScript checking caught unknown JSON response types in the pairing UI. These were corrected before the production build.

## Requirements and evidence

Shared history uses the existing D1 ledger, fixed AIRI provenance, actual configured local model metadata, immutable records and stable operation IDs. Owner/device isolation, revocation, exact retries and transactional rollback have automated coverage. Offline generation retains a private delivery queue and clearly reports pending synchronization. A lost cloud response replays the saved reply rather than generating another.

Local inference uses only loopback Ollama, never the work PC’s Jan. Screen frames go only to local vision inference; tests assert they never enter hosted receipts. The actual generated dialogue is synchronized. Proactive behavior is gated by gateway readiness, recent user activity, quiet hours, cooldowns, daily limits, unanswered invitations and pause state. Session objective and next action survive restart through shared state and are visible to the Site and plugin.

The local proxy requires a generated bearer key, binds only loopback, rejects unrecognized Host values, and does not log request bodies. Hosted pairing uses the existing signed-in Site and same-origin checks. A separate hashed, revocable laptop credential scopes owner access; the work PC’s task-sync credential is not reused.

## Remaining acceptance limits

The implemented bridge and hosted counterpart can be built and tested here; the installed AIRI and Windows desktop cannot be operated from this environment. Therefore a 100 percent end-to-end compatibility claim is not justified yet. Live installation, actual gateway delivery/voice rendering, screenshot interpretation by the chosen local vision model, conversational latency and Windows sign-in/reboot are outstanding acceptance tests, not passed requirements. No avatar asset was created or changed in this integration build.
