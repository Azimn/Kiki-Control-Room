# DODAIOS and Kiki: platform audit, risk register, and preflight gate

**Prepared:** 2026-11-05. **Scope:** public DODAIOS docs/source/releases/issues and the existing Kiki-Control-Room development branches, plus a prior owner-provided laptop repair receipt. **Status:** source-verified audit with synthetic CI proposals; **no new deployment or remote inspection of the owner's Windows laptop**.

## Executive finding

DODAIOS is a credible orchestration shell for Kiki, but a capable frontier model can hide weak tool discovery, incomplete workflow wiring, and uncertain receipt propagation. The correct local-first strategy is to use a language model for short intent extraction and conversation, and deterministic, narrowly permissioned operations for repeatable work. Do not replace the owner's working ChatGPT Chrome voice+text co-working session until equivalent behavior is demonstrated in DODAIOS.

**The next step is a source-level, model-free contract test, followed by real host probes.** Do not reinstall, update, merge draft queue work, reassign Telegram, or replace agents as a prerequisite.

## Provenance and release skew

The last supplied real Windows repair report identified an editable DODAIOS v4.0.1 checkout at commit `c2aeac0c642024b9207cf340cde19cd4b288d6c2`, branch `feature/kiki-browser-reliability`, with local patches and private Society, SQLite, and voice-related state. This is a historical observation, not a fresh November 5 inventory. The latest **published** upstream release checked November 5 is **v4.1.2**, published October 27, with security changes to signed update manifests. Upstream `main` documentation and code are not automatically part of v4.1.2.

Sources: https://github.com/Dodaios/Dodaios/releases/tag/v4.1.2 and https://github.com/Dodaios/Dodaios/blob/main/docs/product/start-here/install-dodaios.md .

The user reports that a custom voice backend previously worked after Codex modified the application, then vanished after an update. Therefore preserve the *actual edited code*, its parent tag/commit, an exportable patch, editable configuration, custom voices/scripts and required dependencies separately. The data directory and active configuration must be recorded by the running app; do not infer their locations from defaults or from the version number alone.

**No-go:** automatic update of the production installation before a source diff, private-data backup with recovery test, and an isolated side-by-side staging environment.

## Agent surfaces and authoritative roles

Do not confuse (a) DODAIOS Society agents, (b) isolated Dodaios-Agent missions, (c) Codex/Claude/OpenCode coding CLI panes, (d) native app commands, (e) saved workflows, and (f) MCP tool processes. These have different execution, permission, state, and result semantics.

The previously configured **Kiki Clique** consists of Kiki as user-facing coordinator, Heather as Society team lead, Tiffany for research, Stacey for reporting/documents, and Amber for verification/quality. These names and roles come from the owner's prior setup; this audit did not fetch live DODAIOS roster rows, individual instructions, provider seats, or grants. Preserve them exactly.

Society team lead mechanics: `ASSIGN` enters a bounded queue; scheduler claims; members perform limited work; results wake Heather; `society_team_report` completes the team goal. One goal at a time per team. A provider-ready chat does not prove a member can read or write a shared file. A mission worker is not an interchangeable Society team member; isolated mission workers do not gain uncontrolled direct desktop actions or recursive agency.

Source: https://github.com/Dodaios/Dodaios/blob/main/docs/agent-society/team-leads.md and https://github.com/Dodaios/Dodaios/blob/main/docs/product/extend-and-automate/dodaios-agents.md .

The owner's prior Kiki Clique repair report says a **recovered** path really created a 162-byte document and Amber independently read it, and the report was returned to Kiki. It also says the subsequent **fresh unattended** replay remained **PARTIAL/HOLD**, not a successful end-to-end release. The historical defect involved replay that substituted synthesized `[used tool ...]` markers for genuine tool-result content. A local repair corrected that behavior, but no repeatable operational pass was established. This is a high-priority regression fixture.

## Model seats, subscription, and budget boundaries

DODAIOS separates Brain, Tool Model for computer vision, speech input/output and Realtime voice, and agent/mission model seats. A model that chats successfully may not produce structured tool calls or interpret screenshots. Compare *actual* tool selection and schema compliance, not parameter count or benchmark score.

