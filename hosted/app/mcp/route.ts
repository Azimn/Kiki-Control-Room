import { service } from '../../lib/service';
import { KIKI_SITE_TOOL_DEFINITIONS } from '../../lib/kiki-tools.mjs';
export const dynamic='force-dynamic';
export async function POST(r:Request){
 if(Number(r.headers.get('content-length')||0)>16000)return new Response('Too large',{status:413});
 let req:any;try{const raw=await r.text();if(raw.length>16000)return new Response('Too large',{status:413});req=JSON.parse(raw)}catch{return new Response('Invalid JSON',{status:400})}
 const answer=(result:any)=>Response.json({jsonrpc:'2.0',id:req.id,result});
 if(req.method==='initialize')return answer({protocolVersion:'2025-03-26',capabilities:{tools:{}},serverInfo:{name:'Kiki Control Room',version:'1.0.0'},instructions:'Retrieve Kiki context first. Record only explicit Kiki-directed messages. Commit the exact intended reply, retaining the returned text. Never claim unrelated ChatGPT messages were captured. Use the returned character guidance to preserve K1-K1’s established voice: a bubbly, playful valley-girl programming genius and golden Art Deco android, with 1980s and 1990s cultural references. Keep technical answers precise and follow the user’s current preferences. Retrieve context, prepare the explicit user turn, compose the reply, commit the exact text, then display the committed text. History receipts are distinct from canonical Kiki-Mind autobiographical memory.'});
 if(req.method==='notifications/initialized')return new Response(null,{status:202});
 if(req.method==='ping')return answer({});
 if(req.method==='tools/list')return answer({tools:KIKI_SITE_TOOL_DEFINITIONS.map((d:any)=>({name:d.name,description:d.description,inputSchema:d.input,annotations:{readOnlyHint:d.readonly,destructiveHint:false,idempotentHint:true,openWorldHint:false}}))});
 const owner=r.headers.get('oai-authenticated-user-id');if(!owner)return new Response('Authentication required',{status:401});
 if(req.method!=='tools/call')return Response.json({jsonrpc:'2.0',id:req.id,error:{code:-32601,message:'Method not found'}});
 const def=KIKI_SITE_TOOL_DEFINITIONS.find((d:any)=>d.name===req.params?.name);const a=req.params?.arguments||{};
 try{if(!def||!a||Array.isArray(a)||typeof a!=='object'||Object.keys(a).some(k=>!Object.keys(def.input.properties).includes(k)))throw Error('Invalid tool arguments.');
 const methods:any={kiki_get_brief:'getBrief',kiki_get_history:'getHistory',kiki_prepare_turn:'prepareTurn',kiki_commit_turn:'commitTurn',kiki_get_tasks:'getTasks',kiki_get_work_session:'getWorkSession',kiki_get_channel_status:'getChannelStatus'};
 const result=await (service() as any)[methods[def.name]]({ownerId:owner},a);return answer({content:[{type:'text',text:JSON.stringify(result)}]});
 }catch(e){return answer({isError:true,content:[{type:'text',text:e instanceof Error?e.message:'Tool failed.'}]})}
}
