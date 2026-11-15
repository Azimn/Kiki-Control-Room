# Moemate Core reuse review for Kiki

Reviewed October 15, 2026 (America/Chicago). Source: https://github.com/Azimn/moemate-core/tree/12e46689af4b31c6883f0f364861146a0dd130ac

## Finding

Useful as a reference and selective code donor for companion interaction. It is not a complete runnable replacement for Kiki or AIRI. The root README explicitly describes modules intended for the Moemate host. The core manifest declares minimum and verified host compatibility 0.8.8. No host implementation or top-level standalone application package appears in the inspected repository tree. This was a source review, not a runtime acceptance test.

## Strongest opportunities

The text skill separates spoken output from generation, queues voice playback through WaitForVoice, and retains text when synthesis fails. This is a useful pattern for Kiki's speech adapter: preserve the committed reply, queue audio, retain readable text and expose playback state. The actual host queue, streaming transport and audio implementation are outside this repository.

Source: core/scripts/skills/text.js

The expression skill routes speech and an emote together. Its current implementation chooses the first angle-bracket expression and uses a fixed 100 ms delay. That is useful as a sketch of coordinated presentation, not verified audio alignment or lip synchronization. Kiki should use explicit expression metadata and actual playback events. The mood skill separately maps neutral, angry, fun, joy, sorrow and surprise to host avatar state. These are presentation controls, not evidence of a cognitive affect system.

Sources: core/scripts/skills/expression.js and core/scripts/skills/mood.js

The conversation-flow prompt instructs the character to wait after questions and avoid unsolicited message spam. The stop skill waits for queued voice and sends a STOP event. Its comments acknowledge a host controller workaround that stops after every response. Kiki can adapt the turn-taking intent, but natural interruption, microphone echo handling and cancellation still require implementation and tests in our runtime.

Sources: core/prompts/conversation_flow.hbs and core/scripts/skills/stop.js

Prompt composition keeps character, retrieved memories, tasks, perception and conversation in separate templates. This is a useful organization pattern for supplying relevant task and browser context to Jan. The perception template accepts app title, screen summary, OCR and clipboard text, but does not implement the capture mechanism. The task template displays name, objective, status and result, but does not implement a durable work-session scheduler. Keep Kiki's existing history provenance and PC-owned task state.

Sources: core/scripts/core.js, core/prompts/perception.hbs, core/prompts/tasks.hbs and core/prompts/memories.hbs

## Voice and platform limits

core/models/talknet.json.hbs points to https://api.dev.moemate.io/tts with an authentication header. The repository does not supply Talknet model weights or a local synthesis server. Voice IDs do not establish availability or rights to external models. Azure and ElevenLabs are provider adapters, not included free local speech engines. Current service availability was not tested. AIRI remains the preferred installed candidate to test for Kiki's body and local voice support.

The inspected scripts rely extensively on window.companion, window.hooks, window.models_tts and window.models_llm supplied by Moemate. They cannot simply be pasted into the Kiki Site. Model adapters include GPT 3.5 and Claude v2-era APIs and require review before any current use. The web-search module depends on Bing and only carries the first result into context. It is not a browser controller.

## Reuse terms and recommendation

The repository LICENSE is MIT, copyright 2023 webaverse-studios. Preserve the copyright and license notice when copying substantial code. This source license does not establish access to hosted APIs or license external voice/model assets.

Adapt speech queues, text fallback, expression metadata and stop/wait behavior into Kiki's existing architecture. Use the prompt templates as references for task-aware context. Do not import the old provider layer, replace shared continuity or treat the modules as the missing Moemate host. No Kiki runtime or Site code was changed during this review.
