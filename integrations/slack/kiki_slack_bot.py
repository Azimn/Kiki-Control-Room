"""Optional Slack Socket Mode transport for the existing local Kiki worker."""
import argparse
from contextlib import closing
from dataclasses import dataclass
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import re
from pathlib import Path
import sqlite3
import socket as net_socket
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request

from runtime.local.slack_bridge import EVENT_ID, SLACK_ID, TS, loopback_opener, redact

HEALTH_PORT = 8766
MAX_PENDING = 128


@dataclass(frozen=True)
class Policy:
    team: str
    app: str
    bot: str
    bot_user: str
    users: frozenset
    channels: frozenset
    peer: tuple | None = None

    @classmethod
    def load(cls, data):
        def ident(value, prefix):
            if not isinstance(value, str) or not value.startswith(prefix) or not SLACK_ID.fullmatch(value):
                raise ValueError('Invalid Slack policy identifier')
            return value

        def allowlist(name, prefix):
            values = data[name]
            if not isinstance(values, list) or not values:
                raise ValueError('Slack allowlists must be nonempty lists')
            return frozenset(ident(value, prefix) for value in values)

        app = ident(data['app_id'], 'A')
        bot = ident(data['bot_id'], 'B')
        bot_user = ident(data['bot_user_id'], 'U')
        peer_data = data.get('peer_exchange')
        peer = None
        if peer_data is not None:
            if not isinstance(peer_data, dict) or not TS.fullmatch(peer_data.get('thread_ts', '')):
                raise ValueError('The peer exchange requires a specific private Slack thread')
            peer = (ident(peer_data['app_id'], 'A'), ident(peer_data['bot_id'], 'B'),
                    ident(peer_data['bot_user_id'], 'U'), ident(peer_data['channel'], ('C', 'G')),
                    peer_data['thread_ts'])
            if any(own == other for own, other in zip((app, bot, bot_user), peer[:3])):
                raise ValueError('A Slack bot cannot be its own peer')
        return cls(ident(data['team_id'], 'T'), app, bot, bot_user,
                   allowlist('allowed_users', ('U', 'W')), allowlist('allowed_channels', ('D', 'C', 'G')), peer)

    def allows(self, channel, user):
        return isinstance(channel, str) and channel in self.channels and isinstance(user, str) and user in self.users

    def allows_delivery(self, event):
        if event.get('peer_app'):
            return self.peer == (event['peer_app'], event['peer_bot'], event['user'],
                                 event['channel'], event['thread_ts'])
        return self.allows(event['channel'], event['user']) and event['user'] != self.bot_user

    def peer_event(self, event):
        if not self.peer or event.get('type') != 'message' or event.get('channel_type') != 'group':
            return None
        if event.get('subtype') not in (None, 'bot_message') or event.get('edited'):
            return None
        profile = event.get('bot_profile')
        profile_app = profile.get('app_id') if isinstance(profile, dict) else None
        app, bot, user, channel, thread = self.peer
        if (event.get('app_id', profile_app), event.get('bot_id'), event.get('channel'),
                event.get('thread_ts')) != (app, bot, channel, thread):
            return None
        if event.get('user', user) != user or (profile_app and profile_app != app):
            return None
        text = event.get('text')
        mention = f'<@{self.bot_user}>'
        if not isinstance(text, str) or len(text) > 2000 or not text.startswith(mention + ' '):
            return None
        return app, bot, user, text[len(mention):].strip()

    def event(self, payload, secrets=()):
        if not isinstance(payload, dict) or payload.get('type') != 'event_callback':
            return None
        if (payload.get('team_id') != self.team or payload.get('api_app_id') != self.app
                or payload.get('context_team_id', self.team) != self.team):
            return None
        if payload.get('is_ext_shared_channel') is not False:
            return None
        installations = payload.get('authorizations')
        if not isinstance(installations, list) or not any(
            isinstance(item, dict) and item.get('team_id') == self.team
            and item.get('user_id') == self.bot_user and item.get('is_bot') is True
            for item in installations
        ):
            return None
        event = payload.get('event')
        if not isinstance(event, dict):
            return None
        if event.get('team', self.team) != self.team or event.get('user_team', self.team) != self.team:
            return None
        channel = event.get('channel')
        peer = self.peer_event(event)
        peer_fields = {}
        if peer:
            peer_app, peer_bot, user, text = peer
            peer_fields = {'peer_app': peer_app, 'peer_bot': peer_bot}
        else:
            if any(key in event for key in ('subtype', 'bot_id', 'bot_profile', 'app_id', 'edited')):
                return None
            channel, user = event.get('channel'), event.get('user')
            if not self.allows(channel, user) or user == self.bot_user:
                return None
            text = event.get('text')
            if not isinstance(text, str) or len(text) > 2000:
                return None
            if event.get('type') == 'app_mention' and channel.startswith(('C', 'G')):
                mention = f'<@{self.bot_user}>'
                if mention not in text:
                    return None
                text = text.replace(mention, '', 1)
            elif not (event.get('type') == 'message' and channel.startswith('D') and event.get('channel_type') == 'im'):
                return None
        event_id, ts, thread_ts = payload.get('event_id'), event.get('ts'), event.get('thread_ts', '')
        if not all(isinstance(item, str) for item in (event_id, ts, thread_ts)):
            return None
        if not EVENT_ID.fullmatch(event_id) or not TS.fullmatch(ts) or (thread_ts and not TS.fullmatch(thread_ts)):
            return None
        if not text.strip():
            return None
        return {'team': self.team, 'event': event_id, 'channel': channel, 'user': user,
                'ts': ts, 'thread_ts': thread_ts, 'text': redact(text.strip(), *secrets),
                'app': self.app, 'bot': self.bot, **peer_fields}


