/**
 * Kiki Control Room: zero-hosting-cost notification and calendar relay.
 * Google Apps Script owns timing and Google Calendar access, not Kiki's mind.
 * No AI provider is required for the scheduler to function.
 *
 * Setup instructions: see docs/FREE_RUNTIME_SETUP.md.
 */
const KIKI_DEFAULT_ZONE = "America/Chicago";
const KIKI_STATE_KEY = "KIKI_RELAY_STATE_V1";

function installKikiRelay() {
  const props = PropertiesService.getScriptProperties();
  relayConfig_(props); // Fail before installing an unusable trigger.
  const prior = ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === "tickKikiRelay");
  prior.forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger("tickKikiRelay").timeBased().everyMinutes(5).create();
  Logger.log("Kiki relay installed. The first tick will run within the trigger interval.");
}

function tickKikiRelay() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) return;
  try {
    const props = PropertiesService.getScriptProperties();
    const cfg = relayConfig_(props);
    const state = loadRelayState_(props);
    const now = new Date();
    try {
      pollTelegram_(cfg, state, now, props);
    } catch (err) {
      Logger.log("Telegram polling failed: " + String(err));
    }
    if (!state.paused) {
      dailyCheckin_(cfg, state, now, props);
      calendarCheck_(cfg, state, now, props);
      followupCheck_(cfg, state, now, props);
    }
    pruneReceipts_(state, now);
    saveRelayState_(props, state);
  } finally {
    lock.releaseLock();
  }
}

function relayConfig_(props) {
  const get = key => String(props.getProperty(key) || "").trim();
  const token = get("TELEGRAM_BOT_TOKEN");
  const chat = get("TELEGRAM_CHAT_ID");
  if (!token || !chat) throw new Error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in Script Properties.");
  const ids = get("READ_CALENDAR_IDS").split(",").map(x => x.trim()).filter(Boolean);
  const timezone = get("KIKI_TIMEZONE") || KIKI_DEFAULT_ZONE;
  return {
    token: token, chat: chat, ids: ids,
    writeId: get("WRITE_CALENDAR_ID"),
    timezone: timezone,
    showTitles: get("SHOW_CALENDAR_TITLES") === "true",
    dailyHour: 9
  };
}

function loadRelayState_(props) {
  const raw = props.getProperty(KIKI_STATE_KEY);
  const state = raw ? JSON.parse(raw) : {};
  if (!Array.isArray(state.tasks)) state.tasks = [];
  if (!state.receipts || typeof state.receipts !== "object") state.receipts = {};
  if (!state.checkin || typeof state.checkin !== "object") state.checkin = {};
  state.offset = Number(state.offset || 0);
  state.nextId = Number(state.nextId || 1);
  state.paused = Boolean(state.paused);
  return state;
}

function saveRelayState_(props, state) {
  const raw = JSON.stringify(state);
  if (raw.length > 75000) throw new Error("Relay state is too large: archive completed tasks.");
  props.setProperty(KIKI_STATE_KEY, raw);
}

function localDay_(date, tz) {
  return Utilities.formatDate(date, tz, "yyyy-MM-dd");
}
function localHour_(date, tz) {
  return Number(Utilities.formatDate(date, tz, "H"));
}
function isQuiet_(date, cfg) {
  const hour = localHour_(date, cfg.timezone);
  return hour < 8 || hour >= 22;
}

function telegram_(cfg, method, body) {
  const url = "https://api.telegram.org/bot" + cfg.token + "/" + method;
  const resp = UrlFetchApp.fetch(url, {
    method: "post", contentType: "application/json",
    payload: JSON.stringify(body), muteHttpExceptions: true
  });
  const code = resp.getResponseCode();
  let data;
  try { data = JSON.parse(resp.getContentText()); }
  catch (_) { throw new Error("Telegram returned non-JSON (" + code + ")."); }
  if (code < 200 || code >= 300 || !data.ok) {
    throw new Error("Telegram " + method + " failed (" + code + "): " + String(data.description || "unknown"));
  }
  return data.result;
}
function tell_(cfg, text) {
  return telegram_(cfg, "sendMessage", {chat_id: cfg.chat, text: text});
}

