"""Actual loopback HTTP + file I/O + cold interpreter restart. NOT OpenClaw/OS reboot proof."""
import hashlib,hmac,json,os,subprocess,sys,threading,time,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'/'local'))
from kiki_local import Kiki,make_handler
from shared_queue import encoded
from queue_worker import cycle
from queue_adapter import VERSION

def run(output):
 output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
 root=output/('http-acceptance-'+str(uuid.uuid4()));root.mkdir()
 path=root/'synthetic.sqlite3'
 runtime='acceptance_http_adapter'
 config={'owner':'synthetic-owner','key':uuid.uuid4().hex+uuid.uuid4().hex,'scopes':['create','read','approve','register','claim','finish'],
         'capabilities':['local.file.write'],'adapter_version':VERSION}
 previous=os.environ.get('KIKI_QUEUE_CREDENTIALS');os.environ['KIKI_QUEUE_CREDENTIALS']=json.dumps({runtime:config})
 app=Kiki(path);server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 def call(command):
  envelope={'runtime':runtime,'timestamp':time.time(),'nonce':str(uuid.uuid4()),'command':command}
  envelope['signature']=hmac.new(config['key'].encode(),encoded(envelope).encode(),hashlib.sha256).hexdigest()
  request=Request('http://127.0.0.1:'+str(server.server_port)+'/api/shared-queue',data=json.dumps(envelope).encode(),headers={'Content-Type':'application/json'})
  with urlopen(request,timeout=5) as r:return json.load(r)
 try:
  command={'op':'create','request_id':'http-create-test','task':{'intent':'Synthetic HTTP acceptance','next_step':'Write and read KIKI_OK',
      'origin':{'source':'acceptance_http','receipt':'http-create-test'},'required_capabilities':['local.file.write'],
      'privacy':'synthetic','authorization':'approved','status':'QUEUED','effect':'sandbox_file',
      'payload':{'content':'KIKI_OK'},'idempotency_key':'http-acceptance'}}
  task=call(command);assert call(command)['id']==task['id']
  result=cycle(app,config,runtime,root)
  read=call({'op':'read','request_id':'http-independent-read','id':task['id']})['tasks'][0]
  assert read['status']=='VERIFIED' and read['evidence']==result['evidence']
  assert (root/(task['id']+'.txt')).read_text()=='KIKI_OK'
 finally:
  server.shutdown();server.server_close();thread.join();app.close()
  if previous is None:os.environ.pop('KIKI_QUEUE_CREDENTIALS',None)
  else:os.environ['KIKI_QUEUE_CREDENTIALS']=previous
 code="import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from kiki_local import Kiki;a=Kiki(sys.argv[2]);print(json.dumps(a.queue.projection('synthetic-owner')));a.close()"
 cold=json.loads(subprocess.check_output([sys.executable,'-c',code,str(Path(__file__).resolve().parents[1]/'runtime'/'local'),str(path)],text=True))
 assert cold['tasks'][0]['evidence']==read['evidence']
 report={'task_id':task['id'],'provider_receipt':read['evidence']['provider_receipt'],'sha256':hashlib.sha256((root/(task['id']+'.txt')).read_bytes()).hexdigest(),
         'verified':['signed_loopback_http_create','duplicate_http_submission','actual_sandbox_write','independent_file_and_http_readback','cold_python_process_recovery'],
         'not_verified':['ChatGPT_tool_creation','hosted_website_read','OpenClaw_gateway_execution','Windows_reboot','Jan_live_model'],
         'artifact':str(root/(task['id']+'.txt'))}
 (output/'http-acceptance.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))

if __name__=='__main__':run(sys.argv[1])
