"""Kiki Control Room local-first runtime.

Python 3.10+ standard library only. SQLite owns operational task state, not
Kiki-Mind canonical autobiography. Local HTTP binds only to loopback.
Telegram is optional and must have exactly one getUpdates consumer.
"""
from __future__ import annotations

import argparse
import json
import hashlib
import hmac
import os
import re
import uuid
from pathlib import Path
import sqlite3
import threading
import sys
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[2]
WEB = BASE / "web"
MAX_BODY = 8192
EMAIL_CHECKIN_HOUR = 11
EMAIL_CHECKIN_MINUTE = 15


class CalendarBridge:
    """Outbound-only, signed requests to the owner's Apps Script calendar bridge."""
    def __init__(self, url, secret):
        if not re.fullmatch(r"https://script\.google\.com/macros/s/[\w-]+/exec", url):
            raise ValueError("Use the deployed Google Apps Script /exec URL.")
        if len(secret) < 32:
            raise ValueError("Calendar bridge key must be at least 32 characters.")
        self.url, self.secret = url, secret

    def request(self, action, booking=None):
        payload = json.dumps({"action": action, "timestamp": int(time.time()),
                              "booking": booking}, separators=(",", ":"))
        signature = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        req = Request(self.url, data=json.dumps({"payload": payload, "signature": signature}).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(req, timeout=30) as response:
                result = json.load(response)
            if not isinstance(result, dict) or result.get("code") not in (
                    "booked", "conflict", "ready", "unavailable", "invalid", "unauthorized"):
                raise ValueError("Invalid bridge response")
            return result
        except Exception:
            # No URLs, secrets, calendar contents, or remote exception text in logs/replies.
            return {"code": "unavailable"}


class Kiki:
    def __init__(self, db_path: str | Path, token="", chat_id="", tz="America/Chicago", calendar=None):
        self.db_path = str(db_path)
        self.token = token
        self.chat_id = str(chat_id)
        self.tz = ZoneInfo(tz)
        self.calendar = calendar
        self.agent = None
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
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, start TEXT NOT NULL,
                duration INTEGER NOT NULL, offered REAL NOT NULL,
                status TEXT NOT NULL, event_id TEXT
            );
            CREATE TABLE IF NOT EXISTS email_queue (
                thread_id TEXT PRIMARY KEY, revision TEXT NOT NULL,
                sender TEXT NOT NULL, subject TEXT NOT NULL,
                group_name TEXT NOT NULL, status TEXT NOT NULL,
                received_at TEXT NOT NULL, snoozed_until REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS email_drafts (
                id TEXT PRIMARY KEY, thread_id TEXT NOT NULL,
                revision TEXT NOT NULL, recipient TEXT NOT NULL,
                body TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL
            );
        """)
        self.conn.commit()
        columns = {row[1] for row in self.conn.execute('PRAGMA table_info(tasks)')}
        with self.conn:
            for name in ('sync_id', 'snoozed_until'):
                if name not in columns:
                    self.conn.execute(f'ALTER TABLE tasks ADD COLUMN {name} TEXT')
            for row in self.conn.execute('SELECT id FROM tasks WHERE sync_id IS NULL').fetchall():
                self.conn.execute('UPDATE tasks SET sync_id=? WHERE id=?', ('task-' + str(uuid.uuid4()), row['id']))
            self.conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS task_sync_id ON tasks(sync_id)')
            self.conn.execute('CREATE TABLE IF NOT EXISTS desktop_receipts(request_id TEXT PRIMARY KEY,content_hash TEXT NOT NULL,status TEXT NOT NULL,acknowledged INTEGER NOT NULL DEFAULT 0)')
        sys.path.insert(0, str(Path(__file__).parent))
        from shared_queue import SharedQueue
        self.queue = SharedQueue(self)

    def close(self):
        with self.lock:
            self.conn.close()

    def ingest_email(self, thread_id, revision, sender, subject, group, received_at):
        """Adapter boundary: explicit candidates only; unread is not needs-reply.

        No mailbox adapter is configured yet. A new inbound revision reopens a
        resolved thread; re-reading the same revision preserves its disposition.
        Bodies and attachments are deliberately not stored in this queue.
        """
        values = (thread_id, revision, sender, subject, received_at)
        if any(not isinstance(v, str) or not v.strip() or len(v) > 1000 for v in values):
            raise ValueError('Valid email metadata required.')
        if group not in ('student', 'colleague', 'review'):
            raise ValueError('Unknown email group.')
        stamp = datetime.fromisoformat(received_at)
        if stamp.tzinfo is None:
            raise ValueError('Email timestamp needs a timezone.')
        with self.lock, self.conn:
            self.conn.execute('''INSERT INTO email_queue
                (thread_id,revision,sender,subject,group_name,status,received_at)
                VALUES(?,?,?,?,?,'needs_reply',?)
                ON CONFLICT(thread_id) DO UPDATE SET
                  sender=excluded.sender, subject=excluded.subject,
                  group_name=excluded.group_name, received_at=excluded.received_at,
                  status=CASE WHEN email_queue.revision=excluded.revision
                    THEN email_queue.status ELSE 'needs_reply' END,
                  snoozed_until=CASE WHEN email_queue.revision=excluded.revision
                    THEN email_queue.snoozed_until ELSE 0 END,
                  revision=excluded.revision''',
                (thread_id, revision, sender, subject, group, received_at))

    def next_email(self, now=None):
        now = now or datetime.now(timezone.utc)
        with self.lock:
            row = self.conn.execute('''SELECT * FROM email_queue
                WHERE status='needs_reply' AND snoozed_until<=?
                ORDER BY CASE group_name WHEN 'student' THEN 0
                  WHEN 'colleague' THEN 1 ELSE 2 END,
                  julianday(received_at), thread_id LIMIT 1''', (now.timestamp(),)).fetchone()
            return dict(row) if row else None

    def save_email_draft(self, draft_id, thread_id, revision, recipient, body, now=None):
        """Local draft only. There is deliberately no email transport/send action.

        Bind drafts to an inbound revision so later incoming mail cannot silently
        reuse an outdated reply. Stable IDs make retries safe across restarts.
        Recipient must come from verified mailbox data, not model inference.
        """
        if not isinstance(draft_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', draft_id):
            raise ValueError('Stable draft identity required.')
        if not isinstance(recipient, str) or len(recipient) > 254 or not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', recipient):
            raise ValueError('Verified recipient address required.')
        if not isinstance(body, str) or not 1 <= len(body.strip()) <= 20000:
            raise ValueError('Draft text must be 1 to 20000 characters.')
        now = now or datetime.now(timezone.utc)
        with self.lock, self.conn:
            thread = self.conn.execute('SELECT revision FROM email_queue WHERE thread_id=?', (thread_id,)).fetchone()
            if not thread or thread['revision'] != revision:
                raise ValueError('Conversation changed; review the latest message before drafting.')
            prior = self.conn.execute('SELECT * FROM email_drafts WHERE id=?', (draft_id,)).fetchone()
            if prior:
                if any(prior[k] != v for k, v in dict(thread_id=thread_id, revision=revision, recipient=recipient, body=body).items()):
                    raise ValueError('Draft retry differs from original; use a new draft identity.')
                return draft_id
            self.conn.execute('''INSERT INTO email_drafts
                (id,thread_id,revision,recipient,body,created_at) VALUES(?,?,?,?,?,?)''',
                (draft_id, thread_id, revision, recipient, body, now.isoformat()))
            return draft_id

    def email_draft(self, draft_id):
        with self.lock:
            row = self.conn.execute('''SELECT d.*, q.revision AS current_revision
                FROM email_drafts d JOIN email_queue q ON q.thread_id=d.thread_id
                WHERE d.id=?''', (draft_id,)).fetchone()
            if not row:
                raise ValueError('Draft not found.')
            result = dict(row)
            result['stale'] = result.pop('current_revision') != result['revision']
            result['send_enabled'] = False
            return result

    def email_checkin(self, now):
        """Opt-in late-morning prompt; no student details sent to Telegram."""
        if not self._get('email_routine_enabled', False):
            return
        local = now.astimezone(self.tz)
        if local.weekday() >= 5:
            return
        item = self.next_email(now)
        day = local.date().isoformat()
        start_minute = EMAIL_CHECKIN_HOUR * 60 + EMAIL_CHECKIN_MINUTE
        minute = local.hour * 60 + local.minute
        if item and start_minute <= minute < start_minute + 60 and self._get('email_checkin_day') != day:
            self._queue('Email time. I have a conversation ready for us. '
                        'Reply /email to bring it forward, or /email-later for an hour.',
                        'email-checkin:' + day, now)
            self._set('email_checkin_day', day)
            self._set('email_followups', 0)
            self._set('email_next_prompt', (now + timedelta(minutes=30)).timestamp())
        elif (item and self._get('email_checkin_day') == day
              and self._get('email_next_prompt', 0)
              and now.timestamp() >= self._get('email_next_prompt')
              and self._get('email_followups', 0) < 2):
            attempt = self._get('email_followups', 0) + 1
            self._queue('Our email conversation is still waiting. We can do one together. '
                        '/email or /email-later. /email-off pauses these check-ins.',
                        f'email-followup:{day}:{attempt}', now)
            self._set('email_followups', attempt)
            self._set('email_next_prompt', (now + timedelta(hours=1)).timestamp())

    def email_command(self, cmd, now):
        item = self.next_email(now)
        if cmd == '/email-on':
            self._set('email_routine_enabled', True)
            return 'Weekday email check-in enabled for 11:15 a.m. Chicago time (one-hour catch-up window). Mailbox scanning is not connected yet.'
        if cmd == '/email-off':
            self._set('email_routine_enabled', False)
            return 'Email check-ins paused. Your queue is preserved.'
        if not item:
            return 'No due email candidates in the local queue. This does not mean your inbox is clear; mailbox scanning is not connected yet.'
        if cmd == '/email-later':
            self.conn.execute('UPDATE email_queue SET snoozed_until=? WHERE thread_id=?',
                              ((now + timedelta(hours=1)).timestamp(), item['thread_id']))
            self._set('email_next_prompt', (now + timedelta(hours=1)).timestamp())
            return 'Deferred for one hour; the conversation remains unresolved.'
        self._set('email_next_prompt', 0)
        return ('One conversation is ready. Mailbox reading and spoken replies are not connected yet. '
                'The queue retains it until a verified outcome is recorded.')

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
                "calendar_enabled": self.calendar is not None,
                "email_mode": "local_drafts_only",
                "email_send_enabled": False,
                "desktop_sync_status": self._get('desktop_sync_status', 'not_configured'),
                "desktop_sync_at": self._get('desktop_sync_at'),
                "model_enabled": self.agent is not None,
                "model_status": self._get('model_status','not_configured'),
                "shared_context_seq": self._get('agent_shared_context',{'seq':0})['seq'],
                "conversations": [dict(r) for r in self.conn.execute('SELECT id,source,text,status,reply FROM agent_jobs ORDER BY created_at DESC LIMIT 20').fetchall()] if self.agent else [],
            }

    def calendar_command(self, cmd, rest, now, request_id=None):
        if cmd == "/cancel":
            pending = self._get("pending_booking")
            if pending:
                self.conn.execute("UPDATE bookings SET status='canceled' WHERE id=? AND status='proposed'", (pending,))
                self._set("pending_booking", None)
            return "Calendar proposal canceled. This does not delete an event that may already have been created."
        if not self.calendar:
            return "Calendar scheduling is not connected yet."
        if cmd == "/calendar":
            result = self.calendar.request("health")
            return ("Calendar scheduling connected. Use /book YYYY-MM-DD HH:MM MIN title. Times are "
                    + str(self.tz) + ".") if result["code"] == "ready" else "Calendar access needs attention. Nothing will be booked."
        if cmd in ("/book", "/block"):
            match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) (\d{1,3}) (.+)", rest)
            if not match:
                return "Use /book YYYY-MM-DD HH:MM MIN title (5-240 minutes)."
            try:
                naive = datetime.strptime(match[1] + " " + match[2], "%Y-%m-%d %H:%M")
                candidates = {naive.replace(tzinfo=self.tz, fold=fold).astimezone(timezone.utc)
                              for fold in (0, 1)
                              if naive.replace(tzinfo=self.tz, fold=fold).astimezone(timezone.utc).astimezone(self.tz).replace(tzinfo=None) == naive}
                if len(candidates) != 1:
                    return "That clock time is ambiguous or skipped by daylight saving. Choose another time."
                start = candidates.pop()
                duration, title = int(match[3]), match[4].strip()
                if start <= now or not 5 <= duration <= 240 or not 1 <= len(title) <= 120:
                    raise ValueError()
            except ValueError:
                return "Choose a future valid time, 5-240 minutes, and a title up to 120 characters."
            # Persist the request identity before any remote write, even across lost responses.
            ident = uuid.uuid5(uuid.NAMESPACE_URL, str(request_id)).hex if request_id is not None else uuid.uuid4().hex
            self.conn.execute("INSERT OR IGNORE INTO bookings VALUES(?,?,?,?,?,'proposed',NULL)",
                              (ident, title, start.isoformat(), duration, now.timestamp()))
            self._set("pending_booking", ident)
            self.conn.commit()
            if cmd == "/block":
                return f"Proposed: {title} at {match[1]} {match[2]} ({duration} min, {self.tz}). /confirm to book or /cancel."
        else:
            ident = self._get("pending_booking")
        row = self.conn.execute("SELECT * FROM bookings WHERE id=?", (ident,)).fetchone()
        if row and row["status"] == "booked":
            self._set("pending_booking", None)
            return f"Booked: {row['title']}. This request was already completed."
        if not row or row["status"] != "proposed":
            return "No current calendar proposal. Use /book to schedule directly."
        if now.timestamp() - row["offered"] > 1800 or datetime.fromisoformat(row["start"]) <= now:
            self.conn.execute("UPDATE bookings SET status='expired' WHERE id=?", (ident,))
            self._set("pending_booking", None)
            return "That proposal expired. Choose a new time."
        booking = {key: row[key] for key in ("id", "title", "start", "duration", "offered")}
        result = self.calendar.request("book", booking)
        if result["code"] == "booked":
            self.conn.execute("UPDATE bookings SET status='booked',event_id=? WHERE id=?", (result.get("event_id"), ident))
            self._set("pending_booking", None)
            local = datetime.fromisoformat(row["start"]).astimezone(self.tz)
            self.ack()
            return f"Booked: {row['title']} on {local:%Y-%m-%d at %H:%M} ({row['duration']} min, {self.tz})."
        if result["code"] == "conflict":
            return "That time overlaps a calendar commitment. Nothing was created. Choose another time."
        if result['code']=='invalid':
            self.conn.execute("UPDATE bookings SET status='invalid' WHERE id=?",(ident,))
            self._set('pending_booking',None)
            return 'This calendar request is invalid or its request ID belongs to different event details. Nothing new was booked. Send a new complete /book request.'
        return "Calendar booking could not be verified. Send /confirm to safely retry this request; /cancel stops retries."

    def add(self, title, now=None):
        if not isinstance(title, str) or not (1 <= len(title.strip()) <= 200):
            raise ValueError("Task title must be 1 to 200 characters.")
        with self.lock, self.conn:
            cur = self.conn.execute(
                "INSERT INTO tasks(title,created_at,sync_id) VALUES(?,?,?)",
                (title.strip(), (now or datetime.now(timezone.utc)).isoformat(), 'task-' + str(uuid.uuid4())),
            )
            self._set("awaiting", False)
            return cur.lastrowid

    def done(self, task_id, now=None):
        if not isinstance(task_id, int) or isinstance(task_id, bool) or task_id < 1:
            raise ValueError("Valid task ID required.")
        with self.lock, self.conn:
            cur = self.conn.execute(
                "UPDATE tasks SET status='done',done_at=? WHERE id=? AND status='open' AND queue_json IS NULL",
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
            self.email_checkin(now)
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

    def command(self, text, now=None, request_id=None):
        if not isinstance(text, str) or not text.startswith("/"):
            return
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].split("@", 1)[0].lower()
        rest = parts[1].strip() if len(parts) == 2 else ""
        with self.lock, self.conn:
            now = now or datetime.now(timezone.utc)
            if cmd in ("/start", "/help"):
                self.ack()
                reply = "Kiki on deck. /add task, /status, /done ID, /snooze 15, /pause, /resume. /book YYYY-MM-DD HH:MM MIN title schedules directly. /block previews; /confirm books; /cancel discards. /calendar checks access."
            elif cmd in ('/email', '/email-later', '/email-on', '/email-off'):
                reply = self.email_command(cmd, now)
            elif cmd in ("/book", "/block", "/confirm", "/cancel", "/calendar"):
                reply = self.calendar_command(cmd, rest, now, request_id)
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
                    text=msg.get('text','')
                    if text.startswith('/'):
                        self.command(text, request_id=f"telegram:{self.chat_id}:{ident}")
                    elif self.agent and text.strip():
                        self.agent.enqueue(f'telegram:{self.chat_id}:{ident}',text,'telegram')
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
            ui_url = os.getenv('KIKI_SITE_URL', '')
            if self.path == '/' and re.fullmatch(r'https://[a-z0-9.-]+\.chatgpt\.site', ui_url):
                self.send_response(302)
                self.send_header('Location', ui_url)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                return
            if self.path == "/api/state":
                return self._json(200, app.state())
            assets = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/offline": ("index.html", "text/html; charset=utf-8"),
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
                if self.path == '/api/shared-queue':
                    credentials = json.loads(os.getenv('KIKI_QUEUE_CREDENTIALS', '{}'))
                    principal = app.queue.authenticate(body, credentials)
                    return self._json(200, app.queue.dispatch(principal, body['command']))
                if self.path == "/api/tasks":
                    app.add(body.get("title"))
                elif self.path == '/api/chat':
                    if not app.agent:
                        return self._json(503,{'error':'Local Jan is not configured.'})
                    ident=body.get('request_id')
                    if not isinstance(ident,str) or not re.fullmatch(r'[a-zA-Z0-9:-]{8,100}',ident):
                        raise ValueError('Stable request identity required.')
                    app.agent.enqueue(ident,body.get('text'),'desktop')
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
            except (ValueError, TypeError, json.JSONDecodeError, sqlite3.Error) as exc:
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
               tz=os.getenv("KIKI_TIMEZONE", "America/Chicago"),
               calendar=CalendarBridge(os.environ["KIKI_CALENDAR_BRIDGE_URL"], os.environ["KIKI_CALENDAR_BRIDGE_KEY"])
               if os.getenv("KIKI_CALENDAR_BRIDGE_URL") and os.getenv("KIKI_CALENDAR_BRIDGE_KEY") else None)
    # Acquire the existing listening port before starting any Telegram consumer.
    # A duplicate startup must fail before it can poll or send.
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app))
    except OSError:
        app.close()
        raise
    stop = threading.Event()
    agent_thread=None
    if os.getenv('KIKI_MODEL_KEY'):
        sys.path.insert(0,str(Path(__file__).parent))
        from jan_agent import JanAgent
        app.agent=JanAgent(app,os.environ['KIKI_MODEL_KEY'])
        agent_thread=threading.Thread(target=app.agent.run,args=(stop,),daemon=True)
        agent_thread.start()
    thread = threading.Thread(target=app.run_background, args=(stop,), daemon=True)
    thread.start()
    sync_thread = None
    if all(os.getenv(name) for name in ('KIKI_SITE_URL', 'KIKI_SITE_SERVICE_TOKEN', 'KIKI_SITE_SYNC_KEY')):
        sys.path.insert(0, str(Path(__file__).parent))
        from desktop_sync import DesktopSync
        sync = DesktopSync(app, os.environ['KIKI_SITE_URL'], os.environ['KIKI_SITE_SERVICE_TOKEN'], os.environ['KIKI_SITE_SYNC_KEY'])
        sync_thread = threading.Thread(target=sync.run, args=(stop,), daemon=True)
        sync_thread.start()
    try:
        print(f"Kiki is ready: http://localhost:{args.port} (localhost only)")
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        stop.set()
        thread.join(timeout=3)
        if sync_thread:
            sync_thread.join(timeout=3)
        if agent_thread:
            agent_thread.join(timeout=3)
        app.close()


if __name__ == "__main__":
    main()
