# Reusing existing skill libraries for Kiki and Heather

Status: source review, November 2, 2026. Candidates only; no third-party code installed on Jay's laptop or activated in DODAIOS. This document records practical opportunities, not unverified claims about compatibility or licensing for live account use.

## Selection rule

Use the smallest already-tested tool that can execute a defined, observable operation. A fixed command is better than screenshot-driven improvisation; a native application command is better than starting a second agent; a documented API is better than arbitrary browser clicks. DODAIOS is the default local executor and keeps the user's chosen model independent from computer-use Tool Model availability. Kiki stays the voice and task owner, Heather stays the existing Society team lead. Only send a bounded specialist job to Heather if the direct operation is insufficient.

This branch intentionally does not copy third-party skills into Kiki Control Room. Importing an unreviewed skill is not equivalent to safely adding a tested executable adapter.

## Source-reviewed candidates

| Source | Relevant work | Candidate decision | Why |
| --- | --- | --- | --- |
| DODAIOS built-in app commands and native skills | Voice app control, provider probes, tasks, MCP invocation, native computer use | **Prefer directly** | Already has native command schemas and risk rules; avoids rebuilding core orchestration |
| DODAIOS native Society team lead | Heather delegation and task review | **Prefer directly** | Native team board, assignments, bounded scheduler, restarts; never create another mission database |
| DODAIOS native workflows | Repeatable scripts and schedule | **Use selectively** | Works from desktop/CLI, but documented live version cannot reliably start workflows by name from conversation, and some step types are not wired into app bootstrap |
| Microsoft Power Automate Desktop | Recorded Windows UI procedures with semantic selectors | **Pilot in supervised mode** | Official flow URL accepts pinned workflow ID, can produce runId; app prompts by default, and a start request is not a completed flow |
| aloth/PowerSkills | Windows Outlook COM, Edge CDP, desktop interaction, Work IQ, process actions | **Inspect and selectively adapt** | Real GitHub repo and reusable PowerShell scripts returning structured JSON; includes generic shell execution and mail powers, not appropriate as an unrestricted agent tool |
| ClawHub Windows Notifier by dougzl | Windows desktop reminders/alerts | **Candidate, verify source first** | Could make Kiki's check-ins visible while DODAIOS is out of focus; third-party install can fetch Node dependencies on first run, so review before enabling |
| Hermes bundled weekly-review-planning | Review stalled commitments | **Reuse the procedure, not another task store** | A useful human workflow; Kiki's authoritative commitments remain in Control Room |
| Hermes bundled document-to-action-items | Extract actions and deadlines from documents | **Review for adaptation** | Candidate use in permitted local docs; must not infer unverifiable deadlines or transmit protected student records to unapproved services |
| Hermes bundled computer-use | Specialized fallback for desktop operations | **Optional** | Use only if native DODAIOS computer use cannot perform a bounded task and Hermes has verified Windows accessibility |
| Hermes bundled apple-reminders | Apple Reminders from CLI | **Not suitable for this Windows host** | Requires macOS `remindctl`, not iPhone integration or Windows-compatible access |
| ClawHub/xiaodu/windows-automation-claw | Generic Windows mouse/keyboard and screenshot helpers | **Lower priority** | Blind mouse coordinates provide less reliability than recorded semantic UI elements, native DODAIOS computer use, or fixed app commands |

## Actual resources inspected

- DODAIOS skills: https://github.com/Dodaios/Dodaios/blob/main/docs/product/extend-and-automate/skills.md
- DODAIOS workflows: https://github.com/Dodaios/Dodaios/blob/main/docs/product/extend-and-automate/workflows-and-commands.md
- DODAIOS team leads: https://github.com/Dodaios/Dodaios/blob/main/docs/agent-society/team-leads.md
- DODAIOS portable skills: https://github.com/Dodaios/Dodaios/blob/main/docs/marketplace/portable-skills.md
- ClawHub registry: https://docs.openclaw.ai/clawhub
- Hermes skills catalog: https://hermes-agent.nousresearch.com/docs/reference/skills-catalog
- PowerSkills source: https://github.com/aloth/PowerSkills
- Windows notifier listing: https://clawhub.ai/dougzl/skills/windows-notifier
- Microsoft PAD flow URL: https://learn.microsoft.com/en-us/power-automate/desktop-flows/run-desktop-flows-url-shortcuts
- Microsoft PAD UI selectors: https://learn.microsoft.com/en-us/power-automate/desktop-flows/desktop-automation

## Concrete first user scenarios

**Open Photoshop:** use DODAIOS native app launcher if it already recognizes Photoshop. Otherwise configure one pinned Photoshop .exe in an operator-owned Kiki Windows shortcut and invoke it by ID; confirm the application actually appeared. No extra agent required.

**Begin lecture preparation:** one configured shortcut opens the relevant approved program/folder or a separately approved Power Automate Desktop flow. Kiki reads the current task checkpoint and offers one next step. No fresh planning if the objective is already in the ledger.

**Take care of a small email batch:** a secure Outlook/approved organization connector or a supervised Power Automate Desktop UI flow retrieves one message, a Kiki skill classifies it, a local draft is created, user approves a send, provider readback confirms delivery, and Kiki updates task state. Work involving institutionally restricted student data must stay within authorized systems. Do not install a general Outlook COM skill with elevated permissions as a shortcut for policy review.

**Clean old reminders:** import a bounded batch through Apple Shortcuts later. Compile possible duplicates and stale reminders, ask for human keep/complete decisions, write back through the authorized source, and confirm the synced state. No 'everything older than a year is done' heuristic.

**Desktop check-in:** review Windows Notifier or DODAIOS's existing notification capability, not another autonomous reminder scheduler. The action must respect quiet hours and current work-session state.

## Evaluation

Before importing any outside skill, inspect files and transitive dependencies, test in an isolated sandbox with no account secrets, confirm tool input constraints, distinguish launch/request from completed external actions, then connect via the DODAIOS controlled tool surface. Record provenance and tests. No general PowerShell command tools from untrusted skill packages in the active DODAIOS model tool set.

## Open seams

An authenticated receipt adapter still needs to translate DODAIOS command/shortcut results into the existing Kiki Control Room protocol with stable IDs, origin and verified outcome. PR #15 remains undeployed; do not invent a second task authority to work around it. Real laptop acceptance, tool-model capability, Heather's actual grants, Power Automate licensing, installed programs and notification delivery have not been inspected from this chat.
