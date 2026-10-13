import { KIKI_CHARACTER } from "./kiki-character.mjs";
/**
 * Kiki Sites MCP tool logic, v0.1.
 *
 * This module contains portable database operations for a Site-hosted MCP
 * adapter. It is not an MCP transport, an auth provider, or a deployed Site.
 * The Sites adapter MUST pass ownerId from verified session credentials.
 * All ChatGPT-origin events use the fixed 'chatgpt' channel.
 */

const MAX_MESSAGE = 6000;
const MAX_HISTORY = 40;
const ID_RE = /^[a-zA-Z0-9][a-zA-Z0-9._:-]{7,127}$/;

function requireOwner(ctx) {
  if (!ctx || typeof ctx.ownerId !== "string" || !ID_RE.test(ctx.ownerId)) {
    throw new Error("Missing verified Kiki account identity.");
  }
  return ctx.ownerId;
}
function identifier(value, name) {
  if (typeof value !== "string" || !ID_RE.test(value)) {
    throw new Error(name + " must be a stable ID of 8 to 128 safe characters.");
  }
  return value;
}
function message(value, name) {
  if (typeof value !== "string" || value.trim().length < 1 ||
      value.length > MAX_MESSAGE) {
    throw new Error(name + " must contain 1 to 6000 characters.");
  }
  return value;
}
function randomId(prefix) {
  return prefix + crypto.randomUUID();
}
function failConflict() {
  throw new Error("This request key already belongs to different content or a different thread.");
}
async function getEventByRetry(db, key, channel) {
  return db.prepare(
    "SELECT e.event_id,e.thread_id,e.turn_id,e.content_json,t.owner_id FROM interaction_events e " +
    "JOIN conversation_threads t ON t.thread_id=e.thread_id " +
    "WHERE e.source_channel=? AND e.idempotency_key=?"
  ).bind(channel, key).first();
}
function parseContent(row) {
  return JSON.parse(row.content_json);
}

/**
 * Expose these operations through verified Sites MCP tools:
 *   kiki_get_brief, kiki_get_history, kiki_prepare_turn, kiki_commit_turn.
 * For readable calls use db.prepare().bind().first()/all().
 * For writes use db.batch() so all related rows commit or roll back together.
 */
