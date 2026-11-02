# DODAIOS Kiki deterministic skills v0.1

Status: review candidate, not deployed on the Windows laptop.
Target: DODAIOS's existing Kiki and Heather Society team, not a second assistant or orchestration runtime.
Base: Kiki-Control-Room branch feature/shared-capability-queue.

## What this delivers

integrations/dodaios/kiki_workflows_mcp.py is a Python standard-library **read-only** MCP stdio process.
It exposes four small, precisely bounded operations:
- kiki_get_recipe: five reviewed procedures (start work, email triage, teaching preparation, reminder cleanup, brain-dump review).
- kiki_compile_brain_dump: converts short dictated text into candidate actions for review. No task is persisted.
- kiki_choose_next_action: proposes one eligible task from a caller-provided current snapshot, suppressing completed, declined, snoozed, deferred and blocked tasks.
- kiki_review_handoff: normalizes a specialist outcome; does not promote self-reported results to verified execution.

The three native SKILL.md files are **drafts for review**, not active:
- skills/kiki-intake-and-followthrough
- skills/heather-coordinate-execution
- skills/kiki-small-task-helpers

No model, network, browser, file write, desktop control, agent spawn, or queue operation is performed by the MCP process. It is not an Apple Reminders integration, nor an authenticated Goblin Tools API.

## Correct authority boundaries

Kiki-Mind remains identity/autobiographical memory authority. Existing Kiki Control Room desktop SQLite remains the commitment authority; the shared queue bridge mediates approved tasks and independent readback. DODAIOS is the execution surface, with Heather as the existing team lead and Tiffany, Stacey, Amber as role-appropriate specialists. Society assignments are not a replacement for Control Room commitments. Agent RESULT events do not prove external state changes.

DODAIOS's team leader already uses society_team_board, society_team_assign and society_team_report; leave its scheduler, board, approval engine and delegation depth alone. The skills describe usage of these real native tools but do not grant them. The CLI-only, browser, native desktop or optional OpenClaw/Hermes execution capabilities remain separate from these deterministic planning microtools.

## Installation on the laptop, after review

Clone/check out this branch into a stable, operator-controlled directory on the laptop. Use the installed Python 3.10+ executable. No packages need installing for the MCP process.

In DODAIOS > MCPs > mcp.json, add a **disabled** server to the existing mcpServers object; substitute the real stable Windows path and Python path:

```json
{
  "mcpServers": {
    "kiki-workflows": {
      "command": "C:\\Path\\To\\Python\\python.exe",
      "args": ["-u", "C:\\Path\\To\\Kiki-Control-Room\\integrations\\dodaios\\kiki_workflows_mcp.py"],
      "enabled": false
    }
  }
}
```

Do not overwrite other MCP definitions. Save and run:

```powershell
dodaios mcps check kiki-workflows
```

The handshake should expose four tools. Review permission scope and enable in the DODAIOS UI only after check passes. Then use:

```powershell
dodaios mcps enable kiki-workflows
dodaios mcps list
```

Import individual skill folders using the native loader:

```powershell
dodaios skills import "C:\Path\To\Kiki-Control-Room\skills\kiki-intake-and-followthrough"
dodaios skills import "C:\Path\To\Kiki-Control-Room\skills\heather-coordinate-execution"
dodaios skills import "C:\Path\To\Kiki-Control-Room\skills\kiki-small-task-helpers"
```

Because these are explicitly draft-state model-authored instructions, a trusted operator must inspect and promote them through DODAIOS's documented CLI:
```powershell
python -m dodaios.skills.cli --promote kiki-intake-and-followthrough
```

Repeat for the other two only after inspecting each. Grant relevant MCP capabilities to the actual Kiki and Heather agents using DODAIOS's existing agent capabilities. Confirm that Heather is already the team's lead. There is no need to re-create the agents.

## Acceptance, in order

1. Run Python tests via `python -m unittest discover -s tests -p "test_*.py" -v`. The new test file exercises MCP stdio initialization, tool discovery, safe parameter validation, deterministic selection, and outcome classification.
2. With the real MCP connected, ask Gemma directly for the reviewed recipe named `start_work`. Verify a **real MCP tool call** in DODAIOS's run inspector, not just a plausible text answer. Try the same on ORNITH only as a separate comparison.
3. Dictate a non-sensitive two-action brain dump. Verify the two structured candidates and zero persisted tasks; manual confirmation remains necessary.
4. Send one bounded synthetic goal from Kiki to Heather. Heather should use the native Society team board, assign at most one appropriate specialist, and return an attributable result through the existing scheduler. No new planner/scheduler may appear.
5. Test one native desktop action (for example, calculator 25 × 4 = 100) separately. It needs a healthy image-capable Tool Model and direct screen verification; the text model's ability to invoke the MCP tools does not establish computer-use readiness.
6. Then connect any additional trusted operators via the Shared Queue's existing signed claim/heartbeat/finish/readback contract. Do not claim Control Room task completion from an MCP recipe response.

Current status: source committed, automated GitHub test run to be checked. No local DODAIOS install, real model invocation, Heather assignment, screenshot, deployment, or bridge connection is verified by the code commit.

## Rollback

Disable the `kiki-workflows` MCP entry and disable the imported skills. This leaves the local SQLite authority, Kiki identity, existing DODAIOS team and historical receipts untouched. No destructive migration is needed.
