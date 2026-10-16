import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createKikiToolService,KIKI_SITE_TOOL_DEFINITIONS} from '../lib/kiki-tools.mjs';
const sql = fs.readFileSync(new URL('../drizzle/0000_hard_umar.sql',import.meta.url),'utf8');
class D1 {
  constructor(){this.db=new DatabaseSync(':memory:');this.db.exec('PRAGMA foreign_keys=ON');this.db.exec(sql)}
  prepare(q){const db=this.db;return {bind(...args){return {async first(){return db.prepare(q).get(...args)||null},async all(){return {results:db.prepare(q).all(...args)}},async run(){return {meta:db.prepare(q).run(...args)}}}}}}
  async batch(stmts){this.db.exec('BEGIN');try{const ans=[];for(const p of stmts)ans.push(await p.run());this.db.exec('COMMIT');return ans}catch(e){this.db.exec('ROLLBACK');throw e}}
  close(){this.db.close()}
}
function fixture(){const db=new D1;return {db,s:createKikiToolService(db),u:{ownerId:'owner-00001'},v:{ownerId:'owner-00002'}}}
test('tool specification separates reads and writes',()=>{assert.deepEqual(KIKI_SITE_TOOL_DEFINITIONS.map(x=>x.name),['kiki_get_brief','kiki_get_history','kiki_prepare_turn','kiki_get_tasks','kiki_get_work_session','kiki_get_channel_status','kiki_commit_turn']);assert.equal(KIKI_SITE_TOOL_DEFINITIONS[0].readonly,true)});
test('prepare and commit create source-attributed historical receipts',async()=>{const {db,s,u}=fixture();try{const p=await s.prepareTurn(u,{text:'The cassette is purple.',retry_key:'request-0001'});const q=await s.commitTurn(u,{turn_id:p.turn_id,text:'Purple cassette. Got it.'});assert.ok(q.assistant_event_id);const h=await s.getHistory(u,{thread_id:p.thread_id});assert.equal(h.events.length,2);assert.deepEqual(h.events.map(x=>x.source),['chatgpt','chatgpt']);assert.equal(h.events[1].provenance.host_display_confirmed,false);assert.equal((await s.getBrief(u)).pending_turns,0)}finally{db.close()}});
test('idempotent retries do not change prior messages',async()=>{const {db,s,u}=fixture();try{const p=await s.prepareTurn(u,{text:'Hello',retry_key:'request-0002'});const p2=await s.prepareTurn(u,{text:'Hello',retry_key:'request-0002'});assert.equal(p2.reused,true);assert.equal(p.turn_id,p2.turn_id);await assert.rejects(s.prepareTurn(u,{text:'Not Hello',retry_key:'request-0002'}),/different/);const c=await s.commitTurn(u,{turn_id:p.turn_id,text:'Hi'});const c2=await s.commitTurn(u,{turn_id:p.turn_id,text:'Hi'});assert.equal(c2.reused,true);assert.equal(c.assistant_event_id,c2.assistant_event_id);await assert.rejects(s.commitTurn(u,{turn_id:p.turn_id,text:'Different'}),/different/);assert.equal(db.db.prepare('SELECT count(*) AS n FROM interaction_events').get().n,2)}finally{db.close()}});
test('ownership forbids cross-account reading and mutation',async()=>{const {db,s,u,v}=fixture();try{const p=await s.prepareTurn(u,{text:'Secret',retry_key:'request-0003',thread_id:'thread-private01'});await assert.rejects(s.getHistory(v,{thread_id:p.thread_id}),/not found/);await assert.rejects(s.commitTurn(v,{turn_id:p.turn_id,text:'Changed'}),/not found/);await assert.rejects(s.prepareTurn(v,{text:'Injection',retry_key:'request-0004',thread_id:p.thread_id}),/different/);assert.equal((await s.getBrief(v)).latest_events.length,0)}finally{db.close()}});
test('unverified identity, bounds, and cursors fail closed',async()=>{const {db,s,u}=fixture();try{await assert.rejects(s.getBrief({}),/verified/);await assert.rejects(s.prepareTurn(u,{text:'',retry_key:'request-0005'}),/6000/);await assert.rejects(s.prepareTurn(u,{text:'Hi',retry_key:'bad'}),/stable ID/);const a=await s.prepareTurn(u,{text:'First',retry_key:'request-0006'});await s.prepareTurn(u,{text:'Second',retry_key:'request-0007',thread_id:a.thread_id});assert.equal((await s.getBrief(u)).pending_turns,2);const first=await s.getHistory(u,{thread_id:a.thread_id,limit:1});const next=await s.getHistory(u,{thread_id:a.thread_id,after_seq:first.next_after_seq});assert.equal(first.events.length,1);assert.equal(next.events.length,1)}finally{db.close()}});

