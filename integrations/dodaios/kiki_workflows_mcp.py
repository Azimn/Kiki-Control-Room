"""Read-only deterministic workflow tools for Kiki inside Dodaios.

Python 3.10+, standard library only. MCP stdio JSON-RPC with one JSON message
per line. No network, shell, file writes, database, credentials, or agent spawn.
The existing Dodaios and Kiki Control Room runtimes remain the authorities.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone

VERSION = "0.1.0"
MAX_MESSAGE = 16384
SKIP = {"done", "completed", "verified", "cancelled", "canceled", "declined"}
RECIPES = {
    "start_work": [
        "Select one eligible current commitment, not the whole backlog",
        "Identify the smallest immediately achievable next action",
        "Open the relevant material through an authorized Dodaios tool if available",
        "Work on that action, then explicitly record progress or a pause",
        "Verify external completion separately before claiming success",
    ],
    "email_triage": [
        "Choose one message from an authorized mailbox or a synthetic example",
        "Classify as action, reference, waiting, or no action",
        "Prepare a reply draft or the next action without sending",
        "Ask for approval before sending, deleting, archiving, or moving messages",
        "Read back the mailbox state after any authorized change",
    ],
    "teaching_prep": [
        "Identify the class and the next meeting using confirmed information",
        "Locate an approved course resource without exposing student records",
        "Choose one bounded portion of the material to prepare",
        "Prepare and check the result before any publication",
        "Leave a precise next step and report only confirmed changes",
    ],
    "reminder_cleanup": [
        "Retrieve a small batch from an explicitly connected reminder source",
        "Identify apparent duplicates and uncertain historical entries",
        "Show a small review batch; never auto-complete based on age",
        "Apply only explicitly authorized changes in the connected source",
        "Read back the updated reminder state before reporting completion",
    ],
    "brain_dump_review": [
        "Capture the unstructured dictation as written",
        "Run kiki_compile_brain_dump to obtain candidate actions",
        "Review candidates to correct context, deadlines, and duplicates",
        "Select the first practical action and assign an owner",
        "Create persistent tasks only through the existing Control Room authority",
    ],
}
TOOLS = [
    {"name": "kiki_get_recipe",
     "description": "Return an exact reviewed workflow for getting started, handling emails, lesson preparation, reminder cleanup, or brain-dump review. This only plans; it performs no actions.",
     "inputSchema": {"type": "object", "properties": {"recipe": {"type": "string", "enum": list(RECIPES)}}, "required": ["recipe"], "additionalProperties": False}},
    {"name": "kiki_compile_brain_dump",
     "description": "Extract up to twelve candidate actions from dictated text deterministically, without creating tasks or reminders.",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string", "maxLength": 4000}}, "required": ["text"], "additionalProperties": False}},
    {"name": "kiki_choose_next_action",
     "description": "Choose one eligible next action from supplied task snapshot. Ignore completed, declined and snoozed tasks. No database access or writes.",
     "inputSchema": {"type": "object", "properties": {"tasks": {"type": "array", "maxItems": 50, "items": {"type": "object"}}}, "required": ["tasks"], "additionalProperties": False}},
    {"name": "kiki_list_shortcuts",
     "description": "List operator-approved Windows shortcut profiles. No launches or task changes.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "kiki_run_shortcut",
     "description": "Launch one operator-approved Windows shortcut by ID. OS launch acknowledgement is not visible-window or external-task verification. Never supply shell commands.",
     "inputSchema": {"type": "object", "properties": {"profile_id": {"type": "string", "maxLength": 40}},
                     "required": ["profile_id"], "additionalProperties": False}},
    {"name": "kiki_review_handoff",
     "description": "Normalize a specialist's task result. Never treats an agent message as proof of external execution, and never updates task state.",
     "inputSchema": {"type": "object", "properties": {
         "task_id": {"type": "string", "maxLength": 120},
         "outcome": {"type": "string", "enum": ["drafted", "blocked", "failed", "user_reported_complete", "external_action_claimed"]},
         "summary": {"type": "string", "maxLength": 800},
         "next_action": {"type": "string", "maxLength": 400}},
         "required": ["task_id", "outcome", "summary"], "additionalProperties": False}},
]


def bounded(value, name, length):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= length:
        raise ValueError(f"{name} must be text between 1 and {length} characters")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError(f"{name} contains unsupported control characters")
    return value.strip()


def require_fields(args, required, allowed):
    if not isinstance(args, dict) or not required.issubset(args) or set(args) - allowed:
        raise ValueError("Invalid tool arguments")


def get_recipe(args):
    require_fields(args, {"recipe"}, {"recipe"})
    name = bounded(args["recipe"], "recipe", 60)
    if name not in RECIPES:
        raise ValueError("Unknown reviewed recipe")
    return {"kind": "reviewed_workflow", "recipe": name,
            "steps": RECIPES[name], "next_action": RECIPES[name][0],
            "performed_external_action": False}


def compile_brain_dump(args):
    require_fields(args, {"text"}, {"text"})
    raw = bounded(args["text"], "text", 4000)
    # Conservative segmentation. It deliberately does not pretend to fully
    # understand conversational intention or assign inferred deadlines.
    chunks = re.split(r"[\r\n;]+|(?<=[.!?])\s+(?=[A-Z])", raw)
    out, seen = [], set()
    for chunk in chunks:
        clean = re.sub(r"^(?:[-*•]\s*|(?:and\s+)?(?:i\s+(?:need|have|want)\s+to\s+|remember\s+to\s+|don't\s+forget\s+to\s+|please\s+))",
                       "", chunk.strip(), flags=re.I).strip().strip(".!? ")
        key = " ".join(clean.casefold().split())
        if key and key not in seen and len(clean) <= 300:
            seen.add(key)
            out.append({"text": clean, "status": "candidate", "needs_review": True})
        if len(out) == 12:
            break
    return {"kind": "task_candidates", "candidates": out,
            "needs_review": True, "created_task_count": 0,
            "performed_external_action": False}


def _deadline(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.utcoffset() is not None else None
    except (ValueError, OverflowError):
        return None


def choose_next_action(args):
    require_fields(args, {"tasks"}, {"tasks"})
    tasks = args["tasks"]
    if not isinstance(tasks, list) or len(tasks) > 50:
        raise ValueError("tasks must be a list with at most 50 entries")
    now = datetime.now(timezone.utc)
    choices = []
    for index, row in enumerate(tasks):
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "")).strip().lower()
        if status in SKIP or row.get("completed") is True:
            continue
        if status in {"snoozed", "deferred", "paused", "blocked", "awaiting_approval"}:
            continue
        snoozed = _deadline(row.get("snoozed_until"))
        if snoozed and snoozed > now:
            continue
        try:
            ident = bounded(row.get("id"), "id", 120)
            title = bounded(row.get("title", row.get("intent")), "title", 300)
            next_action = bounded(row.get("next_action") or title, "next_action", 300)
        except ValueError:
            continue
        priority = row.get("priority", 0)
        if type(priority) is not int or not -10 <= priority <= 10:
            priority = 0
        due = _deadline(row.get("deadline", row.get("due_at")))
        urgent = 1 if due and due <= now else 0
        choices.append(((-urgent, -priority, due.timestamp() if due else float("inf"), index),
                        {"id": ident, "title": title, "next_action": next_action,
                         "due_at": due.isoformat() if due else None}))
    choices.sort(key=lambda pair: pair[0])
    return {"kind": "proposed_next_action", "candidate": choices[0][1] if choices else None,
            "eligible_count": len(choices), "snapshot_only": True,
            "task_state_changed": False}


def review_handoff(args):
    require_fields(args, {"task_id", "outcome", "summary"},
                   {"task_id", "outcome", "summary", "next_action"})
    ident = bounded(args["task_id"], "task_id", 120)
    summary = bounded(args["summary"], "summary", 800)
    outcome = args["outcome"]
    if outcome not in {"drafted", "blocked", "failed", "user_reported_complete", "external_action_claimed"}:
        raise ValueError("Invalid outcome")
    next_action = args.get("next_action")
    if next_action is not None:
        next_action = bounded(next_action, "next_action", 400)
    return {"kind": "unverified_handoff", "task_id": ident, "outcome": outcome,
            "summary": summary, "next_action": next_action,
            "requires_authoritative_receipt": outcome == "external_action_claimed",
            "provider_verified": False, "task_state_changed": False}


def _shortcut_module():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).with_name("windows_shortcuts.py")
    spec = importlib.util.spec_from_file_location("kiki_windows_shortcuts", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def list_shortcuts(args):
    require_fields(args, set(), set())
    import os
    return _shortcut_module().describe_profiles(os.environ.get("KIKI_WINDOWS_SHORTCUTS_FILE"))


def run_shortcut(args):
    require_fields(args, {"profile_id"}, {"profile_id"})
    import os
    return _shortcut_module().run_profile(os.environ.get("KIKI_WINDOWS_SHORTCUTS_FILE"), args["profile_id"])


HANDLERS = {
    "kiki_get_recipe": get_recipe,
    "kiki_list_shortcuts": list_shortcuts,
    "kiki_run_shortcut": run_shortcut,
    "kiki_compile_brain_dump": compile_brain_dump,
    "kiki_choose_next_action": choose_next_action,
    "kiki_review_handoff": review_handoff,
}


def reply(msg):
    ident = msg.get("id")
    method = msg.get("method", "")
    if ident is None:
        return None   # notifications/initialized and cancellation notifications
    if method == "initialize":
        supplied = (msg.get("params") or {}).get("protocolVersion")
        version = supplied if supplied in {"2024-11-05", "2025-03-26", "2025-06-18"} else "2025-06-18"
        result = {"protocolVersion": version, "capabilities": {"tools": {}},
                  "serverInfo": {"name": "kiki-workflows", "version": VERSION}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = msg.get("params") or {}
        tool = params.get("name")
        try:
            if tool not in HANDLERS:
                raise ValueError("Unknown tool")
            payload = params.get("arguments") or {}
            value = HANDLERS[tool](payload)
            result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
                      "isError": False}
        except (ValueError, TypeError) as err:
            result = {"content": [{"type": "text", "text": str(err)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": ident,
                "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def main():
    # MCP stdio: each line contains exactly one JSON-RPC message. Errors must
    # never appear as accidental stdout text that corrupts the transport.
    for line in sys.stdin.buffer:
        if len(line) > MAX_MESSAGE:
            continue
        try:
            msg = json.loads(line)
            if not isinstance(msg, dict):
                continue
            result = reply(msg)
            if result is not None:
                sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except (ValueError, TypeError, KeyError):
            continue


if __name__ == "__main__":
    main()
