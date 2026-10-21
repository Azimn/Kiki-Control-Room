"""Opt-in live Jan draft check with synthetic data in an isolated SQLite DB.

Uses the existing private Windows model key without displaying or persisting it.
No Telegram, calendar, mail, production task DB, or model server is started.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'/'local'))
from kiki_local import Kiki
from jan_agent import JanAgent


def run(output,model_url):
    key=os.getenv('KIKI_MODEL_KEY')
    if not key and sys.platform=='win32':
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as registry:
            key=winreg.QueryValueEx(registry,'KIKI_MODEL_KEY')[0]
    if not key:raise ValueError('Existing private Jan credential unavailable')
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    root=output/('jan-live-'+str(uuid.uuid4()));root.mkdir()
    db=root/'synthetic.sqlite3';app=Kiki(db)
    try:
        with app.conn:app._set('queue_owner_id','synthetic-jan-owner')
        agent=JanAgent(app,key,url=model_url);app.agent=agent
        # Seed bounded, explicitly synthetic shared context, never private history.
        agent.remember_shared({'seq':1,'turns':[{'seq':1,'turn_id':'turn-synthetic-jan-001','source':'chatgpt',
            'user':'For the synthetic rehearsal, the project is called Blue Lantern.',
            'assistant':'Blue Lantern is the synthetic project name. No real message will be sent.',
            'at':'2026-10-19T10:00:00Z','job_id':None}]})
        prompt='Draft a two-sentence friendly update about our synthetic Blue Lantern project for review. Do not send anything.'
        agent.enqueue('jan-live-request-001',prompt,'desktop',{'thread_id':'thread-synthetic-jan-001'})
        job=app.conn.execute('SELECT * FROM agent_jobs WHERE id=?',('jan-live-request-001',)).fetchone()
        proposal=agent.interpret(prompt,agent.context(prompt))
        acknowledgement=agent.finish(job,proposal)
        task_id=app._get('jan_task_resume')['task_id']
        assert task_id in acknowledgement
        result=agent.service_shared_queue()
        if result.get('status')!='VERIFIED':raise ValueError('Live Jan did not verify a draft; inspect isolated task status')
        assert result['evidence']['outcome']=='DRAFTED'
        artifact=result['last_verified_step'];assert artifact['draft'].strip()
        assert artifact['origin']['receipt']=='jan-live-request-001'
        assert len(app.queue.projection('synthetic-jan-owner')['tasks'])==1
        before=app.conn.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]
        assert before==0
        receipt=result['evidence']['provider_receipt']
    finally:app.close()
    code="import sys,json;sys.path.insert(0,sys.argv[1]);from kiki_local import Kiki;from jan_agent import JanAgent;a=Kiki(sys.argv[2]);j=JanAgent(a,'synthetic-key-not-used-for-inference-000');print(json.dumps(j.task_context()));a.close()"
    recovered=json.loads(subprocess.check_output([sys.executable,'-c',code,str(Path(__file__).resolve().parents[1]/'runtime'/'local'),str(db)],text=True))
    assert recovered['resume']['task_id']==task_id
    restored=next(t for t in recovered['tasks'] if t['id']==task_id)
    assert restored['provider_receipt']==receipt and restored['outcome']=='DRAFTED'
    report={'task_id':task_id,'provider_receipt':receipt,'provider_response_id':artifact['provider_response_id'],
        'model':artifact['model'],'outcome':'DRAFTED','context_sha256':artifact['context_sha256'],
        'draft_sha256':hashlib.sha256(artifact['draft'].encode()).hexdigest(),
        'verified':['real_Jan_request_interpretation','real_authenticated_Jan_inference','one_SQLite_task','contextual_draft_persisted_and_read_back',
                    'no_outbox_or_send','same_task_and_receipt_after_cold_process_restart'],
        'not_verified':['cross_machine_transport','hosted_surface_create_and_read','production_Windows_activation','full_Windows_restart'],
        'transport':model_url,'draft':artifact['draft']}
    (root/'receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--model-url',default='http://127.0.0.1:18766',choices=['http://127.0.0.1:18766','http://127.0.0.1:18767'])
    args=parser.parse_args();run(args.output,args.model_url)
