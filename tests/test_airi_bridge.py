import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError

spec=importlib.util.spec_from_file_location('airi_bridge',Path(__file__).resolve().parents[1]/'runtime/airi/bridge.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Desktop:
    def __init__(self):self.active=True;self.idle=1;self.frames=0
    def available(self):return self.active
    def idle_seconds(self):return self.idle
    def capture(self):self.frames+=1;return 'PRIVATE_IMAGE_BYTES'
class Gateway:
    ready=True
    def __init__(self):self.sent=[]
    def send_initiative(self,e):self.sent.append(e);return True
class Transport:
    def __init__(self):self.calls=[];self.receipts={};self.offline=False;self.lose_ack=False;self.session={'revision':0,'objective':'','next_action':'','last_outcome':'','status':'idle'};self.tasks=[];self.task_snapshot_at=None
    def __call__(self,url,body=None,headers=None,timeout=None):
        self.calls.append((url,body,headers))
        if '/api/companion' in url:
            if self.offline:raise OSError('offline')
            if body['action']=='context':return {'events':[{'source':'chatgpt','content':{'text':'The cassette is purple.'}}],'session':self.session.copy(),'tasks':self.tasks,'task_snapshot_at':self.task_snapshot_at}
            if body['action']=='record':
                op=body['operation_id']
                if op in self.receipts and self.receipts[op]!=body:raise ValueError('conflict')
                self.receipts[op]=body.copy()
                if self.lose_ack:self.lose_ack=False;raise OSError('lost response after commit')
                return {'saved':True,'operation_id':op}
            if body['action']=='session':
                if body['revision']!=self.session['revision']:raise ValueError('stale')
                self.session={**body['session'],'revision':body['revision']+1};return self.session.copy()
        if url.endswith('/api/chat'):
            if body['model']=='vision':return {'message':{'content':'A document is open with one paragraph selected.'}}
            return {'message':{'content':'Totally. The cassette is purple.'}}
        return {'models':[{'name':'local-model'}]}

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.transport=Transport();self.desktop=Desktop();self.now=1792162800.0
        self.b=m.Bridge(self.temp.name,self.desktop,self.transport,lambda:self.now)
        self.b.save_config({'model':'local-model','device_token':'a'*64,'site_access_token':'PRIVATE_SITE_TOKEN','device_id':'device-test01'})
        self.body={'messages':[{'role':'system','content':'You are another character.'},{'role':'user','content':'What color is the cassette?'}]}
    def tearDown(self):self.b.store.db.close()
    def test_retrieval_and_exact_ledger_receipt(self):
        result=self.b.complete(self.body,'operation-test01');self.assertEqual(len(self.transport.receipts),1)
        receipt=self.transport.receipts[result['operation_id']];self.assertEqual(receipt['reply'],result['text']);self.assertEqual(receipt['model'],'ollama:local-model')
        inference=[c[1] for c in self.transport.calls if c[0].endswith('/api/chat')][0]
        self.assertIn('purple',inference['messages'][0]['content']);self.assertNotIn('another character',json.dumps(inference))
        self.assertEqual(self.b.complete(self.body,'operation-test01')['text'],result['text']);self.assertEqual(len(self.transport.receipts),1)
    def test_offline_outbox_restart_and_lost_ack(self):
        self.transport.lose_ack=True;result=self.b.complete(self.body,'operation-test02');self.assertEqual(len(self.b.store.pending()),1)
        self.b.store.db.close();self.b=m.Bridge(self.temp.name,self.desktop,self.transport,lambda:self.now)
        self.b.flush();self.assertEqual(len(self.b.store.pending()),0);self.assertEqual(len(self.transport.receipts),1)
        self.assertEqual(self.b.complete(self.body,'operation-test02')['text'],result['text'])
        calls=[c for c in self.transport.calls if c[0].endswith('/api/chat')];self.assertEqual(len(calls),1)
    def test_offline_generation_uses_cache_without_claiming_sync(self):
        self.b.refresh_context();self.transport.offline=True;self.b.complete(self.body,'operation-test03')
        self.assertEqual(len(self.b.store.pending()),1);self.assertEqual(self.b.sync_status,'offline')
    def test_frames_only_go_to_local_vision_and_not_receipts(self):
        self.b.save_config({'screen_enabled':True,'vision_model':'vision'});self.b.complete(self.body,'operation-test04')
        self.assertEqual(self.desktop.frames,1);self.assertNotIn('PRIVATE_IMAGE_BYTES',json.dumps(self.transport.receipts))
        for url,body,_ in self.transport.calls:
            if 'PRIVATE_IMAGE_BYTES' in json.dumps(body):self.assertEqual(url,'http://127.0.0.1:11434/api/chat')
    def test_pause_command_prevents_capture_and_persists_shared_place(self):
        self.b.save_config({'screen_enabled':True,'vision_model':'vision'})
        self.b.complete({'messages':[{'role':'user','content':'/focus Email | Read the first question'}]},'operation-focus1')
        self.b.complete({'messages':[{'role':'user','content':'/pause'}]},'operation-pause1')
        self.assertEqual(self.desktop.frames,0);self.assertEqual(self.transport.session['status'],'paused')
        self.assertEqual(self.transport.session['next_action'],'Read the first question')
    def test_locked_or_idle_screen_never_captured(self):
        self.b.save_config({'screen_enabled':True,'vision_model':'vision'});self.desktop.active=False;self.assertEqual(self.b.screen(),'')
        self.desktop.active=True;self.desktop.idle=10000;self.assertEqual(self.b.screen(),'');self.assertEqual(self.desktop.frames,0)
    def ready_scheduler(self):
        self.b.gateway=Gateway();self.b.store.set('provider_seen',True);self.b.save_config({'quiet_start':0,'quiet_end':0})
        self.b.last_input=self.b.last_output=self.now-4000
    def test_proactive_cooldown_unanswered_pause_and_provenance(self):
        self.ready_scheduler();self.assertTrue(self.b.tick());self.assertFalse(self.b.tick())
        entry=self.b.gateway.sent[0]
        body={'messages':[{'role':'system','content':entry['marker']},{'role':'user','content':'A scheduled Kiki check-in is due.'}]}
        self.b.complete(body);self.assertEqual(self.transport.receipts[entry['id']]['input_kind'],'proactive')
        body['messages'].append({'role':'user','content':'Thanks, what next?'})
        result=self.b.complete(body,'operation-human1');self.assertEqual(self.transport.receipts[result['operation_id']]['input_kind'],'user')
        self.assertEqual(self.b.unanswered,0)
        self.b.unanswered=2;self.now+=4000;self.assertFalse(self.b.tick())
        self.b.unanswered=0;self.b.store.set('snooze_until',self.now+1000);self.assertFalse(self.b.tick())
    def test_proactive_chooses_actual_task_and_avoids_raw_student_content(self):
        self.transport.tasks=[{'id':'pc-1','title':'Reply to Student Name Jane Doe about grade','status':'open','created_at':'2026-10-16T00:00:00Z'}]
        self.transport.task_snapshot_at=m.datetime.fromtimestamp(self.now,m.ZoneInfo('UTC')).isoformat()
        self.ready_scheduler()
        self.assertTrue(self.b.tick())
        reason=self.b.gateway.sent[0]['reason']
        self.assertIn('email-related task',reason)
        self.assertIn('open the relevant message',reason)
        self.assertNotIn('Jane Doe',reason)
        self.assertNotIn('grade',reason.lower())
        self.assertIn('recent PC task snapshot',reason)
        self.b.save_config({'screen_enabled':True,'vision_model':'vision'})
        entry=self.b.gateway.sent[0]
        body={'messages':[{'role':'system','content':entry['marker']},
                          {'role':'user','content':'A scheduled Kiki check-in is due.'}]}
        self.b.complete(body)
        request=[call[1] for call in self.transport.calls if call[0].endswith('/api/chat')][-1]
        self.assertNotIn('Jane Doe',json.dumps(request))
        self.assertNotIn('Student Name',json.dumps(request))
        self.assertEqual(self.desktop.frames,0)

    def test_proactive_skips_snoozed_and_completed_tasks(self):
        tasks=[{'id':'pc-1','title':'Open a confidential email','status':'done'},
               {'id':'pc-2','title':'Schedule faculty meeting','status':'open','snoozed_until':'2099-01-01T00:00:00Z'},
               {'id':'pc-3','title':'Canvas lecture preparation','status':'open'}]
        suggested=m.suggest_proactive_step({'tasks':tasks},self.now)
        self.assertEqual(suggested['category'],'university task')
        self.assertNotIn('faculty meeting',str(suggested))
    def test_proactive_uses_staleness_label_and_does_not_fabricate_urgent_tasks(self):
        self.transport.tasks=[{'id':'pc-7','title':'Research archive','status':'open'}]
        self.transport.task_snapshot_at='2026-10-01T00:00:00Z'
        self.ready_scheduler()
        self.assertTrue(self.b.tick())
        reason=self.b.gateway.sent[0]['reason']
        self.assertIn('previously synchronized PC task snapshot',reason)
        self.assertNotIn('deadline',reason.lower().replace('inferred deadlines',''))
        self.transport.tasks=[]
        self.assertIsNone(m.suggest_proactive_step({'tasks':[]},self.now))
    def test_quiet_hours_and_shared_pause_gate_initiation(self):
        self.ready_scheduler();hour=m.datetime.fromtimestamp(self.now,m.ZoneInfo('America/Chicago')).hour
        self.b.save_config({'quiet_start':hour,'quiet_end':(hour+1)%24});self.assertFalse(self.b.can_initiate())
        self.b.save_config({'quiet_start':0,'quiet_end':0});self.transport.session['status']='paused';self.assertFalse(self.b.tick())
    def test_conflicting_operation_does_not_regenerate_or_overwrite(self):
        self.b.complete(self.body,'operation-test05')
        with self.assertRaises(ValueError):self.b.complete({'messages':[{'role':'user','content':'Different'}]},'operation-test05')
    def test_remote_inference_and_wrong_site_rejected(self):
        with self.assertRaises(ValueError):self.b.save_config({'ollama_url':'https://external.example'})
        with self.assertRaises(ValueError):self.b.save_config({'site_url':'https://other.example'})
    def test_airi_gateway_v0102_superjson_auth_and_announce(self):
        gateway=m.AiriGateway(self.b)
        class Socket:
            def __init__(self):self.frames=[]
            def send(self,payload):self.frames.append(json.loads(payload)['json'])
        gateway.socket=Socket();gateway.receive(json.dumps({'json':{'type':'module:authenticated','data':{'authenticated':True}}}))
        self.assertEqual(gateway.socket.frames[0]['type'],'module:announce')
        gateway.receive(json.dumps({'json':{'type':'module:announced','data':{'identity':gateway.identity}}}))
        self.assertFalse(gateway.ready)
        gateway.receive(json.dumps({'json':{'type':'registry:modules:sync','data':{'modules':[{'name':'stage-tamagotchi'}]}}}))
        self.assertTrue(gateway.ready)
        self.assertTrue(gateway.send_initiative(self.b.new_initiative('A brief check-in.')))
        frame=gateway.socket.frames[-1];self.assertEqual(frame['type'],'input:text');self.assertIn('contextUpdates',frame['data'])
    def test_socket_integration_proxy_ollama_and_shared_api(self):
        transport=self.transport
        class Provider(m.BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_POST(self):
                a=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                target=m.SITE+'/api/companion' if self.path=='/api/companion' else 'http://127.0.0.1:11434'+self.path
                result=transport(target,a,dict(self.headers))
                data=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        provider=ThreadingHTTPServer(('127.0.0.1',0),Provider);threading.Thread(target=provider.serve_forever,daemon=True).start()
        self.addCleanup(provider.server_close);self.addCleanup(provider.shutdown)
        self.b.http=lambda url,body=None,headers=None,timeout=20:m.http_json('http://127.0.0.1:'+str(provider.server_port)+m.urlparse(url).path,body,headers,timeout)
        server=ThreadingHTTPServer(('127.0.0.1',0),m.Handler);server.bridge=self.b;threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        response=m.http_json('http://127.0.0.1:'+str(server.server_port)+'/v1/chat/completions',self.body,{'Authorization':'Bearer '+self.b.token})
        self.assertEqual(response['choices'][0]['message']['content'],'Totally. The cassette is purple.')
        self.assertEqual(len(transport.receipts),1);self.assertEqual(len(self.b.store.pending()),0)
    def test_failed_first_pairing_does_not_persist_unverified_credentials(self):
        self.b.config={**m.DEFAULTS}
        self.b.config_path.unlink()
        self.transport.offline=True
        server=ThreadingHTTPServer(('127.0.0.1',0),m.Handler);server.bridge=self.b
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        pairing={'site_url':m.SITE,'device_token':'b'*64,'site_access_token':'unverified','device_id':'new-device'}
        with self.assertRaises(HTTPError) as exc:
            m.http_json('http://127.0.0.1:'+str(server.server_port)+'/pair',pairing,{'Authorization':'Bearer '+self.b.token})
        self.assertEqual(exc.exception.code,400)
        self.assertNotIn('device_token',self.b.config)
        self.assertFalse(self.b.config_path.exists())
    def test_real_http_auth_and_sse_proxy(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),m.Handler);server.bridge=self.b
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        url='http://127.0.0.1:'+str(server.server_port)
        with self.assertRaises(HTTPError) as exc:urlopen(url+'/status')
        self.assertEqual(exc.exception.code,401)
        request=Request(url+'/v1/chat/completions',data=json.dumps({**self.body,'stream':True}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.b.token})
        with urlopen(request) as r:
            stream=r.read().decode();self.assertIn('data: [DONE]',stream);self.assertIn('chat.completion.chunk',stream);self.assertIn('cassette',stream)
        self.assertEqual(len(self.transport.receipts),1)

if __name__=='__main__':unittest.main()
