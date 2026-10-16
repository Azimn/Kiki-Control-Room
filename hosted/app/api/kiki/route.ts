import { env } from 'cloudflare:workers';
import { service,taskAction } from '../../../lib/service';
export const dynamic='force-dynamic';
function identity(r:Request){const id=r.headers.get('oai-authenticated-user-id');if(!id)throw Error('Sign in required.');return {ownerId:id}}
export async function GET(r:Request){try{const ctx=identity(r);const brief=await service().getBrief(ctx,{limit:20});const [tasks,session,connections]=await Promise.all([service().getTasks(ctx),service().getWorkSession(ctx),service().getChannelStatus(ctx)]);return Response.json({brief,tasks:tasks.hosted_tasks,operational:{tasks,session,connections}},{headers:{'Cache-Control':'no-store'}})}catch{return Response.json({error:'Unable to load your workspace. Sign in and try again.'},{status:401})}}
export async function POST(r:Request){try{const ctx=identity(r);if(r.headers.get('origin')!==new URL(r.url).origin)return Response.json({error:'Origin rejected.'},{status:403});const raw=await r.text();if(raw.length>12000)throw Error('Request too large.');const a=JSON.parse(raw);let result;
 if(a.action==='message')result=await service('kiki_web').prepareTurn(ctx,{text:a.text,retry_key:a.retry_key,thread_id:a.thread_id||null});
 else if(a.action==='history')result=await service().getHistory(ctx,{thread_id:a.thread_id,after_seq:a.after_seq||0,limit:40});
 else if(a.action==='export'){const records=await env.DB!.prepare('SELECT e.* FROM interaction_events e JOIN conversation_threads t ON t.thread_id=e.thread_id WHERE t.owner_id=? ORDER BY seq').bind(ctx.ownerId).all();const tasks=await env.DB!.prepare('SELECT * FROM tasks WHERE owner_id=?').bind(ctx.ownerId).all();result={format:'kiki-interaction-export',version:1,exported_at:new Date().toISOString(),events:records.results,tasks:tasks.results,backup_status:'Portable plaintext export. Independent encrypted backup and restoration are not yet verified.'}}
 else result=await taskAction(ctx.ownerId,a);
 return Response.json(result,{headers:{'Cache-Control':'no-store'}});
 }catch(e){return Response.json({error:e instanceof Error?e.message:'Request failed.'},{status:400})}}
