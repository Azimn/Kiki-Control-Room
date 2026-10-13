import { env } from 'cloudflare:workers';
import { createKikiToolService } from './kiki-tools.mjs';
export function service(channel='chatgpt'):any{return createKikiToolService(env.DB,channel)}
export async function taskAction(owner:string,args:any){
 const db=env.DB; if(!db)throw Error("Database unavailable.");
 if(args.action==='create'){
 if(typeof args.title!=='string'||!args.title.trim()||args.title.length>500)throw Error('Use a task title of 1 to 500 characters.');
 if(typeof args.id!=='string'||!/^task-[a-f0-9-]{36}$/.test(args.id))throw Error('Invalid task request ID.');
 const old=await db.prepare('SELECT * FROM tasks WHERE id=?').bind(args.id).first();
 if(old&&(old.owner_id!==owner||old.title!==args.title))throw Error('Task request conflicts with existing content.');
 const thread='tasks-'+owner;
 await db.batch([db.prepare('INSERT INTO conversation_threads(thread_id,owner_id) VALUES(?,?) ON CONFLICT DO NOTHING').bind(thread,owner),db.prepare('INSERT INTO tasks(id,owner_id,title) VALUES(?,?,?) ON CONFLICT DO NOTHING').bind(args.id,owner,args.title),db.prepare("INSERT INTO interaction_events(event_id,thread_id,turn_id,event_kind,source_channel,actor_id,actor_kind,idempotency_key,content_json,provenance_json) VALUES(?,?,?,'task.created','kiki_web',?,'human',?,?,?) ON CONFLICT DO NOTHING").bind('event-'+crypto.randomUUID(),thread,args.id,owner,'create:'+args.id,JSON.stringify({task_id:args.id,title:args.title}),JSON.stringify({source_channel:'kiki_web',attribution:'explicit_user_action'}))]);
 }else{
 const task=await db.prepare('SELECT * FROM tasks WHERE id=? AND owner_id=?').bind(args.id,owner).first();if(!task)throw Error('Task not found.');if(args.action==='complete'&&task.status==='done')return {ok:true};
 if(!['complete','snooze','resume'].includes(args.action))throw Error('Unknown task action.');
 const until=args.action==='snooze'?new Date(Date.now()+3600000).toISOString():null;
 const status=args.action==='complete'?'done':'open';
 await db.batch([db.prepare('UPDATE tasks SET status=?,snoozed_until=? WHERE id=? AND owner_id=?').bind(status,until,args.id,owner),db.prepare("INSERT INTO interaction_events(event_id,thread_id,turn_id,event_kind,source_channel,actor_id,actor_kind,idempotency_key,content_json,provenance_json) VALUES(?,?,?,?, 'kiki_web',?,'human',?,?,?)").bind('event-'+crypto.randomUUID(),'tasks-'+owner,args.id,args.action==='complete'?'task.completed':'commitment.revised',owner,'task-action:'+crypto.randomUUID(),JSON.stringify({task_id:args.id,action:args.action,snoozed_until:until}),JSON.stringify({source_channel:'kiki_web',attribution:'explicit_user_action'}))]);
 }
 return {ok:true};
}
