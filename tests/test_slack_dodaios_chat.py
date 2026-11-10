import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from integrations.slack.dodaios_chat import DodaiosChat
from integrations.slack.kiki_slack_bot import Inbox


EVENT = {'team': 'TTEST', 'event': 'EvTEST', 'channel': 'DTEST', 'text': 'synthetic test'}


def timeline(*events, running=False, surface='side'):
    return {'session': {'surface': surface, 'provider': 'ollama', 'model': 'kiki', 'running': running},
            'events': [{'kind': kind, 'payload': payload} for kind, payload in events]}


class DodaiosChatTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.inbox = Inbox(Path(temporary.name) / 'transport.sqlite3')
        self.inbox.admit(EVENT)
        self.runtime = DodaiosChat(self.inbox, 'session', 'kiki')

    def test_submits_once_and_replays_result(self):
        complete = timeline(
            ('assistant_text', {'turn_id': 'one', 'text': 'synthetic reply'}),
            ('turn_finished', {'turn_id': 'one', 'status': 'done'}),
        )
        self.runtime.request = Mock(side_effect=[timeline(), {'turn_id': 'one'}, complete, complete])
        self.assertEqual(self.runtime(EVENT), {'status': 'queued'})
        self.assertEqual(self.runtime(EVENT), {'status': 'ready', 'reply': 'synthetic reply'})
        self.assertEqual(self.runtime(EVENT), {'status': 'ready', 'reply': 'synthetic reply'})
        self.assertEqual(sum(call.args[0] == '/messages' for call in self.runtime.request.call_args_list), 1)

    def test_ambiguous_post_is_recovered_without_retrying(self):
        digest = hashlib.sha256(b'TTEST:EvTEST').hexdigest()
        recovered = timeline(
            ('user_message', {'text': f'Slack message ({digest})\nsynthetic test'}),
            ('turn_started', {'turn_id': 'one'}),
            ('assistant_text', {'turn_id': 'one', 'text': 'synthetic reply'}),
            ('turn_finished', {'turn_id': 'one', 'status': 'done'}),
        )
        self.runtime.request = Mock(side_effect=[timeline(), TimeoutError(), recovered])
        self.assertEqual(self.runtime(EVENT), {'status': 'unavailable'})
        self.assertEqual(self.runtime(EVENT), {'status': 'ready', 'reply': 'synthetic reply'})
        self.assertEqual(sum(call.args[0] == '/messages' for call in self.runtime.request.call_args_list), 1)

    def test_tool_enabled_surface_and_tool_events_fail_closed(self):
        self.runtime.request = Mock(return_value=timeline(surface='jarvis'))
        self.assertEqual(self.runtime(EVENT), {'status': 'denied'})
        self.runtime.request.assert_called_once_with('?tail=100')
        self.inbox.set_native_turn('TTEST:EvTEST', None, 'one')
        self.runtime.request.return_value = timeline(('tool_call', {'turn_id': 'one'}))
        self.assertEqual(self.runtime(EVENT), {'status': 'denied'})
        self.assertEqual(self.runtime({**EVENT, 'channel': 'CTEST'}), {'status': 'denied'})


if __name__ == '__main__':
    unittest.main()
