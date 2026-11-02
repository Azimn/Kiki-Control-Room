# Kiki deterministic skills for DODAIOS (prototype v0.1)

**Status: code published on an isolated GitHub feature branch, not installed or deployed on Jay's laptop.**

## Why this approach

Kiki is the sole user-facing assistant. DODAIOS is the preferred executor on the laptop. Heather is the existing DODAIOS team lead, not another runtime. DODAIOS specialists, its native computer-use tool, and optional Hermes/OpenClaw integrations should be used only when a deterministic direct action is insufficient.

Keep three kinds of state distinct:

- Shared history in Kiki Control Room records explicitly submitted turns and attributed interaction evidence. It is the cross-interface conversation ledger, not proof of an external action.
- The existing Windows Kiki SQLite task authority stores commitments and task lifecycle; do not create a parallel task queue.
- DODAIOS's native Society board and workflow store track internal execution and delegated jobs. When a job matters to Kiki, reconcile a verified outcome into Control Room through its approved queue/bridge pathway. Do not treat DODAIOS's internal completion flag as an external provider receipt.

## What is implemented in this branch

`integrations/dodaios/kiki_workflows_mcp.py` is a Python 3.10+ standard-library MCP stdio server exposing six small tools with compact input schemas.

| Tool | Purpose | Side effects |
| --- | --- | --- |
| `kiki_get_recipe` | Prescribed start-work, email triage, teaching, reminder cleanup and brain-dump workflows | None |
| `kiki_compile_brain_dump` | Split short dictation into candidate actions | None |
| `kiki_choose_next_action` | Pick one item from a current, explicitly supplied task snapshot | None |
| `kiki_review_handoff` | Normalize agent output and flag missing verification | None |
| `kiki_list_shortcuts` | Enumerate operator-configured named Windows routines | Reads local config only |
| `kiki_run_shortcut` | Launch an operator-approved Windows routine | Launch requests only |

The fourth tool deliberately **does not** mark a specialist report verified. A launched process or dispatched Power Automate Desktop flow URL is not proof that an application window is open or that an external task was completed. The shortcut tool reports `externally_verified: false` and `shared_history_written: false`; actual bridge receipt integration is still needed.

`integrations/dodaios/windows_shortcuts.py` reads operator-approved, named profiles from a **local** JSON file. The model chooses a profile ID. It never supplies paths, arbitrary arguments, shell commands, raw URLs, or click coordinates. A profile has up to five operator-reviewed steps and can open a known Windows app, a configured absolute EXE, an existing folder, or a configured HTTPS URL. A fifth type, `power_automate`, runs an approved Power Automate Desktop flow identified by a canonical UUID. It uses Microsoft's `ms-powerautomate:` URL with a fresh run ID; PAD may prompt for confirmation. Run ID is for correlating future logs and is NOT proof of flow completion. There is no PowerShell/script executor or arbitrary shell fallback. This provides a starting point for predictable multi-application workspaces, including Photoshop once its installed EXE has been explicitly configured. More complex UI flows should use DODAIOS native computer use or a reviewed Power Automate Desktop flow, never unverified mouse coordinates. To register a Power Automate Desktop flow, add an operator-owned profile action such as `{"kind":"power_automate","target":"dfd0c814-2c30-4cd8-849d-a4b2d2f4f33b"}` replacing the example UUID with the real flow ID from the PAD desktop flow properties. This launches the registered URI handler and records a run ID, not a result. Consult Microsoft's flow URL and licensing/confirmation requirements before use.

All three `skills/*/SKILL.md` files are intentional **drafts**. The connected DODAIOS instance must import the folders, validate their requirements, and promote them after human review. This branch does not change its runtime persona or agent roster.

## Configure on the actual Windows DODAIOS laptop

