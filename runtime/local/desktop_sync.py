"""Outbound-only Site sync. SQLite owns tasks; the Site holds snapshots/requests."""
import hashlib
import json
import re
import uuid
import os
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen


class DesktopSync:
    def __init__(self, app, site_url, service_token, sync_key):
        if not re.fullmatch(r'https://[a-z0-9.-]+\.chatgpt\.site', site_url):
            raise ValueError('Use the HTTPS Sites origin.')
        if len(service_token) < 32 or len(sync_key) < 32:
            raise ValueError('Missing Site sync credentials.')
        self.app, self.url, self.token, self.key = app, site_url, service_token, sync_key

    def snapshot(self):
        app = self.app
        owner = app._get('queue_owner_id')
        shared_queue = app.queue.projection(owner) if owner else None
        with app.lock, app.conn:
            device = app._get('desktop_device_id')
            if not device:
                device = str(uuid.uuid4())
                app._set('desktop_device_id', device)
            seq = app._get('desktop_snapshot_seq', 0) + 1
            app._set('desktop_snapshot_seq', seq)
            rows = app.conn.execute('SELECT * FROM tasks ORDER BY created_at,id').fetchall()
            if len(rows) > 1000:
                raise ValueError('Task snapshot exceeds configured limit; archive before syncing.')
            tasks = [{'id': r['sync_id'], 'local_id': r['id'], 'title': r['title'],
                      'status': r['status'], 'created_at': r['created_at'],
                      'snoozed_until': r['snoozed_until']} for r in rows]
            receipts = [dict(r) for r in app.conn.execute(
                'SELECT request_id,status FROM desktop_receipts WHERE acknowledged=0 ORDER BY rowid LIMIT 170')]
            for receipt in receipts:
                saved=app.conn.execute('SELECT result FROM queue_requests WHERE owner=? AND request_id=?',(owner,receipt['request_id'])).fetchone()
                if saved: receipt['queue_result']=json.loads(saved[0])
            dialogues=[]
            if app.agent:
                for r in app.conn.execute("SELECT * FROM agent_jobs WHERE status='done' AND cloud_ack=0 LIMIT 30"):
                    if json.loads(r['payload']).get('integration_test'):
                        continue
                    if r['source']=='web':
                        receipts.append({'request_id':r['id'],'status':'applied','reply':r['reply']})
                    else:
                        dialogues.append({'request_id':r['id'],'text':r['text'],'reply':r['reply'],'source':r['source']})
            return {'device_id': device, 'seq': seq, 'snapshot': {'tasks': tasks,
                    'telegram_enabled': bool(app.token and app.chat_id),
                    'calendar_enabled': app.calendar is not None,'model_enabled':app.agent is not None,
                    'model_status':app._get('model_status','not_configured'),'shared_queue':shared_queue,'paused':app._get('paused',False)}, 'results': receipts,'dialogues':dialogues,
                    'context_after':app._get('shared_archive_seq',0)}

    def apply(self, action):
        app = self.app
        rid, task_id, kind = action.get('request_id'), action.get('task_id'), action.get('action')
        payload = action.get('payload')
        if kind == 'shared_queue':
            owner=app._get('queue_owner_id')
            if not owner or not isinstance(payload,dict): raise ValueError('Owner pairing required')
            digest=hashlib.sha256(json.dumps(action,sort_keys=True).encode()).hexdigest()
            with app.lock:
                prior=app.conn.execute('SELECT * FROM desktop_receipts WHERE request_id=?',(rid,)).fetchone()
                if prior:
                    if prior['content_hash']!=digest: raise ValueError('Receipt conflict')
                    return prior['status']
            try:
                source=payload.get('source','control_room_web')
                if source not in ('control_room_web','chatgpt'): raise ValueError('Invalid queue source')
                principal={'owner':owner,'runtime':source,'scopes':['create','read','list','update']+(['approve'] if source=='control_room_web' else [])}
                if payload.get('envelope'):
                    principal=app.queue.authenticate(payload['envelope'],json.loads(os.getenv('KIKI_QUEUE_CREDENTIALS','{}')))
                    if principal['owner']!=owner: raise ValueError('Owner mismatch')
                    command=payload['envelope']['command']
                else: command=payload['command']
                if command['request_id']!=rid: raise ValueError('Request identity mismatch')
                app.queue.dispatch(principal,command)
                status='applied'
            except (ValueError,KeyError,TypeError):
                status='failed'
            with app.lock,app.conn:
                app.conn.execute('INSERT INTO desktop_receipts(request_id,content_hash,status) VALUES(?,?,?)',(rid,digest,status))
            return status
        if kind=='chat':
            if app.agent:
                app.agent.enqueue(rid,payload.get('text'),'web',payload)
            return 'pending'
        if not isinstance(rid, str) or not 8 <= len(rid) <= 100 or not isinstance(task_id, str) or not re.fullmatch(r'task-[a-f0-9-]{36}', task_id) or not isinstance(payload, dict):
            raise ValueError('Invalid cloud action.')
        digest = hashlib.sha256(json.dumps(action, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with app.lock, app.conn:
            old = app.conn.execute('SELECT * FROM desktop_receipts WHERE request_id=?', (rid,)).fetchone()
            if old:
                if old['content_hash'] != digest:
                    raise ValueError('Receipt conflicts with changed action.')
                return old['status']
            status = 'applied'
            row = app.conn.execute('SELECT * FROM tasks WHERE sync_id=?', (task_id,)).fetchone()
            try:
                now = datetime.now(timezone.utc)
                if kind in ('create', 'import'):
                    title = payload.get('title')
                    limit = 500 if kind == 'import' else 200
                    if not isinstance(title, str) or not 1 <= len(title.strip()) <= limit:
                        raise ValueError('Invalid task title.')
                    if row and row['title'] != title.strip():
                        raise ValueError('Task identity conflict.')
                    if not row:
                        state = payload.get('status', 'open') if kind == 'import' else 'open'
                        if state not in ('open', 'done'):
                            raise ValueError('Invalid imported state.')
                        created = payload.get('created_at', now.isoformat()) if kind == 'import' else now.isoformat()
                        datetime.fromisoformat(created.replace('Z', '+00:00'))
                        until = payload.get('snoozed_until') if kind == 'import' else None
                        if until:
                            datetime.fromisoformat(until.replace('Z', '+00:00'))
                        app.conn.execute('INSERT INTO tasks(title,status,created_at,done_at,sync_id,snoozed_until) VALUES(?,?,?,?,?,?)',
                                         (title.strip(), state, created, now.isoformat() if state == 'done' else None, task_id, until))
                elif kind in ('complete', 'snooze', 'resume'):
                    if not row:
                        raise ValueError('Task no longer exists.')
                    if row['queue_json']:
                        raise ValueError('Use evidence-aware shared queue commands.')
                    if kind == 'complete':
                        app.conn.execute("UPDATE tasks SET status='done',done_at=COALESCE(done_at,?),snoozed_until=NULL WHERE sync_id=?", (now.isoformat(), task_id))
                    elif row['status'] != 'open':
                        raise ValueError('Completed task cannot be snoozed or resumed.')
                    else:
                        until = (now + timedelta(hours=1)).isoformat() if kind == 'snooze' else None
                        app.conn.execute('UPDATE tasks SET snoozed_until=? WHERE sync_id=?', (until, task_id))
                else:
                    raise ValueError('Unsupported task action.')
            except (ValueError, TypeError):
                status = 'failed'
            app.conn.execute('INSERT INTO desktop_receipts(request_id,content_hash,status) VALUES(?,?,?)', (rid, digest, status))
            return status

    def cycle(self, stop=None):
        body = self.snapshot()
        request = Request(self.url + '/api/desktop-sync', data=json.dumps(body).encode(),
                          headers={'Content-Type': 'application/json',
                                   'OAI-Sites-Authorization': 'Bearer ' + self.token,
                                   'X-Kiki-Sync-Key': self.key}, method='POST')
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
        if stop and stop.is_set():
            return
        if result.get('paired') is not True:
            with self.app.lock, self.app.conn:
                self.app._set('desktop_sync_status', 'waiting_for_owner')
            return
        if self.app.agent and 'context' in result:
            self.app.agent.remember_shared(result['context'])
        if self.app.agent and 'archive' in result:
            self.app.agent.remember_archive(result['archive'])
        with self.app.lock, self.app.conn:
            owner=result.get('owner_id')
            if isinstance(owner,str) and owner:
                prior=self.app._get('queue_owner_id')
                if prior and prior!=owner: raise ValueError('Queue owner mapping changed')
                self.app._set('queue_owner_id',owner)
            for rid in result.get('acknowledged', []):
                self.app.conn.execute('UPDATE desktop_receipts SET acknowledged=1 WHERE request_id=?', (rid,))
                if self.app.agent:
                    self.app.conn.execute('UPDATE agent_jobs SET cloud_ack=1 WHERE id=?',(rid,))
            self.app._set('desktop_sync_status', 'connected')
            self.app._set('desktop_sync_at', datetime.now(timezone.utc).isoformat())
        for action in result.get('actions', []):
            self.apply(action)

    def run(self, stop):
        while not stop.is_set():
            try:
                self.cycle(stop)
            except Exception:
                if stop.is_set():
                    return
                with self.app.lock, self.app.conn:
                    if not stop.is_set():
                        self.app._set('desktop_sync_status', 'offline')
                print('Kiki Site sync delayed; queued actions remain saved.', flush=True)
            stop.wait(15)
