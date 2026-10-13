"""Validate the portable shared-history SQL against real SQLite.

This exercises the schema and invariant constraints. It does not assert that
a cloud database, MCP endpoint, or ChatGPT plugin is deployed.
"""
import sqlite3
import unittest
from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[1] / "architecture" / "migrations" / "001_shared_event_ledger.sql"


class SharedLedgerContractTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(MIGRATION.read_text(encoding="utf-8"))
        self.db.execute(
            "INSERT INTO conversation_threads(thread_id,owner_id) VALUES(?,?)",
            ("thread-0001", "owner-one"),
        )

    def tearDown(self):
        self.db.close()

    def add_event(self, event, key, channel="telegram", kind="message.user_received", actor="human"):
        self.db.execute(
            """INSERT INTO interaction_events
            (event_id,thread_id,turn_id,event_kind,source_channel,source_native_id,
             actor_id,actor_kind,idempotency_key,content_json,provenance_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (event, "thread-0001", "turn-0001", kind, channel,
             channel + ":" + key, "owner-one", actor, key, '{"text":"hello"}',
             '{"transport":"verified-by-server"}'),
        )

    def test_schema_initializes(self):
        tables = {r[0] for r in self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        self.assertTrue({
            "conversation_threads", "interaction_events",
            "conversation_turns", "local_replica_cursors"
        }.issubset(tables))

    def test_multichannel_same_conversation(self):
        self.add_event("event-0001", "retry-0001", "telegram")
        self.add_event("event-0002", "retry-0002", "chatgpt",
                       "message.assistant_committed", "kiki_renderer")
        self.add_event("event-0003", "retry-0003", "kiki_web")
        rows = self.db.execute(
            "SELECT source_channel FROM interaction_events ORDER BY seq"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["telegram", "chatgpt", "kiki_web"])

    def test_duplicate_retry_rejected(self):
        self.add_event("event-0001", "retry-0001")
        with self.assertRaises(sqlite3.IntegrityError):
            self.add_event("event-0002", "retry-0001")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM interaction_events"
        ).fetchone()[0], 1)

    def test_history_cannot_be_mutated_in_place(self):
        self.add_event("event-0001", "retry-0001")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE interaction_events SET actor_id='fake' WHERE event_id='event-0001'")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM interaction_events WHERE event_id='event-0001'")

    def test_receipt_requires_real_user_event(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO conversation_turns(turn_id,thread_id,user_event_id) VALUES(?,?,?)",
                ("turn-0001", "thread-0001", "event-missing"),
            )
        self.add_event("event-0001", "retry-0001")
        self.db.execute(
            "INSERT INTO conversation_turns(turn_id,thread_id,user_event_id) VALUES(?,?,?)",
            ("turn-0001", "thread-0001", "event-0001"),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE conversation_turns SET state='committed' WHERE turn_id='turn-0001'"
            )
        self.add_event("event-0002", "retry-0002", "chatgpt",
                       "message.assistant_committed", "kiki_renderer")
        self.db.execute(
            """UPDATE conversation_turns
               SET assistant_event_id='event-0002',state='committed'
               WHERE turn_id='turn-0001'""",
        )
        self.assertEqual(self.db.execute(
            "SELECT state FROM conversation_turns WHERE turn_id='turn-0001'"
        ).fetchone()[0], "committed")

    def test_malformed_payload_or_channel_fails_closed(self):
        self.add_event("event-0001", "retry-0001")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """INSERT INTO interaction_events
                (event_id,thread_id,turn_id,event_kind,source_channel,
                 actor_id,actor_kind,idempotency_key,content_json,provenance_json)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                ("event-0003", "thread-0001", "turn-0001",
                 "message.user_received", "unknown_app", "owner-one",
                 "human", "retry-0003", '{"okay":true}', '{}'),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """INSERT INTO interaction_events
                (event_id,thread_id,turn_id,event_kind,source_channel,
                 actor_id,actor_kind,idempotency_key,content_json,provenance_json)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                ("event-0004", "thread-0001", "turn-0001",
                 "message.user_received", "chatgpt", "owner-one",
                 "human", "retry-0004", '{broken}', '{}'),
            )


if __name__ == "__main__":
    unittest.main()
