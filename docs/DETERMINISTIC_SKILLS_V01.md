# Kiki deterministic skills v0.1

**Status:** Locally testable portable implementation. **Not deployed** to the laptop, Jan desktop, OpenClaw, Hermes, or the hosted bridge. Work-session checkpoints are local SQLite, not synced. Does not modify the existing `tasks` table or the shared queue protocol.

## Why this structure

The local model selects a vetted intent and supplies small bounded arguments. A small Python standard-library dispatcher executes a specific validated procedure and emits JSON. Non-action planning never claims an external effect. This is intentionally less flexible than giving a small model unrestricted shell access.

The existing `~/.kiki/control-room.sqlite3` stays authoritative. `kiki_skill_sessions` and `kiki_skill_ops` are additive tables in that database, **not another task store**. Stable request IDs make state-changing operations idempotent, including retries after crashes. These tables store work-session checkpoints only and are not mirrored to other Kiki surfaces yet. `COMPLETED_USER_REPORTED` is explicitly not the queue's provider-verified `VERIFIED`.

## Install and quick tests on Windows

Copy this package into a reviewable folder inside the local Kiki checkout. Do not overwrite existing modules. Confirm the actual Kiki DB path and ensure an existing `tasks` table. From the package root:

```powershell
py -3 -m unittest discover -s tests -p "test_*.py" -v
py -3 runtime/local/kiki_skills.py catalog
'{"skill":"plan","recipe":"inbox_triage","depth":2}' | py -3 runtime/local/kiki_skills.py run
'{"skill":"brain_dump","text":"I need to update lecture notes; remember to buy detergent"}' | py -3 runtime/local/kiki_skills.py run
$env:KIKI_DB_PATH = "$HOME\.kiki\control-room.sqlite3"
'{"skill":"session_start","request_id":"example-session-001","objective":"Prepare next class","next_action":"Find the current course notes"}' | py -3 runtime/local/kiki_skills.py run
```

For `session_start`, retain its returned `session_id` and supply it to `session_pause`, `session_read`, and `session_resume`. Request IDs must be stable for retries and unique for genuinely distinct writes. No scheduler, network, API key, Telegram poller, or new listener is started.

OpenClaw can load `skills/kiki-workflows/SKILL.md` from its workspace skills root. Do not silently deploy or activate it while Codex is modifying the Windows agent. The model's tool runner still needs explicit permission for the fixed dispatcher command. The skill file alone does not expose a new executable tool.

## Next integration gates

The existing queue branch (`feature/shared-capability-queue`, PR #15) contains authoritative tasks, claims, and readback receipts. **Do not** map work-session completion directly to queue `VERIFIED`: the latter requires adapter-produced evidence. First test local OpenClaw skill selection with a small Ollama model; then tie user-confirmed work-session results to the existing work-session sync contract; then add separately permissioned Windows and browser action adapters. Refuse unknown action names and parameters rather than inventing new skills.

Synthetic acceptance scenario: start a task on one local session, pause with a precise next action, restart the Python process, resume, and confirm the exact step survives. Attempt a duplicate request ID, malformed JSON, unknown skill, nonexistent database, model-authored dangerous instruction, and completion without human confirmation. None should execute a shell command, create a second database, or produce an external success receipt.
