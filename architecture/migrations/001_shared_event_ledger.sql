-- Kiki Control Room: portable D1/SQLite shared event ledger v0.1
-- This migration is design-stage and not deployed to any remote database.
-- The cloud log is canonical for cross-interface *interaction receipts* and
-- operational events; Kiki-Mind has its own stricter subject-history rules.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversation_threads (
  thread_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  subject_id TEXT NOT NULL DEFAULT 'kiki',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK (length(thread_id) >= 8),
  CHECK (length(owner_id) > 0),
  CHECK (subject_id = 'kiki')
);

-- Only the authenticated service allocates event IDs or signs provenance.
-- Client channel labels and model declarations are claims, not proof.
CREATE TABLE IF NOT EXISTS interaction_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  thread_id TEXT NOT NULL REFERENCES conversation_threads(thread_id),
  turn_id TEXT NOT NULL,
  event_kind TEXT NOT NULL CHECK (
    event_kind IN (
      'message.user_received',
      'message.assistant_committed',
      'task.created',
      'task.completed',
      'commitment.created',
      'commitment.revised',
      'commitment.fulfilled',
      'calendar.action_proposed',
      'calendar.action_approved',
      'calendar.action_executed',
      'system.correction'
    )
  ),
  source_channel TEXT NOT NULL CHECK (
    source_channel IN ('telegram','chatgpt','kiki_web','local','scheduler','system')
  ),
  source_native_id TEXT,
  actor_id TEXT NOT NULL,
  actor_kind TEXT NOT NULL CHECK (actor_kind IN ('human','kiki_renderer','system','tool')),
  idempotency_key TEXT NOT NULL,
  content_json TEXT NOT NULL CHECK (json_valid(content_json)),
  provenance_json TEXT NOT NULL CHECK (json_valid(provenance_json)),
  parent_event_id TEXT REFERENCES interaction_events(event_id),
  recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE (source_channel, idempotency_key),
  CHECK (length(event_id) >= 8),
  CHECK (length(turn_id) >= 8),
  CHECK (length(actor_id) > 0),
  CHECK (length(idempotency_key) >= 8)
);

CREATE INDEX IF NOT EXISTS ix_interaction_events_thread_seq
  ON interaction_events(thread_id,seq);
CREATE INDEX IF NOT EXISTS ix_interaction_events_turn
  ON interaction_events(turn_id,seq);
CREATE INDEX IF NOT EXISTS ix_interaction_events_source_native
  ON interaction_events(source_channel,source_native_id);

-- This table is operational coordination. It is mutable, unlike the event log.
-- The service creates a receipt when it accepts a user turn and attaches the
-- committed response in a transaction, not by overwriting the original event.
CREATE TABLE IF NOT EXISTS conversation_turns (
  turn_id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES conversation_threads(thread_id),
  user_event_id TEXT NOT NULL UNIQUE REFERENCES interaction_events(event_id),
  assistant_event_id TEXT UNIQUE REFERENCES interaction_events(event_id),
  state TEXT NOT NULL DEFAULT 'prepared' CHECK (state IN ('prepared','committed','abandoned')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK (
    (state = 'prepared' AND assistant_event_id IS NULL) OR
    (state = 'committed' AND assistant_event_id IS NOT NULL) OR
    (state = 'abandoned' AND assistant_event_id IS NULL)
  )
);
CREATE INDEX IF NOT EXISTS ix_conversation_turns_thread
  ON conversation_turns(thread_id,created_at);

-- Projections and sync cursors may be rebuilt; neither can change history.
CREATE TABLE IF NOT EXISTS local_replica_cursors (
  replica_id TEXT PRIMARY KEY,
  last_seq INTEGER NOT NULL DEFAULT 0 CHECK (last_seq >= 0),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TRIGGER IF NOT EXISTS interaction_events_no_update
BEFORE UPDATE ON interaction_events
BEGIN
  SELECT RAISE(ABORT,'interaction_events is append-only');
END;

CREATE TRIGGER IF NOT EXISTS interaction_events_no_delete
BEFORE DELETE ON interaction_events
BEGIN
  SELECT RAISE(ABORT,'interaction_events is append-only');
END;
