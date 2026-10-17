# Decision record: adopt existing agent runtime for Kiki

Decision date: 2026-10-16. Scope: Kiki as a proactive personal executive-function companion. Status: Candidate selected, implementation profile committed, local installation and shared-history bridge unverified.

## Problem

The current Kiki system can record cross-channel conversation history and run a Windows desktop task worker, and Telegram is connected. The failure is independent initiation and verified follow-through. Prior natural-language messages have promised calendar creation or reminders without actual provider receipts. ChatGPT scheduled checks do not guarantee the ability to send Telegram alerts or control the PC. Rebuilding another custom model loop is counterproductive.

## Evidence reviewed

[Azimn/AliceMod](https://github.com/Azimn/AliceMod) is a fork of [pmbstyle/Alice](https://github.com/pmbstyle/Alice). The current README describes a Windows/macOS/Linux Electron desktop assistant with voice, tool calls, screen context, Gmail and Calendar integration, scheduled tasks, MCP, and a custom script-tool interface. Alice's local-only operation remains experimental. It is the strongest ready-made companion-interface candidate but its own memory, email, and scheduler risk duplication.

[Azimn/rho](https://github.com/Azimn/rho) is a fork of [mikeyobrien/rho](https://github.com/mikeyobrien/rho), a Pi-based autonomous agent with background daemon, heartbeat, agent email, notes and memory, and cross-session continuity. Rho is documented for Linux, macOS, Android, and iPhone via SSH to a host. It is a strong source of scheduler/behavior practices, not a native Windows solution.

[Azimn/ClawPhone](https://github.com/Azimn/ClawPhone) is a practical guide for operating OpenClaw on a cheap Android smartphone under Termux. It demonstrates the isolated mobile appliance pattern, but is not itself a Windows desktop agent.

[Azimn/chatbotAIML](https://github.com/Azimn/chatbotAIML) is a BlobCity DB integration of the Program AB AIML chatbot, with user sessions and editable bot state. It is not an autonomous desktop automation platform.

[Azimn/gomoku](https://github.com/Azimn/gomoku) was accessible as a repository, but its README was not found and no relevant agent-control behavior was verified. Treat as unclassified, not as an assistant runtime.

The upstream [OpenClaw](https://github.com/openclaw/openclaw) documentation currently describes Windows Hub, gateway, model choices including Ollama and LM Studio, Telegram, heartbeats, device nodes and host execution permissions. Official documentation: https://docs.openclaw.ai/platforms/windows , https://docs.openclaw.ai/heartbeat , https://docs.openclaw.ai/agent-workspace , https://docs.openclaw.ai/tools/exec-approvals . These claims are documentation findings, not evidence of successful installation on Jay's laptop.

## Recommendation

Pilot one OpenClaw execution host using the existing Kiki persona and history adapters. OpenClaw handles independent runtime, desktop and browser tool routing, scheduled wakeups, model selection, and messaging. The Kiki Control Room task system and shared ledger remain authoritative. Do not simultaneously launch a separate Alice, Rho, Hermes, Jan bot, and OpenClaw worker all claiming task and message ownership. Jan remains a replaceable model backend where useful; Alice is a later UI experiment; Calibos is a distinct delegated assistant.

Only three small additions are justified before a pilot: transport of attributed Kiki history into the OpenClaw working context, operational action receipt write-back, and provenance-safe message migration. Reuse native OpenClaw heartbeats, native calendar and email integrations where available, and host command tools. No new scheduler, memory database, browser driver, or notification service.

## Safety and low-friction autonomy

Default to autonomous read-only and reversible actions, with clear risk envelopes. Allow self-started research, inbox triage within permitted data boundaries, proposed correspondence, draft creation, project diagnostics, and work-session initiation. Ask for approval on destructive changes, account/permission changes, privileged software installation, public posting, sending to third parties outside existing limited standing authority, spending money, or student data. Approvals are a user-protection mechanism, not a demand that Jay manually schedule every routine action. A safe agent can proactively prepare and request one precise approval rather than stop working.

## Success or rejection

Success means a Kiki-initiated Telegram work session occurs without a ChatGPT prompt, survives a real Windows restart, resumes an interrupted next step, creates one legitimate synthetic appointment without duplication, and verifies a non-destructive PC action by receipt. A mirrored conversation without action is not success. Discard the OpenClaw choice if repeated tool-use tests on affordable local models fail or if the bridge cannot preserve Kiki's canonical state without conflict. Alice is the next primary replacement candidate if Windows presence and voice outweigh deeper automation. Rho on a dedicated Linux host is another fallback if always-on heartbeat reliability is the decisive factor.