function pollTelegram_(cfg, state, now, props) {
  const updates = telegram_(cfg, "getUpdates", {offset: state.offset, limit: 50, timeout: 0});
  updates.forEach(update => {
    const id = Number(update.update_id);
    if (id < state.offset) return;
    state.offset = id + 1;
    const msg = update.message;
    if (msg && msg.chat && String(msg.chat.id) === cfg.chat && typeof msg.text === "string") {
      try { interpret_(msg.text.trim(), cfg, state, now); }
      catch (err) { Logger.log("Command error: " + String(err)); tell_(cfg, "That command didn't work. Try /help."); }
    }
    // Persist the acknowledgment and command before processing the next update.
    saveRelayState_(props, state);
  });
}

function acknowledge_(state) {
  state.checkin.awaiting = false;
  state.checkin.nextNudgeAt = null;
}
function interpret_(text, cfg, state, now) {
  if (!text.startsWith("/")) return;
  const parts = text.split(/\s+/);
  const cmd = parts[0].split("@")[0].toLowerCase();
  if (cmd === "/help" || cmd === "/start") {
    acknowledge_(state);
    tell_(cfg, "Kiki on deck. /add task, /status, /done ID, /snooze 15, /block YYYY-MM-DD HH:MM MIN title, /confirm, /cancel, /pause, /resume.");
    return;
  }
  if (cmd === "/pause") {
    acknowledge_(state); state.paused = true;
    tell_(cfg, "Okay, going quiet. I'll wait for /resume.");
    return;
  }
  if (cmd === "/resume") {
    state.paused = false; acknowledge_(state);
    tell_(cfg, "Back on frequency. Send /status whenever you're ready.");
    return;
  }
  if (cmd === "/add") {
    const task = text.slice(parts[0].length).trim();
    if (!task || task.length > 200) { tell_(cfg, "Use /add followed by a short task (up to 200 characters)."); return; }
    const id = state.nextId++;
    state.tasks.push({id: id, text: task, status: "open", added: now.toISOString()});
    acknowledge_(state);
    tell_(cfg, "Got it. #" + id + " is in the queue. We can tackle it together.");
    return;
  }
  if (cmd === "/status") {
    acknowledge_(state);
    const open = state.tasks.filter(t => t.status === "open").slice(0, 8);
    tell_(cfg, open.length ? "On deck:\n" + open.map(t => "#" + t.id + " " + t.text).join("\n") : "Queue clear. Nothing is waiting on your task list.");
    return;
  }
  if (cmd === "/done") {
    const id = Number(parts[1]);
    const task = state.tasks.find(t => t.id === id && t.status === "open");
    if (!Number.isInteger(id) || !task) { tell_(cfg, "Use /done ID for an open task. Send /status to see IDs."); return; }
    task.status = "done"; task.finished = now.toISOString();
    acknowledge_(state);
    tell_(cfg, "Nice. #" + id + " is done. Want the next one? /status");
    return;
  }
  if (cmd === "/snooze") {
    const min = parts[1] ? Number(parts[1]) : 15;
    if (!Number.isInteger(min) || min < 5 || min > 240) {
      tell_(cfg, "Try /snooze 15 (5 to 240 minutes)."); return;
    }
    state.checkin.awaiting = true;
    state.checkin.nextNudgeAt = now.getTime() + min * 60000;
    tell_(cfg, "You got " + min + " minutes. I'll check back.");
    return;
  }
  if (cmd === "/block") {
    const match = text.match(/^\/block(?:@\w+)?\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+(\d{1,3})\s+(.+)$/i);
    if (!match || !cfg.writeId) {
      tell_(cfg, cfg.writeId ? "Use /block YYYY-MM-DD HH:MM MIN title." : "Set WRITE_CALENDAR_ID in Script Properties to enable calendar blocks.");
      return;
    }
    const start = Utilities.parseDate(match[1] + " " + match[2], cfg.timezone, "yyyy-MM-dd HH:mm");
    const duration = Number(match[3]);
    const title = match[4].trim();
    if (Utilities.formatDate(start, cfg.timezone, "yyyy-MM-dd HH:mm") !== match[1] + " " + match[2] ||
        start.getTime() <= now.getTime() || duration < 5 || duration > 240 || title.length > 120) {
      tell_(cfg, "Choose a future valid local time, a 5-240 minute duration, and a title up to 120 characters."); return;
    }
    state.pendingBlock = {title: title, start: start.toISOString(), duration: duration, offered: now.getTime()};
    acknowledge_(state);
    tell_(cfg, "Proposed: " + title + " at " + match[1] + " " + match[2] + " (" + duration + " min). Reply /confirm to create it or /cancel.");
    return;
  }
  if (cmd === "/cancel") {
    state.pendingBlock = null;
    acknowledge_(state);
    tell_(cfg, "Calendar proposal canceled.");
    return;
  }
  if (cmd === "/confirm") {
    const b = state.pendingBlock;
    if (!b || now.getTime() - b.offered > 30 * 60000) {
      state.pendingBlock = null; tell_(cfg, "No current calendar proposal. Start with /block."); return;
    }
    const start = new Date(b.start), end = new Date(start.getTime() + b.duration * 60000);
    if (start.getTime() <= now.getTime()) {
      state.pendingBlock = null; tell_(cfg, "That start time has passed. Propose a new block."); return;
    }
    const target = CalendarApp.getCalendarById(cfg.writeId);
    if (!target) { tell_(cfg, "Write calendar not accessible to this account."); return; }
    const conflicts = Array.from(new Set(cfg.ids.concat([cfg.writeId]))).some(id => {
      const cal = CalendarApp.getCalendarById(id);
      return cal && cal.getEvents(start, end).length > 0;
    });
    if (conflicts) { tell_(cfg, "That block overlaps an existing event. Nothing was created. Use /cancel or propose another time."); return; }
    target.createEvent(b.title, start, end, {description: "Created by Kiki Control Room with explicit /confirm."});
    state.pendingBlock = null;
    acknowledge_(state);
    tell_(cfg, "Booked: " + b.title + ". It's on the calendar.");
    return;
  }
  tell_(cfg, "I don't recognize that command. Try /help.");
}

