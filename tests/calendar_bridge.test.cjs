const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const code = fs.readFileSync(path.join(__dirname, '../runtime/apps_script/CalendarBridge.gs'), 'utf8');
const context = vm.createContext({Utilities: {computeHmacSha256Signature: (payload, secret) =>
  Array.from(crypto.createHmac('sha256', secret).update(payload).digest())}, console});
vm.runInContext(code, context);
const now = Date.parse('2026-10-13T18:00:00Z');
const cfg = {writeId: 'kiki', ids: ['work']};
function booking() { return {action: 'book', booking: {id:'a'.repeat(32),title:'Review syllabus',
  start:'2026-10-15T15:00:00Z',duration:30,offered:now/1000}}; }
function backend({conflict=false,unavailable=false,existing=false,failedWrite=false}={}) {
  let writes = 0;
  const events = {};
  if (existing) events['kiki'+'a'.repeat(32)] = {id:'kiki'+'a'.repeat(32)};
  const api = (method, route, body) => {
    if (method === 'post') {
      writes++;
      events[body.id]=body;
      return failedWrite ? {code:503,data:{}} : {code:200,data:body};
    }
    if (route.includes('/events?')) return unavailable ? {code:403,data:{}} :
      {code:200,data:{items:conflict ? [{status:'confirmed'}] : []}};
    if (route.includes('/events/')) {
      const id = route.split('/').pop();
      return events[id] ? {code:200,data:events[id]} : {code:404,data:{}};
    }
    return {code:200,data:{}};
  };
  return {api, get writes() { return writes; }};
}
test('HMAC rejects modified payload, wrong key and stale timestamps', () => {
  const secret='s'.repeat(64), payload=JSON.stringify({timestamp:now/1000,action:'health'});
  const signature=crypto.createHmac('sha256',secret).update(payload).digest('hex');
  assert.equal(context.bridgeAuth_({payload,signature},secret,now).action,'health');
  assert.equal(context.bridgeAuth_({payload:payload+' ',signature},secret,now),null);
  assert.equal(context.bridgeAuth_({payload,signature},'z'.repeat(64),now),null);
  assert.equal(context.bridgeAuth_({payload,signature},secret,now+301000),null);
});
test('explicit booking writes once and retry returns existing event', () => {
  const b=backend();
  assert.equal(context.bridgeBook_(booking(),cfg,now,b.api).code,'booked');
  assert.equal(context.bridgeBook_(booking(),cfg,now,b.api).code,'booked');
  assert.equal(b.writes,1);
});
test('lost insert response is reconciled by deterministic event ID', () => {
  const b=backend({failedWrite:true});
  assert.equal(context.bridgeBook_(booking(),cfg,now,b.api).code,'unavailable');
  assert.equal(context.bridgeBook_(booking(),cfg,now,b.api).code,'booked');
  assert.equal(b.writes,1);
});
test('work-calendar conflict blocks write', () => {
  const b=backend({conflict:true});
  assert.equal(context.bridgeBook_(booking(),cfg,now,b.api).code,'conflict');
  assert.equal(b.writes,0);
});
test('missing calendar permission blocks write rather than ignoring it', () => {
  const b=backend({unavailable:true});
  assert.equal(context.bridgeBook_(booking(),cfg,now,b.api).code,'unavailable');
  assert.equal(b.writes,0);
});
test('expired request and missing configuration never write', () => {
  const b=backend();
  assert.equal(context.bridgeBook_(booking(),cfg,now+1801000,b.api).code,'invalid');
  assert.equal(context.bridgeBook_(booking(),{writeId:'',ids:[]},now,b.api).code,'unavailable');
  assert.equal(b.writes,0);
});
test('Calendar API may omit items for an empty calendar', () => {
  const b=backend();
  const api=(method,route,body)=>route.includes('/events?') && method==='get' ? {code:200,data:{}} : b.api(method,route,body);
  assert.equal(context.bridgeBook_(booking(),cfg,now,api).code,'booked');
  assert.equal(b.writes,1);
});
test('same request ID cannot claim success for changed booking details',()=>{
 const b=backend();assert.equal(context.bridgeBook_(booking(),cfg,now,b.api).code,'booked');
 for(const change of [{title:'Different'},{start:'2026-10-15T16:00:00Z'},{duration:45}]){
  const retry=booking();Object.assign(retry.booking,change);
  assert.equal(context.bridgeBook_(retry,cfg,now,b.api).code,'invalid');
 }
 assert.equal(b.writes,1);
});
test('equivalent timezone instants match; canceled, all-day and foreign events do not',()=>{
 const b=backend();context.bridgeBook_(booking(),cfg,now,b.api);
 const same=booking();same.booking.start='2026-10-15T10:00:00-05:00';
 assert.equal(context.bridgeBook_(same,cfg,now,b.api).code,'booked');
 for(const data of [{status:'cancelled'},{summary:'Review syllabus',start:{date:'2026-10-15'},end:{date:'2026-10-16'}},{summary:'Review syllabus',start:{dateTime:booking().booking.start},end:{dateTime:'2026-10-15T15:30:00Z'}}]){
  assert.equal(context.bridgeBook_(booking(),cfg,now,()=>({code:200,data})).code,'invalid');
 }
});
test('insert collision also compares the existing payload',()=>{
 for(const match of [true,false]){
  let read=0,writes=0;const request=booking();
  const api=(method,route,body)=>{
   if(method==='post'){writes++;return {code:409,data:{}}}
   if(route.includes('/events?'))return {code:200,data:{items:[]}};
   if(route.includes('/events/')){if(++read===1)return {code:404,data:{}};return {code:200,data:{summary:match?request.booking.title:'Different',start:{dateTime:request.booking.start},end:{dateTime:'2026-10-15T15:30:00Z'},extendedProperties:{private:{kiki_request_id:request.booking.id}}}}}
  };
  assert.equal(context.bridgeBook_(request,cfg,now,api).code,match?'booked':'invalid');assert.equal(writes,1);
 }
});
