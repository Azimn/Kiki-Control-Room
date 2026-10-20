# Kiki animated presence and voice (browser prototype)

Status: candidate implementation, not deployed to the hosted Site.

This feature enhances the existing SVG portrait and adds a voice selector, manual Read/Stop buttons, and an optional Speak new replies checkbox. Browsers use their own SpeechSynthesis voices, so the voice catalog and vocal quality vary by device. Preference is saved locally in the browser only. Playback may require a user tap on iOS; it is not a persistent background voice and does not require API billing.

The portrait animates with blinking, the existing float, thinking/speaking halos, a talking mouth driven by utterance playback events, and a brief completion celebration. Mouth movement is approximate, not phoneme-level synchronization. Reduced-motion settings disable ambient and celebration animation.

The companion script never contacts third-party servers or collects microphone audio. It reads the existing conversation snapshot, skips replaying historical responses at startup, and does not speak replies unless the user opts in or taps Hear Kiki. Speech resumes only in the visible tab. No identity, memory, task, scheduling or backend changes are introduced.

## Integration and acceptance
Use the new CSS/JS assets in the existing dashboard. Local prototype: run the server using the documented local Windows setup and open its same-origin site. Test Safari iOS, Chrome/Edge Windows and Android where available. Test no speechSynthesis support, voiceschanged arrival, reduced motion, stop/cancel, page hide, missing/localStorage-disabled, new reply after polling, duplicate polling, and a blank/queued reply. Compare rendered task state with pre-change local server; no new task authority is allowed.

For the hosted Site, use this code as a bounded UI-only patch. The actual hosted source has a separately versioned deployment, and the local HTML must NOT replace it wholesale. The site runtime must deliver the two assets and connect its existing reply event to KikiPresence.onConversations when its data structure differs. Production read/write auth, synced history and native audio endpoints are intentionally untouched.

## Voice quality upgrade later
A consistent voice across Windows and iPhone requires an authenticated audio endpoint that produces a voice recording with a selected synthesizer, e.g. a locally operated Kokoro/Piper process plus a controlled bridge reachable from each device. Do not put private model endpoints, API keys, or loopback-only URLs into public web code. Keep browser speech synthesis as a fallback. Introduce a shared audio playback contract with real start/end events before changing lip sync.

No server-side voice service has been installed or verified by this PR.

## Voice candidate decision (October 20, 2026)
The owner favors a voice called **Jennifer** in a Kokoro-based experience and finds a particular Meta/Facebook conversational voice especially appropriate for Kiki's playful valley-girl delivery. **Neither voice is currently available in the Kiki dashboard.** Jennifer is not present in the published set of 54 standard Kokoro voice IDs, so the specific app, preset file, or service that supplies this variant must be identified before wiring it into the synthesizer. Do not silently substitute `af_jessica` or another standard voice as Jennifer.

The current Meta Model API (models reference, accessed 2026-10-20) lists Muse Voice Transcribe for speech-to-text and explicitly says it **does not synthesize speech**. Meta's consumer-app voice picker is not documentation of third-party access to its exact voice presets. Do not automate extracting audio from Meta consumer sessions, clone an unidentified Meta speaker, or claim that an XR/Wit.ai voice preset is the same voice. Confirm API access and license before choosing it as a production provider.

The chosen deployment direction is a **server-side audio provider with browser fallback**. A same-origin, authenticated dashboard endpoint should synthesize utterances using a locally hosted Kokoro service if available, return a playable MIME-typed audio stream/blob, and signal real audio start/end to the existing SVG animator. The site must not expose private service addresses, credentials or audio to other users. The original text stays visible on audio errors. Apply a hard length bound, throttling, and caching, and allow cancellation. In a hosted Site, a browser cannot reach an unauthenticated Windows loopback address across devices; route requests through existing private PC-to-hosted communication or a deliberately secured bridge. This is **design only**, not a deployed service.

For voice evaluation, compare the actual Jennifer sample the owner likes against the named standard Kokoro voices `af_nova`, `af_sky`, and `af_heart`, if those are available in the runtime. Selection should prioritize consistent recognizability across laptop and iPhone, quality at normal cadence, and low latency without paid API usage. Prosody should come from properly punctuated Kiki responses and permissible synth controls, not inserting stereotyped catchphrases into work-related factual content.

References: https://dev.meta.ai/docs/models and https://github.com/OpenTTSGroup/kokoro-open-tts (voice list).
