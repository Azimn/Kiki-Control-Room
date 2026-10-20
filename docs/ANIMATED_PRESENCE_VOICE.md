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
