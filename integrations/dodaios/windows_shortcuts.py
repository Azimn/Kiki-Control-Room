"""Operator-approved Windows shortcuts for Dodaios.

Only named profiles from a local JSON file may be executed. A model cannot
provide executable paths, URLs, arguments, shell syntax or code. No shell=True.
Tool output is a process-launch receipt, NOT proof a window opened correctly.
Do not install this service as a privileged Windows process.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

MAX_PROFILES = 30
MAX_ACTIONS = 5
ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,39}$")
ALLOWED = {"calculator": "calc.exe", "notepad": "notepad.exe", "explorer": "explorer.exe"}
KIND = {"app", "exe", "folder", "url"}


def profile_store(path):
    if not path:
        raise ValueError("No operator shortcut configuration; set KIKI_WINDOWS_SHORTCUTS_FILE")
    config = Path(path).expanduser().resolve(strict=True)
    if not config.is_file() or config.suffix.casefold() != ".json":
        raise ValueError("Shortcut configuration must be an existing JSON file")
    data = json.loads(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"profiles"}:
        raise ValueError("Invalid configuration structure")
    profiles = data["profiles"]
    if not isinstance(profiles, dict) or len(profiles) > MAX_PROFILES:
        raise ValueError("Invalid profile count")
    for key, actions in profiles.items():
        if not isinstance(key, str) or not ID_RE.fullmatch(key):
            raise ValueError("Invalid shortcut identifier")
        if not isinstance(actions, list) or not 1 <= len(actions) <= MAX_ACTIONS:
            raise ValueError("Shortcuts must contain 1 to 5 actions")
        for action in actions:
            if not isinstance(action, dict) or set(action) != {"kind", "target"}:
                raise ValueError("Each action requires only kind and target")
            kind, target = action["kind"], action["target"]
            if kind not in KIND or not isinstance(target, str) or not 1 <= len(target) <= 1024:
                raise ValueError("Invalid action kind or target")
            if any(ord(c) < 32 for c in target):
                raise ValueError("Control characters are forbidden")
            if kind == "app" and target not in ALLOWED:
                raise ValueError("Unknown built-in app")
            if kind in {"exe", "folder"}:
                dest = Path(target)
                if not dest.is_absolute() or ".." in dest.parts or not dest.exists():
                    raise ValueError("Configured paths must be absolute, existing and resolved")
                if kind == "exe" and (dest.suffix.casefold() != ".exe" or not dest.is_file()):
                    raise ValueError("Only an explicit EXE file may be launched")
                if kind == "folder" and not dest.is_dir():
                    raise ValueError("Configured folder is not a directory")
            if kind == "url":
                parts = urlsplit(target)
                if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
                        or parts.fragment or any(c.isspace() for c in target)):
                    raise ValueError("Only configured HTTPS URLs without embedded credentials or fragments")
    return profiles


def describe_profiles(path):
    profiles = profile_store(path)
    return {"kind": "available_operator_shortcuts", "shortcuts": [
        {"id": key, "steps": len(actions), "kinds": [a["kind"] for a in actions]}
        for key, actions in profiles.items()],
        "executed": False}


def _windows_system_exe(name):
    if sys.platform != "win32":
        raise ValueError("Windows shortcut execution requires Windows")
    root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    executable = root / "System32" / ALLOWED[name]
    if not executable.is_file():
        raise ValueError("Built-in Windows application executable not found")
    return executable


def run_profile(path, profile_id, *, launcher=None, opener=None):
    if not isinstance(profile_id, str) or not ID_RE.fullmatch(profile_id):
        raise ValueError("Invalid shortcut ID")
    profiles = profile_store(path)
    if profile_id not in profiles:
        raise ValueError("Shortcut is not operator-approved")
    if sys.platform != "win32" and launcher is None:
        raise ValueError("Shortcuts must be executed on the Windows host")
    launcher = launcher or (lambda argv: subprocess.Popen(argv, close_fds=True))
    opener = opener or os.startfile
    outcomes = []
    for index, action in enumerate(profiles[profile_id]):
        kind, target = action["kind"], action["target"]
        try:
            if kind == "app":
                argv = [str(_windows_system_exe(target))]
                p = launcher(argv)
                evidence = {"process_id": getattr(p, "pid", None), "kind": "process_started"}
            elif kind == "exe":
                p = launcher([str(Path(target).resolve())])
                evidence = {"process_id": getattr(p, "pid", None), "kind": "process_started"}
            elif kind == "folder":
                opener(str(Path(target).resolve()))
                evidence = {"kind": "open_request_submitted"}
            else:
                opener(target)
                evidence = {"kind": "open_request_submitted"}
            outcomes.append({"index": index, "status": "LAUNCH_REQUESTED", "evidence": evidence})
        except (OSError, ValueError) as exc:
            outcomes.append({"index": index, "status": "FAILED", "reason": type(exc).__name__})
            break
    ok = len(outcomes) == len(profiles[profile_id]) and all(x["status"] == "LAUNCH_REQUESTED" for x in outcomes)
    return {"kind": "local_shortcut_launch", "profile_id": profile_id,
            "status": "LAUNCH_REQUESTED" if ok else "PARTIAL_OR_FAILED", "actions": outcomes,
            "externally_verified": False, "shared_history_written": False,
            "note": "The OS accepted launch requests. Check the intended windows and record verified progress in Kiki Control Room."}
