import hashlib,hmac,json,sys,tempfile,threading,unittest,uuid
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'/'local'))
from kiki_local import Kiki
from shared_queue import SharedQueue,encoded
from queue_adapter import sandbox_file,jan_draft,DraftLease,VERSION
from desktop_sync import DesktopSync

class QueueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite'
  self.app=Kiki(self.path);self.now=10000.;self.q=SharedQueue(self.app,lambda:self.now)
  self.p={'owner':'owner-test','runtime':'openclaw-test','scopes':['create','approve','read','list','update','register','claim','heartbeat','finish'],'capabilities':['local.file.write'],'adapter_version':VERSION}
 def tearDown(self):self.app.close();self.tmp.cleanup()
 def call(self,op,**args):return self.q.dispatch(self.p,{'op':op,'request_id':str(uuid.uuid4()),**args})
 def create(self,**extra):
  return self.call('create',task={'intent':'Synthetic test','next_step':'Write KIKI_OK','origin':{'source':'chatgpt','thread':'synthetic-thread'},'privacy':'synthetic','required_capabilities':['local.file.write'],'authorization':'approved','status':'QUEUED','idempotency_key':str(uuid.uuid4()),'effect':'sandbox_file','payload':{'content':'KIKI_OK'},**extra})
 def register_cap(self,cap):
  with self.q.transaction() as db:r=self.q.event(db,self.p['owner'],None,self.p['runtime'],'TOOL_PROBE',{'capability':cap,'readback':'synthetic-test-probe'})
  return self.call('register',tested_capabilities=[cap],adapter_version=VERSION,probes={cap:r})
 def register(self):return self.register_cap('local.file.write')
 def claim(self):self.register();return self.call('claim')['task']
 def test_duplicate_and_conflicting_submission(self):
  t=self.create(idempotency_key='same-key');self.assertEqual(t['id'],self.create(idempotency_key='same-key')['id'])
  with self.assertRaisesRegex(ValueError,'conflict'):self.create(idempotency_key='same-key',intent='Different')
  self.assertEqual(1,self.app.conn.execute('SELECT COUNT(*) FROM tasks').fetchone()[0])
 def test_two_connection_claim_race(self):
  self.create();self.register();other=Kiki(self.path);q2=SharedQueue(other,lambda:self.now);results=[];errors=[]
  def run(q):
   try:results.append(q.dispatch(self.p,{'op':'claim','request_id':str(uuid.uuid4())}))
   except Exception as e:errors.append(e)
  ts=[threading.Thread(target=run,args=(q,)) for q in (self.q,q2)]
  for t in ts:t.start()
  for t in ts:t.join()
  other.close();self.assertFalse(errors);self.assertEqual(1,sum(r['task'] is not None for r in results))
 def test_expired_send_never_retries(self):
  self.create(effect='external');t=self.claim();self.now+=61;self.register()
  self.assertIsNone(self.call('claim')['task']);s=self.call('read',id=t['id'])['tasks'][0]
  self.assertEqual('BLOCKED',s['status']);self.assertEqual(1,s['attempts'])
 def test_stale_lease_and_version(self):
  self.create();t=self.claim()
  with self.assertRaisesRegex(ValueError,'Version'):self.call('heartbeat',id=t['id'],version=0,lease_token=t['lease']['token'])
  self.now+=61
  with self.assertRaises(ValueError):self.call('heartbeat',id=t['id'],version=t['version'],lease_token=t['lease']['token'])
 def test_offline_and_unavailable_connector(self):
  t=self.create(required_capabilities=['chatgpt.gmail.read'])
  with self.assertRaisesRegex(ValueError,'offline'):self.call('claim')
  self.register();self.assertIsNone(self.call('claim')['task']);self.assertIn('connected session',self.call('read',id=t['id'])['tasks'][0]['availability_reason'])
 def test_failed_verification_and_safety_denial(self):
  self.create();t=self.claim();args={'id':t['id'],'version':t['version'],'lease_token':t['lease']['token']}
  with self.assertRaisesRegex(ValueError,'readback'):self.call('finish',**args,status='VERIFIED',evidence={'provider_receipt':'model-says-done'})
  blocked=self.call('finish',**args,status='BLOCKED',evidence={'reason':'Platform safety denial','safety_denial':True})
  self.assertTrue(blocked['safety_denial']);self.assertIsNone(self.call('claim')['task'])
  with self.assertRaises(ValueError):self.call('update',id=t['id'],version=blocked['version'],status='QUEUED')
 def test_cross_owner_and_permissions(self):
  t=self.create();p={**self.p,'owner':'other-owner'}
  self.assertEqual([],self.q.dispatch(p,{'op':'list','request_id':'read-other'})['tasks'])
  with self.assertRaisesRegex(ValueError,'not found'):self.q.dispatch(p,{'op':'read','request_id':'read-other','id':t['id']})
  with self.assertRaisesRegex(ValueError,'authorized'):self.q.dispatch({**self.p,'scopes':['read']},{'op':'claim','request_id':'bad-claim'})
 def test_signed_credential_replay_and_forgery(self):
  config={self.p['runtime']:{**self.p,'key':'k'*32}}
  e={'runtime':self.p['runtime'],'timestamp':self.now,'nonce':'nonce-0001','command':{'op':'list','request_id':'signed-read'}}
  e['signature']=hmac.new(b'k'*32,encoded(e).encode(),hashlib.sha256).hexdigest()
  self.assertEqual(self.p['owner'],self.q.authenticate(e,config)['owner'])
  with self.assertRaises(Exception):self.q.authenticate(e,config)
  e['nonce']='forged'
  with self.assertRaisesRegex(ValueError,'authentication'):self.q.authenticate(e,config)
 def test_provider_receipt_survives_worker_restart_and_refresh(self):
  self.create();t=self.claim();result=sandbox_file(self.q,self.p,t,self.tmp.name)
  receipt=result['evidence']['provider_receipt'];self.assertEqual('VERIFIED',result['status'])
  self.app.close();self.app=Kiki(self.path);self.q=SharedQueue(self.app,lambda:self.now)
  for _ in range(3):self.assertEqual(receipt,self.call('read',id=t['id'])['tasks'][0]['evidence']['provider_receipt'])
  self.register();self.assertIsNone(self.call('claim')['task']);self.assertEqual(1,len(list(Path(self.tmp.name).glob('task-*.txt'))))
 def test_interrupted_file_is_not_overwritten(self):
  self.create();t=self.claim();p=Path(self.tmp.name)/(t['id']+'.txt');p.write_text('unexpected')
  with self.assertRaisesRegex(ValueError,'mismatch'):sandbox_file(self.q,self.p,t,self.tmp.name)
  self.assertEqual('unexpected',p.read_text())
 def test_legacy_completion_cannot_bypass_evidence(self):
  t=self.create();local=self.app.conn.execute('SELECT id FROM tasks WHERE sync_id=?',(t['id'],)).fetchone()[0]
  with self.assertRaises(ValueError):self.app.done(local)
 def test_pause_health_ttl_and_approval(self):
  self.create();self.register();self.app.pause(True);self.assertIsNone(self.call('claim')['task']);self.app.pause(False)
  self.now+=61
  with self.assertRaisesRegex(ValueError,'offline'):self.call('claim')
  with self.assertRaisesRegex(ValueError,'provisioned'):self.call('register',tested_capabilities=['gmail.send'],adapter_version=VERSION,probes={'gmail.send':'model says yes'})
 def test_jan_draft_records_drafted_and_never_sent(self):
  from types import SimpleNamespace
  from io import BytesIO
  self.p={**self.p,'runtime':'jan-test','capabilities':['local.draft.generate']}
  self.create(effect='draft',required_capabilities=['local.draft.generate'],payload={'prompt':'Draft a synthetic greeting'})
  self.register_cap('local.draft.generate')
  task=self.call('claim')['task']
  response=BytesIO(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'A synthetic local draft.'}}]}).encode())
  with patch('queue_adapter.urlopen',return_value=response) as transport:
   result=jan_draft(self.q,self.p,task,SimpleNamespace(url='http://127.0.0.1:18766',key='private-test-key'))
   self.assertEqual(1,transport.call_count)
  self.assertEqual('DRAFTED',result['evidence']['outcome'])
  self.assertEqual('DRAFTED',result['last_verified_step']['outcome'])
  self.assertNotIn('SENT',json.dumps(result))
 def test_relay_restart_after_commit_before_ack_is_idempotent(self):
  sync=DesktopSync(self.app,'https://test.chatgpt.site','t'*32,'s'*32)
  with self.app.conn:self.app._set('queue_owner_id',self.p['owner'])
  command={'op':'create','request_id':'relay-request','task':{'intent':'Relay test','next_step':'Review draft','origin':{'source':'control_room_web'},'privacy':'synthetic','authorization':'pending','idempotency_key':'relay-key'}}
  action={'request_id':'relay-request','action':'shared_queue','payload':{'command':command,'source':'control_room_web'}}
  self.assertEqual('applied',sync.apply(action));self.assertEqual('applied',sync.apply(action))
  snapshot=sync.snapshot();self.assertEqual(1,len(snapshot['snapshot']['shared_queue']['tasks']))
  self.assertIn('queue_result',snapshot['results'][0])
  command['task']['intent']='Changed'
  with self.assertRaisesRegex(ValueError,'conflict'):sync.apply(action)
 def test_model_prose_cannot_register_even_a_provisioned_capability(self):
  with self.assertRaisesRegex(ValueError,'executable'):self.call('register',tested_capabilities=['local.file.write'],adapter_version=VERSION,probes={'local.file.write':'I tested the tool, trust me'})
 def test_jan_slow_generation_can_renew_beyond_original_lease(self):
  from types import SimpleNamespace
  from io import BytesIO
  self.p={**self.p,'runtime':'jan-test','capabilities':['local.draft.generate']}
  self.create(effect='draft',required_capabilities=['local.draft.generate'],payload={'prompt':'Synthetic draft'})
  self.register_cap('local.draft.generate');task=self.call('claim')['task'];lease=DraftLease(self.q,self.p,task)
  original=task['lease']['until']
  for _ in range(2):self.now+=40;lease.heartbeat()
  self.assertGreater(self.now,original);self.assertGreater(lease.task['lease']['until'],self.now)
  response=BytesIO(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'A real-shaped draft'}}]}).encode())
  with patch('queue_adapter.urlopen',return_value=response):result=jan_draft(self.q,self.p,lease.task,SimpleNamespace(url='http://127.0.0.1:18766',key='test'))
  self.assertEqual('VERIFIED',result['status'])
 def test_jan_prompt_uses_kiki_and_attributed_context(self):
  from queue_adapter import draft_messages
  from types import SimpleNamespace
  task=self.create(effect='draft',payload={'prompt':'Use the synthetic Blue Lantern context'})
  agent=SimpleNamespace(context=lambda query:[{'source':'chatgpt','user':'Blue Lantern'}],task_context=lambda:{'tasks':[{'id':'prior-task','provider_receipt':'receipt-verified'}]})
  messages=draft_messages(agent,task)
  self.assertIn('K1-K1',messages[0]['content']);self.assertIn('untrusted data',messages[0]['content'])
  self.assertIn('Blue Lantern',messages[1]['content']);self.assertIn('receipt-verified',messages[1]['content'])
 def test_public_model_list_cannot_prove_inference_authorization(self):
  from queue_worker import cycle
  from types import SimpleNamespace
  from io import BytesIO
  from urllib.error import HTTPError
  task=self.create(effect='draft',required_capabilities=['local.draft.generate'],payload={'prompt':'Synthetic draft'})
  config={**self.p,'capabilities':['local.draft.generate']}
  responses=[BytesIO(b'{"data":[{"id":"kiki-jan"}]}'),HTTPError('http://127.0.0.1:18766',401,'Unauthorized',{},None)]
  with patch('urllib.request.urlopen',side_effect=responses):
   with self.assertRaises(HTTPError):cycle(self.app,config,'jan-test',agent=SimpleNamespace(url='http://127.0.0.1:18766',key='test'))
  self.assertEqual('QUEUED',self.call('read',id=task['id'])['tasks'][0]['status'])
  self.assertEqual(0,self.app.conn.execute('SELECT COUNT(*) FROM queue_runtimes').fetchone()[0])
 def test_failed_generation_blocks_the_same_task_without_retry_or_send(self):
  from queue_worker import cycle
  from types import SimpleNamespace
  from io import BytesIO
  self.create(effect='draft',required_capabilities=['local.draft.generate'],payload={'prompt':'Synthetic draft'})
  config={**self.p,'capabilities':['local.draft.generate']}
  responses=[BytesIO(b'{"data":[{"id":"kiki-jan"}]}'),BytesIO(b'{"choices":[{"message":{"content":"OK"}}]}')]
  with patch('urllib.request.urlopen',side_effect=responses),patch('queue_adapter.urlopen',side_effect=TimeoutError('private remote details')):
   result=cycle(self.app,config,'jan-test',agent=SimpleNamespace(url='http://127.0.0.1:18766',key='test'))
  self.assertEqual('BLOCKED',result['status']);self.assertEqual(1,result['attempts'])
  self.assertNotIn('private remote details',json.dumps(result))
  self.assertEqual(0,self.app.conn.execute("SELECT COUNT(*) FROM queue_events WHERE kind='VERIFIED'").fetchone()[0])
  self.assertEqual(0,self.app.conn.execute('SELECT COUNT(*) FROM outbox').fetchone()[0])
 def test_expired_file_claim_cannot_touch_disk(self):
  self.create();task=self.claim();self.now+=61
  with self.assertRaisesRegex(ValueError,'no adapter action'):sandbox_file(self.q,self.p,task,self.tmp.name)
  self.assertEqual([],list(Path(self.tmp.name).glob('task-*.txt')))
 def test_expired_jan_claim_cannot_contact_the_model(self):
  from types import SimpleNamespace
  self.p={**self.p,'runtime':'jan-test','capabilities':['local.draft.generate']}
  self.create(effect='draft',required_capabilities=['local.draft.generate'],payload={'prompt':'Synthetic draft'})
  self.register_cap('local.draft.generate');task=self.call('claim')['task'];self.now+=61
  with patch('queue_adapter.urlopen') as transport:
   with self.assertRaisesRegex(ValueError,'no adapter action'):jan_draft(self.q,self.p,task,SimpleNamespace())
   transport.assert_not_called()
 def test_adapter_uses_authoritative_payload_instead_of_modified_claim_copy(self):
  import copy
  self.create();task=self.claim();tampered=copy.deepcopy(task);tampered['payload']['content']='UNAUTHORIZED_CHANGED_CONTENT'
  result=sandbox_file(self.q,self.p,tampered,self.tmp.name)
  self.assertEqual('KIKI_OK',(Path(self.tmp.name)/(task['id']+'.txt')).read_text())
  self.assertEqual('VERIFIED',result['status'])
 def test_wrong_runtime_and_stale_version_cannot_start_file_execution(self):
  self.create();task=self.claim()
  for p,t in [({**self.p,'runtime':'another-runtime'},task),(self.p,{**task,'version':task['version']-1})]:
   with self.assertRaisesRegex(ValueError,'no adapter action'):sandbox_file(self.q,p,t,self.tmp.name)
  self.assertEqual([],list(Path(self.tmp.name).glob('task-*.txt')))
 def test_incomplete_empty_and_tool_call_drafts_never_get_readback_receipts(self):
  from types import SimpleNamespace
  from io import BytesIO
  self.p={**self.p,'runtime':'jan-test','capabilities':['local.draft.generate']}
  self.create(effect='draft',required_capabilities=['local.draft.generate'],payload={'prompt':'Synthetic draft'})
  self.register_cap('local.draft.generate');task=self.call('claim')['task']
  choices=[{'message':{'content':'Missing finish reason'}},
           {'finish_reason':'length','message':{'content':'Truncated draft'}},
           {'finish_reason':'stop','message':{'content':'   '}},
           {'finish_reason':'stop','message':{'content':'Tool attempt','tool_calls':[{'id':'unsupported'}]}}]
  for choice in choices:
   with patch('queue_adapter.urlopen',return_value=BytesIO(json.dumps({'choices':[choice]}).encode())):
    with self.assertRaises(ValueError):jan_draft(self.q,self.p,task,SimpleNamespace(url='http://127.0.0.1:18766',key='test'))
  self.assertEqual(0,self.app.conn.execute("SELECT COUNT(*) FROM queue_events WHERE kind IN ('READBACK','VERIFIED')").fetchone()[0])

if __name__=='__main__':unittest.main()