export function createKikiToolService(db, channel = "chatgpt") {
  if (!db || typeof db.prepare !== "function" || typeof db.batch !== "function") {
    throw new Error("A D1-compatible database binding is required.");
  }

  async function getBrief(ctx, { limit = 8 } = {}) {
    const owner = requireOwner(ctx);
    if (!Number.isInteger(limit) || limit < 1 || limit > 20) {
      throw new Error("Brief limit must be between 1 and 20.");
    }
    const results = await db.prepare(
      "SELECT e.seq,e.thread_id,e.turn_id,e.event_kind,e.source_channel," +
      "e.recorded_at,e.content_json FROM interaction_events e " +
      "JOIN conversation_threads t ON t.thread_id=e.thread_id " +
      "WHERE t.owner_id=? ORDER BY e.seq DESC LIMIT ?"
    ).bind(owner, limit).all();
    const pending = await db.prepare(
      "SELECT count(*) AS count FROM conversation_turns ct " +
      "JOIN conversation_threads t ON t.thread_id=ct.thread_id " +
      "WHERE t.owner_id=? AND ct.state='prepared'"
    ).bind(owner).first();
    return {
      subject_id: "kiki",
      character: KIKI_CHARACTER,
      latest_events: results.results.map(e => ({
        seq: e.seq, thread_id: e.thread_id, turn_id: e.turn_id,
        kind: e.event_kind, source: e.source_channel,
        time: e.recorded_at, content: JSON.parse(e.content_json)
      })).reverse(),
      pending_turns: pending?.count ?? 0,
      disclaimer: "Recorded dialogue is evidence of what was said, not proof of Kiki's autobiographical experience."
    };
  }

  async function getHistory(ctx, { thread_id, after_seq = 0, limit = 20 } = {}) {
    const owner = requireOwner(ctx);
    identifier(thread_id, "thread_id");
    if (!Number.isSafeInteger(after_seq) || after_seq < 0 ||
        !Number.isInteger(limit) || limit < 1 || limit > MAX_HISTORY) {
      throw new Error("Invalid history cursor or limit.");
    }
    const thread = await db.prepare(
      "SELECT owner_id FROM conversation_threads WHERE thread_id=?"
    ).bind(thread_id).first();
    if (!thread || thread.owner_id !== owner) {
      throw new Error("Conversation not found.");
    }
    const events = await db.prepare(
      "SELECT seq,event_id,turn_id,event_kind,source_channel,recorded_at,content_json,provenance_json " +
      "FROM interaction_events WHERE thread_id=? AND seq>? ORDER BY seq LIMIT ?"
    ).bind(thread_id, after_seq, limit).all();
    return {
      thread_id,
      events: events.results.map(row => ({
        seq: row.seq, event_id: row.event_id, turn_id: row.turn_id,
        kind: row.event_kind, source: row.source_channel, time: row.recorded_at,
        content: JSON.parse(row.content_json),
        provenance: JSON.parse(row.provenance_json)
      })),
      next_after_seq: events.results.at(-1)?.seq ?? after_seq
    };
  }

  async function prepareTurn(ctx, { text, retry_key, thread_id = null } = {}) {
    const owner = requireOwner(ctx);
    message(text, "text");
    identifier(retry_key, "retry_key");
    retry_key = owner + ":" + retry_key;
    if (thread_id !== null) identifier(thread_id, "thread_id");

    const existing = await getEventByRetry(db, retry_key, channel);
    if (existing) {
      if (existing.owner_id !== owner || (thread_id && thread_id !== existing.thread_id) ||
          parseContent(existing).text !== text) failConflict();
      return {
        thread_id: existing.thread_id, turn_id: existing.turn_id,
        user_event_id: existing.event_id, status: "prepared",
        character: KIKI_CHARACTER,
        reused: true
      };
    }
    const tid = thread_id || randomId("thread-");
    const turn = randomId("turn-");
    const event = randomId("event-");
    const content = JSON.stringify({ text });
    const provenance = JSON.stringify({
      source_channel: channel, client: channel === "chatgpt" ? "kiki_mcp" : "kiki_web",
      attribution: "user_message_explicitly_submitted",
      model_id: ctx.modelId || null
    });

    // A guarded INSERT ensures a client cannot write into another owner's
    // thread even if two requests race during thread creation.
    await db.batch([
      db.prepare(
        "INSERT INTO conversation_threads(thread_id,owner_id) VALUES(?,?) " +
        "ON CONFLICT(thread_id) DO NOTHING"
      ).bind(tid, owner),
      db.prepare(
        "INSERT INTO interaction_events(event_id,thread_id,turn_id,event_kind," +
        "source_channel,actor_id,actor_kind,idempotency_key,content_json,provenance_json) " +
        "SELECT ?,?,?,'message.user_received',?,?,'human',?,?,? " +
        "WHERE EXISTS(SELECT 1 FROM conversation_threads WHERE thread_id=? AND owner_id=?) " +
        "ON CONFLICT(source_channel,idempotency_key) DO NOTHING"
      ).bind(event, tid, turn, channel, owner, retry_key, content, provenance, tid, owner),
      db.prepare(
        "INSERT INTO conversation_turns(turn_id,thread_id,user_event_id) " +
        "SELECT ?,?,? WHERE EXISTS(" +
        "SELECT 1 FROM interaction_events WHERE event_id=? AND thread_id=?)"
      ).bind(turn, tid, event, event, tid)
    ]);
    const receipt = await getEventByRetry(db, retry_key, channel);
    if (!receipt || receipt.owner_id !== owner ||
        (thread_id && receipt.thread_id !== thread_id) ||
        parseContent(receipt).text !== text) failConflict();
    return {
      thread_id: receipt.thread_id, turn_id: receipt.turn_id,
      user_event_id: receipt.event_id, status: "prepared",
        character: KIKI_CHARACTER,
      reused: receipt.event_id !== event
    };
  }

  async function commitTurn(ctx, { turn_id, text } = {}) {
    const owner = requireOwner(ctx);
    identifier(turn_id, "turn_id");
    message(text, "text");
    const turn = await db.prepare(
      "SELECT ct.turn_id,ct.thread_id,ct.user_event_id,ct.assistant_event_id,ct.state " +
      "FROM conversation_turns ct JOIN conversation_threads t ON t.thread_id=ct.thread_id " +
      "WHERE ct.turn_id=? AND t.owner_id=?"
    ).bind(turn_id, owner).first();
    if (!turn) throw new Error("Prepared turn not found.");
    if (turn.state === "abandoned") throw new Error("Turn was abandoned.");
    if (turn.state === "committed") {
      const committed = await db.prepare(
        "SELECT content_json FROM interaction_events WHERE event_id=?"
      ).bind(turn.assistant_event_id).first();
      if (!committed || parseContent(committed).text !== text) failConflict();
      return {
        thread_id: turn.thread_id, turn_id,
        assistant_event_id: turn.assistant_event_id, text, reused: true
      };
    }

    const event = randomId("event-");
    const idem = "commit:" + turn_id;
    const provenance = JSON.stringify({
      source_channel: channel, client: channel === "chatgpt" ? "kiki_mcp" : "kiki_web",
      attribution: "assistant_candidate_committed",
      host_display_confirmed: false,
      model_id: ctx.modelId || null
    });
    await db.batch([
      db.prepare(
        "INSERT INTO interaction_events(event_id,thread_id,turn_id,event_kind," +
        "source_channel,actor_id,actor_kind,idempotency_key,content_json,provenance_json,parent_event_id) " +
        "VALUES(?,?,?,'message.assistant_committed',?,'kiki','kiki_renderer',?,?,?,?) " +
        "ON CONFLICT(source_channel,idempotency_key) DO NOTHING"
      ).bind(event, turn.thread_id, turn_id, channel, idem, JSON.stringify({ text }), provenance, turn.user_event_id),
      db.prepare(
        "UPDATE conversation_turns SET assistant_event_id=(" +
        "SELECT event_id FROM interaction_events WHERE source_channel=? AND idempotency_key=?)," +
        "state='committed' WHERE turn_id=? AND state='prepared' AND EXISTS(" +
        "SELECT 1 FROM conversation_threads WHERE thread_id=? AND owner_id=?)"
      ).bind(channel, idem, turn_id, turn.thread_id, owner)
    ]);
    const result = await db.prepare(
      "SELECT ct.assistant_event_id,e.content_json FROM conversation_turns ct " +
      "JOIN interaction_events e ON e.event_id=ct.assistant_event_id " +
      "WHERE ct.turn_id=?"
    ).bind(turn_id).first();
    if (!result || parseContent(result).text !== text) failConflict();
    return {
      thread_id: turn.thread_id, turn_id,
      assistant_event_id: result.assistant_event_id, text,
      reused: result.assistant_event_id !== event
    };
  }

  return { getBrief, getHistory, prepareTurn, commitTurn };
}