class Inbox:
    """Durable transport admission and delivery receipts. No tasks or agent state."""

    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS slack_inbox (
                id TEXT PRIMARY KEY, body TEXT, status TEXT NOT NULL,
                due REAL NOT NULL DEFAULT 0, accepted_ts TEXT
            )''')
            columns = {row[1] for row in db.execute('PRAGMA table_info(slack_inbox)')}
            if 'native_turn' not in columns:
                db.execute('ALTER TABLE slack_inbox ADD COLUMN native_turn TEXT')
            if 'peer_slot' not in columns:
                db.execute('ALTER TABLE slack_inbox ADD COLUMN peer_slot TEXT')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS slack_peer_slot ON slack_inbox(peer_slot)')

    def native_turn(self, ident):
        with closing(self.connect()) as db:
            return db.execute('SELECT native_turn FROM slack_inbox WHERE id=?', (ident,)).fetchone()[0]

    def set_native_turn(self, ident, previous, value):
        with closing(self.connect()) as db, db:
            return db.execute(
                'UPDATE slack_inbox SET native_turn=? WHERE id=? AND native_turn IS ?',
                (value, ident, previous),
            ).rowcount == 1

    def connect(self):
        db = sqlite3.connect(self.path, timeout=0.25, isolation_level='IMMEDIATE')
        db.row_factory = sqlite3.Row
        return db

    def admit(self, event):
        ident = f"{event['team']}:{event['event']}"
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM slack_inbox WHERE id=?', (ident,)).fetchone():
                return True
            slot = None
            if event.get('peer_app'):
                slot = f"{event['team']}:{event['channel']}:{event['thread_ts']}"
                if db.execute('SELECT 1 FROM slack_inbox WHERE peer_slot=?', (slot,)).fetchone():
                    return True
            count = db.execute("SELECT count(*) FROM slack_inbox WHERE status IN ('pending','rate_limited')").fetchone()[0]
            if count >= MAX_PENDING:
                return False
            db.execute("INSERT INTO slack_inbox(id,body,peer_slot,status) VALUES(?,?,?,'pending')",
                       (ident, json.dumps(event), slot))
        return True

    def next(self, now):
        with closing(self.connect()) as db:
            return db.execute(
                "SELECT * FROM slack_inbox WHERE status IN ('pending','rate_limited') AND due<=? "
                "AND NOT EXISTS (SELECT 1 FROM slack_inbox WHERE status='rate_limited' AND due>?) ORDER BY rowid LIMIT 1",
                (now, now),
            ).fetchone()

    def update(self, ident, expected, status, *, due=0, accepted_ts=None):
        with closing(self.connect()) as db, db:
            return db.execute(
                "UPDATE slack_inbox SET status=?,due=?,accepted_ts=?,"
                "body=CASE WHEN ? IN ('pending','sending','rate_limited') THEN body END "
                "WHERE id=? AND status=?",
                (status, due, accepted_ts, status, ident, expected),
            ).rowcount == 1

    def recover(self):
        # Sending may have succeeded before a process crash. Hold it for review.
        with closing(self.connect()) as db, db:
            db.execute("UPDATE slack_inbox SET status='uncertain',body=NULL WHERE status='sending'")

    def status(self):
        with closing(self.connect()) as db:
            return dict(db.execute('SELECT status,count(*) FROM slack_inbox GROUP BY status'))


class LocalRuntime:
    def __init__(self, port, key):
        self.url = f'http://127.0.0.1:{port}/api/slack-turn'
        self.key = key
        self.opener = loopback_opener()

    def __call__(self, event):
        req = Request(self.url, data=json.dumps(event, ensure_ascii=False).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        try:
            with self.opener.open(req, timeout=3) as response:
                result = json.load(response)
                return result if isinstance(result, dict) else {'status': 'unavailable'}
        except HTTPError as exc:
            if exc.code in (400, 403, 409, 413):
                return {'status': 'denied'}
            return {'status': 'unavailable'}
        except (OSError, ValueError):
            return {'status': 'unavailable'}


def receive(inbox, policy, secrets, client, request):
    if not request.envelope_id:
        return
    if request.type == 'events_api':
        event = policy.event(request.payload, secrets)
        if event:
            try:
                if not inbox.admit(event):
                    return
            except sqlite3.Error:
                # No acknowledgement until the local transaction commits.
                return
    client.send_socket_mode_response({'envelope_id': request.envelope_id})


def retry_after(response):
    for name, value in response.headers.items():
        if name.lower() == 'retry-after':
            try:
                return max(1, int(value))
            except (TypeError, ValueError):
                break
    return 30


def deliver(inbox, policy, runtime, web, secrets, row, now, stop):
    from slack_sdk.errors import SlackApiError

    ident, previous = row['id'], row['status']
    event = json.loads(row['body'])
    if (event['team'] != policy.team or event['app'] != policy.app or event['bot'] != policy.bot
            or not policy.allows_delivery(event)):
        inbox.update(ident, previous, 'denied')
        return
    result = runtime(event)
    status = result.get('status')
    if status == 'denied':
        inbox.update(ident, previous, 'denied')
        return
    reply = result.get('reply')
    if status != 'ready' or not isinstance(reply, str) or not reply.strip():
        delay = 2 if status == 'queued' else 15
        inbox.update(ident, previous, 'pending', due=now + delay)
        return
    if stop.is_set() or not inbox.update(ident, previous, 'sending'):
        return
    channel = event['channel']
    thread = event['thread_ts'] or (None if channel.startswith('D') else event['ts'])
    try:
        response = web.chat_postMessage(
            channel=channel, thread_ts=thread, text=escape(redact(reply, *secrets)[:1800], quote=False),
            mrkdwn=False, parse='none', unfurl_links=False, unfurl_media=False,
        )
        ts = response.get('ts')
        accepted = (response.get('ok') is True and response.get('channel') == channel
                    and isinstance(ts, str) and TS.fullmatch(ts))
    except SlackApiError as exc:
        if exc.response.status_code == 429:
            inbox.update(ident, 'sending', 'rate_limited', due=max(now, time.time()) + retry_after(exc.response))
        else:
            ambiguous = exc.response.status_code >= 500 or exc.response.get('error') in (
                'internal_error', 'fatal_error', 'request_timeout', 'service_unavailable'
            )
            inbox.update(ident, 'sending', 'uncertain' if ambiguous else 'rejected')
    except Exception:
        inbox.update(ident, 'sending', 'uncertain')
    else:
        inbox.update(ident, 'sending', 'provider_accepted' if accepted else 'uncertain',
                     accepted_ts=ts if accepted else None)


class HealthServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(net_socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(net_socket.SOL_SOCKET, net_socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def health_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/health':
                self.send_error(404)
                return
            try:
                data = json.dumps(state()).encode()
            except sqlite3.Error:
                self.send_error(503)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_):
            pass

    return Handler


def verified_bot(web, policy):
    response = web.auth_test()
    return (response.get('ok') is True and response.get('team_id') == policy.team
            and response.get('user_id') == policy.bot_user and response.get('bot_id') == policy.bot)


def run_listener(inbox, policy, runtime, app_token, bot_token, key, stop):
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    from slack_sdk.socket_mode import SocketModeClient

    # SDK diagnostics may include complete WebSocket messages and connect URLs.
    logger = logging.Logger('kiki-slack-disabled')
    logger.disabled = True
    web = WebClient(token=bot_token, timeout=10, retry_handlers=[], logger=logger)
    secrets = (app_token, bot_token, key)
    socket = None
    state = {'connection': 'starting', 'runtime': 'unchecked'}

    def health():
        return {**state, 'socket_connected': bool(socket and socket.is_connected()),
                'receipts': inbox.status(), 'remote_text': 'unavailable', 'external_readback': 'unverified'}

    server = HealthServer(('127.0.0.1', HEALTH_PORT), health_handler(health))
    health_thread = threading.Thread(target=server.serve_forever, daemon=True)
    health_thread.start()
    try:
        inbox.recover()
        print(f'Slack listener status http://127.0.0.1:{server.server_port}/health', flush=True)
        delay = 1
        while not stop.is_set() and socket is None:
            try:
                if not verified_bot(web, policy):
                    print('Configured Slack bot and workspace identity could not be verified.', flush=True)
                    return 1
                socket = SocketModeClient(app_token=app_token, web_client=web, logger=logger, concurrency=1)
                socket.socket_mode_request_listeners.append(
                    lambda client, req: receive(inbox, policy, secrets, client, req))
                socket.connect()
            except Exception as exc:
                state['connection'] = 'retrying'
                if isinstance(exc, SlackApiError) and exc.response.get('error') in (
                    'invalid_auth', 'token_revoked', 'account_inactive', 'not_authed', 'missing_scope'
                ):
                    print('Slack authentication or app permissions were rejected.', flush=True)
                    return 1
                if socket is not None:
                    socket.close()
                    socket = None
                wait = delay
                if isinstance(exc, SlackApiError) and exc.response.status_code == 429:
                    wait = retry_after(exc.response)
                stop.wait(wait)
                delay = min(delay * 2, 60)
        state['connection'] = 'socket_started'
        while not stop.is_set():
            try:
                row = inbox.next(time.time())
                if row and socket.is_connected():
                    def tracked(event):
                        result = runtime(event)
                        state['runtime'] = result.get('status', 'unavailable')
                        return result

                    deliver(inbox, policy, tracked, web, secrets, row, time.time(), stop)
            except (sqlite3.Error, OSError):
                stop.wait(5)
            stop.wait(0.5)
    finally:
        stop.set()
        if socket is not None:
            socket.close()
        server.shutdown()
        server.server_close()
        health_thread.join()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--run', action='store_true', help='Explicitly start the Slack listener')
    mode.add_argument('--dry-run', action='store_true', help='Validate policy offline without reading credentials')
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.config.read_text(encoding='utf-8-sig'))
        policy = Policy.load(data)
        port = data.get('runtime_port', 8765)
        if type(port) is not int or not 1 <= port <= 65535 or port == HEALTH_PORT:
            raise ValueError('Invalid runtime port')
        native = data.get('dodaios_chat')
        if native is not None and (
            not isinstance(native, dict)
            or not isinstance(native.get('session'), str)
            or not re.fullmatch(r'[a-f0-9-]{12,64}', native['session'])
            or not isinstance(native.get('model'), str)
            or not native['model']
            or len(policy.users) != 1 or len(policy.channels) != 1
            or not all(channel.startswith('D') for channel in policy.channels)
        ):
            raise ValueError('The Dodaios path requires one owner and one private DM')
        peer_session = None
        if policy.peer is not None:
            peer_session = data['peer_exchange'].get('dodaios_session')
            if (native is None or not isinstance(peer_session, str)
                    or not re.fullmatch(r'[a-f0-9-]{12,64}', peer_session)
                    or peer_session == native['session']):
                raise ValueError('The peer exchange needs a separate tool-free Dodaios session')
        if args.dry_run:
            print('Slack policy validated offline.')
            return 0
        app_token = os.environ['KIKI_SLACK_APP_TOKEN']
        bot_token = os.environ['KIKI_SLACK_BOT_TOKEN']
        key = os.environ['KIKI_SLACK_BRIDGE_KEY']
        if not app_token.startswith('xapp-') or not bot_token.startswith('xoxb-') or len(key) < 32:
            raise ValueError('Invalid Slack credential configuration')
        path = args.config.resolve().parent / 'slack-inbox.sqlite3'
        stop = threading.Event()
        inbox = Inbox(path)
        if native is not None:
            from integrations.slack.dodaios_chat import DodaiosChat
            dm_runtime = DodaiosChat(inbox, native['session'], native['model'])
            runtime = dm_runtime
            if peer_session is not None:
                peer_runtime = DodaiosChat(inbox, peer_session, native['model'], peer_only=True)

                def runtime(event):
                    return peer_runtime(event) if event.get('peer_app') else dm_runtime(event)
        else:
            runtime = LocalRuntime(port, key)
        return run_listener(inbox, policy, runtime, app_token, bot_token, key, stop)
    except KeyboardInterrupt:
        return 0
    except (ImportError, OSError, ValueError, AttributeError, TypeError, KeyError, sqlite3.Error):
        print('Slack adapter unavailable. Check the private configuration, dependency, and localhost port.', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
