import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.request import urlopen

from integrations.slack import kiki_slack_bot as bot
from runtime.local.desktop_sync import DesktopSync
from runtime.local.jan_agent import JanAgent
from runtime.local.kiki_local import Kiki, make_handler, ThreadingHTTPServer

try:
    from slack_sdk.errors import SlackApiError
except ImportError:
    SlackApiError = None


POLICY = bot.Policy('TTEST', 'ATEST', 'BTEST', 'UBOT', frozenset({'UOWNER'}), frozenset({'DTEST', 'CTEST'}))
KEY = 'synthetic-loopback-key-for-test-only'
TS = '1234567890.123456'
REPLY_TS = '1234567890.234567'


def envelope(**fields):
    event = dict(type='message', channel_type='im', user='UOWNER', channel='DTEST',
                 ts=TS, text='A synthetic fact about a blue tram.')
    event.update(fields)
    return dict(type='event_callback', event_id='EvTEST', team_id='TTEST', api_app_id='ATEST',
                is_ext_shared_channel=False, event=event,
                authorizations=[dict(team_id='TTEST', user_id='UBOT', is_bot=True)])


class SlackTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'inbox.sqlite3'
        self.inbox = bot.Inbox(self.path)
        self.stop = threading.Event()
        self.web = Mock()
        self.web.chat_postMessage.side_effect = lambda **kw: {'ok': True, 'channel': kw['channel'], 'ts': REPLY_TS}

    def receive(self, payload, callback):
        client = Mock()
        client.send_socket_mode_response.side_effect = callback
        request = SimpleNamespace(type='events_api', envelope_id='envelope-1', payload=payload)
        bot.receive(self.inbox, POLICY, (KEY,), client, request)
        return client

    def process(self, runtime, policy=POLICY, now=None):
        now = time.time() if now is None else now
        row = self.inbox.next(now)
        self.assertIsNotNone(row)
        bot.deliver(self.inbox, policy, runtime, self.web, (KEY,), row, now, self.stop)

    def test_reject_unauthorized_and_unsupported_events(self):
        invalid = [
            envelope(user='UOTHER'), envelope(channel='DOTHER'), envelope(text=None),
            envelope(text='  '), envelope(subtype='message_changed'), envelope(bot_id='BOTHER'),
            envelope(user='UBOT'), envelope(user=[]), envelope(type='message', channel='CTEST'),
            envelope(type='app_mention', channel='CTEST', text='no mention'),
            {**envelope(), 'team_id': 'TOTHER'}, {**envelope(), 'api_app_id': 'AOTHER'},
            {**envelope(), 'is_ext_shared_channel': True}, {**envelope(), 'authorizations': []},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                client = self.receive(payload, lambda _: self.assertEqual({}, self.inbox.status()))
                client.send_socket_mode_response.assert_called_once()
        self.web.assert_not_called()

    def test_peer_exchange_requires_verified_bot_private_thread_and_admits_once(self):
        policy = bot.Policy(POLICY.team, POLICY.app, POLICY.bot, POLICY.bot_user, POLICY.users,
                            POLICY.channels, ('ACALIBOS', 'BCALIBOS', 'UCALIBOS', 'CTEST', TS))
        payload = envelope(user='UCALIBOS', channel='CTEST', channel_type='group',
                           bot_id='BCALIBOS', app_id='ACALIBOS', subtype='bot_message',
                           thread_ts=TS, text='<@UBOT> synthetic request')
        event = policy.event(payload)
        self.assertEqual(event['text'], 'synthetic request')
        self.assertTrue(policy.allows_delivery(event))
        self.assertFalse(POLICY.allows_delivery(event))
        for field, bad in [('bot_id', 'BOTHER'), ('app_id', 'AOTHER'), ('user', 'UOTHER'),
                           ('channel_type', 'channel'), ('thread_ts', REPLY_TS), ('text', 'no mention')]:
            candidate = {**payload, 'event': {**payload['event'], field: bad}}
            self.assertIsNone(policy.event(candidate))
        self.assertTrue(self.inbox.admit(event))
        self.assertTrue(self.inbox.admit({**event, 'event': 'EvFOLLOWUP'}))
        self.assertEqual(self.inbox.status(), {'pending': 1})

    def test_ack_after_durable_commit_and_replay(self):
        def committed(response):
            self.assertEqual(response['envelope_id'], 'envelope-1')
            self.assertEqual(bot.Inbox(self.path).status(), {'pending': 1})

        self.receive(envelope(), committed)
        self.inbox = bot.Inbox(self.path)
        self.receive(envelope(text='retry cannot replace original'), committed)
        row = self.inbox.next(time.time())
        self.assertIn('blue tram', row['body'])

    def test_backpressure_and_disk_failure_leave_envelope_unacknowledged(self):
        with patch.object(bot, 'MAX_PENDING', 0):
            self.receive(envelope(), None).send_socket_mode_response.assert_not_called()
        with patch.object(self.inbox, 'admit', side_effect=bot.sqlite3.OperationalError):
            self.receive(envelope(), None).send_socket_mode_response.assert_not_called()

    @unittest.skipIf(SlackApiError is None, 'optional slack-sdk dependency')
    def test_same_destination_threading_and_secret_redaction(self):
        for i, (payload, expected) in enumerate([
            (envelope(text=KEY), None),
            (envelope(thread_ts=REPLY_TS), REPLY_TS),
            (envelope(type='app_mention', channel='CTEST', text='<@UBOT> hello'), TS),
            (envelope(type='app_mention', channel='CTEST', text='<@UBOT> hello', thread_ts=REPLY_TS), REPLY_TS),
        ]):
            payload['event_id'] = f'EvTEST{i}'
            self.receive(payload, None)
            self.assertNotIn(KEY, self.inbox.next(time.time())['body'])
            self.process(lambda event: {'status': 'ready', 'reply': KEY + ' <!channel>'})
            sent = self.web.chat_postMessage.call_args.kwargs
            self.assertEqual(sent['channel'], payload['event']['channel'])
            self.assertEqual(sent['thread_ts'], expected)
            self.assertEqual(sent['text'], '[redacted] &lt;!channel&gt;')
            self.assertFalse(sent['unfurl_links'])
        self.assertEqual(self.inbox.status(), {'provider_accepted': 4})

    @unittest.skipIf(SlackApiError is None, 'optional slack-sdk dependency')
    def test_rate_limit_survives_restart_and_ambiguous_send_is_not_retried(self):
        self.receive(envelope(), None)
        self.web.chat_postMessage.side_effect = SlackApiError('redacted', SimpleNamespace(
            status_code=429, headers={'retry-after': '45'}))
        now = time.time()
        self.process(lambda _: {'status': 'ready', 'reply': 'hello'}, now=now)
        self.inbox = bot.Inbox(self.path)
        self.inbox.recover()
        self.assertIsNone(self.inbox.next(now + 44))
        self.web.chat_postMessage.side_effect = TimeoutError('provider acceptance ambiguous')
        self.process(lambda _: {'status': 'ready', 'reply': 'hello'}, now=now + 46)
        self.receive(envelope(), None)
        self.assertIsNone(self.inbox.next(now + 100))
        self.assertEqual(self.inbox.status(), {'uncertain': 1})
        self.assertEqual(self.web.chat_postMessage.call_count, 2)

    @unittest.skipIf(SlackApiError is None, 'optional slack-sdk dependency')
    def test_offline_queue_and_revoked_allowlist(self):
        self.receive(envelope(), None)
        now = time.time()
        self.process(lambda _: {'status': 'unavailable'}, now=now)
        self.assertIsNone(self.inbox.next(now + 14))
        revoked = bot.Policy(POLICY.team, POLICY.app, POLICY.bot, POLICY.bot_user, frozenset(), POLICY.channels)
        runtime = Mock()
        self.process(runtime, policy=revoked, now=now + 16)
        runtime.assert_not_called()
        self.web.chat_postMessage.assert_not_called()
        self.assertEqual(self.inbox.status(), {'denied': 1})

    def test_recovery_of_interrupted_send_requires_readback(self):
        self.receive(envelope(), None)
        self.inbox.update('TTEST:EvTEST', 'pending', 'sending')
        self.inbox = bot.Inbox(self.path)
        self.inbox.recover()
        self.assertEqual(self.inbox.status(), {'uncertain': 1})
        self.assertIsNone(self.inbox.next(time.time()))

    @unittest.skipIf(SlackApiError is None, 'optional slack-sdk dependency')
    def test_sdk_startup_retries_and_uses_reconnect_enabled_client(self):
        web = Mock()
        web.auth_test.return_value = dict(ok=True, team_id=POLICY.team, user_id=POLICY.bot_user, bot_id=POLICY.bot)
        first, second = Mock(), Mock()
        first.connect.side_effect = OSError('transient')
        second.is_connected.side_effect = [False, True]
        self.receive(envelope(), None)

        def accepted(**kw):
            self.stop.set()
            return {'ok': True, 'channel': kw['channel'], 'ts': REPLY_TS}

        web.chat_postMessage.side_effect = accepted
        with patch.object(bot, 'HEALTH_PORT', 0), patch('slack_sdk.WebClient', return_value=web), \
                patch('slack_sdk.socket_mode.SocketModeClient', side_effect=[first, second]) as client:
            status = bot.run_listener(self.inbox, POLICY, lambda _: {'status': 'ready', 'reply': 'hello'},
                                      'synthetic-app', 'synthetic-bot', KEY, self.stop)
        self.assertEqual(status, 0)
        self.assertEqual(client.call_count, 2)
        self.assertTrue(client.call_args.kwargs.get('auto_reconnect_enabled', True))
        first.close.assert_called_once()
        second.close.assert_called_once()
        self.assertEqual(self.inbox.status(), {'provider_accepted': 1})

    @unittest.skipIf(SlackApiError is None, 'optional slack-sdk dependency')
    def test_loopback_turn_restart_and_local_desktop_surface(self):
        with patch.dict(os.environ, {'KIKI_SLACK_BRIDGE_KEY': KEY, 'KIKI_SLACK_LOCAL_HISTORY': '0'}):
            app = Kiki(self.path.with_name('control.sqlite3'))
            app.agent = JanAgent(app, 'synthetic-jan-key-for-test-only-32')
            server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(app))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(app.close)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            runtime = bot.LocalRuntime(server.server_port, KEY)
            bad_runtime = bot.LocalRuntime(server.server_port, 'invalid')
            event = POLICY.event(envelope())
            self.assertEqual(bad_runtime(event)['status'], 'denied')
            self.receive(envelope(), None)
            self.assertEqual(runtime(event)['status'], 'queued')
            job = app.conn.execute('SELECT * FROM agent_jobs').fetchone()
            self.assertEqual(job['source'], 'slack')
            request = None

            def infer(req, **_):
                nonlocal request
                request = json.loads(req.data)
                content = json.dumps(dict(action='add_task', reply='made a task', title='fake', task_id=None))
                return io.BytesIO(json.dumps({'choices': [{'message': {'content': content}}]}).encode())

            model_stop = threading.Event()
            # Run the actual serial Control Room worker with synthetic inference.
            with patch.object(app.agent.slack_model, 'open', side_effect=infer), patch('runtime.local.jan_agent.urlopen', side_effect=OSError):
                model = threading.Thread(target=app.agent.run, args=(model_stop,), daemon=True)
                model.start()
                try:
                    deadline = time.monotonic() + 3
                    while runtime(event)['status'] != 'ready':
                        self.assertLess(time.monotonic(), deadline)
                        time.sleep(0.02)
                finally:
                    model_stop.set()
                    app.agent.wake.set()
                    model.join(2)
            self.assertEqual(request['messages'][-1]['role'], 'user')
            self.assertNotIn('blue tram', request['messages'][0]['content'])
            self.assertEqual(app.conn.execute('SELECT count(*) FROM tasks').fetchone()[0], 0)
            self.assertEqual(app.agent.context(), [])
            app.agent = JanAgent(app, 'synthetic-jan-key-for-test-only-32')
            self.inbox = bot.Inbox(self.path)
            self.receive(envelope(), None)
            self.process(runtime)
            self.receive(envelope(), None)
            self.assertIsNone(self.inbox.next(time.time()))
            self.assertEqual(app.conn.execute('SELECT count(*) FROM agent_jobs').fetchone()[0], 1)
            self.web.chat_postMessage.assert_called_once()
            self.assertEqual(app.agent.slack_context(job)[0]['user'], event['text'])
            another = dict(job)
            payload = json.loads(job['payload'])
            payload['user'] = 'UOTHER'
            another['payload'] = json.dumps(payload)
            self.assertEqual(app.agent.slack_context(another), [])
            snapshot = DesktopSync(app, 'https://example.chatgpt.site', 'x'*32, 'y'*32).snapshot()
            self.assertNotIn('blue tram', json.dumps(snapshot))
            self.assertNotIn('blue tram', json.dumps(app.state()))
            with patch.dict(os.environ, {'KIKI_SLACK_LOCAL_HISTORY': '1'}):
                with urlopen(f'http://127.0.0.1:{server.server_port}/api/state') as response:
                    turn = json.load(response)['conversations'][0]
                self.assertEqual((turn['source'], turn['text']), ('slack', event['text']))


if __name__ == '__main__':
    unittest.main()
