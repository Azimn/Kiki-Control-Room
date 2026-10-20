# Kiki in Rakazo: Kokoro Jessica voice and voice chat

Status: implementation-ready integration recipe (NOT installed or live verified in the owner's Docker host). Updated October 20, 2026.

## Finding: Rakazo already has the integration
Rakazo upstream provides Voice settings > **Self-hosted**, backed by an OpenAI-compatible speech adapter. Source: `elie222/rakazo/packages/adapters/src/openai-compatible-voice.ts` and `apps/web/src/pages/VoiceSettingsOverlay.tsx`. The provider explicitly expects Kokoro-FastAPI-style `GET /v1/audio/voices` and `POST /v1/audio/speech`. It labels `af_jessica` as Jessica when the speech server lists that voice. Speech model: `kokoro`. The adapter requests `response_format: "mp3"` and sends Kokoro language code `a` for the voice prefix. Do not fork Rakazo or introduce an agent/plugin solely for TTS.

Rakazo's native UI already has a **Speak this reply** button, **Hold to talk**, and **Call**, assuming a sufficiently new Rakazo release and working microphone/speech services. Voice chat involves two independent directions: Kokoro = text-to-speech for Kiki; speech recognition = microphone-to-text. Kokoro-FastAPI alone does not provide the Whisper transcription endpoint required for provider-side recognition.

## Quick Windows CPU prototype
Run on the *trusted Windows Docker Desktop host*, not inside Kiki's disposable bot sandbox:

```powershell
docker run -d --name kiki-kokoro --restart unless-stopped -p 127.0.0.1:8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
```

This is an example for evaluation using the upstream published image; pin the image digest/tag for repeatable production after testing. Check `http://127.0.0.1:8880/web` from Windows or `http://127.0.0.1:8880/v1/audio/voices` to see whether `af_jessica` is listed. First startup may need time and memory. The CPU image avoids relying on CUDA/GPU support.

**Network boundary:** The Rakazo server process may be inside another Docker container. `127.0.0.1` entered *in Rakazo's Voice settings* would refer to the Rakazo backend container, not Windows, and is usually WRONG. On Docker Desktop, test the host bridge URL `http://host.docker.internal:8880/v1`. Docker Desktop's host routing may not reach services whose published ports are restricted to 127.0.0.1: if verification fails, debug container-to-host reachability before altering access controls. Do not publicly bind Kokoro without access restrictions. An isolated shared Compose network with a private IP is another option, but network routing, DNS validation and deployment layout must be confirmed before choosing it. Never place an unauthenticated speech server on the public internet.

### Rakazo UI setup
In the **Rakazo browser/desktop UI**, open **Settings > Voice**. Select **Self-hosted**, enter **Server URL: `http://host.docker.internal:8880/v1`** (or a confirmed private container-reachable host URL), keep **API key** blank for this local server, enter **Speech model: `kokoro`**, and leave **Transcription model** unchanged unless you also have a verified transcription service. Select **Connect**. The UI should load a voice list from Kokoro. Select **Jessica** (`af_jessica`) in **Voice**, then choose **Hear a sample**. Now Kiki's normal text replies can use **Speak this reply**; Rakazo's **Call** button opens its built-in voice conversation UI.

If `af_jessica` is absent from the voice list, query the actual speech server and confirm the installed image/voice catalog. Rakazo's fallback list is limited and does *not* include Jessica. Do not choose Heart and then report that Jessica was installed.

### Input/transcription and device differences
In Chromium-based desktop browsers, Rakazo may use the Web Speech recognition API to convert microphone speech to text; success varies with the browser and its recognition service. In Electron, Rakazo deliberately avoids assuming web speech recognition works. Rakazo's web voice-call implementation may require a separately configured Whisper-compatible transcription endpoint if the browser cannot recognize speech. The native mobile app has an independent on-device recognition option when available; the phone's offline speech *output* is not Kokoro's Jessica voice. Disable device voice in its settings if using server-generated Jessica clips, and confirm reachability of the Rakazo API over HTTPS from the phone. The phone does **not** need direct exposure to Kokoro: Rakazo's backend generates authenticated speech clips for its own clients.

Test **voice output** before attempting a full phone call. Validate speech-to-text with real mic permissions before claiming two-way voice chat is working.

### Safety and acceptance
Do not overwrite Rakazo's existing Docker volume or Kiki's memory/task database, and do not expose `8880` publicly. Test from Windows Rakazo UI: connected provider, Jessica selection, sample MP3, text reply spoken, stop/replay, and the Call screen. Then test from iPhone on the connected custom Rakazo server; its HTTPS availability and speech-recognition permissions are separate gates. Confirm memory continuity remains intact. Check resource consumption alongside Gemma 4 during simultaneous generation; CPU Kokoro adds RAM/CPU pressure but no model-provider API billing.

## No production deployment performed
This document records supported native integration and a proposed local launch command. The actual Rakazo Docker host and its running image version were not inspected in this session, and no container was started or credentials changed.

Upstream references:
- https://github.com/elie222/rakazo/blob/main/packages/adapters/src/openai-compatible-voice.ts
- https://github.com/elie222/rakazo/blob/main/apps/web/e2e/voice.spec.ts
- https://github.com/remsky/Kokoro-FastAPI
