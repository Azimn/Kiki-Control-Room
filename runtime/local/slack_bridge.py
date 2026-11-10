"""Private admission to the existing Control Room conversation worker."""
import hmac
import os
import re
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

SLACK_SECRET = re.compile(r'(?i)\bx(?:ox[a-z]*|app)-[a-z0-9-]+')
SLACK_ID = re.compile(r'[A-Z][A-Z0-9]{1,39}')
EVENT_ID = re.compile(r'Ev[A-Z0-9]{1,38}')
TS = re.compile(r'\d{1,16}\.\d{6}')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def loopback_opener():
    return build_opener(ProxyHandler({}), NoRedirect())


def redact(text, *secrets):
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[redacted]')
    return SLACK_SECRET.sub('[redacted]', text)


def route(app, headers, body):
    key = os.getenv('KIKI_SLACK_BRIDGE_KEY', '')
    auth = headers.get('Authorization', '').encode()
    if len(key) < 32 or not hmac.compare_digest(auth, ('Bearer ' + key).encode()):
        return 403, {'status': 'denied'}
    if not app.agent:
        return 503, {'status': 'unavailable'}

    fields = ('team', 'event', 'channel', 'user', 'ts', 'thread_ts', 'app', 'bot')
    provenance = {field: body.get(field) for field in fields}
    if any(not isinstance(value, str) for value in provenance.values()):
        return 400, {'status': 'invalid'}
    team, event, channel, user, ts, thread_ts, app_id, bot_id = provenance.values()
    if not EVENT_ID.fullmatch(event) or not all(SLACK_ID.fullmatch(value) for value in (team, channel, user, app_id, bot_id)):
        return 400, {'status': 'invalid'}
    if not TS.fullmatch(ts) or (thread_ts and not TS.fullmatch(thread_ts)):
        return 400, {'status': 'invalid'}
    provenance['conversation'] = thread_ts or ('' if channel.startswith('D') else ts)
    ident = f'slack:{team}:{event}'
    raw = body.get('text')
    if not isinstance(raw, str) or not 1 <= len(raw.strip()) <= 2000:
        return 400, {'status': 'invalid'}
    text = redact(raw, key)
    try:
        app.agent.enqueue(ident, text, 'slack', provenance)
    except ValueError:
        return 409, {'status': 'conflict'}
    with app.lock:
        job = app.conn.execute("SELECT status,reply FROM agent_jobs WHERE id=?", (ident,)).fetchone()
        model_status = app._get('model_status')
    result = {'status': 'queued', 'source': 'slack', 'remote_text': 'unavailable'}
    if job['status'] == 'done':
        result.update(status='ready', reply=redact(job['reply'], key))
    elif model_status == 'unavailable':
        result['status'] = 'queued_runtime_unavailable'
    return 200, result
