import importlib.util
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

spec = importlib.util.spec_from_file_location('kiki_booking', Path(__file__).resolve().parents[1] / 'runtime/local/kiki_local.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeBridge:
    def __init__(self):
        self.requests = []
        self.code = 'booked'

    def request(self, action, booking=None):
        self.requests.append((action, booking))
        return {'code': self.code, 'event_id': 'event123'}


class CalendarBookingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'tasks.sqlite3'
        self.bridge = FakeBridge()
        self.app = module.Kiki(self.path, calendar=self.bridge)
        self.now = datetime(2026, 10, 13, 18, tzinfo=timezone.utc)

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def reply(self):
        return self.app.conn.execute('SELECT text FROM outbox ORDER BY id DESC LIMIT 1').fetchone()[0]

    def test_direct_book_writes_without_second_confirmation_and_persists(self):
        self.app.command('/book 2026-10-15 10:00 30 Review syllabus', self.now)
        self.assertEqual(len(self.bridge.requests), 1)
        self.assertIn('Booked:', self.reply())
        row = self.app.conn.execute('SELECT * FROM bookings').fetchone()
        self.assertEqual(row['status'], 'booked')
        self.assertEqual(row['start'], '2026-10-15T15:00:00+00:00')
        self.app.close()
        self.app = module.Kiki(self.path, calendar=self.bridge)
        self.assertEqual(self.app.conn.execute('SELECT status FROM bookings').fetchone()[0], 'booked')
        self.app.command('/confirm', self.now)
        self.assertEqual(len(self.bridge.requests), 1)

    def test_optional_preview_and_cancel_do_not_write(self):
        self.app.command('/block 2026-10-15 10:00 30 Review syllabus', self.now)
        self.assertFalse(self.bridge.requests)
        self.app.command('/cancel', self.now)
        self.app.command('/confirm', self.now)
        self.assertFalse(self.bridge.requests)

    def test_restart_and_failed_request_retry_use_same_identity(self):
        self.bridge.code = 'unavailable'
        self.app.command('/book 2026-10-15 10:00 30 Review syllabus', self.now)
        first = self.bridge.requests[0][1]['id']
        self.app.close()
        self.app = module.Kiki(self.path, calendar=self.bridge)
        self.bridge.code = 'booked'
        self.app.command('/confirm', self.now)
        self.assertEqual(self.bridge.requests[1][1]['id'], first)
        self.assertIn('Booked:', self.reply())

    def test_conflict_does_not_claim_success(self):
        self.bridge.code = 'conflict'
        self.app.command('/book 2026-10-15 10:00 30 Review syllabus', self.now)
        self.assertIn('Nothing was created', self.reply())
        self.assertEqual(self.app.conn.execute('SELECT status FROM bookings').fetchone()[0], 'proposed')

    def test_invalid_past_and_dst_times_never_reach_bridge(self):
        for text in ('2026-02-30 10:00 30 Test', '2026-10-12 10:00 30 Test',
                     '2026-10-15 10:00 999 Test', '2026-11-01 01:30 30 Test',
                     '2027-03-14 02:30 30 Test'):
            self.app.command('/book ' + text, self.now)
        self.assertFalse(self.bridge.requests)

    def test_unauthorized_telegram_chat_cannot_book(self):
        self.app.token, self.app.chat_id = 'fake', '42'
        self.app._telegram = lambda *args: [{'update_id': 1, 'message': {
            'chat': {'id': 999}, 'text': '/book 2026-10-15 10:00 30 Test'}}]
        self.app.poll()
        self.assertFalse(self.bridge.requests)

    def test_expired_preview_never_writes(self):
        self.app.command('/block 2026-10-15 10:00 30 Test', self.now)
        self.app.command('/confirm', datetime(2026, 10, 13, 19, tzinfo=timezone.utc))
        self.assertFalse(self.bridge.requests)
        self.assertIn('expired', self.reply())

    def test_bridge_configuration_rejects_arbitrary_hosts(self):
        with self.assertRaises(ValueError):
            module.CalendarBridge('https://evil.example/exec', 'x' * 64)

    def test_replayed_telegram_update_does_not_create_second_booking(self):
        text = '/book 2026-10-15 10:00 30 Test'
        self.app.command(text, self.now, request_id='telegram:42:123')
        self.app.close()
        self.app = module.Kiki(self.path, calendar=self.bridge)
        self.app.command(text, self.now, request_id='telegram:42:123')
        self.assertEqual(len(self.bridge.requests), 1)
        self.assertEqual(self.app.conn.execute('SELECT count(*) FROM bookings').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