test('Site adapter rejects unverified sessions and forbidden owner spoofing',async()=>{
  const {db,u}=fixture();
  try{
    const {createSiteToolHandlers}=await import('../lib/site-tool-adapter.mjs');
    const toolset=createSiteToolHandlers({db,resolveVerifiedIdentity:async ctx=>ctx?.verified===true?u:null});
    const brief=toolset.find(x=>x.name==='kiki_get_brief');
    const prepare=toolset.find(x=>x.name==='kiki_prepare_turn');
    await assert.rejects(brief.invoke({arguments:{},requestContext:{ownerId:u.ownerId}}),/Not signed in/);
    await assert.rejects(prepare.invoke({arguments:{text:'Hi',retry_key:'request-0011',ownerId:u.ownerId},requestContext:{verified:true}}),/Unexpected tool arguments/);
    const result=await prepare.invoke({arguments:{text:'Hi',retry_key:'request-0011'},requestContext:{verified:true}});
    assert.ok(result.user_event_id);
    assert.equal(result.tool,'kiki_prepare_turn');
  }finally{db.close()}
});

test('web and MCP share one history with accurate sources',async()=>{const {db,s,u}=fixture();try{const web=createKikiToolService(db,'kiki_web');const p=await web.prepareTurn(u,{text:'Synthetic continuity fact',retry_key:'request-web01'});const q=await s.getHistory(u,{thread_id:p.thread_id});assert.equal(q.events[0].source,'kiki_web');assert.equal(q.events[0].provenance.source_channel,'kiki_web');await s.commitTurn(u,{turn_id:p.turn_id,text:'Committed plugin reply'});const h=await web.getHistory(u,{thread_id:p.thread_id});assert.equal(h.events[1].source,'chatgpt')}finally{db.close()}});
test('two accounts can use the same retry key without collisions',async()=>{const {db,s,u,v}=fixture();try{await s.prepareTurn(u,{text:'A',retry_key:'request-same1'});await s.prepareTurn(v,{text:'B',retry_key:'request-same1'});assert.equal((await s.getBrief(u)).latest_events[0].content.text,'A');assert.equal((await s.getBrief(v)).latest_events[0].content.text,'B')}finally{db.close()}});
test('partial writes roll back and original events cannot change',async()=>{const {db,s,u}=fixture();try{db.db.exec("CREATE TRIGGER fail_turn BEFORE INSERT ON conversation_turns BEGIN SELECT RAISE(ABORT,'injected failure'); END;");await assert.rejects(s.prepareTurn(u,{text:'Fail',retry_key:'request-fail1'}),/injected/);assert.equal(db.db.prepare('SELECT COUNT(*) n FROM interaction_events').get().n,0);db.db.exec('DROP TRIGGER fail_turn');const p=await s.prepareTurn(u,{text:'Original',retry_key:'request-fail1'});assert.throws(()=>db.db.prepare('UPDATE interaction_events SET content_json=? WHERE event_id=?').run('{}',p.user_event_id),/append-only/)}finally{db.close()}});