OpenAI officially includes Codex CLI/IDE access with supported ChatGPT subscriptions, subject to plan usage limits. This is **not** a general free API key or unlimited ChatGPT inference in arbitrary third-party applications. DODAIOS's Codex CLI agent seat, DODAIOS's Brain integration, and experimental GPT-Live subscription voice are separate products and should be tested independently. Test any subscription route without a metered API key to eliminate accidental paid fallback. Never insert cached login tokens into prompts, repositories or test fixtures.

Sources: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan ; https://learn.chatgpt.com/docs/auth?surface=cli ; https://github.com/Dodaios/Dodaios/blob/main/docs/agent-runtimes.md ; https://github.com/Dodaios/Dodaios/blob/main/docs/product/personalize-and-connect/providers-and-api-keys.md .

Preflight model test: each chosen local model receives the same ten synthetic instructions, spanning known command invocation, tool parameter fill, unsupported-tool refusal, completed-task suppression, one-sentence summary, and correct handoff. Record 10/10 reliability separately for intent interpretation, actual tool call, valid schema, and evidence claim; repeat after process restart. Then run the same set on subscription-backed seat. Any tool that is not actually observed in DODAIOS Run Inspector counts as not called. Use low-temperature deterministic prompts and compact advertised tool sets before spending time on bigger models.

## Voice architecture

Voice recognition, conversational Brain, spoken output, dictation, and live-realtime transport are independent selections. The user benefited from simultaneous voice and text, continuous company during non-preferred work, and automatic active-session bookkeeping. A standalone TTS modification does not solve interruptions or session state.

Prefer the established Kiki voice in a **versioned external provider/adapter** when an extension point is supported. Otherwise maintain a minimal pinned upstream source patch with regression tests; do not directly edit untracked installed files. Local Pipeline voice (STT + Brain + TTS) and any replacement local speech engine must remain operational with no subscription. GPT-Live is an optional comparison, not a required dependency.

