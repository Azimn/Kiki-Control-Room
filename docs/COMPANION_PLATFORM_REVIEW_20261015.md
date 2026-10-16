# Kiki companion platform review and Site recovery

Date: October 15, 2026 (America/Chicago).

Jay reports AIRI is already installed for earlier Pretorius testing. Local installation and Kiki integration have not been inspected. Work tonight focuses on the hosted Site because the work computer is unavailable until morning.

## Platform decision

AIRI is the preferred candidate to evaluate as an optional Kiki avatar and voice surface. Its repository documents web and desktop stages, Live2D and VRM models, browser audio input, speech recognition, multiple voice providers including local Kokoro, and Ollama support. These are upstream documented capabilities, not a verified Kiki integration. Preserve Kiki's existing shared history and PC task authority. A bridge must route turns into the existing ledger and return the committed reply rather than create an unrelated character memory store. Test the existing installation separately from Pretorius configuration.

Source: https://github.com/moeru-ai/airi

z-waif is a secondary reference for local voice, VTube Studio reactions and conversation memory. The README recommends Windows and a CUDA GPU with 16 GB or more VRAM, and describes 8 GB VRAM as a minimum across supported GPU brands. Its Oobabooga, RVC and Whisper stack introduces substantial local setup. It is not the first candidate for the older workstation without a hardware and latency test.

Source: https://github.com/SugarcaneDefender/z-waif

Eliza is a broader TypeScript agent runtime and application stack with plugin-based memory, voice, connectors and personal assistant functions. Individual capabilities depend on installed plugins, OS and providers. It is useful for architectural comparison, but adopting another runtime would overlap with the existing Python, SQLite, Jan and shared Site architecture. No migration is proposed at this stage.

Source: https://github.com/elizaOS/eliza

## Hosted work completed

Starting from hosted source commit f2945fe76ea9240c703dd802a744a0022de927b7, the Site now restores the selected conversation, unsent composer draft and chosen task on the same browser. The focused task title stays visible, selecting a radar task selects that task, and pausing no longer resets the focus timer. Stale history requests are cancelled on thread changes.

Source commit: 18ad030ef3d54f31c898e812b1449bcd3c450c98 in the Sites source repository, not this GitHub branch. Saved as Site version 8; publication status must be checked in Sites.

The recovery data is browser presentation state only. It does not store completion status, replace SQLite, provide cross-device work sessions, preserve the timer across reloads, or implement proactive initiation. Existing browser speech playback and dictation remain available; AIRI and continuous voice have not been integrated.

Validation: all 21 hosted automated tests passed, TypeScript checking passed, git diff checking passed, and production build passed. New tests verify interruption recovery and malformed storage handling. Live browser and actual Windows/AIRI acceptance remain unverified.

## Next useful work

Continue the durable work-session contract in WORK_SESSIONS.md with PC-owned objective, next action and pause/resume receipts. Build the browser companion against that contract. Evaluate AIRI as a surface using the existing installed copy when available; measure first reply latency and voice interruption before choosing a permanent voice stack. Muse remains optional background help, with Kiki owning the conversational handoff.