From the repository root after checking out this feature branch:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.kiki" | Out-Null
Copy-Item ".\integrations\dodaios\windows-shortcuts.example.json" "$env:USERPROFILE\.kiki\windows-shortcuts.json"
```

Edit that private JSON file as needed. For Photoshop add a profile with a validated, absolute installed `.exe` path, and never place secrets or a university login in this file.

Then open **DODAIOS > MCPs > mcp.json** and add a disabled local stdio connection. Replace the two marked paths with the actual Windows location and keep the connection disabled until the file, tool list and permissions have been reviewed.

```json
{
  "mcpServers": {
    "kiki-workflows": {
      "command": "python",
      "args": [
        "C:\\YOUR_PATH\\Kiki-Control-Room\\integrations\\dodaios\\kiki_workflows_mcp.py"
      ],
      "env": {
        "KIKI_WINDOWS_SHORTCUTS_FILE": "C:\\Users\\YOUR_USER\\.kiki\\windows-shortcuts.json"
      },
      "enabled": false
    }
  }
}
```

This is a **single entry**, to be merged into your existing mcp.json without deleting other servers. The JSON example is not designed to be used unchanged.

Use `dodaios mcps check kiki-workflows` to probe the server. If it is healthy, enable it through DODAIOS and run a read-only tool test first. Start with `kiki_get_recipe({"recipe":"start_work"})` or `kiki_list_shortcuts({})`. Then explicitly request a harmless named shortcut and observe the application opening. Its response means the OS accepted a launch request, not that a screen or document was verified.

Import the three skill folders separately, for example:

```powershell
dodaios skills import ".\skills\kiki-intake-and-followthrough"
dodaios skills import ".\skills\heather-coordinate-execution"
dodaios skills import ".\skills\kiki-small-task-helpers"
```

Review the imported **Draft** records and use the supported DODAIOS promotion mechanism only after tool matching and operator approval. Heather must actually hold the DODAIOS team-lead role to use `society_team_assign`, `society_team_board` and `society_team_report`. Do not assign that capability by prompt alone.

## Choice of automation surface

For a simple voice command, prefer an existing DODAIOS app command or the allowlisted shortcut. For a multi-application starting ritual, prefer a named shortcut. For a predictable screen interaction, prefer Windows UI Automation or Power Automate Desktop's semantic UI selectors over blind mouse coordinates. For an uncertain screen state, use DODAIOS computer use and its actual compatible image-capable Tool Model. For creative or complex multi-step work, have Heather assign bounded specialist work through the native DODAIOS Society board. Choose an external Hermes or OpenClaw worker only if a proven installed capability is missing from DODAIOS. Do not make this a default four-agent delegation chain.

The following are **not** implemented by this slice: phone Apple Shortcuts, Apple Reminders sync, DODAIOS startup wiring, a hosted task writer, an external-provider verifier, automatic ingestion of skill action receipts into shared history, Photoshop path discovery, a generic Power Automate Desktop flow launcher, or an adapter that reconciles DODAIOS's internal Society task completion with the Kiki Control Room queue. Avoid claiming them completed.

## Next integration gate for Codex

1. Confirm the deployed DODAIOS version and the actual local model used for chat versus the separate image-capable Tool Model. The tool router must be tested with the real selected model, not assumed from model identity.
2. Probe the existing DODAIOS native command and MCP registry. Make the six tools visible and callable through a local typed/chat turn.
3. Configure and test one operator-approved Windows shortcut. Inspect the OS state to verify the correct app actually opened.
4. Reconcile the resulting tool observation into Kiki Control Room through a **new authorized receipt adapter or existing approved queue route**. Preserve distinct `requested`, `OS launch accepted`, and `verified external state` status. Use stable event IDs and origin attribution; retry safely.
5. Prove the same result can be retrieved from Jan and ChatGPT Kiki after the bridge catches up, including restart and duplicate-delivery tests. Only then claim the full cross-surface workflow is complete.

## Tests

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

The new tests include MCP stdio handshake, JSON tool schemas, deterministic candidate selection, historical task suppression, bounded inputs, refusal of arbitrary tool names, shortcut allowlisting, no arbitrary shell/script execution, mocked multi-step launch and fail-stop behavior. They are tested in CI on Windows and Linux. A CI pass is not a live laptop acceptance or bridge sync proof.

## Existing sources

DODAIOS: `docs/product/extend-and-automate/skills.md`, `mcp-connections.md`, `workflows-and-commands.md`, `computer-use.md`, `docs/agent-society/team-leads.md`.

Kiki Control Room: `docs/SHARED_QUEUE_PROTOCOL.md`, `docs/WORK_SESSIONS.md`, `docs/SHARED_CONTEXT.md`. In particular PR #15 retains Windows SQLite as authoritative and explicitly prohibits inferring a completed task from conversational text.

Official Power Automate Desktop documentation: https://learn.microsoft.com/en-us/power-automate/desktop-flows/run-desktop-flows-url-shortcuts