function dailyCheckin_(cfg, state, now, props) {
  const hour = localHour_(now, cfg.timezone);
  const day = localDay_(now, cfg.timezone);
  if (hour < cfg.dailyHour || hour >= cfg.dailyHour + 2 || state.lastCheckinDay === day) return;
  const openCount = state.tasks.filter(t => t.status === "open").length;
  tell_(cfg, "Morning! I'm here. We've got " + openCount + " open " + (openCount === 1 ? "task" : "tasks") +
    ". Reply /status to pick one, /snooze 15 if you need a moment, or /pause to stop reminders.");
  state.lastCheckinDay = day;
  state.checkin = {awaiting: true, nextNudgeAt: now.getTime() + 15 * 60000, nudges: 0, day: day};
  saveRelayState_(props, state);
}

function followupCheck_(cfg, state, now, props) {
  const c = state.checkin;
  if (!c.awaiting || !c.nextNudgeAt || now.getTime() < c.nextNudgeAt || isQuiet_(now, cfg)) return;
  const n = Number(c.nudges || 0);
  if (n >= 6) { c.awaiting = false; saveRelayState_(props, state); return; }
  tell_(cfg, n === 0 ? "Checking in. Want to knock out one task together? /status or /snooze 15." :
    "Still around when you're ready. /status, /snooze 30, or /pause.");
  c.nudges = n + 1;
  c.nextNudgeAt = now.getTime() + (n === 0 ? 30 : 60) * 60000;
  saveRelayState_(props, state);
}

function calendarCheck_(cfg, state, now, props) {
  if (isQuiet_(now, cfg) || !cfg.ids.length) return;
  const until = new Date(now.getTime() + 15 * 60000);
  cfg.ids.forEach(id => {
    try {
      const cal = CalendarApp.getCalendarById(id);
      if (!cal) { Logger.log("Calendar not accessible: " + id); return; }
      cal.getEvents(now, until).forEach(ev => {
        const start = ev.getStartTime();
        const remaining = start.getTime() - now.getTime();
        if (remaining < 0 || remaining > 15 * 60000) return;
        const key = id + "|" + ev.getId() + "|" + start.toISOString();
        if (state.receipts[key]) return;
        const when = Utilities.formatDate(start, cfg.timezone, "h:mm a");
        const label = cfg.showTitles ? ev.getTitle() : "A calendar commitment";
        tell_(cfg, label + " starts at " + when + ". Need to prep or move something?");
        state.receipts[key] = now.getTime();
        saveRelayState_(props, state);
      });
    } catch (err) { Logger.log("Calendar check failed: " + String(err)); }
  });
}

function pruneReceipts_(state, now) {
  const cutoff = now.getTime() - 3 * 86400000;
  Object.keys(state.receipts).forEach(k => {
    if (state.receipts[k] < cutoff) delete state.receipts[k];
  });
  // Keep the queue lightweight. Canonical Kiki-Mind history is separate.
  state.tasks = state.tasks.filter(t => t.status === "open" ||
    (t.finished && new Date(t.finished).getTime() > now.getTime() - 14 * 86400000));
}
