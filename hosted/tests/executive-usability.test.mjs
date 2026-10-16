import test from "node:test";
import assert from "node:assert/strict";
import {DatabaseSync} from "node:sqlite";
import {playbookFor,nextAction,suggestWork,applySessionCommand} from "../lib/executive-support.mjs";
import {readExecutiveOffer,updateWorkSession} from "../lib/work-session.mjs";

class D1 {
  constructor(){this.db=new DatabaseSync(":memory:")}
  prepare(sql){const db=this.db;return {bind(...args){return {
    async first(){return db.prepare(sql).get(...args)||null},
    async all(){return {results:db.prepare(sql).all(...args)}},
    async run(){return {meta:db.prepare(sql).run(...args)}}
  }}}}
  async batch(statements) {
    this.db.exec("BEGIN");
    try{const out=[];for(const statement of statements)out.push(await statement.run());this.db.exec("COMMIT");return out}
    catch(e){this.db.exec("ROLLBACK");throw e}
  }
  close(){this.db.close()}
}
const owner={ownerId:"owner-11111"},other={ownerId:"owner-22222"};
const seed=[{id:"site-1",title:"Reply to email",status:"open",created_at:"2026-10-15T10:00:00Z"},
 {id:"site-2",title:"Prepare lecture notes",status:"open",created_at:"2026-10-15T11:00:00Z"}];
