"""Regression suite for the dependency-free Kiki local runtime."""
import importlib.util
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError


CODE = Path(__file__).resolve().parents[1] / "runtime" / "local" / "kiki_local.py"
spec = importlib.util.spec_from_file_location("kiki_local", CODE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LocalRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.kiki = module.Kiki(Path(self.temp.name) / "kiki.sqlite3")
        self.when = datetime(2026, 10, 14, 14, 5, tzinfo=timezone.utc)

    def tearDown(self):
        self.kiki.close()
        self.temp.cleanup()

    def test_persistence_across_sessions(self):
        i = self.kiki.add("Reply to a message", self.when)
        self.assertEqual(self.kiki.state()["tasks"][0]["id"], i)
        self.kiki.close()
        self.kiki = module.Kiki(Path(self.temp.name) / "kiki.sqlite3")
        self.assertEqual(self.kiki.state()["tasks"][0]["title"], "Reply to a message")
        self.kiki.done(i, self.when)
        self.assertEqual(self.kiki.state()["tasks"][0]["status"], "done")

    def test_task_validation_and_missing_completion(self):
        with self.assertRaises(ValueError):
            self.kiki.add(" ")
        with self.assertRaises(ValueError):
            self.kiki.done(100)
        with self.assertRaises(ValueError):
            self.kiki.done(True)

    def test_morning_message_once_per_day(self):
        self.kiki.add("Prepare class", self.when)
        self.kiki.tick(self.when)
        self.kiki.tick(self.when + timedelta(minutes=5))
        messages = self.kiki.conn.execute(
            "SELECT * FROM outbox WHERE dedupe LIKE 'checkin:%'"
        ).fetchall()
        self.assertEqual(len(messages), 1)
        self.assertTrue(self.kiki.state()["awaiting"])

    def test_followup_until_ack(self):
        self.kiki.tick(self.when)
        self.kiki.tick(self.when + timedelta(minutes=16))
        count = self.kiki.conn.execute("SELECT count(*) FROM outbox").fetchone()[0]
        self.assertEqual(count, 2)
        self.kiki.ack()
        self.kiki.tick(self.when + timedelta(minutes=70))
        self.assertEqual(self.kiki.conn.execute(
            "SELECT count(*) FROM outbox"
        ).fetchone()[0], count)

    def test_pause_and_snooze(self):
        self.kiki.pause(True)
        self.kiki.tick(self.when)
        self.assertEqual(self.kiki.conn.execute(
            "SELECT count(*) FROM outbox"
        ).fetchone()[0], 0)
        self.kiki.pause(False)
        self.kiki.tick(self.when)
        self.kiki.snooze(30, self.when)
        self.assertTrue(self.kiki.state()["awaiting"])
        with self.assertRaises(ValueError):
            self.kiki.snooze(1000)

    def test_telegram_commands_without_network(self):
        self.kiki.command("/add Check syllabus", self.when)
        self.kiki.command("/status", self.when)
        self.assertEqual(self.kiki.state()["tasks"][0]["title"], "Check syllabus")
        self.kiki.command("/done 1", self.when)
        self.assertEqual(self.kiki.state()["tasks"][0]["status"], "done")
        self.kiki.command("/pause", self.when)
        self.assertTrue(self.kiki.state()["paused"])
        self.kiki.command("/resume", self.when)
        self.assertFalse(self.kiki.state()["paused"])

    def test_telegram_rejects_unapproved_chats(self):
        self.kiki.token = "fake"
        self.kiki.chat_id = "42"
        self.kiki._telegram = lambda name, data: [
            {"update_id": 1, "message": {"chat": {"id": 999}, "text": "/add Nope"}},
            {"update_id": 2, "message": {"chat": {"id": 42}, "text": "/add Yep"}},
        ]
        self.kiki.poll()
        self.assertEqual([x["title"] for x in self.kiki.state()["tasks"]], ["Yep"])
        self.assertEqual(self.kiki._get("telegram_offset"), 3)

    def test_rest_api_and_origin_guard(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), module.make_handler(self.kiki))
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        port = httpd.server_address[1]
        try:
            def post(url, payload, origin=None):
                req = Request(
                    f"http://127.0.0.1:{port}{url}",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json",
                             **({"Origin": origin} if origin else {})},
                    method="POST")
                with urlopen(req, timeout=4) as res:
                    return json.load(res)
            result = post("/api/tasks", {"title": "Try voice"})
            self.assertEqual(result["tasks"][0]["title"], "Try voice")
            result = post("/api/done", {"id": 1})
            self.assertEqual(result["tasks"][0]["status"], "done")
            with self.assertRaises(HTTPError) as err:
                post("/api/tasks", {"title": "Unsafe"}, "https://evil.example")
            self.assertEqual(err.exception.code, 403)
            with urlopen(f"http://127.0.0.1:{port}/", timeout=4) as res:
                self.assertIn(b"Kiki Control Room", res.read())
            with urlopen(f"http://127.0.0.1:{port}/manifest.webmanifest", timeout=4) as res:
                self.assertEqual(json.load(res)["name"], "Kiki Control Room")
        finally:
            httpd.shutdown()
            httpd.server_close()
            worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
