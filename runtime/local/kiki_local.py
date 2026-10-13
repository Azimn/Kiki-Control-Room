"""Kiki Control Room local-first runtime.

Python 3.10+ standard library only. SQLite owns operational task state, not
Kiki-Mind canonical autobiography. Local HTTP binds only to loopback.
Telegram is optional and must have exactly one getUpdates consumer.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[2]
WEB = BASE / "web"
MAX_BODY = 8192


class Kiki:
    def __init__(self, db_path: str | Path, token="", chat_id="", tz="America/Chicago"):
        self.db_path = str(db_path)
        self.token = token
        self.chat_id = str(chat_id)
        self.tz = ZoneInfo(tz)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=20)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                done_at TEXT
            );
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT, dedupe TEXT UNIQUE,
                text TEXT NOT NULL, sent_at TEXT, created_at TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def close(self):
        with self.lock:
            self.conn.close()

    def _get(self, key: str, default=None):
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def _set(self, key: str, value):
        self.conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )

    def _queue(self, message: str, dedupe: str | None = None, now=None):
        self.conn.execute(
            "INSERT OR IGNORE INTO outbox(dedupe,text,created_at) VALUES(?,?,?)",
            (dedupe, message, (now or datetime.now(timezone.utc)).isoformat()),
        )

    def state(self):
        with self.lock:
            tasks = [dict(r) for r in self.conn.execute(
                "SELECT id,title,status,created_at,done_at FROM tasks ORDER BY id DESC LIMIT 100"
            ).fetchall()]
            return {
                "tasks": tasks,
                "paused": self._get("paused", False),
                "awaiting": self._get("awaiting", False),
                "checkin_day": self._get("checkin_day"),
                "telegram_enabled": bool(self.token and self.chat_id),
                "timezone": str(self.tz),
            }

    def add(self, title, now=None):
        if not isinstance(title, str) or not (1 <= len(title.strip()) <= 200):
            raise ValueError("Task title must be 1 to 200 characters.")
        with self.lock, self.conn:
            cur = self.conn.execute(
                "INSERT INTO tasks(title,created_at) VALUES(?,?)",
                (title.strip(), (now or datetime.now(timezone.utc)).isoformat()),
            )
            self._set("awaiting", False)
            return cur.lastrowid

    def done(self, task_id, now=None):
        if not isinstance(task_id, int) or isinstance(task_id, bool) or task_id < 1:
            raise ValueError("Valid task ID required.")
        with self.lock, self.conn:
            cur = self.conn.execute(
                "UPDATE tasks SET status='done',done_at=? WHERE id=? AND status='open'",
                ((now or datetime.now(timezone.utc)).isoformat(), task_id),
            )
            if cur.rowcount != 1:
                raise ValueError("Task not found or already completed.")
            self._set("awaiting", False)

    def ack(self):
        with self.lock, self.conn:
            self._set("awaiting", False)
            self._set("next_nudge", None)

    def pause(self, value: bool):
        with self.lock, self.conn:
            self._set("paused", bool(value))
            if value:
                self._set("awaiting", False)
                self._set("next_nudge", None)

    def snooze(self, minutes, now=None):
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 5 or minutes > 240:
            raise ValueError("Snooze must be 5 to 240 minutes.")
        now = now or datetime.now(timezone.utc)
        with self.lock, self.conn:
            self._set("awaiting", True)
            self._set("next_nudge", (now + timedelta(minutes=minutes)).timestamp())

    def tick(self, now=None):
        now = now or datetime.now(timezone.utc)
        local = now.astimezone(self.tz)
        if not (8 <= local.hour < 22):
            return
        with self.lock, self.conn:
            if self._get("paused", False):
                return
            day = local.date().isoformat()
            if 9 <= local.hour < 11 and self._get("checkin_day") != day:
                count = self.conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status='open'"
                ).fetchone()[0]
                self._queue(
                    f"Morning! We've got {count} open task(s). Reply /status to choose one, "
                    "/snooze 15 for more time, or /pause to go quiet.",
                    "checkin:" + day, now,
                )
                self._set("checkin_day", day)
                self._set("awaiting", True)
                self._set("nudges", 0)
                self._set("next_nudge", (now + timedelta(minutes=15)).timestamp())
                return
            due = self._get("next_nudge")
            if not self._get("awaiting", False) or due is None or now.timestamp() < due:
                return
            n = self._get("nudges", 0)
            if n >= 6:
                self._set("awaiting", False)
                return
            self._queue(
                "Checking in. Want to tackle one together? /status, /snooze 15, or /pause."
                if n == 0 else
                "Still here when you're ready. /status, /snooze 30, or /pause.",
                f"nudge:{day}:{n}", now,
            )
            self._set("nudges", n + 1)
            self._set("next_nudge",
                      (now + timedelta(minutes=30 if n == 0 else 60)).timestamp())

    def command(self, text, now=None):
        if not isinstance(text, str) or not text.startswith("/"):
            return
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].split("@", 1)[0].lower()
        rest = parts[1].strip() if len(parts) == 2 else ""
        with self.lock, self.conn:
            if cmd in ("/start", "/help"):
                self.ack()
                reply = "Kiki on deck. /add task, /status, /done ID, /snooze 15, /pause, /resume."
            elif cmd == "/add":
                try:
                    number = self.add(rest, now)
                    reply = f"Task #{number} saved. We can do it together."
                except ValueError as exc:
                    reply = str(exc)
            elif cmd == "/status":
                self.ack()
                rows = self.conn.execute(
                    "SELECT id,title FROM tasks WHERE status='open' ORDER BY id LIMIT 8"
                ).fetchall()
                reply = "On deck:\n" + "\n".join(
                    f"#{r['id']} {r['title']}" for r in rows
                ) if rows else "Queue clear. Nothing waiting right now."
            elif cmd == "/done":
                try:
                    self.done(int(rest), now)
                    reply = f"Task #{rest} done. Want another? /status"
                except (ValueError, TypeError):
                    reply = "Send /done followed by an open task number."
            elif cmd == "/snooze":
                try:
                    minutes = int(rest) if rest else 15
                    self.snooze(minutes, now)
                    reply = f"Okay. I'll check back in {minutes} minutes."
                except ValueError as exc:
                    reply = str(exc)
            elif cmd in ("/pause", "/resume"):
                self.pause(cmd == "/pause")
                reply = "Going quiet until /resume." if cmd == "/pause" else "Back on frequency."
            else:
                reply = "Try /help for the available commands."
            self._queue(reply, now=now)

    def _telegram(self, method, data):
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        req = Request(url, data=json.dumps(data).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=12) as res:
            result = json.load(res)
        if not result.get("ok"):
            raise RuntimeError("Telegram rejected a request.")
        return result["result"]

    def poll(self):
        if not (self.token and self.chat_id):
            return
        with self.lock:
            offset = self._get("telegram_offset", 0)
        updates = self._telegram("getUpdates", {"offset": offset, "limit": 25, "timeout": 0})
        for update in updates:
            ident = int(update["update_id"])
            with self.lock, self.conn:
                if ident < self._get("telegram_offset", 0):
                    continue
                msg = update.get("message", {})
                chat = msg.get("chat", {})
                if str(chat.get("id")) == self.chat_id:
                    self.command(msg.get("text", ""))
                self._set("telegram_offset", ident + 1)

    def deliver(self):
        if not (self.token and self.chat_id):
            return
        with self.lock:
            rows = self.conn.execute(
                "SELECT id,text FROM outbox WHERE sent_at IS NULL ORDER BY id LIMIT 10"
            ).fetchall()
        for row in rows:
            self._telegram("sendMessage", {"chat_id": self.chat_id, "text": row["text"]})
            with self.lock, self.conn:
                self.conn.execute(
                    "UPDATE outbox SET sent_at=? WHERE id=? AND sent_at IS NULL",
                    (datetime.now(timezone.utc).isoformat(), row["id"]),
                )

    def run_background(self, stop: threading.Event):
        while not stop.is_set():
            try:
                self.tick()
                self.poll()
                self.deliver()
            except Exception as exc:
                # Never log tokens or private message contents.
                print(f"Kiki background check delayed ({type(exc).__name__}).", flush=True)
            stop.wait(5)


def make_handler(app: Kiki):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status, body):
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/api/state":
                return self._json(200, app.state())
            assets = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
                "/sw.js": ("sw.js", "text/javascript; charset=utf-8"),
                "/kiki-icon.svg": ("kiki-icon.svg", "image/svg+xml"),
            }
            item = assets.get(self.path)
            if not item:
                return self._json(404, {"error": "Not found"})
            filename, mime = item
            payload = (WEB / filename).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            host = self.headers.get("Origin", "")
            allowed = f"http://{self.headers.get('Host', '')}"
            if host and host != allowed:
                return self._json(403, {"error": "Cross-site requests are blocked"})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self._json(415, {"error": "JSON required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY:
                    return self._json(413, {"error": "Invalid body size"})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("Expected JSON object")
                if self.path == "/api/tasks":
                    app.add(body.get("title"))
                elif self.path == "/api/done":
                    app.done(body.get("id"))
                elif self.path == "/api/snooze":
                    app.snooze(body.get("minutes"))
                elif self.path == "/api/ack":
                    app.ack()
                elif self.path == "/api/pause":
                    app.pause(True)
                elif self.path == "/api/resume":
                    app.pause(False)
                else:
                    return self._json(404, {"error": "Not found"})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)[:180]})
            return self._json(200, app.state())

        def log_message(self, format, *args):
            # Do not write task titles or HTTP request bodies to logs.
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Run Kiki on an always-on local computer.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=str(Path.home() / ".kiki" / "control-room.sqlite3"))
    args = parser.parse_args()
    db = Path(args.db).expanduser()
    db.parent.mkdir(parents=True, exist_ok=True)
    app = Kiki(db, token=os.getenv("KIKI_TELEGRAM_TOKEN", ""),
               chat_id=os.getenv("KIKI_TELEGRAM_CHAT_ID", ""),
               tz=os.getenv("KIKI_TIMEZONE", "America/Chicago"))
    stop = threading.Event()
    thread = threading.Thread(target=app.run_background, args=(stop,), daemon=True)
    thread.start()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app))
        print(f"Kiki is ready: http://localhost:{args.port} (localhost only)")
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        thread.join(timeout=3)
        app.close()


if __name__ == "__main__":
    main()
