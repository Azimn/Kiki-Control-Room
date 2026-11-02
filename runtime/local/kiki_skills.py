"""Kiki deterministic skill dispatcher. Python 3.10+, standard library only.

Local trusted launcher only. No model text is a shell command, receipt, or authority.
Uses the EXISTING Kiki SQLite file for optional work-session checkpoints; never
creates a replacement database or claims bridge synchronization.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

MAX_INPUT = 12_000
MAX_TEXT = 1000
MAX_STEPS = 15

# Reviewed recipes. The operator can edit these via source-controlled changes,
# not by including new runnable instructions inside an untrusted request.
RECIPES = {
    "inbox_triage": (
        "Open the approved mailbox and select one message for review",
        "Determine whether the message needs action, reference, or no action",
        "For an actionable message, prepare a draft or choose one small next action",
        "Review any draft before sending; sending needs its own approval and receipt",
        "Record the next unhandled message so the session can resume",
    ),
    "lecture_prep": (
        "Identify the class meeting and the material actually needed",
        "Open the relevant local teaching materials or approved course system",
        "Choose the smallest section to complete first",
        "Review or produce that section without changing unrelated coursework",
        "Confirm what is complete and leave the next step for the next session",
    ),
    "announcement_draft": (
        "Identify the audience, topic, and any confirmed dates",
        "Draft a concise announcement with the known facts only",
        "Review dates, links, and course-specific requirements",
        "Obtain approval before publishing or sending",
        "Verify the published result separately if publication is authorized",
    ),
    "reminder_cleanup": (
        "Read a bounded batch of reminders from an authorized source",
        "Group potential duplicates and reminders with unclear relevance",
        "Offer a small review batch instead of deleting old items automatically",
        "Record explicit keep, defer, complete, or remove decisions",
        "Verify the external reminders state after authorized updates",
    ),
    "start_work": (
        "Identify one current commitment, not an entire backlog",
        "Choose a step that can be started immediately",
        "Bring forward the needed document, page, or context when available",
        "Work on that one step with an optional check-in",
        "Record progress or pause without claiming unverified completion",
    ),
}

CATALOG = {
    "catalog": "List reviewed deterministic skills and templates",
    "plan": "Return vetted steps for one named workflow template",
    "brain_dump": "Convert a short dictation into candidate tasks; no persistence",
    "review_steps": "Validate proposed steps from a model; no execution",
    "session_start": "Checkpoint one co-working session in the existing SQLite DB",
    "session_pause": "Pause and record the next exact action",
    "session_resume": "Read a checkpoint and resume without repeating old work",
    "session_complete": "Record explicit human-reported completion, never VERIFIED",
    "session_read": "Read checkpoint from the existing SQLite DB",
}


def require_str(value, label, maximum=MAX_TEXT):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise ValueError(f"{label} must be nonempty text of at most {maximum} characters")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError(f"{label} contains control characters")
    return value.strip()


def require_request(data):
    if not isinstance(data, dict) or len(json.dumps(data, ensure_ascii=False)) > MAX_INPUT:
        raise ValueError("Request must be a bounded JSON object")
    name = require_str(data.get("skill"), "skill", 40)
    if name not in CATALOG:
        raise ValueError("Unknown skill; use catalog for allowed skills")
    allowed = {
        "catalog": {"skill"},
        "plan": {"skill", "recipe", "context", "depth"},
        "brain_dump": {"skill", "text"},
        "review_steps": {"skill", "goal", "steps"},
        "session_start": {"skill", "objective", "next_action", "request_id"},
        "session_pause": {"skill", "session_id", "next_action", "request_id"},
        "session_resume": {"skill", "session_id", "request_id"},
        "session_complete": {"skill", "session_id", "user_confirmed", "request_id"},
        "session_read": {"skill", "session_id"},
    }[name]
    if set(data) - allowed:
        raise ValueError("Unsupported parameter for selected skill")
    return name


def plan(data):
    name = require_str(data.get("recipe"), "recipe", 50)
    if name not in RECIPES:
        raise ValueError("No reviewed recipe for that goal; use review_steps or ask for detail")
    depth = data.get("depth", 2)
    if type(depth) is not int or not 1 <= depth <= 3:
        raise ValueError("depth must be 1, 2 or 3")
    context = data.get("context", "")
    if context:
        require_str(context, "context", 300)
    all_steps = list(RECIPES[name])
    # Depth changes batching, not the safety steps or the requirements for approval.
    batches = ([all_steps] if depth == 1 else
               [all_steps[:2], all_steps[2:]] if depth == 2 else
               [[step] for step in all_steps])
    return {"status": "PLANNED", "recipe": name, "context": context,
            "steps": all_steps, "batches": batches,
            "next_action": all_steps[0], "external_effect": False,
            "note": "Suggested work only; no external action was performed"}


# This is deliberately a candidate compiler, not a magical NLP solution. It
# extracts bounded action candidates; a person or local model may refine them.
ACTION_PREFIX = re.compile(r"^(?:and\s+)?(?:i\s+(?:need|have|want)\s+to\s+|remember\s+to\s+|don't\s+forget\s+to\s+|please\s+|todo\s*:\s*|task\s*:\s*)", re.I)

def brain_dump(data):
    raw = require_str(data.get("text"), "text", 4000)
    parts = re.split(r"[\n;]+|(?<=[.!?])\s+(?=[A-Z])", raw)
    candidates, seen = [], set()
    was_truncated = False
    for item in parts:
        item = ACTION_PREFIX.sub("", item.strip().strip("-• ")).strip().strip(".!? ")
        if not item or len(item) > 400:
            continue
        key = re.sub(r"\s+", " ", item).casefold()
        if key not in seen:
            seen.add(key)
            candidates.append({"title": item, "status": "CANDIDATE", "needs_review": True})
        if len(candidates) >= 12:
            was_truncated = len(parts) > len(seen)
            break
    if not candidates:
        raise ValueError("No actionable candidates found")
    return {"status": "CANDIDATES_ONLY", "tasks": candidates,
            "truncated": was_truncated, "external_effect": False,
            "note": "No reminders or commitments created; review before importing"}


def review_steps(data):
    require_str(data.get("goal"), "goal", 300)
    steps = data.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError("steps must be a bounded list")
    cleaned = [require_str(step, "step", 250) for step in steps]
    if len(set(s.casefold() for s in cleaned)) != len(cleaned):
        raise ValueError("Duplicate steps")
    # Validation of shape is not permission to execute. Do not interpret the
    # content as a shell command or privileged skill, even when it says so.
    return {"status": "REVIEW_REQUIRED", "goal": data["goal"],
            "steps": cleaned, "next_action": cleaned[0], "external_effect": False,
            "note": "Model-authored text was validated, not approved or executed"}


def _existing_db(path):
    if not path:
        raise ValueError("KIKI_DB_PATH required for session skills")
    dbpath = Path(path).expanduser().resolve()
    if not dbpath.is_file():
        raise ValueError("Existing Kiki SQLite database required; none will be created")
    db = sqlite3.connect(dbpath.as_uri() + "?mode=rw", uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone():
        db.close()
        raise ValueError("Not a Kiki task-authority database")
    db.execute("""CREATE TABLE IF NOT EXISTS kiki_skill_sessions (
        session_id TEXT PRIMARY KEY, objective TEXT NOT NULL, next_action TEXT NOT NULL,
        status TEXT NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS kiki_skill_ops (
        request_id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL)""")
    db.commit()
    return db


def _session(data, db_path):
    name = data["skill"]
    if name in {"session_start", "session_pause", "session_resume", "session_complete"}:
        request_id = require_str(data.get("request_id"), "request_id", 128)
    else:
        request_id = None
    if name == "session_start":
        require_str(data.get("objective"), "objective", 400)
        require_str(data.get("next_action"), "next_action", 400)
    else:
        session_id = require_str(data.get("session_id"), "session_id", 80)
        if not re.fullmatch(r"session-[0-9a-f-]{36}", session_id):
            raise ValueError("Invalid session ID")
        if name == "session_pause":
            require_str(data.get("next_action"), "next_action", 400)
        if name == "session_complete" and data.get("user_confirmed") is not True:
            raise ValueError("Explicit user confirmation required for completion")
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    db = _existing_db(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        if request_id:
            previous = db.execute("SELECT digest,result FROM kiki_skill_ops WHERE request_id=?", (request_id,)).fetchone()
            if previous:
                if previous["digest"] != digest:
                    raise ValueError("Conflicting request_id reuse")
                db.commit()
                return json.loads(previous["result"])
        if name == "session_start":
            sid = "session-" + str(uuid.uuid4())
            db.execute("INSERT INTO kiki_skill_sessions VALUES(?,?,?,?,?,?)",
                       (sid, data["objective"].strip(), data["next_action"].strip(), "ACTIVE", 1, datetime.now(timezone.utc).isoformat()))
        else:
            sid = data["session_id"]
            row = db.execute("SELECT * FROM kiki_skill_sessions WHERE session_id=?", (sid,)).fetchone()
            if not row:
                raise ValueError("Unknown session")
            previous_status = row["status"]
            if name == "session_pause" and previous_status != "ACTIVE":
                raise ValueError("Only active sessions can be paused")
            if name == "session_resume" and previous_status != "PAUSED":
                raise ValueError("Only paused sessions can be resumed")
            if name == "session_complete" and previous_status not in ("ACTIVE", "PAUSED"):
                raise ValueError("Only open sessions can be completed")
            if name in ("session_pause", "session_resume", "session_complete"):
                status = {"session_pause": "PAUSED", "session_resume": "ACTIVE",
                          "session_complete": "COMPLETED_USER_REPORTED"}[name]
                next_action = data["next_action"].strip() if name == "session_pause" else row["next_action"]
                db.execute("UPDATE kiki_skill_sessions SET status=?,next_action=?,revision=revision+1,updated_at=? WHERE session_id=?",
                           (status, next_action, datetime.now(timezone.utc).isoformat(), sid))
        current = dict(db.execute("SELECT * FROM kiki_skill_sessions WHERE session_id=?", (sid,)).fetchone())
        result = {"status": current["status"], "session": current, "readback": "SQLITE",
                  "shared_sync": False, "verified_external_effect": False}
        if request_id:
            db.execute("INSERT INTO kiki_skill_ops VALUES(?,?,?)", (request_id, digest, json.dumps(result)))
        db.commit()
        return result
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def dispatch(data, *, db_path=None):
    name = require_request(data)
    if name == "catalog":
        return {"status": "AVAILABLE", "skills": CATALOG, "recipes": list(RECIPES)}
    if name == "plan":
        return plan(data)
    if name == "brain_dump":
        return brain_dump(data)
    if name == "review_steps":
        return review_steps(data)
    return _session(data, db_path)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"catalog", "run"}:
        print("Usage: python kiki_skills.py catalog|run", file=sys.stderr)
        return 2
    try:
        if sys.argv[1] == "catalog":
            result = dispatch({"skill": "catalog"})
        else:
            raw = sys.stdin.read(MAX_INPUT + 1)
            if len(raw) > MAX_INPUT:
                raise ValueError("Input exceeds 12 KB")
            result = dispatch(json.loads(raw), db_path=os.environ.get("KIKI_DB_PATH"))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, TypeError, json.JSONDecodeError, sqlite3.Error) as exc:
        # Do not echo the submitted private text or filesystem paths.
        print(json.dumps({"status": "ERROR", "error": str(exc)[:150]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
