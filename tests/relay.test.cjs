"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.resolve(__dirname, "../runtime/apps_script/Code.gs"), "utf8");

function harness() {
  const sent = [];
  const blocks = [];
  let updates = [];
  let calendarEvents = [];
  const props = {
    TELEGRAM_BOT_TOKEN: "test-token",
    TELEGRAM_CHAT_ID: "42",
    READ_CALENDAR_IDS: "test-calendar",
    WRITE_CALENDAR_ID: "test-calendar",
    KIKI_TIMEZONE: "America/Chicago"
  };
  const properties = {
    getProperty(k) { return props[k] || null; },
    setProperty(k, v) { props[k] = String(v); }
  };
  const calendar = {
    getEvents(start, end) {
      return calendarEvents.filter(e => e.getStartTime() >= start && e.getStartTime() < end);
    },
    createEvent(title, start, end) { blocks.push({title, start, end}); }
  };
  const parts = (date, tz) => {
    const entries = new Intl.DateTimeFormat("en-US", {
      timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23"
    }).formatToParts(date);
    return Object.fromEntries(entries.map(e => [e.type, e.value]));
  };
  const ctx = {
    Date, JSON, Number, String, Object, Array, Math,
    PropertiesService: {getScriptProperties() { return properties; }},
    LockService: {getScriptLock() { return {tryLock() { return true; }, releaseLock() {}}; }},
    ScriptApp: {
      getProjectTriggers() {return [];},
      newTrigger() {return {timeBased() {return this;}, everyMinutes() {return this;}, create() {}};}
    },
    Logger: {log() {}},
    CalendarApp: {getCalendarById(id) {return id === "test-calendar" ? calendar : null;}},
    Utilities: {
      formatDate(d, tz, pattern) {
        const p = parts(d, tz);
        if (pattern === "H") return String(Number(p.hour));
        if (pattern === "yyyy-MM-dd") return [p.year, p.month, p.day].join("-");
        if (pattern === "yyyy-MM-dd HH:mm") return [p.year, p.month, p.day].join("-") + " " + p.hour + ":" + p.minute;
        return p.hour + ":" + p.minute;
      },
      parseDate(s) {return new Date(s.replace(" ", "T") + ":00-05:00");},
      newBlob(s) {return {getBytes() {return Buffer.from(s, "utf8");}};}
    },
    UrlFetchApp: {
      fetch(url, options) {
        const method = url.split("/").pop();
        const args = JSON.parse(options.payload);
        let result = {};
        if (method === "sendMessage") sent.push(args.text);
        if (method === "getUpdates") result = updates.filter(u => u.update_id >= args.offset);
        return {getResponseCode() {return 200;}, getContentText() {return JSON.stringify({ok: true, result});}};
      }
    }
  };
  vm.runInNewContext(source + "\nthis.kiki = {relayConfig_, loadRelayState_, interpret_, dailyCheckin_, followupCheck_, calendarCheck_, pollTelegram_, tickKikiRelay, saveRelayState_};", ctx);
  const api = ctx.kiki;
  return {
    api, sent, blocks, props, properties,
    cfg: api.relayConfig_(properties),
    state: api.loadRelayState_(properties),
    setUpdates(x) {updates = x;},
    setEvents(x) {calendarEvents = x;}
  };
}

const morning = new Date("2026-10-14T14:05:00.000Z");

test("task queue accepts commands and records completion", () => {
  const h = harness();
  h.api.interpret_("/add Review faculty memo", h.cfg, h.state, morning);
  assert.equal(h.state.tasks[0].text, "Review faculty memo");
  h.api.interpret_("/status", h.cfg, h.state, morning);
  assert.ok(h.sent.some(t => t.includes("Review faculty memo")));
  h.api.interpret_("/done 1", h.cfg, h.state, morning);
  assert.equal(h.state.tasks[0].status, "done");
});

test("calendar proposal never writes without confirmation", () => {
  const h = harness();
  h.api.interpret_("/block 2026-10-15 10:00 30 Design review", h.cfg, h.state, morning);
  assert.equal(h.blocks.length, 0);
  assert.ok(h.state.pendingBlock);
  h.api.interpret_("/confirm", h.cfg, h.state, morning);
  assert.equal(h.blocks.length, 1);
  assert.equal(h.blocks[0].title, "Design review");
});