Current upstream issue reports include Windows 11 GPT-Live start and `insertBefore` frontend failures on v4.1.2 (issue #1178, November 4). Earlier related issue #828 remains open. Do not diagnose this as an owner's custom voice regression without a reproducible local error trace.

Sources: https://github.com/Dodaios/Dodaios/issues/1178 ; https://github.com/Dodaios/Dodaios/issues/828 ; https://github.com/Dodaios/Dodaios/blob/main/docs/product/personalize-and-connect/languages-and-voices.md ; https://github.com/Dodaios/Dodaios/blob/main/docs/local-live-voice-rebuild.md .

## Browser and MCP boundaries

DODAIOS managed-browser profiles are distinct from connected personal Chrome profiles. The private Chrome extension uses owned, visible tabs and a local pairing code, not arbitrary existing tabs. Its connector does not promise arbitrary JavaScript, file upload/download, cross-frame automation, or unrelated tab takeover. Browser actions are subject to profile locking and visible-session handoff. Separately, Computer Use is screenshot+accessibility interaction with a configured image-capable Tool Model. Playwright MCP is another tool connection, not proof that DODAIOS acquired control of an existing browser session.

Sources: https://github.com/Dodaios/Dodaios/blob/main/docs/browser-profiles.md ; https://github.com/Dodaios/Dodaios/blob/main/docs/browser-use.md ; https://github.com/Dodaios/Dodaios/blob/main/docs/product/extend-and-automate/computer-use.md .

The MCP registry saves server definitions before connection; a successful handshake and `tools/list` are required. The normal URL-only MCP config shape is documented as unreliable in the current registry. An existing connection must be disabled/restarted for configuration changes. Import from Claude Desktop supports only Windows command-based servers. A successful MCP connection alone does not prove that a Brain or Society agent has capability grants. **Important safety warning:** custom MCP tools default to **monitor** risk tier, which normally records and executes without asking; the platform does not infer destructive risk from a tool's prose description. Only add approved read-only or deliberately scoped tools; require specific approval for sends, deletion, or publication. A configured server can be paused after three failures for about a minute, so error traces should distinguish a failed call from a temporary server circuit break.

Source: https://github.com/Dodaios/Dodaios/blob/main/docs/product/extend-and-automate/mcp-connections.md .

## Skills, workflows, and routines are not interchangeable

A **skill** is a bounded instruction/procedure, not an executable or permission grant. A **native app command** is a defined endpoint with validated arguments. A **workflow** is a saved sequence that the workflow runner executes (from the app, CLI, REST, or schedule), but chat and voice do not reliably launch workflows by name because the Command Registry does not expose that operation. The documented workflow `tool call` and `harness dispatch` steps lack normal app bootstrap wiring and fail when reached. Workflows do not currently branch, retry or parallelize steps. A `speak` step may report completion even when no TTS audio exists. A `Telegram message` step is available only with configured credentials. **Routines** operate on the scheduled agent conversation and its selected model seat, and require the app to be running.

This makes the PR #18 six-tool `kiki-workflows` MCP approach preferable to assuming that every YAML workflow can call every runtime operation. Actual Windows actions should be named, operator-reviewed, argument-bounded scripts; the model chooses a tool/profile ID only. Preserve DODAIOS's existing scheduler rather than creating another.

Sources: https://github.com/Dodaios/Dodaios/blob/main/docs/product/extend-and-automate/workflows-and-commands.md ; https://github.com/Dodaios/Dodaios/blob/main/docs/routines.md ; https://github.com/Dodaios/Dodaios/blob/main/docs/product/extend-and-automate/skills.md .

## State and the single source of truth

Kiki-Mind is the identity/autobiographical record. Kiki Control Room Windows SQLite is the operational task authority. Existing attributed shared history is conversational evidence; an LLM's sentence or assistant RESULT is not an external-provider receipt. DODAIOS Society has its own execution board and native routines, not a replacement Kiki task authority. Draft Kiki PR #15 (shared queue) and PR #18 (deterministic tools) are not verified deployed. Existing issue #8 requires initiate/converse/resume with persistent state.

Synthetic workflow gate: open a fake task, select exactly one next action, record a user-reported completion distinct from provider verification, suppress old reminders, fail a specialist handoff without independent file bytes, restart an isolated work-session store, restore the same objective, and verify no duplicate events. A Playwright failure must leave the active session pending and allow manual continuation.

Kiki Control Room sources: https://github.com/Azimn/Kiki-Control-Room/pull/15 ; https://github.com/Azimn/Kiki-Control-Room/pull/18 ; https://github.com/Azimn/Kiki-Control-Room/issues/8 .

## Health and diagnostic sequence (read-only first)

The live host is the authority for its actual version and settings. Check `GET http://127.0.0.1:47821/api/health` for server reachability and `warming`. This is NOT a readiness proof for model, audio, MCP or browser. Use DODAIOS's built-in **Run Inspector**, API Keys & Providers **Test**, MCP **check/list**, Society team board, browser profile status and logs to test each layer separately. The open API description may be discovered at `/api/openapi.json`; protected endpoints need the Control key, and the advertised OpenAPI schema does not fully declare Bearer authorization. Do not expose or embed the Control key in source, screenshots, logs or browser extensions.

Follow the actual DODAIOS configuration precedence: defaults < active `jarvis.toml` < named profile < environment overrides (the `DODAIOS_*` variant wins when both names are set). `JARVIS_DATA_DIR` determines state storage; pointing it to a new empty directory can make the roster appear to vanish without deleting old files. Record the *effective* active values, not just raw TOML.

Sources: https://github.com/Dodaios/Dodaios/blob/main/docs/product/reference/control-api-reference.md ; https://github.com/Dodaios/Dodaios/blob/main/docs/product/reference/configuration-reference.md ; https://github.com/Dodaios/Dodaios/blob/main/docs/product/privacy-safety-and-support/troubleshooting.md .

## Update and reproducibility policy

For every Kiki-dependent change, maintain: upstream version/tag and exact SHA; baseline clean source; a separate Kiki integration branch; local patch export; edited file manifest; private effective-config export with secrets redacted; package dependency lock; standalone adapter installation instructions; independent data-directory backup; and synthetic acceptance tests. Do not replace the user's current virtual environment or disable existing voice without a confirmed restore path.

After an upstream update, test the untouched upstream staging instance, apply only the narrowly versioned extension/patch on a *separate staging checkout*, run the same contracts and real smoke tests, then adopt the update only if source/voice/agent/task behavior has not regressed. Prefer clean upstream APIs, native plugin entry points, stdio MCP, external tool scripts, config profiles and user-data paths over modifying the installed app package.

Upstream security concern: issue #1181 reports a v4.1.2 Windows signed installer verifier rejecting valid older Rekor proofs due to a 24-hour freshness rule. Do not bypass verification merely to force an install. Source: https://github.com/Dodaios/Dodaios/issues/1181 .

## Preflight status register

| Gate | Current evidence | Status |
| --- | --- | --- |
| DODAIOS published release | v4.1.2 confirmed from release API | VERIFIED PUBLIC |
| Installed laptop version/config today | Prior repair receipt said 4.0.1 | UNKNOWN CURRENT |
| Agent roster | User-configured Kiki/Heather/Tiffany/Stacey/Amber from prior records | PRESERVE / READ BACK |
| Custom voice survival | User-reported update regression | OPEN |
| Native DODAIOS MCP | Current docs + new PR #18 six-tool implementation | SOURCE ONLY |
| Existing GitHub CI coverage | Original Kiki relay workflow ran only Node relay tests | GAP: NEW PYTHON MATRIX PROPOSED |
| User voice/text co-working | Demonstrated in ChatGPT Chrome workflow | WORKING REFERENCE, NOT LOCAL PROOF |
| Society transfer | Prior recovered run had real bytes; fresh unattended replay pending | HOLD |
| Subscription seat without API charges | Codex plan login officially available; DODAIOS coupling must be probed | HOST TEST REQUIRED |
| Independent browser/Playwright | Interfaces documented; live success not observed here | HOST TEST REQUIRED |
| Always-on desktop Telegram | Model-free sender exists, courier transfer not deployed | TRACK ISSUE #19 |
| End-to-end pause/restart/bridge readback | No current independent receipt | HOLD |

## GitHub simulation branch

This audit is stacked on `feature/kiki-deterministic-skills-v01` as **`audit/dodaios-preflight-20261105`**. The added `.github/workflows/dodaios-preflight.yml` runs the *actual existing Kiki integration code* with Python unittest on Linux and Windows. Existing tests cover the six-tool MCP stdio handshake, safe input schemas, deterministic selection, and mocked Windows shortcuts. The added `tests/test_dodaios_preflight.py` simulates repeated voice/text equivalent tool requests, user completion suppression, no invented next task, unverifiable specialist success, and refusal of unauthorized action. Neither test suite uses the actual DODAIOS application or a paid model; do not call it an end-to-end test.

If this GitHub workflow is green, the **source-level** gate may pass. The next gate is a separately isolated real Windows installation probe with existing agents and secrets preserved. Do not merge the test branch solely because model-free tests pass.

## External developer communications

Official project website: https://dodaios.ai ; official repo: https://github.com/Dodaios/Dodaios ; developer X link: https://x.com/dodaios (linked by the official website). The X profile returned HTTP 403 during this audit, so **no X post content was verified**. Active GitHub bugs, release notes, and documented source are stronger evidence than promotional videos or unsupported social claims. Direct engagement with the developer should attach a minimal synthetic reproducible test and exact version/commit, not the user's private bot tokens, student information, or full system prompts.

## Immediate implementation order

**First:** inspect current Windows version, active config precedence, custom voice diff, actual roster/permissions, selected provider seats, and dedicated Tool Model without changing them. **Second:** require green isolated GitHub synthetic CI on the stacked branch. **Third:** test the six safe MCP tools in real DODAIOS, and reproduce one verified Stacey-to-Amber artifact handoff, accounting for replay. **Fourth:** build/verify one Kiki active-session checkpoint with dictated and typed results converging. **Fifth:** add one read-only browser skill, then one approved Windows action, and only later the model-free desktop Telegram courier. Each step must retain receipts, a rollback plan, and a measured human-effort improvement.

**Hard no-go:** no accidental API spend; no reliance on private undocumented subscription voice protocol; no second task authority; no second Telegram `getUpdates` process; no FERPA data in external/shared test fixtures; no automatic upgrade over a hand-patched installation; no claim of production completion from GitHub CI alone.
