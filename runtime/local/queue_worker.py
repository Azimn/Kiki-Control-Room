"""One bounded work cycle invoked by the existing OpenClaw/Jan runtime.

Never starts Telegram polling or another scheduler. Requires an operator-issued
runtime credential in KIKI_QUEUE_CREDENTIALS and an existing sandbox directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import uuid
from kiki_local import Kiki
from queue_adapter import VERSION, sandbox_file, jan_draft


def cycle(app, config, runtime, sandbox=None, agent=None):
    capability='local.file.write' if sandbox is not None else 'local.draft.generate'
    if config.get('adapter_version')!=VERSION or config.get('capabilities')!=[capability]:
        raise ValueError('Provision exactly the bounded adapter capability and version')
    p={'owner':config['owner'],'runtime':runtime,'scopes':config['scopes'],
       'capabilities':config['capabilities'],'adapter_version':VERSION}
    if sandbox is not None:
        root=Path(sandbox).resolve(strict=True)
        probe=root/('probe-'+str(uuid.uuid4()))
        try:
            probe.write_text('KIKI_PROBE',encoding='utf-8')
            if probe.read_text(encoding='utf-8')!='KIKI_PROBE': raise ValueError('File probe failed')
            proof=hashlib.sha256(probe.read_bytes()).hexdigest()
        finally:
            if probe.exists(): probe.unlink()
    else:
        if agent is None: raise ValueError('Jan model unavailable')
        from urllib.request import Request,urlopen
        with urlopen(Request(agent.url+'/v1/models',headers={'Authorization':'Bearer '+agent.key}),timeout=5) as r:
            models=json.load(r)
        if not models.get('data'): raise ValueError('No model available')
        proof='model-list:'+hashlib.sha256(json.dumps(models,sort_keys=True).encode()).hexdigest()
    with app.queue.transaction() as db:
        probe_receipt=app.queue.event(db,p['owner'],None,runtime,'TOOL_PROBE',{'capability':capability,'readback':proof,'adapter_version':VERSION})
    app.queue.dispatch(p,{'op':'register','request_id':'probe-'+str(uuid.uuid4()),'tested_capabilities':[capability],
                         'adapter_version':VERSION,'probes':{capability:probe_receipt},'ttl':60})
    result=app.queue.dispatch(p,{'op':'claim','request_id':'claim-'+str(uuid.uuid4())})
    task=result['task']
    if task:
        result=sandbox_file(app.queue,p,task,sandbox) if sandbox is not None else jan_draft(app.queue,p,task,agent)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default=str(Path.home()/'.kiki'/'control-room.sqlite3'))
    parser.add_argument('--runtime',required=True)
    parser.add_argument('--sandbox')
    args=parser.parse_args()
    config=json.loads(os.environ['KIKI_QUEUE_CREDENTIALS'])[args.runtime]
    app=Kiki(args.db)
    try:
        agent=None
        if args.sandbox is None:
            from jan_agent import JanAgent
            agent=JanAgent(app,os.environ['KIKI_MODEL_KEY'])
        result=cycle(app,config,args.runtime,args.sandbox,agent)
        print(json.dumps({'status':result.get('status'),'task_id':result.get('id'),
                          'evidence':result.get('evidence'),'reason':result.get('reason')}))
    finally: app.close()
