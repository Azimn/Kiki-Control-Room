"""Bridge an authorized Slack exchange to an existing tool-free Dodaios chat."""
import hashlib
import json
from urllib.error import HTTPError
from urllib.request import Request

from runtime.local.slack_bridge import loopback_opener


class DodaiosChat:
    """Use Dodaios's own local model and session store.

    The transport owns only the retry fence and turn ID. An ambiguous submission
    is resolved against the session timeline before it can produce a reply.
    """

    def __init__(self, inbox, session, model, *, channel_only=False):
        self.inbox = inbox
        self.session = session
        self.model = model
        self.channel_only = channel_only
        self.origin = 'http://127.0.0.1:47821'
        self.url = f'{self.origin}/api/agent-chat/sessions/{session}'
        self.opener = loopback_opener()

    def request(self, suffix, body=None):
        headers = {'Origin': self.origin}
        data = None
        if body is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(body, ensure_ascii=False).encode()
        request = Request(self.url + suffix, data=data, headers=headers)
        with self.opener.open(request, timeout=5) as response:
            return json.load(response)

    def __call__(self, event):
        if bool(event.get('channel_chat')) != self.channel_only:
            return {'status': 'denied'}
        if not self.channel_only and not event['channel'].startswith('D'):
            return {'status': 'denied'}
        ident = f"{event['team']}:{event['event']}"
        digest = hashlib.sha256(ident.encode()).hexdigest()
        prefix = f'Slack message ({digest})\n'
        try:
            current = self.request('?tail=100')
            session = current['session']
            if (session.get('surface'), session.get('provider'), session.get('model')) != (
                'side', 'ollama', self.model
            ):
                return {'status': 'denied'}
            turn = self.inbox.native_turn(ident)
            if turn is None:
                if session.get('running'):
                    return {'status': 'queued'}
                if not self.inbox.set_native_turn(ident, None, 'submitting'):
                    return {'status': 'queued'}
                try:
                    sent = self.request('/messages', {'text': prefix + event['text']})
                except HTTPError as exc:
                    if exc.code == 409:
                        self.inbox.set_native_turn(ident, 'submitting', None)
                        return {'status': 'queued'}
                    if exc.code in (400, 403, 404, 422):
                        return {'status': 'denied'}
                    raise
                new_turn = sent.get('turn_id')
                if isinstance(new_turn, str) and new_turn:
                    self.inbox.set_native_turn(ident, 'submitting', new_turn)
                return {'status': 'queued'}
            events = current['events']
            if turn == 'submitting':
                turn = recover_turn(events, prefix)
                if not turn:
                    return {'status': 'unavailable'}
                self.inbox.set_native_turn(ident, 'submitting', turn)
            return read_turn(events, turn)
        except (OSError, ValueError, TypeError, KeyError):
            return {'status': 'unavailable'}


def recover_turn(events, prefix):
    own_message = False
    for event in events:
        kind, payload = event['kind'], event['payload']
        if kind == 'user_message':
            own_message = payload.get('text', '').startswith(prefix)
        elif own_message and kind == 'turn_started':
            return payload.get('turn_id')
    return None


def read_turn(events, turn):
    own_events = [event for event in events if event['payload'].get('turn_id') == turn]
    if any(event['kind'] in ('tool_call', 'approval_required') for event in own_events):
        return {'status': 'denied'}
    result = next((e['payload'] for e in own_events if e['kind'] == 'turn_finished'), None)
    if not result:
        return {'status': 'queued'}
    if result.get('status') != 'done':
        return {'status': 'denied'}
    reply = next((e['payload'].get('text') for e in reversed(own_events)
                  if e['kind'] == 'assistant_text'), None)
    if not isinstance(reply, str) or not reply.strip():
        return {'status': 'denied'}
    return {'status': 'ready', 'reply': reply}