test('character guidance accompanies context and preparation without inventing memory',async()=>{const {db,s,u}=fixture();try{const b=await s.getBrief(u);assert.equal(b.character.name,'K1-K1 (Kiki)');assert.equal(b.latest_events.length,0);assert.equal(b.character.capabilities.pc_task_sync,false);const p=await s.prepareTurn(u,{text:'Hello Kiki',retry_key:'request-voice1'});assert.equal(p.character.subject_id,'kiki');assert.equal((await s.getHistory(u,{thread_id:p.thread_id})).events[0].content.text,'Hello Kiki')}finally{db.close()}});

test('operational read tools are read-only and owner-scoped',async()=>{
 const {db,s,u,v}=fixture();try{
  db.db.prepare('INSERT INTO tasks(id,owner_id,title) VALUES(?,?,?)').run('task-a',u.ownerId,'Private email');
  db.db.prepare('INSERT INTO tasks(id,owner_id,title) VALUES(?,?,?)').run('task-b',v.ownerId,'Other person task');
  const a=await s.getTasks(u),b=await s.getTasks(v);
  assert.deepEqual(a.hosted_tasks.map(t=>t.title),['Private email']);
  assert.deepEqual(b.hosted_tasks.map(t=>t.title),['Other person task']);
  assert.equal(a.pc_snapshot,null);
  assert.match(a.pc_authority,/Local SQLite/);
  await assert.rejects(s.getTasks({}),/verified/);
  await assert.rejects(s.getTasks(u,{limit:101}),/limit/);
  assert.equal((await s.getWorkSession(u)).available,false);
  assert.ok(KIKI_SITE_TOOL_DEFINITIONS.filter(x=>x.name.startsWith('kiki_get_')).every(x=>x.readonly));
 }finally{db.close()}
});

test('work session and PC task replicas are never invented or confused with live status',async()=>{
 const {db,s,u,v}=fixture();try{
  db.db.exec("CREATE TABLE companion_sessions(owner_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,content_json TEXT NOT NULL,updated_at TEXT NOT NULL)");
  db.db.prepare('INSERT INTO companion_sessions VALUES(?,?,?,?)').run(u.ownerId,3,JSON.stringify({status:'paused',objective:'Draft reply',next_action:'Review greeting',last_outcome:'Draft saved'}),'2026-10-16T12:00:00Z');
  db.db.exec("CREATE TABLE desktop_sync(owner_id TEXT PRIMARY KEY,snapshot_json TEXT NOT NULL,last_seen TEXT NOT NULL)");
  db.db.prepare('INSERT INTO desktop_sync VALUES(?,?,?)').run(u.ownerId,JSON.stringify({tasks:[{id:'pc-1',title:'PC task'}]}),'2026-10-16T12:01:00Z');
  const session=await s.getWorkSession(u);
  assert.equal(session.revision,3);
  assert.equal(session.next_action,'Review greeting');
  const other=await s.getWorkSession(v);
  assert.equal(other.status,'idle');
  const a=await s.getTasks(u);
  assert.equal(a.pc_snapshot.tasks[0].title,'PC task');
  assert.equal(a.pc_snapshot.live_connection_verified,false);
  assert.equal((await s.getTasks(v)).pc_snapshot,null);
  const health=await s.getChannelStatus(u);
  assert.equal(health.live_connection_verification,'not_available');
  assert.ok(health.channels.some(c=>c.source==='pc_sync'&&c.live_connected===null));
  assert.ok(!(await s.getChannelStatus(v)).channels.some(c=>c.source==='pc_sync'));
 }finally{db.close()}
});

test('past channel events do not become invented online indicators',async()=>{
 const {db,s,u,v}=fixture();try{
  await s.prepareTurn(u,{text:'Recorded once',retry_key:'request-status1'});
  const a=await s.getChannelStatus(u),b=await s.getChannelStatus(v);
  assert.equal(a.hosted_ledger_available,true);
  assert.equal(a.channels.length,1);
  assert.equal(a.channels[0].source,'chatgpt');
  assert.equal(a.channels[0].live_connected,null);
  assert.equal(a.channels[0].evidence,'historical_event_only');
  assert.equal(b.channels.length,0);
 }finally{db.close()}
});
