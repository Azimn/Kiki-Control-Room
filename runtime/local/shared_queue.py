"""One task authority: additive metadata on the existing SQLite tasks table.

Only authenticated adapters call dispatch. Model text is never execution evidence.
"""
import hashlib
import hmac
import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


STATES = {'PROPOSED','NEEDS_DETAIL','QUEUED','CLAIMED','AWAITING_APPROVAL',
          'BLOCKED','VERIFIED','FAILED','CANCELLED'}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def text(value, limit=1000):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError('Invalid bounded text')
    return value


class SharedQueue:
    def __init__(self, app, clock=time.time):
        self.app, self.clock = app, clock
        with app.lock, app.conn:
            cols = {r[1] for r in app.conn.execute('PRAGMA table_info(tasks)')}
            if 'queue_json' not in cols:
                app.conn.execute('ALTER TABLE tasks ADD COLUMN queue_json TEXT')
            app.conn.executescript('''
              CREATE TABLE IF NOT EXISTS queue_events(
                seq INTEGER PRIMARY KEY, receipt_id TEXT UNIQUE NOT NULL,
                owner TEXT NOT NULL, task_id TEXT, actor TEXT NOT NULL,
                kind TEXT NOT NULL, detail TEXT NOT NULL, at REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS queue_requests(
                owner TEXT NOT NULL, request_id TEXT NOT NULL, digest TEXT NOT NULL,
                result TEXT NOT NULL, PRIMARY KEY(owner,request_id));
              CREATE TABLE IF NOT EXISTS queue_runtimes(
                owner TEXT NOT NULL, runtime TEXT NOT NULL, data TEXT NOT NULL,
                PRIMARY KEY(owner,runtime));
              CREATE TABLE IF NOT EXISTS queue_nonces(
                runtime TEXT NOT NULL, nonce TEXT NOT NULL, at REAL NOT NULL,
                PRIMARY KEY(runtime,nonce));
            ''')

    @contextmanager
    def transaction(self):
        with self.app.lock:
            self.app.conn.execute('BEGIN IMMEDIATE')
            try:
                yield self.app.conn
                self.app.conn.commit()
            except BaseException:
                self.app.conn.rollback()
                raise

    def event(self, db, owner, task, actor, kind, detail):
        receipt = 'receipt-' + str(uuid.uuid4())
        db.execute('INSERT INTO queue_events(receipt_id,owner,task_id,actor,kind,detail,at) VALUES(?,?,?,?,?,?,?)',
                   (receipt,owner,task,actor,kind,encoded(detail),self.clock()))
        return receipt

    def rows(self, db, owner):
        return [json.loads(r[0]) for r in db.execute('SELECT queue_json FROM tasks WHERE queue_json IS NOT NULL')
                if json.loads(r[0])['owner'] == owner]

    def get(self, db, owner, ident):
        row = db.execute('SELECT queue_json FROM tasks WHERE sync_id=?', (ident,)).fetchone()
        if not row or not row[0] or json.loads(row[0])['owner'] != owner:
            raise ValueError('Task not found')
        return json.loads(row[0])

    def save(self, db, task):
        db.execute('UPDATE tasks SET queue_json=?,status=? WHERE sync_id=?',
                   (encoded(task),'done' if task['status'] in ('VERIFIED','CANCELLED') else 'open',task['id']))

    def authenticate(self, envelope, credentials):
        """Per-runtime HMAC keys supplied privately by the operator; never model supplied."""
        runtime = envelope.get('runtime')
        config = credentials.get(runtime)
        if not config or len(config.get('key','')) < 32:
            raise ValueError('Runtime authentication required')
        stamp, nonce = envelope.get('timestamp'), envelope.get('nonce')
        if type(stamp) not in (int,float) or abs(self.clock()-stamp)>60:
            raise ValueError('Expired signature')
        text(nonce,100)
        unsigned = {k:v for k,v in envelope.items() if k != 'signature'}
        expected = hmac.new(config['key'].encode(),encoded(unsigned).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,str(envelope.get('signature',''))):
            raise ValueError('Runtime authentication required')
        with self.transaction() as db:
            db.execute('DELETE FROM queue_nonces WHERE at<?',(self.clock()-120,))
            db.execute('INSERT INTO queue_nonces VALUES(?,?,?)',(runtime,nonce,self.clock()))
            count=db.execute('SELECT COUNT(*) FROM queue_nonces WHERE runtime=? AND at>?',(runtime,self.clock()-60)).fetchone()[0]
            if count>60:
                raise ValueError('Runtime rate limit')
        return {'owner':config['owner'],'runtime':runtime,'scopes':config.get('scopes',[]),
                'capabilities':config.get('capabilities',[]),'adapter_version':config.get('adapter_version','')}

    def dispatch(self, principal, command):
        owner, actor = text(principal['owner'],128), text(principal['runtime'],128)
        op = command.get('op')
        if op not in principal['scopes']:
            raise ValueError('Operation not authorized')
        request = text(command.get('request_id'),256)
        digest = hashlib.sha256(encoded({'actor':actor,'command':command}).encode()).hexdigest()
        with self.transaction() as db:
            old=db.execute('SELECT digest,result FROM queue_requests WHERE owner=? AND request_id=?',(owner,request)).fetchone() if op not in ('read','list') else None
            if old:
                if old[0]!=digest: raise ValueError('Idempotency conflict')
                # A cached claim is never refreshed or re-executed by a retry.
                return json.loads(old[1])
            result = self._dispatch(db,principal,command)
            if op not in ('read','list'):
                self.event(db,owner,command.get('id'),actor,'api.'+op,{'request_id':request})
            if op not in ('read','list'):
                db.execute('INSERT INTO queue_requests VALUES(?,?,?,?)',(owner,request,digest,encoded(result)))
            return result

    def _dispatch(self, db, p, a):
        owner, actor, now, op=p['owner'],p['runtime'],self.clock(),a['op']
        if op=='create':
            body=a['task']
            if not isinstance(body,dict): raise ValueError('Task object required')
            title=text(body.get('intent'),500)
            origin=body.get('origin')
            if not isinstance(origin,dict) or set(origin)-{'source','thread','receipt'}:
                raise ValueError('Source attribution required')
            text(origin.get('source'),80)
            for v in origin.values(): text(v,200)
            required=body.get('required_capabilities',[])
            if not isinstance(required,list) or len(required)>16: raise ValueError('Invalid capabilities')
            for cap in required: text(cap,100)
            privacy=body.get('privacy','private')
            if privacy not in ('synthetic','private'): raise ValueError('Protected/student data unsupported')
            auth=body.get('authorization','pending')
            if auth not in ('pending','approved'): raise ValueError('Invalid authorization')
            if auth=='approved' and 'approve' not in p['scopes']: raise ValueError('Approval required')
            idem=text(body.get('idempotency_key'),128)
            for t in self.rows(db,owner):
                if t['idempotency_key']==idem:
                    if t['submission_hash']!=hashlib.sha256(encoded(body).encode()).hexdigest(): raise ValueError('Idempotency conflict')
                    return t
            zone=body.get('timezone','America/Chicago'); ZoneInfo(zone)
            deadline=body.get('deadline')
            if deadline is not None:
                d=datetime.fromisoformat(text(deadline,60).replace('Z','+00:00'))
                if d.utcoffset() is None: raise ValueError('Timezone-aware deadline required')
                deadline=d.astimezone(timezone.utc).isoformat()
            priority=body.get('priority',0)
            if type(priority)!=int or not -10<=priority<=10: raise ValueError('Invalid priority')
            prerequisites=body.get('prerequisites',[])
            if not isinstance(prerequisites,list) or len(prerequisites)>16: raise ValueError('Invalid prerequisites')
            for ident in prerequisites: self.get(db,owner,ident)
            state=body.get('status','PROPOSED')
            if state not in ('PROPOSED','NEEDS_DETAIL','QUEUED','AWAITING_APPROVAL'): raise ValueError('Invalid initial status')
            if state=='QUEUED' and auth!='approved': state='AWAITING_APPROVAL'
            if state=='QUEUED' and not required: state='NEEDS_DETAIL'
            task={'id':'task-'+str(uuid.uuid4()),'owner':owner,'intent':title,'origin':origin,
                  'next_step':text(body.get('next_step'),500),'required_capabilities':required,
                  'prerequisites':prerequisites,'privacy':privacy,'authorization':auth,
                  'priority':priority,'deadline':deadline,'timezone':zone,'idempotency_key':idem,
                  'status':state,'version':1,'attempts':0,'lease':None,'last_verified_step':None,
                  'evidence':None,'blocked_reason':None,'created_at':now,
                  'effect':body.get('effect','external'),'payload':body.get('payload',{}),
                  'submission_hash':hashlib.sha256(encoded(body).encode()).hexdigest()}
            if task['effect'] not in ('sandbox_file','draft','external'): raise ValueError('Invalid effect')
            if not isinstance(task['payload'],dict) or len(encoded(task['payload']))>4000: raise ValueError('Invalid payload')
            db.execute('INSERT INTO tasks(title,status,created_at,sync_id,queue_json) VALUES(?,?,?,?,?)',
                       (title,'open',datetime.now(timezone.utc).isoformat(),task['id'],encoded(task)))
            self.event(db,owner,task['id'],actor,'CREATED',{'origin':origin})
            return task
        if op=='register':
            caps=a.get('tested_capabilities',[])
            if not isinstance(caps,list) or not set(caps)<=set(p.get('capabilities',[])): raise ValueError('Capability not provisioned')
            if not p.get('adapter_version') or a.get('adapter_version')!=p['adapter_version']: raise ValueError('Adapter version mismatch')
            probes=a.get('probes',{})
            if not isinstance(probes,dict) or any(not isinstance(probes.get(c),str) or not probes[c] for c in caps): raise ValueError('Tool probe receipts required')
            for cap in caps:
                row=db.execute("SELECT detail,at FROM queue_events WHERE receipt_id=? AND owner=? AND actor=? AND kind='TOOL_PROBE'",(probes[cap],owner,actor)).fetchone()
                if not row or row['at']<now-60 or json.loads(row['detail']).get('capability')!=cap:
                    raise ValueError('Trusted recent executable tool probe required; model prose is not proof')
            ttl=a.get('ttl',60)
            if type(ttl)!=int or not 15<=ttl<=300: raise ValueError('Invalid health TTL')
            data={'runtime':actor,'expires':now+ttl,'capabilities':caps,'permission_scope':p.get('capabilities',[]),
                  'adapter_version':p['adapter_version'],'probes':probes}
            db.execute('INSERT INTO queue_runtimes VALUES(?,?,?) ON CONFLICT(owner,runtime) DO UPDATE SET data=excluded.data',(owner,actor,encoded(data)))
            return data
        self.recover(db,owner,now)
        if op in ('list','read'):
            tasks=[self.get(db,owner,a['id'])] if op=='read' else self.rows(db,owner)
            runtimes=[json.loads(r[0]) for r in db.execute('SELECT data FROM queue_runtimes WHERE owner=?',(owner,))]
            for t in tasks:
                t['eligible_runtimes']=[r['runtime'] for r in runtimes if r['expires']>now and set(t['required_capabilities'])<=set(r['capabilities'])]
                t['availability_reason']=None if t['eligible_runtimes'] else 'No tested, authorized runtime online; connector requires a real connected session.'
                t['events']=[dict(r) for r in db.execute('SELECT receipt_id,actor,kind,detail,at FROM queue_events WHERE owner=? AND task_id=? ORDER BY seq',(owner,t['id']))]
            return {'tasks':tasks,'runtimes':runtimes,'authority':'windows_sqlite'}
        if op=='claim':
            row=db.execute('SELECT data FROM queue_runtimes WHERE owner=? AND runtime=?',(owner,actor)).fetchone()
            runtime=json.loads(row[0]) if row else None
            if not runtime or runtime['expires']<=now: raise ValueError('Runtime offline; probe tools first')
            if self.app._get('paused',False): return {'task':None,'reason':'Paused'}
            tasks=sorted(self.rows(db,owner),key=lambda t:(-t['priority'],t['deadline'] or '9999',t['created_at']))
            for t in tasks:
                if a.get('id') and t['id']!=a['id']: continue
                if t['status']!='QUEUED' or t['authorization']!='approved' or not t['required_capabilities']: continue
                if not set(t['required_capabilities'])<=set(runtime['capabilities']): continue
                if any(self.get(db,owner,i)['status']!='VERIFIED' for i in t['prerequisites']): continue
                t.update(status='CLAIMED',attempts=t['attempts']+1,version=t['version']+1,
                         lease={'runtime':actor,'token':str(uuid.uuid4()),'until':now+60})
                self.save(db,t); self.event(db,owner,t['id'],actor,'CLAIMED',{'attempt':t['attempts']})
                return {'task':t}
            return {'task':None,'reason':'No eligible authorized step'}
        t=self.get(db,owner,a.get('id'))
        if type(a.get('version'))!=int or t['version']!=a['version']: raise ValueError('Version conflict; reload')
        if op=='update':
            state=a.get('status',t['status'])
            if t['status'] not in ('PROPOSED','NEEDS_DETAIL','AWAITING_APPROVAL','QUEUED') or state not in ('NEEDS_DETAIL','QUEUED','AWAITING_APPROVAL','CANCELLED'): raise ValueError('State requires execution evidence or reconciliation')
            if a.get('authorization')=='approved':
                if 'approve' not in p['scopes']: raise ValueError('Approval required')
                t['authorization']='approved'
                self.event(db,owner,t['id'],actor,'APPROVED',{'request_id':a['request_id']})
            if state=='QUEUED' and t['authorization']!='approved': raise ValueError('Approval required')
            if 'required_capabilities' in a:
                caps=a['required_capabilities']
                if not isinstance(caps,list) or len(caps)>16: raise ValueError('Invalid capabilities')
                for cap in caps:text(cap,100)
                t['required_capabilities']=caps
            if state=='QUEUED' and not t['required_capabilities']: raise ValueError('Required capability needs detail')
            if 'next_step' in a: t['next_step']=text(a['next_step'],500)
            t['status']=state
        elif op in ('heartbeat','finish'):
            lease=t['lease']
            if t['status']!='CLAIMED' or not lease or lease['runtime']!=actor or lease['token']!=a.get('lease_token') or lease['until']<=now: raise ValueError('Expired or mismatched claim')
            if op=='heartbeat': lease['until']=now+60
            else:
                state=a.get('status'); evidence=a.get('evidence')
                if state not in ('VERIFIED','BLOCKED','FAILED') or not isinstance(evidence,dict): raise ValueError('Outcome evidence required')
                if state=='VERIFIED':
                    # Independent verifier artifacts are registered by executable adapters,
                    # not accepted as arbitrary text from a model or remote request.
                    receipt=text(evidence.get('provider_receipt'),128)
                    proof=db.execute("SELECT detail FROM queue_events WHERE owner=? AND task_id=? AND receipt_id=? AND kind='READBACK' AND actor=?",(owner,t['id'],receipt,actor)).fetchone()
                    if not proof: raise ValueError('Trusted independent readback receipt required')
                    verified=json.loads(proof[0])
                    if verified.get('attempt')!=t['attempts']: raise ValueError('Readback belongs to another attempt')
                    t['last_verified_step']=verified
                else:
                    t['blocked_reason']=text(evidence.get('reason'),500)
                    if evidence.get('safety_denial'): t['safety_denial']=True
                t.update(status=state,evidence=evidence,lease=None)
                self.event(db,owner,t['id'],actor,state,evidence)
        else: raise ValueError('Unsupported operation')
        t['version']+=1; self.save(db,t)
        return t

    def recover(self,db,owner,now):
        for t in self.rows(db,owner):
            if t['status']=='CLAIMED' and t['lease']['until']<=now:
                # Conservative for every effect: never automatically replay an uncertain action.
                t.update(status='BLOCKED',blocked_reason='Lease expired; reconcile provider/readback before retry',lease=None,version=t['version']+1)
                self.save(db,t); self.event(db,owner,t['id'],'recovery','INTERRUPTED',{'attempt':t['attempts']})

    def projection(self,owner):
        with self.transaction() as db:
            return self._dispatch(db,{'owner':owner,'runtime':'projection'},{'op':'list'})