export const KIKI_SITE_TOOL_DEFINITIONS = Object.freeze([
  {
    name: "kiki_get_brief", readonly: true,
    description: "Read the latest Kiki interaction receipts across channels, with source attribution and pending turn count.",
    input: { type: "object", properties: { limit: { type: "integer", minimum: 1, maximum: 20 } }, additionalProperties: false }
  },
  {
    name: "kiki_get_history", readonly: true,
    description: "Read a single authorized Kiki thread in chronological order, preserving original channel and provenance.",
    input: { type: "object", properties: {
      thread_id: { type: "string" }, after_seq: { type: "integer", minimum: 0 },
      limit: { type: "integer", minimum: 1, maximum: 40 }
    }, required: ["thread_id"], additionalProperties: false }
  },
  {
    name: "kiki_prepare_turn", readonly: false,
    description: "Record an explicit ChatGPT-to-Kiki user message once and return its immutable turn ID.",
    input: { type: "object", properties: {
      text: { type: "string", minLength: 1, maxLength: 6000 },
      retry_key: { type: "string" }, thread_id: { type: "string" }
    }, required: ["text", "retry_key"], additionalProperties: false }
  },
  {
    name: "kiki_commit_turn", readonly: false,
    description: "Commit the exact assistant text for one prepared turn. Does not claim native ChatGPT UI output was captured.",
    input: { type: "object", properties: {
      turn_id: { type: "string" }, text: { type: "string", minLength: 1, maxLength: 6000 }
    }, required: ["turn_id", "text"], additionalProperties: false }
  }
]);