function fixture() {
 const db=new D1();
 let hosted=seed.map(x=>({...x})), pc=null;
 const tool={
  async getTasks(ctx){if(ctx.ownerId===other.ownerId)return {hosted_tasks:[{id:"other",title:"Private",status:"open"}],pc_snapshot:null};
   return {hosted_tasks:hosted,pc_snapshot:pc}
  },
  async getWorkSession(ctx){const exists=db.db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='companion_sessions'").get();
   if(!exists)return {available:false,status:"unavailable",revision:0};
   const row=db.db.prepare("SELECT revision,content_json,updated_at FROM companion_sessions WHERE owner_id=?").get(ctx.ownerId);
   return row?{available:true,...JSON.parse(row.content_json),revision:row.revision,updated_at:row.updated_at}:
    {available:true,status:"idle",revision:0}
  }
 };
 return {db,tool,setPc(value){pc=value},setTasks(value){hosted=value}};
}
function act(f,command,revision,op="work-test01",extra={}) {
 return updateWorkSession(f.db,owner,{command,revision,operation_id:op,...extra},f.tool);
}
test("Kiki selects a task without making the user choose or inventing urgency",()=>{
 const offer=suggestWork(seed);
 assert.equal(offer.title,"Reply to email");
 assert.equal(offer.source,"hosted");
 assert.match(offer.next_action,/approved email/);
 assert.equal("deadline" in offer,false);
 assert.equal("priority" in offer,false);
});
test("snoozed or completed tasks are excluded; empty queue is honest",()=>{
 const now=new Date("2026-10-16T12:00:00Z");
 assert.equal(suggestWork([{...seed[0],snoozed_until:"2026-10-17T12:00:00Z"}, {...seed[1],status:"done"}],null,now),null);
 assert.equal(suggestWork([{...seed[0],snoozed_until:"2026-10-15T12:00:00Z"}],null,now).title,seed[0].title);
});
test("PC snapshot is labeled with provenance and staleness instead of claiming live connection",()=>{
 const pc={tasks:[{id:"pc-7",title:"Canvas grading",status:"open"}],observed_at:"2026-10-15T11:00:00Z"};
 const offer=suggestWork(seed,pc,new Date("2026-10-16T12:00:00Z"));
 assert.equal(offer.source,"pc_snapshot");
 assert.equal(offer.snapshot_is_recent,false);
 assert.equal(offer.task_id,"pc-7");
});
test("category-specific first steps are concrete and do not fabricate student information",()=>{
 assert.equal(playbookFor("Canvas grading"),"course");
 assert.equal(playbookFor("Schedule faculty meeting"),"meeting");
 assert.equal(playbookFor("Email Outlook"),"email");
 assert.match(nextAction("Canvas grading"),/Open the relevant course/);
 assert.doesNotMatch(nextAction("Canvas grading"),/student name|grade value/i);
});
test("small-step progression needs no replanning and never implies a sent email",()=>{
 let state=applySessionCommand(null,"begin",suggestWork(seed));
 for(let n=0;n<3;n++){
  const prev=state.next_action;state=applySessionCommand(state,"step");
  assert.notEqual(state.next_action,prev);
  assert.match(state.last_outcome,/not independently verified/);
 }
 assert.throws(()=>applySessionCommand(state,"step"),/No further/);
 assert.equal(state.status,"active");
});
test("one-tap offer deferral keeps the selected next action and suppresses another offer",async()=>{
 const f=fixture();try{
  const s=await act(f,"defer_offer",0,"work-defer1",{task_id:"site-1"});
  assert.equal(s.status,"paused");
  assert.match(s.next_action,/approved email/);
  const proposed=await readExecutiveOffer(f.db,owner,f.tool);
  assert.equal(proposed.offer,null);
  assert.equal(proposed.session.status,"paused");
 }finally{f.db.close()}
});
test("cross-device and process recovery retains exact objective and next action",async()=>{
 const f=fixture();try{
  const begun=await act(f,"begin",0,"work-begin1",{task_id:"site-1"});
  const advanced=await act(f,"step",begun.revision,"work-step01");
  const paused=await act(f,"pause",advanced.revision,"work-pause1");
  const secondClientView=await readExecutiveOffer(f.db,owner,f.tool);
  assert.equal(secondClientView.session.next_action,paused.next_action);
  assert.equal(secondClientView.session.objective,"Reply to email");
  const resumed=await act(f,"resume",paused.revision,"work-resume1");
  assert.equal(resumed.next_action,paused.next_action);
  assert.equal(resumed.status,"active");
 }finally{f.db.close()}
});
test("stale revisions fail without clobbering an interrupted session",async()=>{
 const f=fixture();try{
  const s=await act(f,"begin",0,"work-start2",{task_id:"site-1"});
  await act(f,"pause",s.revision,"work-pause2");
  await assert.rejects(act(f,"step",s.revision,"work-stale1"),/changed on another device/);
  const current=await readExecutiveOffer(f.db,owner,f.tool);
  assert.equal(current.session.status,"paused");
 }finally{f.db.close()}
});
test("network retry returns exact committed result and does not repeat action",async()=>{
 const f=fixture();try{
  const one=await act(f,"begin",0,"work-replay1",{task_id:"site-1"});
  const two=await act(f,"begin",0,"work-replay1",{task_id:"site-1"});
  assert.equal(two.reused,true);
  assert.equal(two.revision,one.revision);
  assert.equal(f.db.db.prepare("SELECT count(*) n FROM companion_session_ops").get().n,1);
  await assert.rejects(act(f,"defer_offer",0,"work-replay1",{task_id:"site-1"}),/different content/);
 }finally{f.db.close()}
});
test("an account cannot read or change another owner's session",async()=>{
 const f=fixture();try{
  await act(f,"begin",0,"work-isolate1",{task_id:"site-1"});
  const otherView=await readExecutiveOffer(f.db,other,f.tool);
  assert.equal(otherView.session.revision,0);
  assert.notEqual(otherView.session.objective,"Reply to email");
  await assert.rejects(updateWorkSession(f.db,other,{command:"resume",revision:1,operation_id:"work-intrude1"},f.tool),/changed/);
 }finally{f.db.close()}
});
test("completion changes session state, not underlying task state",async()=>{
 const f=fixture();try{
  const one=await act(f,"begin",0,"work-finish1",{task_id:"site-1"});
  const ended=await act(f,"finish",one.revision,"work-finish2");
  assert.equal(ended.status,"completed");
  assert.match(ended.last_outcome,/NOT been marked complete/);
  assert.equal(f.db.db.prepare("SELECT name FROM sqlite_master WHERE name='tasks'").get(),undefined);
 }finally{f.db.close()}
});
test("failed suggestion changes do not start a different task silently",async()=>{
 const f=fixture();try{
  f.setTasks(seed.slice(1));
  await assert.rejects(act(f,"begin",0,"work-candidate",{task_id:"site-1"}),/changed/);
  const viewed=await readExecutiveOffer(f.db,owner,f.tool);
  assert.equal(viewed.session.status,"idle");
 }finally{f.db.close()}
});
test("no state change, including a declined offer, can be mistaken for verified provider action",()=>{
 const state=applySessionCommand(null,"defer_offer",suggestWork(seed));
 assert.equal(state.status,"paused");
 assert.match(state.last_outcome,/without repeat prompts/);
 assert.throws(()=>applySessionCommand(state,"step"),/Resume/);
 assert.equal(applySessionCommand(state,"finish").status,"completed");
});