test("calendar conflict refuses to write", () => {
  const h = harness();
  const collision = new Date("2026-10-15T15:10:00.000Z");
  h.setEvents([{getStartTime() {return collision;}, getId() {return "1";}, getTitle() {return "Existing";}}]);
  h.api.interpret_("/block 2026-10-15 10:00 30 Design review", h.cfg, h.state, morning);
  h.api.interpret_("/confirm", h.cfg, h.state, morning);
  assert.equal(h.blocks.length, 0);
  assert.ok(h.sent.some(t => t.includes("overlaps")));
});

test("daily nudge sends once, follows up and stops after reply", () => {
  const h = harness();
  h.api.dailyCheckin_(h.cfg, h.state, morning, h.properties);
  assert.equal(h.state.checkin.awaiting, true);
  const n = h.sent.length;
  h.api.dailyCheckin_(h.cfg, h.state, morning, h.properties);
  assert.equal(h.sent.length, n);
  h.api.followupCheck_(h.cfg, h.state, new Date(morning.getTime() + 16 * 60000), h.properties);
  assert.equal(h.sent.length, n + 1);
  h.api.interpret_("/status", h.cfg, h.state, morning);
  const after = h.sent.length;
  h.api.followupCheck_(h.cfg, h.state, new Date(morning.getTime() + 90 * 60000), h.properties);
  assert.equal(h.sent.length, after);
});

test("pause prevents proactive daily and calendar checks", () => {
  const h = harness();
  h.api.interpret_("/pause", h.cfg, h.state, morning);
  h.api.saveRelayState_(h.properties, h.state);
  h.api.tickKikiRelay();
  assert.equal(h.props.KIKI_RELAY_STATE_V1.includes('"paused":true'), true);
  assert.equal(h.sent.filter(x => x.includes("Morning!")).length, 0);
});

test("event notice is deduplicated and hides titles by default", () => {
  const h = harness();
  h.setEvents([{getStartTime() {return new Date(morning.getTime()+10*60000);}, getId() {return "event1";}, getTitle() {return "Confidential meeting";}}]);
  h.api.calendarCheck_(h.cfg, h.state, morning, h.properties);
  const n = h.sent.length;
  assert.equal(n, 1);
  assert.ok(!h.sent[0].includes("Confidential meeting"));
  h.api.calendarCheck_(h.cfg, h.state, morning, h.properties);
  assert.equal(h.sent.length, n);
});

test("only configured Telegram chat can issue commands", () => {
  const h = harness();
  h.setUpdates([
    {update_id:1, message:{chat:{id:99}, text:"/add Untrusted"}},
    {update_id:2, message:{chat:{id:42}, text:"/add Trusted"}}
  ]);
  h.api.pollTelegram_(h.cfg, h.state, morning, h.properties);
  assert.equal(h.state.tasks.length, 1);
  assert.equal(h.state.tasks[0].text, "Trusted");
  assert.equal(h.state.offset, 3);
});

test("Script Properties cap respects 9 KB maximum", () => {
  const h = harness();
  h.state.tasks.push({id:1, text:"x".repeat(10000), status:"open"});
  assert.throws(() => h.api.saveRelayState_(h.properties, h.state), /exceeds Apps Script/);
});

test("calendar-only mode never polls Telegram or sends duplicate morning check-ins", () => {
  const h = harness();
  h.props.KIKI_CALENDAR_ONLY = "true";
  const c = h.api.relayConfig_(h.properties);
  assert.equal(c.calendarOnly, true);
  h.setUpdates([{update_id:1,message:{chat:{id:42},text:"/add Must not be processed"}}]);
  h.api.tickKikiRelay();
  assert.equal(h.api.loadRelayState_(h.properties).tasks.length, 0);
  assert.equal(h.sent.filter(x => x.includes("Morning!")).length, 0);
  assert.equal(h.api.loadRelayState_(h.properties).offset, 0);
});
