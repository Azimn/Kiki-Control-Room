import { applySessionCommand, suggestWork } from "./executive-support.mjs";
const ID = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{7,127}$/;
function check(ok, message) { if (!ok) throw Error(message); }
function stmt(db,sql,...values) { return db.prepare(sql).bind(...values); }
async function setup(db) {
  await db.batch([
    db.prepare("CREATE TABLE IF NOT EXISTS companion_sessions(owner_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,content_json TEXT NOT NULL,updated_at TEXT NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS companion_session_ops(owner_id TEXT NOT NULL,operation_id TEXT NOT NULL,revision_after INTEGER NOT NULL,result_json TEXT NOT NULL,PRIMARY KEY(owner_id,operation_id),UNIQUE(owner_id,revision_after))")
  ]);
}
async function read(db,owner) {
  const row = await stmt(db,"SELECT revision,content_json,updated_at FROM companion_sessions WHERE owner_id=?",owner).first();
  return row ? {...JSON.parse(row.content_json),revision:row.revision,updated_at:row.updated_at,available:true} :
    {available:true,revision:0,status:"idle",objective:"",next_action:"",last_outcome:"",updated_at:null};
}
export async function readExecutiveOffer(db,ctx,taskTool) {
  check(ctx && ID.test(ctx.ownerId||""),"Verified owner required.");
  const [tasks, session] = await Promise.all([taskTool.getTasks(ctx),taskTool.getWorkSession(ctx)]);
  const offered = session.status==="active" || session.status==="paused" ? null :
    suggestWork(tasks.hosted_tasks,tasks.pc_snapshot);
  return {offer:offered,session,
    explanation:offered ? "Suggested from an actual open task. No deadline or urgency was inferred." : "No eligible open task in the available snapshots."};
}
export async function updateWorkSession(db,ctx,payload,taskTool) {
  const owner=ctx?.ownerId;
  check(typeof owner==="string"&&ID.test(owner),"Verified owner required.");
  const a=payload||{};
  check(typeof a.operation_id==="string"&&ID.test(a.operation_id),"Stable operation ID required.");
  check(Number.isSafeInteger(a.revision)&&a.revision>=0,"Session revision required.");
  check(["begin","defer_offer","pause","defer","resume","step","next","finish"].includes(a.command),"Unsupported session action.");
  check(typeof a.detail==="undefined" || (typeof a.detail==="string"&&a.detail.length<=1000),"Invalid next action.");
  await setup(db);
  const prior=await stmt(db,"SELECT result_json FROM companion_session_ops WHERE owner_id=? AND operation_id=?",owner,a.operation_id).first();
  if(prior) {
    const response=JSON.parse(prior.result_json);
    check(response.command===a.command && response.input_revision===a.revision &&
      response.input_detail===(a.detail||"") && response.input_task_id===(a.task_id||""),"Operation ID reused with different content.");
    return {...response.session,reused:true};
  }
  let current=await read(db,owner);
  check(current.revision===a.revision,"Session changed on another device. Refresh and try again.");
  let offer=null;
  if(a.command==="begin"||a.command==="defer_offer") {
    const tasks=await taskTool.getTasks(ctx);
    offer=suggestWork(tasks.hosted_tasks,tasks.pc_snapshot);
    check(offer && String(offer.task_id)===String(a.task_id),"Suggested task changed. Refresh before starting.");
  }
  const next=applySessionCommand(current,a.command,offer,a.detail||"");
  const revision=current.revision+1,updated_at=new Date().toISOString();
  const session={...next,revision,updated_at,available:true};
  const response={command:a.command,input_revision:a.revision,input_detail:a.detail||"",
    input_task_id:a.task_id||"",session};
  const result=JSON.stringify(response);
  const oldContent=JSON.stringify({objective:current.objective,next_action:current.next_action,
    last_outcome:current.last_outcome,status:current.status});
  // The shared AIRI writer also CAS-updates this record by revision. Do not
  // add a second authority or an incompatible session representation.
  await stmt(db,"INSERT OR IGNORE INTO companion_sessions(owner_id,revision,content_json,updated_at) VALUES(?,0,?,?)",
    owner,oldContent,updated_at).run();
  // One transaction: a unique revision receipt permits exactly one winner.
  // If the live AIRI writer wins, the following revision gate rejects this change.
  await db.batch([
    stmt(db,"INSERT INTO companion_session_ops(owner_id,operation_id,revision_after,result_json) SELECT ?,?,?,? WHERE EXISTS(SELECT 1 FROM companion_sessions WHERE owner_id=? AND revision=?)",
      owner,a.operation_id,revision,result,owner,a.revision),
    stmt(db,"UPDATE companion_sessions SET revision=?,content_json=?,updated_at=? WHERE owner_id=? AND revision=? AND EXISTS(SELECT 1 FROM companion_session_ops WHERE owner_id=? AND operation_id=?)",
      revision,JSON.stringify(next),updated_at,owner,a.revision,owner,a.operation_id)
  ]);
  const saved=await read(db,owner);
  check(saved.revision===revision&&saved.objective===next.objective&&saved.next_action===next.next_action&&
    saved.last_outcome===next.last_outcome&&saved.status===next.status,
    "Session changed concurrently. Reload before proceeding.");
  return {...saved,reused:false};
}
