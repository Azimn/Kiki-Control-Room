"""Durability and resurfacing checks; no real mailbox or messaging calls."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

spec = importlib.util.spec_from_file_location('kiki_email_test', Path(__file__).resolve().parents[1] / 'runtime/local/kiki_local.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EmailQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'test.sqlite3'
        self.app = module.Kiki(self.path)
        self.now = datetime(2026, 10, 15, 16, 15, tzinfo=timezone.utc)

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def ingest(self, revision='r1'):
        self.app.ingest_email('thread-a', revision, 'Synthetic student', 'Synthetic question', 'student', self.now.isoformat())

    def test_snooze_survives_restart_and_duplicate_scan(self):
        self.ingest()
        self.app.command('/email-later', self.now)
        self.app.close()
        self.app = module.Kiki(self.path)
        self.ingest()
        self.assertIsNone(self.app.next_email(self.now))
        self.assertIsNotNone(self.app.next_email(self.now + timedelta(hours=1)))

    def test_new_message_reopens_resolved_thread(self):
        self.ingest()
        with self.app.conn:
            self.app.conn.execute("UPDATE email_queue SET status='resolved'")
        self.ingest()
        self.assertIsNone(self.app.next_email(self.now))
        self.ingest('r2')
        self.assertEqual(self.app.next_email(self.now)['revision'], 'r2')

    def test_student_before_colleague_and_oldest_within_group(self):
        self.app.ingest_email('colleague', 'r1', 'Synthetic colleague', 'Question', 'colleague', (self.now-timedelta(days=5)).isoformat())
        self.ingest()
        self.assertEqual(self.app.next_email(self.now)['thread_id'], 'thread-a')

    def test_opt_in_daily_deduplication_and_privacy(self):
        self.ingest()
        self.app.tick(self.now)
        self.assertEqual(self.app.conn.execute('SELECT count(*) FROM outbox').fetchone()[0], 0)
        self.app.command('/email-on', self.now)
        self.app.tick(self.now)
        self.app.tick(self.now)
        prompts = self.app.conn.execute("SELECT text FROM outbox WHERE dedupe LIKE 'email-checkin:%'").fetchall()
        self.assertEqual(len(prompts), 1)
        self.assertNotIn('Synthetic', prompts[0]['text'])

    def test_pause_suppresses_routine(self):
        self.ingest()
        self.app.command('/email-on', self.now)
        self.app.pause(True)
        self.app.tick(self.now)
        self.assertEqual(self.app.conn.execute("SELECT count(*) FROM outbox WHERE dedupe LIKE 'email-checkin:%'").fetchone()[0], 0)

    def test_followups_are_bounded_and_queue_is_retained(self):
        self.ingest()
        self.app.command('/email-on', self.now)
        for minutes in (0, 30, 90, 150, 210):
            self.app.tick(self.now + timedelta(minutes=minutes))
        count = self.app.conn.execute("SELECT count(*) FROM outbox WHERE dedupe LIKE 'email-followup:%'").fetchone()[0]
        self.assertEqual(count, 2)
        self.assertIsNotNone(self.app.next_email(self.now))

    def test_open_session_stops_automatic_followups(self):
        self.ingest()
        self.app.command('/email-on', self.now)
        self.app.tick(self.now)
        self.app.command('/email', self.now)
        self.app.tick(self.now + timedelta(minutes=31))
        self.assertEqual(self.app.conn.execute("SELECT count(*) FROM outbox WHERE dedupe LIKE 'email-followup:%'").fetchone()[0], 0)

    def test_requires_timezone(self):
        with self.assertRaises(ValueError):
            self.app.ingest_email('a', 'r1', 'Sender', 'Subject', 'student', '2026-10-15T11:00:00')

    def test_checkin_does_not_start_before_1115(self):
        self.ingest()
        self.app.command('/email-on', self.now)
        self.app.tick(self.now - timedelta(minutes=1))
        self.assertEqual(self.app.conn.execute("SELECT count(*) FROM outbox WHERE dedupe LIKE 'email-checkin:%'").fetchone()[0], 0)
        self.app.tick(self.now)
        self.assertEqual(self.app.conn.execute("SELECT count(*) FROM outbox WHERE dedupe LIKE 'email-checkin:%'").fetchone()[0], 1)

    def test_draft_survives_restart_without_resolving_or_sending(self):
        self.ingest()
        args = ('draft-0001', 'thread-a', 'r1', 'synthetic@example.invalid', 'Synthetic reply')
        self.app.save_email_draft(*args, now=self.now)
        self.app.save_email_draft(*args, now=self.now)
        self.app.close()
        self.app = module.Kiki(self.path)
        draft = self.app.email_draft('draft-0001')
        self.assertFalse(draft['send_enabled'])
        self.assertFalse(draft['stale'])
        self.assertEqual(draft['body'], 'Synthetic reply')
        self.assertIsNotNone(self.app.next_email(self.now))
        self.assertEqual(self.app.conn.execute('SELECT count(*) FROM outbox').fetchone()[0], 0)
        self.assertFalse(self.app.state()['email_send_enabled'])

    def test_new_inbound_mail_invalidates_old_draft(self):
        self.ingest()
        self.app.save_email_draft('draft-0001', 'thread-a', 'r1', 'synthetic@example.invalid', 'Reply')
        self.ingest('r2')
        self.assertTrue(self.app.email_draft('draft-0001')['stale'])
        with self.assertRaises(ValueError):
            self.app.save_email_draft('draft-0002', 'thread-a', 'r1', 'synthetic@example.invalid', 'Old reply')

    def test_changed_draft_retry_is_rejected(self):
        self.ingest()
        self.app.save_email_draft('draft-0001', 'thread-a', 'r1', 'synthetic@example.invalid', 'Reply')
        with self.assertRaises(ValueError):
            self.app.save_email_draft('draft-0001', 'thread-a', 'r1', 'someone-else@example.invalid', 'Reply')


if __name__ == '__main__':
    unittest.main()
